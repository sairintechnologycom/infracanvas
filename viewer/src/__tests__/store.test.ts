import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';
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
