import { MarkerType } from '@xyflow/react';
import type { Node, Edge } from '@xyflow/react';
import type { ResourceGraph, ResourceNode as ResourceNodeData, GraphEdge } from '../types';
import type { ZoneType } from './colors';

// Layout constants
const NODE_W = 180;
const NODE_H = 84;
const NODE_GAP = 20;

const SUBNET_PAD = 16;
const SUBNET_LABEL_H = 32;
const SUBNET_GAP = 20;
const MIN_SUBNET_W = 220;

const AZ_PAD = 16;
const AZ_LABEL_H = 28;
const AZ_GAP = 24;

const VPC_PAD = 20;
const VPC_LABEL_H = 40;

const INTERNET_PAD = 16;
const INTERNET_LABEL_H = 32;
const INTERNET_GAP = 32;

const REG_PAD = 16;
const REG_LABEL_H = 32;
const REG_COLS = 2;
const REG_ROW_GAP = 16;
const VPC_REG_GAP = 36;

// Suppressed: become zone containers, not nodes
const SUPPRESS_AS_NODE = new Set([
  'aws_vpc',
  'aws_subnet',
  'aws_network_acl',
  'aws_vpc_dhcp_options',
  'aws_route_table',
  'aws_vpc_endpoint',
]);

const INTERNET_TYPES = new Set([
  'aws_internet_gateway',
  'aws_cloudfront_distribution',
  'aws_route53_zone',
  'aws_route53_record',
  'aws_waf_web_acl',
]);

const REGIONAL_TYPES = new Set([
  'aws_s3_bucket',
  'aws_dynamodb_table',
  'aws_sqs_queue',
  'aws_sns_topic',
  'aws_kms_key',
  'aws_iam_role',
  'aws_iam_policy',
  'aws_iam_instance_profile',
  'aws_cloudwatch_log_group',
  'aws_cloudwatch_metric_alarm',
  'aws_secretsmanager_secret',
  'aws_ssm_parameter',
]);

// Resources that live inside subnets
const SUBNET_PLACED_TYPES = new Set([
  'aws_instance', 'aws_autoscaling_group',
  'aws_ecs_service', 'aws_ecs_cluster', 'aws_ecs_task_definition',
  'aws_eks_cluster', 'aws_eks_node_group',
  'aws_lb', 'aws_alb',
  'aws_nat_gateway', 'aws_eip',
  'aws_db_instance', 'aws_rds_instance', 'aws_rds_cluster',
  'aws_elasticache_cluster', 'aws_elasticache_replication_group',
  'aws_redshift_cluster',
  'aws_security_group',
  'aws_lambda_function',
]);

function resolveSubnetRef(ref: string, subnetNodes: ResourceNodeData[]): ResourceNodeData | null {
  for (const s of subnetNodes) {
    if (s.id === ref || ref.includes(s.name) || ref.includes(s.id)) return s;
  }
  return null;
}

function getNodeSubnet(node: ResourceNodeData, subnetNodes: ResourceNodeData[]): ResourceNodeData | null {
  const subnetId = node.attributes?.subnet_id as string | undefined;
  if (subnetId) return resolveSubnetRef(subnetId, subnetNodes);

  const subnets = node.attributes?.subnets as string[] | undefined;
  if (subnets?.length) return resolveSubnetRef(subnets[0], subnetNodes);

  return null;
}

function getSubnetAZ(subnet: ResourceNodeData): string | null {
  return (subnet.attributes?.availability_zone as string) ?? null;
}

function isPublicSubnet(subnet: ResourceNodeData): boolean {
  return !!(subnet.attributes?.map_public_ip_on_launch) ||
    subnet.name?.toLowerCase().includes('public') ||
    (subnet.attributes?.tags as Record<string, string>)?.Tier?.toLowerCase() === 'public';
}

// --- Main layout ---

export function buildFlowElements(graph: ResourceGraph): { nodes: Node[]; edges: Edge[] } {
  const suppressedIds = new Set<string>();
  for (const n of graph.nodes) {
    if (SUPPRESS_AS_NODE.has(n.type)) suppressedIds.add(n.id);
  }

  const subnetNodes = graph.nodes.filter(n => n.type === 'aws_subnet');
  const vpcNode = graph.nodes.find(n => n.type === 'aws_vpc');

  // Categorise
  const internetNodes: ResourceNodeData[] = [];
  const regionalNodes: ResourceNodeData[] = [];
  const subnetCandidates: ResourceNodeData[] = [];

  for (const node of graph.nodes) {
    if (suppressedIds.has(node.id)) continue;
    if (INTERNET_TYPES.has(node.type)) {
      internetNodes.push(node);
    } else if (REGIONAL_TYPES.has(node.type)) {
      // Lambda with VPC config goes into subnet instead
      if (node.type === 'aws_lambda_function') {
        const vpc = node.attributes?.vpc_config as Record<string, unknown> | undefined;
        if (vpc && Object.keys(vpc).length > 0) { subnetCandidates.push(node); continue; }
      }
      regionalNodes.push(node);
    } else if (SUBNET_PLACED_TYPES.has(node.type)) {
      subnetCandidates.push(node);
    } else {
      regionalNodes.push(node); // fallback
    }
  }

  // Assign subnet candidates — two passes so SGs can use consumer placements
  const resourceToSubnet = new Map<string, ResourceNodeData>();
  const subnetToResources = new Map<string, ResourceNodeData[]>();
  const unplaced: ResourceNodeData[] = [];

  // Pass 1: non-SG resources with direct subnet_id / subnets attr
  for (const node of subnetCandidates) {
    if (node.type === 'aws_security_group') continue;
    const subnet = getNodeSubnet(node, subnetNodes);
    if (subnet) {
      resourceToSubnet.set(node.id, subnet);
      if (!subnetToResources.has(subnet.id)) subnetToResources.set(subnet.id, []);
      subnetToResources.get(subnet.id)!.push(node);
    } else {
      unplaced.push(node);
    }
  }

  // Pass 2: security groups — place with their primary consumer
  for (const node of subnetCandidates) {
    if (node.type !== 'aws_security_group') continue;
    let placed = false;
    for (const candidate of subnetCandidates) {
      if (candidate.type === 'aws_security_group') continue;
      if (!resourceToSubnet.has(candidate.id)) continue;
      const sgIds = (candidate.attributes?.vpc_security_group_ids as string[] | undefined) ?? [];
      const sgRefs = (candidate.attributes?.security_groups as string[] | undefined) ?? [];
      const refs = [...sgIds, ...sgRefs];
      if (refs.some(r => r.includes(node.name) || r.includes(node.id))) {
        const subnet = resourceToSubnet.get(candidate.id)!;
        resourceToSubnet.set(node.id, subnet);
        if (!subnetToResources.has(subnet.id)) subnetToResources.set(subnet.id, []);
        subnetToResources.get(subnet.id)!.push(node);
        placed = true;
        break;
      }
    }
    if (!placed) {
      // Place in first available subnet or regional
      if (subnetNodes.length > 0) {
        const firstSubnet = subnetNodes[0];
        resourceToSubnet.set(node.id, firstSubnet);
        if (!subnetToResources.has(firstSubnet.id)) subnetToResources.set(firstSubnet.id, []);
        subnetToResources.get(firstSubnet.id)!.push(node);
      } else {
        unplaced.push(node);
      }
    }
  }

  regionalNodes.push(...unplaced);

  // Group subnets by AZ
  const azToSubnets = new Map<string, ResourceNodeData[]>();
  const hasAZ = subnetNodes.some(s => getSubnetAZ(s) !== null);
  for (const s of subnetNodes) {
    const az = getSubnetAZ(s) ?? 'default';
    if (!azToSubnets.has(az)) azToSubnets.set(az, []);
    azToSubnets.get(az)!.push(s);
  }

  // --- Size calculations (bottom-up) ---

  type SubnetLayout = { subnet: ResourceNodeData; resources: ResourceNodeData[]; w: number; h: number };
  type AZLayout = { az: string; subnets: SubnetLayout[]; w: number; h: number };

  const azLayouts: AZLayout[] = [];

  for (const [az, subnets] of azToSubnets) {
    const subnetLayouts: SubnetLayout[] = [];
    for (const subnet of subnets) {
      const resources = subnetToResources.get(subnet.id) ?? [];
      const n = Math.max(resources.length, 1);
      const sw = Math.max(n * (NODE_W + NODE_GAP) - NODE_GAP + 2 * SUBNET_PAD, MIN_SUBNET_W);
      const sh = SUBNET_LABEL_H + SUBNET_PAD + NODE_H + SUBNET_PAD;
      subnetLayouts.push({ subnet, resources, w: sw, h: sh });
    }
    const totalSubnetW = subnetLayouts.reduce((a, s) => a + s.w, 0) +
      Math.max(0, subnetLayouts.length - 1) * SUBNET_GAP;
    const maxSubnetH = Math.max(...subnetLayouts.map(s => s.h));

    const useAZContainer = hasAZ && az !== 'default';
    const azW = useAZContainer ? totalSubnetW + 2 * AZ_PAD : totalSubnetW;
    const azH = useAZContainer ? AZ_LABEL_H + AZ_PAD + maxSubnetH + AZ_PAD : maxSubnetH;

    azLayouts.push({ az, subnets: subnetLayouts, w: azW, h: azH });
  }

  const totalAZW = azLayouts.reduce((a, l) => a + l.w, 0) +
    Math.max(0, azLayouts.length - 1) * AZ_GAP;
  const maxAZH = azLayouts.length > 0 ? Math.max(...azLayouts.map(l => l.h)) : 0;

  const vpcContentW = subnetNodes.length > 0
    ? totalAZW + 2 * VPC_PAD
    : 400;
  const vpcContentH = subnetNodes.length > 0
    ? VPC_LABEL_H + VPC_PAD + maxAZH + VPC_PAD
    : 200;

  // --- Render ---
  const flowNodes: Node[] = [];
  const startX = 40;
  let currentY = 40;

  // 1. Internet zone
  if (internetNodes.length > 0) {
    const iW = Math.max(
      internetNodes.length * (NODE_W + NODE_GAP) - NODE_GAP + 2 * INTERNET_PAD,
      300,
    );
    const iH = INTERNET_LABEL_H + INTERNET_PAD + NODE_H + INTERNET_PAD;
    flowNodes.push(makeZone('zone-internet', 'Internet / Edge', 'internet', startX, currentY, iW, iH));
    internetNodes.forEach((n, i) => {
      flowNodes.push(makeResource(n, INTERNET_PAD + i * (NODE_W + NODE_GAP), INTERNET_LABEL_H + INTERNET_PAD, 'zone-internet'));
    });
    currentY += iH + INTERNET_GAP;
  }

  const vpcStartY = currentY;

  // 2. VPC + AZ + subnet zones
  const vpcLabel = vpcNode
    ? `${vpcNode.name} · ${(vpcNode.attributes?.cidr_block as string) ?? ''}`
    : 'VPC';
  flowNodes.push(makeZone('zone-vpc', vpcLabel, 'vpc', startX, vpcStartY, vpcContentW, vpcContentH));

  let azX = VPC_PAD;
  const azBaseY = VPC_LABEL_H;
  const useAZContainers = hasAZ;

  for (const azLayout of azLayouts) {
    const useAZContainer = useAZContainers && azLayout.az !== 'default';
    let subnetParent: string;
    let subnetOffsetX: number;
    let subnetOffsetY: number;

    if (useAZContainer) {
      const azId = `zone-az-${azLayout.az.replace(/[^a-z0-9]/gi, '-')}`;
      flowNodes.push(makeZone(azId, `AZ: ${azLayout.az}`, 'az', azX, azBaseY, azLayout.w, azLayout.h, 'zone-vpc'));
      subnetParent = azId;
      subnetOffsetX = AZ_PAD;
      subnetOffsetY = AZ_LABEL_H;
    } else {
      subnetParent = 'zone-vpc';
      subnetOffsetX = azX;
      subnetOffsetY = azBaseY;
    }

    let sX = subnetOffsetX;

    for (const sl of azLayout.subnets) {
      const subnetId = `zone-subnet-${sl.subnet.id.replace(/[^a-z0-9]/gi, '-')}`;
      const cidr = sl.subnet.attributes?.cidr_block as string | undefined;
      const shortCidr = cidr ? `/${cidr.split('/')[1]}` : '';
      const subnetLabel = `${sl.subnet.name}${shortCidr ? ` · ${shortCidr}` : ''}`;
      const zType: ZoneType = isPublicSubnet(sl.subnet) ? 'public_subnet' : 'private_subnet';

      flowNodes.push(makeZone(subnetId, subnetLabel, zType, sX, subnetOffsetY, sl.w, sl.h, subnetParent));

      sl.resources.forEach((n, i) => {
        flowNodes.push(makeResource(n, SUBNET_PAD + i * (NODE_W + NODE_GAP), SUBNET_LABEL_H + SUBNET_PAD / 2, subnetId));
      });

      sX += sl.w + SUBNET_GAP;
    }

    azX += azLayout.w + AZ_GAP;
  }

  // 3. Regional services (right of VPC)
  if (regionalNodes.length > 0) {
    const cols = REG_COLS;
    const rows = Math.ceil(regionalNodes.length / cols);
    const regW = cols * (NODE_W + NODE_GAP) - NODE_GAP + 2 * REG_PAD;
    const regH = REG_LABEL_H + REG_PAD + rows * (NODE_H + REG_ROW_GAP) - REG_ROW_GAP + REG_PAD;
    const regX = startX + vpcContentW + VPC_REG_GAP;

    flowNodes.push(makeZone('zone-regional', 'Regional Services (AWS)', 'regional', regX, vpcStartY, regW, regH));

    regionalNodes.forEach((n, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      flowNodes.push(makeResource(
        n,
        REG_PAD + col * (NODE_W + NODE_GAP),
        REG_LABEL_H + REG_PAD + row * (NODE_H + REG_ROW_GAP),
        'zone-regional',
      ));
    });
  }

  // 4. Edges
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
): Node {
  const node: Node = {
    id,
    type: 'group',
    position: { x, y },
    data: { label, zoneType },
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

function makeResource(data: ResourceNodeData, x: number, y: number, parentId: string): Node {
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
    // Skip if either endpoint is a suppressed structural node (VPC/subnet)
    if (suppressedIds.has(edge.source) || suppressedIds.has(edge.target)) continue;

    const source = nodes.find(n => n.id === edge.source);
    const target = nodes.find(n => n.id === edge.target);
    if (!source || !target) continue;

    result.push({
      id: `e-${idx++}`,
      source: edge.source,
      target: edge.target,
      type: 'smoothstep',
      ...getEdgeStyle(source, target),
    });
  }

  return result;
}

function getEdgeStyle(source: ResourceNodeData, target: ResourceNodeData): Partial<Edge> {
  // Security group attachment
  if (source.type === 'aws_security_group' || target.type === 'aws_security_group') {
    return {
      style: { stroke: '#ef4444', strokeWidth: 1, strokeDasharray: '3 2' },
      label: 'sg',
      labelStyle: { fontSize: 9, fill: '#ef4444' } as React.CSSProperties,
      labelBgStyle: { fill: '#0f172a', fillOpacity: 0.8 },
      labelBgPadding: [3, 1] as [number, number],
    };
  }

  // Access to regional services
  if (REGIONAL_TYPES.has(target.type)) {
    return {
      style: { stroke: '#1e3a5f', strokeWidth: 1, strokeDasharray: '5 4' },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#3b82f6', width: 14, height: 14 },
    };
  }

  // IGW / internet traffic
  if (INTERNET_TYPES.has(source.type) || INTERNET_TYPES.has(target.type)) {
    return {
      style: { stroke: '#475569', strokeWidth: 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#64748b', width: 14, height: 14 },
    };
  }

  // Default dependency
  return {
    style: { stroke: '#1e293b', strokeWidth: 1, strokeDasharray: '4 3' },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#334155', width: 14, height: 14 },
  };
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
