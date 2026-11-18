"""Cancellable downloads of public HTTPS GGUF artifacts into app-owned storage."""
import os
from pathlib import Path
import shutil
import threading
import uuid
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .model_profile import inspect_model


class HTTPSRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != 'https':
            raise ValueError('Model download redirected to an insecure URL')
        return super().redirect_request(request, fp, code, msg, headers, newurl)


class ModelDownloads:
    def __init__(self, directory=None, opener=None):
        base = Path(os.environ.get('SENTRYPHI_DATA_DIR') or Path.home() / '.sentryphi')
        self.directory = Path(directory) if directory else base / 'models'
        self.opener = opener or build_opener(HTTPSRedirects()).open
        self.jobs = {}
        self.lock = threading.RLock()

    def start(self, url):
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or not parsed.path.lower().endswith('.gguf'):
            raise ValueError('Use a public direct HTTPS link ending in .gguf without credentials or query parameters. Download private models with the provider tool and select the local file.')
        with self.lock:
            if any(j['state']['status'] == 'running' for j in self.jobs.values()):
                raise ValueError('A model download is already running')
            identifier = uuid.uuid4().hex
            job = {'state': {'download_id': identifier, 'status': 'running', 'downloaded_bytes': 0, 'total_bytes': None}, 'cancel': threading.Event()}
            self.jobs[identifier] = job
            thread = threading.Thread(target=self._download, args=(identifier, url), daemon=True)
            job['thread'] = thread
            thread.start()
            return dict(job['state'])

    def status(self, identifier):
        with self.lock:
            if identifier not in self.jobs:
                raise ValueError('Download not found; start it again')
            return dict(self.jobs[identifier]['state'])

    def cancel(self, identifier):
        with self.lock:
            if identifier not in self.jobs:
                raise ValueError('Download not found')
            self.jobs[identifier]['cancel'].set()
            return self.status(identifier)

    def _download(self, identifier, url):
        job = self.jobs[identifier]
        temporary = self.directory / (identifier + '.part')
        destination = self.directory / (identifier + '.gguf')
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            request = Request(url, headers={'User-Agent': 'SentryPhi/1.0', 'Accept-Encoding': 'identity'})
            with self.opener(request, timeout=30) as response, temporary.open('xb') as output:
                if response.status != 200:
                    raise ValueError('Download server did not return a complete file')
                length = response.headers.get('Content-Length')
                total = int(length) if length is not None else None
                if total is not None and (total < 24 or total + 1024 ** 3 > shutil.disk_usage(self.directory).free):
                    raise ValueError('Model download is empty or exceeds available disk space')
                with self.lock:
                    job['state']['total_bytes'] = total
                downloaded = 0
                while True:
                    if job['cancel'].is_set():
                        raise InterruptedError()
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    if not downloaded and not chunk.startswith(b'GGUF'):
                        raise ValueError('The link returned a web page or an unsupported model instead of GGUF')
                    if shutil.disk_usage(self.directory).free < len(chunk) + 1024 ** 3:
                        raise ValueError('Not enough free disk space to continue the download')
                    output.write(chunk)
                    downloaded += len(chunk)
                    with self.lock:
                        job['state']['downloaded_bytes'] = downloaded
                if total is not None and downloaded != total:
                    raise ValueError('The model download was incomplete. Try again.')
            if job['cancel'].is_set():
                raise InterruptedError()
            temporary.rename(destination)
            profile = inspect_model(str(destination))
            with self.lock:
                job['state'].update(status='complete', path=str(destination), name=Path(urlsplit(url).path).name, model_profile=profile)
        except InterruptedError:
            with self.lock:
                job['state'].update(status='cancelled')
        except ValueError as error:
            with self.lock:
                job['state'].update(status='failed', error=str(error))
        except Exception:
            with self.lock:
                job['state'].update(status='failed', error='Model download failed. Check the public download link, connection and available storage.')
        finally:
            temporary.unlink(missing_ok=True)
            if job['state']['status'] != 'complete':
                destination.unlink(missing_ok=True)


DOWNLOADS = ModelDownloads()
