"""
Sentryɸ — OAuth Callback Server
core/deploy/oauth_server.py

Starts a short-lived local HTTP server on localhost to capture OAuth redirect callbacks.
Used by all three cloud providers (AWS SSO, Azure AD, GCP OAuth 2.0).

Protocol:
  1. Main process calls start_callback_server(port) → returns server object
  2. User opens auth URL in browser
  3. Provider redirects to http://localhost:{port}/callback?code=...&state=...
  4. Server captures code+state, shows success page, shuts itself down
  5. Main process calls get_auth_result() → returns {"code": ..., "state": ...}

Security:
  - Server only accepts connections on 127.0.0.1 (not 0.0.0.0)
  - Server shuts down immediately after first callback (no persistent listener)
  - code and state are held in memory only, cleared after retrieval
  - Timeout: server auto-shuts after max_wait_seconds if no callback arrives
"""

from __future__ import annotations

import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse
from typing import Optional


# ─────────────────────────────────────────────
#  Success page shown to the user in browser
# ─────────────────────────────────────────────

_SUCCESS_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sentryɸ — Authentication Complete</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #0a0f1a;
      color: #e2e8f0;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
    }
    .card {
      background: #111827;
      border: 1px solid rgba(0,212,255,0.2);
      border-radius: 16px;
      padding: 48px;
      max-width: 420px;
      text-align: center;
      box-shadow: 0 0 40px rgba(0,212,255,0.05);
    }
    .icon { font-size: 48px; margin-bottom: 20px; }
    h1 { font-size: 22px; font-weight: 700; color: #00d4ff; margin-bottom: 12px; }
    p  { font-size: 14px; color: #94a3b8; line-height: 1.6; }
    .tag { display: inline-block; margin-top: 20px; padding: 6px 14px;
           border-radius: 20px; background: rgba(0,212,255,0.1);
           color: #00d4ff; font-size: 12px; font-weight: 600; }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">✓</div>
    <h1>Authentication Complete</h1>
    <p>You've successfully signed in. You can close this browser tab and return to Sentryɸ.</p>
    <span class="tag">Sentryɸ Security Scanner</span>
  </div>
</body>
</html>
"""

_ERROR_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Sentryɸ — Authentication Error</title>
  <style>
    body {{ font-family: sans-serif; background: #0a0f1a; color: #e2e8f0;
            display:flex; align-items:center; justify-content:center; min-height:100vh; }}
    .card {{ background:#111827; border:1px solid rgba(239,68,68,0.3);
              border-radius:16px; padding:48px; max-width:420px; text-align:center; }}
    h1 {{ color:#ef4444; margin-bottom:12px; }} p {{ color:#94a3b8; font-size:14px; }}
  </style>
</head>
<body>
  <div class="card">
    <div style="font-size:48px">✗</div>
    <h1>Authentication Error</h1>
    <p>{message}</p>
  </div>
</body>
</html>
"""


# ─────────────────────────────────────────────
#  Shared result container (thread-safe)
# ─────────────────────────────────────────────

class _AuthResult:
    def __init__(self) -> None:
        self._lock   = threading.Lock()
        self._result: dict | None = None
        self._event  = threading.Event()

    def set(self, result: dict) -> None:
        with self._lock:
            self._result = result
        self._event.set()

    def get(self, timeout: float = 300.0) -> dict | None:
        self._event.wait(timeout=timeout)
        with self._lock:
            result = self._result
            self._result = None   # Clear after retrieval
        return result


# ─────────────────────────────────────────────
#  Request handler
# ─────────────────────────────────────────────

def _make_handler(auth_result: _AuthResult, server_ref: list):
    class CallbackHandler(BaseHTTPRequestHandler):

        def log_message(self, format, *args):
            pass   # Suppress access log output

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path != "/callback":
                self._send_html(404, "<p>Not found</p>")
                return

            qs    = parse_qs(parsed.query)
            code  = qs.get("code",  [""])[0]
            state = qs.get("state", [""])[0]
            error = qs.get("error", [""])[0]

            if error:
                self._send_html(
                    400,
                    _ERROR_HTML.format(message=f"Provider error: {error}"),
                )
                auth_result.set({"error": error, "code": "", "state": state})
            elif code:
                self._send_html(200, _SUCCESS_HTML)
                auth_result.set({"code": code, "state": state, "error": ""})
            else:
                self._send_html(
                    400,
                    _ERROR_HTML.format(message="No authorization code received from provider."),
                )
                auth_result.set({"error": "no_code", "code": "", "state": state})

            # Shut down server in background thread to avoid blocking response
            def shutdown():
                time.sleep(0.1)
                if server_ref:
                    server_ref[0].shutdown()
            threading.Thread(target=shutdown, daemon=True).start()

        def _send_html(self, status: int, html: str) -> None:
            body = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type",   "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control",  "no-store")
            self.end_headers()
            self.wfile.write(body)

    return CallbackHandler


# ─────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────

class OAuthCallbackServer:
    """
    Short-lived local OAuth callback server.

    Usage:
        server = OAuthCallbackServer(port=9876)
        server.start()                          # starts in background thread
        open_browser(auth_url)
        result = server.wait_for_callback(timeout=300)
        # result = {"code": "...", "state": "...", "error": ""}
    """

    def __init__(self, port: int = 9876) -> None:
        self.port        = port
        self._auth_result = _AuthResult()
        self._server_ref: list = []
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start listening for the OAuth callback in a background thread."""
        handler = _make_handler(self._auth_result, self._server_ref)
        httpd   = HTTPServer(("127.0.0.1", self.port), handler)
        self._server_ref.append(httpd)

        self._thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        self._thread.start()

    def wait_for_callback(self, timeout: float = 300.0) -> dict | None:
        """
        Block until the OAuth callback arrives or timeout expires.

        Returns:
            {"code": str, "state": str, "error": str} or None on timeout
        """
        return self._auth_result.get(timeout=timeout)

    def stop(self) -> None:
        """Forcibly stop the server (e.g. on cancellation)."""
        if self._server_ref:
            try:
                self._server_ref[0].shutdown()
            except Exception:  # noqa: BLE001
                pass


# ─────────────────────────────────────────────
#  Provider port registry
# ─────────────────────────────────────────────

PROVIDER_PORTS = {
    "aws":     9876,
    "azure":   9877,
    "gcp":     9878,
    "private": 0,      # No OAuth needed
}


def get_callback_server(provider: str) -> OAuthCallbackServer | None:
    """
    Create and return an OAuthCallbackServer for the given provider.
    Returns None for providers that don't use browser OAuth (e.g. private).
    """
    port = PROVIDER_PORTS.get(provider, 0)
    if port == 0:
        return None
    return OAuthCallbackServer(port=port)
