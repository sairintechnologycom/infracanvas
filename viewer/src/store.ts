import { create } from 'zustand';
import type { DriftStatus, NetworkPath, ResourceGraph, ResourceNode, Severity } from './types';

interface Filters {
  severities: Severity[];
  resourceTypes: string[];
  driftStatuses: DriftStatus[];
  sources: string[];   // [] = all; ['security', 'policy'] = filtered
}

// FlowMap slices (Plan 03-06) — shape coordinated with Plan 03-06 for merge parity
type TabId = 'canvas' | 'flowmap';
type CloudFilter = 'aws' | 'azure' | 'both';

interface FlowMapFilters {
  severities: Severity[];
  cloud: CloudFilter;
  nodeTypes: string[];
  hasFlowLogs: boolean;
}

const emptyFlowMapFilters: FlowMapFilters = {
  severities: [],
  cloud: 'both',
  nodeTypes: [],
  hasFlowLogs: false,
};

interface StoreState {
  graph: ResourceGraph | null;
  selectedNode: ResourceNode | null;
  filterPanelOpen: boolean;
  filters: Filters;
  gateMode: boolean;
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
  setSearchQuery: (query: string) => void;
  // FlowMap actions (Plan 03-06)
  setActiveTab: (tab: TabId) => void;
  toggleFlowMapSeverity: (sev: Severity) => void;
  setFlowMapCloud: (cloud: CloudFilter) => void;
  toggleFlowMapNodeType: (type: string) => void;
  toggleFlowMapFlowLogs: () => void;
  clearFlowMapFilters: () => void;
  setSelectedPath: (path: NetworkPath | null) => void;
}

const emptyFilters: Filters = {
  severities: [],
  resourceTypes: [],
  driftStatuses: [],
  sources: [],
};

export const useStore = create<StoreState>((set) => ({
  graph: null,
  selectedNode: null,
  filterPanelOpen: false,
  filters: { ...emptyFilters },
  gateMode: true,
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
  setSearchQuery: (query) => set({ searchQuery: query }),

  // FlowMap slices (Plan 03-06) — shape coordinated for merge parity
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
}));
