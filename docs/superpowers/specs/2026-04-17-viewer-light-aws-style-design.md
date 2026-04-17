# Viewer Light / AWS Architecture Style — Design

**Date:** 2026-04-17
**Scope:** Provider-aware visual redesign of the InfraCanvas viewer — light canvas, real service icons, clean architectural node language, visible flow arrows. No hardcoded cloud checks; everything dispatches off `node.provider`.
**Supersedes (visual layer of):** `docs/superpowers/specs/2026-04-17-viewer-professional-polish-design.md`. The categorisation and VPC-suppression layout changes from that spec remain — this spec only swaps the visual language on top.

## Problem

User-shared reference diagrams (AWS Well-Architected, Azure hub-and-spoke) establish a visual language the current dark "cyberpunk" theme does not match:

- Light / white canvas vs dark gradient
- Real AWS/Azure service glyphs vs coloured text labels (S3, KMS…)
- Descriptive node layout (icon + name + type) vs dense card with badges
- Clean dashed coloured zone borders vs solid dark grey
- Visible flow arrows with numbered steps vs barely-visible edges

The polish pass completed earlier (category sub-zones, VPC suppression, header tooltip) solves the *layout* problem but the visual vocabulary is wrong for the target use case (architecture reports, cloud-architect handoffs).

## Non-goals

- No animations, no parallax, no "wow" effects.
- No DetailPanel / FilterPanel / minimap restyling (they will look fine on the new canvas).
- No changes to graph-building, edge inference, or categorisation (done in previous spec).
- No new filter or search features.

## Design

### 1. Provider-agnostic theming registry

Create `viewer/src/lib/providerTheme.ts`:

```ts
export type Provider = 'aws' | 'azurerm' | 'generic';

export const PROVIDER_THEMES: Record<Provider, {
  label: string;          // user-facing cloud name
  cloudColor: string;     // outermost cloud-container border
  accentColor: string;    // provider brand accent
  iconKind: 'aws' | 'azure' | 'geometric';
}> = {
  aws:     { label: 'AWS Cloud',     cloudColor: '#E7157B', accentColor: '#FF9900', iconKind: 'aws' },
  azurerm: { label: 'Microsoft Azure', cloudColor: '#0078D4', accentColor: '#0078D4', iconKind: 'azure' },
  generic: { label: 'Cloud',         cloudColor: '#64748B', accentColor: '#64748B', iconKind: 'geometric' },
};

export function detectProvider(type: string): Provider {
  if (type.startsWith('aws_')) return 'aws';
  if (type.startsWith('azurerm_')) return 'azurerm';
  return 'generic';
}

export function primaryProviderOf(nodes: { type: string }[]): Provider {
  const counts: Record<Provider, number> = { aws: 0, azurerm: 0, generic: 0 };
  for (const n of nodes) counts[detectProvider(n.type)]++;
  return (Object.entries(counts).sort((a, b) => b[1] - a[1])[0][0] as Provider);
}
```

All provider-specific styling flows through this registry. No `if (provider === 'aws')` blocks anywhere else.

### 2. Light canvas + dark header

`viewer/src/components/DiagramCanvas.tsx`:
- Canvas background: `#FAFBFC`
- ReactFlow `<Background variant="dots" gap={20} size={1.2} color="#DDE2E8" />`

Header (`SummaryBar.tsx`) stays dark (tool chrome pattern; Linear / Figma use dark chrome + light canvas). No changes to header in this spec.

### 3. Zone styling — light + provider-aware

`viewer/src/lib/colors.ts` — rewrite `ZONE_COLORS` for the light theme. Each zone gets:
- `background: 'rgba(255,255,255,0.6)'` or similar translucent white
- `border` colour driven by zone type (subnets stay green/blue) OR provider theme (cloud outermost)
- `borderStyle: 'dashed'` for cloud/subnet, `'solid'` for containers that are conceptual boundaries (regional, category)

New `ZONE_COLORS` (light theme):

| zoneType | background | border | pillText | pillBg |
|---|---|---|---|---|
| cloud (new) | `rgba(231,21,123,0.03)` (provider-themed) | provider cloud dashed 1.5px | provider colour | white |
| region (new) | transparent | `#64748B` dashed 1px | `#64748B` | white |
| vpc | `rgba(140,79,255,0.04)` | `#8C4FFF` dashed 1.5px | `#8C4FFF` | white |
| az | transparent | `#94A3B8` dashed 1px | `#94A3B8` | transparent |
| public_subnet | `rgba(34,197,94,0.04)` | `#22C55E` dashed 1.5px | `#16A34A` | white |
| private_subnet | `rgba(59,130,246,0.04)` | `#3B82F6` dashed 1.5px | `#2563EB` | white |
| data_subnet | `rgba(168,85,247,0.04)` | `#A855F7` dashed 1.5px | `#9333EA` | white |
| regional | `rgba(255,255,255,0.7)` | `#E2E8F0` solid 1.5px | `#64748B` | `#F1F5F9` |
| category | transparent | `#E2E8F0` dashed 1px | `#64748B` | `#F8FAFC` |
| internet | `rgba(255,255,255,0.7)` | `#94A3B8` dashed 1.5px | `#64748B` | white |

Layout adds one or more outermost `zone-cloud-<provider>` containers wrapping their respective resources:

- **Single-provider graph:** emit exactly one `zone-cloud-<provider>` that parents the existing `zone-vpc`, `zone-regional`, `zone-internet` containers. All previously top-level zones get `parentId = 'zone-cloud-<provider>'` and their positions become relative to the cloud zone (offset by cloud padding). Cloud zone size is computed from the bounding box of its children.
- **Multi-provider graph:** emit one cloud zone per provider detected. Cloud zones sit side-by-side horizontally at the top level. Each cloud zone wraps only resources whose `detectProvider(type)` matches that cloud.
- **Detection per zone:** when deciding which cloud a VPC/regional/internet zone belongs to, use the provider of the first resource inside it. An empty cloud zone is never emitted.

### 4. Node visual — real service icons

#### 4a. Icon dispatch

New component `viewer/src/components/icons/ServiceIcon.tsx`:

```tsx
interface Props { provider: Provider; type: string; size?: number; }
export function ServiceIcon({ provider, type, size = 48 }: Props) {
  const kind = PROVIDER_THEMES[provider].iconKind;
  if (kind === 'aws') return <AwsBrandIcon type={type} size={size} />;
  if (kind === 'azure') return <AzureBrandIcon type={type} size={size} />;
  return <ResourceIcon resourceType={type} size={size} />;  // existing geometric fallback
}
```

- `AwsBrandIcon` uses `aws-react-icons` (already installed). Maps `aws_s3_bucket` → `AwsSimpleStorageServiceS3`, `aws_kms_key` → `AwsKeyManagementServiceKms`, etc. Mapping table lives in `viewer/src/icons/awsIconMap.ts`.
- `AzureBrandIcon` uses a curated SVG subset shipped under `viewer/src/icons/azure/*.svg` (hand-pick ~25 common services: VM, storage account, virtual network, subnet, NSG, Key Vault, App Service, SQL DB, Cosmos, Functions, Load Balancer, etc.). A mapping table `viewer/src/icons/azureIconMap.ts` maps terraform type → SVG path.
- Fallback: existing `ResourceIcon` geometric shapes.

When an AWS / Azure mapping is missing → fall through to geometric. No errors, no crashes.

#### 4b. Node layout (`ResourceNode.tsx`)

```
┌────────────────────┐
│         ╔══╗       │   ← 48x48 service glyph, centre-top
│         ║  ║       │
│         ╚══╝       │
│                    │
│   public_data      │   ← resource name, 13px bold #0F172A
│   S3 Bucket        │   ← type subtitle, 10.5px uppercase #64748B
│              [⚠ 5] │   ← optional finding pill bottom-right, small
└────────────────────┘
```

- Width: 160px, min-height: ~110px
- Background: `#FFFFFF`
- Border: 1px solid `#E2E8F0`, radius 8px
- Shadow: `0 1px 3px rgba(15,23,42,0.06)` default; `0 4px 12px rgba(15,23,42,0.12)` on hover
- Finding chip: pill shape bottom-right, 18px tall, severity colour at 15% bg + solid text + thin border. Only when `findingCount > 0`.
- No full-perimeter severity border. No top-edge severity strip. Findings are a secondary signal on an architecturally-first node.
- Drift markers (+NEW, ~CHG) unchanged.

### 5. Edges — AWS architecture style

`viewer/src/lib/layout.ts` `getEdgeStyle()` — update colour palette for light theme:

- Default dependency: `#475569` solid 1.25px + arrowhead
- Access (to regional services): `#3B82F6` dashed 5-3 + arrowhead
- Security group attachment: `#DC2626` dashed 3-2, no arrowhead, label "sg" in small red
- Internet traffic: `#475569` solid 1.5px + arrowhead

When an edge carries a `label` field (future) a small numbered circle renders at the midpoint — but this is not implemented in this spec (labels don't exist yet in the graph model).

### 6. Header — minimal adjustments

Already-dark header stays. Only change: edge legend tooltip colours updated for consistency with the new edge palette (swap greys for new values). No structural change.

## Implementation order

1. Add `providerTheme.ts` with registry + detection
2. Rewrite `colors.ts` `ZONE_COLORS` for light palette + add `cloud` and `region` zone types
3. Update `DiagramCanvas` background + grid dots
4. Update `GroupNode.tsx` — no structural change, it already reads from `ZONE_COLORS`; just verify labels contrast on light bg
5. Build `ServiceIcon.tsx` dispatch + AWS icon map + Azure SVG pack
6. Rewrite `ResourceNode.tsx` node body for light style with `<ServiceIcon>`
7. Update `layout.ts` — emit outermost `zone-cloud` around everything, shift all children under it; update edge palette
8. Update `SummaryBar.tsx` edge-legend colours

## Test / verification

- Existing Vitest suite passes (may need snapshot updates for zone-colour assertions)
- New tests:
  - `providerTheme.test.ts` — `detectProvider('aws_s3_bucket') === 'aws'`, `detectProvider('azurerm_storage_account') === 'azurerm'`, mixed graph → primary picked correctly
  - `ServiceIcon.test.tsx` — renders AWS branded icon for aws provider, azure SVG for azurerm, geometric fallback for unknown
- Manual verification:
  - AWS fixture (`insecure_setup`): AWS Cloud zone label + pink border; S3/KMS/IAM icons visible; light canvas
  - Azure fixture (`azure`): Azure zone label + blue border; Azure icons visible
  - Mixed fixture (if we create one): both providers render side-by-side; canvas anchors to majority

## Risk / rollback

- Risk: Azure icon SVG pack bundle weight. Mitigate by shipping a curated subset of ~25 SVGs (< 30KB total inlined).
- Risk: AWS icon package (`aws-react-icons`) tree-shaking. Verify the built bundle size doesn't balloon; if it does, switch to curated SVG pack approach for AWS too.
- Risk: Contrast regressions on the light canvas for small text (like `9.5px font-weight 700` type labels). Mitigate by bumping to `#475569` from `#64748B` where needed.
- Rollback: single revert of the commit series (one per implementation step).
