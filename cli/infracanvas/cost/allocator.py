"""Shared infrastructure cost allocator for CostLens (CLA-01..04)."""

from __future__ import annotations

from infracanvas.graph.models import (
    CostLineItem,
    CostLensData,
    ResourceGraph,
    ResourceNode,
    SharedResourceSummary,
    WorkloadCost,
)

SHARED_TYPES: frozenset[str] = frozenset({
    "aws_ec2_transit_gateway",
    "azurerm_express_route_circuit",
    "azurerm_firewall",
    "aws_nat_gateway",
    "aws_vpc_endpoint",
})


def _workload_name(node: ResourceNode, tag_key: str) -> str:
    """Return workload name from node tag, or 'untagged'."""
    val = node.attributes.get(tag_key)
    return str(val).strip() if val else "untagged"


def _split_percentages(n: int) -> list[float]:
    """Split 100% into n equal parts; distribute float remainder to first element."""
    if n == 0:
        return []
    base = round(100.0 / n, 4)
    remainder = round(100.0 - base * n, 4)
    parts = [base] * n
    parts[0] = round(parts[0] + remainder, 4)
    return parts


class SharedCostAllocator:
    """Post-process ResourceGraph to produce CostLensData with workload allocation."""

    def __init__(self, workload_tag_key: str = "Service") -> None:
        self._tag_key = workload_tag_key

    def allocate(self, graph: ResourceGraph) -> ResourceGraph:
        """Allocate shared resource costs across workloads by tag."""
        node_by_id: dict[str, ResourceNode] = {n.id: n for n in graph.nodes}

        # Accumulate workload totals: workload_name -> list[CostLineItem]
        workload_items: dict[str, list[CostLineItem]] = {}
        shared_summaries: list[SharedResourceSummary] = []

        for node in graph.nodes:
            if node.type not in SHARED_TYPES:
                continue

            # Find all workloads attached via graph edges (both directions)
            attached: list[str] = []
            for edge in graph.edges:
                peer_id: str | None = None
                if edge["source"] == node.id:
                    peer_id = edge["target"]
                elif edge["target"] == node.id:
                    peer_id = edge["source"]
                if peer_id and peer_id in node_by_id:
                    wl = _workload_name(node_by_id[peer_id], self._tag_key)
                    attached.append(wl)

            distinct_workloads = sorted(set(attached))

            shared_summaries.append(SharedResourceSummary(
                resource_id=node.id,
                resource_type=node.type,
                monthly_usd=node.cost.monthly_usd,
                workload_count=len(distinct_workloads),
            ))

            if not distinct_workloads:
                continue  # No attachments — skip allocation, resource visible in shared_resources

            pcts = _split_percentages(len(distinct_workloads))
            share_usd = node.cost.monthly_usd / len(distinct_workloads)

            for wl_name, pct in zip(distinct_workloads, pcts):
                line_item = CostLineItem(
                    resource_id=node.id,
                    resource_type=node.type,
                    label=node.name or node.id,
                    monthly_usd=round(share_usd, 2),
                    share_pct=pct,
                )
                workload_items.setdefault(wl_name, []).append(line_item)

        # Include dedicated (non-shared) resource costs in workload totals
        for node in graph.nodes:
            if node.type in SHARED_TYPES:
                continue
            wl_name = _workload_name(node, self._tag_key)
            if wl_name == "untagged":
                continue  # Only include tagged dedicated resources in workload totals
            line_item = CostLineItem(
                resource_id=node.id,
                resource_type=node.type,
                label=node.name or node.id,
                monthly_usd=round(node.cost.monthly_usd, 2),
                share_pct=0.0,
            )
            workload_items.setdefault(wl_name, []).append(line_item)

        workloads: list[WorkloadCost] = []
        for wl_name, items in sorted(workload_items.items()):
            total = round(sum(i.monthly_usd for i in items), 2)
            workloads.append(WorkloadCost(
                name=wl_name,
                total_monthly_usd=total,
                line_items=items,
            ))

        graph.costlens = CostLensData(
            workloads=workloads,
            shared_resources=shared_summaries,
            recommendations=[],  # Populated by IdleDetector in Plan 03
        )
        return graph
