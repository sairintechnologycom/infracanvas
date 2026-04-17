# Viewer Professional Polish — Design

**Date:** 2026-04-17
**Scope:** `viewer/src/components/{ResourceNode,GroupNode,SummaryBar}.tsx` and `viewer/src/lib/layout.ts`
**Goal:** Make the InfraCanvas diagram read as a polished, professional tool — not a prototype.

## Problem

The `insecure_setup` render (see `cli/tests/fixtures/insecure_setup`) exhibits four issues:

1. **Empty VPC container** dominates the left half. Root cause: fixture declares `aws_vpc` but has no subnets or VPC-placed resources. `layout.ts` falls back to a 400×200 empty VPC shell (`lib/layout.ts` lines 233-238).
2. **Unbalanced composition** — right side crowded (2-col × 4-row regional grid), left side empty.
3. **Flat semantic structure** — all 7 resources dumped in one "Regional Services" box with no sub-grouping. Reader cannot see at a glance "what kinds of things exist here".
4. **Header spread thin** — score, severity dots, resource count, cost, drift, edge legend, search, filter button all compete across 48px top bar.

## Non-goals

- No new zone graphics, grid backgrounds, or animations.
- No changes to edge inference logic. Fixtures without explicit dependencies continue to show no edges.
- No changes to `DetailPanel`, `FilterPanel`, or `DiagramCanvas`.

## Design

### 1. Layout (`viewer/src/lib/layout.ts`)

**Suppress empty VPC zone**

Introduce:

```ts
const vpcHasContent = subnetNodes.length > 0 || resourceToSubnet.size > 0;
```

When `vpcHasContent === false`:
- Do not emit the `zone-vpc` group node.
- Regional zone anchors at `startX` (current left edge) instead of `startX + vpcContentW + VPC_REG_GAP`.
- `vpcStartY` logic unchanged (internet zone still takes its vertical slot if present).

**Semantic categorisation inside Regional Services**

Replace the current flat 2-column grid with category sub-sections. Category definitions:

| Category | Label | AWS types | Azure mapping (future) |
|---|---|---|---|
| identity | `IDENTITY & ACCESS` | `aws_iam_*`, `aws_kms_key`, `aws_secretsmanager_*`, `aws_ssm_parameter` | `azurerm_role_*`, `azurerm_key_vault*` |
| data | `DATA` | `aws_s3_bucket`, `aws_db_instance`, `aws_rds_*`, `aws_dynamodb_table`, `aws_elasticache_*`, `aws_redshift_*` | `azurerm_storage_*`, `azurerm_*_database*` |
| messaging | `MESSAGING` | `aws_sqs_queue`, `aws_sns_topic` | `azurerm_servicebus_*` |
| observability | `OBSERVABILITY` | `aws_cloudwatch_*` | `azurerm_monitor_*` |
| network | `NETWORK` | `aws_security_group` (unplaced), `aws_route53_*` (when not in Internet zone) | — |
| other | `OTHER` | anything else falling to regional | — |

Only non-empty categories render. Order is fixed (identity → data → messaging → observability → network → other).

**Per-category column auto-sizing**

```ts
function colsFor(count: number): number {
  if (count <= 2) return 1;
  if (count <= 6) return 2;
  return 3;
}
```

**Layout constants (new):**

- `CAT_LABEL_H = 22` — height reserved for category sub-label
- `CAT_GAP = 20` — vertical gap between categories
- `CAT_INNER_GAP = 12` — gap between the sub-label and first node row

**Regional zone sizing** becomes the sum of all rendered category blocks plus `CAT_GAP` between them, plus the zone's own label + padding.

### 2. Resource node polish (`viewer/src/components/ResourceNode.tsx`)

- **Severity as top-edge accent.** Replace the full-perimeter coloured border with a neutral 1px `#252d3d` border on all four sides, plus a 2px top strip (`borderTop`) coloured by severity. Selected state keeps a full-perimeter border (current `selected ? '#60a5fa'` logic). Shadow drift nodes keep dashed full border.
- **Icon box simplification.** Drop the inner rounded-square tile. Render the service label directly on the outer tile with the service colour as background. Reduces the "tile-in-tile" visual noise.
- **Hover.** `translateY(-2px)` → `translateY(-1px)`. Shadow glow unchanged.
- **Clean ✓ badge.** Dim from `rgba(34,197,94,0.35)` border to `rgba(34,197,94,0.22)`, reduce icon size from 12 to 10. It should not compete for attention with real findings.
- **Footer layout** unchanged — cost/drift left, finding badge right.

### 3. Group node polish (`viewer/src/components/GroupNode.tsx`)

- **Zone label anchoring.** Move pill from floating `top: -11` to `top: 10, left: 14` inside the container. Adjust zone padding in `layout.ts` if needed to preserve resource top offset (currently `VPC_LABEL_H = 40` — this already accommodates an inside label).
- **New `category` zone type.** Smaller pill (font 9px, padding 1px 6px, muted pill colour `rgba(45,55,72,0.5)` with text `#94a3b8`). Used only for the category sub-sections inside Regional Services.
- **`ZONE_COLORS.category`** added to `viewer/src/lib/colors.ts`.

### 4. Header (`viewer/src/components/SummaryBar.tsx`)

- **Edge legend** → move behind a `?` icon button positioned next to Filters. Hover reveals the current SVG legend as a tooltip-style absolutely-positioned panel. Frees approximately 180px.
- **Metadata cluster on right.** `{resource count} · ${cost}/mo` plus drift chips (if any) render as a single muted group with one leading separator. Currently these are three separate items with varying styles.
- **Score numeric weight.** Score stays `text-sm font-bold`; `/100` drops from `text-xs font-semibold opacity-0.8` to `text-[10px] font-semibold opacity-0.6` so the number dominates.
- **Severity dot gap** tightens from `gap-3.5` to `gap-2.5`. Cluster reads as one unit.

## Test / verification

- Manual: re-run `infracanvas scan cli/tests/fixtures/insecure_setup` and open the HTML. Expect: no empty VPC box; 7 resources grouped into Identity & Access / Data / Network sub-sections inside Regional Services; cleaner header.
- Manual: re-run against a fixture with a populated VPC (e.g. `cli/tests/fixtures/multi_az` if it exists, otherwise any fixture with `aws_subnet`) to confirm VPC still renders normally with subnets and AZ grouping intact.
- Existing `vitest` component tests in `viewer/` continue to pass. No snapshot tests are in scope here; if any exist for the affected components they will need updating.

## Risk / rollback

- Risk: edge cases in category assignment for types not enumerated. Mitigation: `other` catches all unknowns.
- Risk: regional zone becomes taller due to category sub-labels. Mitigation: column auto-sizing keeps width bounded; height is acceptable since the diagram is scrollable.
- Rollback: revert the four files in a single commit.
