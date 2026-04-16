---
slug: dark-theme-restyle
date: 2026-04-16
status: in-progress
---

# Dark Professional Theme — Viewer Visual Restyle

## Goal
Switch InfraCanvas viewer from light AWS palette to a dark professional theme.
No logic changes — pure visual/styling layer only.

## Tasks
1. Create `viewer/src/icons/awsServiceConfig.ts`
2. Update `viewer/src/index.css` — dark global theme
3. Update `viewer/src/components/ResourceNode.tsx` — dark card restyle
4. Update `viewer/src/lib/colors.ts` — update ZONE_COLORS for dark theme
5. Update `viewer/src/components/GroupNode.tsx` — pill labels + dark groups
6. Update `viewer/src/components/SummaryBar.tsx` — dark toolbar
7. Update `viewer/src/components/DiagramCanvas.tsx` — dark canvas + minimap
