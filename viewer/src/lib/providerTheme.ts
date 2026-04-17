export type Provider = 'aws' | 'azurerm' | 'generic';

export const PROVIDER_THEMES: Record<Provider, {
  label: string;
  cloudColor: string;
  accentColor: string;
  iconKind: 'aws' | 'azure' | 'geometric';
}> = {
  aws: {
    label: 'AWS Cloud',
    cloudColor: '#E7157B',
    accentColor: '#FF9900',
    iconKind: 'aws',
  },
  azurerm: {
    label: 'Microsoft Azure',
    cloudColor: '#0078D4',
    accentColor: '#0078D4',
    iconKind: 'azure',
  },
  generic: {
    label: 'Cloud',
    cloudColor: '#64748B',
    accentColor: '#64748B',
    iconKind: 'geometric',
  },
};

export function detectProvider(type: string): Provider {
  if (type.startsWith('aws_')) return 'aws';
  if (type.startsWith('azurerm_')) return 'azurerm';
  return 'generic';
}

export function primaryProviderOf(nodes: { type: string }[]): Provider {
  if (nodes.length === 0) return 'generic';
  const counts: Record<Provider, number> = { aws: 0, azurerm: 0, generic: 0 };
  for (const n of nodes) counts[detectProvider(n.type)]++;
  const winner = (Object.entries(counts) as [Provider, number][])
    .sort((a, b) => b[1] - a[1])[0][0];
  return winner;
}
