# Viewer Light / AWS Architecture Style Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the dark "cyberpunk" viewer with a provider-aware light AWS-architecture-style canvas — real service icons, clean nodes, dashed cloud/VPC/subnet zone borders.

**Architecture:** Provider registry (`providerTheme.ts`) dispatches visuals off `node.provider`. Light `ZONE_COLORS`, a new `ServiceIcon` dispatch component that picks AWS brand icons (from `aws-react-icons`, already installed), Azure inline SVG components (curated ~12), or geometric fallback. Layout adds outermost `zone-cloud-<provider>` containers. No hardcoded cloud branching anywhere.

**Tech Stack:** React 18, TypeScript 5.8, @xyflow/react 12, Vite 6 (single-file bundle, `assetsInlineLimit: 100000000`), Tailwind 4, Vitest, `aws-react-icons` 3.3.

**Spec:** `docs/superpowers/specs/2026-04-17-viewer-light-aws-style-design.md`

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `viewer/src/lib/providerTheme.ts` | Provider registry + detection helpers | Create |
| `viewer/src/__tests__/providerTheme.test.ts` | Provider registry tests | Create |
| `viewer/src/lib/colors.ts` | Zone + resource colour palette | Rewrite `ZONE_COLORS` for light; add `cloud` + `region` zone types |
| `viewer/src/icons/awsIconMap.ts` | Maps `aws_*` terraform types → `aws-react-icons` component | Create |
| `viewer/src/icons/azure/` | Curated Azure SVG components (one file per service) | Create (12 files) |
| `viewer/src/icons/azureIconMap.ts` | Maps `azurerm_*` types → Azure SVG component | Create |
| `viewer/src/components/icons/ServiceIcon.tsx` | Unified icon dispatcher | Create |
| `viewer/src/__tests__/ServiceIcon.test.tsx` | Dispatch tests | Create |
| `viewer/src/components/ResourceNode.tsx` | Node card | Rewrite body for light + `<ServiceIcon>` |
| `viewer/src/components/GroupNode.tsx` | Zone container | Minor: tint label text for light bg |
| `viewer/src/components/DiagramCanvas.tsx` | ReactFlow wrapper | Swap background colour + dot colour; update minimap palette |
| `viewer/src/lib/layout.ts` | Graph → ReactFlow nodes | Wrap top-level zones in per-provider `zone-cloud-<provider>`; update edge style palette |
| `viewer/src/__tests__/layout.test.ts` | Layout tests | Extend with cloud-wrapper test |
| `viewer/src/components/SummaryBar.tsx` | Header | Minor: update edge-legend palette to match new edge colours |
| `cli/infracanvas/export/viewer_template.html` | CLI-served HTML template | Sync built bundle |

---

## Task 1: Provider theming registry + detection

**Files:**
- Create: `viewer/src/lib/providerTheme.ts`
- Create: `viewer/src/__tests__/providerTheme.test.ts`

- [ ] **Step 1: Write failing tests**

Create `viewer/src/__tests__/providerTheme.test.ts`:

```ts
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
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd viewer && npm run test -- providerTheme.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the registry**

Create `viewer/src/lib/providerTheme.ts`:

```ts
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
```

- [ ] **Step 4: Run test to verify pass**

Run: `cd viewer && npm run test -- providerTheme.test.ts`
Expected: PASS all 8.

- [ ] **Step 5: Run full suite**

Run: `cd viewer && npm run test`
Expected: no regressions.

- [ ] **Step 6: Commit**

```bash
git add viewer/src/lib/providerTheme.ts viewer/src/__tests__/providerTheme.test.ts
git commit -m "feat(viewer): provider theming registry with AWS/Azure/generic dispatch"
```

---

## Task 2: Light-theme zone colours + new `cloud` and `region` zone types

**Files:**
- Modify: `viewer/src/lib/colors.ts`
- Modify: `viewer/src/__tests__/colors.test.ts`

- [ ] **Step 1: Add failing test for cloud and region entries**

Append to `viewer/src/__tests__/colors.test.ts` inside the existing `describe('ZONE_COLORS', ...)` block (or create a new one):

```ts
test('ZONE_COLORS includes cloud and region zone types for light theme', () => {
  expect(ZONE_COLORS.cloud).toBeDefined();
  expect(ZONE_COLORS.region).toBeDefined();
  expect(ZONE_COLORS.cloud.borderStyle).toBe('dashed');
});

test('light-theme regional background is white-ish (not dark)', () => {
  // Light theme invariant — background should be semi-transparent near-white
  expect(ZONE_COLORS.regional.background.toLowerCase()).toContain('255');
});
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd viewer && npm run test -- colors.test.ts`
Expected: FAIL — `cloud` undefined / regional background mismatch.

- [ ] **Step 3: Rewrite ZONE_COLORS + extend ZoneType**

In `viewer/src/lib/colors.ts`, replace the existing `ZoneType` union AND the entire `ZONE_COLORS` object with:

```ts
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
    background: 'rgba(255,255,255,0.4)',
    border: 'rgba(231,21,123,0.45)',
    label: '#BE185D',
    pill: 'rgba(255,255,255,0.9)',
    pillBorder: 'rgba(231,21,123,0.35)',
    pillText: '#BE185D',
    borderWidth: '1.5px',
    borderStyle: 'dashed',
  },
  region: {
    background: 'transparent',
    border: 'rgba(100,116,139,0.5)',
    label: '#475569',
    pill: 'rgba(255,255,255,0.95)',
    pillBorder: 'rgba(100,116,139,0.35)',
    pillText: '#475569',
    borderWidth: '1px',
    borderStyle: 'dashed',
  },
  internet: {
    background: 'rgba(255,255,255,0.6)',
    border: 'rgba(100,116,139,0.5)',
    label: '#475569',
    pill: 'rgba(255,255,255,0.95)',
    pillBorder: 'rgba(100,116,139,0.3)',
    pillText: '#475569',
    borderWidth: '1.5px',
    borderStyle: 'dashed',
  },
  vpc: {
    background: 'rgba(140,79,255,0.04)',
    border: 'rgba(140,79,255,0.5)',
    label: '#7C3AED',
    pill: 'rgba(255,255,255,0.95)',
    pillBorder: 'rgba(140,79,255,0.35)',
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
    background: 'rgba(34,197,94,0.04)',
    border: 'rgba(34,197,94,0.45)',
    label: '#16A34A',
    pill: 'rgba(255,255,255,0.95)',
    pillBorder: 'rgba(34,197,94,0.35)',
    pillText: '#16A34A',
    borderWidth: '1.5px',
    borderStyle: 'dashed',
  },
  private_subnet: {
    background: 'rgba(59,130,246,0.04)',
    border: 'rgba(59,130,246,0.45)',
    label: '#2563EB',
    pill: 'rgba(255,255,255,0.95)',
    pillBorder: 'rgba(59,130,246,0.35)',
    pillText: '#2563EB',
    borderWidth: '1.5px',
    borderStyle: 'dashed',
  },
  data_subnet: {
    background: 'rgba(168,85,247,0.04)',
    border: 'rgba(168,85,247,0.45)',
    label: '#9333EA',
    pill: 'rgba(255,255,255,0.95)',
    pillBorder: 'rgba(168,85,247,0.35)',
    pillText: '#9333EA',
    borderWidth: '1.5px',
    borderStyle: 'dashed',
  },
  regional: {
    background: 'rgba(255,255,255,0.7)',
    border: 'rgba(226,232,240,1)',
    label: '#475569',
    pill: 'rgba(241,245,249,1)',
    pillBorder: 'rgba(203,213,225,1)',
    pillText: '#475569',
    borderWidth: '1.5px',
    borderStyle: 'solid',
  },
  category: {
    background: 'transparent',
    border: 'rgba(226,232,240,0.9)',
    label: '#475569',
    pill: 'rgba(248,250,252,1)',
    pillBorder: 'rgba(203,213,225,1)',
    pillText: '#475569',
    borderWidth: '1px',
    borderStyle: 'dashed',
  },
};
```

- [ ] **Step 4: Run tests**

Run: `cd viewer && npm run test -- colors.test.ts`
Expected: PASS. The old `category` test (`pillText === '#94a3b8'`) WILL FAIL because we updated `pillText` to `#475569` for light. Update that test's expected value in the same file from `'#94a3b8'` to `'#475569'`.

Re-run: PASS.

- [ ] **Step 5: Run full suite**

Run: `cd viewer && npm run test`
Expected: PASS. If any other tests snapshot zone colours, update them.

- [ ] **Step 6: Commit**

```bash
git add viewer/src/lib/colors.ts viewer/src/__tests__/colors.test.ts
git commit -m "feat(viewer): rewrite ZONE_COLORS for light theme, add cloud/region zones"
```

---

## Task 3: Canvas background + minimap palette

**Files:**
- Modify: `viewer/src/components/DiagramCanvas.tsx`

- [ ] **Step 1: Update background and minimap colours**

In `viewer/src/components/DiagramCanvas.tsx`, locate the `<Background />` element (around line 107) and replace it with:

```tsx
        <Background variant={BackgroundVariant.Dots} gap={20} size={1.2} color="#DDE2E8" />
```

Locate the `<MiniMap />` element (around line 109) and replace with:

```tsx
        <MiniMap
          position="bottom-right"
          nodeColor={(node) => {
            if (node.type === 'group') return 'rgba(148,163,184,0.2)';
            return '#CBD5E1';
          }}
          maskColor="rgba(255,255,255,0.6)"
          pannable
          zoomable
        />
```

Locate the wrapper `div` (around line 88 `<div className="w-full h-full relative">`) and change the className / style so the canvas has a light background. Replace that line with:

```tsx
    <div className="w-full h-full relative" style={{ background: '#FAFBFC' }}>
```

Locate the `connectionLineStyle` on `<ReactFlow>` (around line 100) and change to:

```tsx
        connectionLineStyle={{ stroke: '#94A3B8', strokeWidth: 1 }}
```

Locate the "Fit View" button (around line 122-129). Replace that `<button>` styling with light tokens:

```tsx
        <button
          onClick={handleFitView}
          className="text-[10px] px-2 py-1 rounded cursor-pointer"
          style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', color: '#475569' }}
        >
          Fit View
        </button>
```

- [ ] **Step 2: Run tests**

Run: `cd viewer && npm run test`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add viewer/src/components/DiagramCanvas.tsx
git commit -m "feat(viewer): switch canvas to light theme (bg, dots, minimap, controls)"
```

---

## Task 4: AWS icon map + brand icon component

**Files:**
- Create: `viewer/src/icons/awsIconMap.ts`
- Create: `viewer/src/components/icons/AwsBrandIcon.tsx`

- [ ] **Step 1: Create the AWS icon mapping**

Create `viewer/src/icons/awsIconMap.ts`:

```ts
import type { ComponentType, SVGProps } from 'react';
import {
  ArchitectureServiceAmazonSimpleStorageServiceS3,
  ArchitectureServiceAWSKeyManagementServiceKMS,
  ArchitectureServiceAWSIdentityandAccessManagementIAM,
  ArchitectureServiceAmazonEC2,
  ArchitectureServiceAWSLambda,
  ArchitectureServiceAmazonRDS,
  ArchitectureServiceAmazonDynamoDB,
  ArchitectureServiceAmazonVirtualPrivateCloudVPC,
  ArchitectureServiceAmazonCloudFront,
  ArchitectureServiceAmazonCloudWatch,
  ArchitectureServiceAmazonRoute53,
  ArchitectureServiceAmazonSimpleNotificationServiceSNS,
  ArchitectureServiceAmazonSimpleQueueServiceSQS,
  ArchitectureServiceAmazonElasticLoadBalancing,
  ArchitectureServiceAWSSecretsManager,
  ArchitectureServiceAWSSystemsManager,
  ArchitectureServiceAWSWAF,
} from 'aws-react-icons';

type IconComponent = ComponentType<SVGProps<SVGSVGElement> & { size?: number }>;

const MAP: Record<string, IconComponent> = {
  aws_s3_bucket: ArchitectureServiceAmazonSimpleStorageServiceS3 as IconComponent,
  aws_kms_key: ArchitectureServiceAWSKeyManagementServiceKMS as IconComponent,
  aws_iam_role: ArchitectureServiceAWSIdentityandAccessManagementIAM as IconComponent,
  aws_iam_policy: ArchitectureServiceAWSIdentityandAccessManagementIAM as IconComponent,
  aws_iam_user: ArchitectureServiceAWSIdentityandAccessManagementIAM as IconComponent,
  aws_iam_group: ArchitectureServiceAWSIdentityandAccessManagementIAM as IconComponent,
  aws_iam_instance_profile: ArchitectureServiceAWSIdentityandAccessManagementIAM as IconComponent,
  aws_instance: ArchitectureServiceAmazonEC2 as IconComponent,
  aws_lambda_function: ArchitectureServiceAWSLambda as IconComponent,
  aws_db_instance: ArchitectureServiceAmazonRDS as IconComponent,
  aws_rds_cluster: ArchitectureServiceAmazonRDS as IconComponent,
  aws_dynamodb_table: ArchitectureServiceAmazonDynamoDB as IconComponent,
  aws_vpc: ArchitectureServiceAmazonVirtualPrivateCloudVPC as IconComponent,
  aws_cloudfront_distribution: ArchitectureServiceAmazonCloudFront as IconComponent,
  aws_cloudwatch_log_group: ArchitectureServiceAmazonCloudWatch as IconComponent,
  aws_cloudwatch_metric_alarm: ArchitectureServiceAmazonCloudWatch as IconComponent,
  aws_route53_zone: ArchitectureServiceAmazonRoute53 as IconComponent,
  aws_route53_record: ArchitectureServiceAmazonRoute53 as IconComponent,
  aws_sns_topic: ArchitectureServiceAmazonSimpleNotificationServiceSNS as IconComponent,
  aws_sqs_queue: ArchitectureServiceAmazonSimpleQueueServiceSQS as IconComponent,
  aws_alb: ArchitectureServiceAmazonElasticLoadBalancing as IconComponent,
  aws_lb: ArchitectureServiceAmazonElasticLoadBalancing as IconComponent,
  aws_secretsmanager_secret: ArchitectureServiceAWSSecretsManager as IconComponent,
  aws_ssm_parameter: ArchitectureServiceAWSSystemsManager as IconComponent,
  aws_waf_web_acl: ArchitectureServiceAWSWAF as IconComponent,
};

export function getAwsIcon(type: string): IconComponent | undefined {
  return MAP[type];
}
```

IMPORTANT: `aws-react-icons` exposes a large set of icons. Not every name above may exist exactly as written. Before implementing, the engineer should:
1. List available icons: `ls viewer/node_modules/aws-react-icons/lib/icons/ | grep -i "<keyword>"`
2. Match each terraform type to the closest icon name. If a specific name doesn't exist, substitute with a related one (e.g. if `ArchitectureServiceAmazonEC2` exists but not `ArchitectureServiceEc2`, use the former).
3. If no AWS icon exists for a type, omit that row — the dispatch falls back to geometric rendering.

- [ ] **Step 2: Create the AWS brand icon component**

Create `viewer/src/components/icons/AwsBrandIcon.tsx`:

```tsx
import { getAwsIcon } from '../../icons/awsIconMap';

interface Props {
  type: string;
  size?: number;
}

export function AwsBrandIcon({ type, size = 48 }: Props) {
  const Icon = getAwsIcon(type);
  if (!Icon) return null;
  return <Icon width={size} height={size} />;
}
```

- [ ] **Step 3: Verify build still works**

Run: `cd viewer && npm run build 2>&1 | tail -10`
Expected: build succeeds. If the import paths don't resolve (wrong icon name), the build errors will name the missing imports — remove those rows from the map.

- [ ] **Step 4: Run full test suite**

Run: `cd viewer && npm run test`
Expected: PASS (no tests target these new files yet — verification is in Task 6).

- [ ] **Step 5: Commit**

```bash
git add viewer/src/icons/awsIconMap.ts viewer/src/components/icons/AwsBrandIcon.tsx
git commit -m "feat(viewer): AWS brand icon dispatch via aws-react-icons"
```

---

## Task 5: Azure icon pack (curated inline SVG components)

**Files:**
- Create: `viewer/src/icons/azure/*.tsx` (12 files)
- Create: `viewer/src/icons/azureIconMap.ts`

- [ ] **Step 1: Create the Azure icon directory and first two icons as templates**

Create `viewer/src/icons/azure/StorageAccount.tsx`:

```tsx
import type { SVGProps } from 'react';
export function AzureStorageAccount(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg" {...props}>
      <defs>
        <linearGradient id="azurestorage-a" x1="9" y1="16.42" x2="9" y2="1.58" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#0078d4" />
          <stop offset="0.82" stopColor="#5ea0ef" />
        </linearGradient>
      </defs>
      <rect x="0.75" y="1.58" width="16.5" height="14.84" rx="1.5" fill="url(#azurestorage-a)" />
      <path d="M4.13 5.92h9.74v1.66H4.13zm0 2.74h9.74v1.66H4.13zm0 2.74h6.49v1.66H4.13z" fill="#fff" />
    </svg>
  );
}
```

Create `viewer/src/icons/azure/VirtualMachine.tsx`:

```tsx
import type { SVGProps } from 'react';
export function AzureVirtualMachine(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg" {...props}>
      <defs>
        <linearGradient id="azurevm-a" x1="9" y1="14.44" x2="9" y2="3.05" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#0078d4" />
          <stop offset="0.82" stopColor="#5ea0ef" />
        </linearGradient>
      </defs>
      <rect x="1" y="3.05" width="16" height="11.39" rx="1" fill="url(#azurevm-a)" />
      <rect x="2.5" y="4.55" width="13" height="7.5" fill="#fff" />
      <rect x="6.5" y="14.5" width="5" height="0.75" fill="#5ea0ef" />
    </svg>
  );
}
```

- [ ] **Step 2: Create the remaining 10 Azure icons**

For each of the following, create a file at `viewer/src/icons/azure/<Name>.tsx` with the same pattern (default export a named function returning an `<svg>` with Azure blue palette: `#0078D4` + `#5EA0EF` gradient on `#FFF` detail). File list:

| File | Export name | Purpose | Suggested glyph |
|---|---|---|---|
| `VirtualNetwork.tsx` | `AzureVirtualNetwork` | Virtual network | Two connected boxes with lines |
| `Subnet.tsx` | `AzureSubnet` | Subnet | Dashed inner box |
| `NetworkSecurityGroup.tsx` | `AzureNetworkSecurityGroup` | NSG | Shield over network glyph |
| `KeyVault.tsx` | `AzureKeyVault` | Key vault | Key glyph |
| `SqlDatabase.tsx` | `AzureSqlDatabase` | SQL DB | Database cylinder |
| `CosmosDb.tsx` | `AzureCosmosDb` | Cosmos DB | Planet/orbit rings |
| `AppService.tsx` | `AzureAppService` | App Service | Globe/app icon |
| `FunctionApp.tsx` | `AzureFunctionApp` | Functions | Lambda-style triangle |
| `LoadBalancer.tsx` | `AzureLoadBalancer` | Load balancer | Three horizontal bars |
| `PublicIp.tsx` | `AzurePublicIp` | Public IP | Globe + arrow |
| `ResourceGroup.tsx` | `AzureResourceGroup` | Resource group | Folder/group glyph |
| `Firewall.tsx` | `AzureFirewall` | Firewall | Brick wall |

Source SVGs from Microsoft's official icon pack: <https://learn.microsoft.com/en-us/azure/architecture/icons/>. Download the SVG, trim any `<metadata>`/`<title>`, extract the inner paths/defs, rewrite as a React component matching the `StorageAccount.tsx` / `VirtualMachine.tsx` pattern. Each icon should be self-contained (inline gradient with a unique `id` prefixed like `azurefw-a`, `azurevnet-a` etc. to avoid `<defs>` id collisions).

For each icon, include as a prop `SVGProps<SVGSVGElement>` so `size` passed as `width`/`height` attributes works.

- [ ] **Step 3: Create the Azure icon map**

Create `viewer/src/icons/azureIconMap.ts`:

```ts
import type { ComponentType, SVGProps } from 'react';
import { AzureStorageAccount } from './azure/StorageAccount';
import { AzureVirtualMachine } from './azure/VirtualMachine';
import { AzureVirtualNetwork } from './azure/VirtualNetwork';
import { AzureSubnet } from './azure/Subnet';
import { AzureNetworkSecurityGroup } from './azure/NetworkSecurityGroup';
import { AzureKeyVault } from './azure/KeyVault';
import { AzureSqlDatabase } from './azure/SqlDatabase';
import { AzureCosmosDb } from './azure/CosmosDb';
import { AzureAppService } from './azure/AppService';
import { AzureFunctionApp } from './azure/FunctionApp';
import { AzureLoadBalancer } from './azure/LoadBalancer';
import { AzurePublicIp } from './azure/PublicIp';
import { AzureResourceGroup } from './azure/ResourceGroup';
import { AzureFirewall } from './azure/Firewall';

type IconComponent = ComponentType<SVGProps<SVGSVGElement>>;

const MAP: Record<string, IconComponent> = {
  azurerm_storage_account: AzureStorageAccount,
  azurerm_virtual_machine: AzureVirtualMachine,
  azurerm_linux_virtual_machine: AzureVirtualMachine,
  azurerm_windows_virtual_machine: AzureVirtualMachine,
  azurerm_virtual_network: AzureVirtualNetwork,
  azurerm_subnet: AzureSubnet,
  azurerm_network_security_group: AzureNetworkSecurityGroup,
  azurerm_key_vault: AzureKeyVault,
  azurerm_sql_database: AzureSqlDatabase,
  azurerm_mssql_database: AzureSqlDatabase,
  azurerm_cosmosdb_account: AzureCosmosDb,
  azurerm_cosmosdb_sql_database: AzureCosmosDb,
  azurerm_app_service: AzureAppService,
  azurerm_linux_web_app: AzureAppService,
  azurerm_windows_web_app: AzureAppService,
  azurerm_function_app: AzureFunctionApp,
  azurerm_linux_function_app: AzureFunctionApp,
  azurerm_windows_function_app: AzureFunctionApp,
  azurerm_lb: AzureLoadBalancer,
  azurerm_public_ip: AzurePublicIp,
  azurerm_resource_group: AzureResourceGroup,
  azurerm_firewall: AzureFirewall,
};

export function getAzureIcon(type: string): IconComponent | undefined {
  return MAP[type];
}
```

- [ ] **Step 4: Verify build**

Run: `cd viewer && npm run build 2>&1 | tail -10`
Expected: build succeeds. If any imports fail, the engineer has missing `.tsx` files — create them.

- [ ] **Step 5: Commit**

```bash
git add viewer/src/icons/azure/ viewer/src/icons/azureIconMap.ts
git commit -m "feat(viewer): curated Azure service icon pack (12 inline SVG components)"
```

---

## Task 6: ServiceIcon dispatch component + tests

**Files:**
- Create: `viewer/src/components/icons/ServiceIcon.tsx`
- Create: `viewer/src/__tests__/ServiceIcon.test.tsx`

- [ ] **Step 1: Write failing tests**

Create `viewer/src/__tests__/ServiceIcon.test.tsx`:

```tsx
import { describe, test, expect } from 'vitest';
import { render } from '@testing-library/react';
import { ServiceIcon } from '../components/icons/ServiceIcon';

describe('ServiceIcon', () => {
  test('renders AWS svg for aws provider + known type', () => {
    const { container } = render(<ServiceIcon provider="aws" type="aws_s3_bucket" />);
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  test('renders Azure svg for azurerm provider + known type', () => {
    const { container } = render(<ServiceIcon provider="azurerm" type="azurerm_storage_account" />);
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  test('falls back to geometric for unknown aws type', () => {
    const { container } = render(<ServiceIcon provider="aws" type="aws_totally_fake_type" />);
    // Geometric fallback always returns an svg
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  test('falls back to geometric for generic provider', () => {
    const { container } = render(<ServiceIcon provider="generic" type="unknown_type" />);
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  test('respects size prop', () => {
    const { container } = render(<ServiceIcon provider="aws" type="aws_s3_bucket" size={64} />);
    const svg = container.querySelector('svg')!;
    // width/height may be attributes or styles depending on icon source
    const w = svg.getAttribute('width') ?? svg.style.width;
    expect(w).toMatch(/64/);
  });
});
```

- [ ] **Step 2: Run failing test**

Run: `cd viewer && npm run test -- ServiceIcon.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the dispatcher**

Create `viewer/src/components/icons/ServiceIcon.tsx`:

```tsx
import type { Provider } from '../../lib/providerTheme';
import { PROVIDER_THEMES } from '../../lib/providerTheme';
import { getAwsIcon } from '../../icons/awsIconMap';
import { getAzureIcon } from '../../icons/azureIconMap';
import { ResourceIcon } from './ResourceIcon';

interface Props {
  provider: Provider;
  type: string;
  size?: number;
}

export function ServiceIcon({ provider, type, size = 48 }: Props) {
  const kind = PROVIDER_THEMES[provider].iconKind;

  if (kind === 'aws') {
    const Icon = getAwsIcon(type);
    if (Icon) return <Icon width={size} height={size} />;
  } else if (kind === 'azure') {
    const Icon = getAzureIcon(type);
    if (Icon) return <Icon width={size} height={size} />;
  }

  return <ResourceIcon resourceType={type} size={size} />;
}
```

- [ ] **Step 4: Run tests**

Run: `cd viewer && npm run test -- ServiceIcon.test.tsx`
Expected: PASS all 5.

- [ ] **Step 5: Run full suite**

Run: `cd viewer && npm run test`
Expected: no regressions.

- [ ] **Step 6: Commit**

```bash
git add viewer/src/components/icons/ServiceIcon.tsx viewer/src/__tests__/ServiceIcon.test.tsx
git commit -m "feat(viewer): ServiceIcon dispatch component with AWS/Azure/geometric fallback"
```

---

## Task 7: Rewrite ResourceNode for light theme + ServiceIcon

**Files:**
- Modify: `viewer/src/components/ResourceNode.tsx`

- [ ] **Step 1: Rewrite the component body**

Replace the entire `viewer/src/components/ResourceNode.tsx` with:

```tsx
import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { ResourceNode as ResourceNodeData } from '../types';
import { severityColors, driftColors, getHighestSeverity } from '../lib/colors';
import { detectProvider } from '../lib/providerTheme';
import { ServiceIcon } from './icons/ServiceIcon';
import { useStore } from '../store';

type ResourceNodeProps = NodeProps & {
  data: ResourceNodeData;
};

function ResourceNodeComponent({ data, selected }: ResourceNodeProps) {
  const setSelectedNode = useStore(s => s.setSelectedNode);
  const highestSev = getHighestSeverity(data.findings);
  const findingCount = data.findings.length;
  const isShadow = data.drift === 'shadow';
  const isNew = data.drift === 'added';
  const isChanged = data.drift === 'changed';
  const isDeleted = data.drift === 'deleted';

  const provider = data.provider === 'azurerm' ? 'azurerm' : detectProvider(data.type);

  const typeLabel = data.type
    .replace(/^aws_/, '')
    .replace(/^azurerm_/, '')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, c => c.toUpperCase());

  const borderColor = selected
    ? '#3B82F6'
    : isShadow
    ? '#D97706'
    : isNew
    ? driftColors.added
    : isChanged
    ? driftColors.changed
    : '#E2E8F0';

  return (
    <div
      style={{ width: 160 }}
      className="relative cursor-pointer"
      onClick={() => setSelectedNode(data)}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-slate-400 !border-slate-500 !w-2 !h-2"
      />

      <div
        style={{
          background: '#FFFFFF',
          border: `${selected ? 2 : 1}px ${isShadow ? 'dashed' : 'solid'} ${borderColor}`,
          borderRadius: 8,
          padding: '14px 12px 10px 12px',
          opacity: isDeleted ? 0.45 : 1,
          boxShadow: selected
            ? '0 0 0 3px rgba(59,130,246,0.18), 0 4px 12px rgba(15,23,42,0.1)'
            : '0 1px 3px rgba(15,23,42,0.06)',
          transition: 'all 0.15s ease',
          textAlign: 'center',
          position: 'relative',
        }}
        onMouseEnter={e => {
          if (selected) return;
          (e.currentTarget as HTMLDivElement).style.boxShadow = '0 4px 12px rgba(15,23,42,0.12)';
          (e.currentTarget as HTMLDivElement).style.borderColor = '#CBD5E1';
        }}
        onMouseLeave={e => {
          if (selected) return;
          (e.currentTarget as HTMLDivElement).style.boxShadow = '0 1px 3px rgba(15,23,42,0.06)';
          (e.currentTarget as HTMLDivElement).style.borderColor = borderColor;
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 8 }}>
          <ServiceIcon provider={provider} type={data.type} size={44} />
        </div>

        <div
          style={{
            fontSize: 13,
            fontWeight: 700,
            color: '#0F172A',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            lineHeight: 1.25,
          }}
          title={data.id}
        >
          {data.name}
        </div>
        <div
          style={{
            fontSize: 10.5,
            fontWeight: 500,
            color: '#64748B',
            letterSpacing: '0.2px',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            marginTop: 2,
          }}
        >
          {typeLabel}
        </div>

        {(data.cost.monthly_usd > 0 || isNew || isChanged) && (
          <div style={{ display: 'flex', justifyContent: 'center', gap: 6, marginTop: 6 }}>
            {data.cost.monthly_usd > 0 && (
              <span
                style={{
                  fontSize: 10,
                  fontFamily: 'ui-monospace, monospace',
                  color: '#16A34A',
                  fontWeight: 600,
                }}
              >
                ${data.cost.monthly_usd.toFixed(0)}/mo
              </span>
            )}
            {isNew && (
              <span
                style={{
                  fontSize: 8,
                  padding: '1px 5px',
                  borderRadius: 3,
                  background: 'rgba(34,197,94,0.12)',
                  color: '#15803D',
                  fontWeight: 700,
                  border: '1px solid rgba(34,197,94,0.3)',
                }}
              >
                NEW
              </span>
            )}
            {isChanged && (
              <span
                style={{
                  fontSize: 8,
                  padding: '1px 5px',
                  borderRadius: 3,
                  background: 'rgba(234,179,8,0.12)',
                  color: '#A16207',
                  fontWeight: 700,
                  border: '1px solid rgba(234,179,8,0.3)',
                }}
              >
                CHG
              </span>
            )}
          </div>
        )}

        {findingCount > 0 && highestSev && (
          <div
            style={{
              position: 'absolute',
              top: -6,
              right: -6,
              minWidth: 20,
              height: 20,
              padding: '0 6px',
              borderRadius: 10,
              background: severityColors[highestSev],
              color: '#ffffff',
              fontSize: 11,
              fontWeight: 800,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: `0 1px 4px ${severityColors[highestSev]}66, 0 0 0 2px #FFFFFF`,
            }}
          >
            {findingCount}
          </div>
        )}
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-slate-400 !border-slate-500 !w-2 !h-2"
      />

      {isShadow && (
        <div style={{ textAlign: 'center', marginTop: 2, fontSize: 9, color: '#D97706' }}>
          shadow
        </div>
      )}
    </div>
  );
}

export const ResourceNodeMemo = memo(ResourceNodeComponent);
```

- [ ] **Step 2: Update ResourceNode tests**

The existing `viewer/src/__tests__/ResourceNode.test.tsx` asserts the presence of text `"STG"` / `"STORAGE ACCOUNT"` / `"VNet"` / `"+NEW"` in the old design. The new design:
- Has no `STG`/`VNet` text labels (icons replace them)
- Changes `+NEW` to `NEW`
- Type label is now title-cased: `"Storage Account"` instead of `"STORAGE ACCOUNT"`

Update the assertions to match the new behaviour. Open `viewer/src/__tests__/ResourceNode.test.tsx` and replace the four existing test blocks' assertions with:

```tsx
  test('renders Azure resource name', () => {
    const props = makeNodeProps({
      id: 'azurerm_storage_account.data',
      type: 'azurerm_storage_account',
      name: 'data',
      provider: 'azurerm',
    });
    render(<ResourceNodeMemo {...props} />);
    expect(screen.getByText('data')).toBeInTheDocument();
  });

  test('title-cases type label and strips provider prefix', () => {
    const props = makeNodeProps({
      id: 'azurerm_storage_account.data',
      type: 'azurerm_storage_account',
      name: 'data',
      provider: 'azurerm',
    });
    render(<ResourceNodeMemo {...props} />);
    expect(screen.getByText('Storage Account')).toBeInTheDocument();
  });

  test('renders azurerm resource icon as an svg', () => {
    const props = makeNodeProps({
      id: 'azurerm_virtual_network.vnet',
      type: 'azurerm_virtual_network',
      name: 'vnet',
      provider: 'azurerm',
    });
    const { container } = render(<ResourceNodeMemo {...props} />);
    expect(container.querySelector('svg')).toBeInTheDocument();
    expect(screen.getByText('Virtual Network')).toBeInTheDocument();
  });

  test('applies NEW badge for added drift', () => {
    const props = makeNodeProps({ drift: 'added' });
    render(<ResourceNodeMemo {...props} />);
    expect(screen.getByText('NEW')).toBeInTheDocument();
  });
```

- [ ] **Step 3: Run tests**

Run: `cd viewer && npm run test`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add viewer/src/components/ResourceNode.tsx viewer/src/__tests__/ResourceNode.test.tsx
git commit -m "feat(viewer): rewrite ResourceNode for light theme with real service icons"
```

---

## Task 8: Layout — cloud wrapper zones

**Files:**
- Modify: `viewer/src/lib/layout.ts`
- Modify: `viewer/src/__tests__/layout.test.ts`

- [ ] **Step 1: Add failing test for cloud wrapping**

Append to `viewer/src/__tests__/layout.test.ts`:

```ts
describe('buildFlowElements — cloud wrapping', () => {
  test('wraps AWS resources in a zone-cloud-aws container', () => {
    const graph = makeGraph([
      makeNode('aws_s3_bucket.logs', 'aws_s3_bucket', 'logs'),
      makeNode('aws_iam_policy.p', 'aws_iam_policy', 'p'),
    ]);
    const { nodes } = buildFlowElements(graph);
    const cloud = nodes.find(n => n.id === 'zone-cloud-aws');
    expect(cloud).toBeDefined();
    expect((cloud!.data as { zoneType: string }).zoneType).toBe('cloud');
    // Regional zone should be nested under the cloud
    const regional = nodes.find(n => n.id === 'zone-regional');
    expect(regional?.parentId).toBe('zone-cloud-aws');
  });

  test('emits a separate cloud per provider in a mixed graph', () => {
    const graph = makeGraph([
      makeNode('aws_s3_bucket.a', 'aws_s3_bucket', 'a'),
      makeNode('azurerm_storage_account.b', 'azurerm_storage_account', 'b'),
    ]);
    const { nodes } = buildFlowElements(graph);
    expect(nodes.find(n => n.id === 'zone-cloud-aws')).toBeDefined();
    expect(nodes.find(n => n.id === 'zone-cloud-azurerm')).toBeDefined();
  });
});
```

- [ ] **Step 2: Run failing test**

Run: `cd viewer && npm run test -- layout.test.ts`
Expected: FAIL — `zone-cloud-aws` not found.

- [ ] **Step 3: Add cloud-wrapping logic to `buildFlowElements`**

In `viewer/src/lib/layout.ts`, add these imports at the top (after the existing imports):

```ts
import { detectProvider, PROVIDER_THEMES, type Provider } from './providerTheme';
```

Add this constant block near the existing layout constants (e.g. after `VPC_REG_GAP`):

```ts
const CLOUD_PAD = 20;
const CLOUD_LABEL_H = 36;
const CLOUD_GAP = 40;
```

At the end of `buildFlowElements`, AFTER all other `flowNodes.push(...)` calls and BEFORE `const flowEdges = buildEdges(...)`, insert this wrapping logic:

```ts
  // 5. Wrap top-level zones in per-provider cloud containers
  const providerOfResource = (id: string): Provider => {
    const n = graph.nodes.find(gn => gn.id === id);
    if (!n) return 'generic';
    return detectProvider(n.type);
  };

  // Classify top-level zones (those without parentId) by provider
  type TopZone = { id: string; provider: Provider };
  const topZones: TopZone[] = [];
  for (const fn of flowNodes) {
    if (fn.type !== 'group') continue;
    if (fn.parentId) continue; // already nested
    // Determine the provider by looking at the first resource that claims this zone as parent
    const child = flowNodes.find(c => c.type === 'resource' && c.parentId === fn.id);
    let prov: Provider = 'generic';
    if (child) prov = providerOfResource(child.id);
    topZones.push({ id: fn.id, provider: prov });
  }

  const providersSeen = new Set(topZones.map(t => t.provider));
  if (providersSeen.size === 0) return { nodes: flowNodes, edges: buildEdges(graph.edges, graph.nodes, suppressedIds) };

  // Build a bounding box per provider from their top-level zones
  type Box = { x: number; y: number; w: number; h: number };
  const boxOf = (id: string): Box => {
    const n = flowNodes.find(f => f.id === id)!;
    const w = (n.style?.width as number) ?? 0;
    const h = (n.style?.height as number) ?? 0;
    return { x: n.position.x, y: n.position.y, w, h };
  };

  let cloudXCursor = startX;
  const cloudYOrigin = 40;

  for (const prov of providersSeen) {
    const myZones = topZones.filter(t => t.provider === prov).map(t => t.id);
    if (myZones.length === 0) continue;

    const boxes = myZones.map(boxOf);
    const minX = Math.min(...boxes.map(b => b.x));
    const minY = Math.min(...boxes.map(b => b.y));
    const maxX = Math.max(...boxes.map(b => b.x + b.w));
    const maxY = Math.max(...boxes.map(b => b.y + b.h));

    const cloudW = maxX - minX + 2 * CLOUD_PAD;
    const cloudH = maxY - minY + CLOUD_LABEL_H + 2 * CLOUD_PAD;
    const cloudId = `zone-cloud-${prov}`;

    flowNodes.push(
      makeZone(cloudId, PROVIDER_THEMES[prov].label, 'cloud', cloudXCursor, cloudYOrigin, cloudW, cloudH),
    );

    // Reparent the top-level zones under the cloud and rewrite their positions relative to the cloud
    for (const zId of myZones) {
      const zone = flowNodes.find(f => f.id === zId)!;
      const origX = zone.position.x;
      const origY = zone.position.y;
      zone.parentId = cloudId;
      zone.extent = 'parent' as const;
      zone.position = {
        x: origX - minX + CLOUD_PAD,
        y: origY - minY + CLOUD_LABEL_H + CLOUD_PAD,
      };
    }

    cloudXCursor += cloudW + CLOUD_GAP;
  }
```

- [ ] **Step 4: Run layout tests**

Run: `cd viewer && npm run test -- layout.test.ts`
Expected: PASS all cloud-wrapping + prior tests.

- [ ] **Step 5: Run full suite**

Run: `cd viewer && npm run test`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add viewer/src/lib/layout.ts viewer/src/__tests__/layout.test.ts
git commit -m "feat(viewer): wrap top-level zones in per-provider cloud containers"
```

---

## Task 9: Light-theme edge palette

**Files:**
- Modify: `viewer/src/lib/layout.ts`

- [ ] **Step 1: Update edge style palette**

In `viewer/src/lib/layout.ts`, locate the `getEdgeStyle` function and replace it with:

```ts
function getEdgeStyle(source: ResourceNodeData, target: ResourceNodeData): Partial<Edge> {
  // Security group attachment
  if (source.type === 'aws_security_group' || target.type === 'aws_security_group') {
    return {
      style: { stroke: '#DC2626', strokeWidth: 1, strokeDasharray: '3 2' },
      label: 'sg',
      labelStyle: { fontSize: 9, fill: '#DC2626' } as React.CSSProperties,
      labelBgStyle: { fill: '#FFFFFF', fillOpacity: 0.9 },
      labelBgPadding: [3, 1] as [number, number],
    };
  }

  // Access to regional services
  if (REGIONAL_TYPES.has(target.type)) {
    return {
      style: { stroke: '#3B82F6', strokeWidth: 1.25, strokeDasharray: '5 3' },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#3B82F6', width: 14, height: 14 },
    };
  }

  // IGW / internet traffic
  if (INTERNET_TYPES.has(source.type) || INTERNET_TYPES.has(target.type)) {
    return {
      style: { stroke: '#475569', strokeWidth: 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#475569', width: 14, height: 14 },
    };
  }

  // Default dependency
  return {
    style: { stroke: '#94A3B8', strokeWidth: 1.25, strokeDasharray: '4 3' },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#94A3B8', width: 14, height: 14 },
  };
}
```

- [ ] **Step 2: Run tests**

Run: `cd viewer && npm run test`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add viewer/src/lib/layout.ts
git commit -m "feat(viewer): light-theme edge palette"
```

---

## Task 10: SummaryBar edge-legend palette + header text contrast check

**Files:**
- Modify: `viewer/src/components/SummaryBar.tsx`

- [ ] **Step 1: Update edge legend colours to match new edges**

In `viewer/src/components/SummaryBar.tsx`, locate the three `<span className="flex items-center gap-2">` elements inside the edge-legend tooltip (around the "traffic" / "access" / "security" entries). Replace the `stroke` / `fill` hex values in the inline SVGs to match the new edge palette:

- `traffic` row: both `stroke` and `fill` in the line/polygon → `#475569`
- `access` row: both → `#3B82F6`
- `security` row: `stroke` → `#DC2626`

Specifically, replace the full legend tooltip content (inside the `<div id="edge-legend-tooltip" role="tooltip" ...>`) with:

```tsx
          <span className="flex items-center gap-2">
            <svg width="22" height="6">
              <line x1="0" y1="3" x2="16" y2="3" stroke="#475569" strokeWidth="1.5" />
              <polygon points="16,1 22,3 16,5" fill="#475569" />
            </svg>
            traffic
          </span>
          <span className="flex items-center gap-2">
            <svg width="22" height="6">
              <line x1="0" y1="3" x2="16" y2="3" stroke="#3B82F6" strokeWidth="1.25" strokeDasharray="5 3" />
              <polygon points="16,1 22,3 16,5" fill="#3B82F6" />
            </svg>
            access
          </span>
          <span className="flex items-center gap-2">
            <svg width="22" height="6">
              <line x1="0" y1="3" x2="22" y2="3" stroke="#DC2626" strokeWidth="1" strokeDasharray="3 2" />
            </svg>
            security
          </span>
```

- [ ] **Step 2: Run tests**

Run: `cd viewer && npm run test`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add viewer/src/components/SummaryBar.tsx
git commit -m "feat(viewer): align edge-legend palette with light-theme edges"
```

---

## Task 11: Build + sync template + manual verification

**Files:**
- Modify: `cli/infracanvas/export/viewer_template.html`

- [ ] **Step 1: TypeScript + tests**

Run from `/Users/bhushan/Documents/Projects/Infracanvas/viewer`:

```bash
npx tsc --noEmit && npm run test
```

Expected: both clean.

- [ ] **Step 2: Build bundle**

Run: `cd viewer && npm run build`
Expected: `dist/index.html` produced. Note the bundle size (`tail -5` of output shows it). If bundle > 800KB raw, flag — the Azure icon pack may have grown too large.

- [ ] **Step 3: Sync bundle to CLI template**

```bash
cp viewer/dist/index.html cli/infracanvas/export/viewer_template.html
```

- [ ] **Step 4: Run AWS fixture scan**

```bash
/opt/homebrew/opt/python@3.11/bin/python3.11 -c "from infracanvas.main import app; import sys; sys.argv=['infracanvas','scan','/Users/bhushan/Documents/Projects/Infracanvas/cli/tests/fixtures/insecure_setup','--output','/tmp/infracanvas-aws.html','--format','html']; app()"
open /tmp/infracanvas-aws.html
```

Expected visual outcome:
- Light canvas (`#FAFBFC`) with subtle grey dots
- Outermost pink-dashed **"AWS Cloud"** container wrapping everything
- Regional Services zone inside with category sub-zones (IDENTITY & ACCESS, DATA, NETWORK, OTHER) in dashed grey borders
- Each resource renders as a white card with a real AWS service icon (S3 bucket glyph, KMS key glyph, IAM identity glyph, etc.)
- Finding counts appear as small coloured pill top-right of affected nodes
- Header stays dark

- [ ] **Step 5: Run Azure fixture scan**

```bash
/opt/homebrew/opt/python@3.11/bin/python3.11 -c "from infracanvas.main import app; import sys; sys.argv=['infracanvas','scan','/Users/bhushan/Documents/Projects/Infracanvas/cli/tests/fixtures/azure','--output','/tmp/infracanvas-azure.html','--format','html']; app()"
open /tmp/infracanvas-azure.html
```

Expected visual outcome:
- Outermost blue-dashed **"Microsoft Azure"** container
- Azure service icons (Storage Account, VM, VNet, etc.) where mapped; geometric fallback for unmapped types
- Same light canvas style

- [ ] **Step 6: Commit template sync**

```bash
git add cli/infracanvas/export/viewer_template.html
git commit -m "chore(viewer): sync light-theme bundle to CLI template"
```

- [ ] **Step 7: Spot-check for visible issues**

Look for:
- Category labels that overlap first resource card → adjust `CAT_PAD` in `layout.ts` if so
- Icons that don't render → check console for missing-name errors, add mapping in `awsIconMap.ts` or `azureIconMap.ts`
- Low-contrast text → swap `#64748B` for `#475569` on affected spans

If any issue surfaces, fix in-place and commit as a single follow-up `fix(viewer): ...` commit.

---

## Self-Review Results

**Spec coverage:**

| Spec section | Implemented in |
|---|---|
| 1. Provider registry + detect + primary | Task 1 ✓ |
| 2. Light canvas + dotted grid | Task 3 ✓ |
| 3. Light zone palette + `cloud`/`region` zones | Task 2 ✓ |
| 4a. Icon dispatch (`ServiceIcon`) | Task 6 ✓ |
| 4a. AWS icon map | Task 4 ✓ |
| 4a. Azure SVG pack + map | Task 5 ✓ |
| 4b. Node layout (icon + name + type + finding pill) | Task 7 ✓ |
| 5. Edge palette | Task 9 ✓ |
| 6. Header edge-legend palette alignment | Task 10 ✓ |
| Cloud wrapping (single + mixed provider) | Task 8 ✓ |
| Build + sync + verify | Task 11 ✓ |

**Placeholder scan:** No TBDs. Task 5 directs the engineer to Microsoft's icon source URL for the 10 remaining Azure icons — this is sourcing guidance, not a code placeholder, because the icon component shape is fully specified via the two template files (`StorageAccount.tsx`, `VirtualMachine.tsx`). Task 4 flags that specific `aws-react-icons` export names must be verified against the installed package — that's a defensive instruction, not a placeholder.

**Type consistency:**
- `Provider` type union (`'aws' | 'azurerm' | 'generic'`) used consistently across `providerTheme.ts`, `ServiceIcon.tsx`, `layout.ts`.
- `zone-cloud-${provider}` id scheme consistent between layout emission (Task 8) and test (Task 8).
- `getAwsIcon` / `getAzureIcon` return `IconComponent | undefined` consistently.
- `ZoneType` extended once in Task 2, all subsequent references (Task 8 layout, Task 7 theming) use `'cloud'` and `'region'` correctly.
