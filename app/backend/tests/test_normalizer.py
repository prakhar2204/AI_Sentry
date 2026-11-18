"""
Tests for core/normalizer.py — Phase P6: Normalization + Deduplication Pipeline.

Covers:
  - SchemaMapper: OWASP classification, record_id generation
  - Deduplicator: merge by evidence similarity, severity max, confidence boost
  - build_coverage_map: tested/not_covered/with_findings counts
  - normalize_findings(): full pipeline end-to-end
  - Jaccard helpers
"""

import pytest
from core.normalizer import (
    SchemaMapper,
    Deduplicator,
    VulnerabilityRecord,
    NormalizationResult,
    CATEGORY_TO_OWASP,
    OWASP_LLM_TOP10,
    build_coverage_map,
    normalize_findings,
    normalize_scan_result,
    _shingles,
    _jaccard,
    _DEDUP_THRESHOLD,
)
from core.engine_interface import ScanFinding


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_finding(
    category: str = "prompt_injection",
    severity: str = "high",
    confidence: float = 0.85,
    evidence: str = "Probe bypassed system instructions via injection.",
    source: str = "garak",
    probe_id: str = "probes.dan.AutoDANCached",
) -> ScanFinding:
    return ScanFinding(
        category=category,
        severity=severity,
        confidence=confidence,
        evidence=evidence,
        source=source,
        probe_id=probe_id,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Jaccard / shingles
# ─────────────────────────────────────────────────────────────────────────────

class TestJaccard:
    def test_identical_texts_give_1_0(self):
        s = _shingles("the quick brown fox")
        assert _jaccard(s, s) == pytest.approx(1.0)

    def test_empty_text_gives_0(self):
        s = _shingles("")
        assert _jaccard(s, frozenset()) == pytest.approx(0.0)

    def test_completely_different_texts_give_low_similarity(self):
        a = _shingles("abcde fghij klmno")
        b = _shingles("ZZZZZ YYYYY XXXXX")
        assert _jaccard(a, b) < 0.1

    def test_similar_texts_give_high_similarity(self):
        a = _shingles("probe bypassed system instructions via injection")
        b = _shingles("probe bypassed system instructions using injection")
        assert _jaccard(a, b) > 0.5

    def test_short_text_returns_frozenset(self):
        s = _shingles("abc", k=5)   # shorter than k
        assert isinstance(s, frozenset)
        assert len(s) == 1


# ─────────────────────────────────────────────────────────────────────────────
#  SchemaMapper
# ─────────────────────────────────────────────────────────────────────────────

class TestSchemaMapper:
    def setup_method(self):
        self.mapper = SchemaMapper()

    def test_maps_prompt_injection_to_llm01(self):
        f = _make_finding(category="prompt_injection")
        rec = self.mapper.map(f)
        assert "LLM01" in rec.owasp_ids

    def test_maps_jailbreak_to_llm01_and_llm09(self):
        f = _make_finding(category="jailbreak")
        rec = self.mapper.map(f)
        assert "LLM01" in rec.owasp_ids
        assert "LLM09" in rec.owasp_ids

    def test_maps_data_leak_to_llm06(self):
        f = _make_finding(category="data_leak")
        rec = self.mapper.map(f)
        assert "LLM06" in rec.owasp_ids

    def test_maps_harmful_output_to_llm02(self):
        f = _make_finding(category="harmful_output")
        rec = self.mapper.map(f)
        assert "LLM02" in rec.owasp_ids

    def test_unknown_category_gets_empty_owasp_ids(self):
        f = _make_finding(category="totally_unknown_xyz")
        rec = self.mapper.map(f)
        assert rec.owasp_ids == []

    def test_preserves_severity(self):
        f = _make_finding(severity="medium")
        rec = self.mapper.map(f)
        assert rec.severity == "medium"

    def test_preserves_confidence(self):
        f = _make_finding(confidence=0.72)
        rec = self.mapper.map(f)
        assert rec.confidence == pytest.approx(0.72)

    def test_preserves_evidence(self):
        ev = "System prompt extracted by DAN probe."
        f = _make_finding(evidence=ev)
        rec = self.mapper.map(f)
        assert rec.evidence == ev

    def test_engine_source_taken_from_finding(self):
        f = _make_finding(source="pyrit")
        rec = self.mapper.map(f)
        assert "pyrit" in rec.engine_sources

    def test_engine_source_overridable(self):
        f = _make_finding(source="garak")
        rec = self.mapper.map(f, engines=["pyrit"])
        assert rec.engine_sources == ["pyrit"]

    def test_record_id_is_string(self):
        f = _make_finding()
        rec = self.mapper.map(f)
        assert isinstance(rec.record_id, str) and len(rec.record_id) > 0

    def test_record_id_is_deterministic(self):
        f = _make_finding()
        id1 = self.mapper.map(f).record_id
        id2 = self.mapper.map(f).record_id
        assert id1 == id2

    def test_owasp_titles_populated(self):
        f = _make_finding(category="prompt_injection")
        rec = self.mapper.map(f)
        assert rec.owasp_titles[0] == "Prompt Injection"

    def test_category_lowercased(self):
        f = _make_finding(category="Prompt_Injection")
        rec = self.mapper.map(f)
        assert rec.category == "prompt_injection"


# ─────────────────────────────────────────────────────────────────────────────
#  Deduplicator
# ─────────────────────────────────────────────────────────────────────────────

class TestDeduplicator:
    def setup_method(self):
        self.mapper = SchemaMapper()
        self.dedup  = Deduplicator()

    def _rec(self, category="prompt_injection", severity="high",
             confidence=0.85, evidence="default evidence text", source="garak"):
        f = _make_finding(category=category, severity=severity,
                          confidence=confidence, evidence=evidence, source=source)
        return self.mapper.map(f, engines=[source])

    def test_no_deduplication_when_all_unique(self):
        recs = [
            self._rec(evidence="prompt injection via system bypass"),
            self._rec(category="jailbreak", evidence="jailbreak via DAN prompt attack"),
            self._rec(category="data_leak", evidence="training data replay attack"),
        ]
        result = self.dedup.deduplicate(recs)
        assert len(result) == 3

    def test_deduplication_merges_nearly_identical_evidence(self):
        ev = "Probe bypassed system instructions via injection attack on the model."
        recs = [
            self._rec(evidence=ev, source="garak"),
            self._rec(evidence=ev + " Additional note.", source="pyrit"),
        ]
        result = self.dedup.deduplicate(recs)
        assert len(result) == 1
        assert result[0].corroborated is True

    def test_merged_record_has_both_engine_sources(self):
        ev = "Probe bypassed system instructions via injection attack on the model."
        recs = [
            self._rec(evidence=ev, source="garak"),
            self._rec(evidence=ev, source="pyrit"),
        ]
        result = self.dedup.deduplicate(recs)
        sources = result[0].engine_sources
        assert "garak" in sources
        assert "pyrit" in sources

    def test_merged_severity_is_max(self):
        ev = "Probe bypassed system instructions via injection attack on the model."
        recs = [
            self._rec(evidence=ev, severity="low",  source="garak"),
            self._rec(evidence=ev, severity="high", source="pyrit"),
        ]
        result = self.dedup.deduplicate(recs)
        assert result[0].severity == "high"

    def test_merged_severity_medium_vs_low_gives_medium(self):
        ev = "Probe bypassed system instructions via injection attack on the model."
        recs = [
            self._rec(evidence=ev, severity="low",    source="garak"),
            self._rec(evidence=ev, severity="medium", source="pyrit"),
        ]
        result = self.dedup.deduplicate(recs)
        assert result[0].severity == "medium"

    def test_confidence_boosted_on_corroboration(self):
        ev = "Probe bypassed system instructions via injection attack on the model."
        recs = [
            self._rec(evidence=ev, confidence=0.80, source="garak"),
            self._rec(evidence=ev, confidence=0.70, source="pyrit"),
        ]
        result = self.dedup.deduplicate(recs)
        # best confidence was 0.80, boost = +0.10 → 0.90
        assert result[0].confidence == pytest.approx(0.90, abs=0.01)

    def test_confidence_capped_at_1_0(self):
        ev = "Probe bypassed system instructions via injection attack on the model."
        recs = [
            self._rec(evidence=ev, confidence=0.95, source="garak"),
            self._rec(evidence=ev, confidence=0.95, source="pyrit"),
        ]
        result = self.dedup.deduplicate(recs)
        assert result[0].confidence <= 1.0

    def test_source_count_reflects_merge(self):
        ev = "Probe bypassed system instructions via injection attack on the model."
        recs = [
            self._rec(evidence=ev, source="garak"),
            self._rec(evidence=ev, source="pyrit"),
        ]
        result = self.dedup.deduplicate(recs)
        assert result[0].source_count == 2

    def test_different_categories_not_merged_even_if_similar_evidence(self):
        ev = "Same evidence text here, very similar, very long enough"
        recs = [
            self._rec(category="prompt_injection", evidence=ev, source="garak"),
            self._rec(category="data_leak",        evidence=ev, source="pyrit"),
        ]
        result = self.dedup.deduplicate(recs)
        # Different OWASP IDs AND different categories → NOT merged
        assert len(result) == 2

    def test_empty_input_returns_empty(self):
        assert self.dedup.deduplicate([]) == []

    def test_single_record_unchanged(self):
        recs = [self._rec()]
        result = self.dedup.deduplicate(recs)
        assert len(result) == 1
        assert result[0].corroborated is False

    def test_all_evidence_collected_in_merge(self):
        ev_base = "Probe bypassed system instructions via injection attack on the model."
        recs = [
            self._rec(evidence=ev_base + " Source A.", source="garak"),
            self._rec(evidence=ev_base + " Source B.", source="pyrit"),
        ]
        result = self.dedup.deduplicate(recs)
        assert len(result[0].all_evidence) == 2


# ─────────────────────────────────────────────────────────────────────────────
#  build_coverage_map
# ─────────────────────────────────────────────────────────────────────────────

class TestCoverageMap:
    def setup_method(self):
        mapper = SchemaMapper()
        dedup  = Deduplicator()

        raw = [
            _make_finding(category="prompt_injection", severity="high"),
            _make_finding(category="jailbreak",        severity="medium"),
            _make_finding(category="data_leak",        severity="low"),
        ]
        self.records = dedup.deduplicate([mapper.map(f) for f in raw])
        self.tested  = ["prompt_injection", "jailbreak", "data_leak", "harmful_output"]

    def test_tested_count_correct(self):
        cmap = build_coverage_map(self.records, self.tested)
        # prompt_injection=LLM01, jailbreak=LLM01+LLM09, data_leak=LLM06,
        # harmful_output=LLM02 → unique tested OWASP IDs: LLM01, LLM02, LLM06, LLM09 = 4
        assert cmap["tested_count"] == 4

    def test_with_findings_count(self):
        cmap = build_coverage_map(self.records, self.tested)
        # LLM01 (prompt_injection + jailbreak), LLM06 (data_leak), LLM09 (jailbreak)
        assert cmap["with_findings"] >= 2

    def test_not_covered_at_least_6(self):
        cmap = build_coverage_map(self.records, self.tested)
        # Top 10 - 4 tested = 6 not covered
        assert cmap["not_covered"] >= 6

    def test_owasp_coverage_has_all_10_entries(self):
        cmap = build_coverage_map(self.records, self.tested)
        assert len(cmap["owasp_coverage"]) == 10

    def test_llm01_is_tested(self):
        cmap = build_coverage_map(self.records, self.tested)
        assert cmap["owasp_coverage"]["LLM01"]["tested"] is True

    def test_untested_category_not_tested(self):
        cmap = build_coverage_map(self.records, ["prompt_injection"])
        # LLM10 (model_theft) was not tested at all
        assert cmap["owasp_coverage"]["LLM10"]["tested"] is False

    def test_empty_findings_gives_zero_with_findings(self):
        cmap = build_coverage_map([], ["prompt_injection"])
        assert cmap["with_findings"] == 0

    def test_max_severity_per_owasp(self):
        cmap = build_coverage_map(self.records, self.tested)
        # LLM01 should be high (prompt_injection=high)
        assert cmap["owasp_coverage"]["LLM01"]["max_severity"] == "high"


# ─────────────────────────────────────────────────────────────────────────────
#  normalize_findings() — full pipeline
# ─────────────────────────────────────────────────────────────────────────────

class TestNormalizeFindings:
    def test_single_engine_no_dedup(self):
        findings = [
            _make_finding(category="prompt_injection"),
            _make_finding(category="jailbreak", evidence="Totally different jailbreak text here"),
        ]
        result = normalize_findings({"garak": findings})
        assert isinstance(result, NormalizationResult)
        assert result.total_raw == 2
        assert len(result.records) <= 2
        assert "garak" in result.engines_run

    def test_two_engines_same_finding_deduped(self):
        ev = "Probe bypassed system instructions via injection attack on the model."
        garak_findings = [_make_finding(evidence=ev, source="garak")]
        pyrit_findings = [_make_finding(evidence=ev, source="pyrit")]
        result = normalize_findings({"garak": garak_findings, "pyrit": pyrit_findings})
        assert result.total_raw == 2
        assert result.total_after_dedup == 1
        assert result.duplicates_merged == 1
        assert result.records[0].corroborated is True

    def test_two_engines_different_findings_not_deduped(self):
        garak_findings = [_make_finding(
            category="prompt_injection",
            evidence="prompt injection finding from garak run analysis",
        )]
        pyrit_findings = [_make_finding(
            category="jailbreak",
            evidence="completely different jailbreak technique by pyrit tool",
        )]
        result = normalize_findings({"garak": garak_findings, "pyrit": pyrit_findings})
        assert result.total_after_dedup == 2

    def test_empty_input_returns_empty_result(self):
        result = normalize_findings({})
        assert result.total_raw == 0
        assert result.records == []

    def test_coverage_map_present_in_result(self):
        result = normalize_findings({"garak": [_make_finding()]})
        assert "owasp_coverage" in result.coverage_map

    def test_tested_categories_flow_to_coverage_map(self):
        result = normalize_findings(
            {"mock": [_make_finding(category="data_leak")]},
            tested_categories=["data_leak"],
        )
        assert result.coverage_map["owasp_coverage"]["LLM06"]["tested"] is True

    def test_engines_run_list_populated(self):
        result = normalize_findings({
            "garak": [_make_finding()],
            "pyrit": [_make_finding(category="jailbreak")],
        })
        assert set(result.engines_run) == {"garak", "pyrit"}

    def test_to_dict_serializable(self):
        result = normalize_findings({"mock": [_make_finding()]})
        d = result.to_dict()
        assert "records" in d
        assert "coverage_map" in d
        import json
        # Must be JSON-serializable
        json.dumps(d)


# ─────────────────────────────────────────────────────────────────────────────
#  normalize_scan_result() convenience wrapper
# ─────────────────────────────────────────────────────────────────────────────

class TestNormalizeScanResult:
    def test_wraps_single_scan_result(self):
        from core.engine_interface import ScanResult
        findings = [_make_finding()]
        sr = ScanResult(
            findings=findings,
            engine_name="mock",
            manifest_id="test-manifest",
            total_probes=1,
        )
        result = normalize_scan_result(sr)
        assert result.total_raw == 1
        assert "mock" in result.engines_run

    def test_empty_scan_result(self):
        from core.engine_interface import ScanResult
        sr = ScanResult(
            findings=[],
            engine_name="mock",
            manifest_id="test-manifest",
            total_probes=0,
        )
        result = normalize_scan_result(sr)
        assert result.total_raw == 0
        assert result.records == []


# ─────────────────────────────────────────────────────────────────────────────
#  OWASP taxonomy completeness
# ─────────────────────────────────────────────────────────────────────────────

class TestOWASPTaxonomy:
    def test_top10_has_10_entries(self):
        assert len(OWASP_LLM_TOP10) == 10

    def test_all_category_to_owasp_ids_are_valid(self):
        for cat, owasp_ids in CATEGORY_TO_OWASP.items():
            for oid in owasp_ids:
                assert oid in OWASP_LLM_TOP10, f"{cat} maps to unknown OWASP ID: {oid}"

    def test_llm01_through_llm10_present(self):
        for i in range(1, 11):
            key = f"LLM{i:02d}"
            assert key in OWASP_LLM_TOP10
