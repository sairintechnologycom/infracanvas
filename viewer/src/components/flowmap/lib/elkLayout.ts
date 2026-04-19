import ELK from 'elkjs/lib/elk.bundled.js'
import type { Node as RFNode, Edge as RFEdge } from '@xyflow/react'
import type { ResourceGraph, ResourceNode as RNData } from '../../../types'

// Single elkjs instance per module; stateless layout calls.
const elk = new ELK()

// Node geometry for elkjs layout math. ReactFlow reads our custom-node widths
// from their own <div> style, not from elkjs — these values only affect how
// far apart the layered layout places nodes.
const NODE_W = 200
const NODE_H = 80

// Phase 3a layout options — layered left-to-right per UI-SPEC FlowMapCanvas.
// Spacing: 80px between nodes in the same layer, 120px between layers.
const ELK_OPTIONS = {
  'elk.algorithm': 'layered',
  'elk.direction': 'RIGHT',
  'elk.spacing.nodeNode': '80',
  'elk.layered.spacing.nodeNodeBetweenLayers': '120',
} as const

/**
 * Map a raw ResourceNode.type string to a ReactFlow custom-node type key.
 * Fallback: anything that is not explicitly recognised renders as a cloudHub
 * card. This is intentional for 3a — the primary network actors are TGW +
 * vWAN hubs; incidental network resources (NACLs, peerings) inherit the
 * same card treatment. Plan 3b may refine.
 */
export function pickReactFlowNodeType(type: string): string {
  if (
    type === 'aws_ec2_transit_gateway' ||
    type === 'azurerm_virtual_hub' ||
    type === 'azurerm_virtual_wan'
  ) {
    return 'cloudHub'
  }
  if (
    type.includes('firewall') ||
    type === 'aws_network_firewall' ||
    type === 'azurerm_firewall'
  ) {
    return 'firewall'
  }
  // Future-proof: any explicitly-router type lands here; not emitted in 3a.
  if (type === 'aws_router' || type === 'router') return 'router'
  if (type.startsWith('aws_') || type.startsWith('azurerm_')) return 'cloudHub'
  return 'cloudHub'
}

/**
 * Compute a layered left-to-right layout for the FlowMap network nodes.
 * Returns ReactFlow-shaped `{nodes, edges}` with positions populated by elkjs.
 */
export async function layoutFlowMap(
  graph: ResourceGraph,
  networkNodes: RNData[],
): Promise<{ nodes: RFNode[]; edges: RFEdge[] }> {
  if (networkNodes.length === 0) {
    return { nodes: [], edges: [] }
  }

  const idSet = new Set(networkNodes.map((n) => n.id))

  const elkGraph = {
    id: 'root',
    layoutOptions: ELK_OPTIONS,
    children: networkNodes.map((n) => ({ id: n.id, width: NODE_W, height: NODE_H })),
    edges: graph.edges
      .filter((e) => idSet.has(e.source) && idSet.has(e.target))
      .map((e, i) => ({
        id: `${e.source}->${e.target}-${i}`,
        sources: [e.source],
        targets: [e.target],
      })),
  }

  const layouted = await elk.layout(elkGraph)

  const byId = new Map(networkNodes.map((n) => [n.id, n]))

  const rfNodes: RFNode[] = (layouted.children ?? []).map((c) => {
    const data = byId.get(c.id)
    if (!data) {
      // Defensive: elk should only return ids we gave it, but if not, emit a
      // bare node with no data rather than crashing the layout.
      return {
        id: c.id,
        type: 'cloudHub',
        position: { x: c.x ?? 0, y: c.y ?? 0 },
        data: {},
      }
    }
    return {
      id: c.id,
      type: pickReactFlowNodeType(data.type),
      position: { x: c.x ?? 0, y: c.y ?? 0 },
      data: data as unknown as Record<string, unknown>,
    }
  })

  const rfEdges: RFEdge[] = (layouted.edges ?? []).map((e) => ({
    id: e.id,
    source: (e.sources ?? [])[0] ?? '',
    target: (e.targets ?? [])[0] ?? '',
    type: 'path',
    data: { direction: 'both' as const },
  }))

  return { nodes: rfNodes, edges: rfEdges }
}
