"""Tests for custom policy engine (POL-01, POL-02)."""

from pathlib import Path

from infracanvas.graph.models import ResourceGraph, ResourceNode
from infracanvas.security.engine import evaluate_all
from infracanvas.security.loader import load_policy_rules

FIXTURES = Path(__file__).parent / "fixtures" / "policies"


class TestPolicyLoader:
    def test_loads_yaml_from_directory(self):
        """POL-001-A: load_policy_rules() discovers .yaml files in policy dir."""
        rules = load_policy_rules(FIXTURES)
        assert len(rules) >= 2

    def test_empty_dir_returns_empty(self):
        """POL-001-B: Non-existent directory returns empty list."""
        rules = load_policy_rules(Path("/nonexistent"))
        assert rules == []


class TestPolicyEvaluation:
    def test_policy_source_injected(self):
        """POL-001-C: Findings from policy rules have source='policy'."""
        rules = load_policy_rules(FIXTURES)
        node = ResourceNode(
            id="aws_instance.web", type="aws_instance", name="web",
            provider="aws", attributes={},
        )
        graph = ResourceGraph(nodes=[node])
        graph = evaluate_all(graph, policy_rules=rules)
        policy_findings = [f for f in node.findings if f.source == "policy"]
        assert len(policy_findings) > 0

    def test_policy_finding_has_correct_rule_id(self):
        """POL-001-D: Policy findings carry the policy rule ID (POL-001)."""
        rules = load_policy_rules(FIXTURES)
        node = ResourceNode(
            id="aws_instance.web", type="aws_instance", name="web",
            provider="aws", attributes={},
        )
        graph = ResourceGraph(nodes=[node])
        graph = evaluate_all(graph, policy_rules=rules)
        policy_ids = {f.rule_id for f in node.findings if f.source == "policy"}
        assert "POL-001" in policy_ids

    def test_security_and_policy_findings_coexist(self):
        """POL-001-E: Security rule findings and policy findings both present."""
        rules = load_policy_rules(FIXTURES)
        # S3 bucket without encryption + missing tags = both security + policy findings
        node = ResourceNode(
            id="aws_s3_bucket.data", type="aws_s3_bucket", name="data",
            provider="aws", attributes={"acl": "public-read"},
        )
        graph = ResourceGraph(nodes=[node])
        graph = evaluate_all(graph, policy_rules=rules)
        sources = {f.source for f in node.findings}
        assert "security" in sources
        assert "policy" in sources
