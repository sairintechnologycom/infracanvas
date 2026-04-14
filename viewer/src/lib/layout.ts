import dagre from 'dagre';
import type { Node, Edge } from '@xyflow/react';
import type { ResourceGraph, ResourceNode as ResourceNodeData, GraphEdge } from '../types';
import { EDGE_STYLES, type EdgeRelationship } from './colors';

const NODE_WIDTH = 180;
const NODE_HEIGHT = 80;
const GROUP_PADDING = 60;
const RANK_SEP = 80;
const NODE_SEP = 40;

const REGIONAL_RESOURCE_TYPES = [
  'aws_s3_bucket', 'aws_sqs_queue', 'aws_sns_topic',
  'aws_dynamodb_table', 'aws_cloudfront_distribution',
  'aws_kms_key', 'aws_iam_role', 'aws_iam_policy',
  'aws_lambda_function',
];

interface GroupInfo {
  id: string;
  label: string;
  color: string;
  children: string[];
  dashed?: boolean;
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

  // Issue 1: Track which VPC nodes have a corresponding group
  const suppressedVpcNodes = new Set<string>();
  for (const node of graph.nodes) {
    if (node.type === 'aws_vpc') {
      const groupId = `group-${node.id}`;
      if (groups.has(groupId)) {
        suppressedVpcNodes.add(node.id);
      }
    }
  }

  // Issue 3: Determine security group parent placement
  // Move SG to same parent group as the instance it protects
  for (const node of graph.nodes) {
    if (node.type === 'aws_security_group') {
      const attachedInstance = graph.nodes.find(n =>
        n.type === 'aws_instance' && n.dependencies.includes(node.id)
      );
      if (attachedInstance) {
        const instanceGroup = nodeToGroup.get(attachedInstance.id);
        if (instanceGroup && nodeToGroup.get(node.id) !== instanceGroup) {
          // Move SG from its current group to the instance's group
          const currentGroup = nodeToGroup.get(node.id);
          if (currentGroup) {
            const g = groups.get(currentGroup);
            if (g) g.children = g.children.filter(id => id !== node.id);
          }
          nodeToGroup.set(node.id, instanceGroup);
          groups.get(instanceGroup)?.children.push(node.id);
        }
      }
    }
  }

  // Issue 5: Create Regional Services group for non-VPC resources
  const regionalNodes = graph.nodes.filter(n => {
    if (suppressedVpcNodes.has(n.id)) return false;
    if (nodeToGroup.has(n.id)) return false;
    // Lambda with vpc_config stays in VPC
    if (n.type === 'aws_lambda_function' && n.attributes?.vpc_config) return false;
    return REGIONAL_RESOURCE_TYPES.includes(n.type);
  });

  if (regionalNodes.length > 0) {
    const regionalGroupId = 'group-regional-services';
    groups.set(regionalGroupId, {
      id: regionalGroupId,
      label: 'Regional Services (AWS)',
      color: '#64748b',
      children: regionalNodes.map(n => n.id),
      dashed: true,
    });
    for (const n of regionalNodes) {
      nodeToGroup.set(n.id, regionalGroupId);
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

  // Add resource nodes (skip suppressed VPC nodes)
  for (const node of graph.nodes) {
    if (suppressedVpcNodes.has(node.id)) continue;
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
    const groupId = nodeToGroup.get(node.id);
    if (groupId) {
      g.setParent(node.id, groupId);
    }
  }

  // Issue 6: Deduplicate edges and classify
  const dedupedEdges = deduplicateEdges(graph.edges);
  const classifiedEdges: { edge: GraphEdge; relationship: EdgeRelationship }[] = [];

  for (const edge of dedupedEdges) {
    // Skip edges to/from suppressed VPC nodes
    if (suppressedVpcNodes.has(edge.source) || suppressedVpcNodes.has(edge.target)) continue;

    const relationship = classifyEdge(edge, graph.nodes);
    classifiedEdges.push({ edge, relationship });

    // Only add non-containment edges to dagre
    if (relationship !== 'containment') {
      g.setEdge(edge.source, edge.target);
    }
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

    // Issue 4: Enrich subnet group data
    const groupData: Record<string, unknown> = {
      label: group.label,
      color: group.color,
      dashed: group.dashed ?? false,
    };

    // Find the source node for this group to get subnet metadata
    const groupRefMatch = group.id.match(/^group-(.+)$/);
    if (groupRefMatch) {
      const sourceNode = graph.nodes.find(n => n.id === groupRefMatch[1]);
      if (sourceNode?.type === 'aws_subnet') {
        groupData.subnetNode = sourceNode;
      }
    }

    flowNodes.push({
      id: group.id,
      type: 'group',
      position: {
        x: minX - GROUP_PADDING,
        y: minY - GROUP_PADDING - 20,
      },
      data: groupData,
      style: {
        width: groupWidth,
        height: groupHeight,
        ...(group.dashed ? { borderStyle: 'dashed' } : {}),
      },
      draggable: true,
      selectable: false,
    });
  }

  // Resource nodes
  for (const node of graph.nodes) {
    if (suppressedVpcNodes.has(node.id)) continue;
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

  // Convert edges — skip containment, style by relationship
  const flowEdges: Edge[] = [];
  let edgeIndex = 0;

  for (const { edge, relationship } of classifiedEdges) {
    // Containment edges are not rendered (nesting shows the relationship)
    if (relationship === 'containment') continue;

    const edgeStyle = EDGE_STYLES[relationship];
    if (!edgeStyle) continue;

    // Issue 6: Use straight edges within same group, smoothstep across groups
    const sourceGroup = nodeToGroup.get(edge.source);
    const targetGroup = nodeToGroup.get(edge.target);
    const sameGroup = sourceGroup && targetGroup && sourceGroup === targetGroup;
    const edgeType = sameGroup ? 'straight' : 'smoothstep';

    const flowEdge: Edge = {
      id: `e-${edgeIndex++}`,
      source: edge.source,
      target: edge.target,
      type: edgeType,
      animated: edgeStyle.animated,
      style: edgeStyle.style as React.CSSProperties,
    };

    if (edgeStyle.markerEnd) {
      flowEdge.markerEnd = {
        ...edgeStyle.markerEnd,
        width: 16,
        height: 16,
      };
    }

    // Issue 5: Add access edge labels
    if (relationship === 'access') {
      const sourceNode = graph.nodes.find(n => n.id === edge.source);
      const targetNode = graph.nodes.find(n => n.id === edge.target);
      if (sourceNode && targetNode) {
        flowEdge.label = getAccessEdgeLabel(sourceNode, targetNode);
        flowEdge.labelStyle = edgeStyle.labelStyle as React.CSSProperties;
        flowEdge.labelBgStyle = { fill: '#0f172a', fillOpacity: 0.8 };
        flowEdge.labelBgPadding = [4, 2] as [number, number];
      }
    }

    flowEdges.push(flowEdge);
  }

  return { nodes: flowNodes, edges: flowEdges };
}

function detectGroups(nodes: ResourceNodeData[]): Map<string, GroupInfo> {
  const groups = new Map<string, GroupInfo>();

  for (const node of nodes) {
    if (!node.group) continue;

    // Parse group string like "vpc:aws_vpc.main" or "subnet:${aws_subnet.pub.id}"
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
        // Issue 1: Lowercase label format matching resource address style
        label: `${groupType}.${refName.replace(/^aws_/, '')}`,
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

// Issue 2: Classify edge by relationship type
function classifyEdge(edge: GraphEdge, nodes: ResourceNodeData[]): EdgeRelationship {
  const source = nodes.find(n => n.id === edge.source);
  const target = nodes.find(n => n.id === edge.target);
  if (!source || !target) return 'dependency';

  // subnet → vpc: containment (nesting handles it)
  if (source.type.includes('subnet') && target.type === 'aws_vpc') return 'containment';
  // instance → subnet: containment
  if (source.type === 'aws_instance' && target.type.includes('subnet')) return 'containment';
  // security_group → vpc: containment
  if (source.type === 'aws_security_group' && target.type === 'aws_vpc') return 'containment';
  // security_group → instance: attachment
  if (source.type === 'aws_security_group') return 'attachment';
  // instance → security_group: attachment
  if (source.type === 'aws_instance' && target.type === 'aws_security_group') return 'attachment';
  // instance/lambda → iam_role: attachment
  if (target.type === 'aws_iam_role') return 'attachment';
  // instance/lambda → s3/sqs/sns/dynamodb: access
  if (['aws_s3_bucket', 'aws_sqs_queue', 'aws_sns_topic', 'aws_dynamodb_table'].includes(target.type)) return 'access';
  // everything else: dependency
  return 'dependency';
}

// Issue 5: Label access edges
function getAccessEdgeLabel(_source: ResourceNodeData, target: ResourceNodeData): string {
  if (target.type === 'aws_kms_key') return 'encrypts with';
  if (target.type === 'aws_iam_role') return 'assumes';
  if (['aws_sqs_queue', 'aws_sns_topic'].includes(target.type)) return 'publishes to';
  if (target.type === 'aws_s3_bucket') return 'reads/writes';
  return 'accesses';
}

// Issue 6: Deduplicate edges (keep explicit over implicit)
function deduplicateEdges(edges: GraphEdge[]): GraphEdge[] {
  const seen = new Map<string, GraphEdge>();
  for (const edge of edges) {
    const key = `${edge.source}\u2192${edge.target}`;
    const existing = seen.get(key);
    if (!existing || edge.type === 'explicit') seen.set(key, edge);
  }
  return Array.from(seen.values());
}
