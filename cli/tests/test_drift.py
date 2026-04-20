"""Tests for the drift analyzer (T-016)."""

import pytest

from infracanvas.drift.analyzer import DriftAnalyzer
from infracanvas.graph.models import (
    DriftStatus,
    GraphSummary,
    ResourceGraph,
    ResourceNode,
)
from infracanvas.parser.plan import PlanChange


def _make_graph(node_ids: list[str]) -> ResourceGraph:
    nodes = [
        ResourceNode(
            id=nid,
            type=nid.split(".")[0],
            name=nid.split(".")[1],
            provider="aws",
        )
        for nid in node_ids
    ]
    return ResourceGraph(nodes=nodes, summary=GraphSummary(total_resources=len(nodes)))


def _make_change(addr: str, action: DriftStatus) -> PlanChange:
    parts = addr.split(".")
    return PlanChange(
        resource_address=addr,
        resource_type=parts[0],
        resource_name=parts[1],
        action=action,
    )


class TestDriftAnalyzer:
    def test_apply_marks_node_drift(self):
        graph = _make_graph(["aws_instance.web"])
        changes = [_make_change("aws_instance.web", DriftStatus.changed)]
        analyzer = DriftAnalyzer()
        result = analyzer.apply(graph, changes)
        assert result.nodes[0].drift == DriftStatus.changed

    def test_apply_creates_stub_for_added(self):
        graph = _make_graph(["aws_instance.web"])
        changes = [_make_change("aws_nat_gateway.new", DriftStatus.added)]
        analyzer = DriftAnalyzer()
        result = analyzer.apply(graph, changes)
        assert len(result.nodes) == 2
        stub = next(n for n in result.nodes if n.id == "aws_nat_gateway.new")
        assert stub.drift == DriftStatus.added

    def test_apply_summary_counts_correct(self):
        graph = _make_graph(["aws_instance.a", "aws_instance.b", "aws_s3_bucket.c"])
        changes = [
            _make_change("aws_instance.a", DriftStatus.changed),
            _make_change("aws_s3_bucket.c", DriftStatus.deleted),
            _make_change("aws_nat_gateway.new", DriftStatus.added),
        ]
        analyzer = DriftAnalyzer()
        result = analyzer.apply(graph, changes)
        assert result.summary.drift["added"] == 1
        assert result.summary.drift["changed"] == 1
        assert result.summary.drift["deleted"] == 1

    def test_apply_no_changes_all_unchanged(self):
        graph = _make_graph(["aws_instance.web"])
        analyzer = DriftAnalyzer()
        result = analyzer.apply(graph, [])
        assert result.nodes[0].drift == DriftStatus.unchanged
        assert result.summary.drift["added"] == 0
        assert result.summary.drift["changed"] == 0
        assert result.summary.drift["deleted"] == 0
        # 5-key contract per Plan 02
        assert result.summary.drift["unchanged"] == 1
        assert result.summary.drift["shadow"] == 0


@pytest.mark.parametrize("mix", [
    [],
    [("aws_instance.a", DriftStatus.changed)],
    [("aws_instance.a", DriftStatus.changed),
     ("aws_s3_bucket.b", DriftStatus.deleted)],
    [("aws_instance.a", DriftStatus.changed),
     ("aws_s3_bucket.b", DriftStatus.deleted),
     ("aws_nat_gateway.new", DriftStatus.added)],
    [("aws_instance.a", DriftStatus.shadow)],
    [("aws_instance.a", DriftStatus.changed),
     ("aws_s3_bucket.ghost", DriftStatus.shadow),
     ("aws_nat_gateway.new", DriftStatus.added)],
])
def test_drift_counts_sum_to_node_count(mix):
    """DFT-INV-01: sum(drift_counts.values()) == len(graph.nodes) across all mixes."""
    # Nodes that are being mutated (changed/deleted/shadow) already exist in baseline;
    # added nodes are created as stubs by DriftAnalyzer.
    baseline_ids = [addr for addr, action in mix if action != DriftStatus.added] or ["aws_instance.baseline"]
    # ensure at least one unchanged node is present in some fixtures to exercise all 5 keys
    if "aws_instance.untouched" not in baseline_ids:
        baseline_ids = baseline_ids + ["aws_instance.untouched"]
    graph = _make_graph(baseline_ids)
    # For shadow mix, we have to pre-set node.drift to shadow (since PlanChange
    # doesn't emit shadow; shadow comes from the shadow detector, not the plan).
    for addr, action in mix:
        if action == DriftStatus.shadow:
            node = next((n for n in graph.nodes if n.id == addr), None)
            if node is not None:
                node.drift = DriftStatus.shadow
    # Only feed non-shadow changes to DriftAnalyzer.apply() (shadow is pre-set).
    changes = [
        _make_change(addr, action)
        for addr, action in mix
        if action != DriftStatus.shadow
    ]
    graph = DriftAnalyzer().apply(graph, changes)
    assert sum(graph.summary.drift.values()) == len(graph.nodes), (
        f"invariant broken: drift={graph.summary.drift}, "
        f"node_count={len(graph.nodes)}"
    )
    # Also assert all 5 keys are present (Plan 02 contract)
    assert set(graph.summary.drift.keys()) == {
        "added", "changed", "deleted", "unchanged", "shadow"
    }
