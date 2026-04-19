import { describe, test, expect } from 'vitest'
import { layoutFlowMap, pickReactFlowNodeType } from '../../components/flowmap/lib/elkLayout'
import type { ResourceGraph, ResourceNode } from '../../types'

function emptyGraph(): ResourceGraph {
  return {
    version: '2.1',
    metadata: {
      scan_id: 's1',
      project: 'test',
      provider: 'aws',
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

function makeNode(id: string, type: string, provider = 'aws'): ResourceNode {
  return {
    id,
    type,
    name: id.split('.').pop() ?? id,
    provider,
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

describe('pickReactFlowNodeType', () => {
  test('AWS TGW -> cloudHub', () => {
    expect(pickReactFlowNodeType('aws_ec2_transit_gateway')).toBe('cloudHub')
  })

  test('Azure virtual hub -> cloudHub', () => {
    expect(pickReactFlowNodeType('azurerm_virtual_hub')).toBe('cloudHub')
  })

  test('Azure virtual WAN -> cloudHub', () => {
    expect(pickReactFlowNodeType('azurerm_virtual_wan')).toBe('cloudHub')
  })

  test('aws_network_firewall -> firewall', () => {
    expect(pickReactFlowNodeType('aws_network_firewall')).toBe('firewall')
  })

  test('azurerm_firewall -> firewall', () => {
    expect(pickReactFlowNodeType('azurerm_firewall')).toBe('firewall')
  })

  test('unknown cloud resource falls back to cloudHub', () => {
    expect(pickReactFlowNodeType('aws_route_table')).toBe('cloudHub')
    expect(pickReactFlowNodeType('azurerm_virtual_network_peering')).toBe('cloudHub')
  })
})

describe('layoutFlowMap', () => {
  test('empty network nodes -> empty result', async () => {
    const g = emptyGraph()
    const result = await layoutFlowMap(g, [])
    expect(result.nodes).toEqual([])
    expect(result.edges).toEqual([])
  })

  test('three TGWs + two edges -> three positioned nodes + two edges', async () => {
    const g = emptyGraph()
    const nodes = [
      makeNode('aws_ec2_transit_gateway.a', 'aws_ec2_transit_gateway'),
      makeNode('aws_ec2_transit_gateway.b', 'aws_ec2_transit_gateway'),
      makeNode('aws_ec2_transit_gateway.c', 'aws_ec2_transit_gateway'),
    ]
    g.nodes = nodes
    g.edges = [
      {
        source: 'aws_ec2_transit_gateway.a',
        target: 'aws_ec2_transit_gateway.b',
        type: 'implicit',
      },
      {
        source: 'aws_ec2_transit_gateway.b',
        target: 'aws_ec2_transit_gateway.c',
        type: 'implicit',
      },
    ]
    const result = await layoutFlowMap(g, nodes)
    expect(result.nodes).toHaveLength(3)
    expect(result.edges).toHaveLength(2)
    for (const n of result.nodes) {
      expect(typeof n.position.x).toBe('number')
      expect(typeof n.position.y).toBe('number')
      expect(n.type).toBe('cloudHub')
    }
    for (const e of result.edges) {
      expect(e.type).toBe('path')
      expect((e.data as { direction?: string } | undefined)?.direction).toBe('both')
    }
  })

  test('edges to nodes outside network set are filtered out', async () => {
    const g = emptyGraph()
    const tgw = makeNode('aws_ec2_transit_gateway.hub', 'aws_ec2_transit_gateway')
    g.nodes = [tgw]
    g.edges = [
      // Edge to a non-network node (aws_instance) should NOT appear in output
      { source: 'aws_ec2_transit_gateway.hub', target: 'aws_instance.web', type: 'implicit' },
    ]
    const result = await layoutFlowMap(g, [tgw])
    expect(result.nodes).toHaveLength(1)
    expect(result.edges).toHaveLength(0)
  })

  test('mixed AWS + Azure network nodes resolve to correct ReactFlow types', async () => {
    const g = emptyGraph()
    const tgw = makeNode('aws_ec2_transit_gateway.a', 'aws_ec2_transit_gateway', 'aws')
    const vhub = makeNode('azurerm_virtual_hub.b', 'azurerm_virtual_hub', 'azure')
    const fw = makeNode('aws_network_firewall.c', 'aws_network_firewall', 'aws')
    g.nodes = [tgw, vhub, fw]
    const result = await layoutFlowMap(g, g.nodes)
    const byId = new Map(result.nodes.map((n) => [n.id, n]))
    expect(byId.get('aws_ec2_transit_gateway.a')?.type).toBe('cloudHub')
    expect(byId.get('azurerm_virtual_hub.b')?.type).toBe('cloudHub')
    expect(byId.get('aws_network_firewall.c')?.type).toBe('firewall')
  })
})
