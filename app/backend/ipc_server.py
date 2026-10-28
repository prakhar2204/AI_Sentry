"""
Sentryɸ — Python IPC Server
app/backend/ipc_server.py

Bridges the Electron main process and the Python scan pipeline using
a JSON Lines streaming protocol over stdin/stdout.

Protocol:
  IN  (stdin):  One JSON object (the scan configuration), terminated by newline.
  OUT (stdout): One JSON object per line — progress events streamed in real time.

This module is invoked by Electron as:
  python -m ipc_server

It reads the scan config from stdin, runs the full pipeline using the
existing core modules, and streams events to stdout as they occur.

Event shapes:
  progress  → { "type": "progress", "stage", "percent", "probes_done",
                "probes_total", "elapsed_ms", "message" }
  finding   → { "type": "finding", "category", "severity", "confidence",
                "title", "evidence", "probe_id" }
  activity  → { "type": "activity", "severity", "message", "timestamp" }
  stage     → { "type": "stage", "stage", "message" }
  complete  → { "type": "complete", "report": { ...full ScanReport dict... } }
  error     → { "type": "error", "message", "code" }

Design rules:
  - stdout.flush() after EVERY JSON line (critical for real-time streaming)
  - Only JSON goes to stdout. Logging goes to stderr.
  - Exit code 0 on success, 1 on error.
  - KeyboardInterrupt / SIGTERM = graceful exit (Electron sends these on cancel)
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from datetime import datetime, timezone


# ─────────────────────────────────────────────
#  Emission helpers
# ─────────────────────────────────────────────

def _emit(event: dict) -> None:
    """Write a single JSON event to stdout and flush immediately."""
    try:
        print(json.dumps(event), flush=True)
    except BrokenPipeError:
        # Electron closed the pipe (e.g. window closed mid-scan)
        sys.exit(0)


def _emit_activity(message: str, severity: str = "info") -> None:
    _emit({
        "type": "activity",
        "severity": severity,
        "message": message,
        "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
    })


def _emit_stage(stage: str, message: str) -> None:
    _emit({"type": "stage", "stage": stage, "message": message})


def _emit_progress(
    stage: str,
    percent: int,
    probes_done: int,
    probes_total: int,
    elapsed_ms: int,
    message: str,
) -> None:
    _emit({
        "type": "progress",
        "stage": stage,
        "percent": percent,
        "probes_done": probes_done,
        "probes_total": probes_total,
        "elapsed_ms": elapsed_ms,
        "message": message,
    })


def _emit_finding(
    category: str,
    severity: str,
    confidence: float,
    evidence: str,
    probe_id: str = "",
) -> None:
    # Derive a short human-readable title from the category + probe_id
    title_map = {
        "prompt_injection": "Prompt Injection",
        "jailbreak":        "Jailbreak Resistance",
        "data_leak":        "Data Leakage",
        "harmful_output":   "Harmful Output",
    }
    category_title = title_map.get(category, category.replace("_", " ").title())
    title = f"{category_title} ({probe_id})" if probe_id else category_title

    _emit({
        "type":       "finding",
        "category":   category,
        "severity":   severity,
        "confidence": confidence,
        "title":      title,
        "evidence":   evidence,
        "probe_id":   probe_id,
    })


def _emit_error(message: str, code: str = "SCAN_ERROR") -> None:
    _emit({"type": "error", "message": message, "code": code})


# ─────────────────────────────────────────────
#  Config parsing
# ─────────────────────────────────────────────

def _parse_config(raw: dict) -> dict:
    """
    Normalize the frontend config dict into parameters for create_manifest().

    Frontend sends:
      {
        "target":     "http://localhost:8080/v1/chat/completions",
        "mode":       "api" | "local",
        "scan_depth": "quick" | "standard" | "deep",
        "categories": ["prompt_injection", "jailbreak", ...],
        "api_key":    "sk-...",
        "model_name": "gpt-4",           # optional
        "notes":      "...",             # optional
      }
    """
    target = raw.get("target", "").strip()
    if not target:
        raise ValueError("'target' is required in scan config")

    mode       = raw.get("mode", "api")
    scan_depth = raw.get("scan_depth", "standard")
    categories = raw.get("categories") or None  # None → use depth defaults
    api_key    = raw.get("api_key", "")
    notes      = raw.get("notes", "")

    return {
        "target":     target,
        "mode":       mode,
        "scan_depth": scan_depth,
        "categories": categories,
        "api_key":    api_key,
        "notes":      notes,
    }


# ─────────────────────────────────────────────
#  Simulated probe runner (wraps MockEngine with streaming)
# ─────────────────────────────────────────────

def _run_scan_with_streaming(manifest) -> list:
    """
    Run the MockEngine category-by-category, emitting finding and progress
    events in real time so the frontend sees incremental updates.

    Returns: list of ScanFinding objects (same as MockEngine.run_scan().findings)
    """
    from core.mock_engine import MockEngine, _FINDING_TEMPLATES

    engine = MockEngine()
    all_findings = []
    start_ms = int(time.time() * 1000)

    # Calculate total probes upfront for progress %
    total_probes = sum(
        len(_FINDING_TEMPLATES.get(cat.value, []))
        for cat in manifest.categories
    )
    if total_probes == 0:
        total_probes = 1  # avoid division by zero

    probes_done = 0

    for cat in manifest.categories:
        cat_name   = cat.value
        templates  = _FINDING_TEMPLATES.get(cat_name, [])
        cat_label  = cat_name.replace("_", " ").title()

        _emit_stage("scanning", f"Starting {cat_label} probes...")
        _emit_activity(f"Initializing {cat_label} probe suite ({len(templates)} probes)", "info")

        for i, tmpl in enumerate(templates):
            # Brief pause to make streaming visible (mock only — no real I/O)
            time.sleep(0.3)

            probes_done += 1
            elapsed_ms = int(time.time() * 1000) - start_ms
            pct = int((probes_done / total_probes) * 90)  # reserve last 10% for post-processing

            finding_sev = tmpl["severity"].upper()
            _emit_activity(
                f"[{cat_label}] Probe {tmpl['probe_id']} → {finding_sev} ({tmpl['confidence']:.0%} confidence)",
                "warning" if tmpl["severity"] == "high" else "info",
            )

            _emit_progress(
                stage       = "scanning",
                percent     = pct,
                probes_done = probes_done,
                probes_total= total_probes,
                elapsed_ms  = elapsed_ms,
                message     = f"Running {cat_label} · probe {i + 1}/{len(templates)}",
            )

            # Emit the finding
            _emit_finding(
                category  = cat_name,
                severity  = tmpl["severity"],
                confidence= tmpl["confidence"],
                evidence  = tmpl["evidence"],
                probe_id  = tmpl.get("probe_id", ""),
            )

            # Collect for the final result
            from core.engine_interface import ScanFinding
            all_findings.append(ScanFinding(
                category   = cat_name,
                severity   = tmpl["severity"],
                confidence = tmpl["confidence"],
                evidence   = tmpl["evidence"],
                source     = engine.name,
                probe_id   = tmpl.get("probe_id", ""),
            ))

        _emit_activity(f"{cat_label} complete — {len(templates)} probe(s) run", "info")

    return all_findings


# ─────────────────────────────────────────────
#  Main scan pipeline
# ─────────────────────────────────────────────

def run_scan_pipeline(config: dict) -> None:
    """
    Full scan pipeline with streaming progress events:
      1. Parse + validate config  →  emit: stage "init"
      2. Build ScanManifest       →  emit: activity
      3. Run scan (per-probe)     →  emit: progress + finding + activity
      4. Score findings           →  emit: stage "scoring", progress 92%
      5. Generate recommendations →  emit: stage "recommendations", progress 96%
      6. Assemble report          →  emit: progress 100%, complete
    """
    t_start = time.time()

    # ── 1. Initialise ──────────────────────────────────────────────────────
    _emit_stage("init", "Initialising scan pipeline...")
    _emit_activity("Sentryɸ IPC Server started", "info")
    _emit_progress("init", 2, 0, 0, 0, "Parsing scan configuration...")

    params = _parse_config(config)
    _emit_activity(
        f"Target: {params['target']} · mode={params['mode']} · depth={params['scan_depth']}",
        "info",
    )

    # ── 2. Build manifest ──────────────────────────────────────────────────
    _emit_stage("manifest", "Building scan manifest...")
    _emit_progress("manifest", 5, 0, 0, 0, "Building scan manifest...")

    from core.manifest import create_manifest
    manifest = create_manifest(**params)

    cat_names = ", ".join(c.value for c in manifest.categories)
    _emit_activity(f"Manifest created — ID: {manifest.manifest_id[:8]}... · categories: {cat_names}", "info")
    _emit_progress("manifest", 8, 0, 0, 0, f"Manifest ready · {len(manifest.categories)} category(s) selected")

    # ── 3. Run scan (streaming) ────────────────────────────────────────────
    _emit_stage("scanning", "Starting scan engine...")
    _emit_activity("Launching MockEngine (real engines: Phase P4/P5)", "info")

    findings = _run_scan_with_streaming(manifest)

    elapsed_ms = int((time.time() - t_start) * 1000)
    _emit_progress("scanning", 90, len(findings), len(findings), elapsed_ms,
                   f"Scan complete — {len(findings)} finding(s) detected")
    _emit_activity(f"Engine finished: {len(findings)} total finding(s)", "info")

    # ── 4. Score findings ──────────────────────────────────────────────────
    _emit_stage("scoring", "Running severity classifier and risk scorer...")
    _emit_progress("scoring", 92, len(findings), len(findings), elapsed_ms, "Scoring findings...")

    from core.engine_interface import ScanResult
    from core.scorer import score_scan_result

    scan_result = ScanResult(
        findings     = findings,
        engine_name  = "mock",
        manifest_id  = manifest.manifest_id,
        total_probes = len(findings),
        duration_sec = time.time() - t_start,
        error        = None,
    )

    risk_report = score_scan_result(scan_result)
    _emit_activity(
        f"Risk score: {risk_report.risk_score}/100 ({risk_report.risk_level.upper()})",
        "warning" if risk_report.risk_level == "high" else "info",
    )

    # ── 5. Generate recommendations ────────────────────────────────────────
    _emit_stage("recommendations", "Generating remediation recommendations...")
    _emit_progress("recommendations", 95, len(findings), len(findings), elapsed_ms,
                   "Generating recommendations...")

    from core.recommender import generate_recommendations
    rec_report = generate_recommendations(risk_report)
    _emit_activity(f"Generated {len(rec_report.recommendations)} recommendation(s)", "info")

    # ── 6. Assemble report and emit complete ───────────────────────────────
    _emit_stage("complete", "Assembling final report...")
    _emit_progress("complete", 98, len(findings), len(findings), elapsed_ms, "Assembling report...")

    from core.report_generator import generate_full_report
    report = generate_full_report(manifest, scan_result, risk_report, rec_report)

    elapsed_ms = int((time.time() - t_start) * 1000)
    _emit_progress("complete", 100, len(findings), len(findings), elapsed_ms, "Scan complete")
    _emit_activity(
        f"Report ready — {len(findings)} finding(s) · risk score {risk_report.risk_score}/100 · {elapsed_ms}ms total",
        "info",
    )

    # ── Complete event: full report sent to frontend ───────────────────────
    _emit({"type": "complete", "report": report.to_dict()})


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────

def main() -> None:
    """
    IPC entry point. Reads one JSON config from stdin, runs the scan,
    streams events to stdout.
    """
    # Read config from stdin (Electron writes it then closes stdin).
    # Reconfigure stdin to handle UTF-8 BOM from some Windows environments.
    try:
        import io
        raw_bytes = sys.stdin.buffer.read()
        raw_input = raw_bytes.decode("utf-8-sig").strip()

        if not raw_input:
            _emit_error("No configuration received from Electron", "NO_CONFIG")
            sys.exit(1)

        config = json.loads(raw_input)
        _emit_activity(f"Config received: {len(raw_input)} bytes", "info")

    except json.JSONDecodeError as exc:
        _emit_error(f"Invalid JSON config: {exc}", "INVALID_CONFIG")
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as exc:
        _emit_error(f"Failed to read config: {exc}", "CONFIG_READ_ERROR")
        sys.exit(1)

    # Run scan pipeline
    try:
        run_scan_pipeline(config)
        sys.exit(0)

    except KeyboardInterrupt:
        # Electron sent SIGINT (cancel button pressed)
        _emit_activity("Scan cancelled by user", "warning")
        _emit_error("Scan cancelled", "CANCELLED")
        sys.exit(0)

    except ValueError as exc:
        _emit_error(f"Configuration error: {exc}", "CONFIG_ERROR")
        sys.exit(1)

    except Exception as exc:
        tb = traceback.format_exc()
        print(tb, file=sys.stderr, flush=True)
        _emit_error(f"Unexpected error: {exc}", "ENGINE_FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
