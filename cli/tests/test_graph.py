"""Tests for the graph builder."""

from pathlib import Path

from infracanvas.graph.builder import build_graph
from infracanvas.parser.hcl import parse_directory

FIXTURES = Path(__file__).parent / "fixtures"


class TestBuildGraph:
    def test_simple_vpc_nodes(self):
        parsed = parse_directory(FIXTURES / "simple_vpc")
        graph = build_graph(parsed)

        assert len(graph.nodes) == 5
        node_ids = {n.id for n in graph.nodes}
        assert "aws_vpc.main" in node_ids
        assert "aws_instance.web" in node_ids

    def test_simple_vpc_edges(self):
        parsed = parse_directory(FIXTURES / "simple_vpc")
        graph = build_graph(parsed)

        # There should be implicit edges from subnets to VPC
        edge_pairs = {(e["source"], e["target"]) for e in graph.edges}
        assert ("aws_subnet.public", "aws_vpc.main") in edge_pairs
        assert ("aws_subnet.private", "aws_vpc.main") in edge_pairs

    def test_provider_detection(self):
        parsed = parse_directory(FIXTURES / "simple_vpc")
        graph = build_graph(parsed)

        for node in graph.nodes:
            assert node.provider == "aws"

    def test_node_attributes_preserved(self):
        parsed = parse_directory(FIXTURES / "simple_vpc")
        graph = build_graph(parsed)

        vpc = next(n for n in graph.nodes if n.id == "aws_vpc.main")
        assert vpc.attributes["cidr_block"] == "10.0.0.0/16"

    def test_multi_module_explicit_deps(self):
        parsed = parse_directory(FIXTURES / "multi_module")
        graph = build_graph(parsed)

        instance = next(n for n in graph.nodes if n.id == "aws_instance.app")
        assert "aws_vpc.prod" in instance.dependencies

    def test_multi_module_implicit_deps(self):
        parsed = parse_directory(FIXTURES / "multi_module")
        graph = build_graph(parsed)

        # lambda_function references iam_role via role attribute
        lambda_fn = next(n for n in graph.nodes if n.id == "aws_lambda_function.processor")
        assert "aws_iam_role.lambda_role" in lambda_fn.dependencies

    def test_dependencies_list_populated(self):
        parsed = parse_directory(FIXTURES / "simple_vpc")
        graph = build_graph(parsed)

        subnet = next(n for n in graph.nodes if n.id == "aws_subnet.public")
        assert "aws_vpc.main" in subnet.dependencies

    def test_graph_serialization(self):
        parsed = parse_directory(FIXTURES / "simple_vpc")
        graph = build_graph(parsed)

        data = graph.model_dump()
        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)
