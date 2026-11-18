"""Explicit local GGUF smoke check; never uses a simulated engine."""
import argparse
import json
import urllib.request
from core.local_model_server import LocalModelServer


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("model")
    parser.add_argument("--scan", action="store_true")
    args = parser.parse_args()
    if args.scan:
        from ipc_server import run_scan_pipeline
        from core.local_model_server import stop_local_model
        try:
            run_scan_pipeline({"target": "http://127.0.0.1:11500/v1/chat/completions",
                               "mode": "local", "local_model_path": args.model,
                               "scan_depth": "quick", "categories": ["prompt_injection"],
                               "engine": "garak"})
        finally:
            stop_local_model()
    else:
        server = LocalModelServer()
        try:
            url = server.start(args.model, on_log=lambda s: print(s, flush=True))
            request = urllib.request.Request(url, data=json.dumps({
                "messages": [{"role": "user", "content": "Reply with READY"}],
                "max_tokens": 16}).encode(), headers={"Content-Type": "application/json"})
            print(urllib.request.urlopen(request, timeout=60).read().decode())
        finally:
            server.stop()
