"""Atomic deployment journals. Credentials never belong in these records."""
from __future__ import annotations

import json
import os
import re
import tempfile
import threading
from pathlib import Path


class DeploymentStore:
    def __init__(self, directory: Path | None = None):
        base = Path(os.environ.get('SENTRYPHI_DATA_DIR') or
                    Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local/share')) / 'SentryPhi')
        self.directory = Path(directory) if directory else base / 'deployments'
        self.lock = threading.RLock()

    def _path(self, deployment_id: str) -> Path:
        if not re.fullmatch(r'sp-[a-zA-Z0-9_-]{1,64}', deployment_id):
            raise ValueError('Invalid deployment ID')
        return self.directory / f'{deployment_id}.json'

    def load(self, deployment_id: str) -> dict | None:
        with self.lock:
            path = self._path(deployment_id)
            if not path.exists():
                return None
            data = json.loads(path.read_text(encoding='utf-8'))
            if data.get('deployment_id') != deployment_id:
                raise ValueError('Deployment journal ID mismatch')
            return data

    def save(self, record: dict) -> None:
        self._check_no_credentials(record)
        with self.lock:
            path = self._path(record['deployment_id'])
            self.directory.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix='.deployment-', suffix='.tmp', dir=self.directory)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                    json.dump(record, stream, indent=2)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, path)
            finally:
                Path(temporary).unlink(missing_ok=True)

    def list(self, provider: str | None = None) -> list[dict]:
        if not self.directory.exists():
            return []
        records = []
        for path in sorted(self.directory.glob('sp-*.json')):
            record = self.load(path.stem)
            if record and (provider is None or record.get('provider') == provider):
                records.append(record)
        return records

    @classmethod
    def _check_no_credentials(cls, value):
        if isinstance(value, dict):
            for key, item in value.items():
                if re.search(r'password|secret|access_token|refresh_token|session_token|access_key|private_key|authorization|credentials', key, re.I):
                    raise ValueError(f'Credentials must not be persisted in deployment records ({key})')
                cls._check_no_credentials(item)
        elif isinstance(value, list):
            for item in value:
                cls._check_no_credentials(item)
