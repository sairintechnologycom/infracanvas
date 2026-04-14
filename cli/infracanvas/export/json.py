"""JSON export for InfraCanvas resource graphs."""

from __future__ import annotations

from infracanvas.graph.models import ResourceGraph


def export_graph(graph: ResourceGraph) -> str:
    """Export a ResourceGraph as a JSON string."""
    return graph.model_dump_json(indent=2)
