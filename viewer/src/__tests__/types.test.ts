import { describe, it, expect } from 'vitest';
import { sampleData } from '../sample-data';
import type { ResourceGraph, ResourceNode, Finding, GraphSummary } from '../types';

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
