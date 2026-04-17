import { MarkerType } from '@xyflow/react';
import type { Node, Edge } from '@xyflow/react';
import type { ResourceGraph, ResourceNode as ResourceNodeData, GraphEdge } from '../types';
import type { ZoneType } from './colors';
import { detectProvider, PROVIDER_THEMES, type Provider } from './providerTheme';

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
const REG_ROW_GAP = 16;
const VPC_REG_GAP = 36;

const CLOUD_PAD = 20;
const CLOUD_LABEL_H = 36;
const CLOUD_GAP = 40;

type CategoryKey = 'identity' | 'data' | 'messaging' | 'observability' | 'network' | 'other';

const CATEGORY_ORDER: CategoryKey[] = ['identity', 'data', 'messaging', 'observability', 'network', 'other'];

const CATEGORY_LABELS: Record<CategoryKey, string> = {
  identity: 'IDENTITY & ACCESS',
  data: 'DATA',
  messaging: 'MESSAGING',
  observability: 'OBSERVABILITY',
  network: 'NETWORK',
  other: 'OTHER',
};

function categorise(type: string): CategoryKey {
  if (
    type.startsWith('aws_iam_') ||
    type === 'aws_kms_key' ||
    type.startsWith('aws_secretsmanager_') ||
    type === 'aws_ssm_parameter'
  ) return 'identity';
  if (
    type === 'aws_s3_bucket' ||
    type === 'aws_db_instance' ||
    type.startsWith('aws_rds_') ||
    type === 'aws_dynamodb_table' ||
    type.startsWith('aws_elasticache_') ||
    type.startsWith('aws_redshift_')
  ) return 'data';
  if (type === 'aws_sqs_queue' || type === 'aws_sns_topic') return 'messaging';
  if (type.startsWith('aws_cloudwatch_')) return 'observability';
  if (type === 'aws_security_group' || type.startsWith('aws_route53_')) return 'network';
  return 'other';
}

const CAT_LABEL_H = 22;
const CAT_GAP = 20;
const CAT_PAD = 12;

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

  // 2. VPC + AZ + subnet zones (only when VPC has content)
  const vpcHasContent = subnetNodes.length > 0 || resourceToSubnet.size > 0;
  let regionalX = startX;

  if (vpcHasContent) {
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

    regionalX = startX + vpcContentW + VPC_REG_GAP;
  }

  // 3. Regional services — split by provider, then categorised sub-zones laid out in a grid
  if (regionalNodes.length > 0) {
    // Group regional nodes by provider so each provider gets its own regional zone
    const byProvider = new Map<Provider, ResourceNodeData[]>();
    for (const node of regionalNodes) {
      const prov = detectProvider(node.type);
      if (!byProvider.has(prov)) byProvider.set(prov, []);
      byProvider.get(prov)!.push(node);
    }

    // Emit providers in a stable order: aws first, then azurerm, then generic
    const providerOrder: Provider[] = ['aws', 'azurerm', 'generic'];
    let regXCursor = regionalX;

    for (const prov of providerOrder) {
      const provNodes = byProvider.get(prov);
      if (!provNodes || provNodes.length === 0) continue;

      // Use 'zone-regional' for aws (backward compat), provider-suffixed for others
      const zoneRegId = prov === 'aws' ? 'zone-regional' : `zone-regional-${prov}`;
      const zoneRegLabel = prov === 'aws'
        ? 'Regional Services (AWS)'
        : `Regional Services (${PROVIDER_THEMES[prov].label})`;

      type CatLayout = { key: CategoryKey; label: string; resources: ResourceNodeData[]; w: number; h: number; cols: number };

      const byCategory = new Map<CategoryKey, ResourceNodeData[]>();
      for (const node of provNodes) {
        const key = categorise(node.type);
        if (!byCategory.has(key)) byCategory.set(key, []);
        byCategory.get(key)!.push(node);
      }

      const catLayouts: CatLayout[] = [];
      for (const key of CATEGORY_ORDER) {
        const resources = byCategory.get(key);
        if (!resources || resources.length === 0) continue;
        const c = resources.length <= 3 ? 2 : resources.length <= 6 ? 2 : 3;
        const rows = Math.ceil(resources.length / c);
        const catW = c * (NODE_W + NODE_GAP) - NODE_GAP + 2 * CAT_PAD;
        const catH = CAT_LABEL_H + CAT_PAD + rows * (NODE_H + REG_ROW_GAP) - REG_ROW_GAP + CAT_PAD;
        catLayouts.push({ key, label: CATEGORY_LABELS[key], resources, w: catW, h: catH, cols: c });
      }

      // Non-AWS resources won't match CATEGORY_ORDER keys — emit them flat in an 'other' bucket
      if (catLayouts.length === 0) {
        const c = provNodes.length <= 3 ? 2 : provNodes.length <= 6 ? 2 : 3;
        const rows = Math.ceil(provNodes.length / c);
        const catW = c * (NODE_W + NODE_GAP) - NODE_GAP + 2 * CAT_PAD;
        const catH = CAT_LABEL_H + CAT_PAD + rows * (NODE_H + REG_ROW_GAP) - REG_ROW_GAP + CAT_PAD;
        catLayouts.push({ key: 'other', label: CATEGORY_LABELS['other'], resources: provNodes, w: catW, h: catH, cols: c });
      }

      // Arrange categories in a grid — 2 across when we have 3+ categories, 1 across for ≤2
      const catGridCols = catLayouts.length >= 3 ? 2 : 1;
      const colWidth = Math.max(...catLayouts.map(c => c.w));

      // Row heights = max category height in each row
      const rowHeights: number[] = [];
      for (let i = 0; i < catLayouts.length; i += catGridCols) {
        const rowCats = catLayouts.slice(i, i + catGridCols);
        rowHeights.push(Math.max(...rowCats.map(c => c.h)));
      }

      const regW =
        catGridCols * colWidth + Math.max(0, catGridCols - 1) * CAT_GAP + 2 * REG_PAD;
      const regH =
        REG_LABEL_H +
        REG_PAD +
        rowHeights.reduce((a, h) => a + h, 0) +
        Math.max(0, rowHeights.length - 1) * CAT_GAP +
        REG_PAD;

      flowNodes.push(makeZone(zoneRegId, zoneRegLabel, 'regional', regXCursor, vpcStartY, regW, regH));

      catLayouts.forEach((cat, idx) => {
        const gridRow = Math.floor(idx / catGridCols);
        const gridCol = idx % catGridCols;
        const catX = REG_PAD + gridCol * (colWidth + CAT_GAP);
        const catY =
          REG_LABEL_H +
          REG_PAD +
          rowHeights.slice(0, gridRow).reduce((a, h) => a + h, 0) +
          gridRow * CAT_GAP;

        const catId = `zone-category-${cat.key}`;
        flowNodes.push(makeZone(catId, cat.label, 'category', catX, catY, colWidth, cat.h, zoneRegId));

        // Centre resources horizontally within the fixed colWidth
        const contentW = cat.cols * (NODE_W + NODE_GAP) - NODE_GAP;
        const leftPad = (colWidth - contentW) / 2;

        cat.resources.forEach((n, i) => {
          const col = i % cat.cols;
          const row = Math.floor(i / cat.cols);
          flowNodes.push(makeResource(
            n,
            leftPad + col * (NODE_W + NODE_GAP),
            CAT_LABEL_H + CAT_PAD + row * (NODE_H + REG_ROW_GAP),
            catId,
          ));
        });
      });

      regXCursor += regW + VPC_REG_GAP;
    }
  }

  // 5. Wrap top-level zones in per-provider cloud containers
  const providerOfResource = (id: string): Provider => {
    const n = graph.nodes.find(gn => gn.id === id);
    if (!n) return 'generic';
    return detectProvider(n.type);
  };

  // Classify top-level zones (those without parentId) by provider
  type TopZone = { id: string; provider: Provider };
  const topZones: TopZone[] = [];

  // Collect all zone IDs that descend from a given top-level zone (direct children and their children)
  const descendantZoneIds = (parentId: string): string[] => {
    const result: string[] = [];
    for (const fn of flowNodes) {
      if (fn.type === 'group' && fn.parentId === parentId) {
        result.push(fn.id);
        result.push(...descendantZoneIds(fn.id));
      }
    }
    return result;
  };

  for (const fn of flowNodes) {
    if (fn.type !== 'group') continue;
    if (fn.parentId) continue; // already nested
    // Determine the provider by looking at the first resource that claims this zone or any
    // descendant zone as parent (resources may be nested under category sub-zones)
    const zoneFamily = [fn.id, ...descendantZoneIds(fn.id)];
    const child = flowNodes.find(c => c.type === 'resource' && zoneFamily.includes(c.parentId ?? ''));
    let prov: Provider = 'generic';
    if (child) prov = providerOfResource(child.id);
    topZones.push({ id: fn.id, provider: prov });
  }

  const providersSeen = new Set(topZones.map(t => t.provider));
  if (providersSeen.size === 0) {
    const flowEdges = buildEdges(graph.edges, graph.nodes, suppressedIds);
    return { nodes: flowNodes, edges: flowEdges };
  }

  // Build a bounding box per provider from their top-level zones
  type Box = { x: number; y: number; w: number; h: number };
  const boxOf = (id: string): Box => {
    const n = flowNodes.find(f => f.id === id)!;
    const w = (n.style?.width as number) ?? 0;
    const h = (n.style?.height as number) ?? 0;
    return { x: n.position.x, y: n.position.y, w, h };
  };

  let cloudXCursor = startX;
  const cloudYOrigin = 40;

  for (const prov of providersSeen) {
    const myZones = topZones.filter(t => t.provider === prov).map(t => t.id);
    if (myZones.length === 0) continue;

    const boxes = myZones.map(boxOf);
    const minX = Math.min(...boxes.map(b => b.x));
    const minY = Math.min(...boxes.map(b => b.y));
    const maxX = Math.max(...boxes.map(b => b.x + b.w));
    const maxY = Math.max(...boxes.map(b => b.y + b.h));

    const cloudW = maxX - minX + 2 * CLOUD_PAD;
    const cloudH = maxY - minY + CLOUD_LABEL_H + 2 * CLOUD_PAD;
    const cloudId = `zone-cloud-${prov}`;

    flowNodes.push(
      makeZone(cloudId, PROVIDER_THEMES[prov].label, 'cloud', cloudXCursor, cloudYOrigin, cloudW, cloudH),
    );

    // Reparent the top-level zones under the cloud and rewrite their positions relative to the cloud
    for (const zId of myZones) {
      const zone = flowNodes.find(f => f.id === zId)!;
      const origX = zone.position.x;
      const origY = zone.position.y;
      zone.parentId = cloudId;
      zone.extent = 'parent' as const;
      zone.position = {
        x: origX - minX + CLOUD_PAD,
        y: origY - minY + CLOUD_LABEL_H + CLOUD_PAD,
      };
    }

    cloudXCursor += cloudW + CLOUD_GAP;
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
