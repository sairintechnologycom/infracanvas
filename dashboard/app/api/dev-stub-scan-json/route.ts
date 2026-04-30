import { NextRequest, NextResponse } from 'next/server'
import type { ResourceGraph } from '@infracanvas/viewer'

const DEV_BYPASS = process.env.DEV_BYPASS_AUTH === '1'

function buildStubGraph(scanId: string): ResourceGraph {
  return {
    version: '1.0',
    metadata: {
      scan_id: scanId,
      project: 'demo-stack',
      provider: 'aws',
      scanned_at: '2026-04-29T08:30:00Z',
      terraform_version: '1.7.0',
    },
    nodes: [
      {
        id: 'aws_vpc.main',
        type: 'aws_vpc',
        name: 'main',
        provider: 'aws',
        module: 'root',
        region: 'us-east-1',
        group: 'network',
        attributes: { cidr_block: '10.0.0.0/16' },
        dependencies: [],
        findings: [],
        cost: { monthly_usd: 0, currency: 'USD', basis: 'free-tier' },
        drift: 'unchanged',
        position: { x: 0, y: 0 },
      },
      {
        id: 'aws_security_group.web',
        type: 'aws_security_group',
        name: 'web',
        provider: 'aws',
        module: 'root',
        region: 'us-east-1',
        group: 'network',
        attributes: { ingress: '0.0.0.0/0:22' },
        dependencies: ['aws_vpc.main'],
        findings: [
          {
            rule_id: 'SEC-014',
            severity: 'critical',
            title: 'SSH open to the world',
            description: 'Security group allows inbound 0.0.0.0/0 on port 22.',
            remediation: 'Restrict ingress to bastion CIDR only.',
            evidence: { ingress_cidr: '0.0.0.0/0', port: 22 },
            source: 'security',
          },
        ],
        cost: { monthly_usd: 0, currency: 'USD', basis: 'free-tier' },
        drift: 'changed',
        position: { x: 220, y: 0 },
      },
      {
        id: 'aws_instance.api',
        type: 'aws_instance',
        name: 'api',
        provider: 'aws',
        module: 'root',
        region: 'us-east-1',
        group: 'compute',
        attributes: { instance_type: 't3.medium' },
        dependencies: ['aws_security_group.web', 'aws_vpc.main'],
        findings: [
          {
            rule_id: 'SEC-022',
            severity: 'high',
            title: 'Instance metadata v1 enabled',
            description: 'IMDSv1 is permissive and SSRF-prone.',
            remediation: 'Set http_tokens = "required" for IMDSv2.',
            evidence: { http_tokens: 'optional' },
            source: 'security',
          },
        ],
        cost: { monthly_usd: 30.4, currency: 'USD', basis: 'on-demand' },
        drift: 'unchanged',
        position: { x: 440, y: 0 },
      },
      {
        id: 'aws_s3_bucket.logs',
        type: 'aws_s3_bucket',
        name: 'logs',
        provider: 'aws',
        module: 'root',
        region: 'us-east-1',
        group: 'storage',
        attributes: { versioning: false },
        dependencies: [],
        findings: [],
        cost: { monthly_usd: 4.2, currency: 'USD', basis: 'standard' },
        drift: 'added',
        position: { x: 220, y: 160 },
      },
    ],
    edges: [
      { source: 'aws_security_group.web', target: 'aws_vpc.main', type: 'implicit' },
      { source: 'aws_instance.api', target: 'aws_security_group.web', type: 'implicit' },
      { source: 'aws_instance.api', target: 'aws_vpc.main', type: 'implicit' },
    ],
    summary: {
      total_resources: 4,
      findings: { critical: 1, high: 1, medium: 0, info: 0 },
      estimated_monthly_cost: 34.6,
      score: 87,
      drift: { added: 1, changed: 1, deleted: 0 },
    },
    network_paths: [],
    dc_sites: [],
  }
}

export async function GET(req: NextRequest) {
  if (!DEV_BYPASS) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 })
  }
  const id = req.nextUrl.searchParams.get('id') ?? 'stub-scan'
  return NextResponse.json(buildStubGraph(id))
}
