# Viewer Professional Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish the InfraCanvas viewer to read as a professional tool — suppress empty VPC zones, group regional resources by semantic category, tighten resource/group/header styling.

**Architecture:** Four-file surgical pass across `viewer/src/lib/{colors,layout}.ts` and `viewer/src/components/{ResourceNode,GroupNode,SummaryBar}.tsx`. No new dependencies, no changes to data flow, no DetailPanel/FilterPanel/DiagramCanvas changes.

**Tech Stack:** React 18, TypeScript 5.8, @xyflow/react 12, Tailwind 4, Vitest.

**Spec:** `docs/superpowers/specs/2026-04-17-viewer-professional-polish-design.md`

---

## File Structure

| File | Responsibility | Change type |
|---|---|---|
| `viewer/src/lib/colors.ts` | Zone colour palette | Add `category` zone type |
| `viewer/src/lib/layout.ts` | Diagram tree construction | Suppress empty VPC + category sub-sections |
| `viewer/src/components/GroupNode.tsx` | Zone container render | Anchor label inside + support category zone |
| `viewer/src/components/ResourceNode.tsx` | Resource card render | Severity top-edge accent + icon simplification |
| `viewer/src/components/SummaryBar.tsx` | Top header bar | Legend tooltip + metadata cluster + weight tweaks |
| `viewer/src/__tests__/colors.test.ts` | Existing tests | Extend for `category` |
| `viewer/src/__tests__/layout.test.ts` | New test file | VPC suppression + categorisation |

---

## Task 1: Add `category` zone type

**Files:**
- Modify: `viewer/src/lib/colors.ts`
- Test: `viewer/src/__tests__/colors.test.ts`

- [ ] **Step 1: Open existing colors test and add expectation for `category` key**

Modify `viewer/src/__tests__/colors.test.ts`. Add this test inside the existing `describe` block:

```ts
test('ZONE_COLORS includes category zone type', () => {
  expect(ZONE_COLORS.category).toBeDefined();
  expect(ZONE_COLORS.category.pillText).toBe('#94a3b8');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd viewer && npm run test -- colors.test.ts`
Expected: FAIL — `ZONE_COLORS.category` is undefined.

- [ ] **Step 3: Add `category` to `ZoneType` and `ZONE_COLORS`**

In `viewer/src/lib/colors.ts`, extend the `ZoneType` union:

```ts
export type ZoneType =
  | 'internet'
  | 'vpc'
  | 'az'
  | 'public_subnet'
  | 'private_subnet'
  | 'data_subnet'
  | 'regional'
  | 'category';
```

Add to the `ZONE_COLORS` object (after `regional`):

```ts
category: {
  background: 'transparent',
  border: 'rgba(71,85,105,0.18)',
  label: '#64748b',
  pill: 'rgba(45,55,72,0.5)',
  pillBorder: 'rgba(71,85,105,0.25)',
  pillText: '#94a3b8',
  borderWidth: '1px',
  borderStyle: 'dashed',
},
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd viewer && npm run test -- colors.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add viewer/src/lib/colors.ts viewer/src/__tests__/colors.test.ts
git commit -m "feat(viewer): add category zone type for regional sub-sections"
```

---

## Task 2: GroupNode — anchor label inside + render category zones

**Files:**
- Modify: `viewer/src/components/GroupNode.tsx`

- [ ] **Step 1: Replace the GroupNode render body**

Replace the entire `GroupNodeComponent` function body in `viewer/src/components/GroupNode.tsx` (lines 14-99) with:

```tsx
function GroupNodeComponent({ data }: GroupNodeProps) {
  const zone = ZONE_COLORS[data.zoneType] ?? ZONE_COLORS.regional;
  const isAz = data.zoneType === 'az';
  const isCategory = data.zoneType === 'category';

  const pillPadding = isCategory ? '1px 8px' : '2px 10px';
  const pillFontSize = isCategory ? 9 : 11;
  const labelTop = isCategory ? 6 : 10;

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        background: zone.background,
        border: `${zone.borderWidth} ${zone.borderStyle} ${zone.border}`,
        borderRadius: isCategory ? 8 : 12,
        position: 'relative',
      }}
    >
      {/* Zone label pill — anchored inside the container */}
      <div
        style={{
          position: 'absolute',
          top: labelTop,
          left: 14,
          display: 'flex',
          alignItems: 'center',
          gap: 5,
        }}
      >
        <span
          style={{
            fontSize: pillFontSize,
            fontWeight: 600,
            fontFamily: 'ui-monospace, monospace',
            color: zone.pillText,
            background: isAz ? 'transparent' : zone.pill,
            border: isAz ? 'none' : `1px solid ${zone.pillBorder}`,
            padding: isAz ? '0' : pillPadding,
            borderRadius: 4,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            display: 'flex',
            alignItems: 'center',
            gap: 5,
          }}
        >
          {data.zoneType === 'vpc' && <span style={{ fontSize: 10 }}>⬡</span>}
          {data.label}
        </span>

        {data.chip && !isAz && !isCategory && (
          <span
            style={{
              fontSize: 9,
              fontWeight: 500,
              fontFamily: 'ui-monospace, monospace',
              color: zone.pillText,
              background: zone.pill,
              border: `1px solid ${zone.pillBorder}`,
              padding: '2px 6px',
              borderRadius: 3,
              letterSpacing: '0.04em',
              opacity: 0.8,
            }}
          >
            {data.chip}
          </span>
        )}
      </div>

      {data.cidr && !isCategory && (
        <span
          style={{
            position: 'absolute',
            bottom: 6,
            left: 12,
            fontSize: 10,
            fontFamily: 'ui-monospace, monospace',
            color: '#374151',
          }}
        >
          {data.cidr}
        </span>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Run existing tests**

Run: `cd viewer && npm run test`
Expected: PASS (no component tests target GroupNode directly; this ensures nothing broke).

- [ ] **Step 3: Commit**

```bash
git add viewer/src/components/GroupNode.tsx
git commit -m "feat(viewer): anchor group labels inside containers, support category zone"
```

---

## Task 3: Layout — suppress empty VPC zone

**Files:**
- Modify: `viewer/src/lib/layout.ts`
- Test: `viewer/src/__tests__/layout.test.ts` (create)

- [ ] **Step 1: Create layout test file with VPC suppression test**

Create `viewer/src/__tests__/layout.test.ts`:

```ts
import { describe, test, expect } from 'vitest';
import { buildFlowElements } from '../lib/layout';
import type { ResourceGraph, ResourceNode } from '../types';

function makeGraph(nodes: ResourceNode[]): ResourceGraph {
  return {
    nodes,
    edges: [],
    summary: {
      total_resources: nodes.length,
      score: 100,
      findings: { critical: 0, high: 0, medium: 0, info: 0 },
      drift: { added: 0, changed: 0, deleted: 0 },
      estimated_monthly_cost: 0,
    },
    metadata: {
      project: 'test',
      scanned_at: '2026-04-17T00:00:00Z',
      source: 'terraform',
    },
  };
}

function makeNode(id: string, type: string, name: string): ResourceNode {
  return {
    id, type, name,
    provider: 'aws',
    module: '',
    region: 'us-east-1',
    group: '',
    attributes: {},
    dependencies: [],
    findings: [],
    cost: { monthly_usd: 0, currency: 'USD', basis: '' },
    drift: 'unchanged',
    position: { x: 0, y: 0 },
  };
}

describe('buildFlowElements — VPC suppression', () => {
  test('omits zone-vpc when VPC has no subnets and no VPC-placed resources', () => {
    const graph = makeGraph([
      makeNode('aws_vpc.main', 'aws_vpc', 'main'),
      makeNode('aws_s3_bucket.logs', 'aws_s3_bucket', 'logs'),
      makeNode('aws_kms_key.key', 'aws_kms_key', 'key'),
    ]);
    const { nodes } = buildFlowElements(graph);
    expect(nodes.find(n => n.id === 'zone-vpc')).toBeUndefined();
    expect(nodes.find(n => n.id === 'zone-regional')).toBeDefined();
  });

  test('emits zone-vpc when subnets exist', () => {
    const subnet = makeNode('aws_subnet.pub', 'aws_subnet', 'pub');
    subnet.attributes = { cidr_block: '10.0.1.0/24', map_public_ip_on_launch: true };
    const graph = makeGraph([
      makeNode('aws_vpc.main', 'aws_vpc', 'main'),
      subnet,
    ]);
    const { nodes } = buildFlowElements(graph);
    expect(nodes.find(n => n.id === 'zone-vpc')).toBeDefined();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd viewer && npm run test -- layout.test.ts`
Expected: FAIL on `omits zone-vpc` — current code always emits `zone-vpc`.

- [ ] **Step 3: Modify `buildFlowElements` to skip empty VPC**

In `viewer/src/lib/layout.ts`, inside `buildFlowElements`, locate the comment `// 2. VPC + AZ + subnet zones` (around line 261). Replace the VPC rendering block (lines 261-308) with:

```ts
  // 2. VPC + AZ + subnet zones (only when VPC has content)
  const vpcHasContent = subnetNodes.length > 0 || resourceToSubnet.size > 0;
  let regionalX = startX;

  if (vpcHasContent) {
    const vpcLabel = vpcNode
      ? `${vpcNode.name} · ${(vpcNode.attributes?.cidr_block as string) ?? ''}`
      : 'VPC';
    flowNodes.push(makeZone('zone-vpc', vpcLabel, 'vpc', startX, vpcStartY, vpcContentW, vpcContentH));

    let azX = VPC_PAD;
    const azBaseY = VPC_LABEL_H;
    const useAZContainers = hasAZ;

    for (const azLayout of azLayouts) {
      const useAZContainer = useAZContainers && azLayout.az !== 'default';
      let subnetParent: string;
      let subnetOffsetX: number;
      let subnetOffsetY: number;

      if (useAZContainer) {
        const azId = `zone-az-${azLayout.az.replace(/[^a-z0-9]/gi, '-')}`;
        flowNodes.push(makeZone(azId, `AZ: ${azLayout.az}`, 'az', azX, azBaseY, azLayout.w, azLayout.h, 'zone-vpc'));
        subnetParent = azId;
        subnetOffsetX = AZ_PAD;
        subnetOffsetY = AZ_LABEL_H;
      } else {
        subnetParent = 'zone-vpc';
        subnetOffsetX = azX;
        subnetOffsetY = azBaseY;
      }

      let sX = subnetOffsetX;

      for (const sl of azLayout.subnets) {
        const subnetId = `zone-subnet-${sl.subnet.id.replace(/[^a-z0-9]/gi, '-')}`;
        const cidr = sl.subnet.attributes?.cidr_block as string | undefined;
        const shortCidr = cidr ? `/${cidr.split('/')[1]}` : '';
        const subnetLabel = `${sl.subnet.name}${shortCidr ? ` · ${shortCidr}` : ''}`;
        const zType: ZoneType = isPublicSubnet(sl.subnet) ? 'public_subnet' : 'private_subnet';

        flowNodes.push(makeZone(subnetId, subnetLabel, zType, sX, subnetOffsetY, sl.w, sl.h, subnetParent));

        sl.resources.forEach((n, i) => {
          flowNodes.push(makeResource(n, SUBNET_PAD + i * (NODE_W + NODE_GAP), SUBNET_LABEL_H + SUBNET_PAD / 2, subnetId));
        });

        sX += sl.w + SUBNET_GAP;
      }

      azX += azLayout.w + AZ_GAP;
    }

    regionalX = startX + vpcContentW + VPC_REG_GAP;
  }
```

Then in the regional services block (currently line 311 area), change the `regX` calculation:

```ts
  // 3. Regional services
  if (regionalNodes.length > 0) {
    // ... existing sizing code unchanged ...
    const regX = regionalX;  // was: startX + vpcContentW + VPC_REG_GAP
    // ... rest unchanged for now ...
```

- [ ] **Step 4: Run layout test**

Run: `cd viewer && npm run test -- layout.test.ts`
Expected: PASS.

- [ ] **Step 5: Run full test suite to confirm no regressions**

Run: `cd viewer && npm run test`
Expected: PASS all.

- [ ] **Step 6: Commit**

```bash
git add viewer/src/lib/layout.ts viewer/src/__tests__/layout.test.ts
git commit -m "feat(viewer): suppress empty VPC zone when no subnets or VPC-placed resources"
```

---

## Task 4: Layout — categorise regional resources

**Files:**
- Modify: `viewer/src/lib/layout.ts`
- Modify: `viewer/src/__tests__/layout.test.ts`

- [ ] **Step 1: Add categorisation test**

Append to `viewer/src/__tests__/layout.test.ts` inside a new `describe`:

```ts
describe('buildFlowElements — regional categorisation', () => {
  test('groups regional resources into category sub-zones', () => {
    const graph = makeGraph([
      makeNode('aws_iam_policy.admin', 'aws_iam_policy', 'admin'),
      makeNode('aws_kms_key.key', 'aws_kms_key', 'key'),
      makeNode('aws_s3_bucket.logs', 'aws_s3_bucket', 'logs'),
      makeNode('aws_db_instance.db', 'aws_db_instance', 'db'),
    ]);
    const { nodes } = buildFlowElements(graph);

    const categoryZones = nodes.filter(
      n => typeof n.id === 'string' && n.id.startsWith('zone-category-'),
    );
    const labels = categoryZones.map(n => (n.data as { label: string }).label);
    expect(labels).toContain('IDENTITY & ACCESS');
    expect(labels).toContain('DATA');
  });

  test('orders categories: identity, data, messaging, observability, network, other', () => {
    const graph = makeGraph([
      makeNode('aws_sns_topic.t', 'aws_sns_topic', 't'),
      makeNode('aws_s3_bucket.b', 'aws_s3_bucket', 'b'),
      makeNode('aws_iam_policy.p', 'aws_iam_policy', 'p'),
    ]);
    const { nodes } = buildFlowElements(graph);
    const categoryZones = nodes
      .filter(n => typeof n.id === 'string' && n.id.startsWith('zone-category-'))
      .sort((a, b) => a.position.y - b.position.y)
      .map(n => (n.data as { label: string }).label);
    expect(categoryZones).toEqual(['IDENTITY & ACCESS', 'DATA', 'MESSAGING']);
  });
});
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd viewer && npm run test -- layout.test.ts`
Expected: FAIL — no category zones exist yet.

- [ ] **Step 3: Add category definitions to layout.ts**

Add to the top of `viewer/src/lib/layout.ts` (after existing constant blocks, before `SUPPRESS_AS_NODE`):

```ts
type CategoryKey = 'identity' | 'data' | 'messaging' | 'observability' | 'network' | 'other';

const CATEGORY_ORDER: CategoryKey[] = ['identity', 'data', 'messaging', 'observability', 'network', 'other'];

const CATEGORY_LABELS: Record<CategoryKey, string> = {
  identity: 'IDENTITY & ACCESS',
  data: 'DATA',
  messaging: 'MESSAGING',
  observability: 'OBSERVABILITY',
  network: 'NETWORK',
  other: 'OTHER',
};

function categorise(type: string): CategoryKey {
  if (
    type.startsWith('aws_iam_') ||
    type === 'aws_kms_key' ||
    type.startsWith('aws_secretsmanager_') ||
    type === 'aws_ssm_parameter'
  ) return 'identity';
  if (
    type === 'aws_s3_bucket' ||
    type === 'aws_db_instance' ||
    type.startsWith('aws_rds_') ||
    type === 'aws_dynamodb_table' ||
    type.startsWith('aws_elasticache_') ||
    type.startsWith('aws_redshift_')
  ) return 'data';
  if (type === 'aws_sqs_queue' || type === 'aws_sns_topic') return 'messaging';
  if (type.startsWith('aws_cloudwatch_')) return 'observability';
  if (type === 'aws_security_group' || type.startsWith('aws_route53_')) return 'network';
  return 'other';
}

const CAT_LABEL_H = 22;
const CAT_GAP = 20;
const CAT_PAD = 12;
```

- [ ] **Step 4: Replace regional services rendering**

In `viewer/src/lib/layout.ts`, replace the entire `// 3. Regional services (right of VPC)` block (originally lines 310-330, now slightly shifted) with:

```ts
  // 3. Regional services — categorised sub-zones
  if (regionalNodes.length > 0) {
    const cols = REG_COLS;

    // Group by category
    const byCategory = new Map<CategoryKey, ResourceNodeData[]>();
    for (const node of regionalNodes) {
      const key = categorise(node.type);
      if (!byCategory.has(key)) byCategory.set(key, []);
      byCategory.get(key)!.push(node);
    }

    // Compute per-category dimensions
    type CatLayout = { key: CategoryKey; label: string; resources: ResourceNodeData[]; w: number; h: number; cols: number };
    const catLayouts: CatLayout[] = [];
    for (const key of CATEGORY_ORDER) {
      const resources = byCategory.get(key);
      if (!resources || resources.length === 0) continue;
      const c = resources.length <= 2 ? 1 : resources.length <= 6 ? 2 : 3;
      const rows = Math.ceil(resources.length / c);
      const catW = c * (NODE_W + NODE_GAP) - NODE_GAP + 2 * CAT_PAD;
      const catH = CAT_LABEL_H + CAT_PAD + rows * (NODE_H + REG_ROW_GAP) - REG_ROW_GAP + CAT_PAD;
      catLayouts.push({ key, label: CATEGORY_LABELS[key], resources, w: catW, h: catH, cols: c });
    }

    const regW = Math.max(...catLayouts.map(c => c.w), cols * (NODE_W + NODE_GAP) - NODE_GAP + 2 * REG_PAD);
    const regH =
      REG_LABEL_H +
      REG_PAD +
      catLayouts.reduce((a, c) => a + c.h, 0) +
      Math.max(0, catLayouts.length - 1) * CAT_GAP +
      REG_PAD;

    flowNodes.push(makeZone('zone-regional', 'Regional Services (AWS)', 'regional', regionalX, vpcStartY, regW, regH));

    let catY = REG_LABEL_H + REG_PAD;
    for (const cat of catLayouts) {
      const catId = `zone-category-${cat.key}`;
      flowNodes.push(makeZone(catId, cat.label, 'category', REG_PAD, catY, cat.w, cat.h, 'zone-regional'));

      cat.resources.forEach((n, i) => {
        const col = i % cat.cols;
        const row = Math.floor(i / cat.cols);
        flowNodes.push(makeResource(
          n,
          CAT_PAD + col * (NODE_W + NODE_GAP),
          CAT_LABEL_H + CAT_PAD / 2 + row * (NODE_H + REG_ROW_GAP),
          catId,
        ));
      });

      catY += cat.h + CAT_GAP;
    }
  }
```

- [ ] **Step 5: Run layout tests**

Run: `cd viewer && npm run test -- layout.test.ts`
Expected: PASS.

- [ ] **Step 6: Run full suite**

Run: `cd viewer && npm run test`
Expected: PASS all.

- [ ] **Step 7: Commit**

```bash
git add viewer/src/lib/layout.ts viewer/src/__tests__/layout.test.ts
git commit -m "feat(viewer): categorise regional resources into semantic sub-zones"
```

---

## Task 5: ResourceNode polish

**Files:**
- Modify: `viewer/src/components/ResourceNode.tsx`

- [ ] **Step 1: Replace the main card div and icon box**

In `viewer/src/components/ResourceNode.tsx`, replace the entire return block (lines 44-258) with:

```tsx
  const hasSeverityAccent = !selected && !isShadow && highestSev !== null;
  const baseBorderColor = selected
    ? '#60a5fa'
    : isShadow
    ? '#f59e0b'
    : isNew
    ? driftColors.added
    : isChanged
    ? driftColors.changed
    : '#252d3d';

  return (
    <div
      style={{ width: 168 }}
      className="relative cursor-pointer"
      onClick={() => setSelectedNode(data)}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-slate-600 !border-slate-700 !w-2 !h-2"
      />

      <div
        style={{
          background: 'linear-gradient(135deg, #0f1419 0%, #1a202c 100%)',
          border: `1.5px ${isShadow ? 'dashed' : 'solid'} ${baseBorderColor}`,
          borderTop: hasSeverityAccent
            ? `2.5px solid ${severityColors[highestSev!]}`
            : `1.5px ${isShadow ? 'dashed' : 'solid'} ${baseBorderColor}`,
          borderRadius: 10,
          padding: '14px 16px',
          opacity: isDeleted ? 0.5 : 1,
          boxShadow: selected
            ? `0 0 0 2px ${baseBorderColor}66, 0 8px 32px rgba(0,0,0,0.6), inset 0 1px 2px rgba(255,255,255,0.05)`
            : '0 4px 16px rgba(0,0,0,0.4), inset 0 1px 2px rgba(255,255,255,0.03)',
          transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
          position: 'relative',
        }}
        onMouseEnter={e => {
          (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-1px)';
          (e.currentTarget as HTMLDivElement).style.boxShadow = hasSeverityAccent
            ? `0 0 0 1px ${severityColors[highestSev!]}55, 0 12px 40px rgba(0,0,0,0.5), inset 0 1px 2px rgba(255,255,255,0.05)`
            : `0 0 0 1px ${baseBorderColor}55, 0 12px 40px rgba(0,0,0,0.5), inset 0 1px 2px rgba(255,255,255,0.05)`;
        }}
        onMouseLeave={e => {
          (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)';
          (e.currentTarget as HTMLDivElement).style.boxShadow = selected
            ? `0 0 0 2px ${baseBorderColor}66, 0 8px 32px rgba(0,0,0,0.6), inset 0 1px 2px rgba(255,255,255,0.05)`
            : '0 4px 16px rgba(0,0,0,0.4), inset 0 1px 2px rgba(255,255,255,0.03)';
        }}
      >
        {/* Header: icon tile + meta */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 11, marginBottom: 10 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              background: svc.color,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: svc.label.length > 3 ? 9 : 11,
              fontWeight: 900,
              fontFamily: 'ui-monospace, monospace',
              color: '#ffffff',
              letterSpacing: '-0.5px',
              flexShrink: 0,
              boxShadow: `0 2px 8px ${svc.color}40, inset 0 1px 1px rgba(255,255,255,0.15)`,
            }}
          >
            {svc.label}
          </div>

          <div style={{ minWidth: 0, flex: 1 }}>
            <div
              style={{
                fontSize: 9.5,
                fontWeight: 700,
                fontFamily: 'ui-monospace, monospace',
                color: '#64748b',
                letterSpacing: '0.6px',
                textTransform: 'uppercase',
                marginBottom: 3,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {typeLabel}
            </div>
            <div
              style={{
                fontSize: 13.5,
                fontWeight: 700,
                color: '#f1f5f9',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                lineHeight: 1.3,
                letterSpacing: '-0.2px',
              }}
              title={data.id}
            >
              {data.name}
            </div>
          </div>
        </div>

        {/* Footer: cost + drift + finding badge */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {data.cost.monthly_usd > 0 && (
              <span
                style={{
                  fontSize: 11,
                  fontFamily: 'ui-monospace, monospace',
                  color: '#94a3b8',
                  fontWeight: 600,
                }}
              >
                ${data.cost.monthly_usd.toFixed(0)}/mo
              </span>
            )}
            {isNew && (
              <span
                style={{
                  fontSize: 7.5,
                  padding: '2px 6px',
                  borderRadius: 4,
                  background: 'rgba(34,197,94,0.15)',
                  color: '#4ade80',
                  fontWeight: 800,
                  border: '1px solid rgba(34,197,94,0.4)',
                  letterSpacing: '0.3px',
                }}
              >
                +NEW
              </span>
            )}
            {isChanged && (
              <span
                style={{
                  fontSize: 7.5,
                  padding: '2px 6px',
                  borderRadius: 4,
                  background: 'rgba(250,204,21,0.15)',
                  color: '#facc15',
                  fontWeight: 800,
                  border: '1px solid rgba(250,204,21,0.4)',
                  letterSpacing: '0.3px',
                }}
              >
                ~CHG
              </span>
            )}
          </div>

          {findingCount > 0 && highestSev ? (
            <div
              style={{
                width: 24,
                height: 24,
                borderRadius: '50%',
                background: `${severityColors[highestSev]}25`,
                border: `1.5px solid ${severityColors[highestSev]}66`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 10,
                fontWeight: 900,
                color: severityColors[highestSev],
                flexShrink: 0,
                boxShadow: `0 0 8px ${severityColors[highestSev]}30`,
              }}
            >
              {findingCount}
            </div>
          ) : (
            <div
              style={{
                width: 20,
                height: 20,
                borderRadius: 6,
                background: 'rgba(34,197,94,0.08)',
                border: '1px solid rgba(34,197,94,0.22)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 10,
                fontWeight: 700,
                color: 'rgba(74,222,128,0.75)',
                flexShrink: 0,
              }}
            >
              ✓
            </div>
          )}
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-slate-600 !border-slate-700 !w-2 !h-2"
      />

      {isShadow && (
        <div style={{ textAlign: 'center', marginTop: 2, fontSize: 9, color: '#f59e0b' }}>
          shadow
        </div>
      )}
    </div>
  );
}
```

Also remove the now-unused `borderColor` declaration (lines 26-36 in the original).

- [ ] **Step 2: Run ResourceNode tests**

Run: `cd viewer && npm run test -- ResourceNode.test.tsx`
Expected: PASS (all four existing tests still pass — label, azurerm prefix, azure config, +NEW badge).

- [ ] **Step 3: Run full suite**

Run: `cd viewer && npm run test`
Expected: PASS all.

- [ ] **Step 4: Commit**

```bash
git add viewer/src/components/ResourceNode.tsx
git commit -m "feat(viewer): severity top-edge accent and simplified icon tile on resource nodes"
```

---

## Task 6: SummaryBar header polish

**Files:**
- Modify: `viewer/src/components/SummaryBar.tsx`

- [ ] **Step 1: Replace the SummaryBar return block**

In `viewer/src/components/SummaryBar.tsx`, replace the entire return block (lines 36-188) with:

```tsx
  return (
    <div
      className="flex items-center gap-4 px-5 shrink-0 z-20"
      style={{
        background: 'linear-gradient(180deg, #0f1419 0%, #1a202c 100%)',
        borderBottom: '1.5px solid #252d3d',
        height: 48,
        boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
      }}
    >
      {/* Project name */}
      <div className="flex items-center gap-2.5">
        <Box size={16} color="#60a5fa" />
        <span className="text-sm font-bold" style={{ color: '#f1f5f9' }}>
          {metadata.project}
        </span>
        <span className="text-xs" style={{ color: '#64748b', fontWeight: 500 }}>
          {scanDate}
        </span>
      </div>

      <div className="w-px h-5" style={{ background: '#252d3d' }} />

      {/* Score badge */}
      <div
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all"
        style={{
          background: scoreBg,
          border: `1.5px solid ${scoreBorder}`,
          boxShadow: `0 2px 8px ${scoreBg}`,
        }}
      >
        <Shield size={14} color={scoreColor} />
        <span className="text-sm font-bold" style={{ color: scoreColor, letterSpacing: '-0.02em' }}>
          {summary.score}
        </span>
        <span className="text-[10px] font-semibold" style={{ color: scoreColor, opacity: 0.6 }}>
          /100
        </span>
      </div>

      <div className="w-px h-5" style={{ background: '#252d3d' }} />

      {/* Severity chips — tightened cluster */}
      <div className="flex items-center gap-2.5">
        {severityOrder.map(sev => {
          const count = summary.findings[sev] ?? 0;
          const isActive = activeSeverities.includes(sev);
          return (
            <button
              key={sev}
              onClick={() => toggleSeverityFilter(sev)}
              className="flex items-center gap-1.5 text-xs font-semibold cursor-pointer transition-all hover:opacity-100"
              style={{
                color: severityColors[sev],
                opacity: isActive ? 1 : 0.45,
                background: 'none',
                border: 'none',
                padding: 0,
              }}
            >
              <span
                style={{
                  width: 7,
                  height: 7,
                  borderRadius: '50%',
                  background: severityColors[sev],
                  display: 'inline-block',
                  flexShrink: 0,
                  boxShadow: `0 0 6px ${severityColors[sev]}40`,
                }}
              />
              {count}
            </button>
          );
        })}
      </div>

      <div className="flex-1" />

      {/* Metadata cluster — single group */}
      <div className="flex items-center gap-3">
        <span className="text-[11px]" style={{ color: '#4a5568' }}>
          {summary.total_resources} resources
        </span>
        {summary.estimated_monthly_cost > 0 && (
          <span className="text-[11px] font-medium" style={{ color: '#22c55e' }}>
            ${summary.estimated_monthly_cost.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}/mo
          </span>
        )}
        {(summary.drift.added > 0 || summary.drift.changed > 0 || summary.drift.deleted > 0) && (
          <div className="flex items-center gap-1.5 text-[10px] font-medium">
            {summary.drift.added > 0 && <span style={{ color: '#22c55e' }}>+{summary.drift.added}</span>}
            {summary.drift.changed > 0 && <span style={{ color: '#eab308' }}>~{summary.drift.changed}</span>}
            {summary.drift.deleted > 0 && <span style={{ color: '#ef4444' }}>-{summary.drift.deleted}</span>}
          </div>
        )}
      </div>

      {/* Edge legend — behind hover "?" */}
      <div className="relative group">
        <button
          className="flex items-center justify-center rounded-full text-[10px] font-bold cursor-help transition-all"
          style={{
            width: 20,
            height: 20,
            background: 'transparent',
            border: '1.5px solid #2d3748',
            color: '#64748b',
          }}
          aria-label="Edge legend"
        >
          ?
        </button>
        <div
          className="absolute right-0 top-full mt-2 hidden group-hover:flex flex-col gap-1.5 px-3 py-2 rounded-lg z-30 text-[10px]"
          style={{
            background: '#0f1419',
            border: '1.5px solid #252d3d',
            boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
            color: '#94a3b8',
            minWidth: 140,
          }}
        >
          <span className="flex items-center gap-2">
            <svg width="22" height="6">
              <line x1="0" y1="3" x2="16" y2="3" stroke="rgba(71,85,105,0.6)" strokeWidth="1.5" />
              <polygon points="16,1 22,3 16,5" fill="rgba(71,85,105,0.6)" />
            </svg>
            traffic
          </span>
          <span className="flex items-center gap-2">
            <svg width="22" height="6">
              <line x1="0" y1="3" x2="16" y2="3" stroke="rgba(59,130,246,0.45)" strokeWidth="1.5" strokeDasharray="5 3" />
              <polygon points="16,1 22,3 16,5" fill="rgba(59,130,246,0.45)" />
            </svg>
            access
          </span>
          <span className="flex items-center gap-2">
            <svg width="22" height="6">
              <line x1="0" y1="3" x2="22" y2="3" stroke="rgba(221,52,76,0.4)" strokeWidth="1" strokeDasharray="3 2" />
            </svg>
            security
          </span>
        </div>
      </div>

      <SearchBar />

      <button
        onClick={toggleFilterPanel}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition-all hover:border-slate-500"
        style={{
          background: filterPanelOpen ? 'rgba(45,55,72,0.6)' : 'transparent',
          color: filterPanelOpen ? '#f1f5f9' : '#64748b',
          border: `1.5px solid ${filterPanelOpen ? '#404d5c' : '#2d3748'}`,
        }}
      >
        <Filter size={14} />
        Filters
      </button>
    </div>
  );
```

- [ ] **Step 2: Run tests**

Run: `cd viewer && npm run test`
Expected: PASS all.

- [ ] **Step 3: Commit**

```bash
git add viewer/src/components/SummaryBar.tsx
git commit -m "feat(viewer): tighten header with legend tooltip and metadata cluster"
```

---

## Task 7: Build check + manual verification

**Files:**
- None modified. Pure verification task.

- [ ] **Step 1: TypeScript build**

Run: `cd viewer && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 2: Full test suite**

Run: `cd viewer && npm run test`
Expected: all pass.

- [ ] **Step 3: Build viewer bundle**

Run: `cd viewer && npm run build`
Expected: bundle produced in `viewer/dist/` without errors.

- [ ] **Step 4: Run CLI scan and open HTML**

Run from repo root:

```bash
cd cli && pip install -e . --quiet
infracanvas scan tests/fixtures/insecure_setup --out /tmp/infracanvas-verify.html
open /tmp/infracanvas-verify.html
```

Expected visual outcome:
- No empty VPC container on the left.
- Seven resources appear inside "Regional Services (AWS)", split across **IDENTITY & ACCESS** (IAM policy, KMS key), **DATA** (S3 public_data, S3 logs, RDS exposed_db), **NETWORK** (security group open_sg), and either compute (EC2 untagged) landing in **OTHER**.
- Header feels tighter; edge legend is not visible until you hover the `?` icon next to Filters.
- Resource cards have a thin coloured bar along the top edge (severity colour) rather than a full coloured border.

- [ ] **Step 5: Verify against populated-VPC fixture (regression check)**

If a fixture with subnets exists (check `ls cli/tests/fixtures/`), run:

```bash
infracanvas scan cli/tests/fixtures/<fixture-with-subnets> --out /tmp/infracanvas-vpc.html
open /tmp/infracanvas-vpc.html
```

Expected: VPC zone renders normally with subnets/AZ grouping intact. Regional services still categorise.

- [ ] **Step 6: Final commit note (if any polish tweaks were needed)**

If manual verification surfaced a minor issue, fix it in-place and commit with message describing the tweak. Otherwise, this task has no commit — verification only.

---

## Self-Review Results

**Spec coverage:**
- VPC suppression → Task 3 ✓
- Category sub-sections (identity/data/messaging/observability/network/other) → Task 4 ✓
- Column auto-sizing (≤2/3-6/7+) → Task 4 step 4 (`c = resources.length <= 2 ? 1 : resources.length <= 6 ? 2 : 3`) ✓
- New layout constants (`CAT_LABEL_H`, `CAT_GAP`, `CAT_INNER_GAP`) → Task 4 step 3 (named `CAT_PAD` — this replaces `CAT_INNER_GAP` from the spec as a single padding constant for both inner gaps; functionally equivalent) ✓
- Severity top-edge accent → Task 5 ✓
- Icon box simplification → Task 5 ✓
- Hover lift reduced to -1px → Task 5 ✓
- Clean ✓ badge dimmed → Task 5 ✓
- Group label anchored inside → Task 2 ✓
- New `category` zone type → Task 1 + Task 2 ✓
- Edge legend behind `?` → Task 6 ✓
- Metadata cluster on right → Task 6 ✓
- Score numeric weight / /100 dim → Task 6 ✓
- Severity dot gap tightened → Task 6 ✓

**Placeholder scan:** No TBD/TODO/"add appropriate error handling" patterns. All code blocks complete.

**Type consistency:** `CategoryKey` / `CATEGORY_ORDER` / `CATEGORY_LABELS` / `categorise()` all share the same union. `ZoneType` extended consistently across `colors.ts` and used in `layout.ts` / `GroupNode.tsx`. `zone-category-${key}` id scheme is consistent between layout emission (Task 4) and the test (Task 4 step 1).
