import { create } from 'zustand';
import { createStore } from 'zustand/vanilla';
import { useStore as useZustandStore } from 'zustand';
import { createContext, createElement, useContext, useState, type ReactNode } from 'react';
import type {
  AsymmetryPayload,
  DriftStatus,
  NetworkPath,
  ResourceGraph,
  ResourceNode,
  Severity,
} from './types';

interface Filters {
  severities: Severity[];
  resourceTypes: string[];
  driftStatuses: DriftStatus[];
  sources: string[];   // [] = all; ['security', 'policy'] = filtered
}

// FlowMap slice types (Plan 03-06)
type TabId = 'canvas' | 'flowmap' | 'costlens';
type CloudFilter = 'aws' | 'azure' | 'both';

interface FlowMapFilters {
  severities: Severity[];
  cloud: CloudFilter;
  nodeTypes: string[];
  hasFlowLogs: boolean;
}

export interface StoreState {
  graph: ResourceGraph | null;
  selectedNode: ResourceNode | null;
  filterPanelOpen: boolean;
  filters: Filters;
  gateMode: boolean;
  hasFlowMap: boolean;
  searchQuery: string;
  // FlowMap slices (Plan 03-06)
  activeTab: TabId;
  flowMapFilters: FlowMapFilters;
  selectedPath: NetworkPath | null;
  setGraph: (graph: ResourceGraph) => void;
  setSelectedNode: (node: ResourceNode | null) => void;
  toggleFilterPanel: () => void;
  toggleSeverityFilter: (sev: Severity) => void;
  toggleResourceTypeFilter: (type: string) => void;
  toggleDriftFilter: (status: DriftStatus) => void;
  toggleSourceFilter: (source: string) => void;
  clearFilters: () => void;
  setGateMode: (gateMode: boolean) => void;
  setHasFlowMap: (hasFlowMap: boolean) => void;
  setSearchQuery: (query: string) => void;
  // FlowMap actions (Plan 03-06)
  setActiveTab: (tab: TabId) => void;
  toggleFlowMapSeverity: (sev: Severity) => void;
  setFlowMapCloud: (cloud: CloudFilter) => void;
  toggleFlowMapNodeType: (type: string) => void;
  toggleFlowMapFlowLogs: () => void;
  clearFlowMapFilters: () => void;
  setSelectedPath: (path: NetworkPath | null) => void;
  // Phase 12 FMV-02 — Blocker 3 closure. Maps asymmetry payloads onto
  // existing graph.network_paths entries (by forward_path_id) and rebinds
  // selectedPath if its id matches, so selectedPath.asymmetry is populated
  // synchronously for the PathDetailPanel Asymmetry tab.
  setAsymmetries: (asymmetries: AsymmetryPayload[]) => void;
}

const emptyFilters: Filters = {
  severities: [],
  resourceTypes: [],
  driftStatuses: [],
  sources: [],
};

const emptyFlowMapFilters: FlowMapFilters = {
  severities: [],
  cloud: 'both',
  nodeTypes: [],
  hasFlowLogs: false,
};

// Shared state creator — used by both the singleton `useStore` (React hook)
// and the per-instance `createViewerStore` factory (vanilla store) so the
// two exports are guaranteed identical.
type SetFn = (
  partial:
    | StoreState
    | Partial<StoreState>
    | ((state: StoreState) => StoreState | Partial<StoreState>),
  replace?: false,
) => void;

const stateCreator = (set: SetFn): StoreState => ({
  graph: null,
  selectedNode: null,
  filterPanelOpen: false,
  filters: { ...emptyFilters },
  gateMode: true,
  hasFlowMap: false,
  searchQuery: '',

  setGraph: (graph) => set({ graph }),
  setSelectedNode: (node) => set({ selectedNode: node }),
  toggleFilterPanel: () => set((s) => ({ filterPanelOpen: !s.filterPanelOpen })),

  toggleSeverityFilter: (sev) =>
    set((s) => ({
      filters: {
        ...s.filters,
        severities: s.filters.severities.includes(sev)
          ? s.filters.severities.filter((x) => x !== sev)
          : [...s.filters.severities, sev],
      },
    })),

  toggleResourceTypeFilter: (type) =>
    set((s) => ({
      filters: {
        ...s.filters,
        resourceTypes: s.filters.resourceTypes.includes(type)
          ? s.filters.resourceTypes.filter((x) => x !== type)
          : [...s.filters.resourceTypes, type],
      },
    })),

  toggleDriftFilter: (status) =>
    set((s) => ({
      filters: {
        ...s.filters,
        driftStatuses: s.filters.driftStatuses.includes(status)
          ? s.filters.driftStatuses.filter((x) => x !== status)
          : [...s.filters.driftStatuses, status],
      },
    })),

  toggleSourceFilter: (source) =>
    set((s) => ({
      filters: {
        ...s.filters,
        sources: s.filters.sources.includes(source)
          ? s.filters.sources.filter((x) => x !== source)
          : [...s.filters.sources, source],
      },
    })),

  clearFilters: () => set({ filters: { ...emptyFilters } }),

  setGateMode: (gateMode) => set({ gateMode }),
  setHasFlowMap: (hasFlowMap) => set({ hasFlowMap }),
  setSearchQuery: (query) => set({ searchQuery: query }),

  // FlowMap slices (Plan 03-06)
  activeTab: 'canvas',
  flowMapFilters: { ...emptyFlowMapFilters },
  selectedPath: null,

  setActiveTab: (tab) => set({ activeTab: tab }),

  toggleFlowMapSeverity: (sev) =>
    set((s) => ({
      flowMapFilters: {
        ...s.flowMapFilters,
        severities: s.flowMapFilters.severities.includes(sev)
          ? s.flowMapFilters.severities.filter((x) => x !== sev)
          : [...s.flowMapFilters.severities, sev],
      },
    })),

  setFlowMapCloud: (cloud) =>
    set((s) => ({ flowMapFilters: { ...s.flowMapFilters, cloud } })),

  toggleFlowMapNodeType: (type) =>
    set((s) => ({
      flowMapFilters: {
        ...s.flowMapFilters,
        nodeTypes: s.flowMapFilters.nodeTypes.includes(type)
          ? s.flowMapFilters.nodeTypes.filter((x) => x !== type)
          : [...s.flowMapFilters.nodeTypes, type],
      },
    })),

  toggleFlowMapFlowLogs: () =>
    set((s) => ({
      flowMapFilters: { ...s.flowMapFilters, hasFlowLogs: !s.flowMapFilters.hasFlowLogs },
    })),

  clearFlowMapFilters: () => set({ flowMapFilters: { ...emptyFlowMapFilters } }),

  setSelectedPath: (path) => set({ selectedPath: path }),

  // Phase 12 FMV-02 — Blocker 3 closure. Iterate over graph.network_paths and
  // attach matching AsymmetryPayloads (matched by forward_path_id == path.id).
  // Also rebind selectedPath synchronously if its id matches an incoming
  // payload, so the Asymmetry tab + red dashed PathEdge surface populated data.
  setAsymmetries: (asymmetries) =>
    set((s) => {
      if (!s.graph || asymmetries.length === 0) return {};
      const byForwardId = new Map<string, AsymmetryPayload>(
        asymmetries
          .filter((a): a is AsymmetryPayload & { forward_path_id: string } =>
            typeof a.forward_path_id === 'string' && a.forward_path_id.length > 0,
          )
          .map((a) => [a.forward_path_id, a]),
      );
      if (byForwardId.size === 0) return {};
      const nextPaths = (s.graph.network_paths ?? []).map((p) => {
        const payload = byForwardId.get(p.id);
        return payload ? { ...p, asymmetry: payload } : p;
      });
      const nextGraph: ResourceGraph = { ...s.graph, network_paths: nextPaths };
      const nextSelected =
        s.selectedPath && byForwardId.has(s.selectedPath.id)
          ? { ...s.selectedPath, asymmetry: byForwardId.get(s.selectedPath.id)! }
          : s.selectedPath;
      return { graph: nextGraph, selectedPath: nextSelected };
    }),
});

// Singleton — unchanged API for existing components + tests.
export const useStore = create<StoreState>(stateCreator);

// Factory — independent store instance per call. Dashboard (Phase 7) uses
// this to avoid cross-scan state bleed when switching between scan pages.
export function createViewerStore() {
  return createStore<StoreState>(stateCreator);
}

export type ViewerStoreApi = ReturnType<typeof createViewerStore>;

const ViewerStoreContext = createContext<ViewerStoreApi | undefined>(undefined);

// Wraps consumers of the library; creates a default instance if no `store`
// prop is passed. CLI HTML entry (main.tsx) uses the default-instance mode.
export function ViewerProvider({
  store,
  children,
}: {
  store?: ViewerStoreApi;
  children: ReactNode;
}) {
  const [defaultStore] = useState(() => createViewerStore());
  return createElement(
    ViewerStoreContext.Provider,
    { value: store ?? defaultStore },
    children,
  );
}

// Context-based selector hook — dashboard components use this instead of
// the module singleton. Throws outside a ViewerProvider to prevent silent
// fall-through to the singleton (which would defeat per-page isolation).
export function useViewerStore<T>(selector: (state: StoreState) => T): T {
  const store = useContext(ViewerStoreContext);
  if (!store) {
    throw new Error('useViewerStore must be used within a ViewerProvider');
  }
  return useZustandStore(store, selector);
}

// Library components (DiagramCanvas, ResourceNode, etc.) call this so they
// work in BOTH mount paths: the standalone HTML viewer (no provider, writes
// to module singleton) AND the SaaS dashboard (factory store published via
// ViewerProvider). Falls back to the singleton when no provider is present.
export function useViewerStoreOrSingleton<T>(selector: (state: StoreState) => T): T {
  const contextStore = useContext(ViewerStoreContext);
  return useZustandStore(contextStore ?? useStore, selector);
}
