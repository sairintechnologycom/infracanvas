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
});
