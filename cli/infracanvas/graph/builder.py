"""Build a NetworkX DiGraph from parsed Terraform data."""

from __future__ import annotations

import networkx as nx

from infracanvas.graph.models import ResourceGraph, ResourceNode
from infracanvas.parser.hcl import ParsedTerraform


def build_graph(parsed: ParsedTerraform) -> ResourceGraph:
    """Construct a ResourceGraph from parsed Terraform data."""
    g = nx.DiGraph()
    nodes = _create_nodes(g, parsed)
    edges = _build_edges(g, parsed, nodes)

    for node in nodes:
        node.dependencies = [e["target"] for e in edges if e["source"] == node.id]

    return ResourceGraph(nodes=nodes, edges=edges)


def _create_nodes(
    g: nx.DiGraph, parsed: ParsedTerraform
) -> list[ResourceNode]:
    """Create ResourceNode objects and add them to the graph."""
    nodes: list[ResourceNode] = []
    for res in parsed.resources:
        resource_id = f"{res.resource_type}.{res.name}"
        provider = res.resource_type.split("_")[0] if "_" in res.resource_type else "unknown"
        group = _determine_group(res.attributes)

        node = ResourceNode(
            id=resource_id,
            type=res.resource_type,
            name=res.name,
            provider=provider,
            module=res.module,
            group=group,
            attributes=res.attributes,
            dependencies=[],
        )
        nodes.append(node)
        g.add_node(resource_id, **node.model_dump())
    return nodes


def _build_edges(
    g: nx.DiGraph,
    parsed: ParsedTerraform,
    nodes: list[ResourceNode],
) -> list[dict[str, str]]:
    """Build edges from explicit depends_on and implicit references."""
    edges: list[dict[str, str]] = []
    resource_ids = {n.id for n in nodes}

    for res in parsed.resources:
        source_id = f"{res.resource_type}.{res.name}"

        for dep in res.depends_on:
            if dep in resource_ids:
                edge = {"source": source_id, "target": dep, "type": "depends_on"}
                edges.append(edge)
                g.add_edge(source_id, dep, type="depends_on")

        implicit = parsed.implicit_deps.get(source_id, set())
        for target_id in implicit:
            if target_id in resource_ids:
                edge = {"source": source_id, "target": target_id, "type": "implicit"}
                edges.append(edge)
                g.add_edge(source_id, target_id, type="implicit")

    return edges


def _determine_group(attrs: dict[str, object]) -> str:
    """Determine group for a resource based on vpc_id or subnet_id."""
    vpc_id = attrs.get("vpc_id", "")
    if vpc_id and isinstance(vpc_id, str):
        return f"vpc:{vpc_id}"

    subnet_id = attrs.get("subnet_id", "")
    if subnet_id and isinstance(subnet_id, str):
        return f"subnet:{subnet_id}"

    return ""
