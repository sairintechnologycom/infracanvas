"""Security scoring engine — build ScoreCard from ResourceGraph."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from infracanvas.graph.models import (
    CategoryScore,
    Finding,
    ResourceGraph,
    ScoreCard,
)

# Grade thresholds — matches UI-SPEC: A>=80, B>=65, C>=50, D>=35, F<35
GRADE_MAP = [(80, "A"), (65, "B"), (50, "C"), (35, "D"), (0, "F")]

# Penalty weights per severity
SEVERITY_WEIGHT: dict[str, int] = {
    "critical": 20,
    "high": 10,
    "medium": 5,
    "info": 1,
}

# Category → rule IDs mapping — SCR-02 spec: 5 dimensions.
# Expanded post-Phase 1 to cover the full rule inventory across AWS (SEC-*),
# Azure (AZ-*), and Network (NET-*). Pre-existing test contracts retained:
# SEC-001/003/004/005 → Security; SEC-002/006/009 → Encryption;
# SEC-007/008 → IAM Hygiene; SEC-010 → Tagging.
CATEGORY_RULES: dict[str, set[str]] = {
    "Security": {
        # AWS network exposure + access control
        "SEC-001", "SEC-003", "SEC-004", "SEC-005",
        "SEC-011", "SEC-014", "SEC-016", "SEC-023", "SEC-024",
        # Azure network + storage public access
        "AZ-001", "AZ-002", "AZ-003", "AZ-005",
        "AZ-006", "AZ-007", "AZ-009", "AZ-010",
        "AZ-013", "AZ-014", "AZ-015",
        # Network rules — internet-facing exposure
        "NET-001", "NET-003", "NET-007", "NET-010", "NET-011",
    },
    "Encryption": {
        "SEC-002", "SEC-006", "SEC-009",
        "SEC-022", "SEC-025", "SEC-026", "SEC-029",
        "SEC-031",
        "AZ-004",
    },
    "IAM Hygiene": {
        "SEC-007", "SEC-008",
        "SEC-015", "SEC-028",
        # Hardcoded secrets are an identity/credential management problem.
        "SEC-032", "AZ-012", "AZ-016",
        "AZ-008", "AZ-011",
    },
    "Cost Efficiency": {
        # Resilience + lifecycle hygiene — wasted spend on un-managed resources
        "SEC-012", "SEC-013", "SEC-017", "SEC-018", "SEC-019", "SEC-020",
        "SEC-021", "SEC-027", "SEC-030",
        "NET-002", "NET-004", "NET-005", "NET-006",
        "NET-008", "NET-009", "NET-012",
    },
    "Tagging": {"SEC-010"},
}


def _grade(score: int) -> str:
    for threshold, letter in GRADE_MAP:
        if score >= threshold:
            return letter
    return "F"


class Scorer:
    """Build a ScoreCard from a scanned ResourceGraph."""

    def build(self, graph: ResourceGraph) -> ScoreCard:
        """Compute overall score, category scores, and top issues."""
        all_findings: list[Finding] = []
        for node in graph.nodes:
            all_findings.extend(node.findings)

        # Overall score
        penalty = sum(
            SEVERITY_WEIGHT.get(f.severity.value, 0) for f in all_findings
        )
        overall = max(0, 100 - penalty)
        overall_grade = _grade(overall)

        # Category scores
        categories: list[CategoryScore] = []
        for cat_name, rule_ids in CATEGORY_RULES.items():
            cat_findings = [f for f in all_findings if f.rule_id in rule_ids]
            cat_penalty = sum(
                SEVERITY_WEIGHT.get(f.severity.value, 0) for f in cat_findings
            )
            cat_score = max(0, 100 - cat_penalty)
            categories.append(
                CategoryScore(
                    name=cat_name,
                    score=cat_score,
                    grade=_grade(cat_score),
                    finding_count=len(cat_findings),
                )
            )

        # Top issues — sorted by severity weight descending, max 5
        weight_order = {"critical": 0, "high": 1, "medium": 2, "info": 3}
        sorted_findings = sorted(
            all_findings,
            key=lambda f: weight_order.get(f.severity.value, 99),
        )
        top_issues = sorted_findings[:5]

        return ScoreCard(
            overall=overall,
            overall_grade=overall_grade,
            categories=categories,
            top_issues=top_issues,
            resource_count=len(graph.nodes),
            estimated_monthly_cost=graph.summary.estimated_monthly_cost,
            scan_id=str(graph.metadata.get("scan_id", str(uuid.uuid4()))),
            project=str(graph.metadata.get("project", "unknown")),
            scanned_at=str(
                graph.metadata.get("scanned_at", datetime.now(UTC).isoformat())
            ),
        )
