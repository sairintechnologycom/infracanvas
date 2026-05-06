---
phase: 03-flowmap-v1-0
plan: 06
subsystem: ui
tags: [zustand, react, tabbar, react-lazy, aria, viewer]

requires:
  - phase: 03-flowmap-v1-0/plan-01
    provides: NetworkPath TS interface and ResourceGraph v2.1 with network_paths/dc_sites fields
provides:
  - Zustand store extensions: activeTab/setActiveTab, selectedPath/setSelectedPath, flowMapFilters slice (severities/cloud/nodeTypes/hasFlowLogs) + toggle/clear actions
  - TabBar component with role='tablist', ArrowLeft/Right/Home/End keyboard navigation, aria-selected, BETA pill on FlowMap tab
  - App.tsx shell: TabBar placed between SummaryBar and the 3-column layout; activeTab-conditioned React.lazy swap of the three children to FlowMapFilterPanel/FlowMapCanvas/PathDetailPanel
affects: [03-07, 03-08 — FlowMap UI components that read the flowMapFilters slice and set selectedPath]

tech-stack:
  added: []
  patterns: [React.lazy + Suspense for tab-switched routes, per-tab filter state preservation, role='tabpanel' wrapping the 3-column shell]

key-files:
  created:
    - viewer/src/components/TabBar.tsx
    - viewer/src/__tests__/flowmap/TabBar.test.tsx
  modified:
    - viewer/src/store.ts
    - viewer/src/App.tsx
    - viewer/src/__tests__/store.test.ts

key-decisions:
  - "React.lazy + Suspense for FlowMap children — 03-06 has NO compile-time dependency on 03-07/08. Before those plans merge, App.tsx still compiles and Canvas tab works; FlowMap chunk only loads when activeTab switches."
  - "Canvas filters and FlowMap filters live in separate store slices with no cross-contamination — switching tabs preserves each tab's filter state (spec requirement)"
  - "TabBar uses inline styles that mirror the dark shell theme (#0f1419 background, #252d3d border) rather than Tailwind classes — matches existing FilterPanel/DetailPanel dark-chrome pattern"

patterns-established:
  - "Tab-switched routing via Zustand activeTab selector + React.lazy children (no router library needed)"
  - "WAI-ARIA tablist pattern: role=tablist on container, role=tab on buttons, tabIndex={isActive ? 0 : -1}, aria-selected, aria-controls pointing at role=tabpanel"

requirements-completed: [FMV-01, FMV-05]

duration: ~35 min (initial executor through Task 2 RED) + ~10 min (orchestrator inline completion of Task 2 GREEN + Task 3)
completed: 2026-04-19
---

# Phase 03-flowmap-v1-0 / Plan 06: TabBar + Zustand FlowMap slices + App shell swap

**Canvas/FlowMap TabBar with BETA pill + keyboard nav, Zustand flowMapFilters/activeTab/selectedPath slices, and App.tsx React.lazy swap of the 3-column shell when FlowMap tab is active.**

## Performance

- **Duration:** ~45 min total (sub-agent executed through Task 2 RED, then hit a silent stop — orchestrator verified WIP, landed TabBar.tsx inline, wired App.tsx, added SUMMARY)
- **Tasks:** 3/3
- **Files modified:** 5 (3 task commits from sub-agent + 1 completion commit from orchestrator)

## Accomplishments
- Zustand store gains FlowMap tab slice (activeTab, setActiveTab), path selection slice (selectedPath, setSelectedPath), and flowMapFilters with 4 facets (severities, cloud tri-state, nodeTypes, hasFlowLogs) plus toggle/clear actions
- TabBar component: role='tablist', Canvas + FlowMap buttons, ArrowLeft/ArrowRight/Home/End keyboard navigation, aria-selected reflects activeTab, BETA pill on FlowMap tab, tooltip copy per UI-SPEC
- App.tsx: TabBar rendered between SummaryBar and the 3-column shell; role='tabpanel' wrapper swaps between (FilterPanel + DiagramCanvas + DetailPanel) and React.lazy(FlowMapFilterPanel + FlowMapCanvas + PathDetailPanel) based on activeTab
- Lazy loading means no hard compile dependency on 03-07/08 — Canvas path stays functional if FlowMap chunks fail to load; Suspense fallback is an empty flex container

## Task Commits

1. **Task 1 (TDD red):** `7bd072f` — test(03-06): failing tests for activeTab/selectedPath/flowMapFilters
2. **Task 1 (TDD green):** `3d6fff1` — feat(03-06): Zustand slices landed
3. **Task 2 (TDD red):** `58b2663` — test(03-06): failing TabBar ARIA + keyboard tests
4. **Task 2 GREEN + Task 3 (orchestrator):** `4b10789` — feat(03-06): complete TabBar component + App shell wiring
5. **Post-wave stitch:** `f47382b` — chore(03): wire FlowMapEmptyState into FlowMapCanvas (D-08) + ResizeObserver polyfill

## Files Created/Modified
- `viewer/src/store.ts` — activeTab/selectedPath/flowMapFilters slices + actions
- `viewer/src/__tests__/store.test.ts` — extended coverage for new slices
- `viewer/src/components/TabBar.tsx` — new component (roles, keyboard nav, BETA pill, inline-styled)
- `viewer/src/__tests__/flowmap/TabBar.test.tsx` — ARIA + keyboard + BETA test suite
- `viewer/src/App.tsx` — TabBar placement + activeTab-conditioned React.lazy shell swap

## Decisions Made
- Inline CSS in TabBar matches existing FilterPanel/DetailPanel dark-chrome pattern — no Tailwind utility classes in this component. Consistent with the viewer's mixed styling approach.
- React.lazy imports resolve to `{ default: m.FlowMapCanvas }` etc. since the sibling components export named (not default) exports. This preserves the hard-dependency-free promise.

## Deviations from Plan
- **Sub-agent interruption during Task 2 (silent stop after TDD-red):** The executor committed the TabBar.test.tsx failing test but did not create TabBar.tsx or edit App.tsx. The task-notification reported "completed" but the worktree state proved otherwise (TabBar.tsx untracked, App.tsx unchanged). Orchestrator diagnosed this by spot-checking the worktree immediately after the notification fired, then finished Task 2 GREEN + Task 3 inline.
- **Store.ts merge conflict with Plan 03-08:** Both 03-06 (correctly — this plan owns the slice) and 03-08 (as a deviation — needed the slice to pass its own tsc) added a flowMapFilters slice to store.ts. Git auto-merge couldn't reconcile the minor formatting/comment-phrasing differences. Orchestrator resolved by taking 03-06's canonical version — shape is byte-identical per 03-08's deviation note, so no semantic loss.

## Issues Encountered
- Post-merge tsc initially failed with "cannot find module 'elkjs/lib/elk.bundled.js'" — resolved by running `npm install` (elkjs was declared in package.json by Plan 03-01 but not yet installed in node_modules). Fixed as part of the post-wave stitch commit.
- jsdom-environment ReactFlow tests failed with "ResizeObserver is not defined" — resolved by adding a minimal ResizeObserver polyfill to vitest setup.ts. Documented in SUMMARY because it's a test-infra change that benefits every FlowMap component test.

## User Setup Required
None — purely frontend changes.

## Next Phase Readiness
- FlowMap tab is navigable from the viewer UI
- Plan 03-07 (FlowMapCanvas) loads cleanly on activeTab==='flowmap' via React.lazy
- Plan 03-08 (FlowMapFilterPanel + PathDetailPanel) render in the left/right slots of the 3-column shell when FlowMap tab is active
- flowMapFilters slice is ready to be wired to the filter panel UI (Plan 03-08 already consumes it)
- selectedPath slice is ready for Plan 03-08's PathDetailPanel to populate on path click
- Wave 3 (Plans 03-03 AWS + 03-04 Azure collectors) can land without any FlowMap viewer work — the viewer renders FlowMapEmptyState while the collectors are empty-producing

---
*Phase: 03-flowmap-v1-0*
*Completed: 2026-04-19*
