"""Tests for the scorer and scorecard (T-018)."""

import tempfile
from pathlib import Path

from infracanvas.export.scorecard import export_scorecard
from infracanvas.graph.models import (
    Finding,
    GraphSummary,
    ResourceGraph,
    ResourceNode,
    Severity,
)
from infracanvas.security.scorer import Scorer


def _graph_with_findings(findings_per_node: list[list[Finding]]) -> ResourceGraph:
    nodes = []
    for i, findings in enumerate(findings_per_node):
        nodes.append(
            ResourceNode(
                id=f"aws_test.r{i}",
                type="aws_test",
                name=f"r{i}",
                provider="aws",
                findings=findings,
            )
        )
    return ResourceGraph(
        nodes=nodes,
        summary=GraphSummary(total_resources=len(nodes)),
        metadata={
            "scan_id": "test-scan",
            "project": "test-project",
            "scanned_at": "2026-04-14T00:00:00Z",
            "provider": "aws",
            "terraform_version": "1.7.0",
        },
    )


def _finding(rule_id: str, severity: Severity) -> Finding:
    return Finding(
        rule_id=rule_id,
        severity=severity,
        title=f"Test {rule_id}",
        description="Test finding",
        remediation="Fix it",
    )


class TestScorer:
    def test_score_no_findings_100(self):
        graph = _graph_with_findings([[]])
        scorer = Scorer()
        card = scorer.build(graph)
        assert card.overall == 100
        assert card.overall_grade == "A"

    def test_score_one_critical_80(self):
        graph = _graph_with_findings([[_finding("SEC-001", Severity.critical)]])
        scorer = Scorer()
        card = scorer.build(graph)
        assert card.overall == 80

    def test_clamped_at_zero(self):
        findings = [_finding(f"SEC-{i:03d}", Severity.critical) for i in range(10)]
        graph = _graph_with_findings([findings])
        scorer = Scorer()
        card = scorer.build(graph)
        assert card.overall == 0

    def test_grade_a_at_90(self):
        # 1 high (penalty=10) → score=90 → A
        graph = _graph_with_findings([[_finding("SEC-002", Severity.high)]])
        scorer = Scorer()
        card = scorer.build(graph)
        assert card.overall == 90
        assert card.overall_grade == "A"

    def test_grade_f_below_60(self):
        # 3 critical (penalty=60) → score=40 → F
        findings = [_finding(f"SEC-{i:03d}", Severity.critical) for i in range(3)]
        graph = _graph_with_findings([findings])
        scorer = Scorer()
        card = scorer.build(graph)
        assert card.overall == 40
        assert card.overall_grade == "F"

    def test_category_scores_independent(self):
        # SEC-001 is in Security category, SEC-002 is in Encryption
        graph = _graph_with_findings([
            [_finding("SEC-001", Severity.critical), _finding("SEC-002", Severity.high)]
        ])
        scorer = Scorer()
        card = scorer.build(graph)
        sec_cat = next(c for c in card.categories if c.name == "Security")
        enc_cat = next(c for c in card.categories if c.name == "Encryption")
        assert sec_cat.finding_count == 1
        assert enc_cat.finding_count == 1
        assert sec_cat.score == 80  # 1 critical = -20
        assert enc_cat.score == 90  # 1 high = -10

    def test_top_issues_sorted_severity(self):
        findings = [
            _finding("SEC-010", Severity.info),
            _finding("SEC-001", Severity.critical),
            _finding("SEC-002", Severity.high),
        ]
        graph = _graph_with_findings([findings])
        scorer = Scorer()
        card = scorer.build(graph)
        assert card.top_issues[0].severity == Severity.critical
        assert card.top_issues[1].severity == Severity.high
        assert card.top_issues[2].severity == Severity.info

    def test_top_issues_max_5(self):
        findings = [_finding(f"SEC-{i:03d}", Severity.medium) for i in range(10)]
        graph = _graph_with_findings([findings])
        scorer = Scorer()
        card = scorer.build(graph)
        assert len(card.top_issues) == 5

    def test_scorecard_html_under_50kb(self):
        findings = [_finding(f"SEC-{i:03d}", Severity.medium) for i in range(5)]
        graph = _graph_with_findings([findings])
        scorer = Scorer()
        card = scorer.build(graph)
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "scorecard.html"
            export_scorecard(card, out)
            size = out.stat().st_size
            assert size < 50_000, f"Scorecard HTML is {size} bytes, expected <50KB"
            content = out.read_text()
            assert "InfraCanvas Score" in content
            assert "infracanvas.dev" in content
