"""Tests for FlowMap NET-* network findings (FDM-03, NFN-01 partial — 3a cloud-only).

Locks the Phase 3a network security rule catalogue:
  - 6 AWS: NET-001..NET-006
  - 5 Azure: NET-007, NET-008, NET-009, NET-011, NET-012

NET-010 is reserved for Phase 3b (ASY-03 — stateful firewall on one path,
requires path-dependent analysis) and MUST NOT be present in 3a.

Each NET rule is exercised with a crafted positive fixture (must fire) and a
crafted negative fixture (must stay silent). Rules are auto-discovered by
``load_rules()`` via ``rglob('*.yaml')`` — zero engine code changes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from infracanvas.graph.models import ResourceGraph, ResourceNode, Severity
from infracanvas.security.engine import evaluate_all
from infracanvas.security.loader import load_rules

FIXTURES = Path(__file__).parent / "fixtures" / "flowmap" / "rules"

with open(FIXTURES / "aws_net_fixtures.json") as _f:
    AWS_FIX = json.load(_f)
with open(FIXTURES / "azure_net_fixtures.json") as _f:
    AZ_FIX = json.load(_f)

AWS_NET_IDS = ["NET-001", "NET-002", "NET-003", "NET-004", "NET-005", "NET-006"]
AZURE_NET_IDS = ["NET-007", "NET-008", "NET-009", "NET-011", "NET-012"]
ALL_NET_IDS_3A = AWS_NET_IDS + AZURE_NET_IDS

DOCUMENTED_OPERATORS = {
    "equals",
    "not_equals",
    "in",
    "not_in",
    "exists",
    "not_exists",
    "contains",
    "matches_cidr",
    "list_contains_cidr",
    "any_equals",
}


def _node_from_fixture(data: dict) -> ResourceNode:
    return ResourceNode(**data)


def _evaluate_single(node: ResourceNode) -> ResourceNode:
    """Run all security rules against a one-node graph and return the node."""
    graph = ResourceGraph(nodes=[node])
    graph = evaluate_all(graph)
    return graph.nodes[0]


class TestRuleLoader:
    """NET-* YAML rules must be discovered by the existing rglob loader."""

    def test_loads_all_net_rules(self):
        rules = load_rules()
        ids = {r.id for r in rules}
        for nid in ALL_NET_IDS_3A:
            assert nid in ids, f"Missing rule {nid}"

    def test_net_010_reserved_for_phase_3b(self):
        rules = load_rules()
        ids = {r.id for r in rules}
        assert "NET-010" not in ids, (
            "NET-010 is reserved for Phase 3b (ASY-03 — stateful firewall on "
            "one path); it must NOT ship in 3a (path-dependent)"
        )

    def test_net_rules_have_valid_severities(self):
        net = [r for r in load_rules() if r.id.startswith("NET-")]
        assert net, "No NET-* rules loaded"
        for rule in net:
            assert rule.severity in Severity, (
                f"{rule.id} has invalid severity {rule.severity}"
            )

    def test_net_rules_use_documented_operators(self):
        net = [r for r in load_rules() if r.id.startswith("NET-")]
        for rule in net:
            assert rule.condition.operator in DOCUMENTED_OPERATORS, (
                f"{rule.id} uses undocumented operator "
                f"{rule.condition.operator!r}"
            )

    def test_net_rules_have_framework_ids(self):
        net = [r for r in load_rules() if r.id.startswith("NET-")]
        for rule in net:
            assert rule.framework_ids, f"{rule.id} missing framework_ids"

    def test_net_rules_have_required_fields(self):
        net = [r for r in load_rules() if r.id.startswith("NET-")]
        for rule in net:
            assert rule.id
            assert rule.title
            assert rule.resource_types
            assert rule.condition
            assert rule.condition.attribute
            assert rule.condition.operator
            assert rule.remediation
            assert rule.description


class TestNetworkRuleEvaluation:
    """Each NET-* rule must fire on its positive fixture and stay silent on its negative."""

    @pytest.mark.parametrize("rule_id", AWS_NET_IDS)
    def test_aws_rule_fires_on_positive(self, rule_id: str):
        fixture = AWS_FIX[f"{rule_id}_positive"]
        node = _evaluate_single(_node_from_fixture(fixture))
        findings = [f for f in node.findings if f.rule_id == rule_id]
        assert findings, f"{rule_id} did not fire on positive fixture"
        assert findings[0].source == "security"
        assert findings[0].framework_ids

    @pytest.mark.parametrize("rule_id", AWS_NET_IDS)
    def test_aws_rule_silent_on_negative(self, rule_id: str):
        fixture = AWS_FIX[f"{rule_id}_negative"]
        node = _evaluate_single(_node_from_fixture(fixture))
        findings = [f for f in node.findings if f.rule_id == rule_id]
        assert not findings, (
            f"{rule_id} fired on negative fixture (false positive): "
            f"{[f.evidence for f in findings]}"
        )

    @pytest.mark.parametrize("rule_id", AZURE_NET_IDS)
    def test_azure_rule_fires_on_positive(self, rule_id: str):
        fixture = AZ_FIX[f"{rule_id}_positive"]
        node = _evaluate_single(_node_from_fixture(fixture))
        findings = [f for f in node.findings if f.rule_id == rule_id]
        assert findings, f"{rule_id} did not fire on positive fixture"
        assert findings[0].source == "security"
        assert findings[0].framework_ids

    @pytest.mark.parametrize("rule_id", AZURE_NET_IDS)
    def test_azure_rule_silent_on_negative(self, rule_id: str):
        fixture = AZ_FIX[f"{rule_id}_negative"]
        node = _evaluate_single(_node_from_fixture(fixture))
        findings = [f for f in node.findings if f.rule_id == rule_id]
        assert not findings, (
            f"{rule_id} fired on negative fixture (false positive): "
            f"{[f.evidence for f in findings]}"
        )
