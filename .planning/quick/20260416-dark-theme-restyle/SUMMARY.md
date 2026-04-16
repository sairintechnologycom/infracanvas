---
slug: dark-theme-restyle
date: 2026-04-16
status: complete
---

# Summary

Completed full dark professional theme restyle across 9 files. Zero TypeScript errors, all 30 tests pass.

## Changes Made
- `index.css` — canvas bg #0f1117, dot-grid, dark controls/minimap
- `awsServiceConfig.ts` — new service color+label registry (20 AWS types)
- `ResourceNode.tsx` — #1c2333 cards, colored icon box, meta column, hover lift
- `GroupNode.tsx` — floating pill labels at top:-11px, per-zone styling
- `SummaryBar.tsx` — #161b27 toolbar, score pill, dot+count chips, dark legend SVGs
- `FilterPanel.tsx` — dark sidebar (#161b27 bg, #252d3d borders)
- `DetailPanel.tsx` — dark sidebar, dark dependency pills, dark change rows
- `DiagramCanvas.tsx` — dark minimap mask, dot-grid background
- `colors.ts` — ZONE_COLORS extended with pill/borderWidth/borderStyle; EDGE_STYLES updated for dark palette

## Commit
76b0eb3
