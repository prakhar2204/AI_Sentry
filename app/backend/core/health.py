"""Read-only environment checks for the CLI; no downloads or model loading."""
from dataclasses import dataclass
from importlib import metadata, util
from pathlib import Path
import shutil
import sys


@dataclass(frozen=True)
class HealthCheck:
    name: str
    status: str
    detail: str


def _installed(name: str) -> bool:
    try:
        return util.find_spec(name) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


def _version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "version unavailable"


def environment_checks() -> list[HealthCheck]:
    """Check discovery and local prerequisites, not remote provider credentials."""
    from core.local_model_server import _SERVER_EXE
    garak = _installed("garak")
    pyrit = _installed("pyrit")
    checks = [
        HealthCheck("Python", "pass" if sys.version_info >= (3, 10) else "fail", sys.version.split()[0]),
        HealthCheck("HTTP client", "pass" if _installed("httpx") else "fail", "httpx"),
        HealthCheck("Real scan engine", "pass" if garak or pyrit else "fail",
                    "Installed engine found" if garak or pyrit else "Install requirements-scan.txt in this Python environment"),
        HealthCheck("Garak", "pass" if garak else "warn", _version("garak") if garak else "Not installed"),
        HealthCheck("PyRIT", "pass" if pyrit else "warn", _version("pyrit") if pyrit else "Optional engine not installed"),
        HealthCheck("Local model server", "pass" if _SERVER_EXE.is_file() else "warn",
                    str(_SERVER_EXE) if _SERVER_EXE.is_file() else "Not cached; local GGUF scans need the server download"),
    ]
    try:
        free_mb = shutil.disk_usage(Path(__file__).resolve().parent).free // (1024 * 1024)
        checks.append(HealthCheck("Free disk", "pass" if free_mb >= 500 else "warn", f"{free_mb} MB available"))
    except OSError as exc:
        checks.append(HealthCheck("Free disk", "warn", str(exc)))
    return checks


def run_health_check() -> bool:
    """Print actionable diagnostics and fail when required scan dependencies are absent."""
    checks = environment_checks()
    for check in checks:
        print(f"  [{check.status.upper()}] {check.name}: {check.detail}")
    print("\n  Package discovery does not verify model compatibility, GPU drivers, or cloud access.")
    return all(check.status != "fail" for check in checks)
