"""Pydantic v2 models for InfraCanvas resource graph."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Severity(StrEnum):
    critical = "critical"
    high = "high"
    medium = "medium"
    info = "info"


class Finding(BaseModel):
    rule_id: str
    severity: Severity
    title: str
    description: str
    remediation: str
    evidence: dict[str, object] = {}
    source: str = "security"           # "security" | "policy"
    framework_ids: list[str] = []      # ["CIS-2.1.5", "NIST-SC-7", "SOC2-CC6.1"]


class CostEstimate(BaseModel):
    monthly_usd: float = 0.0
    currency: str = "USD"
    basis: str = ""


class DriftStatus(StrEnum):
    unchanged = "unchanged"
    added = "added"
    changed = "changed"
    deleted = "deleted"
    shadow = "shadow"


class AttributeChange(BaseModel):
    attribute: str
    before: object = None
    after: object = None
    sensitive: bool = False


class ResourceNode(BaseModel):
    id: str
    type: str
    name: str
    provider: str
    module: str = ""
    region: str = ""
    group: str = ""
    attributes: dict[str, object] = {}
    dependencies: list[str] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    cost: CostEstimate = Field(default_factory=CostEstimate)
    drift: DriftStatus = DriftStatus.unchanged
    drift_changes: list[AttributeChange] = Field(default_factory=list)
    position: dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0})


class GraphSummary(BaseModel):
    total_resources: int = 0
    findings: dict[str, int] = Field(
        default_factory=lambda: {"critical": 0, "high": 0, "medium": 0, "info": 0}
    )
    estimated_monthly_cost: float = 0.0
    score: int = 100
    drift: dict[str, int] = Field(
        default_factory=lambda: {
            "added": 0, "changed": 0, "deleted": 0, "unchanged": 0, "shadow": 0,
        }
    )


class CategoryScore(BaseModel):
    name: str
    score: int
    grade: str
    finding_count: int


class ScoreCard(BaseModel):
    overall: int
    overall_grade: str
    categories: list[CategoryScore]
    top_issues: list[Finding]
    resource_count: int
    estimated_monthly_cost: float
    scan_id: str
    project: str
    scanned_at: str


class NetworkFinding(BaseModel):
    """Network-level security finding for a path or hop (FDM-01, NFN-01).

    Shape aligned with the generic rule engine (`Finding`) so NET-* YAML rules
    surface through the unified findings pipeline (Phase 2 D-09, Phase 3 D-12).
    """

    # Network-layer evidence
    source_ip: str
    dest_ip: str
    protocol: str
    port: int
    # Rule-engine-compatible fields (mirror of `Finding` shape)
    severity: Severity
    title: str
    description: str
    remediation: str = ""
    evidence: dict[str, object] = Field(default_factory=dict)
    rule_id: str = ""
    source: str = "network"
    framework_ids: list[str] = Field(default_factory=list)
    # FlowMap linkage
    path_id: str = ""
    hop_id: str = ""


class PathHop(BaseModel):
    """FDM-01: Single hop along a NetworkPath (router / firewall / TGW attachment)."""

    hop_index: int
    node_id: str
    source_ip: str = ""
    dest_ip: str = ""
    protocol: str = ""
    port: int = 0
    interface_in: str = ""
    interface_out: str = ""
    bgp_as_path: list[int] = Field(default_factory=list)
    next_hop: str = ""
    evidence: dict[str, object] = Field(default_factory=dict)


class NetworkPath(BaseModel):
    """FDM-01: Forward or return network path between two ResourceNodes."""

    id: str
    source_node_id: str
    dest_node_id: str
    direction: str  # "forward" | "return"
    hops: list[PathHop] = Field(default_factory=list)
    evidence: dict[str, object] = Field(default_factory=dict)
    path_cost: PathCost | None = None


class DCCollectorReading(BaseModel):
    """FDM-02: One reading emitted by a DC Collector Agent (populated in Phase 3b)."""

    site_id: str
    collector_type: str  # "router" | "firewall" | "checkpoint"
    collected_at: str  # ISO-8601 timestamp
    payload: dict[str, object] = Field(default_factory=dict)


class DCSite(BaseModel):
    """FDM-02: Physical data-centre site (populated in Phase 3b)."""

    id: str
    name: str
    location: str = ""
    routers: list[str] = Field(default_factory=list)  # ResourceNode.id references
    firewalls: list[str] = Field(default_factory=list)
    readings: list[DCCollectorReading] = Field(default_factory=list)


class ResourceGraph(BaseModel):
    version: str = "2.1"
    metadata: dict[str, object] = Field(default_factory=dict)
    nodes: list[ResourceNode] = Field(default_factory=list)
    edges: list[dict[str, str]] = Field(default_factory=list)
    summary: GraphSummary = Field(default_factory=GraphSummary)
    network_paths: list[NetworkPath] = Field(default_factory=list)
    dc_sites: list[DCSite] = Field(default_factory=list)
    costlens: CostLensData | None = None


# Phase 9: CostLens allocation models


class CostLineItem(BaseModel):
    resource_id: str
    resource_type: str
    label: str
    monthly_usd: float
    share_pct: float  # 0.0 for dedicated; allocation % for shared


class WorkloadCost(BaseModel):
    name: str
    total_monthly_usd: float
    line_items: list[CostLineItem] = Field(default_factory=list)


class SharedResourceSummary(BaseModel):
    resource_id: str
    resource_type: str
    monthly_usd: float
    workload_count: int


class IdleRecommendation(BaseModel):
    resource_id: str
    resource_type: str
    description: str
    monthly_waste_usd: float


class CostLensData(BaseModel):
    workloads: list[WorkloadCost] = Field(default_factory=list)
    shared_resources: list[SharedResourceSummary] = Field(default_factory=list)
    recommendations: list[IdleRecommendation] = Field(default_factory=list)


class PathCost(BaseModel):
    estimated_monthly_usd: float
    rate_per_gb: float
    assumed_gb: float
    basis: str
