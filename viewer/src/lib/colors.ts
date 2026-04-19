import { MarkerType } from '@xyflow/react';
import type { DriftStatus, Severity } from '../types';

export const severityColors: Record<Severity | 'clean', string> = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#f59e0b',
  info: '#3b82f6',
  clean: '#22c55e',
};

export const driftColors: Record<DriftStatus, string> = {
  unchanged: '#1e293b',
  added: '#22c55e',
  changed: '#f59e0b',
  deleted: '#ef4444',
  shadow: '#d97706',
};

export const edgeColors: Record<string, string> = {
  implicit: '#475569',
  explicit: '#3b82f6',
  depends_on: '#f97316',
};

export type EdgeRelationship = 'containment' | 'attachment' | 'dependency' | 'access';

export const EDGE_STYLES: Record<EdgeRelationship, null | {
  style: Record<string, unknown>;
  markerEnd?: { type: MarkerType; color: string };
  animated: boolean;
  labelStyle?: Record<string, unknown>;
}> = {
  containment: null,
  attachment: {
    // traffic — solid arrow
    style: { stroke: 'rgba(71,85,105,0.6)', strokeWidth: 1.5 },
    markerEnd: { type: MarkerType.ArrowClosed, color: 'rgba(71,85,105,0.6)' },
    animated: false,
  },
  dependency: {
    // security — short dash, red tint
    style: { stroke: 'rgba(221,52,76,0.4)', strokeWidth: 1, strokeDasharray: '3 2' },
    markerEnd: undefined,
    animated: false,
  },
  access: {
    // access — medium dash, blue
    style: { stroke: 'rgba(59,130,246,0.45)', strokeWidth: 1.5, strokeDasharray: '5 3' },
    markerEnd: { type: MarkerType.ArrowClosed, color: 'rgba(59,130,246,0.45)' },
    animated: false,
    labelStyle: { fontSize: 10, fill: '#4a5568' },
  },
};

// --- Tier-based zone colors ---

export type ZoneType =
  | 'cloud'
  | 'region'
  | 'internet'
  | 'vpc'
  | 'az'
  | 'public_subnet'
  | 'private_subnet'
  | 'data_subnet'
  | 'regional'
  | 'category';

export const ZONE_COLORS: Record<ZoneType, {
  background: string;
  border: string;
  label: string;
  pill: string;
  pillBorder: string;
  pillText: string;
  borderWidth: string;
  borderStyle: string;
}> = {
  cloud: {
    // AWS reference: transparent interior, orange dashed boundary, label tab in corner
    background: 'transparent',
    border: 'rgba(255,153,0,0.7)',
    label: '#D97706',
    pill: 'transparent',
    pillBorder: 'transparent',
    pillText: '#D97706',
    borderWidth: '1.5px',
    borderStyle: 'dashed',
  },
  region: {
    background: 'transparent',
    border: 'rgba(100,116,139,0.5)',
    label: '#475569',
    pill: 'transparent',
    pillBorder: 'transparent',
    pillText: '#475569',
    borderWidth: '1px',
    borderStyle: 'dashed',
  },
  internet: {
    background: 'transparent',
    border: 'rgba(100,116,139,0.55)',
    label: '#475569',
    pill: 'transparent',
    pillBorder: 'transparent',
    pillText: '#475569',
    borderWidth: '1.5px',
    borderStyle: 'dashed',
  },
  vpc: {
    // VPC — AWS purple, transparent
    background: 'transparent',
    border: 'rgba(140,79,255,0.55)',
    label: '#7C3AED',
    pill: 'transparent',
    pillBorder: 'transparent',
    pillText: '#7C3AED',
    borderWidth: '1.5px',
    borderStyle: 'dashed',
  },
  az: {
    background: 'transparent',
    border: 'rgba(148,163,184,0.5)',
    label: '#64748B',
    pill: 'transparent',
    pillBorder: 'transparent',
    pillText: '#64748B',
    borderWidth: '1px',
    borderStyle: 'dashed',
  },
  public_subnet: {
    background: 'transparent',
    border: 'rgba(34,197,94,0.55)',
    label: '#16A34A',
    pill: 'transparent',
    pillBorder: 'transparent',
    pillText: '#16A34A',
    borderWidth: '1.25px',
    borderStyle: 'dashed',
  },
  private_subnet: {
    background: 'transparent',
    border: 'rgba(59,130,246,0.55)',
    label: '#2563EB',
    pill: 'transparent',
    pillBorder: 'transparent',
    pillText: '#2563EB',
    borderWidth: '1.25px',
    borderStyle: 'dashed',
  },
  data_subnet: {
    background: 'transparent',
    border: 'rgba(168,85,247,0.55)',
    label: '#9333EA',
    pill: 'transparent',
    pillBorder: 'transparent',
    pillText: '#9333EA',
    borderWidth: '1.25px',
    borderStyle: 'dashed',
  },
  regional: {
    // Regional services boundary — transparent, slate dashed outline
    background: 'transparent',
    border: 'rgba(100,116,139,0.45)',
    label: '#475569',
    pill: 'transparent',
    pillBorder: 'transparent',
    pillText: '#475569',
    borderWidth: '1.25px',
    borderStyle: 'dashed',
  },
  category: {
    background: 'transparent',
    border: 'rgba(148,163,184,0.4)',
    label: '#64748B',
    pill: 'transparent',
    pillBorder: 'transparent',
    pillText: '#64748B',
    borderWidth: '1px',
    borderStyle: 'dashed',
  },
};

const resourceTypeColors: Record<string, string> = {
  // Compute — AWS orange
  aws_instance:              '#FF9900',
  aws_lambda_function:       '#FF9900',
  // Storage — AWS green
  aws_s3_bucket:             '#3F8624',
  // Database — AWS blue
  aws_rds_instance:          '#2E73B8',
  aws_db_instance:           '#2E73B8',
  aws_dynamodb_table:        '#2E73B8',
  // Networking — AWS purple
  aws_vpc:                   '#8C4FFF',
  aws_subnet:                '#8C4FFF',
  aws_alb:                   '#8C4FFF',
  aws_lb:                    '#8C4FFF',
  aws_internet_gateway:      '#8C4FFF',
  aws_nat_gateway:           '#8C4FFF',
  aws_eip:                   '#8C4FFF',
  // Security — AWS red
  aws_security_group:        '#DD344C',
  aws_kms_key:               '#DD344C',
  aws_iam_role:              '#DD344C',
  aws_iam_policy:            '#DD344C',
  // CDN
  aws_cloudfront_distribution: '#7B2FBE',
};

export function getResourceColor(resourceType: string): string {
  if (resourceTypeColors[resourceType]) return resourceTypeColors[resourceType];
  // Prefix matching for families
  for (const [prefix, color] of Object.entries(resourceTypeColors)) {
    if (resourceType.startsWith(prefix.replace(/_[^_]+$/, ''))) return color;
  }
  return '#94a3b8';
}

export function getHighestSeverity(findings: { severity: Severity }[]): Severity | null {
  if (findings.length === 0) return null;
  const order: Severity[] = ['critical', 'high', 'medium', 'info'];
  for (const sev of order) {
    if (findings.some(f => f.severity === sev)) return sev;
  }
  return null;
}

// FlowMap Phase 3a additions — path + flow-log color tokens
// Kept as a const-as-assertion so TypeScript narrows each key to its literal hex.
export const flowmapPathColors = {
  forward:    '#3B82F6',
  return:     '#F97316',
  divergence: '#EF4444',
  flowOk:     '#22C55E',
  flowStale:  '#94A3B8',
} as const;
