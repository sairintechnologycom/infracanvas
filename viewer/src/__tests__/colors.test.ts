import { describe, it, expect } from 'vitest';
import { getResourceColor, getHighestSeverity, severityColors, driftColors, ZONE_COLORS } from '../lib/colors';

describe('getResourceColor', () => {
  it('returns correct color for known types', () => {
    expect(getResourceColor('aws_vpc')).toBe('#8C4FFF');          // Networking
    expect(getResourceColor('aws_s3_bucket')).toBe('#3F8624');    // Storage
    expect(getResourceColor('aws_instance')).toBe('#FF9900');     // Compute
    expect(getResourceColor('aws_lambda_function')).toBe('#FF9900'); // Compute
  });

  it('returns default gray for non-AWS types', () => {
    expect(getResourceColor('google_compute_instance')).toBe('#94a3b8');
    expect(getResourceColor('azurerm_virtual_network')).toBe('#94a3b8');
  });
});

describe('getHighestSeverity', () => {
  it('returns null for empty findings', () => {
    expect(getHighestSeverity([])).toBeNull();
  });

  it('returns critical when present', () => {
    const findings = [
      { severity: 'info' as const },
      { severity: 'critical' as const },
      { severity: 'high' as const },
    ];
    expect(getHighestSeverity(findings)).toBe('critical');
  });

  it('returns high when no critical', () => {
    const findings = [
      { severity: 'info' as const },
      { severity: 'high' as const },
    ];
    expect(getHighestSeverity(findings)).toBe('high');
  });

  it('returns medium when no critical or high', () => {
    const findings = [{ severity: 'medium' as const }];
    expect(getHighestSeverity(findings)).toBe('medium');
  });

  it('returns info when only info', () => {
    const findings = [{ severity: 'info' as const }];
    expect(getHighestSeverity(findings)).toBe('info');
  });
});

describe('severityColors', () => {
  it('E-002/E-003: has correct colors for all severities', () => {
    expect(severityColors.critical).toBe('#ef4444');
    expect(severityColors.high).toBe('#f97316');
    expect(severityColors.medium).toBe('#f59e0b');
    expect(severityColors.info).toBe('#3b82f6');
    expect(severityColors.clean).toBe('#22c55e');
  });
});

describe('driftColors', () => {
  it('E-004: has correct drift colors', () => {
    expect(driftColors.unchanged).toBe('#1e293b');
    expect(driftColors.added).toBe('#22c55e');
    expect(driftColors.changed).toBe('#f59e0b');
    expect(driftColors.deleted).toBe('#ef4444');
  });
});

describe('ZONE_COLORS', () => {
  it('includes category zone type', () => {
    expect(ZONE_COLORS.category).toBeDefined();
    expect(ZONE_COLORS.category.pillText).toBe('#94a3b8');
  });
});
