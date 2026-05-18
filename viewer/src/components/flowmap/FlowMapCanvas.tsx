import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
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
import { FlowMapEmptyState } from './FlowMapEmptyState'
import { fetchAsymmetries } from '../../lib/asymmetryFetcher'
import { useViewerStoreOrSingleton } from '../../store'
import type { AsymmetryPayload, NetworkPath, ResourceNode } from '../../types'

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
  return useViewerStoreOrSingleton((s) => {
    const anyS = s as unknown as { flowMapFilters?: FlowMapFilters }
    return anyS.flowMapFilters ?? DEFAULT_FLOWMAP_FILTERS
  })
}

// Narrow selector — returns the 03-06 setSelectedPath action or a no-op.
function useSetSelectedPath(): (p: NetworkPath | null) => void {
  return useViewerStoreOrSingleton((s) => {
    const anyS = s as unknown as { setSelectedPath?: (p: NetworkPath | null) => void }
    return anyS.setSelectedPath ?? (() => undefined)
  })
}

// Phase 12 FMV-02 — narrow selector for the setAsymmetries action. Returns a
// no-op when the host store predates Plan 12-07 (defensive forward-compat).
function useSetAsymmetries(): (payloads: AsymmetryPayload[]) => void {
  return useViewerStoreOrSingleton((s) => {
    const anyS = s as unknown as { setAsymmetries?: (p: AsymmetryPayload[]) => void }
    return anyS.setAsymmetries ?? (() => undefined)
  })
}

// Phase 12 FMV-02 — best-effort site_id resolver. The CLI HTML bundle injects
// the entire ResourceGraph onto window.__INFRACANVAS_DATA__; the SaaS dashboard
// path may attach a site_id to graph.metadata (when the scan is bound to a DC
// site). Both shapes are tolerated; null is the offline fallback (asymmetry
// fetch is then a no-op).
function resolveSiteId(graph: unknown): string | null {
  if (!graph || typeof graph !== 'object') return null
  const g = graph as { metadata?: { site_id?: unknown }; site_id?: unknown }
  const fromMeta = g.metadata?.site_id
  if (typeof fromMeta === 'string' && fromMeta.length > 0) return fromMeta
  const direct = g.site_id
  if (typeof direct === 'string' && direct.length > 0) return direct
  return null
}

export function FlowMapCanvas() {
  const graph = useViewerStoreOrSingleton((s) => s.graph)
  const setSelectedNode = useViewerStoreOrSingleton((s) => s.setSelectedNode)
  const flowMapFilters = useFlowMapFilters()
  const setSelectedPath = useSetSelectedPath()
  const setAsymmetries = useSetAsymmetries()
  const selectedPath = useViewerStoreOrSingleton((s) => s.selectedPath)
  const { fitView } = useReactFlow()

  // Phase 12 FMV-02 — Blocker 3 closure. Fetch asymmetry findings from the
  // backend (via the dashboard-injected window.__INFRACANVAS_BACKEND_FETCH__)
  // and dispatch them to the store so selectedPath.asymmetry populates before
  // the user inspects PathEdge / PathDetailPanel. On offline / standalone
  // bundles the fetcher returns [] and this is a no-op.
  const lastFetchedSiteIdRef = useRef<string | null>(null)
  const selectedPathId = selectedPath?.id ?? null
  useEffect(() => {
    const siteId = resolveSiteId(graph)
    if (!siteId) return
    // Re-fetch when the site changes OR when the user picks a new path
    // (so a freshly-selected path is hydrated even after the initial fetch).
    if (lastFetchedSiteIdRef.current === siteId && !selectedPathId) return
    lastFetchedSiteIdRef.current = siteId
    let cancelled = false
    fetchAsymmetries(siteId).then((payloads) => {
      if (cancelled) return
      setAsymmetries(payloads)
    })
    return () => {
      cancelled = true
    }
  }, [graph, selectedPathId, setAsymmetries])

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

  // Empty-state handoff (D-08): when cloud-topology-empty, render
  // Plan 03-08's FlowMapEmptyState in-slot so the 3-column shell stays intact.
  if (isEmpty) return <FlowMapEmptyState />


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
