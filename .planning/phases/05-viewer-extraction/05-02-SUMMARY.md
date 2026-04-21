---
phase: 05-viewer-extraction
plan: 02
subsystem: viewer
tags: [viewer, zustand, react-context, barrel-exports]
dependency_graph:
  requires: []
  provides:
    - "createViewerStore factory (Zustand vanilla) + ViewerProvider + useViewerStore hook in viewer/src/store.ts"
    - "viewer/src/index.ts barrel — 13 D-04 components + 15 D-05 types + D-11 store API (entry point for vite.config.lib.ts)"
    - "CLI HTML main.tsx wrapped in <ViewerProvider> (Provider API exercised end-to-end)"
  affects:
    - "All existing viewer imports of useStore (singleton) remain byte-identical — no component migrated in Phase 5"
    - "Phase 5 Plan 03 (library build wiring) depends on viewer/src/index.ts as build.lib.entry"
    - "Phase 7 (SaaS Dashboard) consumes createViewerStore per-route via <ViewerProvider store={createViewerStore()}> for DSH-01 state isolation"
tech_stack:
  added:
    - "zustand/vanilla createStore import (zustand 5.0.5, already in package.json)"
  patterns:
    - "Shared state creator — single stateCreator const referenced by both create() (singleton) and createStore() (factory). Guarantees behavior parity between the two store exports."
    - "createElement (not JSX) in store.ts so the file stays .ts — avoids a rename that would force all existing './store' importers to update."
    - "Barrel aliases: GroupNodeMemo -> GroupNode, ResourceNodeMemo -> ResourceNodeComponent. Memo wrappers ARE the canonical public forms in the source files."
key_files:
  created:
    - viewer/src/index.ts
  modified:
    - viewer/src/store.ts
    - viewer/src/main.tsx
decisions:
  - "Keep store.ts as .ts and use React.createElement rather than renaming to .tsx (avoids breaking ~14 component imports of './store' and test imports)."
  - "Expose StoreState and ViewerStoreApi as public types — downstream dashboard and plugin code need them for typed selectors and provider-store threading."
  - "useViewerStore() throws outside a <ViewerProvider> rather than silently falling back to the singleton — silent fallback would defeat Phase 7's per-page store isolation requirement (DSH-01)."
  - "Barrel re-exports the memo wrappers (GroupNodeMemo / ResourceNodeMemo) under the plan's documented names (GroupNode / ResourceNodeComponent). The memo wrappers are the canonical forms actually exported from the source files and the forms used by tests."
metrics:
  duration_sec: 139
  duration_note: "Execution wall-clock from Task 1 commit to Task 3 commit; excludes setup (npm ci) and SUMMARY authoring."
  tasks_completed: 3
  files_changed: 3
  completed_date: "2026-04-21"
requirements:
  - DSH-01
---

# Phase 5 Plan 02: Store Factory + Context Provider + Library Barrel Summary

Adds a Zustand store factory + React Context Provider + context-based selector hook alongside the existing singleton `useStore`, wraps the CLI HTML entry in the Provider, and creates `viewer/src/index.ts` as the library barrel that re-exports 13 D-04 components, 15 D-05 types, and the D-11 store API.

## Objective Recap

DSH-01 (Phase 7 dashboard) requires one independent store per page to prevent scan state bleed across routes. The existing singleton is load-bearing for 130 Vitest tests and the CLI single-file HTML; coexistence of singleton + factory is the only non-breaking path. This plan lands the factory + Provider + hook, wires the CLI entry, and creates the barrel that `vite.config.lib.ts` (Plan 03) resolves.

## Exports Added

### `viewer/src/store.ts` new public surface

| Identifier | Kind | Purpose |
|------------|------|---------|
| `StoreState` | `interface` (now exported) | Type for downstream selectors + provider threading |
| `createViewerStore` | factory fn | Returns an independent vanilla Zustand store |
| `ViewerStoreApi` | type alias | `ReturnType<typeof createViewerStore>` |
| `ViewerProvider` | React component | Accepts optional `store` prop, creates default instance if none given |
| `useViewerStore<T>(selector)` | hook | Context-scoped selector, throws outside a `<ViewerProvider>` |
| `useStore` (singleton) | existing | UNCHANGED — still the default export every component uses |

### `viewer/src/index.ts` (new barrel)

- 9 Canvas components: `DiagramCanvas`, `FilterPanel`, `DetailPanel`, `SummaryBar`, `TabBar`, `SearchBar`, `FindingCard`, `GroupNode` (alias of `GroupNodeMemo`), `ResourceNodeComponent` (alias of `ResourceNodeMemo`).
- 4 FlowMap components: `FlowMapCanvas`, `FlowMapFilterPanel`, `PathDetailPanel`, `FlowMapEmptyState`.
- 15 types re-exported from `./types`: `Severity`, `DriftStatus`, `Finding`, `NetworkFinding`, `CostEstimate`, `AttributeChange`, `ResourceNode`, `GraphEdge`, `GraphSummary`, `GraphMetadata`, `PathHop`, `NetworkPath`, `DCCollectorReading`, `DCSite`, `ResourceGraph`.
- Store API: `createViewerStore`, `ViewerProvider`, `useViewerStore` (values) + `ViewerStoreApi`, `StoreState` (types).
- **No side-effect imports** — the `'use client'` directive will be injected by `rollupOptions.output.banner` in `vite.config.lib.ts` (Plan 03).

Total `^export` statements: **16** (plan required ≥14).

## Test Baseline

| Phase | Test Files | Tests | Notes |
|-------|------------|-------|-------|
| Pre-phase baseline | 3 failed / 14 passed (17) | 6 failed / 130 passed (136) | Pre-existing failures are 2 path-rendering tests in `__tests__/flowmap/PathEdge.test.tsx` and 4 others surfaced by the project's Vitest baseline. |
| After Task 1 (store.ts) | 3 failed / 14 passed | 6 failed / 130 passed | Identical delta — no regression. |
| After Task 2 (main.tsx) | 3 failed / 14 passed | 6 failed / 130 passed | Identical delta — no regression. |
| After Task 3 (index.ts) | 3 failed / 14 passed | 6 failed / 130 passed | Identical delta — no regression. |

`npx tsc --noEmit` is clean at each step.

## Component Files Confirmation

`git diff --name-only HEAD~3 HEAD -- viewer/src/components/` returns empty. **No component file under `viewer/src/components/**` was modified**; D-04 components remain source-identical per the plan's invariant.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Barrel re-exported non-existent named exports for GroupNode and ResourceNode components**

- **Found during:** Task 3 (barrel creation)
- **Issue:** Plan's `<interfaces>` block claimed `viewer/src/components/GroupNode.tsx` and `viewer/src/components/ResourceNode.tsx` have named exports `GroupNode` and `ResourceNode` respectively. Reality: both files export **only** the memoized wrappers `GroupNodeMemo` and `ResourceNodeMemo` (lines 124 and the equivalent in ResourceNode.tsx). An unqualified `export { GroupNode } from './components/GroupNode'` would fail TypeScript resolution.
- **Fix:** Re-export the memo wrappers under the plan's documented consumer names — `GroupNodeMemo as GroupNode` and `ResourceNodeMemo as ResourceNodeComponent`. These memo wrappers are already the canonical public forms (tests import `ResourceNodeMemo` and use it as the component under test; `App.tsx`/layout consume them via the node-type registry).
- **Files modified:** `viewer/src/index.ts` (lines 19-26)
- **Commit:** `d92c8d5`
- **Public export names are exactly as the plan specified** (`GroupNode`, `ResourceNodeComponent`). Only the `from` path re-export mechanics changed.

### TypeScript Inference Notes

- `SetFn` was defined explicitly as a typed set-function alias (partial | state | updater-function overload with optional `replace?: false`) so that `stateCreator` can be accepted by **both** `create<StoreState>(...)` and `createStore<StoreState>(...)` without any-casts. Both zustand APIs infer the same shape from this signature.
- No adjustments to existing component-side selector types were required.

## Authentication Gates

None — plan executed autonomously.

## Self-Check: PASSED

- `viewer/src/store.ts`: FOUND — all 6 exports present (`useStore`, `createViewerStore`, `ViewerProvider`, `useViewerStore`, `ViewerStoreApi`, `StoreState`).
- `viewer/src/main.tsx`: FOUND — `<ViewerProvider>` wraps `<App />`.
- `viewer/src/index.ts`: FOUND — 16 export statements, all required identifiers present, no side-effect CSS import.
- Commit `7bf83a4` (Task 1): FOUND in git log.
- Commit `fbc2261` (Task 2): FOUND in git log.
- Commit `d92c8d5` (Task 3): FOUND in git log.
- `npx tsc --noEmit` after all three tasks: clean (no TS errors).
- `npm test -- --run`: 130 passing / 6 pre-existing failures — delta unchanged vs. pre-phase baseline.
- Component files (`viewer/src/components/**`): UNMODIFIED (empty `git diff --name-only`).
