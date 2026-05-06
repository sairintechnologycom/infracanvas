---
plan: 01-05
phase: 01-canvas-mvp
status: complete
completed: 2026-04-16
tasks_total: 2
tasks_completed: 2
commits:
  - "7fdcb55 feat(01-05): wire 15 resource types, shadow pipeline, viewer build verified"
tests_passed: 187
self_check: PASSED
---

## Summary

Wired all 15 AWS resource types into layout tiers (already complete in layout.ts) and icon mappings (added 4 missing families), integrated shadow infra and module resolution into the scan pipeline, and verified the Vite viewer build produces a single-file HTML under 5MB.

## What Was Built

### Task 1: Resource types, icons, scan pipeline wiring
- `viewer/src/lib/layout.ts` — already had all 15 types across RESOURCE_TIER + SUPPRESS_AS_NODE + getResourceTier(); verified complete
- `viewer/src/components/icons/ResourceIcon.tsx` — added icon shapes for `aws_eks` (hexagon+circle), `aws_nat` (arrow gateway), `aws_cloudwatch_log` (document with lines), `aws_elasticache` (stacked ellipses); all handled via family prefix matching
- `viewer/src/lib/colors.ts` — added `shadow: '#d97706'` to driftColors (DriftStatus.shadow was added in 01-03 but color was missing)
- `cli/infracanvas/main.py` — wired `resolve_modules(directory, parsed)` after `parse_directory()` (PRS-04) and `flag_shadow_resources(graph, state)` when `terraform.tfstate` exists (PRS-05)
- `viewer/src/__tests__/FreeGate.test.tsx` — fixed mock selector type annotation to satisfy TS strict mode

### Task 2: Viewer build verification
- `npm run build` → clean tsc + vite, 421KB single-file HTML
- `dist/index.html` contains `__INFRACANVAS_DATA__` placeholder ✓
- No external `<script src=` tags (fully inlined) ✓
- Under 5MB limit (421KB) ✓

## Test Results

- 157 Python tests passing (cli/.venv/bin/pytest)
- 30 viewer tests passing (vitest)
- Viewer build: clean, 421KB

## Deviations

1. **layout.ts already complete** — all 15 resource types were already in RESOURCE_TIER from Phase 3 work. No changes needed; verified correct.
2. **colors.ts fix** — DriftStatus.shadow was added in 01-03 but driftColors wasn't updated, causing a TS build error. Fixed as part of this plan.
3. **FreeGate.test.tsx type fix** — mock selector needed `any` type annotation to satisfy TS strict mode (test-only, no production impact).
