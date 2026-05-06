---
phase: 09-costlens
plan: "01"
subsystem: costlens
tags: [wave-0, test-stubs, shadcn, tdd-red]
dependency_graph:
  requires: []
  provides:
    - cli/tests/test_costlens.py
    - viewer/src/__tests__/costlens/CostLensPanel.test.tsx
    - dashboard/components/scans/WorkloadTable.test.tsx
    - dashboard/components/ui/badge.tsx
    - dashboard/components/ui/tooltip.tsx
  affects:
    - plans 09-02, 09-03, 09-04 (can import test_costlens.py stubs)
    - plans 09-05, 09-06, 09-07 (badge and tooltip available for dashboard UI)
tech_stack:
  added:
    - shadcn Badge component (CVA-based, 6 variants)
    - shadcn Tooltip component (Radix-based, TooltipProvider pattern)
  patterns:
    - pytest.mark.xfail(reason="not implemented — stub") for RED test stubs
    - it.todo() for Vitest Wave 0 pending tests
key_files:
  created:
    - dashboard/components/ui/badge.tsx
    - dashboard/components/ui/tooltip.tsx
    - cli/tests/test_costlens.py
    - viewer/src/__tests__/costlens/CostLensPanel.test.tsx
    - dashboard/components/scans/WorkloadTable.test.tsx
  modified: []
decisions:
  - Used pytest.mark.xfail on each stub method (not pytest.fail() alone) so the suite reports correctly as xfail rather than erroring
  - Used it.todo() (not it.skip()) for Vitest stubs — correct Wave 0 state; todo tests show as pending, not failures
metrics:
  duration_seconds: 177
  completed_date: "2026-05-06"
  tasks_completed: 3
  files_created: 5
  files_modified: 0
---

# Phase 9 Plan 01: Wave 0 Infrastructure Summary

Wave 0 infrastructure complete — shadcn Badge and Tooltip installed, 18 pytest RED stubs and 11 Vitest todo stubs in place for all CostLens test targets.

## What Was Built

**Task 1 — shadcn Badge and Tooltip (commit 7a1d181)**

Installed `badge.tsx` and `tooltip.tsx` via `npx shadcn@latest add badge tooltip` against the project's new-york/slate preset. Both match the CVA + Radix pattern used by other components.

- `badge.tsx`: exports `Badge` and `badgeVariants`; 6 variants (default, secondary, destructive, outline, ghost, link)
- `tooltip.tsx`: exports `Tooltip`, `TooltipTrigger`, `TooltipContent`, `TooltipProvider`

**Task 2 — Python test stubs (commit a2c6520)**

Created `cli/tests/test_costlens.py` with 18 test methods across 3 classes, all marked `pytest.mark.xfail(reason="not implemented — stub")`. Imports from `infracanvas.cost.{allocator,idle,egress}` intentionally fail at collection (RED state — these modules land in Plans 02/03/04).

| Class | Tests | Coverage |
|-------|-------|---------|
| TestSharedAllocator | 9 | CLA-C-1..9 |
| TestIdleDetector | 6 | CLA-C-10..15 |
| TestEgressEstimator | 3 | CPC-C-1..3 |

**Task 3 — Viewer and dashboard test stubs (commit 61fba6f)**

Created `viewer/src/__tests__/costlens/CostLensPanel.test.tsx` (6 `it.todo` stubs) and `dashboard/components/scans/WorkloadTable.test.tsx` (5 `it.todo` stubs). Both test runners accepted the files without crash.

- Viewer: 149 tests total (143 pass + 6 todo)
- Dashboard: 238 tests total (233 pass + 5 todo)

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

**Files verified:**
- `dashboard/components/ui/badge.tsx` — FOUND
- `dashboard/components/ui/tooltip.tsx` — FOUND
- `cli/tests/test_costlens.py` — FOUND (18 test methods, grep -c "def test_" = 18)
- `viewer/src/__tests__/costlens/CostLensPanel.test.tsx` — FOUND (6 it.todo)
- `dashboard/components/scans/WorkloadTable.test.tsx` — FOUND (5 it.todo)

**Commits verified:**
- `7a1d181` — shadcn badge + tooltip
- `a2c6520` — Python RED test stubs
- `61fba6f` — Viewer + dashboard test stubs
