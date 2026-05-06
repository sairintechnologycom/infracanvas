"""Idle/oversized resource detector using static Terraform graph heuristics (CLA-05)."""

from __future__ import annotations

from collections import defaultdict

from infracanvas.graph.models import IdleRecommendation, ResourceGraph, ResourceNode


def _idle_nat_gateway(
    node: ResourceNode,
    edges_by_target: dict[str, list[dict[str, str]]],
    node_by_id: dict[str, ResourceNode],
) -> bool:
    """Idle if no aws_route node has an edge pointing to this NAT GW."""
    return node.type == "aws_nat_gateway" and not any(
        node_by_id.get(e["source"]) is not None
        and node_by_id[e["source"]].type == "aws_route"
        for e in edges_by_target.get(node.id, [])
    )


def _idle_tgw(
    node: ResourceNode,
    edges_by_source: dict[str, list[dict[str, str]]],
    node_by_id: dict[str, ResourceNode],
) -> bool:
    """Idle if no aws_ec2_transit_gateway_vpc_attachment child."""
    return node.type == "aws_ec2_transit_gateway" and not any(
        node_by_id.get(e["target"]) is not None
        and node_by_id[e["target"]].type == "aws_ec2_transit_gateway_vpc_attachment"
        for e in edges_by_source.get(node.id, [])
    )


def _idle_express_route(
    node: ResourceNode,
    edges_by_source: dict[str, list[dict[str, str]]],
    node_by_id: dict[str, ResourceNode],
) -> bool:
    """Idle if no azurerm_virtual_network_gateway_connection child."""
    return node.type == "azurerm_express_route_circuit" and not any(
        node_by_id.get(e["target"]) is not None
        and node_by_id[e["target"]].type == "azurerm_virtual_network_gateway_connection"
        for e in edges_by_source.get(node.id, [])
    )


def _idle_vpc_endpoint(
    node: ResourceNode,
    edges_by_target: dict[str, list[dict[str, str]]],
    node_by_id: dict[str, ResourceNode],
) -> bool:
    """Idle if no aws_route_table has an edge to this endpoint."""
    return node.type == "aws_vpc_endpoint" and not any(
        node_by_id.get(e["source"]) is not None
        and node_by_id[e["source"]].type == "aws_route_table"
        for e in edges_by_target.get(node.id, [])
    )


_IDLE_SIGNALS: dict[str, str] = {
    "aws_nat_gateway": "No aws_route entries reference this NAT Gateway in the Terraform graph",
    "aws_ec2_transit_gateway": "No aws_ec2_transit_gateway_vpc_attachment children found",
    "azurerm_express_route_circuit": "No azurerm_virtual_network_gateway_connection children found",
    "aws_vpc_endpoint": "No aws_route_table entries reference this VPC Endpoint",
}

_IDLE_CANDIDATES: frozenset[str] = frozenset(_IDLE_SIGNALS.keys())


class IdleDetector:
    """Detect idle/oversized resources using static Terraform graph heuristics."""

    def detect(self, graph: ResourceGraph) -> ResourceGraph:
        """Append IdleRecommendation entries to graph.costlens.recommendations."""
        if graph.costlens is None:
            return graph  # Allocator must run first

        # Build adjacency index once — O(edges) not O(nodes * edges)
        node_by_id: dict[str, ResourceNode] = {n.id: n for n in graph.nodes}
        edges_by_source: dict[str, list[dict[str, str]]] = defaultdict(list)
        edges_by_target: dict[str, list[dict[str, str]]] = defaultdict(list)
        for edge in graph.edges:
            edges_by_source[edge["source"]].append(edge)
            edges_by_target[edge["target"]].append(edge)

        recommendations: list[IdleRecommendation] = []

        for node in graph.nodes:
            if node.type not in _IDLE_CANDIDATES:
                continue

            is_idle = False
            if node.type == "aws_nat_gateway":
                is_idle = _idle_nat_gateway(node, edges_by_target, node_by_id)
            elif node.type == "aws_ec2_transit_gateway":
                is_idle = _idle_tgw(node, edges_by_source, node_by_id)
            elif node.type == "azurerm_express_route_circuit":
                is_idle = _idle_express_route(node, edges_by_source, node_by_id)
            elif node.type == "aws_vpc_endpoint":
                is_idle = _idle_vpc_endpoint(node, edges_by_target, node_by_id)

            if is_idle:
                recommendations.append(IdleRecommendation(
                    resource_id=node.id,
                    resource_type=node.type,
                    description=_IDLE_SIGNALS[node.type],
                    monthly_waste_usd=node.cost.monthly_usd,
                ))

        graph.costlens.recommendations.extend(recommendations)
        return graph
