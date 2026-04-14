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
};

export const edgeColors: Record<string, string> = {
  implicit: '#475569',
  explicit: '#3b82f6',
  depends_on: '#f97316',
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
