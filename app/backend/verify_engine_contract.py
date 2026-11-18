"""Exercise every configured Garak probe against a local deterministic HTTP fixture.

This verifies probe/dependency/API compatibility; it is NOT a model security scan.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from core.garak_engine import GarakEngine


class Handler(BaseHTTPRequestHandler):
    requests = 0
    auth_failures = 0
    expected_key = None

    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.expected_key and self.headers.get('Authorization') != f'Bearer {self.expected_key}':
            Handler.auth_failures += 1
            self.send_error(401)
            return
        assert body['messages'] and body['max_tokens'] > 0
        Handler.requests += 1
        payload = json.dumps({'choices': [{'message': {'role': 'assistant', 'content':
            'I cannot assist with that request.'}}]}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--categories', default='')
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('--check-auth', action='store_true', help='Require a local fixture API key')
    args = parser.parse_args()
    Handler.expected_key = 'fixture-key: #not-a-real-secret' if args.check_auth else None
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        engine = GarakEngine(target_url=f'http://127.0.0.1:{server.server_port}/v1/chat/completions',
                             output_dir=Path('scan_artifacts/contract'), depth='deep', prompt_cap=1,
                             timeout=args.timeout, api_key=Handler.expected_key,
                             on_progress=lambda *args: print(args[-1], flush=True))
        result = engine.run(categories=args.categories.split(',') if args.categories else None)
        print(json.dumps({'probes': len(result.probe_results), 'requests': Handler.requests,
                          'auth_failures': Handler.auth_failures, 'errors': result.errors}), flush=True)
        raise SystemExit(0 if result.all_ok and Handler.requests and not Handler.auth_failures else 1)
    finally:
        server.shutdown()
