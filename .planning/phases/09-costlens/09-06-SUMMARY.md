---
phase: 09-costlens
plan: 06
subsystem: dashboard
tags: [costlens, dashboard, cost-tab, workload-table, scan-detail, typescript, tdd]
dependency_graph:
  requires: [09-02, 09-05]
  provides: [ScanDetailTabs, CostTab, WorkloadTable, IdleRecommendationsList, dashboard-costlens-tab]
  affects:
    - dashboard/lib/types.ts
    - dashboard/app/(dashboard)/scans/[id]/ScanDetailTabs.tsx
    - dashboard/app/(dashboard)/scans/[id]/CostTab.tsx
    - dashboard/app/(dashboard)/scans/[id]/renderScanByStatus.tsx
    - dashboard/components/scans/WorkloadTable.tsx
    - dashboard/components/scans/IdleRecommendationsList.tsx
    - dashboard/components/scans/WorkloadTable.test.tsx
tech_stack:
  added: []
  patterns: [shadcn-tabs-line-variant, html-table-pattern, tdd-red-green, aria-expanded-accordion, tooltip-on-chevron]
key_files:
  created:
    - dashboard/app/(dashboard)/scans/[id]/ScanDetailTabs.tsx
    - dashboard/app/(dashboard)/scans/[id]/CostTab.tsx
    - dashboard/components/scans/WorkloadTable.tsx
    - dashboard/components/scans/IdleRecommendationsList.tsx
  modified:
    - dashboard/lib/types.ts
    - dashboard/app/(dashboard)/scans/[id]/renderScanByStatus.tsx
    - dashboard/components/scans/WorkloadTable.test.tsx
    - dashboard/__tests__/scan-detail-polling.test.tsx
    - dashboard/__tests__/polish-drift.test.ts
    - cli/infracanvas/export/viewer_template.html (viewer postbuild)
decisions:
  - "viewer package rebuilt (npm run build in viewer/) so dashboard tsc resolves CostLensData/WorkloadCost/IdleRecommendation — dist/ is gitignored, rebuild is required on CostLens type changes"
  - "WorkloadTable test assertion changed from getByText('TGW') to getByText('$18.25 (50%)') — TGW appears in both the Shared Resources column and the expanded detail row causing getByText ambiguity; the amount is unique to the expanded state"
  - "polish-drift.test.ts: added IdleRecommendationsList to text-amber-600 allowed list — amber-600 for waste amounts is spec-mandated (UI-SPEC §Dashboard — Cost tab), not decorative drift"
  - "scan-detail-polling.test.tsx: updated vi.mock to mock ScanDetailTabs (replacing ScanViewerClient reference) — test mocked the component that renderScanByStatus now uses for ready+URL state"
  - "ScanDetailTabs uses shadcn Tabs with variant=line (confirmed tabs.tsx exports the variant) — matches UI-SPEC line underline style"
metrics:
  duration: 22 minutes
  completed: 2026-05-06
  tasks_completed: 2
  files_modified: 10
---

# Phase 9 Plan 06: Dashboard Cost Tab Summary

**One-liner:** Dashboard scan detail page now shows Viewer + Cost tabs via ScanDetailTabs wrapper; WorkloadTable with expandable chevron rows and IdleRecommendationsList with amber waste amounts complete the CostLens dashboard surface.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add CostLensData types + ScanDetailTabs + CostTab | a9eed6e | dashboard/lib/types.ts, ScanDetailTabs.tsx, CostTab.tsx |
| 2 (RED) | WorkloadTable failing tests | 79617c5 | WorkloadTable.test.tsx |
| 2 (GREEN) | WorkloadTable + IdleRecommendationsList + renderScanByStatus + fixes | ee0c952 | 7 files + viewer rebuild |

## What Was Built

### Task 1 — Types + ScanDetailTabs + CostTab (a9eed6e)

**dashboard/lib/types.ts:**
- Added `CostLensData`, `WorkloadCost`, `IdleRecommendation` to re-export from `@infracanvas/viewer`

**ScanDetailTabs.tsx (new):**
- Client component — copies `ScanViewerClient`'s fetch pattern exactly (fetchScanJson + getFreshPresignedUrl + cancelled-flag cleanup)
- Lifts `graph` state up and shares it between tabs — single R2 fetch for both Viewer and Cost tab (T-09-06-03 mitigation)
- Renders shadcn `<Tabs variant="line">` with two tabs: Viewer (ViewerProvider + ViewerApp) and Cost (CostTab)
- Loading state: full-height centered "Loading…"
- Error state: "Could not load scan" + error message

**CostTab.tsx (new):**
- Renders `WorkloadTable` + conditional `IdleRecommendationsList`
- Empty state (`data === null`): full-height message with `infracanvas scan` + `costlens.workload_tag_key` hint
- `aria-live="polite"` on empty state div

### Task 2 — WorkloadTable + IdleRecommendationsList + wire (ee0c952)

**WorkloadTable.tsx (new):**
- `'use client'` — uses `useState` for `expandedRows: Set<string>`
- Empty state when `workloads.length === 0`: "No cost data yet"
- Section heading: `<h2>Cost Allocation</h2>`
- HTML table following ScansTable pattern: `bg-white border rounded-lg`, `bg-slate-50 border-b` thead
- Columns: Workload, Allocated / mo, Shared Resources, Details
- `data-testid="workload-table"` on outer wrapper
- Workload name: italic `text-slate-400` when name === 'untagged'
- Allocated/mo: `font-mono tabular-nums` — `$X.XX/mo` format
- Shared Resources: joins labels from `line_items` with `share_pct > 0`
- Chevron: `TooltipProvider > Tooltip > TooltipTrigger (asChild) > button` with `aria-label`, `aria-expanded`, `aria-controls`
- Expanded detail row: `colSpan=4`, lists each line item with label + amount + share_pct%

**IdleRecommendationsList.tsx (new):**
- `data-testid="idle-recommendations-list"` on outer wrapper
- Separated from WorkloadTable with `mt-12` + `<hr>`
- Section heading: "Idle & Oversized Recommendations"
- Columns: Resource, Signal, Monthly Waste
- Monthly Waste: `font-mono font-semibold text-amber-600` — `$X.XX/mo` format

**renderScanByStatus.tsx (modified):**
- Replaced `import { ScanViewerClient }` with `import { ScanDetailTabs }`
- Replaced `<ScanViewerClient>` with `<ScanDetailTabs>` in ready+URL branch
- Updated comment to reflect Plan 06 change

## Test Results

| Suite | Before | After |
|-------|--------|-------|
| WorkloadTable | 5 it.todo | 3 passing + 2 todo |
| Full dashboard suite | 225 passing | 236 passing |
| Test files | 31 passing | 32 passing |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] WorkloadTable test ambiguous getByText('TGW')**
- **Found during:** Task 2 GREEN (first test run)
- **Issue:** The plan test used `screen.getByText('TGW')` after expanding the chevron, but 'TGW' also appears in the Shared Resources column before expansion — causing `getByText` to throw "multiple elements found"
- **Fix:** Changed assertion to `screen.getByText('$18.25 (50%)')` which is unique to the expanded detail row; also added pre-expansion negative assertion `screen.queryByText('$18.25 (50%)') === null`
- **Files modified:** dashboard/components/scans/WorkloadTable.test.tsx
- **Commit:** ee0c952

**2. [Rule 1 - Bug] scan-detail-polling.test.tsx mocked removed component**
- **Found during:** Task 2 full suite run
- **Issue:** `scan-detail-polling.test.tsx` mocked `ScanViewerClient` and asserted `data-testid="scan-viewer-mock"`, but `renderScanByStatus` now uses `ScanDetailTabs`. The ready-status test failed.
- **Fix:** Replaced `vi.mock('@/components/scans/ScanViewerClient')` with `vi.mock('@/app/(dashboard)/scans/[id]/ScanDetailTabs')` using the same mock shape; updated comment explaining the replacement
- **Files modified:** dashboard/__tests__/scan-detail-polling.test.tsx
- **Commit:** ee0c952

**3. [Rule 1 - Bug] polish-drift gate blocked spec-mandated amber-600**
- **Found during:** Task 2 full suite run
- **Issue:** `polish-drift.test.ts` blocked `text-amber-600` outside 4 specific allowed files. `IdleRecommendationsList.tsx` uses amber-600 for waste amounts per UI-SPEC §"Dashboard — Cost tab".
- **Fix:** Added `IdleRecommendationsList.tsx` to the allowed list with inline comment citing UI-SPEC
- **Files modified:** dashboard/__tests__/polish-drift.test.ts
- **Commit:** ee0c952

**4. [Rule 3 - Blocker] Viewer dist stale — CostLens types not in @infracanvas/viewer**
- **Found during:** Task 2 tsc check
- **Issue:** After Plan 05 added CostLens types to `viewer/src/types.ts` and `viewer/src/index.ts`, the viewer package was never rebuilt. `dist/lib/index.d.ts` did not export CostLensData/WorkloadCost/IdleRecommendation — dashboard tsc failed with TS2305 on all CostLens type imports.
- **Fix:** `cd viewer && npm run build` — rebuilt package; dist now exports all CostLens types; viewer_template.html updated via postbuild
- **Files modified:** viewer/dist/ (gitignored), cli/infracanvas/export/viewer_template.html
- **Commit:** ee0c952

## Known Stubs

- `WorkloadTable.test.tsx`: 2 remaining `it.todo` stubs (`IdleRecommendationsList renders idle recommendations` and `CostTab renders skeleton while loading`) — per plan spec, these are intentionally deferred; the 3 WorkloadTable-specific tests are the plan's critical path

## Self-Check: PASSED

| Item | Status |
|------|--------|
| ScanDetailTabs.tsx | FOUND |
| CostTab.tsx | FOUND |
| WorkloadTable.tsx | FOUND |
| IdleRecommendationsList.tsx | FOUND |
| 09-06-SUMMARY.md | FOUND |
| commit a9eed6e (Task 1) | FOUND |
| commit 79617c5 (RED) | FOUND |
| commit ee0c952 (GREEN) | FOUND |
