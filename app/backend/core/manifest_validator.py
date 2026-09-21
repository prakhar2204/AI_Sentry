"""
AI-SENTRY -- Manifest Validator
core/manifest_validator.py

Validates the FINAL resolved ScanManifest before any scan begins.

This is a POST-MERGE validator. It receives the complete ScanManifest
object (already loaded + merged by get_final_manifest in Phase 2b) and
guarantees that every field is semantically safe to pass to the scan
engine.

Distinct from:
  - core/validator.py     (Phase 1d) -- validates raw CLI strings BEFORE
                                        the manifest is built
  - core/manifest.py      (Phase 2b) -- validates JSON structure / types
                                        DURING file loading

This layer validates the RESOLVED manifest object. Even if both earlier
layers pass, this catches combinations that become invalid after merging
(e.g. categories that were individually valid but conflict with the
selected mode).

Design decisions:
  - STRICT: no silent auto-correction of invalid values
  - FAIL-FAST: first failure found is returned immediately
  - PURE: no I/O, no network -- pure logic only
  - SPECIFIC errors: every error names the exact field and the exact
    bad value, plus a concrete hint to fix it

Phase 2c deliverable.
Reference: docs/TRD.md Section 2.1 (Manifest System)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.manifest import (
    ScanManifest,
    ScanMode,
    ScanDepth,
    ProbeCategory,
    ManifestStatus,
    VALID_MODE_NAMES,
    VALID_DEPTH_NAMES,
    VALID_CATEGORY_NAMES,
)


# ─────────────────────────────────────────────
#  Result type
# ─────────────────────────────────────────────

@dataclass
class ManifestValidationIssue:
    """
    A single validation failure produced by validate_manifest().

    Attributes:
        field   -- The manifest field that failed (e.g. "categories")
        value   -- The actual value that was rejected
        message -- Human-readable description of the problem
        hint    -- Concrete suggestion for how to fix it
    """
    field:   str
    value:   object
    message: str
    hint:    str = ""

    @classmethod
    def make(
        cls,
        field:   str,
        value:   object,
        message: str,
        hint:    str = "",
    ) -> "ManifestValidationIssue":
        return cls(field=field, value=value, message=message, hint=hint)


# ─────────────────────────────────────────────
#  Individual field validators
# ─────────────────────────────────────────────

def validate_target(target: object) -> Optional[ManifestValidationIssue]:
    """
    Validate the 'target' field of a resolved manifest.

    Rules:
      - Must be a non-None value
      - Must be a string
      - Must not be empty or whitespace-only
      - Must not exceed 2048 characters (same limit as Phase 1d)
    """
    if target is None:
        return ManifestValidationIssue.make(
            field="target",
            value=None,
            message="'target' is missing. Every manifest must specify a target.",
            hint=(
                "Add --target <url> on the CLI, or set \"target\" in your manifest file.\n"
                "  Example: --target https://api.openai.com/v1"
            ),
        )

    if not isinstance(target, str):
        return ManifestValidationIssue.make(
            field="target",
            value=target,
            message=f"'target' must be a string, got {type(target).__name__}.",
            hint="Provide a URL string, e.g. --target https://api.openai.com/v1",
        )

    if not target.strip():
        return ManifestValidationIssue.make(
            field="target",
            value=repr(target),
            message="'target' is empty or contains only whitespace.",
            hint="Provide a non-empty URL, e.g. --target https://api.openai.com/v1",
        )

    if len(target) > 2048:
        return ManifestValidationIssue.make(
            field="target",
            value=f"{target[:50]}... ({len(target)} chars)",
            message=f"'target' is too long ({len(target)} characters). Maximum is 2048.",
            hint="Shorten the URL to 2048 characters or fewer.",
        )

    return None


def validate_mode(mode: object) -> Optional[ManifestValidationIssue]:
    """
    Validate the 'mode' field of a resolved manifest.

    Accepts: ScanMode enum members OR their string representations.

    Valid values: "api", "local"
    """
    if mode is None:
        return ManifestValidationIssue.make(
            field="mode",
            value=None,
            message="'mode' is missing.",
            hint=f"Valid values: {sorted(VALID_MODE_NAMES)}",
        )

    # Accept ScanMode enum directly
    if isinstance(mode, ScanMode):
        return None  # already a valid enum member

    if not isinstance(mode, str):
        return ManifestValidationIssue.make(
            field="mode",
            value=mode,
            message=f"'mode' must be a string, got {type(mode).__name__}.",
            hint=f"Valid values: {sorted(VALID_MODE_NAMES)}",
        )

    val = mode.strip().lower()
    if val not in VALID_MODE_NAMES:
        return ManifestValidationIssue.make(
            field="mode",
            value=repr(mode),
            message=f"Invalid mode: '{mode}'. Expected one of: {sorted(VALID_MODE_NAMES)}",
            hint=(
                "Use --mode api   for remote API endpoints\n"
                "    --mode local for a local llama.cpp server"
            ),
        )

    return None


def validate_scan_depth(depth: object) -> Optional[ManifestValidationIssue]:
    """
    Validate the 'scan_depth' field of a resolved manifest.

    Accepts: ScanDepth enum members OR their string representations.

    Valid values: "quick", "standard", "deep"

    NOTE: The valid values are quick / standard / deep as defined in the
    TRD (Section 2.1, F-03). An earlier phase prompt mentioned "basic"/"full"
    but those do not exist in the TRD or the implemented ScanDepth enum.
    This validator enforces the TRD-defined values.
    """
    if depth is None:
        return ManifestValidationIssue.make(
            field="scan_depth",
            value=None,
            message="'scan_depth' is missing.",
            hint=f"Valid values: {sorted(VALID_DEPTH_NAMES)}",
        )

    # Accept ScanDepth enum directly
    if isinstance(depth, ScanDepth):
        return None

    if not isinstance(depth, str):
        return ManifestValidationIssue.make(
            field="scan_depth",
            value=depth,
            message=f"'scan_depth' must be a string, got {type(depth).__name__}.",
            hint=f"Valid values: {sorted(VALID_DEPTH_NAMES)}",
        )

    val = depth.strip().lower()
    if val not in VALID_DEPTH_NAMES:
        return ManifestValidationIssue.make(
            field="scan_depth",
            value=repr(depth),
            message=(
                f"Invalid scan_depth: '{depth}'. "
                f"Expected one of: {sorted(VALID_DEPTH_NAMES)}"
            ),
            hint=(
                "Use --depth quick    (5-15 min, core probes)\n"
                "    --depth standard (30-90 min, balanced -- default)\n"
                "    --depth deep     (2-6 hrs, full enterprise suite)"
            ),
        )

    return None


def validate_categories(categories: object) -> Optional[ManifestValidationIssue]:
    """
    Validate the 'categories' field of a resolved manifest.

    Rules:
      - Must not be None
      - Must be a list
      - Must not be empty
      - Every item must be a ProbeCategory enum or a valid category string
      - No unknown category names are silently accepted

    Valid category values:
      prompt_injection, jailbreak, data_leak, harmful_output
    """
    if categories is None:
        return ManifestValidationIssue.make(
            field="categories",
            value=None,
            message="'categories' is missing.",
            hint=(
                "Specify at least one category. Valid values: "
                + ", ".join(sorted(VALID_CATEGORY_NAMES))
            ),
        )

    if not isinstance(categories, list):
        return ManifestValidationIssue.make(
            field="categories",
            value=categories,
            message=(
                f"'categories' must be a list, got {type(categories).__name__}. "
                "Example: [\"jailbreak\", \"data_leak\"]"
            ),
            hint=(
                "Use --categories jailbreak data_leak  (CLI) or\n"
                "    \"categories\": [\"jailbreak\", \"data_leak\"]  (JSON file)"
            ),
        )

    if len(categories) == 0:
        return ManifestValidationIssue.make(
            field="categories",
            value="[]",
            message="'categories' is empty. At least one probe category is required.",
            hint=(
                "Valid categories: "
                + ", ".join(sorted(VALID_CATEGORY_NAMES))
            ),
        )

    for item in categories:
        # Accept ProbeCategory enum members directly
        if isinstance(item, ProbeCategory):
            continue

        if not isinstance(item, str):
            return ManifestValidationIssue.make(
                field="categories",
                value=item,
                message=(
                    f"Each category must be a string, got {type(item).__name__} "
                    f"({repr(item)})."
                ),
                hint=(
                    "Valid categories: "
                    + ", ".join(sorted(VALID_CATEGORY_NAMES))
                ),
            )

        val = item.strip().lower()
        if val not in VALID_CATEGORY_NAMES:
            return ManifestValidationIssue.make(
                field="categories",
                value=repr(item),
                message=(
                    f"Invalid category: '{item}' is not supported."
                ),
                hint=(
                    "Valid categories: "
                    + ", ".join(sorted(VALID_CATEGORY_NAMES))
                    + "\n  Remove or replace the unknown value."
                ),
            )

    return None


def validate_output_dir(output_dir: object) -> Optional[ManifestValidationIssue]:
    """
    Validate the 'output_dir' field of a resolved manifest.

    Rules:
      - May be None or empty (will use default)
      - If provided, must be a string
      - Must not exceed 512 characters
    """
    if output_dir is None or output_dir == "":
        return None  # will fall back to default

    if not isinstance(output_dir, str):
        return ManifestValidationIssue.make(
            field="output_dir",
            value=output_dir,
            message=f"'output_dir' must be a string, got {type(output_dir).__name__}.",
            hint="Example: --output ./aisentry-report",
        )

    if len(output_dir) > 512:
        return ManifestValidationIssue.make(
            field="output_dir",
            value=f"{output_dir[:40]}...",
            message=f"'output_dir' path is too long ({len(output_dir)} chars). Max 512.",
            hint="Use a shorter output directory path.",
        )

    return None


# ─────────────────────────────────────────────
#  Orchestrator
# ─────────────────────────────────────────────

def validate_manifest(manifest: ScanManifest) -> Optional[ManifestValidationIssue]:
    """
    Validate a fully resolved ScanManifest.

    Runs all field validators in priority order. Returns the FIRST
    issue found (fail-fast). Returns None if the manifest is valid.

    Validation order:
      1. target      -- required; must be non-empty string ≤2048 chars
      2. mode        -- must be "api" or "local"
      3. scan_depth  -- must be "quick", "standard", or "deep"
      4. categories  -- must be non-empty list of known category values
      5. output_dir  -- if present, must be a string ≤512 chars

    This function is PURE: no I/O, no network, no side effects.

    Parameters:
        manifest -- A ScanManifest instance (after Phase 2b merging)

    Returns:
        None                     if the manifest is fully valid
        ManifestValidationIssue  describing the first problem found
    """
    if not isinstance(manifest, ScanManifest):
        raise TypeError(
            f"validate_manifest() expects a ScanManifest, got {type(manifest).__name__}."
        )

    checks = [
        lambda: validate_target(manifest.target),
        lambda: validate_mode(manifest.mode),
        lambda: validate_scan_depth(manifest.scan_depth),
        lambda: validate_categories(manifest.categories),
        lambda: validate_output_dir(manifest.output_dir),
    ]

    for check in checks:
        issue = check()
        if issue is not None:
            return issue

    return None


# ─────────────────────────────────────────────
#  Display helper
# ─────────────────────────────────────────────

def format_manifest_validation_error(issue: ManifestValidationIssue) -> str:
    """
    Format a ManifestValidationIssue for CLI display.

    Output format:
        [X] Manifest validation failed -- <field>
            <message>
            Hint: <hint>
    """
    lines = [
        "",
        f"  [X] Manifest validation failed -- {issue.field}",
        f"      {issue.message}",
    ]
    if issue.hint:
        for i, line in enumerate(issue.hint.splitlines()):
            prefix = "      Hint: " if i == 0 else "            "
            lines.append(f"{prefix}{line}")
    return "\n".join(lines)


def print_manifest_validation_error(issue: ManifestValidationIssue) -> None:
    """Print a formatted manifest validation error to stdout."""
    print(format_manifest_validation_error(issue))
    print()
