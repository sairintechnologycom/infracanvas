# Unified UI Design: Canvas + FlowMap + CostLens

**Date:** 2026-05-01
**Status:** Approved — ready for implementation planning
**Scope:** Surface the existing viewer tab shell in the SaaS dashboard, add CostLens tab placeholder, and change FlowMap from disabled to empty-state-CTA behaviour.

---

## Problem

Today, the viewer package (`@infracanvas/viewer`) already has a Canvas/FlowMap tab shell in `App.tsx` — with keyboard shortcuts, hash-based URL sync, and lazy-loaded FlowMap components. However:

1. The dashboard's `ScanViewerClient` renders `DiagramCanvas` directly and never sees the tab shell.
2. `App` is not exported from `index.ts`, so the dashboard can't use it.
3. The FlowMap tab is currently **disabled** when there's no network data. The agreed behaviour is an **empty state CTA** instead (always clickable).
4. There is no CostLens tab yet.

---

## Decision

Wire the existing viewer `App` into the dashboard as `ViewerApp`, make three targeted changes to the viewer package, and update `ScanViewerClient` to use `ViewerApp`. The dashboard's `MetadataHeader` and `ScanDetailActions` remain outside the viewer — they're dashboard concerns.

---

## Navigation Structure

- **Tabs inside the scan detail page** (`/scans/[id]`): `Canvas | FlowMap | CostLens`
- Tab bar sits between `MetadataHeader` and the diagram canvas, owned by the viewer package
- Switching tabs is instant client-side state — no navigation, no re-fetch
- Sidebar stays as-is (Scans / Compare / Settings) — no new top-level routes

---

## Tab Behaviour

### Canvas tab
- Default active tab. Renders `FilterPanel + DiagramCanvas + DetailPanel` (unchanged).

### FlowMap tab
- **Always clickable** — never disabled.
- If `hasFlowMap` is true: renders `FlowMapFilterPanel + FlowMapCanvas + PathDetailPanel`.
- If `hasFlowMap` is false: renders `FlowMapEmptyState` with a "Connect a collector →" CTA (display-only text; no link destination is in scope for this phase).
- `hasFlowMap` in standalone HTML: derived from `Boolean(injected?.flowmap)` (existing logic, unchanged).
- `hasFlowMap` in dashboard: derived from `Boolean(graph.network_paths?.length)`, set by `ScanViewerClient` after graph loads.

### CostLens tab
- Rendered but non-interactive: greyed out, pointer-events none, "soon" badge.
- Becomes a real tab when Phase 9 ships — no structural change needed.

---

## What Actually Changes

The hard parts (tab shell in `App.tsx`, store fields, keyboard shortcuts, hash sync) are **already done**. The remaining delta is 4 targeted edits:

### 1. `viewer/src/components/TabBar.tsx` — modify

Two changes:
- **Remove disabled logic for FlowMap:** Delete the `isDisabled` guard and `cursor: not-allowed` style. FlowMap tab is always clickable regardless of `hasFlowMap`.
- **Add CostLens tab:** Append a third entry to `TABS` with `id: 'costlens'`, label `'CostLens'`, a `soon` badge (styled like the existing `beta` badge but blue), and `tabIndex={-1}` + `pointer-events: none` always — it is never interactive.

### 2. `viewer/src/App.tsx` — modify

One change:
- In the `isFlowMap` branch, wrap the FlowMap render in a `hasFlowMap` check:
  - `hasFlowMap === true` → existing `<FlowMapFilterPanel/><FlowMapCanvas/><PathDetailPanel/>` render (unchanged)
  - `hasFlowMap === false` → render `<FlowMapEmptyState />` centred in the panel

### 3. `viewer/src/index.ts` — modify

One change:
- Add a named export: `export { default as ViewerApp } from './App'`
- Existing exports are untouched.

### 4. `dashboard/components/scans/ScanViewerClient.tsx` — modify

Two changes:
- Replace `import { DiagramCanvas } from '@infracanvas/viewer'` with `import { ViewerApp } from '@infracanvas/viewer'`.
- After the graph loads (in the `.then()` callback), call `store.getState().setHasFlowMap(Boolean(data.network_paths?.length))` before `setGraph`.
- Remove the `<ReactFlowProvider>` wrapper — `ViewerApp` (`App.tsx`) already mounts `ReactFlowProvider` internally.
- Replace `<DiagramCanvas />` with `<ViewerApp />` in the JSX.

---

## Store — Minor Type Change Only

`activeTab`, `setActiveTab`, `hasFlowMap`, `setHasFlowMap` already exist in `viewer/src/store.ts`. One change: widen the `TabId` type from `'canvas' | 'flowmap'` to `'canvas' | 'flowmap' | 'costlens'` so it matches the new tab definition. The store value will never actually be `'costlens'` since that tab is always non-interactive, but the type should be consistent with the UI.

---

## Error Handling

- `network_paths` undefined or empty: both treated as no data — `Boolean(data.network_paths?.length)` handles both.
- FlowMap empty state render: `FlowMapEmptyState` already exists in the package.
- Tab switch during graph loading: graph is loaded before the viewer is shown (`ScanViewerClient` shows a loading spinner until complete), so no race condition.

---

## Testing

| Test file | Action | What it covers |
|---|---|---|
| `viewer/src/__tests__/TabBar.test.tsx` | Update | FlowMap tab always clickable; empty state renders when `hasFlowMap=false`; CostLens tab non-interactive |
| `viewer/src/__tests__/App.test.tsx` | Update | FlowMap empty state shown when `hasFlowMap=false` and tab is active |
| `dashboard/__tests__/ScanViewerClient.test.tsx` | Update | `ViewerApp` renders; `setHasFlowMap` called with correct value; no `ReactFlowProvider` double-wrap |

---

## Explicitly Out of Scope

- CostLens implementation (Phase 9)
- FlowMap asymmetric routing (Phase 12)
- Sidebar changes
- New backend endpoints
- FlowMap data collection changes
- `SummaryBar` or `FilterPanel` changes
- Keyboard shortcut changes (already done in Phase 4)

---

## Files Changed Summary

| File | Action |
|---|---|
| `viewer/src/components/TabBar.tsx` | Modify — remove FlowMap disabled logic; add CostLens "soon" tab |
| `viewer/src/App.tsx` | Modify — render `FlowMapEmptyState` when `hasFlowMap=false` and FlowMap tab active |
| `viewer/src/store.ts` | Modify — widen `TabId` type to include `'costlens'` |
| `viewer/src/index.ts` | Modify — export `App` as `ViewerApp` |
| `dashboard/components/scans/ScanViewerClient.tsx` | Modify — use `ViewerApp`, call `setHasFlowMap`, drop `ReactFlowProvider` wrapper |
