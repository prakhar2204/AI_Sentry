"""
AI-SENTRY -- Central Input Validator
core/validator.py

Pure validation layer: no I/O, no HTTP, no side effects.
Every function returns a ValidationError dataclass (never raises).

Sits between the consent gate and the input handlers:

    CLI → Consent → [THIS MODULE] → input_handler / local_handler

Phase 1d deliverable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

# ─────────────────────────────────────────────
#  Result type
# ─────────────────────────────────────────────

@dataclass
class ValidationError:
    """
    Container returned by every validation function.

    Attributes:
        ok      -- True if validation passed, False otherwise.
        field   -- Name of the CLI argument / concept that failed.
        message -- Human-readable explanation of what went wrong.
        hint    -- Optional corrective suggestion shown to the user.
    """
    ok:      bool
    field:   str = ""
    message: str = ""
    hint:    str = ""

    @classmethod
    def pass_(cls) -> "ValidationError":
        """Convenience constructor for a passing result."""
        return cls(ok=True)

    @classmethod
    def fail(cls, field: str, message: str, hint: str = "") -> "ValidationError":
        """Convenience constructor for a failing result."""
        return cls(ok=False, field=field, message=message, hint=hint)


# ─────────────────────────────────────────────
#  Valid values
# ─────────────────────────────────────────────

VALID_MODES   = ("api", "local")
VALID_SCHEMES = ("http", "https")
VALID_DEPTHS  = ("quick", "standard", "deep")

# Hosts accepted in --mode local
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}

# Max URL length — sanity guard against garbage input
_MAX_URL_LEN = 2048


# ─────────────────────────────────────────────
#  Public validators
# ─────────────────────────────────────────────

def validate_mode(mode: Optional[str]) -> ValidationError:
    """
    Validate the --mode argument.

    Rules:
      - Must not be None or empty.
      - Must be one of: 'api', 'local'.

    Returns ValidationError with ok=True on success.
    """
    if not mode:
        return ValidationError.fail(
            field="--mode",
            message="No scan mode provided.",
            hint=f"Use --mode api  (remote endpoint) or --mode local  (llama.cpp server).",
        )

    mode = mode.strip().lower()

    if mode not in VALID_MODES:
        quoted = "  |  ".join(f"'{m}'" for m in VALID_MODES)
        return ValidationError.fail(
            field="--mode",
            message=f"Invalid mode: '{mode}'. Expected one of: {quoted}",
            hint=f"Example: --mode api  or  --mode local",
        )

    return ValidationError.pass_()


def validate_target(target: Optional[str], mode: str) -> ValidationError:
    """
    Validate the --target argument according to the selected mode.

    API mode rules:
      - Must not be empty.
      - Must start with http:// or https://.
      - Must have a non-empty host.
      - Must be <= {_MAX_URL_LEN} characters.

    Local mode rules:
      - Must not be empty.
      - Must start with http:// or https://.
      - Host must be localhost or 127.0.0.1.
      - Must include an explicit port number.

    Returns ValidationError with ok=True on success.
    """
    if not target or not target.strip():
        return ValidationError.fail(
            field="--target",
            message="No target provided. --target is required.",
            hint=(
                "API mode example:   --target https://api.openai.com/v1\n"
                "  Local mode example: --target http://localhost:8080"
            ),
        )

    target = target.strip()

    if len(target) > _MAX_URL_LEN:
        return ValidationError.fail(
            field="--target",
            message=f"Target URL is too long ({len(target)} chars). Maximum is {_MAX_URL_LEN}.",
        )

    # ── Parse ──────────────────────────────────────
    try:
        parsed = urlparse(target)
    except Exception:
        return ValidationError.fail(
            field="--target",
            message=f"Could not parse '{target}' as a URL.",
            hint="Ensure the target is a valid URL starting with http:// or https://",
        )

    # ── Scheme ────────────────────────────────────
    scheme = (parsed.scheme or "").lower()
    if scheme not in VALID_SCHEMES:
        friendly = f"'{scheme}'" if scheme else "(none)"
        return ValidationError.fail(
            field="--target",
            message=f"Invalid URL scheme {friendly}. Only http:// and https:// are supported.",
            hint=(
                "API mode example:   --target https://api.openai.com/v1\n"
                "  Local mode example: --target http://localhost:8080"
            ),
        )

    # ── Host ──────────────────────────────────────
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return ValidationError.fail(
            field="--target",
            message="URL has no host. The target must include a hostname or IP address.",
            hint="Example: --target http://localhost:8080",
        )

    # ── Mode-specific rules ───────────────────────
    mode = (mode or "").strip().lower()

    if mode == "local":
        return _validate_local_target(target, parsed, hostname)

    if mode == "api":
        return _validate_api_target(target, parsed, hostname)

    # Unknown mode — mode validation should catch this first, but be safe
    return ValidationError.fail(
        field="--mode",
        message=f"Cannot validate target: unknown mode '{mode}'.",
    )


def validate_input_combination(mode: Optional[str], target: Optional[str]) -> ValidationError:
    """
    Validate the combination of --mode and --target together.

    Catches contradictions that individual validators cannot see alone:
      - --mode local with a remote host (not localhost)
      - --mode api with a localhost target (suggest --mode local instead)

    Individual field validation (validate_mode, validate_target) should
    be called first; this function assumes both fields are syntactically valid.

    Returns ValidationError with ok=True if the combination is sensible.
    """
    mode   = (mode   or "").strip().lower()
    target = (target or "").strip()

    if not mode or not target:
        # Let the individual validators handle missing fields
        return ValidationError.pass_()

    try:
        parsed = urlparse(target)
    except Exception:
        return ValidationError.pass_()  # URL parse failure handled elsewhere

    hostname = (parsed.hostname or "").lower()

    if mode == "local" and hostname not in _LOCAL_HOSTS and hostname:
        return ValidationError.fail(
            field="--mode / --target",
            message=(
                f"--mode local requires a local address, "
                f"but the target host is '{hostname}'."
            ),
            hint=(
                "For a local llama.cpp server, use:\n"
                "  --mode local --target http://localhost:8080\n\n"
                f"  If '{hostname}' is a remote API, use:\n"
                "  --mode api   --target <url>"
            ),
        )

    if mode == "api" and hostname in _LOCAL_HOSTS:
        return ValidationError.fail(
            field="--mode / --target",
            message=(
                f"--mode api was used with a local address ('{hostname}'). "
                "Remote API mode expects an external endpoint."
            ),
            hint=(
                "For a local llama.cpp server, use:\n"
                "  --mode local --target http://localhost:8080\n\n"
                "  For a remote API, use a public URL:\n"
                "  --mode api   --target https://api.openai.com/v1"
            ),
        )

    return ValidationError.pass_()


# ─────────────────────────────────────────────
#  CLI-facing orchestrator
# ─────────────────────────────────────────────

def run_all_validations(mode: Optional[str], target: Optional[str]) -> Optional[ValidationError]:
    """
    Run the full validation pipeline in order:

        1. validate_mode()
        2. validate_target()
        3. validate_input_combination()

    Returns the first ValidationError that fails, or None if all pass.

    Called by cli/main.py right after the consent gate.
    """
    checks = [
        lambda: validate_mode(mode),
        lambda: validate_target(target, mode or ""),
        lambda: validate_input_combination(mode, target),
    ]

    for check in checks:
        result = check()
        if not result.ok:
            return result

    return None  # all passed


# ─────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────

def _validate_local_target(
    raw: str,
    parsed: object,  # urllib.parse.ParseResult
    hostname: str,
) -> ValidationError:
    """Enforce local-mode-specific URL rules."""

    if hostname not in _LOCAL_HOSTS:
        quoted_hosts = ", ".join(f"'{h}'" for h in sorted(_LOCAL_HOSTS))
        return ValidationError.fail(
            field="--target",
            message=(
                f"In --mode local, the target host must be one of: {quoted_hosts}. "
                f"Got: '{hostname}'."
            ),
            hint=(
                "Start your llama.cpp server and use:\n"
                "  --target http://localhost:8080\n"
                "  --target http://127.0.0.1:8080"
            ),
        )

    port = getattr(parsed, "port", None)
    if port is None:
        return ValidationError.fail(
            field="--target",
            message=(
                "In --mode local, the target must include an explicit port number. "
                f"Got: '{raw}' (no port found)."
            ),
            hint=(
                "Specify the port your llama.cpp server is running on:\n"
                "  --target http://localhost:8080\n"
                "  --target http://127.0.0.1:11434"
            ),
        )

    if not (1 <= port <= 65535):
        return ValidationError.fail(
            field="--target",
            message=f"Port {port} is out of range. Valid ports are 1–65535.",
            hint="Common llama.cpp ports: 8080, 11434, 1234",
        )

    return ValidationError.pass_()


def _validate_api_target(
    raw: str,
    parsed: object,
    hostname: str,
) -> ValidationError:
    """Enforce API-mode-specific URL rules."""

    # Reject obvious file paths that got past the scheme check
    if raw.lower().endswith(".gguf"):
        return ValidationError.fail(
            field="--target",
            message=(
                "The target looks like a local GGUF file path, not an API endpoint. "
                "Local model files are not supported in --mode api."
            ),
            hint=(
                "To use a local model, start llama.cpp and use:\n"
                "  --mode local --target http://localhost:8080\n\n"
                "  To use a remote API, provide a URL:\n"
                "  --mode api   --target https://api.openai.com/v1"
            ),
        )

    # Remote API should generally not use localhost (combination validator also checks this,
    # but a clear message here is better UX if the user did not supply --mode)
    # We allow it here — validate_input_combination will reject the pairing.

    return ValidationError.pass_()


# ─────────────────────────────────────────────
#  Print helper (used by CLI, not by tests)
# ─────────────────────────────────────────────

def print_validation_error(err: ValidationError) -> None:
    """Print a formatted validation error to stdout."""
    print(f"\n  [X] Validation failed — {err.field}")
    print(f"      {err.message}")
    if err.hint:
        print(f"\n      Hint: {err.hint}")
    print()
