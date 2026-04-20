"""Drift analyzer — overlay Terraform plan changes onto resource graph."""

from __future__ import annotations

from infracanvas.graph.models import DriftStatus, ResourceGraph, ResourceNode
from infracanvas.parser.plan import PlanChange


class DriftAnalyzer:
    """Match plan changes to graph nodes and annotate drift status."""

    def apply(self, graph: ResourceGraph, changes: list[PlanChange]) -> ResourceGraph:
        """Apply plan changes to graph nodes and update drift summary."""
        node_map = {node.id: node for node in graph.nodes}

        for change in changes:
            addr = change.resource_address
            if addr in node_map:
                node = node_map[addr]
                node.drift = change.action
                node.drift_changes = change.attribute_changes
            elif change.action == DriftStatus.added:
                # Resource in plan but not in current graph — create stub
                provider = (
                    change.resource_type.split("_")[0]
                    if "_" in change.resource_type
                    else "unknown"
                )
                stub = ResourceNode(
                    id=addr,
                    type=change.resource_type,
                    name=change.resource_name,
                    provider=provider,
                    attributes=change.after,
                    drift=DriftStatus.added,
                    drift_changes=change.attribute_changes,
                )
                graph.nodes.append(stub)

        # Update drift summary counts
        drift_counts = {"added": 0, "changed": 0, "deleted": 0, "unchanged": 0, "shadow": 0}
        for node in graph.nodes:
            if node.drift in drift_counts:
                drift_counts[node.drift] += 1

        graph.summary.drift = drift_counts
        graph.summary.total_resources = len(graph.nodes)

        return graph
