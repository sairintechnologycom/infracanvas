import { describe, test, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { PathDetailPanel } from '../../components/flowmap/PathDetailPanel';
import { useStore } from '../../store';
import type { ResourceNode } from '../../types';

function _node(overrides: Partial<ResourceNode> = {}): ResourceNode {
  return {
    id: 'aws_ec2_transit_gateway.hybrid',
    type: 'aws_ec2_transit_gateway',
    name: 'hybrid',
    provider: 'aws',
    module: '',
    region: 'us-east-1',
    group: '',
    attributes: {},
    dependencies: [],
    findings: [],
    cost: { monthly_usd: 0, currency: 'USD', basis: '' },
    drift: 'unchanged',
    position: { x: 0, y: 0 },
    ...overrides,
  };
}

describe('PathDetailPanel', () => {
  beforeEach(() => {
    useStore.setState({ selectedNode: null });
  });

  test('nothing-selected mode renders Select a node', () => {
    render(<PathDetailPanel />);
    expect(screen.getByText('Select a node')).toBeInTheDocument();
  });

  test('node-selected renders name + id', () => {
    useStore.setState({ selectedNode: _node() });
    render(<PathDetailPanel />);
    expect(screen.getByText('hybrid')).toBeInTheDocument();
    expect(screen.getByText('aws_ec2_transit_gateway.hybrid')).toBeInTheDocument();
  });

  test('Routes tab appears for TGW route table', () => {
    useStore.setState({
      selectedNode: _node({
        type: 'aws_ec2_transit_gateway_route_table',
        attributes: {
          routes: [{ DestinationCidrBlock: '10.0.0.0/16', Type: 'propagated', State: 'active' }],
        },
      }),
    });
    render(<PathDetailPanel />);
    expect(screen.getByText(/Routes/i)).toBeInTheDocument();
  });

  test('Routes tab empty state shows no-routes message', () => {
    useStore.setState({
      selectedNode: _node({ type: 'aws_ec2_transit_gateway_route_table', attributes: {} }),
    });
    render(<PathDetailPanel />);
    fireEvent.click(screen.getByText(/Routes/i));
    expect(screen.getByText('No routes collected for this node.')).toBeInTheDocument();
  });

  test('close button clears selection', () => {
    useStore.setState({ selectedNode: _node() });
    render(<PathDetailPanel />);
    fireEvent.click(screen.getByLabelText('Close details'));
    expect(useStore.getState().selectedNode).toBeNull();
  });

  // CPC-03: Cost tab tests

  test('PDP-COST-01: Cost tab absent when monthly_usd is 0', () => {
    useStore.setState({
      selectedNode: _node({ cost: { monthly_usd: 0, currency: 'USD', basis: '' } }),
    });
    render(<PathDetailPanel />);
    expect(screen.queryByRole('button', { name: /Cost/i })).toBeNull();
  });

  test('PDP-COST-02: Cost tab appears when monthly_usd > 0', () => {
    useStore.setState({
      selectedNode: _node({ cost: { monthly_usd: 42.5, currency: 'USD', basis: 'AWS egress rate' } }),
    });
    render(<PathDetailPanel />);
    expect(screen.getByRole('button', { name: /Cost/i })).toBeInTheDocument();
  });

  test('PDP-COST-03: Cost tab shows monthly cost and basis on click', () => {
    useStore.setState({
      selectedNode: _node({ cost: { monthly_usd: 42.5, currency: 'USD', basis: 'AWS egress rate' } }),
    });
    render(<PathDetailPanel />);
    fireEvent.click(screen.getByRole('button', { name: /Cost/i }));
    expect(screen.getByText('$42.50')).toBeInTheDocument();
    expect(screen.getByText('AWS egress rate')).toBeInTheDocument();
  });

  test('PDP-COST-04: disclaimer shown when basis contains "no flow data"', () => {
    useStore.setState({
      selectedNode: _node({
        cost: {
          monthly_usd: 18.0,
          currency: 'USD',
          basis: 'assumed 100 GB/mo — no flow data available',
        },
      }),
    });
    render(<PathDetailPanel />);
    fireEvent.click(screen.getByRole('button', { name: /Cost/i }));
    expect(
      screen.getByText(/Estimate based on assumed transfer volume/i)
    ).toBeInTheDocument();
  });

  test('PDP-COST-05: no disclaimer when basis does not contain "no flow data"', () => {
    useStore.setState({
      selectedNode: _node({
        cost: { monthly_usd: 12.0, currency: 'USD', basis: 'AWS us-east-1 egress 0.09/GB' },
      }),
    });
    render(<PathDetailPanel />);
    fireEvent.click(screen.getByRole('button', { name: /Cost/i }));
    expect(
      screen.queryByText(/Estimate based on assumed transfer volume/i)
    ).toBeNull();
  });
});
