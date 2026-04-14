export type Severity = 'critical' | 'high' | 'medium' | 'info';

export type DriftStatus = 'unchanged' | 'added' | 'changed' | 'deleted';

export interface Finding {
  rule_id: string;
  severity: Severity;
  title: string;
  description: string;
  remediation: string;
  evidence: Record<string, unknown>;
}

export interface CostEstimate {
  monthly_usd: number;
  currency: string;
  basis: string;
}

export interface AttributeChange {
  attribute: string;
  before: unknown;
  after: unknown;
  sensitive: boolean;
}

export interface ResourceNode {
  id: string;
  type: string;
  name: string;
  provider: string;
  module: string;
  region: string;
  group: string;
  attributes: Record<string, unknown>;
  dependencies: string[];
  findings: Finding[];
  cost: CostEstimate;
  drift: DriftStatus;
  drift_changes?: AttributeChange[];
  position: { x: number; y: number };
}

export interface GraphEdge {
  source: string;
  target: string;
  type: 'implicit' | 'explicit' | 'depends_on';
}

export interface GraphSummary {
  total_resources: number;
  findings: Record<Severity, number>;
  estimated_monthly_cost: number;
  score: number;
  drift: { added: number; changed: number; deleted: number };
}

export interface GraphMetadata {
  scan_id: string;
  project: string;
  provider: string;
  scanned_at: string;
  terraform_version: string;
}

export interface ResourceGraph {
  version: string;
  metadata: GraphMetadata;
  nodes: ResourceNode[];
  edges: GraphEdge[];
  summary: GraphSummary;
}

declare global {
  interface Window {
    __INFRACANVAS_DATA__: ResourceGraph | null;
  }
}
