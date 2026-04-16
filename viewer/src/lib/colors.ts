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
    style: { stroke: '#475569', strokeWidth: 1.5 },
    markerEnd: undefined,
    animated: false,
  },
  dependency: {
    style: { stroke: '#cbd5e1', strokeWidth: 1, strokeDasharray: '4 3' },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' },
    animated: false,
  },
  access: {
    style: { stroke: '#3b82f6', strokeWidth: 1, strokeDasharray: '6 4' },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#3b82f6' },
    animated: false,
    labelStyle: { fontSize: 10, fill: '#64748b' },
  },
};

// --- Tier-based zone colors ---

export type ZoneType =
  | 'internet'
  | 'vpc'
  | 'az'
  | 'public_subnet'
  | 'private_subnet'
  | 'data_subnet'
  | 'regional';

export const ZONE_COLORS: Record<ZoneType, {
  background: string;
  border: string;
  label: string;
}> = {
  internet: {
    background: 'rgba(100, 116, 139, 0.04)',
    border: 'rgba(100, 116, 139, 0.25)',
    label: '#64748b',
  },
  vpc: {
    background: 'rgba(119, 91, 163, 0.06)',
    border: 'rgba(119, 91, 163, 0.45)',
    label: '#7B5EA7',
  },
  az: {
    background: 'transparent',
    border: 'rgba(100, 116, 139, 0.20)',
    label: '#64748b',
  },
  public_subnet: {
    background: 'rgba(0, 153, 77, 0.05)',
    border: 'rgba(0, 153, 77, 0.35)',
    label: '#16a34a',
  },
  private_subnet: {
    background: 'rgba(0, 115, 187, 0.05)',
    border: 'rgba(0, 115, 187, 0.32)',
    label: '#0369a1',
  },
  data_subnet: {
    background: 'rgba(140, 79, 255, 0.05)',
    border: 'rgba(140, 79, 255, 0.28)',
    label: '#7c3aed',
  },
  regional: {
    background: 'rgba(50, 80, 130, 0.04)',
    border: 'rgba(73, 144, 200, 0.28)',
    label: '#2563eb',
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
