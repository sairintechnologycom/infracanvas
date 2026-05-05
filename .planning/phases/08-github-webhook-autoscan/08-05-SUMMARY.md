---
phase: 8
plan: "08-05"
subsystem: dashboard-ui
tags: [tdd, badge, webhook, auto-scan, vitest]
dependency_graph:
  requires: ["08-02"]
  provides: ["SourceCell export", "Auto-scan badge in ScansTable and MetadataHeader"]
  affects: ["dashboard/components/scans/ScansTable.tsx", "dashboard/components/scans/MetadataHeader.tsx"]
tech_stack:
  added: []
  patterns: ["TDD RED/GREEN", "named export from component file", "conditional JSX render"]
key_files:
  created:
    - dashboard/components/scans/ScansTable.test.tsx
    - dashboard/components/scans/MetadataHeader.test.tsx
  modified:
    - dashboard/components/scans/ScansTable.tsx
    - dashboard/components/scans/MetadataHeader.tsx
    - dashboard/lib/types.ts
    - dashboard/vitest.config.ts
decisions:
  - "Added 'github' and 'webhook' to ScanListItem.source union — context_note stated both values are live in the system"
  - "Extended vitest.config.ts include to cover components/**/*.test.{ts,tsx} — plan placed test files under components/scans/ which was outside the prior include pattern"
  - "SourceCell handles both 'github' and 'github_webhook' for GitHub label — future-proofs against both legacy and current source values"
metrics:
  duration: "4m 6s"
  completed: "2026-05-05T12:51:16Z"
  tasks_completed: 2
  files_changed: 6
---

# Phase 8 Plan 05: Auto-scan Badge in ScansTable and MetadataHeader Summary

Auto-scan badge wired via `source === 'webhook'` conditional in SourceCell (Zap icon) and MetadataHeader (`data-testid=auto-scan-badge` span); 4 vitest tests RED then GREEN.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | TDD RED — 4 failing tests for Auto-scan badge | 64c93c0 | ScansTable.test.tsx, MetadataHeader.test.tsx, types.ts, vitest.config.ts |
| 2 | TDD GREEN — add Auto-scan badge to SourceCell and MetadataHeader | a89a322 | ScansTable.tsx, MetadataHeader.tsx, types.ts |

## What Was Built

**ScansTable.tsx — SourceCell:**
- Added `export` keyword so the function is importable in tests
- Added `Zap` to lucide-react import (violet-500 color)
- New `source === 'webhook'` branch: renders `<Zap size={14} />` + 'Auto-scan' text
- Updated `source === 'github_webhook'` to also handle `source === 'github'` (covers both legacy and current GitHub manual scan source values)

**MetadataHeader.tsx:**
- Added `{scan.source === 'webhook' && <span data-testid="auto-scan-badge">Auto-scan</span>}` after the commit_sha span
- Badge styled: `bg-violet-100 text-violet-700 rounded text-xs font-medium` inline-flex

**dashboard/lib/types.ts:**
- Added `'github'` and `'webhook'` to `ScanListItem.source` union (was `'cli' | 'manual' | 'github_webhook' | null`)

**dashboard/vitest.config.ts:**
- Extended `include` to cover `components/**/*.test.{ts,tsx}` so test files co-located with components are discovered

## TDD Gate Compliance

RED gate: `test(08-05)` commit `64c93c0` — 3 failures confirmed before implementation
GREEN gate: `feat(08-05)` commit `a89a322` — 4/4 tests pass

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added 'github' to ScanListItem.source union**
- **Found during:** Task 2 — TypeScript strict-mode check flagged `source === 'github'` as dead comparison
- **Issue:** The `SourceCell` test uses `source="github"` and the context_note confirms 'github' is a live source value, but `ScanListItem.source` didn't include it
- **Fix:** Added `'github'` to the union alongside `'webhook'`
- **Files modified:** `dashboard/lib/types.ts`
- **Commit:** a89a322

**2. [Rule 3 - Blocking] Extended vitest.config.ts include pattern**
- **Found during:** Task 1 — vitest refused to run files at `components/scans/*.test.tsx` because the `include` filter only covered `__tests__/`, `lib/`, and `app/`
- **Issue:** Plan specified test file paths under `components/scans/` but vitest config didn't include that glob
- **Fix:** Added `components/**/*.test.{ts,tsx}` to the `include` array
- **Files modified:** `dashboard/vitest.config.ts`
- **Commit:** 64c93c0

## Known Stubs

None — both SourceCell and MetadataHeader render real data from their props with no placeholder values.

## Verification Results

```
vitest run components/scans/ScansTable.test.tsx components/scans/MetadataHeader.test.tsx
  4 passed (4)

Full suite: 229 passed (229) — was 225 pre-plan

tsc --noEmit: 0 new errors
  (pre-existing: __tests__/scan-filters.test.tsx TS6133 — deferred from Plan 01)
```

## Self-Check: PASSED

- dashboard/components/scans/ScansTable.test.tsx — exists
- dashboard/components/scans/MetadataHeader.test.tsx — exists
- dashboard/components/scans/ScansTable.tsx — modified (webhook branch + export)
- dashboard/components/scans/MetadataHeader.tsx — modified (auto-scan-badge)
- Commits 64c93c0 and a89a322 — both present in git log
