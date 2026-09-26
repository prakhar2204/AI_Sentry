"""
AI-SENTRY -- Report Service
services/report_service.py

In-memory report store that bridges the backend engine with the
Electron/React UI. The UI calls these functions via IPC to retrieve
scan reports without re-running the pipeline.

Design:
  - Reports are stored in-memory (dict keyed by scan_id)
  - The CLI pipeline stores reports here after generation
  - The Electron main process calls get_latest_report() / get_report_by_id()
  - All returns are plain dicts (JSON-serializable, no custom objects)

When the Electron app is built (Phase 8), this service will be
exposed via IPC handlers. For now it is used by the CLI pipeline.

Phase 6a deliverable.
"""

from __future__ import annotations

from typing import Any, Optional

from core.report_generator import ScanReport


# ─────────────────────────────────────────────
#  In-memory store
# ─────────────────────────────────────────────

_report_store: dict[str, ScanReport] = {}
_latest_id: Optional[str] = None


# ─────────────────────────────────────────────
#  Store operations
# ─────────────────────────────────────────────

def store_report(report: ScanReport) -> str:
    """
    Store a report and mark it as the latest.

    Parameters:
        report -- A ScanReport from generate_full_report()

    Returns:
        The scan_id of the stored report.
    """
    global _latest_id
    scan_id = report.meta["scan_id"]
    _report_store[scan_id] = report
    _latest_id = scan_id
    return scan_id


def get_report_by_id(scan_id: str) -> Optional[dict[str, Any]]:
    """
    Retrieve a report by its scan_id.

    Parameters:
        scan_id -- The manifest_id / scan_id

    Returns:
        Report dict (JSON-ready) or None if not found.
    """
    report = _report_store.get(scan_id)
    if report is None:
        return None
    return report.to_dict()


def get_latest_report() -> Optional[dict[str, Any]]:
    """
    Retrieve the most recently stored report.

    Returns:
        Report dict (JSON-ready) or None if no reports exist.
    """
    if _latest_id is None:
        return None
    return get_report_by_id(_latest_id)


def get_latest_report_object() -> Optional[ScanReport]:
    """
    Retrieve the most recently stored ScanReport object.

    Used internally by the CLI for display/export.
    The Electron UI should use get_latest_report() instead.
    """
    if _latest_id is None:
        return None
    return _report_store.get(_latest_id)


def list_report_ids() -> list[str]:
    """
    List all stored scan IDs (oldest first).

    Returns:
        List of scan_id strings.
    """
    return list(_report_store.keys())


def get_report_count() -> int:
    """Return the number of stored reports."""
    return len(_report_store)


def clear_reports() -> int:
    """
    Clear all stored reports. Used for testing.

    Returns:
        Number of reports that were cleared.
    """
    global _latest_id
    count = len(_report_store)
    _report_store.clear()
    _latest_id = None
    return count
