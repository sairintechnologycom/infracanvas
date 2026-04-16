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
        default_factory=lambda: {"added": 0, "changed": 0, "deleted": 0}
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
    """CLI-02: Network-level security finding for a resource."""

    resource_id: str
    protocol: str
    source_cidr: str
    dest_cidr: str
    finding_type: str
    severity: Severity
    title: str
    description: str
    remediation: str = ""
    evidence: dict[str, object] = {}


class ResourceGraph(BaseModel):
    version: str = "2.0"
    metadata: dict[str, object] = Field(default_factory=dict)
    nodes: list[ResourceNode] = Field(default_factory=list)
    edges: list[dict[str, str]] = Field(default_factory=list)
    summary: GraphSummary = Field(default_factory=GraphSummary)
