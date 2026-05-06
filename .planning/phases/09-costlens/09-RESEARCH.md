# Phase 9: CostLens — Research

**Researched:** 2026-05-06
**Domain:** Shared-cost allocation engine, idle detection, viewer tab activation, dashboard Cost tab, FlowMap per-path cost
**Confidence:** HIGH — all findings verified against live codebase; no speculative claims

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Equal split — divide each shared resource's monthly cost evenly by count of distinct workloads attached to it. No traffic weighting.
- **D-02:** Workload tag key is configurable via `infracanvas.yaml` under `costlens.workload_tag_key`. Default: `Service`.
- **D-03:** Resources with no matching tag → synthetic `'untagged'` workload. They receive a full equal share. Allocation percentages must sum to 100% per shared resource.
- **D-04:** Static Terraform heuristics only for idle detection:
  - `aws_nat_gateway` with zero `aws_route` entries referencing it → idle
  - `aws_ec2_transit_gateway` with no `aws_ec2_transit_gateway_vpc_attachment` children → idle
  - `azurerm_express_route_circuit` with no `azurerm_virtual_network_gateway_connection` children → idle
  - `aws_vpc_endpoint` with no associated route tables in the graph → idle
- **D-05:** Activate existing `costlens` tab (remove `soon: true`). Layout: workload-view cards.
- **D-06:** Idle/oversized recommendations as bottom section of CostLens tab (below workload cards).
- **D-07:** Dashboard 'Cost' tab on scan detail page — native React table reading `costlens` from R2 JSON.
- **D-08:** CLI extends scan JSON with top-level `costlens` block at scan time.
- **CPC-01:** Topology-based cross-cloud egress cost estimation using static pricing tables.
- **CPC-03:** Cost-aware path ranking in FlowMap PathDetailPanel.

### Claude's Discretion
- CPC-01/03 implementation details — static egress rate table design, PathDetailPanel integration approach.

### Deferred Ideas (OUT OF SCOPE)
- **CPC-02:** Flow-log-driven data transfer attribution → Phase 12
- **Per-team cost aggregation:** Cross-scan cost rollup and `/costlens` top-level SaaS route
- **CloudWatch / Azure Monitor idle detection:** Usage-based signals
- **Tag-based weighting:** Tag-weighted allocation beyond equal split
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CLA-01 | TGW attachment cost split by workload tag | New `SharedCostAllocator` in `cli/infracanvas/cost/allocator.py`; reads `aws_ec2_transit_gateway` nodes + attachment edges from graph |
| CLA-02 | ExpressRoute circuit cost split by connected vNet workload tag | Same allocator; reads `azurerm_express_route_circuit` nodes + vNet attachment edges |
| CLA-03 | Azure Firewall cost split by route-table-referenced workloads | Same allocator; reads `azurerm_firewall` nodes + route table edges |
| CLA-04 | Shared NAT Gateway + VPC Endpoint cost split by traffic share | Same allocator; reads `aws_nat_gateway` + `aws_vpc_endpoint` nodes + subnet/route-table edges |
| CLA-05 | Idle/oversized resource recommendations | New `IdleDetector` in `cli/infracanvas/cost/idle.py`; static Terraform graph heuristics per D-04 |
| CLA-06 | CostLens dashboard panel showing allocated vs shared cost per workload | Dashboard `CostTab.tsx` + `WorkloadTable.tsx` + `IdleRecommendationsList.tsx`; reads `costlens` key from R2 JSON |
| CPC-01 | Per-path cross-cloud data transfer cost computation | New egress pricing tables in `cli/infracanvas/cost/egress.py`; applied to `network_paths` edges |
| CPC-03 | Cost-aware path ranking in FlowMap viewer | Extend `PathDetailPanel.tsx` with per-path transfer cost annotation and sort |
</phase_requirements>

---

## Summary

Phase 9 delivers CostLens: a shared-cost allocation engine layered on top of the existing per-resource cost estimator, plus viewer/dashboard surfaces to present the results. The work spans five distinct components: (1) a new Python `SharedCostAllocator` that post-processes the graph after `CostEstimator.estimate()`, (2) a new `IdleDetector` using static graph heuristics, (3) a `costlens` block appended to scan JSON output, (4) a React `CostLensPanel` component tree activated in the viewer's existing `costlens` tab slot, and (5) a native dashboard 'Cost' tab on the scan detail page.

The architecture is consistent with every prior phase: CLI pre-computes everything and embeds it in JSON; UI surfaces are read-only consumers. No new backend endpoints are required — the `costlens` block rides in the existing R2 scan JSON that `ScanViewerClient` already fetches. The allocation model is pure Python over the in-memory `ResourceGraph`; workload discovery requires only reading `node.attributes` for the configured tag key and traversing `graph.edges` to find attachment relationships.

The two non-trivial implementation risks are (1) the existing TabBar tests are hardcoded to assert `SOON` label and `aria-disabled` on the costlens tab — activating the tab will cause ~5 test failures that must be updated in the same task; and (2) badge and tooltip shadcn components are not yet installed in the dashboard — they must be added via `npx shadcn add` before building dashboard UI components.

**Primary recommendation:** Implement in 4 waves: Wave 0 (data models + config), Wave 1 (Python allocation engine + idle detector), Wave 2 (viewer CostLens tab components), Wave 3 (dashboard Cost tab + CPC-01/CPC-03).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Shared cost allocation computation | CLI (Python) | — | Pre-computed at scan time; follows established ResourceGraph-as-output pattern |
| Idle detection heuristics | CLI (Python) | — | Graph traversal over Terraform data; no runtime required |
| costlens JSON block | CLI export layer | — | `export_graph()` calls `graph.model_dump_json()` — adding field to `ResourceGraph` Pydantic model is sufficient |
| Workload card UI | Browser (Viewer) | — | HTML report; consumes `graph.costlens` from `window.__INFRACANVAS_DATA__` |
| Dashboard Cost tab | Browser (Dashboard RSC → Client) | — | RSC fetches scan metadata; client fetches R2 JSON and renders `costlens` key |
| Per-path egress cost | CLI (Python) | Viewer (display) | Rates computed at scan time; FlowMap PathDetailPanel annotates edges from pre-computed data |
| shadcn badge + tooltip | Dashboard browser | — | Missing components; must be installed before dashboard UI tasks |

---

## Technical Approach

### Component 1: SharedCostAllocator (CLA-01..04)

**File:** `cli/infracanvas/cost/allocator.py` (new)

The allocator runs as a second pass after `CostEstimator.estimate(graph)`. It:

1. Reads `costlens.workload_tag_key` from `InfraCanvasConfig` (default: `'Service'`)
2. Identifies shared resource nodes by type:
   - `aws_ec2_transit_gateway`
   - `azurerm_express_route_circuit`
   - `azurerm_firewall`
   - `aws_nat_gateway`
   - `aws_vpc_endpoint`
3. For each shared resource, traverses `graph.edges` to find attached nodes (any edge where `source` or `target` equals the shared resource's id)
4. For each attached node, reads `node.attributes.get(workload_tag_key, None)` to determine workload name; uses `'untagged'` if absent
5. Collects distinct workload names → `workload_count = len(distinct_workloads)`
6. Splits `shared_node.cost.monthly_usd / workload_count` equally to each workload
7. Aggregates per-workload: total allocated cost + line items (shared resource name, $ amount, % share)
8. Returns a `CostLensData` Pydantic model

**Allocation guarantee (CLA success criterion 4):** `sum(share_pct for workload in shared_resource.workloads) == 100.0`. Use integer rounding + distribute remainder to first workload.

**Edge case — shared resource with no attachments:** `workload_count = 0` → skip (no allocation; resource still visible in `shared_resources` list with note "no attached workloads").

**Dedicated resource cost inclusion:** Each workload's card also shows per-node dedicated costs. These are the `node.cost.monthly_usd` values for non-shared nodes whose tag matches the workload.

### Component 2: IdleDetector (CLA-05)

**File:** `cli/infracanvas/cost/idle.py` (new)

Four heuristics from D-04, each operating purely on `graph.nodes` and `graph.edges`:

```
idle_nat_gateway(node, graph):
    # idle if no aws_route node has an edge pointing to this NAT GW
    return node.type == 'aws_nat_gateway' and
           not any(
               e['target'] == node.id and
               _node_by_id(graph, e['source']).type == 'aws_route'
               for e in graph.edges
           )

idle_tgw(node, graph):
    # idle if no aws_ec2_transit_gateway_vpc_attachment child
    return node.type == 'aws_ec2_transit_gateway' and
           not any(
               e['source'] == node.id and
               _node_by_id(graph, e['target']).type == 'aws_ec2_transit_gateway_vpc_attachment'
               for e in graph.edges
           )

idle_express_route(node, graph):
    # idle if no azurerm_virtual_network_gateway_connection child
    return node.type == 'azurerm_express_route_circuit' and
           not any(
               e['source'] == node.id and
               _node_by_id(graph, e['target']).type == 'azurerm_virtual_network_gateway_connection'
               for e in graph.edges
           )

idle_vpc_endpoint(node, graph):
    # idle if no aws_route_table has an edge to this endpoint
    return node.type == 'aws_vpc_endpoint' and
           not any(
               e['target'] == node.id and
               _node_by_id(graph, e['source']).type == 'aws_route_table'
               for e in graph.edges
           )
```

Each idle node produces an `IdleRecommendation`: `resource_id`, `type` (e.g. `aws_nat_gateway`), `description` (human-readable signal), `monthly_waste_usd` (from `node.cost.monthly_usd`).

**Note:** `graph.edges` is `list[dict[str, str]]` — dicts with `"source"` and `"target"` string keys. The helper `_node_by_id(graph, id)` can raise `KeyError` if an edge references a node not in `graph.nodes` — guard with a try/except or pre-build a `{node.id: node}` lookup dict.

### Component 3: CostLensData Pydantic model (D-08)

**File:** `cli/infracanvas/graph/models.py` (modify — add after `ResourceGraph`)

```python
class CostLineItem(BaseModel):
    resource_id: str
    resource_type: str
    label: str          # human display name
    monthly_usd: float
    share_pct: float    # 0.0 for dedicated; allocation % for shared

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

Add to `ResourceGraph`:
```python
costlens: CostLensData | None = None
```

Since `export_graph()` calls `graph.model_dump_json()`, the `costlens` field serializes automatically. No changes needed to `export/json.py`.

### Component 4: Config extension (D-02)

**File:** `cli/infracanvas/config.py` (modify)

`InfraCanvasConfig` currently has no nested config. The simplest approach that avoids a breaking schema change: add a new optional `CostLensConfig` model and an optional field:

```python
class CostLensConfig(BaseModel):
    workload_tag_key: str = "Service"

class InfraCanvasConfig(BaseModel):
    # ... existing fields ...
    costlens: CostLensConfig = Field(default_factory=CostLensConfig)
```

YAML format (backwards-compatible — existing configs without `costlens:` get defaults):
```yaml
costlens:
  workload_tag_key: Service
```

### Component 5: CLI integration in main.py (D-08)

**File:** `cli/infracanvas/main.py` (modify — two scan callsites)

After `graph = estimator.estimate(graph)` at lines ~688 and ~796:
```python
from infracanvas.cost.allocator import SharedCostAllocator
from infracanvas.cost.idle import IdleDetector

allocator = SharedCostAllocator(workload_tag_key=config.costlens.workload_tag_key)
graph = allocator.allocate(graph)

detector = IdleDetector()
graph = detector.detect(graph)
```

`allocator.allocate()` and `detector.detect()` both return the mutated `ResourceGraph` with `graph.costlens` populated.

### Component 6: Viewer CostLens tab (D-05, D-06)

**Three new files:**
- `viewer/src/components/costlens/CostLensPanel.tsx`
- `viewer/src/components/costlens/WorkloadCard.tsx`
- `viewer/src/components/costlens/IdleRecommendations.tsx`

**App.tsx modification:** The current `isFlowMap` branch in `App.tsx` (line 91) only handles `canvas` vs `flowmap`. The `costlens` case falls through to the canvas branch. Replace with a three-way branch:

```tsx
const isCostLens = activeTab === 'costlens';
const isFlowMap = activeTab === 'flowmap';

// in render:
{isCostLens ? (
  <CostLensPanel data={graph?.costlens ?? null} />
) : isFlowMap ? (
  // existing FlowMap branch
) : (
  // existing canvas branch
)}
```

**viewer/src/types.ts:** Add `CostLensData` interface and mark `ResourceGraph.costlens` as `CostLensData | undefined`.

**viewer/src/index.ts:** Export `CostLensData` type and `CostLensPanel` component.

**TabBar.tsx modification:** Remove `soon: true` from the costlens tab definition (line 36). Update tooltip text to `'Shared infrastructure cost allocation'` per UI-SPEC copywriting.

**Keyboard shortcuts:** `App.tsx` currently binds `'3'` to nothing. Add `'3'` → `setActiveTab('costlens')` in the keyboard handler (lines 54–89).

**Hash routing:** The `readHash` function in App.tsx only handles `'flowmap'`. Add `'costlens'` case.

### Component 7: Dashboard Cost tab (D-07, CLA-06)

**Architecture:** The scan detail page is an RSC that fetches scan metadata (including `presigned_get_url`) from the backend. The viewer is rendered by `ScanViewerClient` which client-side fetches the full scan JSON from R2. The Cost tab needs the same data — the `costlens` block is inside that R2 JSON.

**Integration pattern:** `ScanViewerClient` already fetches the full `ResourceGraph` (which includes `costlens`). The simplest architecture is a sibling client component `CostTabClient` that also fetches from the same presigned URL. However, to avoid double-fetching R2, the cleanest approach is to refactor the scan detail page to use shadcn `Tabs` at the page level, with both viewer and cost tab sharing the same fetched data.

**Recommended approach:** Wrap both `ScanViewerClient` and a new `CostTabClient` inside a new `ScanDetailTabs` client component that:
1. Fetches the scan JSON once (using same `fetchScanJson` + presigned URL pattern)
2. Passes `data.costlens` to `CostTabClient`
3. Passes full `data` (as `ResourceGraph`) to the viewer

**New files:**
- `dashboard/app/(dashboard)/scans/[id]/ScanDetailTabs.tsx` — client component, tab switcher (shadcn Tabs: "viewer" + "cost")
- `dashboard/app/(dashboard)/scans/[id]/CostTab.tsx` — receives `CostLensData | null`, renders WorkloadTable + IdleRecommendationsList
- `dashboard/components/scans/WorkloadTable.tsx` — shadcn Table, expandable rows with accordion chevron
- `dashboard/components/scans/IdleRecommendationsList.tsx` — shadcn Card list, WasteBadge inline

**renderScanByStatus.tsx modification:** Replace `<ScanViewerClient .../>` with `<ScanDetailTabs scanId={scan.id} initialPresignedUrl={scan.presigned_get_url} />` for the `ready` case.

**Missing shadcn components to install:**
- `badge` — not present in `dashboard/components/ui/`
- `tooltip` — not present in `dashboard/components/ui/`

Install before any dashboard UI task:
```bash
cd dashboard && npx shadcn@latest add badge tooltip
```

**dashboard/lib/types.ts:** Add `CostLensData` and child interfaces, mirroring the Python Pydantic models. Re-export from `@infracanvas/viewer` once viewer exports them.

### Component 8: CPC-01 — Cross-cloud egress cost (CPC-01)

**File:** `cli/infracanvas/cost/egress.py` (new)

Static pricing table approach following the existing `FLAT_MONTHLY`/`REGION_MULTIPLIERS` pattern:

```python
# AWS inter-region egress (per GB)
AWS_INTER_REGION_EGRESS: dict[tuple[str, str], float] = {
    ("us-east-1", "eu-west-1"): 0.02,
    ("us-east-1", "ap-southeast-1"): 0.08,
    # etc.
}

# AWS → Internet (per GB)
AWS_INTERNET_EGRESS: dict[str, float] = {
    "us-east-1": 0.09,
    "eu-west-1": 0.09,
    # etc.
}

# Azure egress (per GB, zone 1)
AZURE_EGRESS: dict[str, float] = {
    "East US": 0.087,
    # etc.
}

# Cross-cloud: AWS → Azure, AWS → on-prem
CROSS_CLOUD_EGRESS: float = 0.02  # TGW → ExpressRoute path
```

Applied to `graph.network_paths` edges: for each `NetworkPath`, look up source and dest node regions, determine if inter-region or cross-cloud, apply per-GB rate. Since no flow data exists (CPC-02 deferred), use a configurable `assumed_monthly_gb` default (e.g. 100 GB/mo) with a basis note `"estimated at 100 GB/mo"`.

Results are stored as `path_cost_usd` in a new `PathCost` model added to `NetworkPath`:
```python
class PathCost(BaseModel):
    estimated_monthly_usd: float
    rate_per_gb: float
    assumed_gb: float
    basis: str

# Add to NetworkPath:
path_cost: PathCost | None = None
```

### Component 9: CPC-03 — Cost-aware path ranking (CPC-03)

**File:** `viewer/src/components/flowmap/PathDetailPanel.tsx` (modify)

`PathDetailPanel` currently renders overview/findings/attributes/routes tabs for a selected node. CPC-03 adds cost annotation to edge display — when a path's `path_cost` is populated, show it in the overview tab alongside per-hop detail.

The `selectedPath` state already exists in `store.ts` (`selectedPath: NetworkPath | null`) but is not yet wired to a full path-level display. For Phase 9, the approach is:

1. Add `path_cost` to the `NetworkPath` TypeScript interface in `viewer/src/types.ts`
2. In `PathDetailPanel`, read `selectedPath` from store and display `path_cost.estimated_monthly_usd` when non-null
3. Sort paths by `path_cost.estimated_monthly_usd` ascending in the panel list (cheapest first)

---

## Codebase Inventory

### Files to CREATE

| File | Purpose |
|------|---------|
| `cli/infracanvas/cost/allocator.py` | `SharedCostAllocator` class — shared resource cost splitting |
| `cli/infracanvas/cost/idle.py` | `IdleDetector` class — static graph heuristics |
| `cli/infracanvas/cost/egress.py` | Cross-cloud egress pricing tables + `EgressEstimator` |
| `cli/tests/test_costlens.py` | All CLA-C-N and CPC-C-N pytest tests |
| `viewer/src/components/costlens/CostLensPanel.tsx` | Root CostLens tab panel |
| `viewer/src/components/costlens/WorkloadCard.tsx` | Per-workload card with line-item breakdown |
| `viewer/src/components/costlens/IdleRecommendations.tsx` | Idle recommendations bottom section |
| `dashboard/app/(dashboard)/scans/[id]/ScanDetailTabs.tsx` | Client component: tab switcher + shared R2 fetch |
| `dashboard/app/(dashboard)/scans/[id]/CostTab.tsx` | Cost tab content (receives CostLensData) |
| `dashboard/components/scans/WorkloadTable.tsx` | shadcn Table with expandable rows |
| `dashboard/components/scans/IdleRecommendationsList.tsx` | shadcn Card list of idle recommendations |

### Files to MODIFY

| File | Change | Key Lines |
|------|--------|-----------|
| `cli/infracanvas/graph/models.py` | Add `CostLineItem`, `WorkloadCost`, `SharedResourceSummary`, `IdleRecommendation`, `CostLensData` models; add `costlens: CostLensData \| None = None` to `ResourceGraph` | After line 179 |
| `cli/infracanvas/config.py` | Add `CostLensConfig` nested model; add `costlens: CostLensConfig` field to `InfraCanvasConfig` | Lines 11–16 |
| `cli/infracanvas/main.py` | Import + invoke `SharedCostAllocator` and `IdleDetector` after `estimator.estimate(graph)` at two callsites | Lines ~688, ~796 |
| `viewer/src/types.ts` | Add `CostLensData`, `WorkloadCost`, `CostLineItem`, `IdleRecommendation` interfaces; add `costlens?: CostLensData` to `ResourceGraph`; add `path_cost?: PathCost` to `NetworkPath` | After line 143 |
| `viewer/src/App.tsx` | Three-way `isCostLens / isFlowMap / canvas` branch; add `'3'` keyboard shortcut; add `'costlens'` to hash routing | Lines 91, 31–44, 76–88 |
| `viewer/src/components/TabBar.tsx` | Remove `soon: true` from costlens tab (line 36); update tooltip text | Line 36–38 |
| `viewer/src/index.ts` | Export `CostLensPanel`, `CostLensData` type | After existing exports |
| `viewer/src/__tests__/flowmap/TabBar.test.tsx` | Update 5+ tests that assert `SOON` label, `aria-disabled`, `not-allowed` cursor, keyboard navigation skipping costlens | Lines 29–31, 50–64, 118–145 |
| `dashboard/lib/types.ts` | Add `CostLensData`, `WorkloadCost`, `CostLineItem`, `IdleRecommendation` TypeScript interfaces | After line 60 |
| `dashboard/app/(dashboard)/scans/[id]/renderScanByStatus.tsx` | Replace `<ScanViewerClient>` with `<ScanDetailTabs>` for ready+URL case | Line 26–31 |
| `cli/infracanvas/graph/models.py` | Add `PathCost` model; add `path_cost: PathCost \| None = None` to `NetworkPath` | After line 150 |
| `viewer/src/types.ts` | Add `PathCost` interface; add `path_cost?: PathCost` to `NetworkPath` | Near line 109 |
| `viewer/src/components/flowmap/PathDetailPanel.tsx` | Add cost display in overview tab; sort paths by cost | Lines 60+ |

---

## Implementation Sequence

### Wave 0 — Data models and config (no dependencies, all other waves depend on these)

1. **Task 09-01:** Add Pydantic models to `cli/infracanvas/graph/models.py` (`CostLensData` family + `PathCost`)
2. **Task 09-02:** Add TypeScript interfaces to `viewer/src/types.ts` + `dashboard/lib/types.ts`
3. **Task 09-03:** Extend `InfraCanvasConfig` with `CostLensConfig` in `cli/infracanvas/config.py`
4. **Task 09-04:** Install missing shadcn components (`badge`, `tooltip`) in dashboard

### Wave 1 — Python allocation engine (depends on Wave 0)

5. **Task 09-05:** Implement `SharedCostAllocator` in `cli/infracanvas/cost/allocator.py`
6. **Task 09-06:** Implement `IdleDetector` in `cli/infracanvas/cost/idle.py`
7. **Task 09-07:** Implement `EgressEstimator` in `cli/infracanvas/cost/egress.py` (CPC-01)
8. **Task 09-08:** Wire allocator + idle detector into `cli/infracanvas/main.py` scan callsites
9. **Task 09-09:** Write full pytest suite in `cli/tests/test_costlens.py`

### Wave 2 — Viewer CostLens tab (depends on Wave 0; can run parallel to Wave 1)

10. **Task 09-10:** Implement `CostLensPanel`, `WorkloadCard`, `IdleRecommendations` viewer components
11. **Task 09-11:** Activate `costlens` tab in `TabBar.tsx`; update `App.tsx` three-way branch + keyboard/hash routing
12. **Task 09-12:** Update `viewer/src/__tests__/flowmap/TabBar.test.tsx` (fix 5+ broken tests); add CostLens panel tests
13. **Task 09-13:** Update `viewer/src/index.ts` exports

### Wave 3 — Dashboard Cost tab + FlowMap CPC-03 (depends on Wave 0 + Wave 1 for data)

14. **Task 09-14:** Implement `ScanDetailTabs`, `CostTab` on scan detail page
15. **Task 09-15:** Implement `WorkloadTable`, `IdleRecommendationsList` dashboard components
16. **Task 09-16:** Update `renderScanByStatus.tsx` to use `ScanDetailTabs`
17. **Task 09-17:** Implement CPC-03 cost annotation in `PathDetailPanel.tsx`

---

## Test Strategy

### Existing test infrastructure

- **Framework:** pytest (CLI), Vitest + @testing-library/react (viewer/dashboard)
- **CLI tests location:** `cli/tests/` — pattern `test_*.py`
- **Viewer tests location:** `viewer/src/__tests__/` — pattern `*.test.tsx`
- **Test ID convention:** `CLA-C-N` for CostLens allocation, `CPC-C-N` for cross-cloud path cost
- **Existing cost tests:** `cli/tests/test_cost.py` — IDs `COST-C-1..COST-C-6` + integration tests. Do NOT modify; new tests go in `test_costlens.py`.

### Python test cases (new file: `cli/tests/test_costlens.py`)

```
CLA-C-1: Two workloads share a TGW → each gets 50% of TGW cost
CLA-C-2: Three workloads share a NAT GW → each gets 33.33% (sum = 100%)
CLA-C-3: One tagged + one untagged resource share a VPC endpoint → untagged workload appears
CLA-C-4: Allocation percentages sum to 100.0 for a 3-way split (rounding remainder test)
CLA-C-5: Shared resource with no attached nodes → appears in shared_resources, no workload entries
CLA-C-6: ExpressRoute with two vNet attachments → cost split equally
CLA-C-7: Azure Firewall with three route-table-referenced workloads → three-way split
CLA-C-8: workload_tag_key config respected (non-default key 'Team')
CLA-C-9: Dedicated resource costs (non-shared nodes) included in workload total
CLA-C-10: idle NAT GW with zero route references → recommendation generated with correct waste amount
CLA-C-11: idle TGW with no VPC attachments → recommendation generated
CLA-C-12: idle ExpressRoute with no gateway connections → recommendation generated
CLA-C-13: idle VPC endpoint with no route tables → recommendation generated
CLA-C-14: non-idle NAT GW (has route entry) → no recommendation
CLA-C-15: Integration — full graph scan produces valid CostLensData JSON block
CPC-C-1: Inter-region path AWS us-east-1 → eu-west-1 → correct per-GB rate applied
CPC-C-2: Cross-cloud path (TGW → ExpressRoute) → CROSS_CLOUD_EGRESS rate used
CPC-C-3: Path with no region data → path_cost is None (graceful skip)
```

### Viewer test updates

`viewer/src/__tests__/flowmap/TabBar.test.tsx` — 5 tests MUST be updated:
- Line 29: `'CostLens tab carries SOON label'` → remove test (SOON label gone)
- Line 50: `'ArrowLeft from Canvas wraps to FlowMap (last navigable, skipping CostLens)'` → update to wrap to CostLens
- Line 58: `'End jumps to last navigable tab (FlowMap, not CostLens)'` → update to jump to CostLens
- Lines 118–145: `'TabBar — CostLens "soon" tab is non-interactive'` describe block → delete entirely

New viewer tests to add:
- `CostLensPanel renders workload cards with correct names and amounts`
- `CostLensPanel renders untagged workload card in italic`
- `CostLensPanel renders idle recommendations section`
- `CostLensPanel renders empty state when costlens is null`
- `WorkloadCard shows correct line-item breakdown`
- `CostLens tab is keyboard-navigable after activation (ArrowRight Canvas → FlowMap → CostLens)`

### Dashboard test approach

Dashboard tests use Vitest + @testing-library/react. Follow pattern from `MetadataHeader.test.tsx` and `ScansTable.test.tsx`.

New tests:
- `WorkloadTable renders workload rows with correct data`
- `WorkloadTable chevron expands detail row with aria-expanded`
- `WorkloadTable renders empty state when no workloads`
- `IdleRecommendationsList renders idle recommendations with WasteBadge`
- `CostTab renders skeleton while loading`
- `CostTab renders error state on fetch failure`

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (CLI) | pytest |
| Framework (Viewer/Dashboard) | Vitest 4.1.4 |
| CLI config | `cli/pyproject.toml` |
| Viewer config | `viewer/vitest.config.ts` |
| CLI quick run | `cd cli && python -m pytest tests/test_costlens.py -x` |
| CLI full suite | `cd cli && python -m pytest tests/ -x` |
| Viewer quick run | `cd viewer && npm test -- --run` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLA-01 | TGW cost split by workload tag | unit | `pytest tests/test_costlens.py::TestSharedAllocator::test_tgw_two_workload_split -x` | Wave 1 |
| CLA-02 | ExpressRoute cost split by vNet workload tag | unit | `pytest tests/test_costlens.py::TestSharedAllocator::test_express_route_split -x` | Wave 1 |
| CLA-03 | Azure Firewall cost split by route-table workloads | unit | `pytest tests/test_costlens.py::TestSharedAllocator::test_azure_firewall_split -x` | Wave 1 |
| CLA-04 | NAT GW + VPC Endpoint split | unit | `pytest tests/test_costlens.py::TestSharedAllocator::test_nat_gateway_split -x` | Wave 1 |
| CLA-05 | Idle detection heuristics | unit | `pytest tests/test_costlens.py::TestIdleDetector -x` | Wave 1 |
| CLA-06 | Dashboard cost panel reads costlens block | integration | `cd viewer && npm test -- --run WorkloadTable` | Wave 3 |
| CPC-01 | Per-path egress cost | unit | `pytest tests/test_costlens.py::TestEgressEstimator -x` | Wave 1 |
| CPC-03 | Cost-aware path ranking | component | `cd viewer && npm test -- --run PathDetailPanel` | Wave 3 |

### Sampling Rate
- **Per task commit:** `cd cli && python -m pytest tests/test_costlens.py -x && cd ../viewer && npm test -- --run`
- **Per wave merge:** `cd cli && python -m pytest tests/ && cd ../viewer && npm test -- --run`
- **Phase gate:** Full CLI + viewer suites green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `cli/tests/test_costlens.py` — covers CLA-C-1..CLA-C-15, CPC-C-1..CPC-C-3
- [ ] `viewer/src/__tests__/costlens/CostLensPanel.test.tsx` — covers viewer CostLens rendering
- [ ] `dashboard/components/scans/WorkloadTable.test.tsx` — covers dashboard table

---

## Common Pitfalls

### Pitfall 1: TabBar tests break on costlens activation
**What goes wrong:** Removing `soon: true` from the costlens tab causes 5+ existing TabBar tests to fail immediately — tests assert `SOON` label exists, `aria-disabled=true`, `not-allowed` cursor, and keyboard navigation that skips costlens.
**Why it happens:** Tests were written to verify the "coming soon" state; activating the tab inverts all those assertions.
**How to avoid:** Task 09-12 (update TabBar tests) must be done in the SAME wave as Task 09-11 (activate tab). Never activate the tab without updating tests in the same commit.
**Warning signs:** `npm test -- --run TabBar` fails with "unable to find SOON text".

### Pitfall 2: graph.edges is list[dict[str, str]], not a typed edge model
**What goes wrong:** Python code doing `edge.source` fails with `AttributeError`; must use `edge['source']`.
**Why it happens:** `ResourceGraph.edges` is `list[dict[str, str]]` (confirmed in models.py line 176), not `list[GraphEdge]`.
**How to avoid:** Always access edge fields via dict key: `edge['source']`, `edge['target']`. Build a node lookup dict `{n.id: n for n in graph.nodes}` before traversal to avoid O(n²) scans and handle missing node IDs gracefully.
**Warning signs:** `AttributeError: 'dict' object has no attribute 'source'`.

### Pitfall 3: ResourceGraph.costlens not exported from viewer package
**What goes wrong:** Dashboard `CostTabClient` imports `ResourceGraph` from `@infracanvas/viewer` but `ResourceGraph.costlens` is `undefined` at runtime because the type wasn't added to the viewer's `types.ts` before rebuilding the package.
**Why it happens:** The viewer is a library package — `dashboard/` imports from the built `dist/lib/index.js`. Types must be added to `viewer/src/types.ts` AND the viewer must be rebuilt (`npm run build:lib`) before dashboard code can reference them.
**How to avoid:** Wave 0 adds types to `viewer/src/types.ts`. The viewer lib rebuild is a required step before dashboard Wave 3 tasks.
**Warning signs:** TypeScript error `Property 'costlens' does not exist on type 'ResourceGraph'` in dashboard.

### Pitfall 4: Dashboard double-fetches R2 scan JSON
**What goes wrong:** If `ScanViewerClient` and `CostTabClient` are independent client components each fetching the presigned URL, R2 is hit twice per page load — wasting bandwidth and hitting presigned URL expiry edge cases.
**Why it happens:** Naively creating a new `CostTabClient` that calls `fetchScanJson` independently.
**How to avoid:** Use the `ScanDetailTabs` wrapper pattern — one client component fetches once, passes `data.costlens` as a prop to `CostTab` and full `data` to the viewer.
**Warning signs:** Network tab shows two fetches to the same R2 hostname on scan detail page load.

### Pitfall 5: Allocation percentages don't sum to 100% due to float rounding
**What goes wrong:** Three-way equal split at 33.33...% produces 99.99% total.
**Why it happens:** `100 / 3 = 33.333...` rounded to 2dp = 33.33. Three × 33.33 = 99.99.
**How to avoid:** Use integer cent arithmetic or the "remainder to first workload" pattern: compute `floor(100/n)` for all, assign remainder to first workload. Verify with `CLA-C-4` test.
**Warning signs:** CLA success criterion 4 ("allocations sum to 100%") fails in test.

### Pitfall 6: badge and tooltip shadcn components missing from dashboard
**What goes wrong:** `import { Badge } from '@/components/ui/badge'` causes module not found error.
**Why it happens:** `badge` and `tooltip` are NOT in the dashboard's `components/ui/` directory (confirmed by ls output — only 18 components installed, neither badge nor tooltip is present).
**How to avoid:** Wave 0 Task 09-04 installs both before any dashboard UI work: `cd dashboard && npx shadcn@latest add badge tooltip`.
**Warning signs:** TypeScript/build error on import.

### Pitfall 7: App.tsx hash routing doesn't handle costlens
**What goes wrong:** Navigating to `report.html#costlens` lands on canvas tab because the hash handler only checks `'flowmap'`.
**Why it happens:** App.tsx `readHash()` (lines 33–38) only has `if (hash === 'flowmap')` — all other hashes fall through to `'canvas'`.
**How to avoid:** Add `else if (hash === 'costlens') setActiveTab('costlens')` in the same task that activates the tab.
**Warning signs:** `#costlens` URL shows canvas tab content.

### Pitfall 8: Idle detection O(n²) on large graphs
**What goes wrong:** For each of N idle-candidate nodes, scanning all M edges is O(N×M). A scan of 500 resources with thousands of edges will be slow.
**Why it happens:** Naively iterating `graph.edges` inside a per-node loop.
**How to avoid:** Pre-build an adjacency index: `edges_by_source: dict[str, list[dict]] = defaultdict(list)` and `edges_by_target: dict[str, list[dict]] = defaultdict(list)` once before the detection loop.
**Warning signs:** Test with fixture of 500 nodes takes > 1 second.

---

## Risks & Landmines

### R1: Viewer lib rebuild required before dashboard tasks
The dashboard imports `@infracanvas/viewer` as a built package from `dist/lib/`. Any type changes to `viewer/src/types.ts` require running `cd viewer && npm run build:lib` before those types are available in the dashboard. Tasks must respect this build dependency — viewer lib tasks must complete and rebuild before dashboard tasks import new types.

**Mitigation:** Wave sequencing — Wave 0 types → viewer lib rebuild step → Wave 3 dashboard.

### R2: `workload_tag_key` attribute lookup is case-sensitive
`node.attributes` is `dict[str, object]`. Terraform attribute keys from HCL are always lowercase. If a user configures `workload_tag_key: SERVICE` (uppercase), the lookup fails silently and all resources fall into `'untagged'`. The default `'Service'` may also silently miss if actual tag key is `'service'`.
**Mitigation:** Document that the tag key must match exactly. Consider a case-insensitive lookup option (Claude's discretion — acceptable to do case-insensitive matching in the allocator).

### R3: Shared resource attachment graph traversal — edge direction conventions
The `graph.edges` direction convention (source → target) may not consistently represent "attached to" relationships for all shared resource types. For TGW, edges may go `tgw → attachment` or `attachment → tgw` depending on how the graph builder creates them. The allocator must handle both directions.
**Mitigation:** Test both `edge['source'] == shared_node.id` and `edge['target'] == shared_node.id` when finding attached nodes. Confirm with fixture tests that reflect actual graph builder output.

### R4: `costlens` field in `ResourceGraph` Pydantic model — schema version bump
Adding `costlens: CostLensData | None = None` to `ResourceGraph` changes the JSON schema. Old scan JSON files stored in R2 (without a `costlens` key) must still parse correctly. Pydantic v2 with `= None` default handles this gracefully — the field will be `None` when absent.
**Mitigation:** Confirm that `ResourceGraph` version is still `"2.1"` (no bump needed since field is optional with default). The dashboard `CostTab` must handle `costlens === null` with the empty state UI.

### R5: CPC-01 assumed_monthly_gb baseline
Without flow log data (CPC-02 deferred), all egress cost estimates use an assumed GB/month figure. The default value (100 GB/mo assumed) is arbitrary and may be confusing without clear labeling.
**Mitigation:** Always include `basis: "estimated at 100 GB/mo (no flow data)"` in `PathCost.basis`. Display a disclaimer in PathDetailPanel: "Estimate based on assumed transfer volume — enable flow logs for actuals."

### R6: `azurerm_firewall` FLAT_MONTHLY pricing not yet in estimator.py
The existing `FLAT_MONTHLY` dict in `estimator.py` does not include `azurerm_firewall`, `azurerm_express_route_circuit`, `aws_ec2_transit_gateway`, or `aws_vpc_endpoint`. The shared allocator needs `node.cost.monthly_usd` to be non-zero for these resources to produce meaningful allocations.
**Mitigation:** Wave 0 or Wave 1 must also extend `FLAT_MONTHLY` in `estimator.py` with Azure/shared resource pricing before the allocator runs. Estimated rates:
- `aws_ec2_transit_gateway`: $0.05/hr attachment + $0.02/GB → use flat $36.50/mo (attachment-only, no traffic)
- `azurerm_express_route_circuit`: ~$55/mo (Standard, 50 Mbps)
- `azurerm_firewall`: ~$730/mo ($1.00/hr base + $0.016/GB; flat base only)
- `aws_vpc_endpoint`: $0.01/hr = $7.30/mo

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | CLI allocator/idle/egress modules | Confirmed (project requirement) | 3.12+ | — |
| pytest | CLI tests | Confirmed (existing test suite) | per pyproject.toml | — |
| Node.js + npm | Viewer/dashboard builds | Confirmed (project requirement) | LTS | — |
| Vitest | Viewer/dashboard tests | Confirmed (vitest 4.1.4 in project) | 4.1.4 | — |
| shadcn `badge` | Dashboard `WasteBadge` | Not installed | — | Must install Wave 0 |
| shadcn `tooltip` | Dashboard chevron tooltip | Not installed | — | Must install Wave 0 |
| shadcn `tabs` | Dashboard tab switcher | Installed | in `components/ui/tabs.tsx` | — |
| shadcn `table` | Dashboard WorkloadTable | Installed | in `components/ui/table.tsx` | — |
| shadcn `card` | Dashboard IdleRecommendationsList | Installed | in `components/ui/card.tsx` | — |
| shadcn `skeleton` | Dashboard loading state | Installed | in `components/ui/skeleton.tsx` | — |

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A — CostLens is read-only, authenticated by Clerk (existing) |
| V3 Session Management | No | Handled by existing Clerk session |
| V4 Access Control | No | No new endpoints; data access via existing presigned URL flow |
| V5 Input Validation | Yes | `workload_tag_key` from YAML config — Pydantic validates string type |
| V6 Cryptography | No | No new crypto; R2 presigned URLs from existing backend |

No new threat vectors introduced — all data flows through existing authenticated channels.

---

## Sources

### Primary (HIGH confidence — verified against live codebase)
- `cli/infracanvas/cost/estimator.py` — full content read; pricing tables, `CostEstimator.estimate()` pattern
- `cli/infracanvas/graph/models.py` lines 1–180 — `ResourceGraph`, `ResourceNode`, `CostEstimate`, `NetworkPath` models; `edges: list[dict[str, str]]` confirmed
- `cli/infracanvas/config.py` — `InfraCanvasConfig` structure confirmed; no `costlens` key yet
- `viewer/src/App.tsx` — full content read; `isFlowMap` branch structure, hash routing, keyboard shortcuts
- `viewer/src/components/TabBar.tsx` — `soon: true` on costlens tab confirmed (line 36)
- `viewer/src/store.ts` — `TabId = 'canvas' | 'flowmap' | 'costlens'` confirmed; `selectedPath` exists
- `viewer/src/types.ts` — full content read; `ResourceGraph` has no `costlens` field yet
- `viewer/src/index.ts` — full content read; no CostLens exports yet
- `viewer/src/__tests__/flowmap/TabBar.test.tsx` — 5+ tests asserting SOON/aria-disabled on costlens
- `dashboard/components/scans/ScanViewerClient.tsx` — `fetchScanJson` + presigned URL pattern confirmed
- `dashboard/app/(dashboard)/scans/[id]/renderScanByStatus.tsx` — full content; `<ScanViewerClient>` is the ready-path renderer
- `dashboard/lib/r2.ts` — `fetchScanJson` with 403-retry pattern
- `dashboard/lib/types.ts` — `ScanGetResp`, `ResourceGraph` re-exported from viewer; no `CostLensData` yet
- `dashboard/components/ui/` — badge and tooltip NOT present; tabs/table/card/skeleton/button confirmed

### Secondary (MEDIUM confidence — CONTEXT.md and UI-SPEC)
- `09-CONTEXT.md` — locked decisions D-01..D-08, CPC-01/03
- `09-UI-SPEC.md` — approved component inventory, layout contracts, typography, copywriting

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed from live `package.json` and `pyproject.toml`
- Architecture: HIGH — patterns verified from existing Phase 7/8 implementations
- Pitfalls: HIGH — edge cases verified from actual code (dict edge access, missing shadcn components, TabBar tests)

**Research date:** 2026-05-06
**Valid until:** 2026-06-06 (stable codebase)

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `aws_ec2_transit_gateway → aws_ec2_transit_gateway_vpc_attachment` edge direction in graph | Technical Approach §Idle, §Allocator | Idle detection and attachment traversal may find zero results; needs fixture validation |
| A2 | Flat monthly rates for `azurerm_firewall`, `azurerm_express_route_circuit`, `aws_ec2_transit_gateway`, `aws_vpc_endpoint` — values based on training knowledge | Risks §R6 | Incorrect pricing displayed to users; low risk as estimates are labeled |
| A3 | CPC-01 egress rates from AWS/Azure pricing pages — based on training knowledge, not verified against live pricing pages | Technical Approach §CPC-01 | Rates may be stale; mitigated by labeling all estimates as approximations |

## Open Questions

1. **Edge direction for TGW attachments in Terraform graph**
   - What we know: `flowmap/aws.py` creates `aws_ec2_transit_gateway` and `aws_ec2_transit_gateway_vpc_attachment` nodes; edges are built by the graph builder
   - What's unclear: Whether the edge is `tgw → attachment` or `attachment → tgw`
   - Recommendation: First test in `test_costlens.py` (CLA-C-1) should be written with a fixture that matches actual graph builder output; run existing scan on test Terraform to verify direction before finalizing allocator

2. **Azure Firewall edge traversal method**
   - What we know: D-03 says "route-table-referenced workloads"; `azurerm_firewall` nodes exist in the graph
   - What's unclear: Whether firewall → workload relationships are modeled as direct edges or through route table intermediaries
   - Recommendation: Check `cli/infracanvas/flowmap/azure.py` for edge creation logic before writing CLA-03 allocator logic; the planner should add this as a prerequisite subtask
