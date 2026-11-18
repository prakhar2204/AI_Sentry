import io
import struct
import threading

import pytest
from core.model_download import ModelDownloads


class Response(io.BytesIO):
    status = 200
    def __init__(self, data, length=None):
        super().__init__(data)
        self.headers = {'Content-Length': str(len(data) if length is None else length)}


def test_download_is_validated_then_exposed_as_local_model(tmp_path):
    content = b'GGUF' + struct.pack('<IQQ', 3, 1, 0) + b'test-model'
    downloads = ModelDownloads(tmp_path, lambda *a, **k: Response(content))
    result = downloads.start('https://models.example.test/phi.gguf')
    downloads.jobs[result['download_id']]['thread'].join(5)
    status = downloads.status(result['download_id'])
    assert status['status'] == 'complete'
    assert status['name'] == 'phi.gguf'
    assert status['downloaded_bytes'] == len(content)
    assert not list(tmp_path.glob('*.part'))


@pytest.mark.parametrize('url', ['http://models.example/test.gguf', 'https://user:pass@example.test/a.gguf',
    'https://example.test/a.gguf?token=SENTINEL', 'https://example.test/model.bin', 'https://example.test/page'])
def test_invalid_private_or_unsupported_urls_never_start_requests(tmp_path, url):
    def request(*a, **k):
        raise AssertionError('Must not make a network request')
    with pytest.raises(ValueError):
        ModelDownloads(tmp_path, request).start(url)


@pytest.mark.parametrize('response', [Response(b'<html>download page rather than a model</html>'),
    Response(b'GGUF' + b'0' * 25, length=1024)])
def test_failed_download_does_not_leave_partial_model(tmp_path, response):
    downloads = ModelDownloads(tmp_path, lambda *a, **k: response)
    job = downloads.start('https://example.test/model.gguf')
    downloads.jobs[job['download_id']]['thread'].join(5)
    assert downloads.status(job['download_id'])['status'] == 'failed'
    assert not list(tmp_path.iterdir())


def test_cancellation_removes_partial_download(tmp_path):
    wait = threading.Event()
    def request(*a, **k):
        wait.wait(2)
        return Response(b'GGUF' + struct.pack('<IQQ', 3, 1, 0))
    downloads = ModelDownloads(tmp_path, request)
    job = downloads.start('https://example.test/model.gguf')
    downloads.cancel(job['download_id'])
    wait.set()
    downloads.jobs[job['download_id']]['thread'].join(5)
    assert downloads.status(job['download_id'])['status'] == 'cancelled'
    assert not list(tmp_path.iterdir())
