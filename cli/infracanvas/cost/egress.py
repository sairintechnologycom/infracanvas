"""Cross-cloud egress cost estimator for CostLens CPC-01 per-path estimation."""

from __future__ import annotations

from infracanvas.graph.models import PathCost, ResourceGraph, ResourceNode

# AWS inter-region egress rates ($/GB) — region pair keys
AWS_EGRESS_RATES: dict[str, float] = {
    "us-east-1:us-east-2": 0.01,
    "us-east-1:us-west-1": 0.02,
    "us-east-1:us-west-2": 0.02,
    "us-east-1:eu-west-1": 0.02,
    "us-east-1:eu-west-2": 0.02,
    "us-east-1:eu-central-1": 0.02,
    "us-east-1:ap-northeast-1": 0.09,
    "us-east-1:ap-southeast-1": 0.09,
    "us-east-1:ap-south-1": 0.086,
    "us-west-2:eu-west-1": 0.02,
    "us-west-2:ap-northeast-1": 0.09,
    "eu-west-1:ap-northeast-1": 0.09,
}

# Azure inter-region egress rates ($/GB, zone 1)
AZURE_EGRESS_RATES: dict[str, float] = {
    "eastus:westeurope": 0.05,
    "eastus:southeastasia": 0.08,
    "westeurope:eastus": 0.05,
    "westeurope:southeastasia": 0.08,
}

# Cross-cloud (AWS <-> Azure) and Internet egress ($/GB)
CROSS_CLOUD_EGRESS: float = 0.09  # AWS -> Azure / Azure -> AWS via Internet
AWS_INTERNET_EGRESS: float = 0.09  # AWS -> Internet (first 10TB)
AZURE_INTERNET_EGRESS: float = 0.087  # Azure -> Internet (zone 1)

# Default fallback for unknown region pairs
DEFAULT_EGRESS_RATE: float = 0.09

# Assumed monthly transfer volume when no flow data is available (CPC-02 deferred)
ASSUMED_MONTHLY_GB: float = 100.0
BASIS_NOTE: str = "estimated at 100 GB/mo (no flow data — enable flow logs for actuals)"


def _normalize_region(region: str) -> str:
    """Normalize region string to lowercase for table lookup."""
    return region.strip().lower().replace(" ", "")


def _get_node_region(node: ResourceNode) -> str | None:
    """Extract region from node attributes (AWS 'region' or Azure 'location')."""
    region = node.attributes.get("region") or node.attributes.get("location")
    return str(region).strip() if region else None


def _is_cross_cloud(src_node: ResourceNode, dst_node: ResourceNode) -> bool:
    """Return True if path crosses cloud boundary (AWS <-> Azure)."""
    src_aws = src_node.provider == "aws" or src_node.type.startswith("aws_")
    dst_azure = dst_node.provider == "azurerm" or dst_node.type.startswith("azurerm_")
    src_azure = src_node.provider == "azurerm" or src_node.type.startswith("azurerm_")
    dst_aws = dst_node.provider == "aws" or dst_node.type.startswith("aws_")
    return (src_aws and dst_azure) or (src_azure and dst_aws)


def _lookup_rate(src_region: str, dst_region: str, cross_cloud: bool) -> float:
    """Look up egress rate for a region pair. Returns DEFAULT_EGRESS_RATE if unknown."""
    if _normalize_region(src_region) == _normalize_region(dst_region):
        return 0.0
    if cross_cloud:
        return CROSS_CLOUD_EGRESS

    # AWS inter-region lookup (both key directions)
    for key in (f"{src_region}:{dst_region}", f"{dst_region}:{src_region}"):
        if key in AWS_EGRESS_RATES:
            return AWS_EGRESS_RATES[key]

    # Azure inter-region lookup (normalized lowercase)
    src_norm = _normalize_region(src_region)
    dst_norm = _normalize_region(dst_region)
    for key in (f"{src_norm}:{dst_norm}", f"{dst_norm}:{src_norm}"):
        if key in AZURE_EGRESS_RATES:
            return AZURE_EGRESS_RATES[key]

    return DEFAULT_EGRESS_RATE


class EgressEstimator:
    """Annotate NetworkPath objects with estimated per-path transfer costs (CPC-01).

    Uses static pricing tables applied at a default assumed volume of 100 GB/mo.
    CPC-02 (flow-log-driven attribution) is deferred to Phase 12.
    """

    def __init__(self, assumed_monthly_gb: float = ASSUMED_MONTHLY_GB) -> None:
        self._assumed_gb = assumed_monthly_gb

    def estimate(self, graph: ResourceGraph) -> ResourceGraph:
        """Annotate each NetworkPath with path_cost where region data is available.

        Paths with missing source/dest nodes or missing region attributes receive
        path_cost=None (graceful skip — T-09-04-04 mitigation).
        """
        if not graph.network_paths:
            return graph

        node_by_id: dict[str, ResourceNode] = {n.id: n for n in graph.nodes}

        for path in graph.network_paths:
            src_node = node_by_id.get(path.source_node_id)
            dst_node = node_by_id.get(path.dest_node_id)

            if src_node is None or dst_node is None:
                path.path_cost = None
                continue

            src_region = _get_node_region(src_node)
            dst_region = _get_node_region(dst_node)

            if src_region is None or dst_region is None:
                path.path_cost = None  # CPC-C-3: graceful skip
                continue

            cross_cloud = _is_cross_cloud(src_node, dst_node)
            rate = _lookup_rate(src_region, dst_region, cross_cloud)
            estimated_usd = round(rate * self._assumed_gb, 4)

            path.path_cost = PathCost(
                estimated_monthly_usd=estimated_usd,
                rate_per_gb=rate,
                assumed_gb=self._assumed_gb,
                basis=BASIS_NOTE,
            )

        return graph
