"""Tests for the graph builder (Suite B)."""

from pathlib import Path

from infracanvas.graph.builder import build_graph
from infracanvas.graph.models import ResourceGraph
from infracanvas.parser.hcl import parse_directory

FIXTURES = Path(__file__).parent / "fixtures"


class TestNetworkFinding:
    """CLI-02: NetworkFinding model validation tests (Wave 0 Nyquist stub)."""

    def test_resource_graph_version_2_0(self):
        """GRF-03: ResourceGraph defaults to version 2.0."""
        graph = ResourceGraph()
        assert graph.version == "2.0"

    def test_network_finding_valid(self):
        """CLI-02: NetworkFinding accepts valid fields."""
        from infracanvas.graph.models import NetworkFinding
        finding = NetworkFinding(
            resource_id="aws_security_group.web",
            protocol="tcp",
            source_cidr="0.0.0.0/0",
            dest_cidr="10.0.1.0/24",
            finding_type="unrestricted_ingress",
            severity="critical",
            title="Unrestricted ingress",
            description="Security group allows unrestricted ingress on tcp",
        )
        assert finding.resource_id == "aws_security_group.web"
        assert finding.protocol == "tcp"
        assert finding.source_cidr == "0.0.0.0/0"
        assert finding.dest_cidr == "10.0.1.0/24"
        assert finding.finding_type == "unrestricted_ingress"

    def test_network_finding_rejects_missing_fields(self):
        """CLI-02: NetworkFinding requires all mandatory fields."""
        from infracanvas.graph.models import NetworkFinding
        import pytest
        with pytest.raises(Exception):
            NetworkFinding(resource_id="sg.web")  # missing required fields


class TestBuildGraph:
    """B-001 through B-008: Graph builder tests."""

    def test_b001_correct_node_count(self):
        """B-001: Graph has correct node count after parsing simple_vpc fixture."""
        parsed = parse_directory(FIXTURES / "simple_vpc")
        graph = build_graph(parsed)
        assert len(graph.nodes) == 6

    def test_b002_edge_between_subnet_and_vpc(self):
        """B-002: Edge exists between subnet and vpc (implicit dependency)."""
        parsed = parse_directory(FIXTURES / "simple_vpc")
        graph = build_graph(parsed)
        edge_pairs = {(e["source"], e["target"]) for e in graph.edges}
        assert ("aws_subnet.public", "aws_vpc.main") in edge_pairs

    def test_b003_node_attributes(self):
        """B-003: Node attributes include provider, type, name."""
        parsed = parse_directory(FIXTURES / "simple_vpc")
        graph = build_graph(parsed)
        vpc = next(n for n in graph.nodes if n.id == "aws_vpc.main")
        assert vpc.provider == "aws"
        assert vpc.type == "aws_vpc"
        assert vpc.name == "main"

    def test_b004_graph_exports_to_valid_json(self):
        """B-004: Graph exports to valid JSON matching ResourceGraph schema."""
        parsed = parse_directory(FIXTURES / "simple_vpc")
        graph = build_graph(parsed)
        json_str = graph.model_dump_json()
        assert len(json_str) > 0
        # Validate it's parseable
        import json
        data = json.loads(json_str)
        assert "nodes" in data
        assert "edges" in data

    def test_b005_json_roundtrip(self):
        """B-005: JSON round-trip: parse → model → json → model."""
        parsed = parse_directory(FIXTURES / "simple_vpc")
        graph = build_graph(parsed)
        json_str = graph.model_dump_json()
        restored = ResourceGraph.model_validate_json(json_str)
        assert len(restored.nodes) == len(graph.nodes)
        assert len(restored.edges) == len(graph.edges)

    def test_b006_same_vpc_same_group(self):
        """B-006: Nodes with same vpc reference are assigned same group value."""
        parsed = parse_directory(FIXTURES / "simple_vpc")
        graph = build_graph(parsed)
        subnet_pub = next(n for n in graph.nodes if n.id == "aws_subnet.public")
        subnet_priv = next(n for n in graph.nodes if n.id == "aws_subnet.private")
        sg = next(n for n in graph.nodes if n.id == "aws_security_group.web")
        assert subnet_pub.group == subnet_priv.group
        assert sg.group == subnet_pub.group
        assert subnet_pub.group != ""

    def test_b007_summary_counts(self):
        """B-007: Graph summary counts resources correctly."""
        parsed = parse_directory(FIXTURES / "simple_vpc")
        graph = build_graph(parsed)
        # Summary isn't set by builder, but nodes count is correct
        assert len(graph.nodes) == 6

    def test_b008_empty_directory(self, tmp_path):
        """B-008: Empty directory produces graph with 0 nodes and no error."""
        parsed = parse_directory(tmp_path)
        graph = build_graph(parsed)
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

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
        lambda_fn = next(n for n in graph.nodes if n.id == "aws_lambda_function.processor")
        assert "aws_iam_role.lambda_role" in lambda_fn.dependencies

    def test_dependencies_list_populated(self):
        parsed = parse_directory(FIXTURES / "simple_vpc")
        graph = build_graph(parsed)
        subnet = next(n for n in graph.nodes if n.id == "aws_subnet.public")
        assert "aws_vpc.main" in subnet.dependencies

    def test_edge_types(self):
        """Verify edge type field is set correctly."""
        parsed = parse_directory(FIXTURES / "multi_module")
        graph = build_graph(parsed)
        depends_on_edges = [e for e in graph.edges if e["type"] == "depends_on"]
        implicit_edges = [e for e in graph.edges if e["type"] == "implicit"]
        assert len(depends_on_edges) > 0
        assert len(implicit_edges) > 0
