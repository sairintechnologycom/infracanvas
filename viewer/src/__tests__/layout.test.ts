import { describe, test, expect } from 'vitest';
import { buildFlowElements } from '../lib/layout';
import type { ResourceGraph, ResourceNode } from '../types';

function makeGraph(nodes: ResourceNode[]): ResourceGraph {
  return {
    version: '1.0',
    nodes,
    edges: [],
    summary: {
      total_resources: nodes.length,
      score: 100,
      findings: { critical: 0, high: 0, medium: 0, info: 0 },
      drift: { added: 0, changed: 0, deleted: 0 },
      estimated_monthly_cost: 0,
    },
    metadata: {
      scan_id: 'test-scan',
      project: 'test',
      provider: 'aws',
      scanned_at: '2026-04-17T00:00:00Z',
      terraform_version: '1.5.0',
    },
  };
}

function makeNode(id: string, type: string, name: string): ResourceNode {
  return {
    id, type, name,
    provider: 'aws',
    module: '',
    region: 'us-east-1',
    group: '',
    attributes: {},
    dependencies: [],
    findings: [],
    cost: { monthly_usd: 0, currency: 'USD', basis: '' },
    drift: 'unchanged',
    position: { x: 0, y: 0 },
  };
}

describe('buildFlowElements — VPC suppression', () => {
  test('omits zone-vpc when VPC has no subnets and no VPC-placed resources', () => {
    const graph = makeGraph([
      makeNode('aws_vpc.main', 'aws_vpc', 'main'),
      makeNode('aws_s3_bucket.logs', 'aws_s3_bucket', 'logs'),
      makeNode('aws_kms_key.key', 'aws_kms_key', 'key'),
    ]);
    const { nodes } = buildFlowElements(graph);
    expect(nodes.find(n => n.id === 'zone-vpc')).toBeUndefined();
    expect(nodes.find(n => n.id === 'zone-regional')).toBeDefined();
  });

  test('emits zone-vpc when subnets exist', () => {
    const subnet = makeNode('aws_subnet.pub', 'aws_subnet', 'pub');
    subnet.attributes = { cidr_block: '10.0.1.0/24', map_public_ip_on_launch: true };
    const graph = makeGraph([
      makeNode('aws_vpc.main', 'aws_vpc', 'main'),
      subnet,
    ]);
    const { nodes } = buildFlowElements(graph);
    expect(nodes.find(n => n.id === 'zone-vpc')).toBeDefined();
  });
});

describe('buildFlowElements — regional categorisation', () => {
  test('groups regional resources into category sub-zones', () => {
    const graph = makeGraph([
      makeNode('aws_iam_policy.admin', 'aws_iam_policy', 'admin'),
      makeNode('aws_kms_key.key', 'aws_kms_key', 'key'),
      makeNode('aws_s3_bucket.logs', 'aws_s3_bucket', 'logs'),
      makeNode('aws_db_instance.db', 'aws_db_instance', 'db'),
    ]);
    const { nodes } = buildFlowElements(graph);

    const categoryZones = nodes.filter(
      n => typeof n.id === 'string' && n.id.startsWith('zone-category-'),
    );
    const labels = categoryZones.map(n => (n.data as { label: string }).label);
    expect(labels).toContain('IDENTITY & ACCESS');
    expect(labels).toContain('DATA');
  });

  test('orders categories: identity, data, messaging, observability, network, other', () => {
    const graph = makeGraph([
      makeNode('aws_sns_topic.t', 'aws_sns_topic', 't'),
      makeNode('aws_s3_bucket.b', 'aws_s3_bucket', 'b'),
      makeNode('aws_iam_policy.p', 'aws_iam_policy', 'p'),
    ]);
    const { nodes } = buildFlowElements(graph);
    const categoryZones = nodes
      .filter(n => typeof n.id === 'string' && n.id.startsWith('zone-category-'))
      .sort((a, b) => a.position.y - b.position.y)
      .map(n => (n.data as { label: string }).label);
    expect(categoryZones).toEqual(['IDENTITY & ACCESS', 'DATA', 'MESSAGING']);
  });
});
