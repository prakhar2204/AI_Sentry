"""Own a loopback-only Transformers process, using the deployment inference adapter."""
import atexit
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen


class LocalTransformersServer:
    def __init__(self):
        self.process = None
        atexit.register(self.stop)

    def start(self, profile, timeout=600):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        environment = dict(os.environ, MODEL_FORMAT='transformers', MODEL_PATH=profile['source'],
            MODEL_CONTEXT=str(profile['context_length']), MODEL_CONCURRENCY='1',
            MODEL_BIND='127.0.0.1', PORT=str(port), HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
        self.process = subprocess.Popen([sys.executable, str(Path(__file__).parent / 'deploy' / 'serving_runtime.py')],
            env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        endpoint = f'http://127.0.0.1:{port}'
        deadline = time.monotonic() + timeout
        try:
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    raise RuntimeError('Transformers could not load the model. Check architecture support and complete tokenizer/safetensors files.')
                try:
                    with urlopen(endpoint + '/health', timeout=2) as response:
                        if response.status == 200:
                            return endpoint
                except OSError:
                    pass
                time.sleep(.5)
            raise RuntimeError('Transformers model loading timed out. Check available RAM and model compatibility.')
        except BaseException:
            self.stop()
            raise

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
