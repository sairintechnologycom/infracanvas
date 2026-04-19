import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  useReactFlow,
  BackgroundVariant,
  type NodeTypes,
  type EdgeTypes,
  type Node as RFNode,
  type Edge as RFEdge,
  type NodeMouseHandler,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import { CloudHubNodeMemo } from './nodes/CloudHubNode'
import { RouterNodeMemo } from './nodes/RouterNode'
import { FirewallNodeMemo } from './nodes/FirewallNode'
import { DCSiteGroupNodeMemo } from './nodes/DCSiteGroupNode'
import { PathEdge, pathEdgeMarkerDefs } from './edges/PathEdge'
import { layoutFlowMap } from './lib/elkLayout'
import { useStore } from '../../store'
import type { NetworkPath, ResourceNode } from '../../types'

// Set of resource types that belong on the FlowMap — cloud network-layer
// primitives collected by Plans 03-03 (AWS) + 03-04 (Azure). Exported so
// Plan 03-08's FlowMapFilterPanel can reuse the same list for its
// "Node Type" checkbox facet (SUMMARY Next Phase Readiness).
export const NETWORK_TYPES: ReadonlySet<string> = new Set([
  // AWS
  'aws_ec2_transit_gateway',
  'aws_ec2_transit_gateway_attachment',
  'aws_ec2_transit_gateway_route_table',
  'aws_vpn_connection',
  'aws_route_table',
  'aws_network_acl',
  'aws_dx_connection',
  'aws_dx_virtual_interface',
  // Azure
  'azurerm_virtual_wan',
  'azurerm_virtual_hub',
  'azurerm_virtual_hub_connection',
  'azurerm_virtual_network',
  'azurerm_virtual_network_peering',
  'azurerm_network_security_group',
  'azurerm_express_route_circuit',
  'azurerm_express_route_circuit_peering',
])

const nodeTypes: NodeTypes = {
  cloudHub: CloudHubNodeMemo,
  router: RouterNodeMemo,
  firewall: FirewallNodeMemo,
  dcSiteGroup: DCSiteGroupNodeMemo,
}

const edgeTypes: EdgeTypes = { path: PathEdge }

// Store-slice shape added by Plan 03-06 (wave-2 sibling). We read these via
// bracket access so FlowMapCanvas compiles in this worktree even before the
// store extension merges; once Plan 03-06 lands, the runtime shape matches
// exactly and the cast is a no-op.
interface FlowMapFilters {
  severities: string[]
  cloud: 'aws' | 'azure' | 'both'
  nodeTypes: string[]
  hasFlowLogs: boolean
}

const DEFAULT_FLOWMAP_FILTERS: FlowMapFilters = {
  severities: [],
  cloud: 'both',
  nodeTypes: [],
  hasFlowLogs: false,
}

// Narrow selector helper — returns the 03-06 flowMapFilters slice or defaults.
function useFlowMapFilters(): FlowMapFilters {
  return useStore((s) => {
    const anyS = s as unknown as { flowMapFilters?: FlowMapFilters }
    return anyS.flowMapFilters ?? DEFAULT_FLOWMAP_FILTERS
  })
}

// Narrow selector — returns the 03-06 setSelectedPath action or a no-op.
function useSetSelectedPath(): (p: NetworkPath | null) => void {
  return useStore((s) => {
    const anyS = s as unknown as { setSelectedPath?: (p: NetworkPath | null) => void }
    return anyS.setSelectedPath ?? (() => undefined)
  })
}

export function FlowMapCanvas() {
  const graph = useStore((s) => s.graph)
  const setSelectedNode = useStore((s) => s.setSelectedNode)
  const flowMapFilters = useFlowMapFilters()
  const setSelectedPath = useSetSelectedPath()
  const { fitView } = useReactFlow()

  const networkNodes = useMemo(() => {
    if (!graph) return []
    return graph.nodes.filter((n) => NETWORK_TYPES.has(n.type))
  }, [graph])

  const networkPathCount = graph?.network_paths?.length ?? 0
  const isEmpty = networkNodes.length === 0 && networkPathCount === 0

  const [nodes, setNodes, onNodesChange] = useNodesState<RFNode>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<RFEdge>([])
  const [layoutPending, setLayoutPending] = useState(false)

  // Compute layout on graph change (async — elkjs resolves in microtask queue).
  useEffect(() => {
    if (!graph || isEmpty) {
      setNodes([])
      setEdges([])
      return
    }
    let cancelled = false
    setLayoutPending(true)
    layoutFlowMap(graph, networkNodes)
      .then((result) => {
        if (cancelled) return
        // Append a DC-site placeholder group node to the right of the cloud
        // topology. In 3a this is always the Phase-3b-upgrade pill.
        const lastX = result.nodes.length > 0
          ? Math.max(...result.nodes.map((n) => n.position.x))
          : 0
        const placeholder: RFNode = {
          id: 'dc-site-placeholder',
          type: 'dcSiteGroup',
          position: { x: lastX + 280, y: 0 },
          data: { label: 'On-Prem Data Centre', hasSites: false },
          draggable: false,
          selectable: false,
        }
        setNodes([...result.nodes, placeholder])
        setEdges(result.edges)
        setTimeout(() => fitView({ padding: 0.15, duration: 300 }), 100)
      })
      .catch(() => {
        if (!cancelled) {
          setNodes([])
          setEdges([])
        }
      })
      .finally(() => {
        if (!cancelled) setLayoutPending(false)
      })
    return () => {
      cancelled = true
    }
  }, [graph, networkNodes, isEmpty, setNodes, setEdges, fitView])

  // Filter dimming — dim nodes that fail the current flowMapFilters predicate.
  useEffect(() => {
    setNodes((nds) =>
      nds.map((node) => {
        if (node.type === 'dcSiteGroup') return node
        const data = node.data as unknown as ResourceNode | undefined
        if (!data) return node

        let visible = true

        if (flowMapFilters.cloud === 'aws' && data.provider !== 'aws') visible = false
        if (flowMapFilters.cloud === 'azure' && data.provider !== 'azure') visible = false

        if (flowMapFilters.nodeTypes.length > 0 && !flowMapFilters.nodeTypes.includes(data.type)) {
          visible = false
        }

        if (flowMapFilters.severities.length > 0) {
          const nodeSevs = new Set(data.findings.map((f) => f.severity as string))
          if (!flowMapFilters.severities.some((s) => nodeSevs.has(s))) visible = false
        }

        if (flowMapFilters.hasFlowLogs && !data.attributes.flow_log) visible = false

        return {
          ...node,
          style: { ...node.style, opacity: visible ? 1 : 0.2, transition: 'opacity 0.2s' },
        }
      }),
    )
  }, [flowMapFilters, setNodes])

  const onNodeClick: NodeMouseHandler = useCallback(
    (_event, node) => {
      if (node.type === 'dcSiteGroup') return
      if (node.data) setSelectedNode(node.data as unknown as ResourceNode)
    },
    [setSelectedNode],
  )

  const onPaneClick = useCallback(() => {
    setSelectedNode(null)
    setSelectedPath(null)
  }, [setSelectedNode, setSelectedPath])

  // Escape clears both selectedNode and selectedPath (UI-SPEC Interaction Contracts).
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setSelectedNode(null)
        setSelectedPath(null)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [setSelectedNode, setSelectedPath])

  // Empty-state handoff — return null so App.tsx 3-column shell reveals
  // Plan 03-08's FlowMapEmptyState in the empty slot.
  if (isEmpty) return null

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative', background: '#FAFBFC' }}>
      {/* Hidden SVG <defs> so PathEdge markerStart/markerEnd url() refs resolve */}
      <svg width={0} height={0} style={{ position: 'absolute' }} aria-hidden="true">
        {pathEdgeMarkerDefs}
      </svg>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        defaultEdgeOptions={{ type: 'smoothstep' }}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        minZoom={0.2}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1.2} color="#DDE2E8" />
        <Controls position="bottom-left" showInteractive={false} />
        <MiniMap
          position="bottom-right"
          nodeColor={(n) => {
            const data = n.data as unknown as ResourceNode | undefined
            if (!data) return '#CBD5E1'
            if (data.provider === 'aws') return '#FF9900'
            if (data.provider === 'azure') return '#0078D4'
            return '#64748B'
          }}
          maskColor="rgba(255,255,255,0.6)"
          pannable
          zoomable
        />
      </ReactFlow>
      {layoutPending && (
        <div
          style={{
            position: 'absolute',
            top: 12,
            left: 12,
            fontSize: 11,
            color: '#64748B',
            background: '#FFFFFF',
            padding: '4px 8px',
            borderRadius: 4,
            border: '1px solid #E2E8F0',
          }}
        >
          Computing layout…
        </div>
      )}
    </div>
  )
}

export default FlowMapCanvas
