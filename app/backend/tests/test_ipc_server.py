"""
Sentryɸ — IPC Server Tests
tests/test_ipc_server.py

Validates the JSON Lines output format of ipc_server.py by running it
as a subprocess with a test config and asserting event shapes.

All tests pass when:
  - Each output line is valid JSON
  - Required event types appear in the correct order
  - The complete event contains a well-formed ScanReport dict
  - Error events have required fields
  - The process exits with code 0

Phase P2b/P2c deliverable.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

BACKEND_DIR = Path(__file__).parent.parent
PYTHON_EXE = sys.executable

QUICK_CONFIG = json.dumps({
    "target":     "http://localhost:8080",
    "mode":       "api",
    "scan_depth": "quick",
    "categories": ["prompt_injection", "jailbreak"],
})

STANDARD_CONFIG = json.dumps({
    "target":     "http://localhost:9000",
    "mode":       "local",
    "scan_depth": "standard",
    "categories": ["prompt_injection", "jailbreak", "data_leak", "harmful_output"],
})


def run_ipc_server(config_json: str, timeout: int = 30) -> tuple[list[dict], int]:
    """
    Run ipc_server as subprocess, pipe config_json to stdin.
    Returns (events, exit_code).

    events: list of parsed JSON dicts from stdout (one per line).
    exit_code: process exit code.
    """
    proc = subprocess.run(
        [PYTHON_EXE, "-m", "ipc_server"],
        input=config_json.encode("utf-8"),
        capture_output=True,
        timeout=timeout,
        cwd=str(BACKEND_DIR),
    )

    events: list[dict] = []
    for line in proc.stdout.decode("utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        events.append(json.loads(line))

    return events, proc.returncode


# ─────────────────────────────────────────────
#  Tests: process exits correctly
# ─────────────────────────────────────────────

def test_exit_code_success():
    """Process exits 0 on a successful quick scan."""
    _, code = run_ipc_server(QUICK_CONFIG)
    assert code == 0, f"Expected exit 0, got {code}"


def test_exit_code_invalid_json():
    """Process exits 1 on invalid JSON input."""
    _, code = run_ipc_server("{NOT JSON}")
    assert code == 1, f"Expected exit 1, got {code}"


def test_exit_code_missing_target():
    """Process exits 1 when 'target' is missing from config."""
    bad_config = json.dumps({"mode": "api", "scan_depth": "quick"})
    _, code = run_ipc_server(bad_config)
    assert code == 1, f"Expected exit 1, got {code}"


# ─────────────────────────────────────────────
#  Tests: all lines are valid JSON
# ─────────────────────────────────────────────

def test_all_lines_valid_json():
    """Every stdout line must be parseable JSON."""
    events, _ = run_ipc_server(QUICK_CONFIG)
    assert len(events) > 0, "Expected at least one JSON event"
    # If we got here without json.JSONDecodeError, all lines are valid.


# ─────────────────────────────────────────────
#  Tests: required event types present
# ─────────────────────────────────────────────

def _event_types(events: list[dict]) -> list[str]:
    return [e.get("type", "") for e in events]


def test_has_stage_events():
    """At least one 'stage' event must be emitted."""
    events, _ = run_ipc_server(QUICK_CONFIG)
    types = _event_types(events)
    assert "stage" in types, f"Missing 'stage' event. Got types: {set(types)}"


def test_has_progress_events():
    """At least one 'progress' event must be emitted."""
    events, _ = run_ipc_server(QUICK_CONFIG)
    types = _event_types(events)
    assert "progress" in types, f"Missing 'progress' event. Got types: {set(types)}"


def test_has_finding_events():
    """At least one 'finding' event must be emitted for prompt_injection category."""
    events, _ = run_ipc_server(QUICK_CONFIG)
    types = _event_types(events)
    assert "finding" in types, f"Missing 'finding' event. Got types: {set(types)}"


def test_has_activity_events():
    """At least one 'activity' event must be emitted."""
    events, _ = run_ipc_server(QUICK_CONFIG)
    types = _event_types(events)
    assert "activity" in types, f"Missing 'activity' event. Got types: {set(types)}"


def test_last_event_is_complete():
    """The very last event must be 'complete'."""
    events, _ = run_ipc_server(QUICK_CONFIG)
    assert events, "Expected events"
    last_type = events[-1].get("type")
    assert last_type == "complete", f"Last event type should be 'complete', got '{last_type}'"


# ─────────────────────────────────────────────
#  Tests: event field shapes
# ─────────────────────────────────────────────

def test_progress_event_fields():
    """progress events have required numeric/string fields."""
    events, _ = run_ipc_server(QUICK_CONFIG)
    progress_events = [e for e in events if e.get("type") == "progress"]
    assert progress_events, "No progress events found"

    for evt in progress_events:
        assert isinstance(evt.get("percent"), int), f"percent must be int: {evt}"
        assert isinstance(evt.get("probes_done"), int), f"probes_done must be int: {evt}"
        assert isinstance(evt.get("probes_total"), int), f"probes_total must be int: {evt}"
        assert isinstance(evt.get("elapsed_ms"), int), f"elapsed_ms must be int: {evt}"
        assert isinstance(evt.get("message"), str), f"message must be str: {evt}"
        assert isinstance(evt.get("stage"), str), f"stage must be str: {evt}"


def test_progress_percent_range():
    """All progress.percent values must be in 0-100."""
    events, _ = run_ipc_server(QUICK_CONFIG)
    for evt in events:
        if evt.get("type") == "progress":
            pct = evt["percent"]
            assert 0 <= pct <= 100, f"percent out of range: {pct}"


def test_finding_event_fields():
    """finding events have severity, confidence, category, evidence."""
    events, _ = run_ipc_server(QUICK_CONFIG)
    finding_events = [e for e in events if e.get("type") == "finding"]
    assert finding_events, "No finding events found"

    for evt in finding_events:
        assert evt.get("severity") in ("high", "medium", "low"), f"Bad severity: {evt}"
        conf = evt.get("confidence")
        assert isinstance(conf, (int, float)), f"confidence must be numeric: {evt}"
        assert 0.0 <= conf <= 1.0, f"confidence out of range: {conf}"
        assert isinstance(evt.get("category"), str), f"category must be str: {evt}"
        assert isinstance(evt.get("evidence"), str), f"evidence must be str: {evt}"


def test_activity_event_fields():
    """activity events have timestamp, severity, message."""
    events, _ = run_ipc_server(QUICK_CONFIG)
    activity_events = [e for e in events if e.get("type") == "activity"]
    assert activity_events, "No activity events found"

    for evt in activity_events:
        assert isinstance(evt.get("timestamp"), str), f"timestamp must be str: {evt}"
        assert evt.get("severity") in ("info", "warning", "error", "debug"), (
            f"Bad severity: {evt}"
        )
        assert isinstance(evt.get("message"), str), f"message must be str: {evt}"


def test_stage_event_fields():
    """stage events have 'stage' and 'message' string fields."""
    events, _ = run_ipc_server(QUICK_CONFIG)
    stage_events = [e for e in events if e.get("type") == "stage"]
    for evt in stage_events:
        assert isinstance(evt.get("stage"), str), f"stage.stage must be str: {evt}"
        assert isinstance(evt.get("message"), str), f"stage.message must be str: {evt}"


# ─────────────────────────────────────────────
#  Tests: complete event report structure
# ─────────────────────────────────────────────

def test_complete_event_has_report():
    """complete event must contain a 'report' dict."""
    events, _ = run_ipc_server(QUICK_CONFIG)
    complete = next((e for e in events if e.get("type") == "complete"), None)
    assert complete is not None, "No 'complete' event found"
    assert isinstance(complete.get("report"), dict), "complete.report must be a dict"


def test_complete_report_has_required_sections():
    """Report dict must have all top-level sections."""
    events, _ = run_ipc_server(QUICK_CONFIG)
    complete = next(e for e in events if e.get("type") == "complete")
    report = complete["report"]

    required = {"report_version", "meta", "summary", "breakdown",
                "categories", "findings", "recommendations", "engine"}
    missing = required - set(report.keys())
    assert not missing, f"Report missing sections: {missing}"


def test_complete_report_summary_fields():
    """summary section has risk_score (int), risk_level (str), total_findings (int)."""
    events, _ = run_ipc_server(QUICK_CONFIG)
    complete = next(e for e in events if e.get("type") == "complete")
    summary = complete["report"]["summary"]

    assert isinstance(summary.get("risk_score"), int), f"risk_score must be int: {summary}"
    assert 0 <= summary["risk_score"] <= 100, f"risk_score out of range: {summary}"
    assert isinstance(summary.get("risk_level"), str), f"risk_level must be str: {summary}"
    assert isinstance(summary.get("total_findings"), int)


def test_complete_report_findings_list():
    """findings must be a list of dicts with required keys."""
    events, _ = run_ipc_server(QUICK_CONFIG)
    complete = next(e for e in events if e.get("type") == "complete")
    findings = complete["report"]["findings"]

    assert isinstance(findings, list), "findings must be a list"
    for f in findings:
        assert "category" in f
        assert "severity" in f
        assert "confidence" in f
        assert "evidence" in f


def test_complete_report_recommendations_list():
    """recommendations must be a list."""
    events, _ = run_ipc_server(QUICK_CONFIG)
    complete = next(e for e in events if e.get("type") == "complete")
    recs = complete["report"]["recommendations"]
    assert isinstance(recs, list), "recommendations must be a list"


def test_report_meta_target_matches_config():
    """report.meta.target must match the config target."""
    events, _ = run_ipc_server(QUICK_CONFIG)
    complete = next(e for e in events if e.get("type") == "complete")
    meta = complete["report"]["meta"]
    assert meta["target"] == "http://localhost:8080", f"Wrong target: {meta}"


# ─────────────────────────────────────────────
#  Tests: error events
# ─────────────────────────────────────────────

def test_error_event_on_bad_config():
    """Error event emitted for missing target with required fields."""
    bad_config = json.dumps({"mode": "api"})
    events, _ = run_ipc_server(bad_config)
    error_events = [e for e in events if e.get("type") == "error"]
    assert error_events, "Expected at least one 'error' event"

    for evt in error_events:
        assert isinstance(evt.get("message"), str), f"error.message must be str: {evt}"
        assert isinstance(evt.get("code"), str), f"error.code must be str: {evt}"


# ─────────────────────────────────────────────
#  Tests: standard depth (all 4 categories)
# ─────────────────────────────────────────────

def test_standard_scan_has_all_categories():
    """Standard scan with 4 categories produces findings for each."""
    events, code = run_ipc_server(STANDARD_CONFIG, timeout=60)
    assert code == 0, f"Standard scan exited with {code}"

    complete = next((e for e in events if e.get("type") == "complete"), None)
    assert complete is not None, "No complete event"

    cats_in_report = set(complete["report"]["categories"].keys())
    expected = {"prompt_injection", "jailbreak", "data_leak", "harmful_output"}
    assert expected == cats_in_report, f"Missing categories: {expected - cats_in_report}"


def test_standard_scan_finding_count():
    """Standard scan (4 cats) should produce exactly 9 findings (mock engine)."""
    events, _ = run_ipc_server(STANDARD_CONFIG, timeout=60)
    complete = next(e for e in events if e.get("type") == "complete")
    total = complete["report"]["summary"]["total_findings"]
    assert total == 9, f"Expected 9 findings from mock engine, got {total}"
