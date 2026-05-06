---
phase: 09-costlens
plan: 05
subsystem: viewer
tags: [costlens, viewer, tab-activation, components, typescript, tests]
dependency_graph:
  requires: [09-02]
  provides: [CostLensPanel, CostLensData, viewer-costlens-tab]
  affects: [viewer/src/types.ts, viewer/src/App.tsx, viewer/src/components/TabBar.tsx, viewer/src/index.ts]
tech_stack:
  added: []
  patterns: [inline-style-objects, lazy-import, three-way-render-branch, tdd-red-green]
key_files:
  created:
    - viewer/src/components/costlens/CostLensPanel.tsx
    - viewer/src/components/costlens/WorkloadCard.tsx
    - viewer/src/components/costlens/IdleRecommendations.tsx
  modified:
    - viewer/src/types.ts
    - viewer/src/index.ts
    - viewer/src/components/TabBar.tsx
    - viewer/src/App.tsx
    - viewer/src/__tests__/flowmap/TabBar.test.tsx
    - viewer/src/__tests__/costlens/CostLensPanel.test.tsx
decisions:
  - "Removed all dead `soon` render code from TabBar.tsx (interface field, filter logic, SOON badge) rather than leaving it as dead code — keeps the component clean for future tabs"
  - "CostLensPanel test import path is ../../components/... (not ../../../) — test file is in src/__tests__/costlens/ so two levels up reaches src/"
  - "Three-way render branch uses isCostLens first, then isFlowMap, then canvas fallback — matches tab order and is easy to extend for a fourth tab"
metrics:
  duration: 23 minutes
  completed: 2026-05-06
  tasks_completed: 2
  files_modified: 8
---

# Phase 9 Plan 05: Viewer CostLens Tab Activation Summary

**One-liner:** CostLens tab activated with WorkloadCard grid + IdleRecommendations panel; hash routing (#costlens), keyboard shortcut (press 3), and 151/151 tests green.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add CostLens TypeScript interfaces to types.ts + index.ts | 7320e6a | viewer/src/types.ts, viewer/src/index.ts |
| 2 | Implement CostLens components + activate tab + fix TabBar tests | d598945 | 7 files (3 created, 4 modified) |

## What Was Built

### Task 1 — Types (7320e6a)

Added to `viewer/src/types.ts`:
- `CostLineItem` — resource_id, resource_type, label, monthly_usd, share_pct
- `WorkloadCost` — name, total_monthly_usd, line_items
- `SharedResourceSummary` — resource_id, resource_type, monthly_usd, workload_count
- `IdleRecommendation` — resource_id, resource_type, description, monthly_waste_usd
- `CostLensData` — workloads, shared_resources, recommendations
- `PathCost` — estimated_monthly_usd, rate_per_gb, assumed_gb, basis

Extended existing interfaces:
- `ResourceGraph.costlens?: CostLensData`
- `NetworkPath.path_cost?: PathCost`

Re-exported all CostLens types from `viewer/src/index.ts` plus `CostLensPanel` component.

### Task 2 — Components + Tab Activation (d598945)

**TabBar.tsx changes:**
- Removed `soon: true` from costlens tab definition
- Removed dead `soon?` field from `TabDef` interface
- Removed SOON badge render block
- Removed `isSoon` logic from render, keyboard handler, click handler
- Updated costlens tooltip to "Shared infrastructure cost allocation — press 3"
- All 3 tabs are now fully navigable (no skipping)

**App.tsx changes:**
- Added `CostLensPanel` lazy import
- Added `graph` selector from store
- Extended `readHash()` to handle `hash === 'costlens'`
- Added `'3'` key binding for costlens
- Replaced two-way `isFlowMap` with three-way `isCostLens / isFlowMap / canvas` render branch
- Passes `graph?.costlens ?? null` to CostLensPanel

**New component files:**
- `WorkloadCard.tsx` — Card with blue left border; renders workload name (italic when "untagged"), total in monospace, line items with share_pct%; empty state message when no line items
- `IdleRecommendations.tsx` — Amber-tinted list items with resource ID, description, waste amount formatted as "$X.XX est. monthly waste"
- `CostLensPanel.tsx` — Empty state (DollarSign icon + "No cost allocation data") when data=null; grid of WorkloadCards + optional IdleRecommendations section when data populated

**Test updates:**
- `TabBar.test.tsx`: Removed `describe('TabBar — CostLens "soon" tab is non-interactive', ...)` block (4 tests); replaced with `describe('TabBar — CostLens tab is fully interactive (Phase 9 activation)', ...)` (4 tests asserting not-aria-disabled, pointer cursor, click-activates, tooltip-contains-press-3); updated ArrowLeft-wraps and End-jumps tests to expect `costlens` instead of `flowmap`; added CostLens-activates-with-ArrowRight-from-FlowMap test; added clicking-CostLens-activates-it test. Net: 20 TabBar tests total.
- `CostLensPanel.test.tsx`: Replaced 5 `it.todo` stubs + 1 additional todo with 6 passing tests: empty state, workload names/amounts, untagged card, idle section, line-item breakdown, no idle section when no recommendations.

## Test Results

| Suite | Before | After |
|-------|--------|-------|
| Total tests | 143 + 6 todo | 151 passing |
| TabBar tests | 14 passing + 4 SOON tests | 20 passing |
| CostLensPanel | 6 todo | 6 passing |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test import path for CostLensPanel.test.tsx**
- **Found during:** Task 2 test run
- **Issue:** Plan template showed `../../../components/costlens/CostLensPanel` but test file is at `src/__tests__/costlens/` — three `../` levels from there reaches `viewer/` root, not `src/`. Correct path is `../../components/costlens/CostLensPanel`.
- **Fix:** Changed import to `../../components/costlens/CostLensPanel` and `../../types`.
- **Files modified:** viewer/src/__tests__/costlens/CostLensPanel.test.tsx
- **Commit:** d598945

**2. [Rule 2 - Missing critical cleanup] Removed all dead `soon` code from TabBar.tsx**
- **Found during:** Task 2 acceptance criteria check — `grep -c "soon"` returned 6 instead of 0
- **Issue:** Removing `soon: true` from the tab definition left dead code: the `soon?` TypeScript field, the `isSoon` variable, the `!t.soon` filter in keyboard handler, and the SOON badge render block.
- **Fix:** Removed all `soon`-related code; simplified TabBar to handle only active/inactive states with no disabled-tab concept.
- **Files modified:** viewer/src/components/TabBar.tsx
- **Commit:** d598945

## Threat Surface Scan

No new network endpoints, auth paths, or trust boundary changes introduced. CostLensData flows from `window.__INFRACANVAS_DATA__` (same trust boundary as rest of graph data). T-09-05-01 (Information Disclosure) disposition is `accept` per plan threat model — scan reports already contain full infrastructure data.

## Self-Check: PASSED

- FOUND: viewer/src/components/costlens/CostLensPanel.tsx
- FOUND: viewer/src/components/costlens/WorkloadCard.tsx
- FOUND: viewer/src/components/costlens/IdleRecommendations.tsx
- FOUND: .planning/phases/09-costlens/09-05-SUMMARY.md
- FOUND commit: 7320e6a (feat(09-05): types)
- FOUND commit: d598945 (feat(09-05): components + tab activation)
- 151/151 viewer tests passing
