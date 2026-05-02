// Library entry for @infracanvas/viewer
//
// Consumed by two builds:
//   1. `vite.config.lib.ts` → dist/lib/index.js (Next.js dashboard, Phase 7)
//   2. Tests + app bundle import component names directly from ./components
//
// Do NOT add side-effect imports here — the 'use client' banner is emitted
// by rollupOptions.output.banner in vite.config.lib.ts, not by a source
// directive (Rollup's optimizer strips source-level bare strings).

// ===== Full app (used by dashboard ScanViewerClient) =====
export { default as ViewerApp } from './App'

// ===== Components (D-04 — full set) =====
export { DiagramCanvas } from './components/DiagramCanvas'
export { FilterPanel } from './components/FilterPanel'
export { DetailPanel } from './components/DetailPanel'
export { SummaryBar } from './components/SummaryBar'
export { TabBar } from './components/TabBar'
export { SearchBar } from './components/SearchBar'
export { FindingCard } from './components/FindingCard'
// GroupNode.tsx and ResourceNode.tsx export memoized wrappers
// (GroupNodeMemo / ResourceNodeMemo) as their canonical public component.
// Re-export under the plan's documented names — `GroupNode` for the group
// renderer, `ResourceNodeComponent` for the resource renderer (the latter
// aliased so it doesn't clash with the `ResourceNode` data type exported
// from ./types below).
export { GroupNodeMemo as GroupNode } from './components/GroupNode'
export { ResourceNodeMemo as ResourceNodeComponent } from './components/ResourceNode'

export { FlowMapCanvas } from './components/flowmap/FlowMapCanvas'
export { FlowMapFilterPanel } from './components/flowmap/FlowMapFilterPanel'
export { PathDetailPanel } from './components/flowmap/PathDetailPanel'
export { FlowMapEmptyState } from './components/flowmap/FlowMapEmptyState'

// ===== Types (D-05 — all public types from types.ts) =====
export type {
  Severity,
  DriftStatus,
  Finding,
  NetworkFinding,
  CostEstimate,
  AttributeChange,
  ResourceNode,
  GraphEdge,
  GraphSummary,
  GraphMetadata,
  PathHop,
  NetworkPath,
  DCCollectorReading,
  DCSite,
  ResourceGraph,
} from './types'

// ===== Store API (D-11 — factory + Context Provider + hook) =====
export {
  createViewerStore,
  ViewerProvider,
  useViewerStore,
} from './store'

export type { ViewerStoreApi, StoreState } from './store'
