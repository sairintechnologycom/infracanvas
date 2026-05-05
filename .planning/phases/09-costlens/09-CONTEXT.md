# Phase 9: CostLens - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver the CostLens shared-cost allocation engine: extend the existing per-resource cost estimator with shared-resource splitting (TGW, ExpressRoute, Azure Firewall, NAT GW, VPC Endpoint → workloads), add idle/oversized static-heuristic recommendations, activate the viewer's CostLens tab (currently `soon: true`), extend the scan JSON output with a `costlens` block, and wire a native 'Cost' tab on the scan detail page in the SaaS dashboard.

**In scope:**
- `cli/infracanvas/cost/` — new shared-cost allocator (CLA-01..04): splits TGW/ExpressRoute/Azure Firewall/NAT GW/VPC Endpoint costs equally among attached workloads (by configurable tag key)
- `cli/infracanvas/cost/` — idle/oversized detector (CLA-05): static Terraform-graph heuristics only
- `cli/infracanvas/export/` — extend scan JSON with a `costlens: {workloads, shared_resources, recommendations}` block (CLA-06 data source)
- `viewer/src/` — activate CostLens tab (remove `soon: true`), implement workload-view cards + idle recommendations bottom section
- `dashboard/app/(dashboard)/scans/[id]/` — new native 'Cost' tab reading `costlens` from the scan JSON stored in R2
- `viewer/src/types.ts` — CostLensData TypeScript type
- CPC-01/03: topology-based cross-cloud data transfer cost estimation (per-path rates from known egress pricing), cost-aware path ranking in FlowMap

**Out of scope:**
- CPC-02 (flow-log-driven data transfer attribution) — deferred to Phase 12 (DC Agent brings NetFlow)
- CloudWatch / Azure Monitor metrics-based idle detection — deferred (no metrics pipeline yet)
- Per-team cost aggregation across scans / `/costlens` top-level route — future phase when CostLens matures
- Tag-based weight configuration beyond the tag key — equal split only

</domain>

<decisions>
## Implementation Decisions

### Shared resource cost allocation (CLA-01..04)
- **D-01:** Equal split — divide each shared resource's monthly cost evenly by the count of distinct workloads attached to it (from the Terraform graph). No traffic weighting required.
- **D-02:** Workload tag key is configurable via `infracanvas.yaml` under `costlens.workload_tag_key`. CLI reads this config key at scan time. Default value (if unset): `Service`.
- **D-03:** Resources with no matching tag are bucketed into a synthetic `'untagged'` workload. They receive a full equal share — their allocation is visible and not silently dropped. Allocation percentages must sum to 100% per shared resource (CLA success criterion 4).

### Idle/oversized detection (CLA-05)
- **D-04:** Static Terraform heuristics only. Idle signals:
  - `aws_nat_gateway` with zero `aws_route` entries referencing it in the graph → idle
  - `aws_ec2_transit_gateway` with no `aws_ec2_transit_gateway_vpc_attachment` children → idle
  - `azurerm_express_route_circuit` with no `azurerm_virtual_network_gateway_connection` children → idle
  - `aws_vpc_endpoint` with no associated route tables in the graph → idle
  - No CloudWatch / Azure Monitor data required.

### CostLens viewer tab layout (viewer — HTML report)
- **D-05:** Activate the existing `costlens` tab (remove `soon: true` and `aria-disabled`). Layout: workload-view cards. Each workload card shows: workload name, total allocated cost/mo, line-item breakdown of each shared resource's contribution (name + $ amount + % share) and dedicated resource costs. An `untagged` card appears if untagged resources exist.
- **D-06:** Idle/oversized recommendations appear as a bottom section of the CostLens tab (below all workload cards). Each recommendation: resource ID, type, idle signal description, estimated monthly waste.

### Dashboard panel — CLA-06
- **D-07:** 'Cost' tab added to the scan detail page (`app/(dashboard)/scans/[id]/page.tsx`) alongside the existing Viewer. Native React table (not inside the viewer iframe): workload rows with allocated cost + shared resource breakdown + idle recommendations list at the bottom.
- **D-08:** CLI extends scan JSON output with a top-level `costlens` block at scan time:
  ```json
  {
    "costlens": {
      "workloads": [
        { "name": "payments-svc", "total_monthly_usd": 412.0, "line_items": [...] }
      ],
      "shared_resources": [...],
      "recommendations": [
        { "resource_id": "aws_nat_gateway.main", "type": "idle", "description": "...", "monthly_waste_usd": 32.85 }
      ]
    }
  }
  ```
  Dashboard reads the `costlens` block from the R2 scan JSON via the existing presigned GET URL — no new backend endpoint required.

### CPC-01/03 — per-path data transfer cost (Claude's discretion)
- CPC-01: Topology-based estimation. Use known AWS/Azure inter-region and cross-cloud egress unit rates (same static-pricing-table approach as the existing estimator) applied to paths visible in the FlowMap graph. No flow logs required.
- CPC-03: Cost-aware path ranking in FlowMap viewer — annotate FlowMap edges with computed per-path transfer cost; rank paths by total cost in the PathDetailPanel.
- CPC-02 (flow-log-driven attribution) deferred to Phase 12.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §"Category 7 — CostLens Shared Cost (CLA / CPC)" — CLA-01..06, CPC-01..03 full requirement text
- `.planning/ROADMAP.md` §"Phase 9: CostLens" — goal, success criteria, dependencies

### Existing cost engine
- `cli/infracanvas/cost/estimator.py` — current per-resource estimator: static pricing tables, region multipliers, `_estimate_resource()` entry point, `CostEstimate` model
- `cli/tests/test_cost.py` — existing cost test suite (test IDs COST-C-1..COST-C-5 + integration tests)

### Data models
- `cli/infracanvas/graph/models.py` — `ResourceGraph`, `ResourceNode`, `CostEstimate` Pydantic models; `costlens` block must be added as an optional field to `ResourceGraph`
- `viewer/src/types.ts` — `CostEstimate` TypeScript interface; new `CostLensData` type to be added here

### Viewer / tab infrastructure
- `viewer/src/components/TabBar.tsx` — CostLens tab definition (currently `soon: true`); Phase 9 activates it
- `viewer/src/store.ts` — `TabId = 'canvas' | 'flowmap' | 'costlens'` already includes costlens

### Dashboard scan detail
- `dashboard/app/(dashboard)/scans/[id]/page.tsx` — scan detail page; new 'Cost' tab is added here
- `dashboard/lib/backend.ts` — `backendFetch` helper used by all dashboard API routes (established CC-13 pattern)

### Config
- `cli/infracanvas/config.py` — config loading (add `costlens.workload_tag_key` key here)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `cli/infracanvas/cost/estimator.py` — `CostEstimator` class and `_estimate_resource()` already handle per-resource cost. Shared allocator extends this; doesn't replace it.
- `viewer/src/components/TabBar.tsx` — tab infrastructure already supports `costlens` as a TabId; just remove `soon: true` to enable it
- `viewer/src/store.ts` — `TabId` union and tab-switching state already include `'costlens'`; viewer CostLens panel just needs the actual component wired into the tab render branch
- `cli/infracanvas/config.py` — config loader already walks up the filesystem; add `costlens.workload_tag_key` as an optional config key with default `'Service'`

### Established Patterns
- **Static pricing tables**: EC2_PRICES, RDS_PRICES, FLAT_MONTHLY, REGION_MULTIPLIERS in `estimator.py` — add cross-cloud egress tables following the same pattern for CPC-01
- **ResourceGraph as pre-computed output**: The CLI pre-computes everything and embeds it in the JSON. Dashboard reads; no server-side compute. The `costlens` block follows this same pattern.
- **Scan JSON in R2**: Scan results stored via `put_bytes` in `backend/app/queue/tasks/scan_repo.py`. Dashboard fetches via presigned GET URL. No new endpoint needed for CLA-06.
- **Pydantic models for graph structures**: All CLI outputs are Pydantic models. `CostLensData` should be a new Pydantic model added to `graph/models.py`, added as `Optional[CostLensData]` on `ResourceGraph`.
- **TDD**: Existing tests use pytest with test ID docstrings. New tests follow `CLA-C-N` and `CPC-C-N` naming.

### Integration Points
- CLI: `_estimate_resource()` is called per-node in `CostEstimator.annotate(graph)`. New shared-cost allocation runs as a second pass after per-node annotation, reading graph edges to find attachments.
- Viewer: The CostLens tab render branch in the main app (currently returning null for the `costlens` case) needs a `<CostLensPanel data={graph.costlens} />` component.
- Dashboard: Scan detail page fetches scan JSON (already has presigned URL). The `costlens` key in the parsed JSON feeds the new 'Cost' tab component.
- FlowMap: PathDetailPanel (`viewer/src/components/flowmap/PathDetailPanel.tsx`) is the integration point for CPC-03 cost-aware path annotation.

</code_context>

<specifics>
## Specific Ideas

- Workload card layout (user-confirmed mockup):
  ```
  ┌─ payments-svc ──────── $412/mo ──────────┐
  │  TGW attachment:        $89  (25%)        │
  │  NAT Gateway share:     $11  (8%)         │
  │  EC2 (dedicated):       $312              │
  └──────────────────────────────────────────┘
  ```
- Dashboard 'Cost' tab layout (user-confirmed mockup):
  ```
  workload        allocated     shared
  payments-svc    $412/mo       TGW + NAT GW
  auth-svc        $234/mo       TGW
  untagged        $178/mo       TGW
  [Idle/oversized recommendations]
  ```

</specifics>

<deferred>
## Deferred Ideas

- **CPC-02 — flow-log-driven data transfer attribution**: Requires DC Agent (Phase 10) NetFlow data. Deferred to Phase 12 (Path Computation + Asymmetric Routing, which already handles NetFlow correlation).
- **Per-team cost aggregation**: Cross-scan cost rollup and a `/costlens` top-level SaaS route — deferred until CostLens has shipped and user demand is validated.
- **CloudWatch / Azure Monitor idle detection**: Usage-based idle signals (actual CPU/memory utilization) deferred until a metrics pipeline exists.
- **Tag-based weighting**: Tag-weighted allocation (env=prod → 60%, env=dev → 40%) — deferred to Phase 9 follow-up if users request it.

</deferred>

---

*Phase: 9-CostLens*
*Context gathered: 2026-05-05*
