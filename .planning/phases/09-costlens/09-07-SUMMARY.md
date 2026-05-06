---
phase: 09-costlens
plan: "07"
subsystem: viewer
tags: [flowmap, costlens, path-detail-panel, cost-tab, cpc-03]
dependency_graph:
  requires:
    - 09-04  # EgressEstimator + PathCost Python shape
    - 09-05  # PathCost TypeScript interface in types.ts
  provides:
    - CPC-03  # Cost tab in FlowMap PathDetailPanel
  affects:
    - viewer/src/components/flowmap/PathDetailPanel.tsx
tech_stack:
  added: []
  patterns:
    - Conditional tab via spread into tabs array (same pattern as Routes tab)
    - CostTab sub-component reusing existing Row helper
    - hasCost = node.cost.monthly_usd > 0 as display gate
    - basis?.includes('no flow data') disclaimer (T-09-07-03 mitigated)
key_files:
  modified:
    - viewer/src/components/flowmap/PathDetailPanel.tsx
    - viewer/src/__tests__/flowmap/PathDetailPanel.test.tsx
decisions:
  - "Cost tab in PathDetailPanel uses node.cost (CostEstimate) not NetworkPath.path_cost — the panel shows the selected node, not a path list. The PathCost interface lives on NetworkPath.path_cost but the panel never renders a path list."
  - "Path list sorting is N/A: PathDetailPanel shows a single selected node (not a list of paths). The selectedPath store field exists but is not wired into this panel. Sorting behaviour applies if/when a path-list view is added."
  - "Disclaimer line triggered by basis?.includes('no flow data') — read-only string check, no exec path (T-09-07-03 accepted)."
metrics:
  duration: "~20 minutes"
  completed: "2026-05-06"
  tasks_completed: 1
  tasks_total: 1
  tests_added: 5
  tests_total_after: 156
  files_modified: 2
---

# Phase 9 Plan 07: FlowMap PathDetailPanel Cost Tab Summary

**One-liner:** CPC-03 — Cost tab added to PathDetailPanel showing node egress cost estimate with `no flow data` disclaimer, gated on `node.cost.monthly_usd > 0`.

## What Was Built

PathDetailPanel.tsx in the viewer now surfaces a "Cost" tab when the selected node has a non-zero monthly cost estimate. The tab shows:
- **Monthly Cost** — `$X.XX` formatted value from `node.cost.monthly_usd`
- **Basis** — the rate/assumption string from `node.cost.basis` (e.g., "AWS us-east-1 egress $0.09/GB")
- **Disclaimer** — "Estimate based on assumed transfer volume — enable flow logs for actuals." shown when `basis` contains `'no flow data'` (the EgressEstimator's `BASIS_NOTE` constant from Plan 04)

The tab is absent (no tab button, no tab content) when `monthly_usd === 0` or when no node is selected.

## TDD Gate Compliance

| Gate | Commit | Description |
|------|--------|-------------|
| RED  | 06f2b54 | 5 failing tests — PDP-COST-01..05 |
| GREEN | 5883fa3 | Implementation passes all 5 new + 5 existing tests |

## Tasks

### Task 1: Add Cost tab to PathDetailPanel (TDD RED → GREEN)

**Status:** Complete

**Commits:**
- `06f2b54` — `test(09-07): add failing Cost tab tests for PathDetailPanel (RED)`
- `5883fa3` — `feat(09-07): add Cost tab to PathDetailPanel with disclaimer support (GREEN)`

**Changes to PathDetailPanel.tsx:**
1. Added `DollarSign` to lucide-react import (line 2)
2. Extended `Tab` type to include `'cost'` variant (line 7)
3. Derived `hasCost = node.cost.monthly_usd > 0` (line 60)
4. Appended conditional Cost tab entry to `tabs` array (line 66)
5. Added `{activeTab === 'cost' && hasCost && <CostTab node={node} />}` in content section (line 133)
6. Added `CostTab` sub-component (lines 274–287) reusing existing `Row` helper

**Test results:** 156/156 viewer tests pass (18 test files). tsc --noEmit clean.

## Deviations from Plan

### Clarification (not a deviation): Path sorting is N/A

**Found during:** Task 1 pre-read

The plan states: "If PathDetailPanel renders a list of paths, sort by path_cost.estimated_monthly_usd ascending."

The actual component shows a single selected **node** (sourced from `useViewerStoreOrSingleton(s => s.selectedNode)`), not a list of paths. `selectedPath: NetworkPath | null` exists in the store but is not consumed by PathDetailPanel. There is no path list to sort.

The cost display therefore uses `node.cost: CostEstimate` (which has `monthly_usd`, `currency`, `basis`) rather than `NetworkPath.path_cost: PathCost` (which has `estimated_monthly_usd`, `rate_per_gb`, `assumed_gb`, `basis`). This matches PATTERNS.md §1016–1064 exactly — the PATTERNS spec correctly uses `node.cost.monthly_usd` as the trigger.

Plan note acknowledged: "If no path list exists in the panel, skip this step and note it in the SUMMARY." Done.

## Acceptance Criteria Verification

| Criterion | Result |
|-----------|--------|
| `grep -c "DollarSign" PathDetailPanel.tsx` >= 1 | 2 (import + usage) |
| `grep -c "'cost'" PathDetailPanel.tsx` >= 1 | 3 (type, tab entry, render) |
| `grep -c "hasCost\|path_cost\|monthly_usd" PathDetailPanel.tsx` >= 1 | 4 |
| `npm test -- --run` exits 0 | 156/156 pass |
| `tsc --noEmit` clean for PathDetailPanel | Clean (no errors) |

## Known Stubs

None — all cost data flows from the CLI's EgressEstimator via `node.cost` already in the graph JSON.

## Threat Flags

None — cost data is pre-computed static infrastructure metadata at the same trust level as existing node costs already rendered in the HTML report (T-09-07-01 accepted).

## Self-Check: PASSED

- `viewer/src/components/flowmap/PathDetailPanel.tsx` — exists, modified
- `viewer/src/__tests__/flowmap/PathDetailPanel.test.tsx` — exists, 10 tests
- Commit `06f2b54` (RED) — exists
- Commit `5883fa3` (GREEN) — exists
- 156/156 viewer tests pass
