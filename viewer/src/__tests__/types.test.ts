import { describe, it, expect, test } from 'vitest';
import { sampleData } from '../sample-data';
import type {
  DCCollectorReading,
  DCSite,
  Finding,
  GraphSummary,
  NetworkPath,
  PathHop,
  ResourceGraph,
  ResourceNode,
} from '../types';

describe('Types conformance', () => {
  it('E-010: sample-data matches ResourceGraph shape', () => {
    const graph: ResourceGraph = sampleData;

    // Top-level fields
    expect(graph.version).toBeDefined();
    expect(graph.metadata).toBeDefined();
    expect(graph.nodes).toBeDefined();
    expect(graph.edges).toBeDefined();
    expect(graph.summary).toBeDefined();

    // Metadata fields
    expect(graph.metadata.scan_id).toBeDefined();
    expect(graph.metadata.project).toBeDefined();
    expect(graph.metadata.provider).toBeDefined();
    expect(graph.metadata.scanned_at).toBeDefined();
    expect(graph.metadata.terraform_version).toBeDefined();
  });

  it('nodes have all required fields', () => {
    for (const node of sampleData.nodes) {
      const n: ResourceNode = node;
      expect(n.id).toBeDefined();
      expect(n.type).toBeDefined();
      expect(n.name).toBeDefined();
      expect(n.provider).toBeDefined();
      expect(typeof n.module).toBe('string');
      expect(typeof n.region).toBe('string');
      expect(typeof n.group).toBe('string');
      expect(n.attributes).toBeDefined();
      expect(Array.isArray(n.dependencies)).toBe(true);
      expect(Array.isArray(n.findings)).toBe(true);
      expect(n.cost).toBeDefined();
      expect(n.cost.monthly_usd).toBeDefined();
      expect(n.drift).toBeDefined();
      expect(n.position).toBeDefined();
    }
  });

  it('findings have all required fields', () => {
    const nodesWithFindings = sampleData.nodes.filter(n => n.findings.length > 0);
    expect(nodesWithFindings.length).toBeGreaterThan(0);

    for (const node of nodesWithFindings) {
      for (const finding of node.findings) {
        const f: Finding = finding;
        expect(f.rule_id).toBeDefined();
        expect(f.severity).toBeDefined();
        expect(f.title).toBeDefined();
        expect(f.description).toBeDefined();
        expect(f.remediation).toBeDefined();
        expect(f.evidence).toBeDefined();
      }
    }
  });

  it('summary has all required fields', () => {
    const s: GraphSummary = sampleData.summary;
    expect(s.total_resources).toBeDefined();
    expect(s.findings.critical).toBeDefined();
    expect(s.findings.high).toBeDefined();
    expect(s.findings.medium).toBeDefined();
    expect(s.findings.info).toBeDefined();
    expect(s.estimated_monthly_cost).toBeDefined();
    expect(s.score).toBeDefined();
    expect(s.drift).toBeDefined();
  });

  it('edges have correct type values', () => {
    for (const edge of sampleData.edges) {
      expect(edge.source).toBeDefined();
      expect(edge.target).toBeDefined();
      expect(['implicit', 'explicit', 'depends_on']).toContain(edge.type);
    }
  });

  it('severity values are valid', () => {
    const validSeverities = ['critical', 'high', 'medium', 'info'];
    for (const node of sampleData.nodes) {
      for (const f of node.findings) {
        expect(validSeverities).toContain(f.severity);
      }
    }
  });

  it('drift values are valid', () => {
    const validDrift = ['unchanged', 'added', 'changed', 'deleted'];
    for (const node of sampleData.nodes) {
      expect(validDrift).toContain(node.drift);
    }
  });
});

describe('FlowMap types (FDM-01, FDM-02)', () => {
  test('NetworkPath compiles with required fields', () => {
    const p: NetworkPath = {
      id: 'p1',
      source_node_id: 'a',
      dest_node_id: 'b',
      direction: 'forward',
      hops: [],
      evidence: {},
    };
    expect(p.direction).toBe('forward');
    expect(p.hops).toEqual([]);
  });

  test('PathHop compiles with required fields', () => {
    const h: PathHop = {
      hop_index: 0,
      node_id: 'vpc-rt-1',
      source_ip: '10.0.0.1',
      dest_ip: '10.1.0.1',
      protocol: 'tcp',
      port: 443,
      interface_in: 'eth0',
      interface_out: 'eth1',
      bgp_as_path: [],
      next_hop: '',
      evidence: {},
    };
    expect(h.port).toBe(443);
  });

  test('DCCollectorReading compiles with required fields', () => {
    const r: DCCollectorReading = {
      site_id: 'dc-nyc',
      collector_type: 'router',
      collected_at: '2026-04-18T10:00:00Z',
      payload: {},
    };
    expect(r.collector_type).toBe('router');
  });

  test('DCSite compiles with required fields', () => {
    const s: DCSite = {
      id: 'dc-nyc',
      name: 'New York DC',
      location: 'NYC',
      routers: [],
      firewalls: [],
      readings: [],
    };
    expect(s.name).toBe('New York DC');
  });

  test('ResourceGraph accepts network_paths and dc_sites', () => {
    const g: Partial<ResourceGraph> = { network_paths: [], dc_sites: [] };
    expect(g.network_paths).toEqual([]);
    expect(g.dc_sites).toEqual([]);
  });

  test('sampleData includes empty network_paths and dc_sites arrays', () => {
    expect(sampleData.network_paths).toEqual([]);
    expect(sampleData.dc_sites).toEqual([]);
  });
});
