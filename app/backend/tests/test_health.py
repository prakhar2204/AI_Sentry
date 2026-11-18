from types import SimpleNamespace
from core import health


def test_missing_real_engines_fails_instead_of_reporting_placeholder_success(monkeypatch, capsys):
    monkeypatch.setattr(health, '_installed', lambda name: name == 'httpx')
    assert health.run_health_check() is False
    assert '[FAIL] Real scan engine' in capsys.readouterr().out


def test_optional_engine_missing_does_not_block_garak(monkeypatch):
    monkeypatch.setattr(health, '_installed', lambda name: name in ('garak', 'httpx'))
    monkeypatch.setattr(health, '_version', lambda name: 'test-version')
    checks = health.environment_checks()
    assert not any(c.status == 'fail' for c in checks)
    assert next(c for c in checks if c.name == 'PyRIT').status == 'warn'


def test_low_disk_is_reported_without_changing_files(monkeypatch):
    monkeypatch.setattr(health.shutil, 'disk_usage', lambda path: SimpleNamespace(free=100 * 1024 * 1024))
    check = next(c for c in health.environment_checks() if c.name == 'Free disk')
    assert check.status == 'warn'
    assert '100 MB' in check.detail


def test_cli_returns_failed_health_status(monkeypatch):
    from cli.main import handle_healthcheck
    monkeypatch.setattr(health, 'run_health_check', lambda: False)
    assert handle_healthcheck() == 1


def test_cli_starts_with_windows_legacy_output_encoding():
    import os
    import subprocess
    import sys
    from pathlib import Path
    backend = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, str(backend / '__main__.py'), '--help'],
                            cwd=backend, env={**os.environ, 'PYTHONIOENCODING': 'cp1252'},
                            capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')
    assert 'Sentryɸ' in result.stdout.decode('utf-8')
