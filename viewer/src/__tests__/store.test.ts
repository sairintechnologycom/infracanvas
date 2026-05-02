import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { createElement, type ReactNode } from 'react';
import {
  useStore,
  createViewerStore,
  ViewerProvider,
  useViewerStoreOrSingleton,
} from '../store';
import type { ResourceGraph, ResourceNode } from '../types';

const mockNode: ResourceNode = {
  id: 'aws_vpc.main',
  type: 'aws_vpc',
  name: 'main',
  provider: 'aws',
  module: '',
  region: 'us-east-1',
  group: '',
  attributes: { cidr_block: '10.0.0.0/16' },
  dependencies: [],
  findings: [],
  cost: { monthly_usd: 0, currency: 'USD', basis: '' },
  drift: 'unchanged',
  position: { x: 0, y: 0 },
};

const mockGraph: ResourceGraph = {
  version: '1.0',
  metadata: {
    scan_id: 'test-001',
    project: 'test-project',
    provider: 'aws',
    scanned_at: '2026-01-01T00:00:00Z',
    terraform_version: '1.7.0',
  },
  nodes: [mockNode],
  edges: [],
  summary: {
    total_resources: 1,
    findings: { critical: 0, high: 0, medium: 0, info: 0 },
    estimated_monthly_cost: 0,
    score: 100,
    drift: { added: 0, changed: 0, deleted: 0 },
  },
  network_paths: [],
  dc_sites: [],
};

describe('Store', () => {
  beforeEach(() => {
    useStore.setState({
      graph: null,
      selectedNode: null,
      filterPanelOpen: false,
      filters: { severities: [], resourceTypes: [], driftStatuses: [], sources: [] },
    });
  });

  it('E-009: setGraph updates graph state', () => {
    useStore.getState().setGraph(mockGraph);
    expect(useStore.getState().graph).toBe(mockGraph);
  });

  it('setSelectedNode updates selected node', () => {
    useStore.getState().setSelectedNode(mockNode);
    expect(useStore.getState().selectedNode).toBe(mockNode);
  });

  it('setSelectedNode(null) clears selection', () => {
    useStore.getState().setSelectedNode(mockNode);
    useStore.getState().setSelectedNode(null);
    expect(useStore.getState().selectedNode).toBeNull();
  });

  it('toggleFilterPanel toggles state', () => {
    expect(useStore.getState().filterPanelOpen).toBe(false);
    useStore.getState().toggleFilterPanel();
    expect(useStore.getState().filterPanelOpen).toBe(true);
    useStore.getState().toggleFilterPanel();
    expect(useStore.getState().filterPanelOpen).toBe(false);
  });

  it('E-007: toggleSeverityFilter adds and removes severity', () => {
    useStore.getState().toggleSeverityFilter('critical');
    expect(useStore.getState().filters.severities).toContain('critical');

    useStore.getState().toggleSeverityFilter('critical');
    expect(useStore.getState().filters.severities).not.toContain('critical');
  });

  it('toggleResourceTypeFilter adds and removes type', () => {
    useStore.getState().toggleResourceTypeFilter('aws_vpc');
    expect(useStore.getState().filters.resourceTypes).toContain('aws_vpc');

    useStore.getState().toggleResourceTypeFilter('aws_vpc');
    expect(useStore.getState().filters.resourceTypes).not.toContain('aws_vpc');
  });

  it('toggleDriftFilter adds and removes drift status', () => {
    useStore.getState().toggleDriftFilter('changed');
    expect(useStore.getState().filters.driftStatuses).toContain('changed');

    useStore.getState().toggleDriftFilter('changed');
    expect(useStore.getState().filters.driftStatuses).not.toContain('changed');
  });

  it('clearFilters resets all filters', () => {
    useStore.getState().toggleSeverityFilter('critical');
    useStore.getState().toggleResourceTypeFilter('aws_vpc');
    useStore.getState().toggleDriftFilter('changed');
    useStore.getState().clearFilters();

    const { filters } = useStore.getState();
    expect(filters.severities).toHaveLength(0);
    expect(filters.resourceTypes).toHaveLength(0);
    expect(filters.driftStatuses).toHaveLength(0);
  });

  it('multiple severity filters accumulate', () => {
    useStore.getState().toggleSeverityFilter('critical');
    useStore.getState().toggleSeverityFilter('high');
    expect(useStore.getState().filters.severities).toEqual(['critical', 'high']);
  });
});

describe('FlowMap store slices (Plan 03-06)', () => {
  beforeEach(() => {
    useStore.setState({
      activeTab: 'canvas',
      flowMapFilters: { severities: [], cloud: 'both', nodeTypes: [], hasFlowLogs: false },
      selectedPath: null,
      filters: { severities: [], resourceTypes: [], driftStatuses: [], sources: [] },
    });
  });

  it('activeTab default is canvas', () => {
    expect(useStore.getState().activeTab).toBe('canvas');
  });

  it('setActiveTab flips to flowmap', () => {
    useStore.getState().setActiveTab('flowmap');
    expect(useStore.getState().activeTab).toBe('flowmap');
  });

  it('switching tabs preserves existing canvas filters', () => {
    useStore.getState().toggleSeverityFilter('critical');
    useStore.getState().setActiveTab('flowmap');
    useStore.getState().setActiveTab('canvas');
    expect(useStore.getState().filters.severities).toContain('critical');
  });

  it('switching tabs preserves flowMapFilters', () => {
    useStore.getState().toggleFlowMapSeverity('high');
    useStore.getState().setActiveTab('canvas');
    useStore.getState().setActiveTab('flowmap');
    expect(useStore.getState().flowMapFilters.severities).toContain('high');
  });

  it('toggleFlowMapSeverity adds and removes', () => {
    useStore.getState().toggleFlowMapSeverity('high');
    expect(useStore.getState().flowMapFilters.severities).toEqual(['high']);
    useStore.getState().toggleFlowMapSeverity('high');
    expect(useStore.getState().flowMapFilters.severities).toEqual([]);
  });

  it('setFlowMapCloud is mutually exclusive', () => {
    useStore.getState().setFlowMapCloud('aws');
    expect(useStore.getState().flowMapFilters.cloud).toBe('aws');
    useStore.getState().setFlowMapCloud('azure');
    expect(useStore.getState().flowMapFilters.cloud).toBe('azure');
    useStore.getState().setFlowMapCloud('both');
    expect(useStore.getState().flowMapFilters.cloud).toBe('both');
  });

  it('toggleFlowMapNodeType adds and removes', () => {
    useStore.getState().toggleFlowMapNodeType('aws_ec2_transit_gateway');
    expect(useStore.getState().flowMapFilters.nodeTypes).toContain('aws_ec2_transit_gateway');
    useStore.getState().toggleFlowMapNodeType('aws_ec2_transit_gateway');
    expect(useStore.getState().flowMapFilters.nodeTypes).not.toContain('aws_ec2_transit_gateway');
  });

  it('toggleFlowMapFlowLogs flips boolean', () => {
    expect(useStore.getState().flowMapFilters.hasFlowLogs).toBe(false);
    useStore.getState().toggleFlowMapFlowLogs();
    expect(useStore.getState().flowMapFilters.hasFlowLogs).toBe(true);
    useStore.getState().toggleFlowMapFlowLogs();
    expect(useStore.getState().flowMapFilters.hasFlowLogs).toBe(false);
  });

  it('clearFlowMapFilters resets all flowMap filters', () => {
    useStore.getState().toggleFlowMapSeverity('critical');
    useStore.getState().setFlowMapCloud('aws');
    useStore.getState().toggleFlowMapNodeType('aws_vpc');
    useStore.getState().toggleFlowMapFlowLogs();
    useStore.getState().clearFlowMapFilters();
    const f = useStore.getState().flowMapFilters;
    expect(f.severities).toEqual([]);
    expect(f.cloud).toBe('both');
    expect(f.nodeTypes).toEqual([]);
    expect(f.hasFlowLogs).toBe(false);
  });

  it('setSelectedPath round-trip', () => {
    const p = {
      id: 'p1',
      source_node_id: 'a',
      dest_node_id: 'b',
      direction: 'forward' as const,
      hops: [],
      evidence: {},
    };
    useStore.getState().setSelectedPath(p);
    expect(useStore.getState().selectedPath?.id).toBe('p1');
    useStore.getState().setSelectedPath(null);
    expect(useStore.getState().selectedPath).toBeNull();
  });

  it('clearFlowMapFilters does not touch canvas filters', () => {
    useStore.getState().toggleSeverityFilter('critical');
    useStore.getState().toggleFlowMapSeverity('high');
    useStore.getState().clearFlowMapFilters();
    expect(useStore.getState().filters.severities).toContain('critical');
    expect(useStore.getState().flowMapFilters.severities).toEqual([]);
  });
});

describe('useViewerStoreOrSingleton — dual-mode hook (regression for empty-canvas bug)', () => {
  beforeEach(() => {
    useStore.setState({ graph: null });
  });

  it('reads from module singleton when no ViewerProvider is mounted (standalone HTML viewer path)', () => {
    useStore.getState().setGraph(mockGraph);
    const { result } = renderHook(() => useViewerStoreOrSingleton((s) => s.graph));
    expect(result.current).toBe(mockGraph);
  });

  it('reads from context-bound factory store when wrapped in ViewerProvider (dashboard path)', () => {
    // Singleton stays empty; factory store gets the graph. This is exactly
    // the production scenario in ScanViewerClient — without the fix, the
    // hook would fall through to the empty singleton and the canvas blanks.
    const factoryStore = createViewerStore();
    factoryStore.getState().setGraph(mockGraph);

    const wrapper = ({ children }: { children: ReactNode }) =>
      createElement(ViewerProvider, { store: factoryStore }, children);

    const { result } = renderHook(() => useViewerStoreOrSingleton((s) => s.graph), { wrapper });
    expect(result.current).toBe(mockGraph);
    // Singleton untouched — proves per-page isolation is preserved.
    expect(useStore.getState().graph).toBeNull();
  });
});
