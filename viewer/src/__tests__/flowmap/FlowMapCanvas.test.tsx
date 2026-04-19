import { describe, test, expect, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import { ReactFlowProvider } from '@xyflow/react'
import { FlowMapCanvas, NETWORK_TYPES } from '../../components/flowmap/FlowMapCanvas'
import { useStore } from '../../store'
import type { ResourceGraph, ResourceNode } from '../../types'

function emptyGraph(): ResourceGraph {
  return {
    version: '2.1',
    metadata: {
      scan_id: '',
      project: '',
      provider: '',
      scanned_at: '',
      terraform_version: '',
    },
    nodes: [],
    edges: [],
    summary: {
      total_resources: 0,
      findings: { critical: 0, high: 0, medium: 0, info: 0 },
      estimated_monthly_cost: 0,
      score: 0,
      drift: { added: 0, changed: 0, deleted: 0 },
    },
    network_paths: [],
    dc_sites: [],
  }
}

function makeNode(id: string, type: string): ResourceNode {
  return {
    id,
    type,
    name: id.split('.').pop() ?? id,
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
  }
}

function renderCanvas() {
  return render(
    <ReactFlowProvider>
      <FlowMapCanvas />
    </ReactFlowProvider>,
  )
}

describe('FlowMapCanvas', () => {
  beforeEach(() => {
    useStore.setState({ graph: null, selectedNode: null })
  })

  test('NETWORK_TYPES export is a non-empty set', () => {
    expect(NETWORK_TYPES).toBeInstanceOf(Set)
    expect(NETWORK_TYPES.size).toBeGreaterThan(0)
    expect(NETWORK_TYPES.has('aws_ec2_transit_gateway')).toBe(true)
    expect(NETWORK_TYPES.has('azurerm_virtual_hub')).toBe(true)
  })

  test('NETWORK_TYPES excludes non-network resources', () => {
    expect(NETWORK_TYPES.has('aws_instance')).toBe(false)
    expect(NETWORK_TYPES.has('aws_s3_bucket')).toBe(false)
  })

  test('renders FlowMapEmptyState when graph is null (D-08 empty-state handoff)', () => {
    const { getByText } = renderCanvas()
    // FlowMapEmptyState renders the "Beta" preview pill + CLI command copy
    expect(getByText(/beta/i)).toBeInTheDocument()
  })

  test('renders FlowMapEmptyState when graph has no network nodes and empty network_paths', () => {
    const g = emptyGraph()
    g.nodes = [makeNode('aws_instance.web', 'aws_instance')]
    g.summary.total_resources = 1
    useStore.setState({ graph: g })
    const { getByText } = renderCanvas()
    expect(getByText(/beta/i)).toBeInTheDocument()
  })

  test('renders non-null wrapper when a TGW node is present', () => {
    const g = emptyGraph()
    g.nodes = [makeNode('aws_ec2_transit_gateway.hybrid', 'aws_ec2_transit_gateway')]
    g.summary.total_resources = 1
    useStore.setState({ graph: g })
    const { container } = renderCanvas()
    // Non-empty — the top-level wrapper div renders immediately; elkjs
    // layout resolves asynchronously, but the wrapper itself is synchronous.
    expect(container.firstChild).not.toBeNull()
  })
})
