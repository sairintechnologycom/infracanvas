---
quick_id: 260416-jke
type: quick
autonomous: true
files_modified:
  - viewer/src/lib/colors.ts
  - viewer/src/components/ResourceNode.tsx
  - viewer/src/components/GroupNode.tsx
---

<objective>
Redesign the viewer color scheme to match AWS/Azure architecture diagram conventions.
Replace neon greens, oranges, and low-contrast dark tones with official AWS palette colors — category-based resource colors, proper VPC/subnet zone fills, and cleaner card visual design.

Output: Updated colors.ts with AWS palette, updated ResourceNode with left-border accent, updated GroupNode with improved AZ label styling.
</objective>

<execution_context>
@/Users/bhushan/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@/Users/bhushan/Documents/Projects/Infracanvas/viewer/src/lib/colors.ts
@/Users/bhushan/Documents/Projects/Infracanvas/viewer/src/components/ResourceNode.tsx
@/Users/bhushan/Documents/Projects/Infracanvas/viewer/src/components/GroupNode.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Rewrite colors.ts with AWS palette</name>
  <files>viewer/src/lib/colors.ts</files>
  <action>
Replace the ZONE_COLORS and resourceTypeColors objects with the AWS architecture diagram palette. All other exports (severityColors, driftColors, edgeColors, EDGE_STYLES, getResourceColor, getHighestSeverity) remain unchanged — only the values inside ZONE_COLORS and resourceTypeColors change.

ZONE_COLORS new values:

```typescript
vpc: {
  background: 'rgba(119,91,163,0.12)',
  border: '#7B5EA7',
  label: '#a882dc',
},
public_subnet: {
  background: 'rgba(0,153,77,0.08)',
  border: 'rgba(0,153,77,0.45)',
  label: '#2ecc71',
},
private_subnet: {
  background: 'rgba(0,115,187,0.08)',
  border: 'rgba(0,115,187,0.40)',
  label: '#4a9fd4',
},
data_subnet: {
  background: 'rgba(140,79,255,0.07)',
  border: 'rgba(140,79,255,0.35)',
  label: '#a07ddb',
},
az: {
  background: 'transparent',
  border: 'rgba(140,155,180,0.28)',
  label: '#7a92b4',
},
internet: {
  background: 'rgba(100,120,160,0.05)',
  border: 'rgba(140,160,200,0.28)',
  label: '#8fa8cc',
},
regional: {
  background: 'rgba(50,80,130,0.07)',
  border: 'rgba(73,144,200,0.30)',
  label: '#6ba3cc',
},
```

resourceTypeColors new values (category-grouped, AWS official palette):

```typescript
// Compute — AWS orange
aws_instance: '#FF9900',
aws_lambda_function: '#FF9900',
// Storage — AWS green
aws_s3_bucket: '#3F8624',
// Database — AWS blue
aws_rds_instance: '#2E73B8',
aws_db_instance: '#2E73B8',
aws_dynamodb_table: '#2E73B8',
// Networking — AWS purple
aws_vpc: '#8C4FFF',
aws_subnet: '#8C4FFF',
aws_alb: '#8C4FFF',
aws_lb: '#8C4FFF',
aws_internet_gateway: '#8C4FFF',
aws_nat_gateway: '#8C4FFF',
aws_eip: '#8C4FFF',
// Security — AWS red
aws_security_group: '#DD344C',
aws_kms_key: '#DD344C',
aws_iam_role: '#DD344C',
aws_iam_policy: '#DD344C',
// CDN — deep purple
aws_cloudfront_distribution: '#7B2FBE',
```

Do not change the getResourceColor fallback logic or any other function.
  </action>
  <verify>
    <automated>cd /Users/bhushan/Documents/Projects/Infracanvas/viewer && npx tsc --noEmit 2>&1 | head -20</automated>
  </verify>
  <done>colors.ts compiles with no TypeScript errors; ZONE_COLORS and resourceTypeColors reflect AWS palette values exactly as specified above.</done>
</task>

<task type="auto">
  <name>Task 2: Update ResourceNode and GroupNode visual design</name>
  <files>viewer/src/components/ResourceNode.tsx, viewer/src/components/GroupNode.tsx</files>
  <action>
**ResourceNode.tsx — three targeted changes only:**

1. Card background: change `rgba(15, 23, 42, 0.97)` → `#1a2535`.

2. Add a 3px left border accent using the resource's category color. Import `getResourceColor` from colors (it is already imported via the destructure — add it). Apply as `borderLeft: \`3px solid ${getResourceColor(data.type)}\`` alongside the existing border property on the outer card div. The existing `border` (top/right/bottom) drives severity/drift state, so use `borderLeft` as an override for the accent. Concretely, update the card style object:

```typescript
// current
border: `1.5px ${isShadow ? 'dashed' : 'solid'} ${borderColor}`,

// new — keep existing border but override left side with category accent
border: `1.5px ${isShadow ? 'dashed' : 'solid'} ${borderColor}`,
borderLeft: `3px solid ${getResourceColor(data.type)}`,
```

Note: import getResourceColor — it is in the same colors import line. Add it to the destructure: `import { severityColors, driftColors, getHighestSeverity, getResourceColor } from '../lib/colors';`

3. Type label color: change `color: '#475569'` → `color: '#7a9abf'`.

4. Clean check icon: change `background: 'rgba(34,197,94,0.12)'` → `rgba(46,204,113,0.15)` and `border: '1px solid rgba(34,197,94,0.35)'` → `rgba(46,204,113,0.40)`. (The check icon is the ✓ div shown when findingCount === 0.)

No other changes to ResourceNode.tsx.

---

**GroupNode.tsx — one targeted change:**

AZ label: when `data.zoneType === 'az'`, apply uppercase + slightly reduced opacity for a muted style. Update the zone label div to add a conditional `textTransform`:

```typescript
style={{
  // ... existing styles ...
  textTransform: data.zoneType === 'az' ? 'uppercase' : 'none',
  opacity: data.zoneType === 'az' ? 0.75 : 1,
}}
```

No other changes to GroupNode.tsx.
  </action>
  <verify>
    <automated>cd /Users/bhushan/Documents/Projects/Infracanvas/viewer && npx tsc --noEmit 2>&1 | head -20</automated>
  </verify>
  <done>
Both files compile with no TypeScript errors.
ResourceNode cards show: lighter background (#1a2535), 3px left-border in category color, readable type label (#7a9abf), softer clean check icon.
GroupNode AZ labels render uppercase and muted.
  </done>
</task>

</tasks>

<verification>
After both tasks:
1. `cd viewer && npx tsc --noEmit` — zero errors
2. `npm run build` in viewer/ — clean build, no warnings about missing exports
3. Visual spot-check: open any generated HTML report and confirm VPC group border is purple (#7B5EA7), public subnet is green, resource cards have visible left-color accent
</verification>

<success_criteria>
- ZONE_COLORS uses AWS VPC purple, green public subnet, blue private subnet
- resourceTypeColors groups resources by AWS service category with official AWS palette colors
- ResourceNode cards have #1a2535 background, 3px left accent in category color, #7a9abf type label
- GroupNode AZ labels are uppercase + muted
- Zero TypeScript compilation errors
- No logic changes — purely visual/style values
</success_criteria>

<output>
After completion, update `.planning/quick/20260416-aws-colors/SUMMARY.md` with what changed and the final state of each file.
</output>
```
