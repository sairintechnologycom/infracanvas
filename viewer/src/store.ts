import { create } from 'zustand';
import type { DriftStatus, ResourceGraph, ResourceNode, Severity } from './types';

interface Filters {
  severities: Severity[];
  resourceTypes: string[];
  driftStatuses: DriftStatus[];
}

interface StoreState {
  graph: ResourceGraph | null;
  selectedNode: ResourceNode | null;
  filterPanelOpen: boolean;
  filters: Filters;
  setGraph: (graph: ResourceGraph) => void;
  setSelectedNode: (node: ResourceNode | null) => void;
  toggleFilterPanel: () => void;
  toggleSeverityFilter: (sev: Severity) => void;
  toggleResourceTypeFilter: (type: string) => void;
  toggleDriftFilter: (status: DriftStatus) => void;
  clearFilters: () => void;
}

const emptyFilters: Filters = {
  severities: [],
  resourceTypes: [],
  driftStatuses: [],
};

export const useStore = create<StoreState>((set) => ({
  graph: null,
  selectedNode: null,
  filterPanelOpen: false,
  filters: { ...emptyFilters },

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

  clearFilters: () => set({ filters: { ...emptyFilters } }),
}));
