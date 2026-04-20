export type Severity = 'critical' | 'high' | 'medium' | 'info';

export type DriftStatus = 'unchanged' | 'added' | 'changed' | 'deleted' | 'shadow';

export interface Finding {
  rule_id: string;
  severity: Severity;
  title: string;
  description: string;
  remediation: string;
  evidence: Record<string, unknown>;
  source?: string;              // 'security' | 'policy'
  framework_ids?: string[];     // ['CIS-2.1.5', 'NIST-SC-7']
}

export interface NetworkFinding {
  source_ip: string;
  dest_ip: string;
  protocol: string;
  port: number;
  severity: Severity;
  title: string;
  description: string;
  remediation?: string;
  evidence?: Record<string, unknown>;
  // FDM-01: rule-engine-compatible extensions (mirror of Finding shape)
  rule_id?: string;
  source?: string;            // 'network'
  framework_ids?: string[];
  path_id?: string;
  hop_id?: string;
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

// FDM-01: FlowMap path + hop models (mirror of cli/infracanvas/graph/models.py)

export interface PathHop {
  hop_index: number;
  node_id: string;
  source_ip: string;
  dest_ip: string;
  protocol: string;
  port: number;
  interface_in: string;
  interface_out: string;
  bgp_as_path: number[];
  next_hop: string;
  evidence: Record<string, unknown>;
}

export interface NetworkPath {
  id: string;
  source_node_id: string;
  dest_node_id: string;
  direction: 'forward' | 'return';
  hops: PathHop[];
  evidence: Record<string, unknown>;
}

// FDM-02: DC collector models (populated in Phase 3b)

export interface DCCollectorReading {
  site_id: string;
  collector_type: 'router' | 'firewall' | 'checkpoint';
  collected_at: string;
  payload: Record<string, unknown>;
}

export interface DCSite {
  id: string;
  name: string;
  location: string;
  routers: string[];
  firewalls: string[];
  readings: DCCollectorReading[];
}

export interface ResourceGraph {
  version: string;
  metadata: GraphMetadata;
  nodes: ResourceNode[];
  edges: GraphEdge[];
  summary: GraphSummary;
  // FDM-01/FDM-02: populated in Phase 3b; empty arrays in Phase 3a.
  network_paths: NetworkPath[];
  dc_sites: DCSite[];
  // WRG-03 / D-13: optional marker section indicating the scan carried FlowMap
  // payload. Presence (any non-null / non-undefined value) toggles the
  // FlowMap tab's enabled state in the viewer. Exact shape is defined by the
  // CLI's --with-flowmap export; the viewer only checks existence.
  flowmap?: unknown;
}

declare global {
  interface Window {
    __INFRACANVAS_DATA__: ResourceGraph | null;
    __INFRACANVAS_GATE__: boolean | undefined;
  }
}
