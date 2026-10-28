"""
Sentryɸ — Export Handler
app/backend/export_handler.py

Handles report file export for all formats:
  - JSON : writes the canonical ScanReport.to_dict() structure
  - HTML : standalone self-contained document (inline CSS, all escaped)
  - TXT  : plain-text human-readable report
  - PDF  : HTML → PDF via WeasyPrint (optional; falls back to HTML with notice)

Usage (called from ipc_server.py or directly):

    from export_handler import export_report, ExportResult

    result = export_report(
        report_dict = report.to_dict(),   # ScanReport.to_dict()
        format      = "html",             # "json" | "html" | "txt" | "pdf"
        output_path = "/path/to/file.html"
    )

    if result.success:
        print(f"Saved {result.size_bytes} bytes to {result.path}")
    else:
        print(f"Export failed: {result.error}")

Phase P3 deliverable.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


# ─────────────────────────────────────────────
#  Result type
# ─────────────────────────────────────────────

@dataclass
class ExportResult:
    """Result of an export operation."""
    success:    bool
    path:       str
    size_bytes: int = 0
    error:      str = ""
    fallback:   str = ""   # Non-empty if PDF fell back to another format


# ─────────────────────────────────────────────
#  HTML escaping
# ─────────────────────────────────────────────

_HTML_ESCAPE_TABLE = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
}

def _h(text: str) -> str:
    """Escape a string for safe HTML embedding."""
    return "".join(_HTML_ESCAPE_TABLE.get(c, c) for c in str(text))


# ─────────────────────────────────────────────
#  JSON serializer
# ─────────────────────────────────────────────

def _serialize_json(report: dict) -> str:
    """Serialize report dict to formatted JSON string."""
    return json.dumps(report, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────
#  TXT serializer
# ─────────────────────────────────────────────

_DIVIDER      = "=" * 60
_THIN_DIVIDER = "-" * 60

_SEV_TAGS = {
    "high":   "HIGH  ",
    "medium": "MEDIUM",
    "low":    "LOW   ",
}


def _serialize_txt(report: dict) -> str:
    """Generate a plain-text report matching backend format_txt_report() output."""
    lines = []
    meta    = report.get("meta", {})
    summary = report.get("summary", {})
    breakdown = report.get("breakdown", {})
    categories = report.get("categories", {})
    findings = report.get("findings", [])
    recs     = report.get("recommendations", [])
    engine   = report.get("engine", {})
    is_sim   = str(meta.get("scan_id", "")).startswith("sim-")

    lines += [
        "",
        _DIVIDER,
        "  Sentryɸ -- SECURITY SCAN REPORT",
    ]
    if is_sim:
        lines.append("  *** SIMULATION MODE -- NOT A REAL ASSESSMENT ***")
    lines += [_DIVIDER, ""]

    lines += [
        f"  Target       : {meta.get('target', '')}",
        f"  Mode         : {meta.get('mode', '')}",
        f"  Scan Depth   : {meta.get('scan_depth', '')}",
        f"  Categories   : {', '.join(meta.get('categories', []))}",
        f"  Scan ID      : {meta.get('scan_id', '')}",
        f"  Scan Time    : {meta.get('timestamp', '')}",
        f"  Report Time  : {meta.get('report_generated_at', '')}",
        "",
    ]

    # Risk summary
    lines += [_THIN_DIVIDER, "  RISK SUMMARY", _THIN_DIVIDER, ""]
    lines += [
        f"  Risk Score    : {summary.get('risk_score', 0)}/100  ({summary.get('risk_level', '')})",
        f"  Total Findings: {summary.get('total_findings', 0)}",
        "",
        f"    HIGH       : {breakdown.get('high', 0)}",
        f"    MEDIUM     : {breakdown.get('medium', 0)}",
        f"    LOW        : {breakdown.get('low', 0)}",
        "",
    ]

    # Category breakdown
    if categories:
        lines += [_THIN_DIVIDER, "  CATEGORY BREAKDOWN", _THIN_DIVIDER, ""]
        for name, cat in categories.items():
            lines.append(
                f"    {name:<20}  findings: {cat.get('count', 0)}"
                f"  max: {str(cat.get('max_severity', 'none')):<6}"
                f"  avg_conf: {cat.get('avg_confidence', 0):.2f}"
            )
        lines.append("")

    # Findings
    lines += [_THIN_DIVIDER, "  FINDINGS", _THIN_DIVIDER, ""]
    if not findings:
        lines += ["  No findings -- target passed all probes.", ""]
    else:
        for i, f in enumerate(findings, 1):
            tag = _SEV_TAGS.get(f.get("severity", ""), "?????")
            conf_pct = round(f.get("confidence", 0) * 100)
            lines.append(f"  #{i} [{tag}] {f.get('category', '')}  (confidence: {conf_pct}%)")
            lines.append(f"     {f.get('evidence', '')}")
            parts = []
            if f.get("probe_id"):
                parts.append(f"Probe: {f['probe_id']}")
            parts.append(f"Source: {f.get('source', '')}")
            lines.append(f"     {' | '.join(parts)}")
            lines.append("")

    # Recommendations
    lines += [_THIN_DIVIDER, "  RECOMMENDATIONS", _THIN_DIVIDER, ""]
    if not recs:
        lines += ["  No recommendations -- no vulnerabilities found.", ""]
    else:
        for rec in recs:
            tag = _SEV_TAGS.get(rec.get("severity", ""), "?????")
            lines.append(f"  [{tag}] {rec.get('category', '')}")
            for j, action in enumerate(rec.get("actions", []), 1):
                lines.append(f"    {j}. {action}")
            lines.append("")

    # Engine info
    lines += [_THIN_DIVIDER, "  ENGINE INFO", _THIN_DIVIDER, ""]
    lines += [
        f"  Engine       : {engine.get('name', '')}",
        f"  Probes Run   : {engine.get('total_probes', 0)}",
    ]
    if engine.get("duration_sec", 0) > 0:
        lines.append(f"  Duration     : {engine['duration_sec']:.1f}s")
    if engine.get("error"):
        lines.append(f"  Error        : {engine['error']}")
    lines.append("")

    lines += [
        _DIVIDER,
        "  Report generated by Sentryɸ",
    ]
    if is_sim:
        lines += [
            "  SIMULATION MODE: These results are for demonstration only.",
            "  A real assessment must be run against the actual target.",
        ]
    lines += [_DIVIDER, ""]

    return "\n".join(lines)


# ─────────────────────────────────────────────
#  HTML serializer
# ─────────────────────────────────────────────

_SEV_COLORS = {
    "high":   ("#e05260", "#e0526022"),
    "medium": ("#e8a838", "#e8a83822"),
    "low":    ("#4a9edb", "#4a9edb22"),
}

_RISK_COLORS = {
    "CRITICAL": "#c0392b",
    "HIGH":     "#e05260",
    "MEDIUM":   "#e8a838",
    "LOW":      "#4a9edb",
    "NONE":     "#3dbc6a",
}

_INLINE_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  background: #0d0d14;
  color: #c5c8d6;
  padding: 40px 20px;
  line-height: 1.6;
}
.wrap { max-width: 960px; margin: 0 auto; }
.brand {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 36px;
  padding-bottom: 20px;
  border-bottom: 1px solid #1e2040;
}
.brand-name { font-size: 20px; font-weight: 700; color: #fff; letter-spacing: -0.02em; }
.brand-sub  { font-size: 13px; color: #555; }
.sim-banner {
  background: #e8a83818; border: 1px solid #e8a83840;
  color: #e8a838; padding: 10px 16px; border-radius: 8px;
  margin-bottom: 24px; font-size: 13px; font-weight: 600;
}
h2 {
  font-size: 16px; font-weight: 700; color: #fff;
  margin: 32px 0 12px; padding-bottom: 8px;
  border-bottom: 1px solid #1e2040;
  letter-spacing: 0.02em; text-transform: uppercase;
}
.score-card {
  display: flex; align-items: center; gap: 24px;
  background: #13131f; border: 1px solid #1e2040;
  border-radius: 12px; padding: 24px 28px;
  margin-bottom: 24px;
}
.score-num  { font-size: 52px; font-weight: 800; line-height: 1; }
.score-denom { font-size: 20px; color: #555; font-weight: 400; }
.score-level { font-size: 18px; font-weight: 700; margin-top: 4px; }
.score-meta { font-size: 13px; color: #666; margin-top: 4px; }
.breakdown { display: flex; gap: 12px; margin-top: 12px; }
.bd-item { text-align: center; background: #0d0d14; border-radius: 8px; padding: 12px 20px; flex: 1; border: 1px solid #1e2040; }
.bd-num  { font-size: 24px; font-weight: 700; }
.bd-lbl  { font-size: 12px; color: #666; margin-top: 2px; }
table { width: 100%; border-collapse: collapse; margin-bottom: 16px; }
thead th {
  text-align: left; font-size: 11px; font-weight: 600;
  color: #666; text-transform: uppercase; letter-spacing: 0.06em;
  padding: 8px 12px; border-bottom: 1px solid #1e2040;
}
tbody tr:hover td { background: #13131f; }
td { padding: 10px 12px; border-bottom: 1px solid #1a1a2e; font-size: 13px; vertical-align: top; }
.sev-badge {
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-size: 11px; font-weight: 700; text-transform: uppercase;
}
code {
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 12px; background: #0d0d14; padding: 6px 8px;
  border-radius: 4px; display: block; white-space: pre-wrap;
  word-break: break-word; color: #a8b0c8; border: 1px solid #1a1a2e;
}
.rec-card {
  background: #13131f; border: 1px solid #1e2040; border-radius: 10px;
  padding: 16px 20px; margin-bottom: 12px;
}
.rec-header { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.rec-cat { font-size: 14px; font-weight: 700; color: #fff; }
.rec-actions { list-style: none; }
.rec-actions li {
  padding: 6px 0 6px 20px; font-size: 13px; color: #aaa;
  position: relative; border-bottom: 1px solid #1a1a2e;
}
.rec-actions li:last-child { border-bottom: none; }
.rec-actions li::before { content: "›"; position: absolute; left: 4px; color: #6366f1; }
.meta-grid { display: grid; grid-template-columns: 160px 1fr; gap: 8px 16px; font-size: 13px; }
.meta-label { color: #555; font-weight: 600; }
.meta-value { color: #c5c8d6; word-break: break-all; }
.footer {
  margin-top: 40px; padding-top: 20px; border-top: 1px solid #1e2040;
  font-size: 12px; color: #444; text-align: center;
}
"""


def _serialize_html(report: dict) -> str:
    """Generate a fully self-contained, XSS-safe HTML report document."""
    meta      = report.get("meta", {})
    summary   = report.get("summary", {})
    breakdown = report.get("breakdown", {})
    categories = report.get("categories", {})
    findings  = report.get("findings", [])
    recs      = report.get("recommendations", [])
    engine    = report.get("engine", {})
    is_sim    = str(meta.get("scan_id", "")).startswith("sim-")

    risk_level = summary.get("risk_level", "LOW")
    risk_score = summary.get("risk_score", 0)
    risk_color = _RISK_COLORS.get(risk_level, "#888")

    def sev_badge(sev: str) -> str:
        fg, bg = _SEV_COLORS.get(sev.lower(), ("#888", "#88822"))
        return (
            f'<span class="sev-badge" '
            f'style="background:{bg};color:{fg};border:1px solid {fg}44;">'
            f'{_h(sev.upper())}</span>'
        )

    # ── Finding rows ──
    finding_rows = []
    for i, f in enumerate(findings, 1):
        conf_pct = round(f.get("confidence", 0) * 100)
        finding_rows.append(
            f"<tr>"
            f'<td style="color:#666;white-space:nowrap;">#{i}</td>'
            f"<td>{sev_badge(f.get('severity', ''))}</td>"
            f'<td style="font-weight:600;">{_h(f.get("category", "").replace("_", " ").title())}</td>'
            f'<td style="color:#aaa;">{conf_pct}%</td>'
            f'<td><code>{_h(f.get("evidence", ""))}</code>'
            + (f'<div style="font-size:11px;color:#555;margin-top:4px;">'
               f'Probe: {_h(f.get("probe_id",""))} · Source: {_h(f.get("source",""))}'
               f'</div>' if f.get("probe_id") else "")
            + f"</td>"
            f"</tr>"
        )

    # ── Category rows ──
    cat_rows = []
    for name, cat in categories.items():
        max_sev = cat.get("max_severity") or "none"
        fg, _ = _SEV_COLORS.get(max_sev, ("#888", "#22"))
        cat_rows.append(
            f"<tr>"
            f'<td style="font-weight:600;">{_h(name.replace("_"," ").title())}</td>'
            f'<td style="text-align:center;">{cat.get("count", 0)}</td>'
            f'<td>{sev_badge(max_sev) if max_sev != "none" else "—"}</td>'
            f'<td>{cat.get("avg_confidence", 0):.0%}</td>'
            f"</tr>"
        )

    # ── Recommendation cards ──
    rec_cards = []
    for rec in recs:
        sev = rec.get("severity", "low")
        actions_html = "".join(
            f"<li>{_h(a)}</li>" for a in rec.get("actions", [])
        )
        rec_cards.append(
            f'<div class="rec-card">'
            f'<div class="rec-header">'
            f'{sev_badge(sev)}'
            f'<span class="rec-cat">{_h(rec.get("category", "").replace("_"," ").title())}</span>'
            f"</div>"
            f'<ul class="rec-actions">{actions_html}</ul>'
            f"</div>"
        )

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Sentryɸ Security Report — {_h(meta.get("target",""))}</title>
  <style>{_INLINE_CSS}</style>
</head>
<body>
<div class="wrap">

  <div class="brand">
    <div>
      <div class="brand-name">Sentryɸ</div>
      <div class="brand-sub">LLM Security Assessment Report</div>
    </div>
  </div>

  {"<div class='sim-banner'>⚠ SIMULATION MODE — This report was generated with simulated data and does not represent a real security assessment.</div>" if is_sim else ""}

  <h2>Executive Summary</h2>
  <div class="score-card">
    <div>
      <div class="score-num" style="color:{risk_color};">
        {risk_score}<span class="score-denom">/100</span>
      </div>
      <div class="score-level" style="color:{risk_color};">{_h(risk_level)} Risk</div>
      <div class="score-meta">{summary.get("total_findings",0)} finding(s) detected</div>
    </div>
    <div class="breakdown">
      <div class="bd-item">
        <div class="bd-num" style="color:#e05260;">{breakdown.get("high",0)}</div>
        <div class="bd-lbl">High</div>
      </div>
      <div class="bd-item">
        <div class="bd-num" style="color:#e8a838;">{breakdown.get("medium",0)}</div>
        <div class="bd-lbl">Medium</div>
      </div>
      <div class="bd-item">
        <div class="bd-num" style="color:#4a9edb;">{breakdown.get("low",0)}</div>
        <div class="bd-lbl">Low</div>
      </div>
    </div>
  </div>

  <h2>Scan Details</h2>
  <div class="meta-grid">
    <span class="meta-label">Target</span><span class="meta-value">{_h(meta.get("target",""))}</span>
    <span class="meta-label">Mode</span><span class="meta-value">{_h(meta.get("mode",""))}</span>
    <span class="meta-label">Scan depth</span><span class="meta-value">{_h(meta.get("scan_depth",""))}</span>
    <span class="meta-label">Categories</span><span class="meta-value">{_h(", ".join(meta.get("categories",[])))}</span>
    <span class="meta-label">Scan ID</span><span class="meta-value">{_h(meta.get("scan_id",""))}</span>
    <span class="meta-label">Scan time</span><span class="meta-value">{_h(meta.get("timestamp",""))}</span>
    <span class="meta-label">Report time</span><span class="meta-value">{_h(meta.get("report_generated_at",""))}</span>
  </div>

  {"<h2>Category Breakdown</h2><table><thead><tr><th>Category</th><th>Findings</th><th>Max Severity</th><th>Avg Confidence</th></tr></thead><tbody>" + "".join(cat_rows) + "</tbody></table>" if cat_rows else ""}

  <h2>Findings</h2>
  {"<p style='color:#555;font-size:13px;'>No findings — the target passed all probes.</p>" if not findings else
    "<table><thead><tr><th>#</th><th>Severity</th><th>Category</th><th>Confidence</th><th>Evidence</th></tr></thead><tbody>" + "".join(finding_rows) + "</tbody></table>"}

  <h2>Recommendations</h2>
  {"<p style='color:#555;font-size:13px;'>No recommendations — no vulnerabilities found.</p>" if not rec_cards else "".join(rec_cards)}

  <h2>Assessment Details</h2>
  <div class="meta-grid">
    <span class="meta-label">Engine</span><span class="meta-value">{_h(engine.get("name",""))}</span>
    <span class="meta-label">Probes run</span><span class="meta-value">{engine.get("total_probes",0)}</span>
    {"<span class='meta-label'>Duration</span><span class='meta-value'>" + f"{engine.get('duration_sec',0):.1f}s" + "</span>" if engine.get("duration_sec",0) > 0 else ""}
    {"<span class='meta-label'>Error</span><span class='meta-value' style='color:#e05260;'>" + _h(engine.get("error","")) + "</span>" if engine.get("error") else ""}
  </div>

  <div class="footer">
    <div>Report generated by Sentryɸ · {_h(generated_at)}</div>
    {"<div style='margin-top:4px;color:#e8a838;'>Simulation mode — not a real security assessment</div>" if is_sim else ""}
  </div>

</div>
</body>
</html>"""
    return html


# ─────────────────────────────────────────────
#  PDF via WeasyPrint (optional)
# ─────────────────────────────────────────────

def _weasyprint_available() -> bool:
    """Check if WeasyPrint is installed."""
    try:
        import weasyprint  # noqa: F401
        return True
    except ImportError:
        return False


def _serialize_pdf(report: dict, output_path: str) -> ExportResult:
    """
    Convert the report to PDF using WeasyPrint.
    Falls back to HTML if WeasyPrint is not available.
    """
    if not _weasyprint_available():
        # Fallback: write as HTML with a PDF-not-available notice
        html_path = output_path.replace(".pdf", ".html")
        html = _serialize_html(report)
        # Inject a notice at the top of the document body
        notice = (
            '<div style="background:#e8a83818;border:1px solid #e8a83840;color:#e8a838;'
            'padding:10px 16px;border-radius:8px;margin-bottom:24px;font-size:13px;">'
            "⚠ PDF export requires WeasyPrint. This file has been saved as HTML instead. "
            "Install WeasyPrint (<code>pip install weasyprint</code>) to enable PDF export."
            "</div>"
        )
        # Inject after <div class="wrap"> (double-quoted form used by _serialize_html)
        html = html.replace('<div class="wrap">', f'<div class="wrap">\n\n  {notice}', 1)
        try:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            size = os.path.getsize(html_path)
            return ExportResult(
                success=True,
                path=html_path,
                size_bytes=size,
                fallback="PDF not available (WeasyPrint not installed). Saved as HTML instead.",
            )
        except OSError as e:
            return ExportResult(success=False, path=output_path, error=str(e))

    # WeasyPrint is available — convert HTML → PDF
    try:
        import weasyprint
        html = _serialize_html(report)
        weasyprint.HTML(string=html).write_pdf(output_path)
        size = os.path.getsize(output_path)
        return ExportResult(success=True, path=output_path, size_bytes=size)
    except Exception as e:
        return ExportResult(success=False, path=output_path, error=str(e))


# ─────────────────────────────────────────────
#  Main entry point
# ─────────────────────────────────────────────

VALID_FORMATS = ("json", "html", "txt", "pdf")


def export_report(
    report_dict: dict,
    format: str,         # "json" | "html" | "txt" | "pdf"
    output_path: str,
) -> ExportResult:
    """
    Export a ScanReport dict to the specified format and path.

    Parameters:
        report_dict  -- ScanReport.to_dict() output
        format       -- target format: "json", "html", "txt", or "pdf"
        output_path  -- absolute path where the file should be written

    Returns:
        ExportResult with success, path, size_bytes, and optional error/fallback.
    """
    if format not in VALID_FORMATS:
        return ExportResult(
            success=False,
            path=output_path,
            error=f"Unknown format '{format}'. Valid formats: {', '.join(VALID_FORMATS)}"
        )

    # PDF handled separately (has weasyprint fallback logic)
    if format == "pdf":
        return _serialize_pdf(report_dict, output_path)

    try:
        if format == "json":
            content = _serialize_json(report_dict)
        elif format == "html":
            content = _serialize_html(report_dict)
        else:  # txt
            content = _serialize_txt(report_dict)

        # Ensure parent directory exists
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        size = os.path.getsize(output_path)
        return ExportResult(success=True, path=output_path, size_bytes=size)

    except OSError as e:
        return ExportResult(success=False, path=output_path, error=f"File write error: {e}")
    except Exception as e:
        return ExportResult(success=False, path=output_path, error=f"Export error: {e}")


# ─────────────────────────────────────────────
#  Subprocess entry point (called by Electron main.cjs)
#
#  Reads a JSON payload from stdin:
#    { "action": "export", "format": "...", "output_path": "...", "report": {...} }
#
#  Writes a single JSON result line to stdout:
#    { "success": true,  "path": "...", "size_bytes": 12345, "fallback": null }
#    { "success": false, "path": "...", "error": "..." }
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    try:
        raw = sys.stdin.buffer.read().decode("utf-8-sig").strip()
        payload = json.loads(raw)
    except Exception as e:
        print(json.dumps({"success": False, "path": "", "error": f"Invalid JSON input: {e}"}), flush=True)
        sys.exit(1)

    fmt         = payload.get("format", "json")
    output_path = payload.get("output_path", "")
    report_dict = payload.get("report", {})

    if not output_path:
        print(json.dumps({"success": False, "path": "", "error": "Missing output_path"}), flush=True)
        sys.exit(1)

    if not report_dict:
        print(json.dumps({"success": False, "path": output_path, "error": "Missing report data"}), flush=True)
        sys.exit(1)

    result = export_report(report_dict, fmt, output_path)

    print(json.dumps({
        "success":    result.success,
        "path":       result.path,
        "size_bytes": result.size_bytes,
        "fallback":   result.fallback or None,
        "error":      result.error or None,
    }), flush=True)

    sys.exit(0 if result.success else 1)
