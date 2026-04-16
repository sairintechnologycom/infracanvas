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
    style: { stroke: '#334155', strokeWidth: 1, strokeDasharray: '4 3' },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#475569' },
    animated: false,
  },
  access: {
    style: { stroke: '#1e3a5f', strokeWidth: 1, strokeDasharray: '6 4' },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#1e3a5f' },
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
    background: 'rgba(100, 120, 160, 0.05)',
    border: 'rgba(140, 160, 200, 0.28)',
    label: '#8fa8cc',
  },
  vpc: {
    background: 'rgba(119, 91, 163, 0.10)',
    border: 'rgba(119, 91, 163, 0.55)',
    label: '#a882dc',
  },
  az: {
    background: 'transparent',
    border: 'rgba(140, 155, 180, 0.28)',
    label: '#7a92b4',
  },
  public_subnet: {
    background: 'rgba(0, 153, 77, 0.07)',
    border: 'rgba(0, 153, 77, 0.40)',
    label: '#2ecc71',
  },
  private_subnet: {
    background: 'rgba(0, 115, 187, 0.07)',
    border: 'rgba(0, 115, 187, 0.38)',
    label: '#4a9fd4',
  },
  data_subnet: {
    background: 'rgba(140, 79, 255, 0.07)',
    border: 'rgba(140, 79, 255, 0.32)',
    label: '#a07ddb',
  },
  regional: {
    background: 'rgba(50, 80, 130, 0.07)',
    border: 'rgba(73, 144, 200, 0.30)',
    label: '#6ba3cc',
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
