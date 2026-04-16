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
    background: 'rgba(100, 116, 139, 0.08)',
    border: 'rgba(100, 116, 139, 0.25)',
    label: '#94a3b8',
  },
  vpc: {
    background: 'rgba(30, 41, 59, 0.60)',
    border: 'rgba(59, 130, 246, 0.35)',
    label: '#60a5fa',
  },
  az: {
    background: 'transparent',
    border: 'rgba(100, 116, 139, 0.30)',
    label: '#94a3b8',
  },
  public_subnet: {
    background: 'rgba(34, 197, 94, 0.07)',
    border: 'rgba(34, 197, 94, 0.30)',
    label: '#4ade80',
  },
  private_subnet: {
    background: 'rgba(59, 130, 246, 0.07)',
    border: 'rgba(59, 130, 246, 0.30)',
    label: '#60a5fa',
  },
  data_subnet: {
    background: 'rgba(168, 85, 247, 0.07)',
    border: 'rgba(168, 85, 247, 0.30)',
    label: '#c084fc',
  },
  regional: {
    background: 'rgba(30, 41, 59, 0.40)',
    border: 'rgba(100, 116, 139, 0.25)',
    label: '#94a3b8',
  },
};

const resourceTypeColors: Record<string, string> = {
  aws_vpc: '#3b82f6',
  aws_subnet: '#06b6d4',
  aws_security_group: '#ef4444',
  aws_instance: '#f97316',
  aws_s3_bucket: '#22c55e',
  aws_rds_instance: '#a855f7',
  aws_db_instance: '#a855f7',
  aws_lambda_function: '#eab308',
  aws_alb: '#6366f1',
  aws_lb: '#6366f1',
  aws_kms_key: '#ec4899',
  aws_iam_role: '#64748b',
  aws_iam_policy: '#64748b',
  aws_cloudfront_distribution: '#0ea5e9',
  aws_dynamodb_table: '#14b8a6',
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
