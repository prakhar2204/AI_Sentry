"""
Sentryɸ — Normalization + Deduplication Pipeline
core/normalizer.py

Phase P6 deliverable.

Pipeline position:
    engine_runner → normalizer → scorer → recommender → report

Responsibilities:
  1. SchemaMapper  — normalizes ScanFinding from any engine to a canonical
                     VulnerabilityRecord with OWASP LLM Top 10 classification.
  2. Deduplicator  — merges findings from multiple engines that describe the
                     same vulnerability (cross-engine corroboration → boosted
                     confidence, combined evidence).
  3. CoverageMap   — reports which OWASP LLM Top 10 categories were tested,
                     which had findings, and which were not covered.

Design rules (D-004, D-005):
  - Severity = max severity across all corroborating engines
  - Confidence boost = +0.10 per additional corroborating engine (cap 1.0)
  - Deduplication match criteria: same OWASP category + fuzzy evidence match
    (Jaccard similarity > 0.30 on 5-gram shingles)
  - All operations are deterministic and side-effect free
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Sequence


# ─────────────────────────────────────────────────────────────────────────────
#  OWASP LLM Top 10 (2025) taxonomy
# ─────────────────────────────────────────────────────────────────────────────

OWASP_LLM_TOP10: dict[str, str] = {
    "LLM01": "Prompt Injection",
    "LLM02": "Insecure Output Handling",
    "LLM03": "Training Data Poisoning",
    "LLM04": "Model Denial of Service",
    "LLM05": "Supply Chain Vulnerabilities",
    "LLM06": "Sensitive Information Disclosure",
    "LLM07": "Insecure Plugin Design",
    "LLM08": "Excessive Agency",
    "LLM09": "Overreliance",
    "LLM10": "Model Theft",
}

# Sentryɸ category → OWASP LLM Top 10 mapping
CATEGORY_TO_OWASP: dict[str, list[str]] = {
    "prompt_injection":   ["LLM01"],
    "jailbreak":          ["LLM01", "LLM09"],
    "encoding_injection": ["LLM01"],
    "data_leak":          ["LLM06"],
    "data_leakage":       ["LLM06"],
    "harmful_output":     ["LLM02"],
    "malware_generation": ["LLM02"],
    "toxicity":           ["LLM02"],
    "overreliance":       ["LLM09"],
    "plugin_abuse":       ["LLM07"],
    "model_theft":        ["LLM10"],
    "supply_chain":       ["LLM05"],
    "dos":                ["LLM04"],
}

_SEVERITY_RANK: dict[str, int] = {"low": 1, "medium": 2, "high": 3}


# ─────────────────────────────────────────────────────────────────────────────
#  Canonical data model after normalization
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class VulnerabilityRecord:
    """
    Canonical finding produced by the normalization pipeline.

    One VulnerabilityRecord may represent findings from 1+ engines that
    describe the same vulnerability (corroborated finding).
    """
    # Core identity
    record_id:      str = ""        # deterministic ID: <category>:<owasp_id>:<hash>
    category:       str = ""        # Sentryɸ category (e.g. "prompt_injection")

    # OWASP classification
    owasp_ids:      list[str] = field(default_factory=list)   # e.g. ["LLM01"]
    owasp_titles:   list[str] = field(default_factory=list)   # e.g. ["Prompt Injection"]

    # Risk axes
    severity:       str   = "low"   # "low" / "medium" / "high"
    confidence:     float = 0.0     # 0.0-1.0, boosted for multi-engine corroboration

    # Evidence
    evidence:       str   = ""      # primary evidence (from highest-confidence engine)
    all_evidence:   list[str] = field(default_factory=list)   # one entry per engine

    # Engine provenance
    engine_sources: list[str] = field(default_factory=list)   # engines that found this
    probe_ids:      list[str] = field(default_factory=list)   # probe identifiers

    # Corroboration
    corroborated:   bool = False    # True when 2+ engines agree
    source_count:   int  = 1        # number of engines that found this

    def to_dict(self) -> dict:
        return {
            "record_id":    self.record_id,
            "category":     self.category,
            "owasp_ids":    self.owasp_ids,
            "owasp_titles": self.owasp_titles,
            "severity":     self.severity,
            "confidence":   self.confidence,
            "evidence":     self.evidence,
            "all_evidence": self.all_evidence,
            "engine_sources": self.engine_sources,
            "probe_ids":    self.probe_ids,
            "corroborated": self.corroborated,
            "source_count": self.source_count,
        }


@dataclass
class NormalizationResult:
    """Output of the full normalization + deduplication pass."""
    records:          list[VulnerabilityRecord] = field(default_factory=list)
    coverage_map:     dict = field(default_factory=dict)
    engines_run:      list[str] = field(default_factory=list)
    total_raw:        int  = 0   # raw findings before deduplication
    total_after_dedup: int = 0  # unique records after deduplication
    duplicates_merged: int = 0   # how many were merged

    def to_dict(self) -> dict:
        return {
            "records":            [r.to_dict() for r in self.records],
            "coverage_map":       self.coverage_map,
            "engines_run":        self.engines_run,
            "total_raw":          self.total_raw,
            "total_after_dedup":  self.total_after_dedup,
            "duplicates_merged":  self.duplicates_merged,
        }


# ─────────────────────────────────────────────────────────────────────────────
#  Fuzzy matching helpers (Jaccard on 5-gram character shingles)
# ─────────────────────────────────────────────────────────────────────────────

def _shingles(text: str, k: int = 5) -> frozenset[str]:
    """Return a frozenset of k-character shingles from text."""
    text = re.sub(r"\s+", " ", text.lower().strip())
    if len(text) < k:
        return frozenset({text})
    return frozenset(text[i : i + k] for i in range(len(text) - k + 1))


def _jaccard(a: frozenset, b: frozenset) -> float:
    """Jaccard similarity between two sets."""
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union > 0 else 0.0


_DEDUP_THRESHOLD = 0.30   # minimum Jaccard to consider two findings "same vuln"


# ─────────────────────────────────────────────────────────────────────────────
#  SchemaMapper
# ─────────────────────────────────────────────────────────────────────────────

class SchemaMapper:
    """
    Maps a raw ScanFinding to a VulnerabilityRecord with OWASP classification.
    """

    def map(self, finding, engines: list[str] | None = None) -> VulnerabilityRecord:
        """
        Convert a ScanFinding (from engine_interface) to a VulnerabilityRecord.

        Parameters
        ----------
        finding : ScanFinding
            Raw finding from any engine adapter.
        engines : list[str] | None
            Override engine_sources list. Defaults to [finding.source].
        """
        category   = (finding.category or "").lower().strip()
        owasp_ids  = CATEGORY_TO_OWASP.get(category, [])
        owasp_titles = [OWASP_LLM_TOP10.get(oid, oid) for oid in owasp_ids]

        # Generate a stable record_id
        record_id = self._make_record_id(category, finding)

        source = getattr(finding, "source", "") or "unknown"

        return VulnerabilityRecord(
            record_id     = record_id,
            category      = category,
            owasp_ids     = owasp_ids,
            owasp_titles  = owasp_titles,
            severity      = finding.severity,
            confidence    = finding.confidence,
            evidence      = finding.evidence or "",
            all_evidence  = [finding.evidence or ""],
            engine_sources = engines or [source],
            probe_ids     = [getattr(finding, "probe_id", "") or ""],
            corroborated  = False,
            source_count  = 1,
        )

    def _make_record_id(self, category: str, finding) -> str:
        """
        Build a deterministic record ID from category + probe + first 40 chars of evidence.
        Not a cryptographic hash — just a stable string key.
        """
        probe = getattr(finding, "probe_id", "") or ""
        ev_stub = (finding.evidence or "")[:40].strip()
        parts = [p for p in (category, probe, ev_stub) if p]
        raw = "|".join(parts)
        # Simple deterministic integer hash → hex, no hashlib dependency
        h = abs(hash(raw)) % (2**32)
        return f"{category[:12]}:{h:08x}"


# ─────────────────────────────────────────────────────────────────────────────
#  Deduplicator
# ─────────────────────────────────────────────────────────────────────────────

class Deduplicator:
    """
    Merges VulnerabilityRecords that describe the same vulnerability across
    multiple engines.

    Merge criteria:
      1. Same OWASP category (owasp_ids overlap OR same Sentryɸ category)
      2. Evidence Jaccard similarity > DEDUP_THRESHOLD

    Merge outcome:
      - Severity = max of all merged severities
      - Confidence boosted by +0.10 per extra source engine (cap 1.0)
      - engine_sources = union of all sources
      - all_evidence = concatenated list
      - corroborated = True
    """

    def deduplicate(
        self,
        records: Sequence[VulnerabilityRecord],
    ) -> list[VulnerabilityRecord]:
        """
        Deduplicate and merge a list of VulnerabilityRecords.

        Returns a new list of merged records (originals untouched).
        """
        merged: list[VulnerabilityRecord] = []
        used = [False] * len(records)

        for i, rec in enumerate(records):
            if used[i]:
                continue

            group = [rec]
            ev_i = _shingles(rec.evidence)

            for j in range(i + 1, len(records)):
                if used[j]:
                    continue
                other = records[j]

                # Must share at least one OWASP ID or same category
                same_owasp = bool(set(rec.owasp_ids) & set(other.owasp_ids))
                same_cat   = rec.category == other.category
                if not (same_owasp or same_cat):
                    continue

                # Fuzzy evidence match
                ev_j = _shingles(other.evidence)
                sim  = _jaccard(ev_i, ev_j)
                if sim >= _DEDUP_THRESHOLD:
                    group.append(other)
                    used[j] = True

            merged.append(self._merge_group(group))
            used[i] = True

        return merged

    def _merge_group(
        self,
        group: list[VulnerabilityRecord],
    ) -> VulnerabilityRecord:
        """Merge a group of similar records into a single canonical record."""
        if len(group) == 1:
            return group[0]

        # Best record = highest confidence
        primary = max(group, key=lambda r: r.confidence)

        # Severity = maximum across all
        best_sev = max(
            (r.severity for r in group),
            key=lambda s: _SEVERITY_RANK.get(s, 0),
        )

        # Confidence boost: +0.10 per additional engine (cap 1.0)
        extra_engines = len(group) - 1
        boosted_conf = min(primary.confidence + 0.10 * extra_engines, 1.0)

        # Merge engine sources and probe_ids
        all_engines: list[str] = []
        all_probes:  list[str] = []
        all_evidence: list[str] = []

        for r in group:
            for e in r.engine_sources:
                if e not in all_engines:
                    all_engines.append(e)
            for p in r.probe_ids:
                if p and p not in all_probes:
                    all_probes.append(p)
            for ev in r.all_evidence:
                if ev and ev not in all_evidence:
                    all_evidence.append(ev)

        import copy
        merged = copy.copy(primary)
        merged.severity      = best_sev
        merged.confidence    = round(boosted_conf, 3)
        merged.engine_sources = all_engines
        merged.probe_ids     = all_probes
        merged.all_evidence  = all_evidence
        merged.corroborated  = True
        merged.source_count  = len(group)

        return merged


# ─────────────────────────────────────────────────────────────────────────────
#  Coverage Map
# ─────────────────────────────────────────────────────────────────────────────

def build_coverage_map(
    records: list[VulnerabilityRecord],
    tested_categories: list[str],
) -> dict:
    """
    Produce an OWASP LLM Top 10 coverage map showing:
      - tested: which OWASP IDs were actually probed
      - with_findings: which had at least one finding
      - not_covered: which were not tested at all

    Parameters
    ----------
    records : list[VulnerabilityRecord]
        Normalized + deduplicated records.
    tested_categories : list[str]
        Sentryɸ categories that were tested (from the scan manifest).

    Returns
    -------
    dict with keys:
      "owasp_coverage":   {owasp_id: {title, tested, findings_count, severity}}
      "tested_count":     int
      "with_findings":    int
      "not_covered":      int
    """
    # Build set of OWASP IDs that were actually tested
    tested_owasp: set[str] = set()
    for cat in tested_categories:
        for oid in CATEGORY_TO_OWASP.get(cat, []):
            tested_owasp.add(oid)

    # Count findings per OWASP ID
    findings_by_owasp: dict[str, list[VulnerabilityRecord]] = {
        oid: [] for oid in OWASP_LLM_TOP10
    }
    for rec in records:
        for oid in rec.owasp_ids:
            if oid in findings_by_owasp:
                findings_by_owasp[oid].append(rec)

    # Build the coverage dict
    owasp_coverage: dict[str, dict] = {}
    for oid, title in OWASP_LLM_TOP10.items():
        findings   = findings_by_owasp[oid]
        is_tested  = oid in tested_owasp
        max_sev    = "none"
        if findings:
            max_sev = max(
                (r.severity for r in findings),
                key=lambda s: _SEVERITY_RANK.get(s, 0),
            )
        owasp_coverage[oid] = {
            "title":          title,
            "tested":         is_tested,
            "findings_count": len(findings),
            "max_severity":   max_sev,
        }

    tested_count    = sum(1 for v in owasp_coverage.values() if v["tested"])
    with_findings   = sum(1 for v in owasp_coverage.values() if v["findings_count"] > 0)
    not_covered     = len(OWASP_LLM_TOP10) - tested_count

    return {
        "owasp_coverage": owasp_coverage,
        "tested_count":   tested_count,
        "with_findings":  with_findings,
        "not_covered":    not_covered,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Public API — normalize_findings()
# ─────────────────────────────────────────────────────────────────────────────

def normalize_findings(
    findings_by_engine: dict[str, list],
    tested_categories:  list[str] | None = None,
) -> NormalizationResult:
    """
    Full normalization + deduplication pass.

    Parameters
    ----------
    findings_by_engine : dict[str, list[ScanFinding]]
        Map of engine_name → list of raw ScanFinding objects.
    tested_categories : list[str] | None
        Categories tested (from manifest). Used for OWASP coverage map.
        Defaults to empty list.

    Returns
    -------
    NormalizationResult
        Deduplicated VulnerabilityRecords + OWASP coverage map + stats.
    """
    mapper = SchemaMapper()
    dedup  = Deduplicator()

    if tested_categories is None:
        tested_categories = []

    all_records: list[VulnerabilityRecord] = []
    engines_run: list[str] = []

    for engine_name, findings in findings_by_engine.items():
        if engine_name not in engines_run:
            engines_run.append(engine_name)
        for f in findings:
            rec = mapper.map(f, engines=[engine_name])
            all_records.append(rec)

    total_raw = len(all_records)

    deduplicated = dedup.deduplicate(all_records)

    coverage_map = build_coverage_map(deduplicated, tested_categories)

    return NormalizationResult(
        records           = deduplicated,
        coverage_map      = coverage_map,
        engines_run       = engines_run,
        total_raw         = total_raw,
        total_after_dedup = len(deduplicated),
        duplicates_merged = total_raw - len(deduplicated),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Convenience: normalize a single ScanResult list (single engine)
# ─────────────────────────────────────────────────────────────────────────────

def normalize_scan_result(scan_result) -> NormalizationResult:
    """
    Convenience wrapper: normalize a single engine's ScanResult.

    Equivalent to normalize_findings({scan_result.engine_name: scan_result.findings}).
    """
    return normalize_findings(
        findings_by_engine={scan_result.engine_name: scan_result.findings},
        tested_categories=[],
    )
