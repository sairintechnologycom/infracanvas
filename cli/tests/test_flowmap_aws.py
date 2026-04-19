"""Tests for AWS cloud-network FlowMap collector (AWS-01, AWS-02, AWS-03).

Mocks boto3 via sys.modules patch — tests are hermetic and do NOT require
`pip install 'infracanvas[flowmap]'` to run. Placebo-shaped JSON fixtures
(cli/tests/fixtures/flowmap/aws/) stand in for recorded AWS responses.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from infracanvas.flowmap.aws import collect_aws_network
from infracanvas.graph.models import ResourceGraph, ResourceNode

FIXTURES = Path(__file__).parent / "fixtures" / "flowmap" / "aws"


def _load_fixture(name: str) -> dict[str, Any]:
    with open(FIXTURES / name) as f:
        data: dict[str, Any] = json.load(f)
        return data


def _node(
    resource_type: str,
    name: str = "test",
    attrs: dict[str, Any] | None = None,
) -> ResourceNode:
    return ResourceNode(
        id=f"{resource_type}.{name}",
        type=resource_type,
        name=name,
        provider="aws",
        attributes=attrs or {},
    )


def _mock_session(
    tgw_data: dict[str, Any] | None = None,
    dx_data: dict[str, Any] | None = None,
    flow_logs: dict[str, Any] | None = None,
) -> tuple[MagicMock, MagicMock, MagicMock]:
    """Build a MagicMock boto3 module + ec2 + dx clients with placebo-backed responses."""
    tgw_data = tgw_data or _load_fixture("placebo_tgw.json")
    dx_data = dx_data or _load_fixture("placebo_dx.json")
    flow_logs = flow_logs or {"FlowLogs": []}

    ec2 = MagicMock()
    ec2.describe_transit_gateways.return_value = tgw_data["describe_transit_gateways"]
    ec2.describe_transit_gateway_attachments.return_value = (
        tgw_data["describe_transit_gateway_attachments"]
    )
    ec2.describe_transit_gateway_route_tables.return_value = (
        tgw_data["describe_transit_gateway_route_tables"]
    )
    ec2.search_transit_gateway_routes.return_value = tgw_data["search_transit_gateway_routes"]
    ec2.describe_vpn_connections.return_value = tgw_data["describe_vpn_connections"]
    ec2.describe_route_tables.return_value = {"RouteTables": []}
    ec2.describe_network_acls.return_value = {"NetworkAcls": []}
    ec2.describe_flow_logs.return_value = flow_logs

    dx = MagicMock()
    dx.describe_connections.return_value = dx_data["describe_connections"]
    dx.describe_virtual_interfaces.return_value = dx_data["describe_virtual_interfaces"]

    session = MagicMock()
    session.get_credentials.return_value = MagicMock()  # truthy
    session.client.side_effect = lambda svc, **kw: {"ec2": ec2, "directconnect": dx}[svc]

    boto3 = MagicMock()
    boto3.Session.return_value = session
    return boto3, ec2, dx


class TestImportGuards:
    def test_missing_boto3_raises(self) -> None:
        """AWS-01-A: RuntimeError when boto3 not installed."""
        with patch.dict("sys.modules", {"boto3": None}):
            with pytest.raises(RuntimeError, match="boto3 not installed"):
                collect_aws_network(ResourceGraph(), region="us-east-1")

    def test_missing_creds_raises(self) -> None:
        """AWS-01-B: RuntimeError when AWS credentials absent."""
        boto3, _, _ = _mock_session()
        boto3.Session.return_value.get_credentials.return_value = None
        with patch.dict("sys.modules", {"boto3": boto3}):
            with pytest.raises(RuntimeError, match="AWS credentials"):
                collect_aws_network(ResourceGraph(), region="us-east-1")


class TestCollectAwsNetwork:
    def test_collects_transit_gateways(self) -> None:
        """AWS-01: TGW + Name tag + AmazonSideAsn surface on graph.nodes."""
        boto3, _, _ = _mock_session()
        with patch.dict("sys.modules", {"boto3": boto3}):
            g = collect_aws_network(ResourceGraph(), region="us-east-1")
        tgw_nodes = [n for n in g.nodes if n.type == "aws_ec2_transit_gateway"]
        assert len(tgw_nodes) == 1
        assert tgw_nodes[0].name == "hybrid-primary"
        assert tgw_nodes[0].attributes["transit_gateway_id"] == "tgw-0a1b2c3d4e5f67890"
        assert tgw_nodes[0].attributes["amazon_side_asn"] == 64512
        # Real infra — no shadow_ prefix, drift unchanged
        assert not tgw_nodes[0].name.startswith("shadow_")

    def test_collects_tgw_attachments(self) -> None:
        """AWS-01: 3 attachments land (2 VPC + 1 VPN)."""
        boto3, _, _ = _mock_session()
        with patch.dict("sys.modules", {"boto3": boto3}):
            g = collect_aws_network(ResourceGraph(), region="us-east-1")
        atts = [n for n in g.nodes if n.type == "aws_ec2_transit_gateway_attachment"]
        assert len(atts) == 3
        resource_types = {n.attributes["resource_type"] for n in atts}
        assert resource_types == {"vpc", "vpn"}

    def test_collects_tgw_route_tables_with_routes(self) -> None:
        """AWS-01: route table includes 3 propagated/static routes in attributes."""
        boto3, _, _ = _mock_session()
        with patch.dict("sys.modules", {"boto3": boto3}):
            g = collect_aws_network(ResourceGraph(), region="us-east-1")
        rtbs = [n for n in g.nodes if n.type == "aws_ec2_transit_gateway_route_table"]
        assert len(rtbs) == 1
        routes = rtbs[0].attributes["routes"]
        assert len(routes) == 3

    def test_collects_vpn_connections(self) -> None:
        """AWS-01: VPN node surfaces with transit_gateway_id link."""
        boto3, _, _ = _mock_session()
        with patch.dict("sys.modules", {"boto3": boto3}):
            g = collect_aws_network(ResourceGraph(), region="us-east-1")
        vpns = [n for n in g.nodes if n.type == "aws_vpn_connection"]
        assert len(vpns) == 1
        assert vpns[0].attributes["transit_gateway_id"] == "tgw-0a1b2c3d4e5f67890"

    def test_collects_direct_connect(self) -> None:
        """AWS-02: 1 DX connection + 2 virtual interfaces with BGP ASN."""
        boto3, _, _ = _mock_session()
        with patch.dict("sys.modules", {"boto3": boto3}):
            g = collect_aws_network(ResourceGraph(), region="us-east-1")
        conns = [n for n in g.nodes if n.type == "aws_dx_connection"]
        vifs = [n for n in g.nodes if n.type == "aws_dx_virtual_interface"]
        assert len(conns) == 1
        assert len(vifs) == 2
        assert any(v.attributes["asn"] == 64520 for v in vifs)
        # VIF types recorded
        vif_types = {v.attributes["virtual_interface_type"] for v in vifs}
        assert vif_types == {"private", "transit"}

    def test_flow_log_metadata_attached_to_existing_vpc(self) -> None:
        """AWS-03: flow_logs metadata attaches to existing aws_vpc (no phantom VPC)."""
        boto3, ec2, _ = _mock_session(flow_logs={
            "FlowLogs": [{
                "FlowLogId": "fl-abc",
                "ResourceId": "vpc-0abc111",
                "LogGroupName": "/aws/vpc/prod",
                "LogDestinationType": "cloud-watch-logs",
                "TrafficType": "ALL",
                "LogFormat": "${version} ${account-id}",
            }]
        })
        graph = ResourceGraph(nodes=[_node("aws_vpc", "prod", {"vpc_id": "vpc-0abc111"})])
        with patch.dict("sys.modules", {"boto3": boto3}):
            g = collect_aws_network(graph, region="us-east-1")
        vpc_nodes = [n for n in g.nodes if n.type == "aws_vpc"]
        assert len(vpc_nodes) == 1  # no phantom VPC — only the pre-existing HCL-parsed one
        vpc_node = vpc_nodes[0]
        assert vpc_node.attributes["flow_log"]["log_group"] == "/aws/vpc/prod"
        assert vpc_node.attributes["flow_log"]["traffic_type"] == "ALL"
        assert vpc_node.attributes["flow_log"]["destination_type"] == "cloud-watch-logs"

    def test_api_failure_swallowed(self) -> None:
        """AWS-01: single describe_* raising does NOT abort full collection."""
        boto3, ec2, _ = _mock_session()
        ec2.describe_vpn_connections.side_effect = Exception("AccessDenied")
        with patch.dict("sys.modules", {"boto3": boto3}):
            g = collect_aws_network(ResourceGraph(), region="us-east-1")
        # TGW still collects despite VPN failure
        assert any(n.type == "aws_ec2_transit_gateway" for n in g.nodes)
        # VPN collection swallowed — no vpn_connection nodes
        assert not any(n.type == "aws_vpn_connection" for n in g.nodes)
        # DX still collected
        assert any(n.type == "aws_dx_connection" for n in g.nodes)

    def test_no_shadow_prefix_in_ids(self) -> None:
        """PATTERNS naming: FlowMap nodes are real infra, NEVER shadow_-prefixed."""
        boto3, _, _ = _mock_session()
        with patch.dict("sys.modules", {"boto3": boto3}):
            g = collect_aws_network(ResourceGraph(), region="us-east-1")
        for n in g.nodes:
            assert not n.name.startswith("shadow_"), f"Unexpected shadow_ prefix on {n.id}"
            local = n.id.split(".", 1)[1]
            assert not local.startswith("shadow_"), f"Unexpected shadow_ in id {n.id}"

    def test_region_propagates_to_nodes(self) -> None:
        """AWS-01: region kwarg propagates into every collected node."""
        boto3, _, _ = _mock_session()
        with patch.dict("sys.modules", {"boto3": boto3}):
            g = collect_aws_network(ResourceGraph(), region="eu-west-1")
        new_nodes = [n for n in g.nodes if n.provider == "aws"]
        assert len(new_nodes) > 0
        assert all(n.region == "eu-west-1" for n in new_nodes)

    def test_flowmap_cost_basis_tagged(self) -> None:
        """Collected nodes carry cost.basis='flowmap collection' for downstream classification."""
        boto3, _, _ = _mock_session()
        with patch.dict("sys.modules", {"boto3": boto3}):
            g = collect_aws_network(ResourceGraph(), region="us-east-1")
        assert all(
            n.cost.basis == "flowmap collection"
            for n in g.nodes
            if n.type.startswith(("aws_ec2_transit_gateway", "aws_dx_", "aws_vpn_"))
        )
