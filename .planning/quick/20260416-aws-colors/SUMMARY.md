---
status: complete
date: 2026-04-16
commit: 95decfa
files_changed: 3
---

# Quick Task: AWS-Convention Color Scheme

## One-liner

Replaced flat Tailwind-palette colors with AWS-convention category colors — VPC/networking purple, compute orange, storage green, database blue, security red — and tightened zone background/border opacity for visual hierarchy.

## Changes Applied

### colors.ts
- ZONE_COLORS: updated all seven zone entries with new background/border/label values; VPC now uses AWS purple, subnets use distinct green/blue/purple
- resourceTypeColors: replaced 15-entry flat map with 21-entry categorized map using AWS service-category colors; added aws_internet_gateway, aws_nat_gateway, aws_eip

### ResourceNode.tsx
- Added getResourceColor to import
- Card background changed to solid #1a2535
- Added borderLeft: 3px solid {getResourceColor(data.type)} for per-category color stripe
- Type label color changed from #475569 to #7a9abf
- Clean check icon colors updated to rgba(46,204,113,...) values

### GroupNode.tsx
- Zone label: added textTransform uppercase, letterSpacing 0.06em
- az zone labels receive opacity 0.80

## Deviations

None — plan executed exactly as written.
