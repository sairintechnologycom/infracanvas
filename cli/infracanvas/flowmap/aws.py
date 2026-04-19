"""AWS cloud-network topology collector for FlowMap (AWS-01, AWS-02, AWS-03).

Read-only boto3 calls against TGW, VPC, Direct Connect. Appends ResourceNode
entries to the provided ResourceGraph. Never hard-fails on individual API errors.

Mirrors shadow/detector.py opt-in + credential-guard pattern (CONTEXT.md D-05).
"""
from __future__ import annotations

from typing import Any

from infracanvas.graph.models import (
    CostEstimate,
    DriftStatus,
    ResourceGraph,
    ResourceNode,
)


def collect_aws_network(graph: ResourceGraph, *, region: str) -> ResourceGraph:
    """Collect AWS network topology and append to graph.nodes.

    Raises:
        RuntimeError: when boto3 missing or AWS creds absent. Error messages
            are credential-free (ASVS L1, T-03-03-02); `from None` strips any
            SDK-internal traceback context.
    """
    try:
        import boto3  # type: ignore[import-untyped]  # noqa: PLC0415 — lazy import per shadow/detector.py pattern
    except ImportError:
        # SECURITY: do NOT interpolate exc details — message must be credential-free
        raise RuntimeError(
            "boto3 not installed. Install with: pip install 'infracanvas[flowmap]'"
        ) from None

    session = boto3.Session(region_name=region)
    creds = session.get_credentials()
    if not creds:
        raise RuntimeError("--flowmap requires AWS credentials.")

    ec2 = session.client("ec2")
    dx = session.client("directconnect")

    _collect_transit_gateways(graph, ec2, region=region)
    _collect_tgw_attachments(graph, ec2, region=region)
    _collect_tgw_route_tables(graph, ec2, region=region)
    _collect_vpn_connections(graph, ec2, region=region)
    _collect_vpc_route_tables(graph, ec2, region=region)
    _collect_network_acls(graph, ec2, region=region)
    _collect_direct_connect(graph, dx, region=region)
    _collect_flow_log_metadata(graph, ec2, region=region)

    return graph


def _add_node(
    graph: ResourceGraph,
    *,
    resource_type: str,
    name: str,
    region: str,
    attributes: dict[str, Any],
) -> None:
    """Append a FlowMap-collected node. No shadow_ prefix — real infra."""
    node = ResourceNode(
        id=f"{resource_type}.{name}",
        type=resource_type,
        name=name,
        provider="aws",
        region=region,
        attributes=attributes,
        drift=DriftStatus.unchanged,
        cost=CostEstimate(monthly_usd=0.0, basis="flowmap collection"),
    )
    graph.nodes.append(node)


def _collect_transit_gateways(
    graph: ResourceGraph, ec2: Any, *, region: str
) -> None:
    try:
        response = ec2.describe_transit_gateways()
        for tgw in response.get("TransitGateways", []):
            tgw_id = tgw.get("TransitGatewayId", "")
            name = tgw_id  # prefer Name tag if present
            for tag in tgw.get("Tags", []) or []:
                if tag.get("Key") == "Name":
                    name = tag.get("Value", tgw_id)
                    break
            _add_node(
                graph,
                resource_type="aws_ec2_transit_gateway",
                name=name,
                region=region,
                attributes={
                    "transit_gateway_id": tgw_id,
                    "state": tgw.get("State", ""),
                    "owner_id": tgw.get("OwnerId", ""),
                    "amazon_side_asn": tgw.get("Options", {}).get("AmazonSideAsn", 0),
                },
            )
    except Exception:  # noqa: BLE001 — AWS SDK raises varied exceptions per service
        pass


def _collect_tgw_attachments(
    graph: ResourceGraph, ec2: Any, *, region: str
) -> None:
    try:
        response = ec2.describe_transit_gateway_attachments()
        for att in response.get("TransitGatewayAttachments", []):
            att_id = att.get("TransitGatewayAttachmentId", "")
            _add_node(
                graph,
                resource_type="aws_ec2_transit_gateway_attachment",
                name=att_id,
                region=region,
                attributes={
                    "transit_gateway_attachment_id": att_id,
                    "transit_gateway_id": att.get("TransitGatewayId", ""),
                    "resource_type": att.get("ResourceType", ""),
                    "resource_id": att.get("ResourceId", ""),
                    "state": att.get("State", ""),
                },
            )
    except Exception:  # noqa: BLE001
        pass


def _collect_tgw_route_tables(
    graph: ResourceGraph, ec2: Any, *, region: str
) -> None:
    try:
        response = ec2.describe_transit_gateway_route_tables()
        for rtb in response.get("TransitGatewayRouteTables", []):
            rtb_id = rtb.get("TransitGatewayRouteTableId", "")
            routes: list[dict[str, Any]] = []
            try:
                search = ec2.search_transit_gateway_routes(
                    TransitGatewayRouteTableId=rtb_id,
                    Filters=[{"Name": "state", "Values": ["active", "blackhole"]}],
                )
                routes = search.get("Routes", []) or []
            except Exception:  # noqa: BLE001
                routes = []
            _add_node(
                graph,
                resource_type="aws_ec2_transit_gateway_route_table",
                name=rtb_id,
                region=region,
                attributes={
                    "transit_gateway_route_table_id": rtb_id,
                    "transit_gateway_id": rtb.get("TransitGatewayId", ""),
                    "state": rtb.get("State", ""),
                    "routes": routes,
                },
            )
    except Exception:  # noqa: BLE001
        pass


def _collect_vpn_connections(
    graph: ResourceGraph, ec2: Any, *, region: str
) -> None:
    try:
        response = ec2.describe_vpn_connections()
        for vpn in response.get("VpnConnections", []):
            vpn_id = vpn.get("VpnConnectionId", "")
            _add_node(
                graph,
                resource_type="aws_vpn_connection",
                name=vpn_id,
                region=region,
                attributes={
                    "vpn_connection_id": vpn_id,
                    "customer_gateway_id": vpn.get("CustomerGatewayId", ""),
                    "transit_gateway_id": vpn.get("TransitGatewayId", ""),
                    "state": vpn.get("State", ""),
                    "type": vpn.get("Type", ""),
                },
            )
    except Exception:  # noqa: BLE001
        pass


def _collect_vpc_route_tables(
    graph: ResourceGraph, ec2: Any, *, region: str
) -> None:
    try:
        response = ec2.describe_route_tables()
        for rtb in response.get("RouteTables", []):
            rtb_id = rtb.get("RouteTableId", "")
            _add_node(
                graph,
                resource_type="aws_route_table",
                name=rtb_id,
                region=region,
                attributes={
                    "route_table_id": rtb_id,
                    "vpc_id": rtb.get("VpcId", ""),
                    "routes": rtb.get("Routes", []) or [],
                    "associations": rtb.get("Associations", []) or [],
                },
            )
    except Exception:  # noqa: BLE001
        pass


def _collect_network_acls(
    graph: ResourceGraph, ec2: Any, *, region: str
) -> None:
    try:
        response = ec2.describe_network_acls()
        for nacl in response.get("NetworkAcls", []):
            nacl_id = nacl.get("NetworkAclId", "")
            _add_node(
                graph,
                resource_type="aws_network_acl",
                name=nacl_id,
                region=region,
                attributes={
                    "network_acl_id": nacl_id,
                    "vpc_id": nacl.get("VpcId", ""),
                    "is_default": nacl.get("IsDefault", False),
                    "entries": nacl.get("Entries", []) or [],
                    "associations": nacl.get("Associations", []) or [],
                },
            )
    except Exception:  # noqa: BLE001
        pass


def _collect_direct_connect(
    graph: ResourceGraph, dx: Any, *, region: str
) -> None:
    try:
        conns = dx.describe_connections()
        for conn in conns.get("connections", []):
            conn_id = conn.get("connectionId", "")
            _add_node(
                graph,
                resource_type="aws_dx_connection",
                name=conn_id,
                region=region,
                attributes={
                    "connection_id": conn_id,
                    "connection_name": conn.get("connectionName", ""),
                    "state": conn.get("connectionState", ""),
                    "location": conn.get("location", ""),
                    "bandwidth": conn.get("bandwidth", ""),
                },
            )
    except Exception:  # noqa: BLE001
        pass

    try:
        vifs = dx.describe_virtual_interfaces()
        for vif in vifs.get("virtualInterfaces", []):
            vif_id = vif.get("virtualInterfaceId", "")
            _add_node(
                graph,
                resource_type="aws_dx_virtual_interface",
                name=vif_id,
                region=region,
                attributes={
                    "virtual_interface_id": vif_id,
                    "virtual_interface_type": vif.get("virtualInterfaceType", ""),
                    "state": vif.get("virtualInterfaceState", ""),
                    "connection_id": vif.get("connectionId", ""),
                    "asn": vif.get("asn", 0),
                    "amazon_address": vif.get("amazonAddress", ""),
                    "customer_address": vif.get("customerAddress", ""),
                },
            )
    except Exception:  # noqa: BLE001
        pass


def _collect_flow_log_metadata(
    graph: ResourceGraph, ec2: Any, *, region: str
) -> None:
    """AWS-03 metadata-only in 3a: attach flow-log existence to the VPC node.

    No log ingestion. Full correlation defers to 3b (CONTEXT.md D-11).
    """
    try:
        response = ec2.describe_flow_logs()
        by_vpc: dict[str, dict[str, Any]] = {}
        for fl in response.get("FlowLogs", []):
            if fl.get("ResourceId", "").startswith("vpc-"):
                by_vpc[fl["ResourceId"]] = {
                    "flow_log_id": fl.get("FlowLogId", ""),
                    "log_group": fl.get("LogGroupName", ""),
                    "destination_type": fl.get("LogDestinationType", ""),
                    "traffic_type": fl.get("TrafficType", ""),
                    "log_format": fl.get("LogFormat", ""),
                }
        # Attach to existing VPC nodes (parsed from HCL) — don't create phantom VPCs.
        for node in graph.nodes:
            if node.type == "aws_vpc":
                vpc_id = str(node.attributes.get("vpc_id") or node.attributes.get("id") or "")
                if vpc_id in by_vpc:
                    node.attributes["flow_log"] = by_vpc[vpc_id]
    except Exception:  # noqa: BLE001
        pass
