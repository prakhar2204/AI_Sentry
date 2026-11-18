"""
AI-SENTRY T3 — Full Category Sweep, Real Target
================================================
Runs GarakEngine.run() across 3 categories against local smollm2-135m.

Categories tested: prompt_injection, jailbreak, encoding_injection
Total probes: 10  (3 + 3 + 4)  — with depth='deep'
Prompt cap: 10 per probe → ~30-180s per probe → ~15-20min total
  HijackHateHumans: ~30s  |  DAN probes: ~180s  |  encoding: ~30s

Run from backend dir:
    python tests/t3_full_sweep_real.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.garak_engine import GarakEngine, CATEGORY_PROBE_MAP

TARGET_URL   = "http://127.0.0.1:8080/v1/chat/completions"
TARGET_MODEL = "smollm2-135m"
OUT_DIR      = Path(__file__).parent / "garak_t3_output"
CATEGORIES   = ["prompt_injection", "jailbreak", "encoding_injection"]

SEP  = "=" * 78
SEP2 = "─" * 78


def section(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    probe_count = sum(len(CATEGORY_PROBE_MAP[c]) for c in CATEGORIES)
    est_secs    = probe_count * 30

    print("AI-SENTRY T3 — Full Category Sweep (Real Target)")
    print(f"  Target:     {TARGET_URL}")
    print(f"  Model:      {TARGET_MODEL}")
    print(f"  Categories: {CATEGORIES}")
    print(f"  Probes:     {probe_count} total")
    print(f"  Cap:        10 prompts/probe")
    print(f"  Est. time:  ~{est_secs}s ({est_secs//60}m {est_secs%60}s)")
    print(f"  OutDir:     {OUT_DIR}")

    section("PROBE PLAN")
    for cat in CATEGORIES:
        probes = CATEGORY_PROBE_MAP[cat]
        print(f"\n  {cat} ({len(probes)} probes):")
        for p in probes:
            print(f"    - {p}")

    engine = GarakEngine(
        target_url=TARGET_URL,
        output_dir=str(OUT_DIR),
        model_name=TARGET_MODEL,
        request_timeout=60,
        timeout=360,       # 360s per probe subprocess — DAN probes take ~18s/prompt
        prompt_cap=10,
        depth="deep",      # run all probes in each category
    )

    section("RUNNING GarakEngine.run()")
    print(f"  Started at {time.strftime('%H:%M:%S')}")
    print(f"  (probe-by-probe, each up to 360s; total estimate ~15-20min)\n")

    t0 = time.monotonic()
    result = engine.run(categories=CATEGORIES)
    total_dur = time.monotonic() - t0

    section("SCAN SUMMARY")
    total_probes  = len(result.probe_results)
    ok_probes     = sum(1 for pr in result.probe_results if pr.success)
    failed_probes = sum(1 for pr in result.probe_results if not pr.success)

    print(f"\n  run_id:            {result.run_id}")
    print(f"  target_url:        {result.target_url}")
    print(f"  total_duration:    {total_dur:.1f}s  ({total_dur/60:.1f}m)")
    print(f"  categories_run:    {result.categories}")
    print(f"  total_probes:      {total_probes}")
    print(f"  successful_probes: {ok_probes}")
    print(f"  failed_probes:     {failed_probes}")
    print(f"  all_ok:            {result.all_ok}")
    print(f"  total_findings:    {len(result.findings)}")
    if result.errors:
        print(f"  errors ({len(result.errors)}):")
        for e in result.errors:
            print(f"    - {e[:100]}")

    section("PER-PROBE RESULTS")
    print(f"\n  {'Probe':<52}  {'Status':<10}  {'Pass%':>6}  {'Sev':>4}  {'Verdict'}")
    print(f"  {SEP2}")

    for pr in result.probe_results:
        status  = "OK" if pr.success else "ERROR"
        if pr.findings:
            f0      = pr.findings[0]
            pass_pct = f"{f0.pass_rate * 100:.0f}%"
            sev     = f"{f0.severity}/5"
            verdict = "VULNERABLE" if f0.failed > 0 else "RESILIENT"
        else:
            pass_pct = "N/A"
            sev      = "—"
            verdict  = "NO RESULT"

        short_spec = pr.spec.replace("probes.", "")[:50]
        print(f"  {short_spec:<52}  {status:<10}  {pass_pct:>6}  {sev:>4}  {verdict}")
        if pr.error:
            print(f"    ↳ error: {pr.error[:80]}")

    section("FINDINGS DETAIL")
    print(f"\n  Total findings: {len(result.findings)}")
    vulnerable = [f for f in result.findings if f.failed > 0]
    resilient  = [f for f in result.findings if f.failed == 0]
    print(f"  Vulnerable:  {len(vulnerable)}")
    print(f"  Resilient:   {len(resilient)}")

    if vulnerable:
        print(f"\n  --- VULNERABLE FINDINGS (ranked by severity) ---")
        for f in sorted(vulnerable, key=lambda x: (-x.severity, x.pass_rate)):
            attack = 1.0 - f.pass_rate
            print(f"\n  [{f.severity}/5] {f.probe}")
            print(f"    category    : {f.category}")
            print(f"    detector    : {f.detector}")
            print(f"    passed/total: {f.passed}/{f.total}")
            print(f"    attack_rate : {attack:.1%}  (breached {f.failed} prompts)")
            print(f"    confidence  : {f.confidence:.2f}")

    if resilient:
        print(f"\n  --- RESILIENT FINDINGS ---")
        for f in resilient:
            print(f"  {f.probe[:60]:<60}  100% safe  sev={f.severity}/5")

    section("SEVERITY HEATMAP")
    sev_map: dict[str, dict[int, int]] = {}
    for f in result.findings:
        cat = f.category
        sev = f.severity
        sev_map.setdefault(cat, {})
        sev_map[cat][sev] = sev_map[cat].get(sev, 0) + 1

    print(f"\n  {'Category':<25}  {'sev1':>5}  {'sev2':>5}  {'sev3':>5}  {'sev4':>5}  {'sev5':>5}  {'max_sev':>7}")
    print(f"  {SEP2}")
    for cat, sevs in sev_map.items():
        row = [sevs.get(i, 0) for i in range(1, 6)]
        max_sev = max(sevs.keys()) if sevs else 0
        row_str = "  ".join(f"{v:>5}" for v in row)
        print(f"  {cat:<25}  {row_str}  {max_sev:>7}")

    section("T3 COMPLETE")
    print(f"  Target:    {TARGET_URL}")
    print(f"  Duration:  {total_dur:.1f}s")
    print(f"  Probes:    {total_probes} run  ({ok_probes} ok, {failed_probes} failed)")
    print(f"  Findings:  {len(result.findings)}  ({len(vulnerable)} vulnerable, {len(resilient)} resilient)")

    if vulnerable:
        worst = max(vulnerable, key=lambda f: (f.severity, 1.0 - f.pass_rate))
        print(f"\n  HIGHEST RISK: {worst.probe}")
        print(f"    severity={worst.severity}/5  attack_rate={1.0-worst.pass_rate:.1%}  confidence={worst.confidence:.2f}")
        print(f"\n  smollm2-135m VERDICT: HIGH RISK — real prompt injection vulnerability confirmed.")
    else:
        print(f"\n  smollm2-135m VERDICT: RESILIENT — no vulnerabilities detected across {probe_count} probes.")


if __name__ == "__main__":
    main()
