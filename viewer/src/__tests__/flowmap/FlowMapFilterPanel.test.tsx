import { describe, test, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { FlowMapFilterPanel } from '../../components/flowmap/FlowMapFilterPanel';
import { useStore } from '../../store';
import type { ResourceGraph } from '../../types';

const _graph = (): ResourceGraph => ({
  version: '2.1',
  metadata: { scan_id: '', project: '', provider: '', scanned_at: '', terraform_version: '' },
  nodes: [
    {
      id: 'aws_ec2_transit_gateway.a',
      type: 'aws_ec2_transit_gateway',
      name: 'a',
      provider: 'aws',
      module: '',
      region: 'us-east-1',
      group: '',
      attributes: {},
      dependencies: [],
      findings: [
        {
          rule_id: 'NET-001',
          severity: 'high',
          title: '',
          description: '',
          remediation: '',
          evidence: {},
          source: 'security',
        },
      ],
      cost: { monthly_usd: 0, currency: 'USD', basis: '' },
      drift: 'unchanged',
      position: { x: 0, y: 0 },
    },
  ],
  edges: [],
  summary: {
    total_resources: 1,
    findings: { critical: 0, high: 1, medium: 0, info: 0 },
    estimated_monthly_cost: 0,
    score: 0,
    drift: { added: 0, changed: 0, deleted: 0 },
  },
  network_paths: [],
  dc_sites: [],
});

describe('FlowMapFilterPanel', () => {
  beforeEach(() => {
    useStore.setState({
      graph: _graph(),
      filterPanelOpen: true,
      flowMapFilters: { severities: [], cloud: 'both', nodeTypes: [], hasFlowLogs: false },
    });
  });

  test('renders when filterPanelOpen true and graph present', () => {
    render(<FlowMapFilterPanel />);
    expect(screen.getByText('Filters')).toBeInTheDocument();
    expect(screen.getByText('Severity')).toBeInTheDocument();
    expect(screen.getByText('Cloud')).toBeInTheDocument();
    expect(screen.getByText('Node Type')).toBeInTheDocument();
  });

  test('returns null when filterPanelOpen false', () => {
    useStore.setState({ filterPanelOpen: false });
    const { container } = render(<FlowMapFilterPanel />);
    expect(container.firstChild).toBeNull();
  });

  test('clicking AWS cloud pill sets filters.cloud', () => {
    render(<FlowMapFilterPanel />);
    fireEvent.click(screen.getByRole('button', { name: 'AWS' }));
    expect(useStore.getState().flowMapFilters.cloud).toBe('aws');
  });

  test('toggling severity flips store state', () => {
    render(<FlowMapFilterPanel />);
    const high = screen.getByLabelText(/high/i);
    fireEvent.click(high);
    expect(useStore.getState().flowMapFilters.severities).toContain('high');
  });

  test('clear button resets filters', () => {
    useStore.setState({
      flowMapFilters: { severities: ['critical'], cloud: 'aws', nodeTypes: [], hasFlowLogs: true },
    });
    render(<FlowMapFilterPanel />);
    fireEvent.click(screen.getByText('Clear'));
    const f = useStore.getState().flowMapFilters;
    expect(f.severities).toEqual([]);
    expect(f.cloud).toBe('both');
    expect(f.hasFlowLogs).toBe(false);
  });
});
