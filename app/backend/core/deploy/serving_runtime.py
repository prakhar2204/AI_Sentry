"""Portable inference adapter used in generated images and local HF serving.

No provider credentials are required: selected weights are packaged in /model.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen

READY = False
MODEL = TOKENIZER = None
LOCK = threading.Lock()


def load_transformers(directory):
    global READY, MODEL, TOKENIZER
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    TOKENIZER = AutoTokenizer.from_pretrained(directory, local_files_only=True, trust_remote_code=False)
    MODEL = AutoModelForCausalLM.from_pretrained(directory, local_files_only=True,
        trust_remote_code=False, use_safetensors=True, torch_dtype=torch.float32)
    MODEL.eval()
    READY = True


def inference(data):
    if not isinstance(data, dict) or not isinstance(data.get('messages'), list):
        raise ValueError('Provide an OpenAI-compatible messages array')
    data = {k: data[k] for k in ('messages', 'temperature', 'max_tokens') if k in data}
    data['max_tokens'] = min(2048, max(1, int(data.get('max_tokens', 256))))
    data['stream'] = False
    if os.environ.get('MODEL_FORMAT', 'gguf') == 'gguf':
        request = Request('http://127.0.0.1:8081/v1/chat/completions', json.dumps(data).encode(), {'Content-Type': 'application/json'})
        with urlopen(request, timeout=240) as response:
            return json.load(response)
    import torch
    with LOCK, torch.inference_mode():
        text = TOKENIZER.apply_chat_template(data['messages'], tokenize=False, add_generation_prompt=True) if TOKENIZER.chat_template else '\n'.join(str(item.get('content', '')) for item in data['messages'])
        encoded = TOKENIZER(text, return_tensors='pt')
        if encoded['input_ids'].shape[-1] + data['max_tokens'] > int(os.environ.get('MODEL_CONTEXT', '4096')):
            raise ValueError('Request exceeds the configured context length')
        output = MODEL.generate(**encoded, max_new_tokens=data['max_tokens'], do_sample=False,
                                pad_token_id=TOKENIZER.eos_token_id)
        answer = TOKENIZER.decode(output[0][encoded['input_ids'].shape[-1]:], skip_special_tokens=True)
        return {'choices': [{'message': {'role': 'assistant', 'content': answer}, 'finish_reason': 'stop'}]}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Never put prompts or model responses in request logs.

    def reply(self, status, data):
        content = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if self.path not in ('/ping', '/health'):
            return self.reply(404, {'error': 'Not found'})
        healthy = READY
        if os.environ.get('MODEL_FORMAT', 'gguf') == 'gguf':
            try:
                with urlopen('http://127.0.0.1:8081/health', timeout=2) as response:
                    healthy = response.status == 200
            except Exception:
                healthy = False
        self.reply(200 if healthy else 503, {'status': 'ready' if healthy else 'loading'})

    def do_POST(self):
        if self.path not in ('/invocations', '/predict', '/v1/chat/completions'):
            return self.reply(404, {'error': 'Not found'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 2 * 1024 * 1024:
                return self.reply(413, {'error': 'Request exceeds 2 MiB'})
            data = json.loads(self.rfile.read(length))
            if isinstance(data, dict) and 'instances' in data:
                if not isinstance(data['instances'], list) or not 1 <= len(data['instances']) <= 8:
                    raise ValueError('Supply 1–8 prediction instances')
                return self.reply(200, {'predictions': [inference(item) for item in data['instances']]})
            self.reply(200, inference(data))
        except (ValueError, TypeError, KeyError):
            self.reply(400, {'error': 'Invalid request or context limit exceeded'})
        except Exception:
            self.reply(503, {'error': 'Model unavailable or inference failed'})


def main():
    directory = os.environ.get('MODEL_PATH', '/model')
    child = None
    if os.environ.get('MODEL_FORMAT', 'gguf') == 'gguf':
        model = next(Path(directory).glob('*.gguf'), None)
        if not model:
            raise RuntimeError('The packaged GGUF model is missing')
        child = subprocess.Popen(['/app/llama-server', '--model', str(model), '--host', '127.0.0.1',
            '--port', '8081', '--ctx-size', str(int(os.environ.get('MODEL_CONTEXT', '4096')) * int(os.environ.get('MODEL_CONCURRENCY', '1'))),
            '--parallel', os.environ.get('MODEL_CONCURRENCY', '1'), '--n-gpu-layers',
            '99' if os.environ.get('MODEL_ACCELERATOR') == 'gpu' else '0'])
    else:
        # A failed load must exit the process rather than leave a permanently
        # "loading" health endpoint alive for the entire deployment timeout.
        load_transformers(directory)
    try:
        ThreadingHTTPServer((os.environ.get('MODEL_BIND', '0.0.0.0'), int(os.environ.get('PORT', '8080'))), Handler).serve_forever()
    finally:
        if child:
            child.terminate()
            child.wait(timeout=15)


if __name__ == '__main__':
    main()
