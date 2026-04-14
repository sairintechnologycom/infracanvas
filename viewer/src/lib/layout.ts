import dagre from 'dagre';
import type { Node, Edge } from '@xyflow/react';
import type { ResourceGraph, ResourceNode as ResourceNodeData } from '../types';

const NODE_WIDTH = 180;
const NODE_HEIGHT = 80;
const GROUP_PADDING = 60;
const RANK_SEP = 80;
const NODE_SEP = 40;

interface GroupInfo {
  id: string;
  label: string;
  color: string;
  children: string[];
}

export function buildFlowElements(graph: ResourceGraph): { nodes: Node[]; edges: Edge[] } {
  // Detect groups
  const groups = detectGroups(graph.nodes);
  const nodeToGroup = new Map<string, string>();
  for (const group of groups.values()) {
    for (const childId of group.children) {
      nodeToGroup.set(childId, group.id);
    }
  }

  // Build dagre graph
  const g = new dagre.graphlib.Graph({ compound: true });
  g.setGraph({ rankdir: 'TB', ranksep: RANK_SEP, nodesep: NODE_SEP });
  g.setDefaultEdgeLabel(() => ({}));

  // Add group nodes
  for (const group of groups.values()) {
    g.setNode(group.id, { width: 300, height: 200 });
  }

  // Add resource nodes
  for (const node of graph.nodes) {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
    const groupId = nodeToGroup.get(node.id);
    if (groupId) {
      g.setParent(node.id, groupId);
    }
  }

  // Add edges
  for (const edge of graph.edges) {
    g.setEdge(edge.source, edge.target);
  }

  dagre.layout(g);

  // Convert to React Flow nodes
  const flowNodes: Node[] = [];

  // Group nodes first (so they render behind children)
  for (const group of groups.values()) {
    const dagreNode = g.node(group.id);
    if (!dagreNode) continue;

    // Calculate bounds from children
    const childPositions = group.children
      .map(id => g.node(id))
      .filter(Boolean);

    if (childPositions.length === 0) continue;

    const minX = Math.min(...childPositions.map(n => n.x - NODE_WIDTH / 2));
    const maxX = Math.max(...childPositions.map(n => n.x + NODE_WIDTH / 2));
    const minY = Math.min(...childPositions.map(n => n.y - NODE_HEIGHT / 2));
    const maxY = Math.max(...childPositions.map(n => n.y + NODE_HEIGHT / 2));

    const groupWidth = Math.max(300, maxX - minX + GROUP_PADDING * 2);
    const groupHeight = maxY - minY + GROUP_PADDING * 2 + 20;

    flowNodes.push({
      id: group.id,
      type: 'group',
      position: {
        x: minX - GROUP_PADDING,
        y: minY - GROUP_PADDING - 20,
      },
      data: { label: group.label, color: group.color },
      style: { width: groupWidth, height: groupHeight },
      draggable: true,
      selectable: false,
    });
  }

  // Resource nodes
  for (const node of graph.nodes) {
    const dagreNode = g.node(node.id);
    if (!dagreNode) continue;

    const groupId = nodeToGroup.get(node.id);
    let position = {
      x: dagreNode.x - NODE_WIDTH / 2,
      y: dagreNode.y - NODE_HEIGHT / 2,
    };

    // If inside a group, make position relative to group
    if (groupId) {
      const groupFlowNode = flowNodes.find(n => n.id === groupId);
      if (groupFlowNode) {
        position = {
          x: position.x - groupFlowNode.position.x,
          y: position.y - groupFlowNode.position.y,
        };
      }
    }

    flowNodes.push({
      id: node.id,
      type: 'resource',
      position,
      data: node as unknown as Record<string, unknown>,
      parentId: groupId,
      extent: groupId ? 'parent' as const : undefined,
      draggable: true,
    });
  }

  // Convert edges
  const flowEdges: Edge[] = graph.edges.map((edge, i) => ({
    id: `e-${i}`,
    source: edge.source,
    target: edge.target,
    type: 'smoothstep',
    animated: edge.type === 'depends_on',
    style: {
      stroke: edge.type === 'implicit' ? '#475569' : edge.type === 'depends_on' ? '#f97316' : '#3b82f6',
      strokeWidth: 1.5,
    },
    markerEnd: {
      type: 'arrowclosed' as const,
      color: edge.type === 'implicit' ? '#475569' : edge.type === 'depends_on' ? '#f97316' : '#3b82f6',
      width: 16,
      height: 16,
    },
  }));

  return { nodes: flowNodes, edges: flowEdges };
}

function detectGroups(nodes: ResourceNodeData[]): Map<string, GroupInfo> {
  const groups = new Map<string, GroupInfo>();

  for (const node of nodes) {
    if (!node.group) continue;

    // Parse group string like "vpc:${aws_vpc.main.id}" or "subnet:${aws_subnet.pub.id}"
    const [groupType, groupRef] = node.group.split(':');
    if (!groupRef) continue;

    // Extract resource reference from ${...} if present
    const refMatch = groupRef.match(/\$\{([^.]+\.[^.]+)/);
    const groupId = refMatch ? `group-${refMatch[1]}` : `group-${groupRef}`;
    const refName = refMatch ? refMatch[1] : groupRef;

    if (!groups.has(groupId)) {
      const color = groupType === 'vpc' ? '#3b82f6' : groupType === 'subnet' ? '#06b6d4' : '#64748b';
      groups.set(groupId, {
        id: groupId,
        label: `${groupType.toUpperCase()}: ${refName}`,
        color,
        children: [],
      });
    }

    groups.get(groupId)!.children.push(node.id);
  }

  // Only keep groups with 2+ children
  for (const [id, group] of groups) {
    if (group.children.length < 2) {
      groups.delete(id);
    }
  }

  return groups;
}
