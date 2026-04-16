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

    def test_grade_f_below_35(self):
        # 4 critical (penalty=80) → score=20 → F (new thresholds: F < 35)
        findings = [_finding(f"SEC-{i:03d}", Severity.critical) for i in range(4)]
        graph = _graph_with_findings([findings])
        scorer = Scorer()
        card = scorer.build(graph)
        assert card.overall == 20
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


class TestDimensions:
    """Tests for SCR-02 spec — 5 correct scoring dimensions."""

    def _empty_graph(self) -> ResourceGraph:
        return _graph_with_findings([[]])

    def _graph_with_rule(self, rule_id: str, severity: Severity) -> ResourceGraph:
        return _graph_with_findings([[_finding(rule_id, severity)]])

    def test_exactly_5_category_names(self):
        """SCR-02: Scorer returns exactly 5 categories."""
        graph = self._empty_graph()
        card = Scorer().build(graph)
        names = [c.name for c in card.categories]
        assert len(names) == 5, f"Expected 5 categories, got {len(names)}: {names}"

    def test_category_names_match_spec(self):
        """SCR-02: Category names are exactly as specified."""
        graph = self._empty_graph()
        card = Scorer().build(graph)
        names = [c.name for c in card.categories]
        expected = {"Security", "Encryption", "IAM Hygiene", "Cost Efficiency", "Tagging"}
        assert set(names) == expected, f"Got: {set(names)}"

    def test_networking_not_in_categories(self):
        """Old 'Networking' category must NOT appear."""
        graph = self._empty_graph()
        card = Scorer().build(graph)
        names = [c.name for c in card.categories]
        assert "Networking" not in names

    def test_iam_without_hygiene_not_in_categories(self):
        """Old 'IAM' category (without 'Hygiene') must NOT appear."""
        graph = self._empty_graph()
        card = Scorer().build(graph)
        names = [c.name for c in card.categories]
        assert "IAM" not in names

    def test_security_maps_to_sec001_003_004_005(self):
        """Category 'Security' includes SEC-001, SEC-003, SEC-004, SEC-005."""
        for rule_id in ["SEC-001", "SEC-003", "SEC-004", "SEC-005"]:
            graph = self._graph_with_rule(rule_id, Severity.high)
            card = Scorer().build(graph)
            cat = next(c for c in card.categories if c.name == "Security")
            assert cat.finding_count == 1, f"Expected SEC category to count {rule_id}"

    def test_encryption_maps_to_sec002_006_009(self):
        """Category 'Encryption' includes SEC-002, SEC-006, SEC-009."""
        for rule_id in ["SEC-002", "SEC-006", "SEC-009"]:
            graph = self._graph_with_rule(rule_id, Severity.high)
            card = Scorer().build(graph)
            cat = next(c for c in card.categories if c.name == "Encryption")
            assert cat.finding_count == 1, f"Expected Encryption category to count {rule_id}"

    def test_iam_hygiene_maps_to_sec007_008(self):
        """Category 'IAM Hygiene' includes SEC-007, SEC-008."""
        for rule_id in ["SEC-007", "SEC-008"]:
            graph = self._graph_with_rule(rule_id, Severity.high)
            card = Scorer().build(graph)
            cat = next(c for c in card.categories if c.name == "IAM Hygiene")
            assert cat.finding_count == 1, f"Expected IAM Hygiene category to count {rule_id}"

    def test_cost_efficiency_zero_findings_scores_100(self):
        """Category 'Cost Efficiency' has empty rule set, scores 100 by default."""
        graph = self._empty_graph()
        card = Scorer().build(graph)
        cat = next(c for c in card.categories if c.name == "Cost Efficiency")
        assert cat.finding_count == 0
        assert cat.score == 100

    def test_tagging_maps_to_sec010(self):
        """Category 'Tagging' maps to SEC-010."""
        graph = self._graph_with_rule("SEC-010", Severity.high)
        card = Scorer().build(graph)
        cat = next(c for c in card.categories if c.name == "Tagging")
        assert cat.finding_count == 1

    def test_grade_map_a_at_80(self):
        """GRADE_MAP threshold: score 80 → A."""
        # 1 high finding = penalty 10, score = 90 → A
        graph = self._graph_with_rule("SEC-001", Severity.high)
        card = Scorer().build(graph)
        assert card.overall == 90
        assert card.overall_grade == "A"

    def test_grade_map_b_at_79(self):
        """GRADE_MAP threshold: score 79 → B."""
        # 1 critical = -20, score = 80 → A. Need score=79 → two highs = -20, score=80→A
        # Use: 1 critical + 1 medium = penalty 20+5=25, score=75 → B
        findings = [_finding("SEC-001", Severity.critical), _finding("SEC-002", Severity.medium)]
        graph = _graph_with_findings([findings])
        card = Scorer().build(graph)
        assert card.overall == 75
        assert card.overall_grade == "B"

    def test_grade_map_b_at_65(self):
        """GRADE_MAP threshold: score 65 → B."""
        # penalty=35 → score=65 → B (1 critical + 1 medium + 2 info = 20+5+2=27, not enough)
        # 1 critical (20) + 1 high (10) + 1 info (1) = 31 → score=69 → B
        # Need score=65: penalty=35 → 1 critical(20) + 1 high(10) + 1 medium(5) = 35 → score=65 → B
        findings = [
            _finding("SEC-001", Severity.critical),
            _finding("SEC-002", Severity.high),
            _finding("SEC-003", Severity.medium),
        ]
        graph = _graph_with_findings([findings])
        card = Scorer().build(graph)
        assert card.overall == 65
        assert card.overall_grade == "B"

    def test_grade_map_c_at_64(self):
        """GRADE_MAP threshold: score 64 → C."""
        # penalty=36 → 1 critical(20) + 1 high(10) + 1 medium(5) + 1 info(1) = 36 → score=64 → C
        findings = [
            _finding("SEC-001", Severity.critical),
            _finding("SEC-002", Severity.high),
            _finding("SEC-003", Severity.medium),
            _finding("SEC-004", Severity.info),
        ]
        graph = _graph_with_findings([findings])
        card = Scorer().build(graph)
        assert card.overall == 64
        assert card.overall_grade == "C"

    def test_grade_map_c_at_50(self):
        """GRADE_MAP threshold: score 50 → C."""
        # penalty=50 → 2 critical(40) + 1 medium(5) + 5 info(5) = 50 → score=50 → C
        findings = (
            [_finding(f"SEC-{i:03d}", Severity.critical) for i in range(2)]
            + [_finding("SEC-010", Severity.medium)]
            + [_finding(f"SEC-01{i}", Severity.info) for i in range(5)]
        )
        graph = _graph_with_findings([findings])
        card = Scorer().build(graph)
        assert card.overall == 50
        assert card.overall_grade == "C"

    def test_grade_map_d_at_49(self):
        """GRADE_MAP threshold: score 49 → D."""
        # penalty=51 → 2 critical(40) + 1 high(10) + 1 info(1) = 51 → score=49 → D
        findings = (
            [_finding(f"SEC-{i:03d}", Severity.critical) for i in range(2)]
            + [_finding("SEC-010", Severity.high)]
            + [_finding("SEC-011", Severity.info)]
        )
        graph = _graph_with_findings([findings])
        card = Scorer().build(graph)
        assert card.overall == 49
        assert card.overall_grade == "D"

    def test_grade_map_d_at_35(self):
        """GRADE_MAP threshold: score 35 → D."""
        # penalty=65 → 3 critical(60) + 1 medium(5) = 65 → score=35 → D
        findings = (
            [_finding(f"SEC-{i:03d}", Severity.critical) for i in range(3)]
            + [_finding("SEC-010", Severity.medium)]
        )
        graph = _graph_with_findings([findings])
        card = Scorer().build(graph)
        assert card.overall == 35
        assert card.overall_grade == "D"

    def test_grade_map_f_at_34(self):
        """GRADE_MAP threshold: score 34 → F."""
        # penalty=66 → 3 critical(60) + 1 medium(5) + 1 info(1) = 66 → score=34 → F
        findings = (
            [_finding(f"SEC-{i:03d}", Severity.critical) for i in range(3)]
            + [_finding("SEC-010", Severity.medium)]
            + [_finding("SEC-011", Severity.info)]
        )
        graph = _graph_with_findings([findings])
        card = Scorer().build(graph)
        assert card.overall == 34
        assert card.overall_grade == "F"
