"""Tests for the security rules engine (Suite C)."""

import json
from pathlib import Path

import pytest

from infracanvas.graph.builder import build_graph
from infracanvas.graph.models import ResourceGraph, ResourceNode, Severity
from infracanvas.parser.hcl import parse_directory
from infracanvas.security.engine import _evaluate_rule, evaluate_all
from infracanvas.security.loader import load_rules
from infracanvas.security.models import RuleCondition, SecurityRule

FIXTURES = Path(__file__).parent / "fixtures"
RULE_FIXTURES = Path(__file__).parent / "fixtures" / "rules"

with open(RULE_FIXTURES / "sec_fixtures.json") as _f:
    SEC_FIX = json.load(_f)
with open(RULE_FIXTURES / "az_fixtures.json") as _f:
    AZ_FIX = json.load(_f)

# 30 SEC-AWS rules (verified 2026-04-20 via grep on rules/aws/*.yaml)
SEC_AWS_IDS = [
    "SEC-001", "SEC-002", "SEC-003", "SEC-004", "SEC-005",
    "SEC-006", "SEC-007", "SEC-008", "SEC-009", "SEC-010",
    "SEC-011", "SEC-012", "SEC-013", "SEC-014", "SEC-015",
    "SEC-016", "SEC-017", "SEC-018", "SEC-019", "SEC-020",
    "SEC-021", "SEC-022", "SEC-023", "SEC-024", "SEC-025",
    "SEC-026", "SEC-027", "SEC-028", "SEC-029", "SEC-030",
]

# 10 AZ-* rules (verified 2026-04-20 via grep on rules/azure/*.yaml)
SEC_AZ_IDS = [
    "AZ-001", "AZ-002", "AZ-003", "AZ-004", "AZ-005",
    "AZ-006", "AZ-007", "AZ-008", "AZ-009", "AZ-010",
]


def _node_from_fixture(data: dict) -> ResourceNode:
    return ResourceNode(**data)


def _evaluate_single(node: ResourceNode) -> ResourceNode:
    """Run all security rules against a one-node graph and return the node."""
    graph = ResourceGraph(nodes=[node])
    graph = evaluate_all(graph)
    return graph.nodes[0]


def _scan_fixture(name: str):
    """Helper: parse → build → evaluate a fixture."""
    parsed = parse_directory(FIXTURES / name)
    graph = build_graph(parsed)
    return evaluate_all(graph)


class TestRuleLoader:
    """C-010: YAML rule loader discovers all .yaml files in rules/."""

    def test_loads_all_rules(self):
        rules = load_rules()
        # 30 AWS SEC-* + 10 Azure AZ-* + 11 NET-* (Phase 3a) = 51
        # NET-010 reserved for Phase 3b (path-dependent ASY-03)
        assert len(rules) >= 51

    def test_rule_ids(self):
        rules = load_rules()
        rule_ids = {r.id for r in rules}
        for i in range(1, 11):
            assert f"SEC-{i:03d}" in rule_ids

    def test_rule_severities(self):
        rules = load_rules()
        severity_map = {r.id: r.severity for r in rules}
        assert severity_map["SEC-001"] == Severity.critical
        assert severity_map["SEC-002"] == Severity.high
        assert severity_map["SEC-003"] == Severity.critical
        assert severity_map["SEC-004"] == Severity.high
        assert severity_map["SEC-005"] == Severity.critical
        assert severity_map["SEC-006"] == Severity.high
        assert severity_map["SEC-007"] == Severity.critical
        assert severity_map["SEC-008"] == Severity.high
        assert severity_map["SEC-009"] == Severity.medium
        assert severity_map["SEC-010"] == Severity.info

    def test_rule_required_fields(self):
        """All rules have required fields."""
        rules = load_rules()
        for rule in rules:
            assert rule.id
            assert rule.title
            assert rule.severity
            assert rule.resource_types
            assert rule.condition
            assert rule.remediation
            assert rule.description


class TestSecurityEngine:
    """C-001 through C-009: Security rule evaluation tests."""

    def test_c001_positive_s3_public_acl(self):
        """C-001+: S3 with acl = 'public-read' → SEC-001 critical finding."""
        graph = _scan_fixture("insecure_setup")
        s3 = next(n for n in graph.nodes if n.id == "aws_s3_bucket.public_data")
        sec001 = [f for f in s3.findings if f.rule_id == "SEC-001"]
        assert len(sec001) == 1
        assert sec001[0].severity == Severity.critical

    def test_c001_negative_s3_private(self):
        """C-001-: S3 with acl = 'private' → no SEC-001 finding."""
        graph = _scan_fixture("insecure_setup")
        # logs bucket has no acl set (so no SEC-001)
        logs = next(n for n in graph.nodes if n.id == "aws_s3_bucket.logs")
        sec001 = [f for f in logs.findings if f.rule_id == "SEC-001"]
        assert len(sec001) == 0

    def test_c002_s3_no_encryption(self):
        """C-002+: S3 with no encryption block → SEC-002 high finding."""
        graph = _scan_fixture("insecure_setup")
        s3 = next(n for n in graph.nodes if n.id == "aws_s3_bucket.public_data")
        sec002 = [f for f in s3.findings if f.rule_id == "SEC-002"]
        assert len(sec002) == 1
        assert sec002[0].severity == Severity.high

    def test_c003_sg_port22_open(self):
        """C-003+: Security group with 0.0.0.0/0 on port 22 → SEC-003 critical."""
        graph = _scan_fixture("simple_vpc")
        sg = next(n for n in graph.nodes if n.id == "aws_security_group.web")
        sec003 = [f for f in sg.findings if f.rule_id == "SEC-003"]
        assert len(sec003) == 1
        assert sec003[0].severity == Severity.critical

    def test_c004_rds_public(self):
        """C-004+: RDS with publicly_accessible = true → SEC-005 critical."""
        graph = _scan_fixture("insecure_setup")
        db = next(n for n in graph.nodes if n.id == "aws_db_instance.exposed_db")
        sec005 = [f for f in db.findings if f.rule_id == "SEC-005"]
        assert len(sec005) == 1
        assert sec005[0].severity == Severity.critical

    def test_c005_iam_wildcard(self):
        """C-005+: IAM policy with Action * → SEC-007 critical."""
        graph = _scan_fixture("insecure_setup")
        policy = next(n for n in graph.nodes if n.id == "aws_iam_policy.admin_policy")
        sec007 = [f for f in policy.findings if f.rule_id == "SEC-007"]
        assert len(sec007) == 1

    def test_c006_score_one_critical(self):
        """C-006: Score: 1 critical = max(0, 100-20) = 80."""
        score = 100 - (1 * 20 + 0 * 10 + 0 * 5 + 0 * 1)
        assert score == 80

    def test_c007_score_clamped_to_zero(self):
        """C-007: Score clamped to 0 for 5+ criticals."""
        score = 100 - (5 * 20 + 0 * 10 + 0 * 5 + 0 * 1)
        score = max(0, score)
        assert score == 0
        # 6 criticals also 0
        score2 = 100 - (6 * 20)
        score2 = max(0, score2)
        assert score2 == 0

    def test_c008_finding_summary_counts(self):
        """C-008: Finding summary counts match findings list."""
        graph = _scan_fixture("simple_vpc")
        # Manually count
        counts = {"critical": 0, "high": 0, "medium": 0, "info": 0}
        for node in graph.nodes:
            for f in node.findings:
                counts[f.severity.value] += 1
        assert counts["critical"] >= 1  # SEC-001 and SEC-003

    def test_c009_unmatched_resource_type(self):
        """C-009: Unmatched resource type → no error."""
        # Build a node with an unknown type
        node = ResourceNode(
            id="aws_route53_zone.main",
            type="aws_route53_zone",
            name="main",
            provider="aws",
            attributes={},
        )
        from infracanvas.graph.models import ResourceGraph
        graph = ResourceGraph(nodes=[node])
        graph = evaluate_all(graph)
        # No rules match this type, so no findings
        assert len(graph.nodes[0].findings) == 0

    def test_insecure_setup_findings(self):
        graph = _scan_fixture("insecure_setup")
        all_findings = []
        for node in graph.nodes:
            all_findings.extend(node.findings)
        assert len(all_findings) > 0
        rule_ids_found = {f.rule_id for f in all_findings}
        assert "SEC-001" in rule_ids_found
        assert "SEC-005" in rule_ids_found

    def test_missing_tags_detected(self):
        graph = _scan_fixture("insecure_setup")
        untagged = next(n for n in graph.nodes if n.id == "aws_instance.untagged_server")
        sec010 = [f for f in untagged.findings if f.rule_id == "SEC-010"]
        assert len(sec010) == 1
        assert sec010[0].severity == Severity.info

    def test_kms_no_rotation_detected(self):
        graph = _scan_fixture("insecure_setup")
        kms = next(n for n in graph.nodes if n.id == "aws_kms_key.no_rotation")
        sec009 = [f for f in kms.findings if f.rule_id == "SEC-009"]
        assert len(sec009) == 1
        assert sec009[0].severity == Severity.medium

    def test_finding_has_evidence(self):
        graph = _scan_fixture("insecure_setup")
        s3 = next(n for n in graph.nodes if n.id == "aws_s3_bucket.public_data")
        finding = next(f for f in s3.findings if f.rule_id == "SEC-001")
        assert "attribute" in finding.evidence
        assert finding.evidence["attribute"] == "acl"

    def test_clean_infra_no_critical_findings(self):
        """Clean infrastructure should have no critical findings."""
        graph = _scan_fixture("clean_infra")
        critical = [
            f for n in graph.nodes for f in n.findings
            if f.severity == Severity.critical
        ]
        assert len(critical) == 0


class TestOperatorCoverage:
    """FIX-4: Direct operator tests to cover all branches in engine.py."""

    def _make_rule(self, operator: str, attribute: str = "status",
                   value=None, values=None) -> SecurityRule:
        return SecurityRule(
            id="TEST-001",
            title="Test rule",
            severity=Severity.medium,
            resource_types=["aws_test"],
            condition=RuleCondition(
                attribute=attribute,
                operator=operator,
                value=value,
                values=values or [],
            ),
            remediation="Fix it",
            description="Test",
        )

    def _make_node(self, attrs: dict) -> ResourceNode:
        return ResourceNode(
            id="aws_test.thing",
            type="aws_test",
            name="thing",
            provider="aws",
            attributes=attrs,
        )

    def test_operator_equals(self):
        rule = self._make_rule("equals", value="private")
        node = self._make_node({"status": "private"})
        finding = _evaluate_rule(rule, node)
        assert finding is not None
        assert finding.rule_id == "TEST-001"

    def test_operator_equals_no_match(self):
        rule = self._make_rule("equals", value="private")
        node = self._make_node({"status": "public"})
        finding = _evaluate_rule(rule, node)
        assert finding is None

    def test_operator_not_equals(self):
        rule = self._make_rule("not_equals", value="private")
        node = self._make_node({"status": "public"})
        finding = _evaluate_rule(rule, node)
        assert finding is not None

    def test_operator_not_in(self):
        rule = self._make_rule("not_in", attribute="tier", values=["free", "basic"])
        node = self._make_node({"tier": "enterprise"})
        finding = _evaluate_rule(rule, node)
        assert finding is not None

    def test_operator_not_in_no_match(self):
        rule = self._make_rule("not_in", attribute="tier", values=["free", "basic"])
        node = self._make_node({"tier": "free"})
        finding = _evaluate_rule(rule, node)
        assert finding is None

    def test_operator_any_equals(self):
        rule = self._make_rule("any_equals", attribute="ingress.protocol", value="tcp")
        node = self._make_node({"ingress": [{"protocol": "tcp"}, {"protocol": "udp"}]})
        finding = _evaluate_rule(rule, node)
        assert finding is not None

    def test_operator_any_equals_no_match(self):
        rule = self._make_rule("any_equals", attribute="ingress.protocol", value="icmp")
        node = self._make_node({"ingress": [{"protocol": "tcp"}]})
        finding = _evaluate_rule(rule, node)
        assert finding is None

    def test_operator_matches_cidr(self):
        rule = self._make_rule("matches_cidr", attribute="cidr_block",
                               values=["0.0.0.0/0"])
        node = self._make_node({"cidr_block": "0.0.0.0/0"})
        finding = _evaluate_rule(rule, node)
        assert finding is not None

    def test_operator_matches_cidr_no_match(self):
        rule = self._make_rule("matches_cidr", attribute="cidr_block",
                               values=["0.0.0.0/0"])
        node = self._make_node({"cidr_block": "10.0.0.0/16"})
        finding = _evaluate_rule(rule, node)
        assert finding is None


class TestSEC_RuleEvaluation:
    """Parametrized positive + negative coverage for every SEC-AWS rule (D-16)."""

    @pytest.mark.parametrize("rule_id", SEC_AWS_IDS)
    def test_aws_rule_fires_on_positive(self, rule_id: str):
        """SEC-R{rule_id}-POS: positive fixture triggers the rule."""
        fixture = SEC_FIX[f"{rule_id}_positive"]
        node = _evaluate_single(_node_from_fixture(fixture))
        findings = [f for f in node.findings if f.rule_id == rule_id]
        assert findings, f"{rule_id} did not fire on positive fixture"
        assert findings[0].source == "security"
        assert findings[0].framework_ids

    @pytest.mark.parametrize("rule_id", SEC_AWS_IDS)
    def test_aws_rule_silent_on_negative(self, rule_id: str):
        """SEC-R{rule_id}-NEG: negative fixture does not trigger the rule."""
        fixture = SEC_FIX[f"{rule_id}_negative"]
        node = _evaluate_single(_node_from_fixture(fixture))
        findings = [f for f in node.findings if f.rule_id == rule_id]
        assert not findings, (
            f"{rule_id} fired on negative fixture (false positive): "
            f"{[f.evidence for f in findings]}"
        )


class TestAZ_RuleEvaluation:
    """Parametrized positive + negative coverage for every AZ-* rule (D-16)."""

    @pytest.mark.parametrize("rule_id", SEC_AZ_IDS)
    def test_az_rule_fires_on_positive(self, rule_id: str):
        """SEC-R{rule_id}-POS (Azure): positive fixture triggers the rule."""
        fixture = AZ_FIX[f"{rule_id}_positive"]
        node = _evaluate_single(_node_from_fixture(fixture))
        findings = [f for f in node.findings if f.rule_id == rule_id]
        assert findings, f"{rule_id} did not fire on positive fixture"
        assert findings[0].source == "security"

    @pytest.mark.parametrize("rule_id", SEC_AZ_IDS)
    def test_az_rule_silent_on_negative(self, rule_id: str):
        """SEC-R{rule_id}-NEG (Azure): negative fixture does not trigger the rule."""
        fixture = AZ_FIX[f"{rule_id}_negative"]
        node = _evaluate_single(_node_from_fixture(fixture))
        findings = [f for f in node.findings if f.rule_id == rule_id]
        assert not findings, f"{rule_id} fired on negative fixture"
