import { MarkerType } from '@xyflow/react';
import type { Node, Edge } from '@xyflow/react';
import type { ResourceGraph, ResourceNode as ResourceNodeData, GraphEdge } from '../types';
import type { ZoneType } from './colors';

// Layout constants
const NODE_W = 180;
const NODE_H = 72;
const GAP_X = 24;
const TIER_PAD = 24;
const LABEL_H = 36;
const ZONE_GAP = 40;
const VPC_PAD = 24;
const VPC_LABEL_H = 40;
const EMPTY_ZONE_H = 64;

// --- Tier classification ---

type Tier = 'internet' | 'public' | 'private' | 'data' | 'regional';

const RESOURCE_TIER: Record<string, Tier> = {
  // Internet/Edge
  aws_internet_gateway: 'internet',
  aws_cloudfront_distribution: 'internet',
  aws_route53_zone: 'internet',
  aws_route53_record: 'internet',
  aws_waf_web_acl: 'internet',
  // Public subnet tier
  aws_alb: 'public',
  aws_lb: 'public',
  aws_nat_gateway: 'public',
  aws_eip: 'public',
  // Private subnet tier (compute)
  aws_instance: 'private',
  aws_autoscaling_group: 'private',
  aws_ecs_service: 'private',
  aws_ecs_cluster: 'private',
  aws_ecs_task_definition: 'private',
  aws_eks_cluster: 'private',
  aws_eks_node_group: 'private',
  // Data tier
  aws_db_instance: 'data',
  aws_rds_instance: 'data',
  aws_rds_cluster: 'data',
  aws_elasticache_cluster: 'data',
  aws_elasticache_replication_group: 'data',
  aws_redshift_cluster: 'data',
  // Regional services
  aws_s3_bucket: 'regional',
  aws_dynamodb_table: 'regional',
  aws_sqs_queue: 'regional',
  aws_sns_topic: 'regional',
  aws_kms_key: 'regional',
  aws_iam_role: 'regional',
  aws_iam_policy: 'regional',
  aws_iam_instance_profile: 'regional',
  aws_cloudwatch_log_group: 'regional',
  aws_cloudwatch_metric_alarm: 'regional',
  aws_secretsmanager_secret: 'regional',
  aws_ssm_parameter: 'regional',
};

// Resources suppressed from node rendering — represented by zone containers or badges
const SUPPRESS_AS_NODE = new Set([
  'aws_vpc',
  'aws_subnet',
  'aws_security_group',
  'aws_network_acl',
  'aws_vpc_dhcp_options',
  'aws_route_table',
  'aws_vpc_endpoint',
]);

// Determine tier for compute resources based on their subnet reference
function getComputeTier(node: ResourceNodeData, allNodes: ResourceNodeData[]): Tier {
  const subnetRef = node.attributes?.subnet_id as string | undefined;
  if (subnetRef) {
    const subnet = allNodes.find(n => n.id === subnetRef || subnetRef.includes(n.name));
    if (subnet) {
      if (subnet.name?.includes('public') || subnet.attributes?.map_public_ip_on_launch) {
        return 'public';
      }
      return 'private';
    }
  }
  return 'private';
}

function getResourceTier(node: ResourceNodeData, allNodes: ResourceNodeData[]): Tier {
  // Compute resources: check subnet reference for tier placement
  if (['aws_instance', 'aws_ecs_service', 'aws_ecs_task_definition'].includes(node.type)) {
    return getComputeTier(node, allNodes);
  }
  if (node.type === 'aws_lambda_function') {
    const vpc = node.attributes?.vpc_config;
    const hasVpcConfig = vpc && typeof vpc === 'object' && Object.keys(vpc as object).length > 0;
    return hasVpcConfig ? 'private' : 'regional';
  }
  return RESOURCE_TIER[node.type] ?? 'private';
}

function tierToZone(tier: Tier): ZoneType {
  switch (tier) {
    case 'internet': return 'internet';
    case 'public': return 'public_subnet';
    case 'private': return 'private_subnet';
    case 'data': return 'data_subnet';
    case 'regional': return 'regional';
  }
}

const TIER_LABELS: Record<Tier, string> = {
  internet: 'Internet / Edge',
  public: 'Public Tier',
  private: 'Private Tier',
  data: 'Data Tier',
  regional: 'Regional Services (AWS)',
};

const TIER_CHIPS: Partial<Record<Tier, string>> = {
  public: '\uD83C\uDF10 public \u00b7 internet-facing',
  private: '\uD83D\uDD12 private \u00b7 no public IP',
  data: '\uD83D\uDDC4 data \u00b7 isolated',
};

// --- Main layout function ---

export function buildFlowElements(graph: ResourceGraph): { nodes: Node[]; edges: Edge[] } {
  // Suppress VPC-structural nodes — represented by zone containers/badges
  const suppressedIds = new Set<string>();
  for (const node of graph.nodes) {
    if (SUPPRESS_AS_NODE.has(node.type)) {
      suppressedIds.add(node.id);
    }
  }

  // Find VPC node for label
  const vpcNode = graph.nodes.find(n => n.type === 'aws_vpc');
  const vpcLabel = vpcNode ? vpcNode.id : 'VPC';

  // Find subnet metadata for CIDR display
  const subnetNodes = graph.nodes.filter(n => n.type === 'aws_subnet');
  const publicSubnet = subnetNodes.find(n =>
    n.name?.includes('public') || n.group?.includes('public')
  );
  const privateSubnet = subnetNodes.find(n =>
    n.name?.includes('private') || n.group?.includes('private')
  );

  // Filter to renderable nodes (exclude suppressed structural types)
  const renderableNodes = graph.nodes.filter(n => !suppressedIds.has(n.id));

  // Classify renderable nodes into tiers
  const tiered: Record<Tier, ResourceNodeData[]> = {
    internet: [], public: [], private: [], data: [], regional: [],
  };
  for (const node of renderableNodes) {
    tiered[getResourceTier(node, graph.nodes)].push(node);
  }

  // --- Position calculation ---
  const flowNodes: Node[] = [];
  const startX = 40;
  let currentY = 40;

  function rowWidth(count: number): number {
    return Math.max(count * (NODE_W + GAP_X) - GAP_X + 2 * TIER_PAD, 400);
  }
  const singleTierH = NODE_H + 2 * TIER_PAD + LABEL_H;

  // Internet zone (above VPC, standalone)
  if (tiered.internet.length > 0) {
    const w = rowWidth(tiered.internet.length);
    flowNodes.push(makeZone('zone-internet', 'Internet / Edge', 'internet', startX, currentY, w, singleTierH));
    tiered.internet.forEach((n, i) => {
      flowNodes.push(makeResource(n, TIER_PAD + i * (NODE_W + GAP_X), LABEL_H + TIER_PAD, 'zone-internet'));
    });
    currentY += singleTierH + ZONE_GAP;
  }

  // VPC container with nested tier zones — always render all three tiers
  const vpcTiers: Tier[] = ['public', 'private', 'data'];

  // Calculate max tier width across all tiers (including empty ones for uniform sizing)
  const populatedTierWidths = vpcTiers
    .filter(t => tiered[t].length > 0)
    .map(t => rowWidth(tiered[t].length));
  const maxTierW = populatedTierWidths.length > 0
    ? Math.max(...populatedTierWidths, 400)
    : 400;
  const vpcContentW = maxTierW + 2 * VPC_PAD;

  // Calculate VPC height — always render all three tier zones
  let vpcInnerY = VPC_LABEL_H;
  const tierLayout: { tier: Tier; relY: number; isEmpty: boolean }[] = [];
  for (const tier of vpcTiers) {
    tierLayout.push({ tier, relY: vpcInnerY, isEmpty: tiered[tier].length === 0 });
    const zoneH = tiered[tier].length === 0 ? EMPTY_ZONE_H : singleTierH;
    vpcInnerY += zoneH + ZONE_GAP;
  }
  const vpcH = vpcInnerY - ZONE_GAP + VPC_PAD + 40;

  const vpcStartY = currentY;

  // VPC outer group
  flowNodes.push(makeZone('zone-vpc', vpcLabel, 'vpc', startX, vpcStartY, vpcContentW, vpcH));

  // Tier zones inside VPC — always rendered, even if empty
  for (const { tier, relY, isEmpty } of tierLayout) {
    const zoneId = `zone-${tier}`;
    const zoneH = isEmpty ? EMPTY_ZONE_H : singleTierH;
    const cidr = tier === 'public'
      ? (publicSubnet?.attributes?.cidr_block as string | undefined)
      : tier === 'private' || tier === 'data'
        ? (privateSubnet?.attributes?.cidr_block as string | undefined)
        : undefined;

    flowNodes.push(makeZone(
      zoneId, TIER_LABELS[tier], tierToZone(tier),
      VPC_PAD, relY, maxTierW, zoneH,
      'zone-vpc', TIER_CHIPS[tier], cidr,
    ));

    tiered[tier].forEach((n, i) => {
      flowNodes.push(makeResource(n, TIER_PAD + i * (NODE_W + GAP_X), LABEL_H + TIER_PAD, zoneId));
    });
  }

  // Regional Services (right column, aligned with VPC top)
  if (tiered.regional.length > 0) {
    const cols = 2;
    const rows = Math.ceil(tiered.regional.length / cols);
    const regW = cols * (NODE_W + GAP_X) - GAP_X + 2 * TIER_PAD;
    const regRowGap = 56;
    const regH = rows * (NODE_H + regRowGap) - regRowGap + 2 * TIER_PAD + LABEL_H;
    const regX = startX + vpcContentW + ZONE_GAP;

    flowNodes.push(makeZone('zone-regional', 'Regional Services (AWS)', 'regional', regX, vpcStartY, regW, regH));

    tiered.regional.forEach((n, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      flowNodes.push(makeResource(
        n,
        TIER_PAD + col * (NODE_W + GAP_X),
        LABEL_H + TIER_PAD + row * (NODE_H + regRowGap),
        'zone-regional',
      ));
    });
  }

  // Build edges
  const flowEdges = buildEdges(graph.edges, graph.nodes, suppressedIds);

  return { nodes: flowNodes, edges: flowEdges };
}

// --- Node builders ---

function makeZone(
  id: string,
  label: string,
  zoneType: ZoneType,
  x: number,
  y: number,
  width: number,
  height: number,
  parentId?: string,
  chip?: string,
  cidr?: string,
): Node {
  const node: Node = {
    id,
    type: 'group',
    position: { x, y },
    data: { label, zoneType, chip, cidr },
    style: { width, height },
    draggable: true,
    selectable: false,
  };
  if (parentId) {
    node.parentId = parentId;
    node.extent = 'parent' as const;
  }
  return node;
}

function makeResource(
  data: ResourceNodeData,
  x: number,
  y: number,
  parentId: string,
): Node {
  return {
    id: data.id,
    type: 'resource',
    position: { x, y },
    data: data as unknown as Record<string, unknown>,
    parentId,
    extent: 'parent' as const,
    draggable: true,
  };
}

// --- Edge system ---

function buildEdges(
  edges: GraphEdge[],
  nodes: ResourceNodeData[],
  suppressedIds: Set<string>,
): Edge[] {
  const deduped = deduplicateEdges(edges);
  const result: Edge[] = [];
  let idx = 0;

  for (const edge of deduped) {
    if (suppressedIds.has(edge.source) || suppressedIds.has(edge.target)) continue;

    const source = nodes.find(n => n.id === edge.source);
    const target = nodes.find(n => n.id === edge.target);
    if (!source || !target) continue;

    const sourceTier = getResourceTier(source, nodes);
    const targetTier = getResourceTier(target, nodes);
    const style = getEdgeStyle(source, target, sourceTier, targetTier);
    if (!style) continue;

    result.push({
      id: `e-${idx++}`,
      source: edge.source,
      target: edge.target,
      type: 'smoothstep',
      ...style,
    });
  }

  return result;
}

function getEdgeStyle(
  source: ResourceNodeData,
  target: ResourceNodeData,
  sourceTier: Tier,
  targetTier: Tier,
): Partial<Edge> | null {
  // Security group relationships (check first — takes priority)
  if (source.type === 'aws_security_group' || target.type === 'aws_security_group') {
    return {
      style: { stroke: '#ef4444', strokeWidth: 1, strokeDasharray: '3 2' },
      label: 'attached',
      labelStyle: { fontSize: 9, fill: '#ef4444' } as React.CSSProperties,
      labelBgStyle: { fill: '#0f172a', fillOpacity: 0.8 },
      labelBgPadding: [3, 1] as [number, number],
    };
  }

  // Traffic flow: adjacent VPC tiers (internet→public→private→data)
  const tierOrder: Tier[] = ['internet', 'public', 'private', 'data'];
  const si = tierOrder.indexOf(sourceTier);
  const ti = tierOrder.indexOf(targetTier);
  if (si >= 0 && ti >= 0 && ti === si + 1) {
    return {
      style: { stroke: '#334155', strokeWidth: 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#475569', width: 16, height: 16 },
    };
  }

  // Access to regional services
  if (targetTier === 'regional') {
    return {
      style: { stroke: '#1e3a5f', strokeWidth: 1, strokeDasharray: '5 4' },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#3b82f6', width: 16, height: 16 },
      label: getAccessLabel(target),
      labelStyle: { fontSize: 10, fill: '#475569' } as React.CSSProperties,
      labelBgStyle: { fill: '#0f172a', fillOpacity: 0.8 },
      labelBgPadding: [4, 2] as [number, number],
    };
  }

  // Default dependency
  return {
    style: { stroke: '#1e293b', strokeWidth: 1, strokeDasharray: '4 3' },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#334155', width: 16, height: 16 },
  };
}

function getAccessLabel(target: ResourceNodeData): string {
  if (target.type === 'aws_kms_key') return 'encrypts with';
  if (target.type === 'aws_iam_role') return 'assumes';
  if (target.type === 'aws_iam_policy') return 'grants';
  if (target.type === 'aws_sqs_queue') return 'publishes to';
  if (target.type === 'aws_sns_topic') return 'publishes to';
  if (target.type === 'aws_s3_bucket') return 'reads/writes';
  if (target.type === 'aws_dynamodb_table') return 'queries';
  if (target.type === 'aws_secretsmanager_secret') return 'reads secret';
  return 'accesses';
}

function deduplicateEdges(edges: GraphEdge[]): GraphEdge[] {
  const seen = new Map<string, GraphEdge>();
  for (const edge of edges) {
    const key = `${edge.source}\u2192${edge.target}`;
    const existing = seen.get(key);
    if (!existing || edge.type === 'explicit') seen.set(key, edge);
  }
  return Array.from(seen.values());
}
