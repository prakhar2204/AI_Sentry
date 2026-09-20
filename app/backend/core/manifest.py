"""
AI-SENTRY -- Scan Manifest System
core/manifest.py

Defines, creates, validates, and persists the complete specification
of a scan before it executes.

The manifest is the contract between:
  - Phase 1 (Input Layer: consent, validation, endpoint probe)
  - Phase 3 (Orchestration Layer: engine dispatch)

Every scan is driven entirely by its manifest. No hardcoded values
are read anywhere below this layer.

Phase 2a deliverable.

Reference: docs/TRD.md §2.1 "Manifest System"
"""

from __future__ import annotations

import json
import uuid
from copy import deepcopy
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional


# ─────────────────────────────────────────────
#  Enumerations  (match TRD taxonomy exactly)
# ─────────────────────────────────────────────

class ScanDepth(str, Enum):
    """
    Scan depth profile — controls how many probes each engine runs.

    Quick    :  5-15 min  — core probes only; rapid iteration
    Standard : 30-90 min  — balanced coverage; pre-launch default
    Deep     :  2-6 hrs   — full suite; enterprise audit
    """
    QUICK    = "quick"
    STANDARD = "standard"
    DEEP     = "deep"


class ScanMode(str, Enum):
    """
    Connection mode for the target model.
    Must match modes accepted by the validator (Phase 1d).
    """
    API   = "api"
    LOCAL = "local"


class ProbeCategory(str, Enum):
    """
    User-facing probe category names.

    Each category maps to one or more vulnerability classes in the
    TRD taxonomy (VulnClass) and activates specific probes in each
    engine adapter (Phase 3).

    Kept intentionally coarse-grained at the manifest level so users
    don't need to understand engine-level internals.

    Mapping to TRD VulnClass:
      prompt_injection → PROMPT_INJECTION, SYSTEM_PROMPT_EXTRACTION
      jailbreak        → JAILBREAK_DAN, JAILBREAK_ROLEPLAY,
                         JAILBREAK_CRESCENDO, EXCESSIVE_AGENCY
      data_leak        → PII_LEAKAGE, TRAINING_DATA_EXTRACTION,
                         COPYRIGHT_REPRODUCTION, INSECURE_OUTPUT_HANDLING
      harmful_output   → TOXICITY_GENERAL, TOXICITY_TARGETED,
                         BIAS_GENDER, BIAS_RACIAL, BIAS_POLITICAL,
                         HALLUCINATION_FACTUAL, HALLUCINATION_CITATION
    """
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK        = "jailbreak"
    DATA_LEAK        = "data_leak"
    HARMFUL_OUTPUT   = "harmful_output"


class ManifestStatus(str, Enum):
    """
    Manifest lifecycle states (from TRD §2.1).

    CREATED         — manifest object built; not yet submitted to consent gate
    CONSENT_PENDING — shown to user; awaiting yes/no
    APPROVED        — user confirmed; ready to hand to orchestrator
    RUNNING         — orchestration layer has taken control
    COMPLETED       — all engines finished; report generated
    FAILED          — unrecoverable error during execution
    CANCELLED       — user or system aborted during run
    """
    CREATED         = "created"
    CONSENT_PENDING = "consent_pending"
    APPROVED        = "approved"
    RUNNING         = "running"
    COMPLETED       = "completed"
    FAILED          = "failed"
    CANCELLED       = "cancelled"


# ─────────────────────────────────────────────
#  Category metadata  (for display / consent gate)
# ─────────────────────────────────────────────

CATEGORY_DESCRIPTIONS: dict[ProbeCategory, str] = {
    ProbeCategory.PROMPT_INJECTION: (
        "Tests whether the model can be manipulated via crafted inputs to "
        "ignore its system prompt, execute injected instructions, or leak "
        "its internal configuration."
    ),
    ProbeCategory.JAILBREAK: (
        "Tests whether the model can be induced to violate its training "
        "objectives through DAN-style prompts, roleplay scenarios, and "
        "multi-turn crescendo attacks."
    ),
    ProbeCategory.DATA_LEAK: (
        "Tests whether the model leaks PII, reproduces copyrighted content, "
        "exposes training data, or generates outputs that could cause "
        "downstream injection attacks."
    ),
    ProbeCategory.HARMFUL_OUTPUT: (
        "Tests for generation of toxic, biased, or dangerous content "
        "including targeted toxicity, gender/racial/political bias, and "
        "confident generation of false information (hallucination)."
    ),
}

# Categories included by each scan depth (ordered for display)
DEPTH_CATEGORIES: dict[ScanDepth, list[ProbeCategory]] = {
    ScanDepth.QUICK: [
        ProbeCategory.PROMPT_INJECTION,
        ProbeCategory.JAILBREAK,
    ],
    ScanDepth.STANDARD: [
        ProbeCategory.PROMPT_INJECTION,
        ProbeCategory.JAILBREAK,
        ProbeCategory.DATA_LEAK,
        ProbeCategory.HARMFUL_OUTPUT,
    ],
    ScanDepth.DEEP: [
        ProbeCategory.PROMPT_INJECTION,
        ProbeCategory.JAILBREAK,
        ProbeCategory.DATA_LEAK,
        ProbeCategory.HARMFUL_OUTPUT,
    ],
}

# Approximate probe counts per category per depth
# Used by the consent gate to display what will run (Phase 3 will use real counts)
PROBE_COUNT_ESTIMATES: dict[ScanDepth, dict[ProbeCategory, int]] = {
    ScanDepth.QUICK: {
        ProbeCategory.PROMPT_INJECTION: 20,
        ProbeCategory.JAILBREAK:        15,
        ProbeCategory.DATA_LEAK:         0,  # not included in quick
        ProbeCategory.HARMFUL_OUTPUT:    0,
    },
    ScanDepth.STANDARD: {
        ProbeCategory.PROMPT_INJECTION: 60,
        ProbeCategory.JAILBREAK:        50,
        ProbeCategory.DATA_LEAK:        40,
        ProbeCategory.HARMFUL_OUTPUT:   45,
    },
    ScanDepth.DEEP: {
        ProbeCategory.PROMPT_INJECTION: 150,
        ProbeCategory.JAILBREAK:        120,
        ProbeCategory.DATA_LEAK:        100,
        ProbeCategory.HARMFUL_OUTPUT:   110,
    },
}


# ─────────────────────────────────────────────
#  Manifest dataclass
# ─────────────────────────────────────────────

@dataclass
class ScanManifest:
    """
    The complete specification of a scan.

    This object is created before the scan starts and is passed
    unchanged through the entire pipeline. Each layer reads from it;
    only the status field is mutated during execution.

    Fields:
        manifest_id     -- Unique ID for this scan (UUID4 string)
        created_at      -- ISO 8601 UTC timestamp of creation
        target          -- The model endpoint URL or local address
        mode            -- ScanMode: "api" or "local"
        scan_depth      -- ScanDepth: "quick", "standard", or "deep"
        categories      -- Which probe categories to run
        api_key         -- API key (empty string for local mode)
        output_dir      -- Where to write the final report
        status          -- Current lifecycle state
        source_file     -- Path to JSON file this was loaded from (if any)
        notes           -- Free-text field for the user or the system
    """
    manifest_id:  str
    created_at:   str
    target:       str
    mode:         ScanMode
    scan_depth:   ScanDepth
    categories:   list[ProbeCategory]
    api_key:      str            = ""
    output_dir:   str            = "./aisentry-report"
    status:       ManifestStatus = ManifestStatus.CREATED
    source_file:  Optional[str]  = None
    notes:        str            = ""

    # ── Convenience properties ─────────────────

    @property
    def total_probe_estimate(self) -> int:
        """Rough estimate of total probes that will be sent."""
        depth_map = PROBE_COUNT_ESTIMATES.get(self.scan_depth, {})
        return sum(depth_map.get(c, 0) for c in self.categories)

    @property
    def is_local_mode(self) -> bool:
        return self.mode == ScanMode.LOCAL

    @property
    def is_api_mode(self) -> bool:
        return self.mode == ScanMode.API

    # ── Serialisation ──────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize to a plain dict suitable for JSON output.
        All Enum values are converted to their string representation.
        """
        return {
            "manifest_id":         self.manifest_id,
            "created_at":          self.created_at,
            "target":              self.target,
            "mode":                self.mode.value,
            "scan_depth":          self.scan_depth.value,
            "categories":          [c.value for c in self.categories],
            "api_key":             "***" if self.api_key else "",  # never serialize keys
            "output_dir":          self.output_dir,
            "status":              self.status.value,
            "source_file":         self.source_file,
            "notes":               self.notes,
            "total_probe_estimate": self.total_probe_estimate,
        }

    def to_json(self, indent: int = 2) -> str:
        """Return a formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def advance_status(self, new_status: ManifestStatus) -> None:
        """
        Transition the manifest to a new lifecycle state.
        Raises ValueError if the transition is not legal.
        """
        legal: dict[ManifestStatus, set[ManifestStatus]] = {
            ManifestStatus.CREATED:         {ManifestStatus.CONSENT_PENDING},
            ManifestStatus.CONSENT_PENDING: {ManifestStatus.APPROVED, ManifestStatus.CANCELLED},
            ManifestStatus.APPROVED:        {ManifestStatus.RUNNING, ManifestStatus.CANCELLED},
            ManifestStatus.RUNNING:         {ManifestStatus.COMPLETED, ManifestStatus.FAILED, ManifestStatus.CANCELLED},
            ManifestStatus.COMPLETED:       set(),
            ManifestStatus.FAILED:          set(),
            ManifestStatus.CANCELLED:       set(),
        }
        allowed = legal.get(self.status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Invalid status transition: {self.status.value} -> {new_status.value}. "
                f"Allowed from {self.status.value}: "
                f"{[s.value for s in allowed] or 'none (terminal state)'}"
            )
        self.status = new_status


# ─────────────────────────────────────────────
#  Defaults
# ─────────────────────────────────────────────

DEFAULT_SCAN_DEPTH    = ScanDepth.STANDARD
DEFAULT_CATEGORIES    = DEPTH_CATEGORIES[DEFAULT_SCAN_DEPTH]
DEFAULT_OUTPUT_DIR    = "./aisentry-report"

# All valid category strings (for validation)
VALID_CATEGORY_NAMES  = {c.value for c in ProbeCategory}
VALID_DEPTH_NAMES     = {d.value for d in ScanDepth}
VALID_MODE_NAMES      = {m.value for m in ScanMode}


# ─────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────

def create_manifest(
    target:     str,
    mode:       str                   = "api",
    scan_depth: str                   = DEFAULT_SCAN_DEPTH.value,
    categories: Optional[list[str]]   = None,
    api_key:    str                   = "",
    output_dir: str                   = DEFAULT_OUTPUT_DIR,
    notes:      str                   = "",
) -> ScanManifest:
    """
    Create a new ScanManifest from validated string parameters.

    This is the primary factory function. All parameters have safe
    defaults so it can be called with minimal arguments.

    Parameters:
        target      -- URL of the model endpoint or local server
        mode        -- "api" or "local" (default: "api")
        scan_depth  -- "quick", "standard", or "deep" (default: "standard")
        categories  -- list of category names, or None for depth defaults
        api_key     -- API key for remote endpoints (never stored in JSON output)
        output_dir  -- where to write the final report
        notes       -- optional free-text notes

    Returns:
        ScanManifest with status=CREATED

    Raises:
        ValueError if any parameter fails validation
    """
    # Validate and coerce enums
    mode_enum  = _parse_mode(mode)
    depth_enum = _parse_depth(scan_depth)

    # Resolve categories
    if categories is None:
        resolved_categories = list(DEPTH_CATEGORIES[depth_enum])
    else:
        resolved_categories = _parse_categories(categories)

    # Ensure we have at least one category
    if not resolved_categories:
        raise ValueError(
            "At least one probe category must be selected. "
            f"Valid categories: {sorted(VALID_CATEGORY_NAMES)}"
        )

    return ScanManifest(
        manifest_id=str(uuid.uuid4()),
        created_at=_utc_now(),
        target=target.strip(),
        mode=mode_enum,
        scan_depth=depth_enum,
        categories=resolved_categories,
        api_key=api_key,
        output_dir=output_dir,
        notes=notes,
    )


def load_manifest_from_file(path: str) -> ScanManifest:
    """
    Load a ScanManifest from a JSON file on disk.

    The JSON file is the canonical format for sharing, replaying, and
    auditing scan configurations. See example_manifest.json for format.

    Parameters:
        path -- Absolute or relative path to a .json file

    Returns:
        ScanManifest with source_file set to the resolved path

    Raises:
        FileNotFoundError if the file does not exist
        ValueError if the JSON is malformed or contains invalid values
    """
    file_path = Path(path).resolve()

    if not file_path.exists():
        raise FileNotFoundError(
            f"Manifest file not found: {file_path}\n"
            "Create one with: ai-sentry manifest --generate > manifest.json"
        )

    if not file_path.suffix.lower() == ".json":
        raise ValueError(
            f"Manifest file must be a .json file. Got: {file_path.suffix}"
        )

    try:
        raw = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in manifest file '{file_path}': {exc}"
        )

    if not isinstance(raw, dict):
        raise ValueError(
            f"Manifest file must contain a JSON object (dict), not {type(raw).__name__}."
        )

    # Extract required field
    target = raw.get("target", "").strip()
    if not target:
        raise ValueError("Manifest file is missing required field: 'target'")

    manifest = create_manifest(
        target=target,
        mode=raw.get("mode", ScanMode.API.value),
        scan_depth=raw.get("scan_depth", DEFAULT_SCAN_DEPTH.value),
        categories=raw.get("categories", None),
        api_key=raw.get("api_key", ""),
        output_dir=raw.get("output_dir", DEFAULT_OUTPUT_DIR),
        notes=raw.get("notes", ""),
    )

    manifest.source_file = str(file_path)
    return manifest


def merge_cli_and_manifest(
    file_manifest: Optional[ScanManifest],
    *,
    target:     Optional[str] = None,
    mode:       Optional[str] = None,
    scan_depth: Optional[str] = None,
    categories: Optional[list[str]] = None,
    api_key:    Optional[str] = None,
    output_dir: Optional[str] = None,
) -> ScanManifest:
    """
    Merge a file-loaded manifest with CLI overrides.

    Priority (highest to lowest):
        1. Explicit CLI flags (always win)
        2. JSON file values
        3. Built-in safe defaults

    If file_manifest is None, a manifest is built entirely from CLI
    flags + defaults (equivalent to calling create_manifest directly).

    Parameters:
        file_manifest -- ScanManifest loaded from JSON (or None)
        target        -- CLI --target flag (overrides file)
        mode          -- CLI --mode flag (overrides file)
        scan_depth    -- CLI --depth flag (overrides file)
        categories    -- CLI --categories flag (overrides file)
        api_key       -- CLI --api-key flag (overrides file)
        output_dir    -- CLI --output flag (overrides file)

    Returns:
        A new ScanManifest with the merged configuration.
        The source manifest is never mutated.
    """
    if file_manifest is None:
        # No file — build entirely from CLI flags + defaults
        return create_manifest(
            target=target or "",
            mode=mode or ScanMode.API.value,
            scan_depth=scan_depth or DEFAULT_SCAN_DEPTH.value,
            categories=categories,
            api_key=api_key or "",
            output_dir=output_dir or DEFAULT_OUTPUT_DIR,
        )

    # Start from the file manifest values
    merged_target     = target     if target     is not None else file_manifest.target
    merged_mode       = mode       if mode       is not None else file_manifest.mode.value
    merged_depth      = scan_depth if scan_depth is not None else file_manifest.scan_depth.value
    merged_categories = categories if categories is not None else [c.value for c in file_manifest.categories]
    merged_api_key    = api_key    if api_key    is not None else file_manifest.api_key
    merged_output_dir = output_dir if output_dir is not None else file_manifest.output_dir

    new_manifest = create_manifest(
        target=merged_target,
        mode=merged_mode,
        scan_depth=merged_depth,
        categories=merged_categories,
        api_key=merged_api_key,
        output_dir=merged_output_dir,
        notes=file_manifest.notes,
    )

    # Preserve source_file reference for audit trail
    new_manifest.source_file = file_manifest.source_file
    return new_manifest


def generate_example_manifest(
    target:     str = "https://api.openai.com/v1",
    mode:       str = "api",
    scan_depth: str = "standard",
) -> str:
    """
    Generate a commented example manifest JSON string.
    Useful for the `ai-sentry manifest --generate` command (Phase 3+).
    """
    example = {
        "target":     target,
        "mode":       mode,
        "scan_depth": scan_depth,
        "categories": [c.value for c in DEPTH_CATEGORIES[ScanDepth(scan_depth)]],
        "api_key":    "",
        "output_dir": "./aisentry-report",
        "notes":      "Generated by AI-SENTRY. Edit as needed.",
        "_comment": (
            "categories: choose any combination of: "
            + ", ".join(sorted(VALID_CATEGORY_NAMES))
        ),
    }
    return json.dumps(example, indent=2)


# ─────────────────────────────────────────────
#  Display helper  (used by CLI consent gate)
# ─────────────────────────────────────────────

def format_manifest_summary(manifest: ScanManifest) -> str:
    """
    Return a human-readable summary of the manifest for display in
    the consent gate or CLI output.
    """
    divider = "-" * 60
    lines = [
        "",
        divider,
        "  SCAN CONFIGURATION",
        divider,
        f"  Target       : {manifest.target}",
        f"  Mode         : {manifest.mode.value}",
        f"  Scan depth   : {manifest.scan_depth.value}",
        f"  Est. probes  : ~{manifest.total_probe_estimate}",
        "",
        "  Categories:",
    ]

    for cat in manifest.categories:
        desc = CATEGORY_DESCRIPTIONS.get(cat, "")
        lines.append(f"    [{cat.value}]")
        if desc:
            # Wrap description to 55 chars
            words, current = [], ""
            for word in desc.split():
                if len(current) + len(word) + 1 > 55:
                    lines.append(f"      {current.strip()}")
                    current = word + " "
                else:
                    current += word + " "
            if current.strip():
                lines.append(f"      {current.strip()}")

    if manifest.output_dir:
        lines.append(f"\n  Output dir   : {manifest.output_dir}")
    if manifest.notes:
        lines.append(f"  Notes        : {manifest.notes}")
    if manifest.source_file:
        lines.append(f"  Config file  : {manifest.source_file}")

    lines.append(f"\n  Manifest ID  : {manifest.manifest_id}")
    lines.append(f"  Created      : {manifest.created_at}")
    lines.append(divider)
    return "\n".join(lines)


# ─────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────

def _utc_now() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_mode(value: str) -> ScanMode:
    val = (value or "").strip().lower()
    try:
        return ScanMode(val)
    except ValueError:
        raise ValueError(
            f"Invalid mode '{value}'. "
            f"Valid values: {sorted(VALID_MODE_NAMES)}"
        )


def _parse_depth(value: str) -> ScanDepth:
    val = (value or "").strip().lower()
    try:
        return ScanDepth(val)
    except ValueError:
        raise ValueError(
            f"Invalid scan_depth '{value}'. "
            f"Valid values: {sorted(VALID_DEPTH_NAMES)}"
        )


def _parse_categories(values: list[str]) -> list[ProbeCategory]:
    """Parse and validate a list of category name strings."""
    if not isinstance(values, list):
        raise ValueError(
            f"'categories' must be a list, got {type(values).__name__}."
        )

    result: list[ProbeCategory] = []
    seen: set[str] = set()

    for raw in values:
        val = (raw or "").strip().lower()
        if not val:
            continue
        if val in seen:
            continue  # silently deduplicate
        try:
            result.append(ProbeCategory(val))
            seen.add(val)
        except ValueError:
            raise ValueError(
                f"Unknown probe category '{raw}'. "
                f"Valid categories: {sorted(VALID_CATEGORY_NAMES)}"
            )

    return result


# =============================================================================
#  PHASE 2b -- Manifest Loader System
# =============================================================================

@dataclass
class ManifestLoadResult:
    """
    Result returned by get_final_manifest().

    Attributes:
        ok       -- True if a valid manifest was produced.
        manifest -- The resolved ScanManifest (None if ok=False).
        error    -- Human-readable description of what went wrong.
        hint     -- Corrective suggestion shown to the user.
        source   -- Where the manifest came from: "cli", "file", or "merged".
    """
    ok:       bool
    manifest: Optional[ScanManifest] = None
    error:    str                    = ""
    hint:     str                    = ""
    source:   str                    = ""

    @classmethod
    def success(cls, manifest: ScanManifest, source: str) -> "ManifestLoadResult":
        return cls(ok=True, manifest=manifest, source=source)

    @classmethod
    def failure(cls, error: str, hint: str = "") -> "ManifestLoadResult":
        return cls(ok=False, error=error, hint=hint)


def validate_manifest_structure(raw: object) -> Optional[str]:
    """
    Validate the raw parsed JSON object from a manifest file.

    Returns None if the structure is acceptable.
    Returns a human-readable error string if something is wrong.
    """
    if raw is None:
        return "Manifest file is empty or contains only 'null'."

    if isinstance(raw, list):
        return (
            "Manifest file must contain a JSON object { ... }, "
            "not a JSON array [ ... ]."
        )

    if not isinstance(raw, dict):
        return (
            f"Manifest file must contain a JSON object, "
            f"got {type(raw).__name__}."
        )

    if len(raw) == 0:
        return "Manifest file is an empty JSON object {}. 'target' is required."

    data = {k: v for k, v in raw.items() if not k.startswith("_")}

    target = data.get("target")
    if target is None:
        return (
            "Manifest file is missing required field 'target'. "
            "Example: \"target\": \"https://api.openai.com/v1\""
        )
    if not isinstance(target, str) or not target.strip():
        return (
            "'target' must be a non-empty string. "
            f"Got: {repr(target)}"
        )

    if "mode" in data and not isinstance(data["mode"], str):
        return f"'mode' must be a string. Got: {type(data['mode']).__name__}"

    if "scan_depth" in data and not isinstance(data["scan_depth"], str):
        return f"'scan_depth' must be a string. Got: {type(data['scan_depth']).__name__}"

    if "categories" in data:
        cats = data["categories"]
        if not isinstance(cats, list):
            return f"'categories' must be a list. Got: {type(cats).__name__}"
        for i, item in enumerate(cats):
            if not isinstance(item, str):
                return (
                    f"'categories[{i}]' must be a string. "
                    f"Got: {type(item).__name__} ({repr(item)})"
                )

    return None


def load_manifest_file(path: str) -> ScanManifest:
    """
    Load and fully validate a ScanManifest from a JSON file.

    Hardened version of load_manifest_from_file() with:
      - Empty file detection
      - Null / array JSON detection
      - Comment-key stripping (keys starting with _)
      - Structural validation before enum parsing

    Raises:
        FileNotFoundError  -- file does not exist
        ValueError         -- any structural or value problem
    """
    file_path = Path(path).resolve()

    if not file_path.exists():
        raise FileNotFoundError(
            f"Manifest file not found: {file_path}\n"
            "  Create one from the template: copy example_manifest.json config.json"
        )

    if file_path.suffix.lower() != ".json":
        raise ValueError(
            f"Manifest file must have a .json extension. Got: '{file_path.suffix}'"
        )

    content = file_path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(
            f"Manifest file is empty: {file_path.name}\n"
            "  Add at least: {{\"target\": \"https://api.openai.com/v1\"}}"
        )

    try:
        raw = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in '{file_path.name}': {exc}\n"
            "  Tip: validate your JSON at https://jsonlint.com"
        )

    struct_error = validate_manifest_structure(raw)
    if struct_error:
        raise ValueError(f"Manifest '{file_path.name}': {struct_error}")

    data = {k: v for k, v in raw.items() if not k.startswith("_")}

    manifest = create_manifest(
        target=data["target"].strip(),
        mode=data.get("mode", ScanMode.API.value),
        scan_depth=data.get("scan_depth", DEFAULT_SCAN_DEPTH.value),
        categories=data.get("categories", None),
        api_key=data.get("api_key", ""),
        output_dir=data.get("output_dir", DEFAULT_OUTPUT_DIR),
        notes=data.get("notes", ""),
    )
    manifest.source_file = str(file_path)
    return manifest


def get_final_manifest(
    manifest_path:  Optional[str]       = None,
    cli_target:     Optional[str]       = None,
    cli_mode:       Optional[str]       = None,
    cli_scan_depth: Optional[str]       = None,
    cli_categories: Optional[list[str]] = None,
    cli_api_key:    Optional[str]       = None,
    cli_output_dir: Optional[str]       = None,
) -> ManifestLoadResult:
    """
    Single entry point: resolve the final ScanManifest from any combination
    of a JSON file and/or CLI flags.

    Priority: CLI flags > JSON file > built-in defaults

    Scenarios:
      A. CLI only   -- manifest_path=None, cli_target provided
      B. File only  -- manifest_path set, no CLI overrides
      C. Both       -- CLI flags override file values where provided

    Returns ManifestLoadResult with .ok, .manifest, .error, .hint, .source
    """
    file_manifest: Optional[ScanManifest] = None

    # -- Step 1: Load file (if requested) ---------------------------------
    if manifest_path:
        try:
            file_manifest = load_manifest_file(manifest_path)
        except FileNotFoundError as exc:
            return ManifestLoadResult.failure(
                error=str(exc),
                hint="Check the path and try again.",
            )
        except ValueError as exc:
            return ManifestLoadResult.failure(
                error=str(exc),
                hint=(
                    "Fix the manifest file or drop --manifest to use CLI flags only.\n"
                    "  See example_manifest.json for the correct format."
                ),
            )

    # -- Step 2: Determine source label -----------------------------------
    any_cli_override = any([
        cli_target, cli_mode, cli_scan_depth,
        cli_categories, cli_api_key, cli_output_dir,
    ])
    if file_manifest is None:
        source = "cli"
    elif any_cli_override:
        source = "merged"
    else:
        source = "file"

    # -- Step 3: Require a target -----------------------------------------
    effective_target = cli_target or (file_manifest.target if file_manifest else "")
    if not effective_target:
        return ManifestLoadResult.failure(
            error="No target provided. --target is required.",
            hint=(
                "Provide a target via:\n"
                "  CLI:  --target https://api.openai.com/v1\n"
                "  File: {\"target\": \"https://api.openai.com/v1\"}"
            ),
        )

    # -- Step 4: Merge and build ------------------------------------------
    try:
        final = merge_cli_and_manifest(
            file_manifest,
            target=cli_target,
            mode=cli_mode,
            scan_depth=cli_scan_depth,
            categories=cli_categories,
            api_key=cli_api_key,
            output_dir=cli_output_dir,
        )
    except ValueError as exc:
        return ManifestLoadResult.failure(
            error=str(exc),
            hint="Check your --categories, --mode, and --depth values.",
        )

    return ManifestLoadResult.success(manifest=final, source=source)


def print_manifest_load_error(result: ManifestLoadResult) -> None:
    """Print a formatted manifest load error to stdout."""
    print(f"\n  [X] Manifest error: {result.error}")
    if result.hint:
        print(f"\n      Hint: {result.hint}")
    print()
