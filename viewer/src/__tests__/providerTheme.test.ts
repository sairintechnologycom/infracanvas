import { describe, test, expect } from 'vitest';
import { detectProvider, primaryProviderOf, PROVIDER_THEMES } from '../lib/providerTheme';

describe('detectProvider', () => {
  test('recognises AWS types', () => {
    expect(detectProvider('aws_s3_bucket')).toBe('aws');
    expect(detectProvider('aws_iam_policy')).toBe('aws');
  });

  test('recognises Azure types', () => {
    expect(detectProvider('azurerm_storage_account')).toBe('azurerm');
    expect(detectProvider('azurerm_virtual_network')).toBe('azurerm');
  });

  test('falls back to generic for unknown', () => {
    expect(detectProvider('google_compute_instance')).toBe('generic');
    expect(detectProvider('')).toBe('generic');
  });
});

describe('primaryProviderOf', () => {
  test('picks the majority provider', () => {
    expect(primaryProviderOf([
      { type: 'aws_s3_bucket' },
      { type: 'aws_iam_policy' },
      { type: 'azurerm_storage_account' },
    ])).toBe('aws');
  });

  test('handles single-provider graphs', () => {
    expect(primaryProviderOf([
      { type: 'azurerm_virtual_network' },
    ])).toBe('azurerm');
  });

  test('handles empty list', () => {
    expect(primaryProviderOf([])).toBe('generic');
  });
});

describe('PROVIDER_THEMES', () => {
  test('has entries for all three providers', () => {
    expect(PROVIDER_THEMES.aws.label).toBe('AWS Cloud');
    expect(PROVIDER_THEMES.azurerm.label).toBe('Microsoft Azure');
    expect(PROVIDER_THEMES.generic.label).toBe('Cloud');
  });

  test('each theme specifies iconKind', () => {
    expect(PROVIDER_THEMES.aws.iconKind).toBe('aws');
    expect(PROVIDER_THEMES.azurerm.iconKind).toBe('azure');
    expect(PROVIDER_THEMES.generic.iconKind).toBe('geometric');
  });
});
