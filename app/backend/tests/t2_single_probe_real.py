"""
AI-SENTRY T2 — Single Probe, Real Target (http://127.0.0.1:8080/v1/chat/completions)
======================================================================================
Probe: probes.promptinject.HijackHateHumans  (capped to 10 prompts via prompt_cap=10)

Confirmed working: 10 prompts * ~2.6s/prompt = ~26s  ✅
60% attack success rate on smollm2-135m verified in direct garak run.

Exercises the full fixed GarakEngine stack:
  _write_rest_config → req_template_json_object + request_timeout + soft_probe_prompt_cap
  _run_probe         → subprocess + rc=1 treated as success (vulnerabilities found)
  _parse_report      → VulnerabilityFinding objects with severity + confidence

Run from backend dir:
    python tests/t2_single_probe_real.py
"""

import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.garak_engine import GarakEngine

TARGET_URL   = "http://127.0.0.1:8080/v1/chat/completions"
TARGET_MODEL = "smollm2-135m"
PROBE_SPEC   = "probes.promptinject.HijackHateHumans"
CATEGORY     = "prompt_injection"
OUT_DIR      = Path(__file__).parent / "garak_t2_output"

SEP = "=" * 78


def section(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("AI-SENTRY T2 — Single Probe Real-Target Test  (FINAL)")
    print(f"  Target:       {TARGET_URL}")
    print(f"  Model:        {TARGET_MODEL}")
    print(f"  Probe:        {PROBE_SPEC}")
    print(f"  Prompt cap:   10 (via run.soft_probe_prompt_cap)")
    print(f"  Req timeout:  60s per HTTP request")
    print(f"  Sub timeout:  120s subprocess")
    print(f"  OutDir:       {OUT_DIR}")

    engine = GarakEngine(
        target_url=TARGET_URL,
        output_dir=str(OUT_DIR),
        model_name=TARGET_MODEL,
        request_timeout=60,
        timeout=120,
        prompt_cap=10,
        depth="quick",
    )

    # ── STEP 1: Show generated config ─────────────────────────────────────────
    section("STEP 1: GarakEngine Config YAML (all fixes applied)")
    tmp_id  = uuid.uuid4().hex[:8]
    tmp_cfg = engine._write_rest_config(tmp_id)
    print(f"  Config path: {tmp_cfg}\n")
    for ln in tmp_cfg.read_text(encoding="utf-8").splitlines():
        print(f"    {ln}")
    tmp_cfg.unlink(missing_ok=True)
    print("\n  Key fixes vs. original:")
    print("    req_template_json_object → proper OpenAI messages body (not raw string)")
    print("    request_timeout: 60      → was 20s garak default (caused ReadTimeout)")
    print("    soft_probe_prompt_cap: 10→ was 256 (caused 820s timeout on smollm2)")
    print("    rc=1 = success           → was treated as error (FAIL=vulnerabilities found)")

    # ── STEP 2: Run probe ─────────────────────────────────────────────────────
    section("STEP 2: Running GarakEngine._run_probe()")
    real_run_id = str(uuid.uuid4())
    real_cfg    = engine._write_rest_config(real_run_id)
    print(f"  run_id: {real_run_id}")
    print(f"  Running {PROBE_SPEC} (10 prompts, timeout=120s)...\n")

    t0 = time.monotonic()
    pr = engine._run_probe(PROBE_SPEC, CATEGORY, real_cfg, real_run_id)
    dur = time.monotonic() - t0
    real_cfg.unlink(missing_ok=True)

    print(f"  Finished in {dur:.1f}s")
    print(f"  returncode:  {pr.returncode}  (0=all pass, 1=failures found — both SUCCESS)")
    print(f"  success:     {pr.success}")
    print(f"  error:       {pr.error or '(none)'}")
    print(f"  report:      {pr.report_path}")
    print(f"  findings:    {len(pr.findings)}")

    if not pr.report_path or not pr.report_path.exists():
        print("\n  ERROR: No report JSONL — garak may have crashed.")
        return

    # ── STEP 3: Raw JSONL breakdown ───────────────────────────────────────────
    section("STEP 3: Raw JSONL Record Breakdown")
    records: list[dict] = []
    with open(pr.report_path, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            ln = ln.strip()
            if ln:
                try:
                    records.append(json.loads(ln))
                except json.JSONDecodeError:
                    pass

    counts: dict[str, int] = {}
    for r in records:
        et = r.get("entry_type", "UNKNOWN")
        counts[et] = counts.get(et, 0) + 1

    size_kb = pr.report_path.stat().st_size / 1024
    print(f"\n  File:    {pr.report_path.name} ({size_kb:.1f} KB)")
    print(f"  Records: {len(records)}")
    print("  Breakdown:")
    for et, cnt in counts.items():
        print(f"    {et:<30} x {cnt}")

    eval_recs    = [r for r in records if r.get("entry_type") == "eval"]
    attempt_recs = [r for r in records if r.get("entry_type") == "attempt"]
    print(f"\n  eval records (scored results):  {len(eval_recs)}")
    print(f"  attempt records (interactions): {len(attempt_recs)}")

    # ALL eval records
    print(f"\n  --- ALL EVAL RECORDS ---")
    for i, ev in enumerate(eval_recs):
        print(f"\n  eval[{i}]:")
        for k, v in ev.items():
            if k == "entry_type":
                continue
            vs = json.dumps(v, ensure_ascii=False)
            if len(vs) > 120:
                vs = vs[:120] + "..."
            print(f"    {k:<24}: {vs}")

    # Vulnerable attempts first
    failing = [
        a for a in attempt_recs
        if any(any(s > 0 for s in sc) for sc in a.get("detector_results", {}).values())
    ]
    passing = [a for a in attempt_recs if a not in failing]
    samples = (failing[:3] + passing[:2])[:5]

    print(f"\n  --- SAMPLE ATTEMPTS (VULNERABLE first, max 5) ---")
    print(f"  Vulnerable: {len(failing)}  |  Safe: {len(passing)}")
    for i, att in enumerate(samples):
        prompt_txt = att.get("prompt", {}).get("turns", [{}])[0].get("content", {}).get("text", "")
        outs       = att.get("outputs", [])
        resp_txt   = outs[0].get("text", "") if outs else ""
        det        = att.get("detector_results", {})
        tag        = " *** VULNERABLE ***" if att in failing else " (safe)"

        print(f"\n  attempt[{i}] seq={att.get('seq')} status={att.get('status')}{tag}")
        print(f"    PROMPT  : {prompt_txt.replace(chr(10), ' ')[:110]}...")
        print(f"    RESPONSE: {resp_txt.replace(chr(10), ' ')[:110]}")
        print(f"    DETECTOR: {det}")

    # ── STEP 4: VulnerabilityFinding objects ──────────────────────────────────
    section("STEP 4: VulnerabilityFinding Objects")
    findings = pr.findings
    print(f"\n  Count: {len(findings)}")
    for i, f in enumerate(findings):
        attack_rate = 1.0 - f.pass_rate
        verdict     = "VULNERABLE" if f.failed > 0 else "RESILIENT"
        print(f"\n  Finding #{i+1}  [{verdict}]")
        print(f"    finding_id  : {f.finding_id}")
        print(f"    engine      : {f.engine}")
        print(f"    category    : {f.category}")
        print(f"    probe       : {f.probe}")
        print(f"    detector    : {f.detector}")
        print(f"    passed      : {f.passed}")
        print(f"    failed      : {f.failed}")
        print(f"    total       : {f.total}")
        print(f"    pass_rate   : {f.pass_rate:.4f}  ({f.pass_rate * 100:.1f}% safe)")
        print(f"    attack_rate : {attack_rate:.4f}  ({attack_rate * 100:.1f}% breached)")
        print(f"    severity    : {f.severity}/5")
        print(f"    confidence  : {f.confidence:.2f}")

    # ── STEP 5: Side-by-side ─────────────────────────────────────────────────
    section("STEP 5: SIDE-BY-SIDE — Raw eval JSONL vs VulnerabilityFinding")
    if eval_recs and findings:
        ev = eval_recs[0]
        fi = findings[0]
        print(f"\n  {'Field':<24}  {'eval JSONL (raw)':<32}  VulnerabilityFinding")
        print(f"  {'─'*76}")
        rows = [
            ("probe",           ev.get("probe", ""),                   fi.probe[:32]),
            ("detector",        ev.get("detector", ""),                fi.detector[:32]),
            ("passed",          ev.get("passed", ""),                  fi.passed),
            ("fails/failed",    ev.get("fails", ""),                   fi.failed),
            ("total_evaluated", ev.get("total_evaluated", ""),         fi.total),
            ("pass_rate",
                f"{ev.get('passed',0)}/{ev.get('total_evaluated',1)}",
                f"{fi.pass_rate:.4f}"),
            ("severity",        "— derived by AI-SENTRY",             f"{fi.severity}/5"),
            ("confidence",      "— derived by AI-SENTRY",             f"{fi.confidence:.2f}"),
        ]
        for label, rv, ov in rows:
            print(f"  {label:<24}  {str(rv)[:32]:<32}  {ov}")
    elif not eval_recs:
        print("\n  No eval records in report (garak killed before detection phase).")
    else:
        print("\n  No findings — model was fully resilient to this probe.")

    # ── COMPLETE ──────────────────────────────────────────────────────────────
    section("T2 COMPLETE")
    print(f"  Probe:       {PROBE_SPEC}")
    print(f"  Target:      {TARGET_URL}")
    print(f"  Duration:    {dur:.1f}s")
    print(f"  Report:      {pr.report_path}")
    print(f"  Findings:    {len(findings)}")
    if findings:
        f0 = findings[0]
        verdict = "VULNERABLE" if f0.failed > 0 else "RESILIENT"
        attack  = 1.0 - f0.pass_rate
        print(f"  Outcome:     {verdict}")
        print(f"  pass_rate:   {f0.pass_rate:.1%}  ({f0.failed}/{f0.total} prompts breached model)")
        print(f"  attack_rate: {attack:.1%}")
        print(f"  severity:    {f0.severity}/5")
        print(f"  confidence:  {f0.confidence:.2f}")
    else:
        print("  Outcome:     (no eval records — check error above)")


if __name__ == "__main__":
    main()
