# Phase 9: CostLens - Pattern Map

**Mapped:** 2026-05-06
**Files analyzed:** 15 new/modified files
**Analogs found:** 14 / 15

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `cli/infracanvas/cost/allocator.py` | service | transform | `cli/infracanvas/cost/estimator.py` | exact |
| `cli/infracanvas/cost/idle.py` | service | transform | `cli/infracanvas/cost/estimator.py` | role-match |
| `cli/infracanvas/cost/egress.py` | service | transform | `cli/infracanvas/cost/estimator.py` | exact |
| `cli/infracanvas/cost/estimator.py` | service | transform | self (modify) | exact |
| `cli/infracanvas/graph/models.py` | model | transform | self (modify) | exact |
| `cli/infracanvas/config.py` | config | — | self (modify) | exact |
| `cli/infracanvas/main.py` | controller | request-response | self (modify) | exact |
| `viewer/src/types.ts` | model | — | self (modify) | exact |
| `viewer/src/components/TabBar.tsx` | component | event-driven | self (modify) | exact |
| `viewer/src/App.tsx` | component | event-driven | self (modify) | exact |
| `viewer/src/components/costlens/CostLensPanel.tsx` | component | request-response | `viewer/src/components/flowmap/FlowMapEmptyState.tsx` | role-match |
| `viewer/src/components/costlens/WorkloadCard.tsx` | component | request-response | `viewer/src/components/flowmap/PathDetailPanel.tsx` | role-match |
| `viewer/src/components/costlens/IdleRecommendations.tsx` | component | request-response | `viewer/src/components/flowmap/PathDetailPanel.tsx` | role-match |
| `dashboard/app/(dashboard)/scans/[id]/ScanDetailTabs.tsx` | component | request-response | `dashboard/components/scans/ScanViewerClient.tsx` | exact |
| `dashboard/app/(dashboard)/scans/[id]/CostTab.tsx` | component | request-response | `dashboard/components/scans/ScanViewerClient.tsx` | role-match |
| `dashboard/components/scans/WorkloadTable.tsx` | component | CRUD | `dashboard/components/scans/ScansTable.tsx` | exact |
| `dashboard/components/scans/IdleRecommendationsList.tsx` | component | CRUD | `dashboard/components/scans/ScansTable.tsx` | role-match |
| `dashboard/app/(dashboard)/scans/[id]/renderScanByStatus.tsx` | utility | request-response | self (modify) | exact |

---

## Pattern Assignments

### `cli/infracanvas/cost/allocator.py` (service, transform) — NEW

**Analog:** `cli/infracanvas/cost/estimator.py`

**Imports pattern** (estimator.py lines 1–8):
```python
"""Static cost estimator for AWS resources (us-east-1 on-demand pricing)."""

from __future__ import annotations

from typing import Any

from infracanvas.graph.models import CostEstimate, ResourceGraph
from infracanvas.parser.plan import PlanChange
```
New file uses the same `from __future__ import annotations` + same graph model imports. Replace `PlanChange` with new Pydantic models `CostLensData`, `WorkloadCost`, `CostLineItem`, `SharedResourceSummary`.

**Class pattern** (estimator.py lines 110–137):
```python
class CostEstimator:
    """Annotate resource nodes with cost estimates."""

    def estimate(self, graph: ResourceGraph) -> ResourceGraph:
        """Annotate each node.cost with region-aware pricing and update summary."""
        total = 0.0
        group_costs: dict[str, float] = {}
        for node in graph.nodes:
            base = _estimate_resource(node.type, node.attributes)
            ...
            node.cost = CostEstimate(...)
            total += node.cost.monthly_usd
        graph.summary.estimated_monthly_cost = round(total, 2)
        graph.metadata["group_costs"] = {k: round(v, 2) for k, v in group_costs.items()}
        return graph
```
`SharedCostAllocator` follows the same pattern: takes `graph: ResourceGraph`, mutates `graph.costlens`, returns `graph`. The `workload_tag_key` is injected via `__init__`:
```python
class SharedCostAllocator:
    def __init__(self, workload_tag_key: str = "Service") -> None:
        self._tag_key = workload_tag_key

    def allocate(self, graph: ResourceGraph) -> ResourceGraph:
        ...
        graph.costlens = CostLensData(workloads=..., shared_resources=..., recommendations=...)
        return graph
```

**Graph edge traversal** (modelled from estimator's `for node in graph.nodes` + `graph.edges` is `list[dict[str, str]]` per models.py line 176):
```python
# Build lookup dict to avoid O(n) search per edge
node_by_id: dict[str, ResourceNode] = {n.id: n for n in graph.nodes}

SHARED_TYPES = {
    "aws_ec2_transit_gateway",
    "azurerm_express_route_circuit",
    "azurerm_firewall",
    "aws_nat_gateway",
    "aws_vpc_endpoint",
}

for node in graph.nodes:
    if node.type not in SHARED_TYPES:
        continue
    attached_workloads: set[str] = set()
    for edge in graph.edges:          # edge is dict[str, str]
        peer_id = None
        if edge["source"] == node.id:
            peer_id = edge["target"]
        elif edge["target"] == node.id:
            peer_id = edge["source"]
        if peer_id and peer_id in node_by_id:
            peer = node_by_id[peer_id]
            wl = str(peer.attributes.get(self._tag_key, "")) or "untagged"
            attached_workloads.add(wl)
```

**Allocation rounding guarantee** (CLA success criterion 4 — percentages sum to 100%):
```python
# Integer rounding: distribute remainder to first workload
workload_list = sorted(attached_workloads)
n = len(workload_list)
base_pct = round(100.0 / n, 4)
remainder = round(100.0 - base_pct * n, 4)
shares = [base_pct] * n
shares[0] = round(shares[0] + remainder, 4)
```

**Error handling pattern** (from estimator.py `if resource_type in FLAT_MONTHLY` fallthrough):
```python
# Edge case: shared resource with no attached workloads — skip allocation
if not attached_workloads:
    shared_summaries.append(SharedResourceSummary(
        resource_id=node.id,
        resource_type=node.type,
        monthly_usd=node.cost.monthly_usd,
        workload_count=0,
    ))
    continue
```

---

### `cli/infracanvas/cost/idle.py` (service, transform) — NEW

**Analog:** `cli/infracanvas/cost/estimator.py`

**Module pattern** — module-level private helpers + public class (estimator.py lines 61–108):
```python
def _estimate_ec2(attrs: dict[str, Any]) -> CostEstimate:
    ...

def _estimate_resource(resource_type: str, attrs: dict[str, Any]) -> CostEstimate:
    """Estimate monthly cost for a single resource."""
    if resource_type in ("aws_instance",):
        return _estimate_ec2(attrs)
    ...
```
`idle.py` uses the same pattern: module-level `_idle_*` predicate functions, one public `IdleDetector` class with a `detect(graph) -> ResourceGraph` method.

**Imports pattern**:
```python
"""Idle/oversized resource detector using static Terraform graph heuristics."""

from __future__ import annotations

from infracanvas.graph.models import IdleRecommendation, ResourceGraph, ResourceNode
```

**Core pattern** (four heuristic functions mirroring estimator's type-dispatch):
```python
def _idle_nat_gateway(node: ResourceNode, graph: ResourceGraph,
                      node_by_id: dict[str, ResourceNode]) -> bool:
    return node.type == "aws_nat_gateway" and not any(
        edge["target"] == node.id
        and node_by_id.get(edge["source"], ResourceNode(...)).type == "aws_route"
        for edge in graph.edges
    )

class IdleDetector:
    def detect(self, graph: ResourceGraph) -> ResourceGraph:
        node_by_id = {n.id: n for n in graph.nodes}
        recommendations: list[IdleRecommendation] = []
        for node in graph.nodes:
            if _idle_nat_gateway(node, graph, node_by_id):
                recommendations.append(IdleRecommendation(
                    resource_id=node.id,
                    resource_type=node.type,
                    description="No aws_route entries reference this NAT Gateway",
                    monthly_waste_usd=node.cost.monthly_usd,
                ))
            ...
        if graph.costlens is not None:
            graph.costlens.recommendations.extend(recommendations)
        return graph
```

**Guard for missing node refs** (node_by_id.get with sentinel avoids KeyError on stale edges):
```python
peer = node_by_id.get(edge["source"])
if peer is None:
    continue
```

---

### `cli/infracanvas/cost/egress.py` (service, transform) — NEW

**Analog:** `cli/infracanvas/cost/estimator.py`

**Static pricing table pattern** (estimator.py lines 10–58):
```python
HOURS_PER_MONTH = 730

REGION_MULTIPLIERS: dict[str, float] = {
    "us-east-1": 1.0, "us-east-2": 1.0, ...
    "East US": 1.0, "West US": 1.05, ...   # Azure regions already in table
}

FLAT_MONTHLY: dict[str, float] = {
    "aws_nat_gateway": 0.045 * HOURS_PER_MONTH,
    ...
}
```
`egress.py` adds cross-cloud egress pricing following the exact same dict-of-constants pattern:
```python
"""Cross-cloud egress cost rates for CPC-01 per-path estimation."""

from __future__ import annotations

# AWS inter-region egress rates ($/GB)
AWS_EGRESS_RATES: dict[str, float] = {
    "us-east-1:us-west-2": 0.02,
    "us-east-1:eu-west-1": 0.02,
    "us-east-1:ap-northeast-1": 0.09,
    # cross-cloud (AWS → Azure)
    "aws:azure": 0.09,
}

# Azure inter-region egress rates ($/GB)
AZURE_EGRESS_RATES: dict[str, float] = {
    "East US:West Europe": 0.05,
    "East US:Southeast Asia": 0.08,
}

# Default fallback (unknown cross-region)
DEFAULT_EGRESS_RATE = 0.09
```

---

### `cli/infracanvas/cost/estimator.py` (service, transform) — MODIFY

**What to add** — new entries to the existing `FLAT_MONTHLY` dict (lines 38–44):
```python
FLAT_MONTHLY: dict[str, float] = {
    "aws_nat_gateway": 0.045 * HOURS_PER_MONTH,   # $32.85 — already present
    "aws_alb": 0.0225 * HOURS_PER_MONTH,           # already present
    "aws_lb": 0.0225 * HOURS_PER_MONTH,             # already present
    "aws_eks_cluster": 0.10 * HOURS_PER_MONTH,      # already present
    "aws_kms_key": 1.00,                             # already present
    # Phase 9: CostLens shared resources
    "aws_ec2_transit_gateway": 0.05 * HOURS_PER_MONTH,    # $36.50 TGW hourly charge
    "aws_vpc_endpoint": 0.01 * HOURS_PER_MONTH,           # $7.30 Interface endpoint/hr
    "azurerm_express_route_circuit": 55.00,                # flat monthly (Standard, 50Mbps)
    "azurerm_firewall": 1.25 * HOURS_PER_MONTH,           # $912.50/mo Premium tier
}
```
No other changes to estimator.py. The `_estimate_resource` dispatch at line 100 picks these up automatically via `if resource_type in FLAT_MONTHLY`.

---

### `cli/infracanvas/graph/models.py` (model) — MODIFY

**Analog:** existing `ResourceGraph` model (models.py lines 172–179)

**Addition pattern** — add after `ResourceGraph` class (line 179), following the same Pydantic v2 `BaseModel` + `Field(default_factory=...)` convention used throughout the file:

```python
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
```

**ResourceGraph addition** (add field to class body at line 179, after `dc_sites`):
```python
class ResourceGraph(BaseModel):
    version: str = "2.1"
    metadata: dict[str, object] = Field(default_factory=dict)
    nodes: list[ResourceNode] = Field(default_factory=list)
    edges: list[dict[str, str]] = Field(default_factory=list)
    summary: GraphSummary = Field(default_factory=GraphSummary)
    network_paths: list[NetworkPath] = Field(default_factory=list)
    dc_sites: list[DCSite] = Field(default_factory=list)
    costlens: CostLensData | None = None   # Phase 9 addition
```

---

### `cli/infracanvas/config.py` (config) — MODIFY

**Analog:** existing `InfraCanvasConfig` (config.py lines 11–16)

**Existing pattern** (full file — small, read completely):
```python
class InfraCanvasConfig(BaseModel):
    severity_threshold: str = "high"
    ignore_rules: list[str] = []
    output_dir: str = "."
    open_browser: bool = True
    provider: str = "aws"
```
`model_validate(data)` at line 28 handles unknown keys silently — so adding a new nested model is backward-compatible; existing configs without `costlens:` get the default.

**Addition pattern** (insert before `InfraCanvasConfig`, after the imports):
```python
class CostLensConfig(BaseModel):
    workload_tag_key: str = "Service"
```

**Modify `InfraCanvasConfig`**:
```python
class InfraCanvasConfig(BaseModel):
    severity_threshold: str = "high"
    ignore_rules: list[str] = []
    output_dir: str = "."
    open_browser: bool = True
    provider: str = "aws"
    costlens: CostLensConfig = Field(default_factory=CostLensConfig)
```

**Required import addition** (line 7, alongside existing `from pydantic import BaseModel`):
```python
from pydantic import BaseModel, Field
```

---

### `cli/infracanvas/main.py` (controller, request-response) — MODIFY

**Integration wiring** — the scan pipeline currently calls `estimator.estimate(graph)`. After that call (at ~lines 688 and ~796 per RESEARCH.md), add:

```python
from infracanvas.cost.allocator import SharedCostAllocator
from infracanvas.cost.idle import IdleDetector

# After: graph = estimator.estimate(graph)
allocator = SharedCostAllocator(workload_tag_key=config.costlens.workload_tag_key)
graph = allocator.allocate(graph)
detector = IdleDetector()
graph = detector.detect(graph)
```

**Error handling pattern** (mirrors existing try-except in main.py around `parse_directory()`):
```python
try:
    graph = allocator.allocate(graph)
    graph = detector.detect(graph)
except Exception as exc:
    console.print(f"[yellow]Warning:[/yellow] CostLens allocation failed: {exc}")
    # Non-fatal — scan continues without costlens block
```

---

### `viewer/src/types.ts` (model) — MODIFY

**Analog:** existing interface pattern in types.ts (lines 1–151)

**Existing pattern** — each new model from Python maps 1:1 to a TypeScript interface:
```typescript
// Python CostEstimate → TypeScript CostEstimate (already present, lines 34–38)
export interface CostEstimate {
  monthly_usd: number;
  currency: string;
  basis: string;
}

// Python NetworkPath → TypeScript NetworkPath (lines 102–109)
export interface NetworkPath {
  id: string;
  source_node_id: string;
  dest_node_id: string;
  direction: 'forward' | 'return';
  hops: PathHop[];
  evidence: Record<string, unknown>;
}
```

**Addition pattern** (insert before the `declare global` block at line 145):
```typescript
// Phase 9: CostLens types (mirror of cli/infracanvas/graph/models.py CostLensData)

export interface CostLineItem {
  resource_id: string;
  resource_type: string;
  label: string;
  monthly_usd: number;
  share_pct: number;
}

export interface WorkloadCost {
  name: string;
  total_monthly_usd: number;
  line_items: CostLineItem[];
}

export interface SharedResourceSummary {
  resource_id: string;
  resource_type: string;
  monthly_usd: number;
  workload_count: number;
}

export interface IdleRecommendation {
  resource_id: string;
  resource_type: string;
  description: string;
  monthly_waste_usd: number;
}

export interface CostLensData {
  workloads: WorkloadCost[];
  shared_resources: SharedResourceSummary[];
  recommendations: IdleRecommendation[];
}
```

**Modify `ResourceGraph`** (add field after `flowmap?: unknown;` at line 143):
```typescript
export interface ResourceGraph {
  ...
  flowmap?: unknown;
  costlens?: CostLensData;   // Phase 9 addition
}
```

---

### `viewer/src/components/TabBar.tsx` (component, event-driven) — MODIFY

**Exact change** — remove `soon: true` from the costlens tab definition (lines 34–38) and update tooltip:

```typescript
// BEFORE (lines 34–38):
{
  id: 'costlens',
  label: 'CostLens',
  soon: true,
  tooltip: 'Shared infrastructure cost allocation — coming in Phase 9',
},

// AFTER:
{
  id: 'costlens',
  label: 'CostLens',
  tooltip: 'Shared infrastructure cost allocation — press 3',
},
```

**Test impact** — RESEARCH.md confirms 6+ TabBar tests assert `SOON` label and `aria-disabled` on the costlens tab. These must be updated in the same task as TabBar.tsx. Test file location: `viewer/src/components/__tests__/TabBar.test.tsx` (verify with grep before editing).

---

### `viewer/src/App.tsx` (component, event-driven) — MODIFY

**Three changes needed:**

**1. Lazy import for CostLensPanel** (lines 11–21, follow FlowMapCanvas lazy pattern):
```typescript
const CostLensPanel = lazy(() =>
  import('./components/costlens/CostLensPanel').then((m) => ({
    default: m.CostLensPanel,
  })),
);
```

**2. Hash routing** (lines 31–42 `readHash` function):
```typescript
// BEFORE:
if (hash === 'flowmap') {
  setActiveTab('flowmap');
} else {
  setActiveTab('canvas');
}

// AFTER:
if (hash === 'flowmap') {
  setActiveTab('flowmap');
} else if (hash === 'costlens') {
  setActiveTab('costlens');
} else {
  setActiveTab('canvas');
}
```

**3. Keyboard shortcut + render branch** (lines 82–128):
```typescript
// Add '3' → costlens (after existing '2' handler at line 83):
if (e.key === '3' && !e.metaKey && !e.ctrlKey && !e.altKey) {
  setActiveTab('costlens');
  return;
}

// Replace two-way isFlowMap branch (line 91) with three-way:
const isCostLens = activeTab === 'costlens';
const isFlowMap = activeTab === 'flowmap';

// In render (replace lines 104–124):
{isCostLens ? (
  <Suspense fallback={<div className="flex-1" />}>
    <CostLensPanel data={graph?.costlens ?? null} />
  </Suspense>
) : isFlowMap ? (
  hasFlowMap ? (
    <Suspense fallback={<div className="flex-1" />}>
      <FlowMapFilterPanel />
      <div className="flex-1 min-w-0">
        <FlowMapCanvas />
      </div>
      <PathDetailPanel />
    </Suspense>
  ) : (
    <FlowMapEmptyState />
  )
) : (
  <>
    <FilterPanel />
    <div className="flex-1 min-w-0">
      <DiagramCanvas />
    </div>
    <DetailPanel />
  </>
)}
```

**Note:** `graph` is not directly in scope in App.tsx — it must be read from store: `const graph = useViewerStoreOrSingleton((s) => s.graph);`

---

### `viewer/src/components/costlens/CostLensPanel.tsx` (component, request-response) — NEW

**Analog:** `viewer/src/components/flowmap/FlowMapEmptyState.tsx` (for empty state) + `viewer/src/components/flowmap/PathDetailPanel.tsx` (for detail layout)

**Imports pattern** (from PathDetailPanel.tsx lines 1–6):
```typescript
import { useState } from 'react';
import { DollarSign } from 'lucide-react';
import type { CostLensData } from '../../types';
```

**Component structure** (FlowMapEmptyState pattern lines 6–148 for null data case):
```typescript
export function CostLensPanel({ data }: { data: CostLensData | null }) {
  if (!data) {
    return (
      <div
        role="status"
        style={{ width: '100%', height: '100%', display: 'flex',
                 alignItems: 'center', justifyContent: 'center',
                 background: '#FAFBFC' }}
      >
        <div style={{ width: 520, background: '#FFFFFF', border: '1px solid #E2E8F0',
                      borderRadius: 12, boxShadow: '0 4px 16px rgba(15,23,42,0.04)',
                      padding: 32, display: 'flex', flexDirection: 'column',
                      alignItems: 'flex-start', gap: 16 }}>
          <DollarSign size={40} color="#94A3B8" />
          <h2 style={{ fontSize: 13, fontWeight: 600, color: '#0F172A', margin: 0 }}>
            No cost allocation data
          </h2>
          <p style={{ fontSize: 11, fontWeight: 500, color: '#475569',
                      lineHeight: 1.45, margin: 0 }}>
            Re-run with the latest CLI version to collect shared cost allocation data.
          </p>
        </div>
      </div>
    );
  }
  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 24, background: '#FAFBFC' }}>
      {/* Workload cards grid */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {data.workloads.map((wl) => <WorkloadCard key={wl.name} workload={wl} />)}
      </div>
      {/* Idle recommendations section */}
      {data.recommendations.length > 0 && (
        <IdleRecommendations recommendations={data.recommendations} />
      )}
    </div>
  );
}
```

---

### `viewer/src/components/costlens/WorkloadCard.tsx` (component, request-response) — NEW

**Analog:** `viewer/src/components/flowmap/PathDetailPanel.tsx` (OverviewTab / Row pattern, lines 136–154)

**Row helper pattern** (PathDetailPanel.tsx lines 147–154):
```typescript
function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
      <span style={{ color: '#4a5568' }}>{label}</span>
      <span style={{ color: '#e2e8f0', fontFamily: 'var(--font-mono)' }}>{value}</span>
    </div>
  );
}
```

**Card structure** (user-confirmed mockup from CONTEXT.md):
```typescript
import type { WorkloadCost } from '../../types';

export function WorkloadCard({ workload }: { workload: WorkloadCost }) {
  return (
    <div style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: 8,
                  padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between',
                    marginBottom: 12 }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: '#0F172A' }}>
          {workload.name}
        </span>
        <span style={{ fontSize: 13, fontWeight: 700, color: '#0F172A',
                       fontFamily: 'var(--font-mono)' }}>
          ${workload.total_monthly_usd.toFixed(2)}/mo
        </span>
      </div>
      {workload.line_items.map((item) => (
        <div key={item.resource_id}
             style={{ display: 'flex', justifyContent: 'space-between',
                      fontSize: 11, color: '#64748B', padding: '2px 0' }}>
          <span>{item.label}</span>
          <span style={{ fontFamily: 'var(--font-mono)' }}>
            ${item.monthly_usd.toFixed(2)}
            {item.share_pct > 0 ? ` (${item.share_pct.toFixed(0)}%)` : ''}
          </span>
        </div>
      ))}
    </div>
  );
}
```

---

### `viewer/src/components/costlens/IdleRecommendations.tsx` (component, request-response) — NEW

**Analog:** `viewer/src/components/flowmap/PathDetailPanel.tsx` (FindingsTab pattern, lines 156–167)

**List pattern** (PathDetailPanel.tsx FindingsTab lines 156–167):
```typescript
function FindingsTab({ findings }: { findings: Finding[] }) {
  if (findings.length === 0) {
    return <p style={{ fontSize: 11, color: '#4a5568' }}>No findings on this node.</p>;
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {findings.map((f, i) => (
        <FindingCard key={`${f.rule_id}-${i}`} finding={f} />
      ))}
    </div>
  );
}
```

**Component structure**:
```typescript
import type { IdleRecommendation } from '../../types';

export function IdleRecommendations({ recommendations }: { recommendations: IdleRecommendation[] }) {
  return (
    <div style={{ marginTop: 32 }}>
      <h3 style={{ fontSize: 12, fontWeight: 700, color: '#475569',
                   textTransform: 'uppercase', letterSpacing: '0.05em',
                   marginBottom: 12 }}>
        Idle / Oversized
      </h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {recommendations.map((rec) => (
          <div key={rec.resource_id}
               style={{ background: '#FFF7ED', border: '1px solid #FED7AA',
                        borderRadius: 6, padding: '10px 14px',
                        display: 'flex', justifyContent: 'space-between',
                        alignItems: 'flex-start', gap: 8 }}>
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#92400E',
                            fontFamily: 'var(--font-mono)' }}>
                {rec.resource_id}
              </div>
              <div style={{ fontSize: 11, color: '#78350F', marginTop: 2 }}>
                {rec.description}
              </div>
            </div>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#B45309',
                           fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>
              ${rec.monthly_waste_usd.toFixed(2)}/mo waste
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

### `dashboard/app/(dashboard)/scans/[id]/ScanDetailTabs.tsx` (component, request-response) — NEW

**Analog:** `dashboard/components/scans/ScanViewerClient.tsx` (lines 1–103)

**Imports pattern** (ScanViewerClient.tsx lines 1–12):
```typescript
'use client'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ViewerProvider, ViewerApp, createViewerStore } from '@infracanvas/viewer'
import '@infracanvas/viewer/styles.css'
import type { ResourceGraph, ViewerStoreApi } from '@infracanvas/viewer'
import { fetchScanJson } from '@/lib/r2'
```

**Data fetch + loading/error pattern** (ScanViewerClient.tsx lines 23–103) — copy exactly, but lift the `graph` state up to share between viewer and cost tab:
```typescript
'use client'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { ViewerProvider, ViewerApp, createViewerStore } from '@infracanvas/viewer'
import '@infracanvas/viewer/styles.css'
import type { ResourceGraph, ViewerStoreApi, CostLensData } from '@infracanvas/viewer'
import { fetchScanJson } from '@/lib/r2'
import { CostTab } from './CostTab'

interface Props {
  scanId: string
  initialPresignedUrl: string
}

export function ScanDetailTabs({ scanId, initialPresignedUrl }: Props) {
  const store: ViewerStoreApi = useMemo(() => createViewerStore(), [scanId])
  const [graph, setGraph] = useState<ResourceGraph | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const getFreshPresignedUrl = useCallback(async (): Promise<string> => {
    const res = await fetch(`/api/scan-presigned?id=${scanId}`)
    if (!res.ok) throw new Error(`Failed to refresh presigned URL: ${res.status}`)
    const data = (await res.json()) as { presigned_get_url: string }
    return data.presigned_get_url
  }, [scanId])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchScanJson({ presignedUrl: initialPresignedUrl, onPresignedExpired: getFreshPresignedUrl })
      .then((data) => {
        if (!cancelled) {
          store.getState().setGraph(data)
          store.getState().setHasFlowMap(Boolean(data.network_paths?.length))
          setGraph(data)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load scan')
          setLoading(false)
        }
      })
    return () => { cancelled = true }
  }, [initialPresignedUrl, getFreshPresignedUrl, store])

  if (loading) {
    return <div className="flex items-center justify-center h-full text-sm text-slate-500">Loading…</div>
  }
  if (error || !graph) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3">
        <p className="text-sm text-slate-900 font-semibold">Could not load scan</p>
        <p className="text-xs text-slate-500">{error ?? 'Unknown error'}</p>
      </div>
    )
  }

  return (
    <Tabs defaultValue="viewer" className="h-full flex flex-col">
      <TabsList variant="line" className="px-4 border-b border-slate-200">
        <TabsTrigger value="viewer">Viewer</TabsTrigger>
        <TabsTrigger value="cost">Cost</TabsTrigger>
      </TabsList>
      <TabsContent value="viewer" className="flex-1 min-h-0">
        <ViewerProvider store={store}>
          <ViewerApp />
        </ViewerProvider>
      </TabsContent>
      <TabsContent value="cost" className="flex-1 overflow-auto">
        <CostTab data={graph.costlens ?? null} />
      </TabsContent>
    </Tabs>
  )
}
```

**shadcn Tabs** — `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent` are already installed at `dashboard/components/ui/tabs.tsx` (confirmed). Use `variant="line"` from the `tabsListVariants` CVA in tabs.tsx.

---

### `dashboard/app/(dashboard)/scans/[id]/CostTab.tsx` (component, request-response) — NEW

**Analog:** `dashboard/components/scans/ScanViewerClient.tsx` (error/empty state pattern)

**Pattern** — thin wrapper, receives `CostLensData | null`, renders WorkloadTable + IdleRecommendationsList:
```typescript
import type { CostLensData } from '@infracanvas/viewer'
import { WorkloadTable } from '@/components/scans/WorkloadTable'
import { IdleRecommendationsList } from '@/components/scans/IdleRecommendationsList'

interface Props {
  data: CostLensData | null
}

export function CostTab({ data }: Props) {
  if (!data) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-slate-500">
        No cost allocation data. Re-run with a recent CLI version.
      </div>
    )
  }
  return (
    <div className="p-6 space-y-8">
      <WorkloadTable workloads={data.workloads} />
      {data.recommendations.length > 0 && (
        <IdleRecommendationsList recommendations={data.recommendations} />
      )}
    </div>
  )
}
```

---

### `dashboard/components/scans/WorkloadTable.tsx` (component, CRUD) — NEW

**Analog:** `dashboard/components/scans/ScansTable.tsx` (lines 1–196 — shadcn table with thead/tbody/tr/td)

**Imports pattern** (ScansTable.tsx lines 1–7):
```typescript
'use client'
import { useRouter } from 'next/navigation'
import { Terminal, Upload, Zap } from 'lucide-react'
import type { ScanListResp, ScanListItem } from '@/lib/types'
```
New file adapts to:
```typescript
'use client'
import type { WorkloadCost } from '@infracanvas/viewer'
```

**Table skeleton pattern** (ScansTable.tsx lines 111–196):
```typescript
// ScansTable's exact HTML table structure to copy:
<div className="mt-4 overflow-x-auto">
  <div className="bg-white border border-slate-200 rounded-lg overflow-hidden"
       data-testid="workload-table">
    <table className="w-full">
      <thead className="bg-slate-50 border-b border-slate-200">
        <tr>
          {COLUMNS.map(col => (
            <th key={col}
                className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              {col}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {workloads.map(wl => (
          <tr key={wl.name}
              className="border-b border-slate-100 last:border-b-0 hover:bg-slate-50">
            <td className="px-4 py-3 text-sm font-medium text-slate-900">{wl.name}</td>
            <td className="px-4 py-3 font-mono text-sm tabular-nums text-slate-900">
              ${wl.total_monthly_usd.toFixed(2)}/mo
            </td>
            <td className="px-4 py-3 text-sm text-slate-600">
              {wl.line_items.filter(i => i.share_pct > 0).map(i => i.label).join(' + ') || '—'}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
</div>
```

**Columns**: `['Workload', 'Allocated', 'Shared Resources']` — matching user-confirmed mockup from CONTEXT.md.

---

### `dashboard/components/scans/IdleRecommendationsList.tsx` (component, CRUD) — NEW

**Analog:** `dashboard/components/scans/ScansTable.tsx` (empty state + list pattern)

**Pattern** — shadcn Card-style list (card.tsx is present in `dashboard/components/ui/`):
```typescript
'use client'
import type { IdleRecommendation } from '@infracanvas/viewer'

const COLUMNS = ['Resource', 'Signal', 'Monthly Waste']

export function IdleRecommendationsList({ recommendations }: { recommendations: IdleRecommendation[] }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-900 mb-3">
        Idle / Oversized Recommendations
      </h3>
      <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              {COLUMNS.map(col => (
                <th key={col}
                    className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {recommendations.map((rec) => (
              <tr key={rec.resource_id}
                  className="border-b border-slate-100 last:border-b-0">
                <td className="px-4 py-3 font-mono text-sm text-slate-900">{rec.resource_id}</td>
                <td className="px-4 py-3 text-sm text-slate-600">{rec.description}</td>
                <td className="px-4 py-3 font-mono text-sm font-semibold text-amber-600">
                  ${rec.monthly_waste_usd.toFixed(2)}/mo
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
```

**Note:** `badge` and `tooltip` shadcn components are NOT yet installed (confirmed absent from `dashboard/components/ui/`). Install before building dashboard UI tasks:
```bash
cd dashboard && npx shadcn@latest add badge tooltip
```

---

### `dashboard/app/(dashboard)/scans/[id]/renderScanByStatus.tsx` (utility) — MODIFY

**Exact change** — replace `<ScanViewerClient .../>` with `<ScanDetailTabs .../>` for the `ready` case (lines 26–33):

```typescript
// BEFORE (lines 26–33):
if (scan.status === 'ready' && scan.presigned_get_url) {
  return (
    <ScanViewerClient
      scanId={scan.id}
      initialPresignedUrl={scan.presigned_get_url}
    />
  )
}

// AFTER:
if (scan.status === 'ready' && scan.presigned_get_url) {
  return (
    <ScanDetailTabs
      scanId={scan.id}
      initialPresignedUrl={scan.presigned_get_url}
    />
  )
}
```

**Import change** — replace `ScanViewerClient` import with `ScanDetailTabs`:
```typescript
// BEFORE (line 3):
import { ScanViewerClient } from '@/components/scans/ScanViewerClient'

// AFTER:
import { ScanDetailTabs } from './ScanDetailTabs'
```

---

### `viewer/src/components/flowmap/PathDetailPanel.tsx` (component) — MODIFY (CPC-03)

**Addition** — add a `Cost` tab to the existing tab array (lines 60–65) and a new `CostTab` sub-component.

**Existing tab pattern** (lines 60–65):
```typescript
const tabs: Array<{ id: Tab; label: string; icon: typeof FileText }> = [
  { id: 'overview', label: 'Overview', icon: FileText },
  { id: 'findings', label: `Findings (${node.findings.length})`, icon: Shield },
  { id: 'attributes', label: 'Attributes', icon: Code },
  ...(hasRoutes ? [{ id: 'routes' as const, label: 'Routes', icon: List }] : []),
];
```

**Type extension**:
```typescript
// BEFORE:
type Tab = 'overview' | 'findings' | 'attributes' | 'routes';

// AFTER:
type Tab = 'overview' | 'findings' | 'attributes' | 'routes' | 'cost';
```

**Tab addition** (append to tabs array, only when node has cost data):
```typescript
const hasCost = node.cost.monthly_usd > 0;
// in tabs array:
...(hasCost ? [{ id: 'cost' as const, label: 'Cost', icon: DollarSign }] : []),
```

**Tab content** (follow OverviewTab Row pattern from lines 136–145):
```typescript
{activeTab === 'cost' && hasCost && <CostTab node={node} />}

function CostTab({ node }: { node: ResourceNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 11, color: '#94A3B8' }}>
      <Row label="Monthly Cost" value={`$${node.cost.monthly_usd.toFixed(2)}`} />
      <Row label="Basis" value={node.cost.basis || '—'} />
    </div>
  );
}
```

**Import addition** (line 2, alongside existing lucide icons):
```typescript
import { X, Network, FileText, Shield, Code, List, DollarSign } from 'lucide-react';
```

---

## Shared Patterns

### Python module header
**Source:** `cli/infracanvas/cost/estimator.py` lines 1–8
**Apply to:** `allocator.py`, `idle.py`, `egress.py`
```python
"""<docstring>"""

from __future__ import annotations

from typing import Any   # only if needed

from infracanvas.graph.models import ResourceGraph   # + new model names
```

### Python class with graph-mutating method
**Source:** `cli/infracanvas/cost/estimator.py` lines 110–137
**Apply to:** `allocator.py`, `idle.py`
- Constructor takes config via `__init__`
- Single public method: `def method(self, graph: ResourceGraph) -> ResourceGraph`
- Returns the mutated graph
- Module-level private helper functions for sub-computations

### Python test pattern
**Source:** `cli/tests/test_cost.py` lines 1–100
**Apply to:** new `cli/tests/test_allocator.py`, `cli/tests/test_idle.py`
```python
"""Tests for the shared cost allocator (CLA-C-N)."""
import pytest
from infracanvas.cost.allocator import SharedCostAllocator
from infracanvas.graph.models import ResourceGraph, ResourceNode

def _node(resource_type: str, name: str, attrs: dict) -> ResourceNode:
    return ResourceNode(
        id=f"{resource_type}.{name}",
        type=resource_type,
        name=name,
        provider="aws",
        attributes=attrs,
    )

class TestSharedCostAllocator:
    def test_equal_split_two_workloads(self):
        """CLA-C-1: Two attached workloads receive 50% share each."""
        ...
```
Test IDs follow `CLA-C-N` (allocator) and `CPC-C-N` (egress) naming per CONTEXT.md conventions.

### Viewer inline style pattern (not Tailwind)
**Source:** `viewer/src/components/flowmap/FlowMapEmptyState.tsx`, `viewer/src/components/flowmap/PathDetailPanel.tsx`
**Apply to:** All new `viewer/src/components/costlens/` files
- Inline `style={{}}` objects, NOT Tailwind classes
- Color constants: `#0F172A` (dark text), `#475569` (body), `#94A3B8` (muted), `#E2E8F0` (border), `#3B82F6` (accent blue)
- Font mono via `fontFamily: 'var(--font-mono)'` for numeric values
- No CSS modules, no external CSS files

### Dashboard client component pattern
**Source:** `dashboard/components/scans/ScanViewerClient.tsx` lines 1–103
**Apply to:** `ScanDetailTabs.tsx`, `CostTab.tsx`
- `'use client'` directive at line 1
- `useState` + `useEffect` for async data loading
- `cancelled` flag in useEffect cleanup to prevent state updates after unmount
- Loading state: `<div className="flex items-center justify-center h-full text-sm text-slate-500">`
- Error state: `<div className="flex flex-col items-center justify-center h-full gap-3">`

### Dashboard table pattern (shadcn-free, native HTML table)
**Source:** `dashboard/components/scans/ScansTable.tsx` lines 111–196
**Apply to:** `WorkloadTable.tsx`, `IdleRecommendationsList.tsx`
- `data-testid` attribute on outer wrapper
- `bg-white border border-slate-200 rounded-lg overflow-hidden` outer container
- `thead`: `bg-slate-50 border-b border-slate-200`
- `th`: `px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500`
- `tr`: `border-b border-slate-100 last:border-b-0 hover:bg-slate-50`
- `td`: `px-4 py-3 text-sm`

### CostLensData type export from viewer package
**Source:** `dashboard/lib/types.ts` lines 1–8 (re-export pattern from `@infracanvas/viewer`)
**Apply to:** `dashboard/lib/types.ts` (add `CostLensData` to re-export list), `ScanDetailTabs.tsx`, `CostTab.tsx`, `WorkloadTable.tsx`, `IdleRecommendationsList.tsx`
```typescript
// dashboard/lib/types.ts addition:
export type {
  ResourceGraph,
  GraphSummary,
  Finding,
  Severity,
  DriftStatus,
  CostLensData,      // Phase 9 addition
  WorkloadCost,      // Phase 9 addition
  IdleRecommendation, // Phase 9 addition
} from '@infracanvas/viewer'
```
This requires `CostLensData` to first be exported from the viewer package via `viewer/src/index.ts`.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `cli/infracanvas/cost/egress.py` | service | transform | Closest is estimator.py (static pricing table pattern is identical — not truly "no analog", listed here for awareness) |

All other files have close analogs in the codebase. No file requires purely novel patterns.

---

## Pre-conditions / Blockers

1. **shadcn badge + tooltip not installed** — `dashboard/components/ui/badge.tsx` and `tooltip.tsx` are absent. Run `cd dashboard && npx shadcn@latest add badge tooltip` before any dashboard UI task.
2. **viewer package exports** — `CostLensData` and sibling interfaces must be added to `viewer/src/index.ts` exports before `dashboard/lib/types.ts` can re-export them.
3. **TabBar tests** — 6+ tests in `viewer/src/components/__tests__/TabBar.test.tsx` assert `soon` / `aria-disabled` on the costlens tab. Must be updated in the same task as TabBar.tsx change.

---

## Metadata

**Analog search scope:** `cli/infracanvas/cost/`, `cli/infracanvas/graph/`, `cli/infracanvas/config.py`, `cli/infracanvas/main.py`, `viewer/src/`, `dashboard/app/(dashboard)/scans/[id]/`, `dashboard/components/scans/`, `dashboard/components/ui/`, `dashboard/lib/`
**Files scanned:** 22
**Pattern extraction date:** 2026-05-06
