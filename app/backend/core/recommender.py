"""
AI-SENTRY -- Recommendation Engine
core/recommender.py

Converts a RiskReport into actionable, prioritized remediation
recommendations for each detected vulnerability category.

Design:
    - Recommendations are deterministic: same findings → same output
    - Each category has severity-tiered action sets (high/medium/low)
    - Only categories present in findings are included
    - Output is sorted HIGH → MEDIUM → LOW
    - Actions are deduplicated within each recommendation

This module is PURE: no I/O, no network, no randomness.

Phase 5b deliverable.
Reference: docs/TRD.md Section 2.4 (Intelligence Layer)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from core.scorer import RiskReport, CategoryBreakdown


# ─────────────────────────────────────────────
#  Constants -- severity ordering
# ─────────────────────────────────────────────

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


# ─────────────────────────────────────────────
#  Constants -- action database
# ─────────────────────────────────────────────

# Each category has actions tiered by the max_severity found.
# Higher severity includes all lower-severity actions plus additional ones.

_ACTION_DATABASE: dict[str, dict[str, list[str]]] = {
    "prompt_injection": {
        "high": [
            "Implement strict input sanitization on all user-facing prompts",
            "Deploy a dedicated prompt injection detection layer (e.g. guardrails)",
            "Use parameterized prompt templates -- never concatenate raw user input",
            "Add a system prompt integrity check that validates responses against expected behavior",
            "Conduct a red-team exercise focused on prompt extraction attacks",
        ],
        "medium": [
            "Implement strict input sanitization on all user-facing prompts",
            "Use parameterized prompt templates -- never concatenate raw user input",
            "Add input length limits to reduce attack surface",
        ],
        "low": [
            "Monitor logs for unusual prompt patterns",
            "Add input length limits to reduce attack surface",
        ],
    },
    "jailbreak": {
        "high": [
            "Implement a multi-layer content filter on both input and output",
            "Deploy a jailbreak detection classifier before the main model",
            "Add a response validation layer that checks output against safety policies",
            "Disable or restrict roleplay and persona-switching capabilities",
            "Conduct regular adversarial testing with updated jailbreak techniques",
        ],
        "medium": [
            "Implement a multi-layer content filter on both input and output",
            "Add a response validation layer that checks output against safety policies",
            "Review and strengthen the system prompt's safety instructions",
        ],
        "low": [
            "Review and strengthen the system prompt's safety instructions",
            "Monitor for emerging jailbreak patterns in production logs",
        ],
    },
    "data_leak": {
        "high": [
            "Implement output filtering to detect and redact PII before responses are sent",
            "Add a data loss prevention (DLP) layer to the model pipeline",
            "Restrict the model's ability to reproduce verbatim text beyond a token threshold",
            "Audit training data for sensitive content that could be memorized",
            "Deploy differential privacy or output perturbation techniques",
        ],
        "medium": [
            "Implement output filtering to detect and redact PII before responses are sent",
            "Restrict the model's ability to reproduce verbatim text beyond a token threshold",
            "Add content fingerprinting to detect training data reproduction",
        ],
        "low": [
            "Monitor outputs for patterns matching known sensitive data formats",
            "Add content fingerprinting to detect training data reproduction",
        ],
    },
    "harmful_output": {
        "high": [
            "Deploy a toxicity classifier on all model outputs",
            "Implement bias detection and mitigation in the model pipeline",
            "Add a factual grounding layer to reduce hallucination",
            "Establish content policies with automated enforcement",
            "Conduct a comprehensive bias audit across demographic groups",
        ],
        "medium": [
            "Deploy a toxicity classifier on all model outputs",
            "Implement bias detection and mitigation in the model pipeline",
            "Add factual grounding checks for claims the model makes",
        ],
        "low": [
            "Monitor outputs for bias patterns in production",
            "Add factual grounding checks for claims the model makes",
        ],
    },
}


# ─────────────────────────────────────────────
#  Result type
# ─────────────────────────────────────────────

@dataclass(frozen=True)
class Recommendation:
    """
    A single remediation recommendation for one vulnerability category.

    Attributes:
        category -- Which probe category this addresses
        severity -- The max severity found for this category
        actions  -- Ordered list of remediation actions (deduplicated)
    """
    category: str
    severity: str
    actions:  tuple[str, ...]   # tuple for immutability

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "severity": self.severity,
            "actions":  list(self.actions),
        }


@dataclass(frozen=True)
class RecommendationReport:
    """
    Complete set of recommendations from the engine.

    Attributes:
        recommendations -- Sorted list of Recommendation objects (HIGH first)
        risk_level      -- Echoed from the RiskReport
        risk_score      -- Echoed from the RiskReport
        total_actions   -- Sum of all actions across all recommendations
    """
    recommendations: tuple[Recommendation, ...]
    risk_level:      str
    risk_score:      int
    total_actions:   int

    def to_dict(self) -> dict:
        return {
            "recommendations": [r.to_dict() for r in self.recommendations],
            "risk_level":      self.risk_level,
            "risk_score":      self.risk_score,
            "total_actions":   self.total_actions,
        }


# ─────────────────────────────────────────────
#  Core logic
# ─────────────────────────────────────────────

def get_actions_for_category(category: str, severity: str) -> list[str]:
    """
    Look up remediation actions for a category at a given severity.

    Returns actions for the specified severity tier.
    Unknown categories or severities return a generic action.

    Parameters:
        category -- Category name (e.g. "prompt_injection")
        severity -- Max severity found ("high", "medium", "low")

    Returns:
        List of action strings (deduplicated, order preserved).
    """
    cat_actions = _ACTION_DATABASE.get(category)
    if cat_actions is None:
        return [f"Review findings for '{category}' and apply appropriate mitigations"]

    actions = cat_actions.get(severity)
    if actions is None:
        return [f"Review findings for '{category}' and apply appropriate mitigations"]

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for action in actions:
        if action not in seen:
            seen.add(action)
            unique.append(action)
    return unique


def prioritize_recommendations(
    recommendations: list[Recommendation],
) -> list[Recommendation]:
    """
    Sort recommendations by severity: HIGH → MEDIUM → LOW.

    Within the same severity, categories are sorted alphabetically
    for deterministic output.
    """
    return sorted(
        recommendations,
        key=lambda r: (
            _SEVERITY_ORDER.get(r.severity, 99),
            r.category,
        ),
    )


# ─────────────────────────────────────────────
#  Orchestrator
# ─────────────────────────────────────────────

def generate_recommendations(risk_report: RiskReport) -> RecommendationReport:
    """
    Produce a complete RecommendationReport from a RiskReport.

    Steps:
      1. For each category in the breakdown, look up actions at its max_severity
      2. Build a Recommendation per category
      3. Sort by severity (HIGH first)
      4. Assemble into RecommendationReport

    Parameters:
        risk_report -- A RiskReport from core/scorer.py

    Returns:
        RecommendationReport with prioritized, deduplicated recommendations.
    """
    recs: list[Recommendation] = []

    for cat_name, breakdown in risk_report.category_breakdown.items():
        actions = get_actions_for_category(cat_name, breakdown.max_severity)
        recs.append(Recommendation(
            category=cat_name,
            severity=breakdown.max_severity,
            actions=tuple(actions),
        ))

    sorted_recs = prioritize_recommendations(recs)
    total_actions = sum(len(r.actions) for r in sorted_recs)

    return RecommendationReport(
        recommendations=tuple(sorted_recs),
        risk_level=risk_report.risk_level,
        risk_score=risk_report.risk_score,
        total_actions=total_actions,
    )


# ─────────────────────────────────────────────
#  Display
# ─────────────────────────────────────────────

_DIVIDER = "-" * 60

_SEVERITY_TAGS = {
    "high":   "[HIGH]",
    "medium": "[MED ]",
    "low":    "[LOW ]",
}


def format_recommendations(report: RecommendationReport) -> str:
    """
    Format recommendations for CLI display.

    Output format:
        ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
          RECOMMENDATIONS
        ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
          [HIGH] prompt_injection
            1. Implement strict input sanitization...
            2. Deploy a dedicated prompt injection detection layer...
          ...
        ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
    """
    lines = [
        "",
        _DIVIDER,
        "  RECOMMENDATIONS",
        _DIVIDER,
        "",
    ]

    if not report.recommendations:
        lines.append("  No recommendations -- no findings detected.")
        lines.append("")
        lines.append(_DIVIDER)
        return "\n".join(lines)

    for rec in report.recommendations:
        tag = _SEVERITY_TAGS.get(rec.severity, "[???]")
        lines.append(f"  {tag} {rec.category}")
        for i, action in enumerate(rec.actions, 1):
            lines.append(f"    {i}. {action}")
        lines.append("")

    lines.append(f"  Total actions: {report.total_actions}")
    lines.append("")
    lines.append(_DIVIDER)
    return "\n".join(lines)


def display_recommendations(report: RecommendationReport) -> None:
    """Print formatted recommendations to stdout."""
    print(format_recommendations(report))
