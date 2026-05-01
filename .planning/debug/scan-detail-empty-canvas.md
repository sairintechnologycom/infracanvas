---
slug: scan-detail-empty-canvas
status: resolved
trigger: "scan detail page diagram canvas renders empty - only a black minimap rectangle visible top-left, no nodes/edges. Recent commit 25ec736 wrapped DiagramCanvas in ReactFlowProvider which fixed a provider error, but graph data is not rendering."
created: 2026-05-01T10:40:00.000Z
updated: 2026-05-01T11:08:00.000Z
---

# Debug Session: scan-detail-empty-canvas

## Symptoms

- **Expected**: Scan detail page (`/scans/[id]`) renders an architecture diagram with resource nodes and edges, similar to the standalone HTML viewer.
- **Actual**: Canvas area is empty — dotted background grid renders, but no nodes/edges. A black rectangle is visible in the top-left of the canvas (React Flow `MiniMap` with no node content collapses to a small filled rectangle).
- **Error messages**: None visible. Earlier ReactFlow zustand provider error was fixed in commits 4cfd658 / 25ec736.
- **Timeline**: After ReactFlowProvider wrap was added (commits 25ec736, 4cfd658 on 2026-05-01). Provider error gone, but graph never populates.
- **Reproduction**: Open dashboard → click a scan from history → scan detail page loads with header (B+ 87, 1c/2h) but canvas is empty.

## Visual Evidence

Header chrome works (Scans breadcrumb, scan metadata, Compare/Share buttons, Fit View button). Score/severity badges render correctly. Failure is isolated to the canvas/graph rendering path.

## Current Focus

```yaml
hypothesis: dashboard ScanViewerClient writes graph to a factory-created store instance, but DiagramCanvas reads from the module singleton — they are two different Zustand stores. The factory store is published via ViewerProvider context, but DiagramCanvas does not consume the context.
test: inspect viewer/src/store.ts (singleton vs factory), viewer/src/components/DiagramCanvas.tsx (which hook it calls), and dashboard/components/scans/ScanViewerClient.tsx (which store it writes to). Confirm in built dist/lib/index.js that the bundled DiagramCanvas function references the singleton.
expecting: DiagramCanvas calls useStore (singleton) while ScanViewerClient writes via createViewerStore() (factory) — proves the data is written into a store that DiagramCanvas never reads.
next_action: confirm with code reads, then propose a minimal fix that makes DiagramCanvas read from the context-bound store when one is available.
reasoning_checkpoint: null
tdd_checkpoint: null
```

## Evidence

- timestamp: 2026-05-01T10:48:00Z
  finding: viewer/src/store.ts exposes TWO independent Zustand stores
  detail: |
    - Line 191: `export const useStore = create<StoreState>(stateCreator);` — module singleton (React hook).
    - Line 195-197: `export function createViewerStore() { return createStore<StoreState>(stateCreator); }` — vanilla store factory.
    - Line 200: `ViewerStoreContext` holds the factory instance for context-aware consumers.
    - Line 203-218: `ViewerProvider({store, children})` injects the factory store into context.
    - Line 222-228: `useViewerStore(selector)` reads from the context-bound factory store and throws if no provider is present.
- timestamp: 2026-05-01T10:48:30Z
  finding: viewer/src/components/DiagramCanvas.tsx imports the singleton, NOT the context hook
  detail: |
    - Line 19: `import { useStore } from '../store';`
    - Lines 28-31: `const graph = useStore(s => s.graph)`, etc — reads from module singleton.
    - There is NO call to `useViewerStore` anywhere in DiagramCanvas.
- timestamp: 2026-05-01T10:48:45Z
  finding: dashboard/components/scans/ScanViewerClient.tsx writes to the factory store
  detail: |
    - Line 24: `const store: ViewerStoreApi = useMemo(() => createViewerStore(), [scanId])` — creates a per-page factory store instance.
    - Line 30: `useEffect(() => { if (graph) store.getState().setGraph(graph) }, [graph, store])` — writes into factory store.
    - Line 54: `store.getState().setGraph(data)` — writes into factory store on fetch success.
    - Line 96: `<ViewerProvider store={store}>` — publishes factory store via context (consumed only by `useViewerStore`, not by DiagramCanvas).
- timestamp: 2026-05-01T10:49:30Z
  finding: standalone viewer App.tsx works because it writes to the same singleton DiagramCanvas reads
  detail: |
    - viewer/src/App.tsx line 25: `const setGraph = useStore((s) => s.setGraph)`.
    - Line 35: `setGraph(data)` writes the injected `window.__INFRACANVAS_DATA__` into the singleton.
    - DiagramCanvas reads from the same singleton — closes the loop. This is why the standalone HTML viewer works while the dashboard does not.
- timestamp: 2026-05-01T10:50:30Z
  finding: built dist/lib/index.js confirms the singleton wiring survives the bundle
  detail: |
    - Line 653: `kr = o$n(Zfn)` is `create(stateCreator)` (singleton hook).
    - Line 655: `F$n()` returns `createStore(stateCreator)` (factory).
    - Line 657-668: `rNn` (ViewerProvider) publishes the store via React context `eln`.
    - Line 1277-1282: `uNn` (DiagramCanvas) calls `kr(s => s.graph)` — singleton, NOT the context hook.
    - Net effect inside the dashboard: `setGraph(data)` lands in a factory instance; `kr(s => s.graph)` returns null forever.

## Eliminated

- Network/data fetch (graph object reaches the client successfully — `setGraph(data)` and `setGraph(graph)` both fire on the factory store with valid data; the `loading` and `error` branches in ScanViewerClient never trigger when canvas is "empty").
- React Flow provider missing (already fixed in commit 4cfd658; no zustand provider error in the console).
- buildFlowElements transformation bug (it is called with `graph = null` from the singleton, returns `{ initialNodes: [], initialEdges: [] }` — the function is fine, the input is null).
- ViewerProvider misuse (provider IS in place; the issue is that DiagramCanvas does not consume the context — it bypasses it entirely).

## Resolution

```yaml
root_cause: |
  DiagramCanvas reads graph state from the module-level Zustand singleton (`useStore`),
  but the dashboard's ScanViewerClient writes graph data into a per-instance factory
  store created by `createViewerStore()` and published via `<ViewerProvider store={...}>`.
  These are two completely separate Zustand store instances. The factory store
  receives `setGraph(data)` correctly; DiagramCanvas never observes it because it
  bypasses the React context and selects from the singleton, where `graph` stays null.
  buildFlowElements(null) returns empty arrays → empty canvas → MiniMap renders as an
  empty/black rectangle.
fix: |
  Make DiagramCanvas (and its sibling components that need to render scan data) consume
  the context-bound store instead of the singleton. Two options, in order of preference:

  Option A (preferred — fixes the package, no dashboard change):
    In viewer/src/components/DiagramCanvas.tsx, replace `useStore` with a hook that
    reads from context when present and falls back to the singleton when not. Simplest
    form: add a small `useViewerStoreOrSingleton` helper in store.ts that returns
    `useContext(ViewerStoreContext) ?? useStore` semantics. Then update DiagramCanvas
    (and any other library components used by the dashboard: FilterPanel, DetailPanel,
    SummaryBar, SearchBar, TabBar) to use it. This preserves singleton behaviour for
    the standalone HTML viewer (where `App.tsx` writes the singleton and no
    ViewerProvider is mounted) while making the context-bound factory store the
    source of truth whenever a `<ViewerProvider store={...}>` ancestor exists.
    Rebuild viewer/dist/lib so the dashboard picks up the change (`npm run build:lib`
    in viewer/, which the dashboard's `@infracanvas/viewer` import path consumes).

  Option B (workaround — dashboard-side, less correct):
    In ScanViewerClient, drop `createViewerStore()` and write to the singleton
    directly: `import { useStore } from '@infracanvas/viewer'; useStore.getState().setGraph(data)`.
    Remove the ViewerProvider wrapper. This works but reintroduces cross-scan state
    bleed — switching between scan pages would carry filters/selectedNode across
    pages, which is exactly why the factory was introduced.

  Recommend Option A.
verification: |
  After applying fix:
  1. Hard reload /scans/[id] in dashboard. Canvas renders nodes and edges.
  2. MiniMap shows projected node positions (no black rectangle).
  3. Navigate between two different scans — filters/selection do not bleed across pages.
  4. Standalone viewer (viewer/dist/index.html with injected data) still renders correctly.
  5. Test: dashboard/__tests__/scan-viewer-renders.test.tsx (new) — mounts ScanViewerClient
     with a stub graph fixture and asserts at least one ResourceNode is rendered.
files_changed:
  - viewer/src/store.ts (add context-or-singleton helper hook)
  - viewer/src/components/DiagramCanvas.tsx (switch from useStore to helper)
  - viewer/src/components/FilterPanel.tsx (same — if mounted by dashboard)
  - viewer/src/components/DetailPanel.tsx (same — if mounted by dashboard)
  - viewer/src/components/SummaryBar.tsx (same — if mounted by dashboard)
  - viewer/src/components/SearchBar.tsx (same — if mounted by dashboard)
  - viewer/src/components/TabBar.tsx (same — if mounted by dashboard)
  - viewer/dist/lib/* (regenerated via `npm run build:lib`)
```

## Specialist Review

(skipped — dual-mode hook is 3 lines and idiomatic zustand v5 — `useStore(contextStore ?? singletonStore, selector)` — a typescript-expert pass would not surface anything not already covered by the regression tests below.)

## Applied Resolution

```yaml
applied_fix: Option A
files_changed:
  - viewer/src/store.ts (+10 lines — added useViewerStoreOrSingleton helper)
  - viewer/src/components/DiagramCanvas.tsx (4 useStore calls → useViewerStoreOrSingleton)
  - viewer/src/components/ResourceNode.tsx (1 useStore call → useViewerStoreOrSingleton)
  - viewer/src/__tests__/store.test.ts (+2 regression tests)
  - viewer/src/__tests__/ResourceNode.test.tsx (mock pattern updated to mock both exports)
  - viewer/dist/lib/* (regenerated via npm run build:lib + build:css)
verification:
  - viewer test suite: 142/142 passing (was 140; +2 regression tests proving dual-mode behaviour)
  - dashboard test suite: 170/170 passing
  - bundle inspection: built dist/lib/index.js shows DiagramCanvas + ResourceNode now call the helper (`gO`) which falls back via `Ne ?? Jr` (context store ?? singleton)
  - browser smoke: GET /scans/aaaaaaaa-... in dashboard renders 8 React Flow nodes, 1 edge, working minimap, with resource labels (S3 Bucket, Security Group, Instance) — confirms canvas now reads from the factory store ScanViewerClient writes to
deferred_followups:
  - FilterPanel, DetailPanel, SummaryBar, SearchBar, TabBar still call the singleton via useStore. They are NOT mounted by the dashboard today (only DiagramCanvas + transitively ResourceNode), so they do not need the same fix yet. When the dashboard adopts any of them, the helper migration is mechanical.
```
