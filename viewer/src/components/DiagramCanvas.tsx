import { useCallback, useEffect, useMemo } from 'react';
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
  type NodeMouseHandler,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { ResourceNodeMemo } from './ResourceNode';
import { GroupNodeMemo } from './GroupNode';
import { buildFlowElements } from '../lib/layout';
import { useStore, useViewerStoreOrSingleton } from '../store';
import type { ResourceNode } from '../types';

const nodeTypes: NodeTypes = {
  resource: ResourceNodeMemo,
  group: GroupNodeMemo,
};

export function DiagramCanvas() {
  const graph = useViewerStoreOrSingleton(s => s.graph);
  const filters = useViewerStoreOrSingleton(s => s.filters);
  const searchQuery = useViewerStoreOrSingleton(s => s.searchQuery);
  const setSelectedNode = useViewerStoreOrSingleton(s => s.setSelectedNode);
  const { fitView } = useReactFlow();

  const { initialNodes, initialEdges } = useMemo(() => {
    if (!graph) return { initialNodes: [], initialEdges: [] };
    const { nodes, edges } = buildFlowElements(graph);
    return { initialNodes: nodes, initialEdges: edges };
  }, [graph]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Recompute when graph changes
  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
    setTimeout(() => fitView({ padding: 0.15, duration: 300 }), 100);
  }, [initialNodes, initialEdges, setNodes, setEdges, fitView]);

  // Apply filters and search query (dim non-matching nodes)
  useEffect(() => {
    const query = searchQuery.toLowerCase().trim();
    setNodes(nds =>
      nds.map(node => {
        if (node.type !== 'resource') return node;
        const data = node.data as unknown as ResourceNode;
        const visible = isNodeVisible(data, filters);
        const matchesSearch = query === '' ||
          data.name.toLowerCase().includes(query) ||
          data.type.toLowerCase().includes(query);
        return {
          ...node,
          style: {
            ...node.style,
            opacity: visible && matchesSearch ? 1 : 0.2,
            transition: 'opacity 0.2s',
          },
        };
      })
    );
  }, [filters, searchQuery, setNodes]);

  const onNodeClick: NodeMouseHandler = useCallback((_event, node) => {
    if (node.type === 'resource') {
      setSelectedNode(node.data as unknown as ResourceNode);
    }
  }, [setSelectedNode]);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, [setSelectedNode]);

  const handleFitView = useCallback(() => {
    fitView({ padding: 0.15, duration: 300 });
  }, [fitView]);

  return (
    <div className="w-full h-full relative" style={{ background: '#FAFBFC' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        defaultEdgeOptions={{
          type: 'smoothstep',
        }}
        connectionLineStyle={{ stroke: '#94A3B8', strokeWidth: 1 }}
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
          nodeColor={(node) => {
            if (node.type === 'group') return 'rgba(148,163,184,0.2)';
            return '#CBD5E1';
          }}
          maskColor="rgba(255,255,255,0.6)"
          pannable
          zoomable
        />
      </ReactFlow>

      {/* Fit view + reset button overlay */}
      <div className="absolute bottom-3 left-14 flex gap-1.5 z-10">
        <button
          onClick={handleFitView}
          className="text-xs px-2 py-1 rounded cursor-pointer"
          style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', color: '#475569' }}
        >
          Fit View
        </button>
      </div>
    </div>
  );
}

function isNodeVisible(
  node: ResourceNode,
  filters: ReturnType<typeof useStore.getState>['filters']
): boolean {
  // Severity filter
  if (filters.severities.length > 0) {
    const nodeHasMatchingSev = node.findings.some(f =>
      filters.severities.includes(f.severity)
    );
    if (!nodeHasMatchingSev && node.findings.length > 0) return false;
    if (node.findings.length === 0 && !filters.severities.includes('clean' as never)) return false;
  }

  // Resource type filter
  if (filters.resourceTypes.length > 0 && !filters.resourceTypes.includes(node.type)) {
    return false;
  }

  // Drift filter
  if (filters.driftStatuses.length > 0 && !filters.driftStatuses.includes(node.drift)) {
    return false;
  }

  return true;
}
