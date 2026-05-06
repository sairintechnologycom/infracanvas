---
phase: 09-costlens
reviewed: 2026-05-06T10:20:00Z
depth: standard
files_reviewed: 21
files_reviewed_list:
  - cli/infracanvas/config.py
  - cli/infracanvas/cost/allocator.py
  - cli/infracanvas/cost/egress.py
  - cli/infracanvas/cost/idle.py
  - cli/infracanvas/graph/models.py
  - cli/infracanvas/main.py
  - cli/tests/test_costlens.py
  - dashboard/app/(dashboard)/scans/[id]/CostTab.tsx
  - dashboard/app/(dashboard)/scans/[id]/ScanDetailTabs.tsx
  - dashboard/app/(dashboard)/scans/[id]/renderScanByStatus.tsx
  - dashboard/components/scans/IdleRecommendationsList.tsx
  - dashboard/components/scans/WorkloadTable.tsx
  - dashboard/lib/types.ts
  - viewer/src/App.tsx
  - viewer/src/components/TabBar.tsx
  - viewer/src/components/costlens/CostLensPanel.tsx
  - viewer/src/components/costlens/IdleRecommendations.tsx
  - viewer/src/components/costlens/WorkloadCard.tsx
  - viewer/src/components/flowmap/PathDetailPanel.tsx
  - viewer/src/index.ts
  - viewer/src/types.ts
findings:
  critical: 4
  warning: 5
  info: 3
  total: 12
status: issues_found
---

# Phase 9: Code Review Report

**Reviewed:** 2026-05-06T10:20:00Z
**Depth:** standard
**Files Reviewed:** 21
**Status:** issues_found

## Summary

Phase 9 introduced the CostLens allocation engine (SharedCostAllocator, IdleDetector, EgressEstimator), a viewer tab, and a dashboard Cost tab. The core allocation math is correct and well-tested. However, four blockers were found: the primary user-facing `scan` command is completely missing the CostLens pipeline (so HTML/JSON exports from `scan` always carry `costlens: null`), same-region paths are priced at the non-zero DEFAULT_EGRESS_RATE instead of $0, the `azurerm_firewall` type is tracked as shared but has no idle detection logic despite being in SHARED_TYPES, and the WorkloadTable uses a keyless React fragment inside `.map()` which produces runtime key warnings and can cause rendering corruption. Additional warnings cover floating point sum imprecision, a deprecated browser API, a misleading error message, and a duplicate code block.

---

## Critical Issues

### CR-01: `scan` command never runs CostEstimator or CostLens pipeline — exports always have `costlens: null`

**File:** `cli/infracanvas/main.py:410-412`

**Issue:** The `scan` command calls `_run_scan()` and then immediately goes to output handling. It never calls `CostEstimator.estimate()`, `SharedCostAllocator.allocate()`, `IdleDetector.detect()`, or `EgressEstimator.estimate()`. The `score` command (line 687) and the `plan` command (line 809) both run the full CostLens pipeline, but `scan` — the primary command users run — does not. The HTML and JSON exports produced by `infracanvas scan` will always have every node with `cost.monthly_usd = 0.0` and `costlens = null`, making the CostLens viewer tab always show the "No cost allocation data" empty state for scan-produced reports.

**Fix:** Add the cost estimation and CostLens pipeline to the `scan` command body, immediately after `_run_scan()` returns (before any `--json`/`--ci` early exits so the cost data is present in all output formats):

```python
# After line 412: graph = _run_scan(...)

# Apply cost estimation + CostLens allocation pipeline
estimator = CostEstimator()
graph = estimator.estimate(graph)

from infracanvas.cost.allocator import SharedCostAllocator  # noqa: PLC0415
from infracanvas.cost.egress import EgressEstimator        # noqa: PLC0415
from infracanvas.cost.idle import IdleDetector             # noqa: PLC0415
try:
    _allocator = SharedCostAllocator(workload_tag_key=config.costlens.workload_tag_key)
    graph = _allocator.allocate(graph)
    graph = IdleDetector().detect(graph)
    graph = EgressEstimator().estimate(graph)
except Exception as exc:  # noqa: BLE001
    _err_console.print(f"[yellow]Warning:[/yellow] CostLens allocation failed: {exc}")
```

---

### CR-02: Same-region egress priced at DEFAULT_EGRESS_RATE ($0.09/GB) instead of $0.00

**File:** `cli/infracanvas/cost/egress.py:64-81`

**Issue:** `_lookup_rate()` has no guard for the case where `src_region == dst_region`. When two nodes are in the same region (e.g., both in `us-east-1`), the function falls through all table lookups and returns `DEFAULT_EGRESS_RATE = 0.09`. Intra-region traffic is free (or close to free), so every same-region path is over-estimated by $9.00/month at the assumed 100 GB/mo volume. This produces materially incorrect cost estimates displayed to users.

**Fix:**

```python
def _lookup_rate(src_region: str, dst_region: str, cross_cloud: bool) -> float:
    """Look up egress rate for a region pair. Returns DEFAULT_EGRESS_RATE if unknown."""
    if cross_cloud:
        return CROSS_CLOUD_EGRESS

    # Intra-region: no egress charge
    src_norm = _normalize_region(src_region)
    dst_norm = _normalize_region(dst_region)
    if src_norm == dst_norm:
        return 0.0

    # AWS inter-region lookup (both key directions)
    for key in (f"{src_region}:{dst_region}", f"{dst_region}:{src_region}"):
        if key in AWS_EGRESS_RATES:
            return AWS_EGRESS_RATES[key]

    # Azure inter-region lookup (normalized lowercase)
    for key in (f"{src_norm}:{dst_norm}", f"{dst_norm}:{src_norm}"):
        if key in AZURE_EGRESS_RATES:
            return AZURE_EGRESS_RATES[key]

    return DEFAULT_EGRESS_RATE
```

---

### CR-03: `azurerm_firewall` in SHARED_TYPES has no idle detection — silently skipped by IdleDetector

**File:** `cli/infracanvas/cost/idle.py:62-69` and `cli/infracanvas/cost/allocator.py:17`

**Issue:** `SHARED_TYPES` in `allocator.py` includes `"azurerm_firewall"` (line 17), so it participates in cost allocation. But `_IDLE_SIGNALS` in `idle.py` has no entry for `"azurerm_firewall"` — it only covers NAT Gateway, TGW, ExpressRoute, and VPC Endpoint. The `IdleDetector.detect()` loop checks `node.type not in _IDLE_CANDIDATES` and skips the node entirely. An Azure Firewall with no attached route tables (or any other idle signal) will never generate an `IdleRecommendation`, silently missing waste.

The test `TestIdleDetector` has no test case for `azurerm_firewall`, so this gap is also untested.

**Fix:** Add an idle signal and detection function for `azurerm_firewall`. An Azure Firewall is idle when no `azurerm_route_table` has an edge pointing to it:

```python
def _idle_azure_firewall(
    node: ResourceNode,
    edges_by_target: dict[str, list[dict[str, str]]],
    node_by_id: dict[str, ResourceNode],
) -> bool:
    """Idle if no azurerm_route_table has an edge to this firewall."""
    return node.type == "azurerm_firewall" and not any(
        node_by_id.get(e["source"]) is not None
        and node_by_id[e["source"]].type == "azurerm_route_table"
        for e in edges_by_target.get(node.id, [])
    )

# Add to _IDLE_SIGNALS:
"azurerm_firewall": "No azurerm_route_table entries reference this Azure Firewall",

# Add to detect() dispatch:
elif node.type == "azurerm_firewall":
    is_idle = _idle_azure_firewall(node, edges_by_target, node_by_id)
```

---

### CR-04: React `<>` fragment used as direct child of `.map()` without a `key` prop in WorkloadTable

**File:** `dashboard/components/scans/WorkloadTable.tsx:62`

**Issue:** The `.map()` on line 53 returns a bare `<>...</>` fragment (line 62) containing two `<tr>` elements. React requires a `key` on the outermost element returned from a list's `.map()`. The `key={wl.name}` is placed on the inner `<tr>` (line 64), not on the fragment. This causes a React "Each child in a list should have a unique 'key' prop" warning on every render and can produce incorrect diffing behavior when workloads are reordered or when the expansion row is toggled — React may reconcile the wrong row against the wrong DOM element.

**Fix:** Replace the bare fragment with a keyed fragment:

```tsx
return (
  <React.Fragment key={wl.name}>
    <tr
      className="border-b border-slate-100 last:border-b-0 hover:bg-slate-50"
    >
      {/* remove key from the <tr> */}
      ...
    </tr>
    {isExpanded && (
      <tr id={`detail-${wl.name}`} className="bg-slate-50">
        ...
      </tr>
    )}
  </React.Fragment>
)
```

---

## Warnings

### WR-01: Broad `except Exception` silently swallows CostLens failures, masking bugs during development

**File:** `cli/infracanvas/main.py:701-702` and `cli/infracanvas/main.py:824-825`

**Issue:** Both `score` and `plan` commands wrap the entire CostLens pipeline in `except Exception as exc` and print a yellow warning. This is the correct production posture, but the `# noqa: BLE001` suppresses the linting rule that would normally flag this. The allocator, idle detector, and egress estimator can all raise `AttributeError` or `KeyError` due to unexpected graph shapes — these indicate real bugs that are currently swallowed rather than surfaced.

**Fix:** For correctness, narrow the exception scope to expected infrastructure-data errors (e.g., `ValueError`, `KeyError`) or add a `--debug` flag that re-raises. At minimum, remove the `noqa` suppression so the linter reminds future developers this is intentional.

---

### WR-02: `_split_percentages` produces floating-point sum slightly above 100.0 for some values of `n`

**File:** `cli/infracanvas/cost/allocator.py:29-37`

**Issue:** For `n=7`, `_split_percentages(7)` returns `[14.2858, 14.2857, 14.2857, 14.2857, 14.2857, 14.2857, 14.2857]` which sums to `100.00000000000001` — a floating-point value above 100. The test at line 76 uses `abs(total_pct - 100.0) < 0.001` which passes, but the function's docstring claims it "distributes float remainder to first element" as a correction mechanism. The remainder calculation itself uses `round()` which can introduce additional error. If the sum exceeds 100.0 and is rendered as `"${pct.toFixed(0)}%"` in the UI for all items, the displayed total can show "101%".

**Fix:** Compute the last element's percentage as `100.0 - sum(parts[1:])` rather than using a pre-computed remainder:

```python
def _split_percentages(n: int) -> list[float]:
    if n == 0:
        return []
    base = round(100.0 / n, 4)
    parts = [base] * n
    # Set first element to the exact complement so sum is exactly 100.0
    parts[0] = round(100.0 - base * (n - 1), 4)
    return parts
```

---

### WR-03: `navigator.platform` is deprecated — unreliable for Mac detection in TabBar

**File:** `viewer/src/components/TabBar.tsx:17`

**Issue:** `navigator.platform` was deprecated in the Web Platform and will be removed in future browser versions. It already returns inconsistent values on newer macOS (e.g., it returns `"MacIntel"` even on Apple Silicon Macs, and may return empty string in some headless environments). The correct API is `navigator.userAgentData.platform` (where available) with a fallback to the UA string.

**Fix:**

```typescript
const _isMac =
  typeof navigator !== 'undefined' &&
  (
    (navigator as Navigator & { userAgentData?: { platform: string } })
      .userAgentData?.platform?.toLowerCase().includes('mac') ??
    navigator.platform.toLowerCase().includes('mac')
  );
```

---

### WR-04: `CostTab.tsx` error message references `infracanvas.yaml` — wrong filename

**File:** `dashboard/app/(dashboard)/scans/[id]/CostTab.tsx:26`

**Issue:** The empty-state copy says `infracanvas.yaml` but the actual config file is `.infracanvas.yml` (with a leading dot, no leading dot in the display text, and `.yml` not `.yaml` extension). A user following this hint will create the wrong file and get no results.

**Fix:**

```tsx
<code className="mx-1 px-1 bg-slate-100 rounded text-xs font-mono">
  .infracanvas.yml
</code>
```

---

### WR-05: CostLens pipeline duplicated verbatim in `score` and `plan` commands — no shared helper

**File:** `cli/infracanvas/main.py:690-702` and `cli/infracanvas/main.py:813-825`

**Issue:** The 13-line CostLens allocation block (import + try/except wrapping allocator + idle + egress) is copy-pasted identically between the `score` and `plan` commands. Any future change (e.g., adding a new pipeline stage) must be applied in two places. Given that CR-01 requires adding a third copy to `scan`, this pattern will become three copies.

**Fix:** Extract to a private helper:

```python
def _run_costlens(graph: ResourceGraph, config: InfraCanvasConfig) -> ResourceGraph:
    """Run the CostLens allocation pipeline. Returns graph unchanged on failure."""
    from infracanvas.cost.allocator import SharedCostAllocator  # noqa: PLC0415
    from infracanvas.cost.egress import EgressEstimator        # noqa: PLC0415
    from infracanvas.cost.idle import IdleDetector             # noqa: PLC0415
    try:
        graph = SharedCostAllocator(workload_tag_key=config.costlens.workload_tag_key).allocate(graph)
        graph = IdleDetector().detect(graph)
        graph = EgressEstimator().estimate(graph)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[yellow]Warning:[/yellow] CostLens allocation failed: {exc}")
    return graph
```

---

## Info

### IN-01: `SharedResourceSummary.workload_count` counts distinct workload names, not raw attachment count

**File:** `cli/infracanvas/cost/allocator.py:70-76`

**Issue:** The field name `workload_count` and its value `len(distinct_workloads)` are correct by intent. However, a shared resource connected to two edges both pointing at nodes tagged as the same workload will show `workload_count=1`, not `workload_count=2`. This is the desired semantic (equal cost split per workload, not per edge), but the field name could mislead a future developer into thinking it counts connections. The `workload_count` field is currently unused in the dashboard UI — it is only present in the model.

**Fix:** Add a docstring to `SharedResourceSummary.workload_count` clarifying it is the count of distinct workload tags, not raw graph edges.

---

### IN-02: `noqa: F401` on `IdleDetector` import in test file implies it was once unused

**File:** `cli/tests/test_costlens.py:6`

**Issue:** Line 6 imports `IdleDetector` with `# noqa: F401  (RED — Plan 03)`. The comment suggests this was a stub import added before the implementation existed. Now that `IdleDetector` is fully implemented and tested in `TestIdleDetector`, the `noqa` suppression and its comment are stale. The import is no longer unused — it is actively used on line 229.

**Fix:** Remove the `# noqa: F401  (RED — Plan 03)` comment from the import line.

---

### IN-03: `SharedResourceSummary` is exported in `viewer/src/index.ts` types but missing from `dashboard/lib/types.ts` re-exports

**File:** `dashboard/lib/types.ts:2-11` and `viewer/src/index.ts:56-58`

**Issue:** `viewer/src/index.ts` exports `SharedResourceSummary` via the types section (it is present in `viewer/src/types.ts` at line 128). But `dashboard/lib/types.ts` only re-exports `CostLensData`, `WorkloadCost`, and `IdleRecommendation` from `@infracanvas/viewer`. If any dashboard component needs `SharedResourceSummary` (e.g., to render the shared resources list), it must either import directly from `@infracanvas/viewer` instead of from `@/lib/types`, or the type will be silently unavailable from the canonical dashboard type barrel.

**Fix:** Add `SharedResourceSummary` to the re-export list in `dashboard/lib/types.ts`:

```typescript
export type {
  ResourceGraph,
  GraphSummary,
  Finding,
  Severity,
  DriftStatus,
  CostLensData,
  WorkloadCost,
  IdleRecommendation,
  SharedResourceSummary,  // add this
} from '@infracanvas/viewer'
```

---

_Reviewed: 2026-05-06T10:20:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
