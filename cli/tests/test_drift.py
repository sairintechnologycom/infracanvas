"""Tests for the drift analyzer (T-016)."""

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
