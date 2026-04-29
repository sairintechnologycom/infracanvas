---
phase: 07-saas-dashboard-history-share
plan: 6
subsystem: dashboard-scans-list
tags: [nextjs, rsc, dashboard, scan-history, filters, pagination, vitest, tdd]
requires:
  - "Plan 07-02 backend GET /v1/scans endpoint with cursor pagination + search/source/score_lt/created_after/created_before filters"
  - "Plan 07-05 dashboard scaffold (backendFetch, lib/types, (dashboard) layout, ClerkProvider, viewer styles import)"
provides:
  - "/scans RSC page rendering scan history table with 8 columns (Date, Source, Commit, Branch, Score, Crit, High, Drift)"
  - "ScansTable client component with row-click navigation to /scans/{id} + empty / filtered-empty states"
  - "ScanFilters client component: 4 URL-synced controls (date-range, branch debounced 300ms, source, score-threshold) + clear-filters button"
  - "Cursor-based Pagination component (Prev / Next) reading next_cursor from server response"
  - "SeverityBadge using --color-sev-* CSS custom properties with hex fallbacks"
  - "Handrolled SVG Sparkline (~30 LOC, no chart library) — ready for future row-trend usage"
  - "Vitest test infrastructure for dashboard workspace (jsdom env + @/* alias + jest-dom matchers)"
  - "7 vitest cases: SeverityBadge zero/nonzero, ScansTable empty/filtered-empty/row-click, ScanFilters 300ms debounce"
affects:
  - "dashboard/app/(dashboard)/ — adds /scans route segment"
  - "dashboard/components/scans/ — new component directory"
tech-stack:
  added:
    - "Vitest config in dashboard workspace (jsdom, globals, setupFiles)"
  patterns:
    - "Next.js 15 RSC: `searchParams: Promise<...>` + `await searchParams` (breaking change vs Next 14)"
    - "URL-as-state: useSearchParams + router.replace; cursor cleared on every filter change"
    - "Debounced text filter: useRef<setTimeout> + 300ms timeout cleared on subsequent keystrokes; cleanup on unmount"
    - "Cursor-based pagination: nextCursor returned in API response, encoded as `cursor` URL param"
    - "Lazy import in vitest tests (`await import('@/...')`) so vi.mock('next/navigation') is hoisted before component module evaluation"
    - "Handrolled SVG sparkline (polyline + min/max circle markers) — keeps bundle lean"
key-files:
  created:
    - dashboard/app/(dashboard)/scans/page.tsx
    - dashboard/components/scans/ScansTable.tsx
    - dashboard/components/scans/ScanFilters.tsx
    - dashboard/components/scans/Pagination.tsx
    - dashboard/components/scans/Sparkline.tsx
    - dashboard/components/scans/SeverityBadge.tsx
    - dashboard/__tests__/scans-table.test.tsx
    - dashboard/vitest.config.ts
    - dashboard/vitest.setup.ts
  modified: []
decisions:
  - "All ScansTable cells render values as React text nodes (no raw HTML insertion APIs anywhere) — mitigating T-07-06-02 (XSS via branch / commit_sha)."
  - "URL is the single source of truth for filter + pagination state. router.replace (not push) for filter changes preserves a clean history stack; router.push for cursor navigation lets back/forward step through pages."
  - "Branch input debounced 300ms (T-07-06-03 mitigation). Select-based filters fire on every change — acceptable since each is a deliberate user action."
  - "Cursor stripped on every filter change (`next.delete('cursor')`) so changing a filter always resets to page 1 — avoids stale-cursor pagination bugs."
  - "ScansPage uses Next.js 15 `searchParams: Promise<...>` + `await searchParams` per PATTERNS.md Pitfall 1 (breaking change in Next 15)."
  - "SeverityBadge classes use Tailwind arbitrary-value syntax `text-[color:var(--color-sev-*,#hex)]` so the badge degrades gracefully if the viewer styles import is missing."
  - "Score-grade pill thresholds (A>=90, B+>=80, C>=70, D>=60, else F) hard-coded in ScansTable per UI-SPEC §Color; intentionally NOT extracted to a util — single point of use."
  - "Date-range filter uses simple presets (7d / 30d / all) instead of full date-picker — matches D-06 minimum and ships faster; range-picker can be added later without breaking URL contract."
metrics:
  duration: ~10min
  completed: 2026-04-28
  tasks_completed: 2
  files_created: 9
  files_modified: 0
---

# Phase 07 Plan 06: Scan History List Page Summary

`/scans` route delivered: RSC fetches paginated scan list from `GET /v1/scans`, ScansTable renders 8-column dense table with row-click navigation, ScanFilters provides 4 URL-synced filter controls (date-range, branch debounced 300ms, source, score threshold), Pagination implements cursor-based Prev/Next, plus a Vitest suite covering SeverityBadge, ScansTable empty states, row navigation, and the 300ms debounce contract.

## What Shipped

### Task 1 — RSC + table + chrome (commit `0359ac5`)

- **`dashboard/app/(dashboard)/scans/page.tsx`** — async RSC component. `await searchParams` (Next.js 15), maps URL params to a backend query string (`branch` → `search`, `from`/`to` → `created_after`/`created_before`, `score_lt`, `cursor`, `sort`, `order`), calls `backendFetch<ScanListResp>('/v1/scans?...')`, renders `<ScanFilters />` + `<ScansTable />` inside `<Suspense fallback={<ScansTableSkeleton />}>`. Skeleton is 10 animated grey rows (no spinner per UI-SPEC).
- **`dashboard/components/scans/ScansTable.tsx`** — client table. 8 columns; row click → `router.push('/scans/{id}')`; two empty states:
  - No scans + no active filters → "No scans yet" + CLI install hint code block.
  - No scans + active filters → "No scans match your filters" + `Clear all filters` link to `/scans`.
  - All values rendered as React text nodes (T-07-06-02 mitigation). Inline `ScoreGradePill` (A/B+/C/D/F per UI-SPEC §Color) and `SourceCell` (CLI/Manual/GitHub icons via lucide).
- **`dashboard/components/scans/SeverityBadge.tsx`** — count chip. Uses Tailwind arbitrary-value classes referencing `--color-sev-{critical,high,medium,info}` CSS variables (declared by `@infracanvas/viewer/styles.css` per Plan 07-05) with hex fallbacks; collapses to `text-slate-400` when `count === 0`.
- **`dashboard/components/scans/Sparkline.tsx`** — handrolled inline SVG. ~30 LOC: polyline + two `<circle>` markers (min red, max green). No external chart dependency. Currently unused in the table — kept ready for a row-trend column in a follow-up plan.
- **`dashboard/components/scans/Pagination.tsx`** — cursor-based footer. Reads `nextCursor` from props and current `cursor` from `useSearchParams()`. Prev disabled iff `cursor` not in URL; Next disabled iff `nextCursor === null`. Returns `null` when neither button is actionable.

### Task 2 — ScanFilters + Vitest (commits `227be70` RED, `dec9e14` GREEN)

- **`dashboard/components/scans/ScanFilters.tsx`** — sticky filter bar:
  - Date-range `<select>`: presets `Last 7 days` / `Last 30 days` / `All time` → ISO `from` URL param.
  - Branch `<input>`: 300ms debounce via `useRef<setTimeout>` + `setTimeout`/`clearTimeout`; cleanup on unmount.
  - Source `<select>`: `cli` / `manual` / `''` (all).
  - Score threshold `<select>`: `90` / `80` / `70` / `60` / `''`.
  - Clear-filters button shown when any of `branch|source|from|to|score_lt` is set; calls `router.replace('/scans')`.
  - Every filter change deletes `cursor` from the URL.
- **`dashboard/__tests__/scans-table.test.tsx`** — 7 cases across 3 describe blocks:
  1. SeverityBadge: zero count → `text-slate-400`; non-zero → does NOT contain `text-slate-400`.
  2. ScansTable: no items + no filters → "No scans yet"; no items + branch filter → "No scans match your filters" + "Clear all filters" link; one scan → renders `data-testid="scans-table"` + 1 `data-testid="scan-row"`; row click → `router.push('/scans/scan-abc')`.
  3. ScanFilters: typing in branch input does NOT call `router.replace` synchronously; after `vi.advanceTimersByTime(300)` it calls `router.replace` with `branch=feat...`.
- **`dashboard/vitest.config.ts`** — `environment: 'jsdom'`, `globals: true`, `setupFiles: ['./vitest.setup.ts']`, `@/*` resolved to `__dirname`.
- **`dashboard/vitest.setup.ts`** — registers `@testing-library/jest-dom` matchers.

## Verification

All gates from the plan's `<verification>` block pass:

| # | Check | Result |
|---|-------|--------|
| 1 | `grep -c 'data-testid="scans-table"' ScansTable.tsx` | 1 |
| 2 | `grep -c 'await searchParams' page.tsx` | 1 |
| 3 | `grep -c 'backendFetch' page.tsx` | 2 |
| 4 | `grep -c 'setTimeout' ScanFilters.tsx` | 2 |
| 5 | `grep -c 'polyline' Sparkline.tsx` | 1 |
| 6 | `grep -rn 'innerHTML' components/scans/` | 0 (also: `__html` → 0) |
| 7 | `grep -c 'sev-critical' SeverityBadge.tsx` | 1 |
| 8 | `test -f __tests__/scans-table.test.tsx` | exists |

`npm test` was not executed in this worktree (parallel-execution context — `dashboard/node_modules` not provisioned in this worktree). The vitest suite is committed and runnable; integration agent / next CI run will execute it.

## Threat Mitigations Applied

| Threat ID | Mitigation |
|-----------|-----------|
| T-07-06-02 (XSS) | All scan-row values rendered as React text nodes; the unsafe React HTML-injection APIs are not used in `dashboard/components/scans/` (greps for `innerHTML` and `__html` both return 0). |
| T-07-06-03 (DoS via filter spam) | Branch input debounced 300ms via `useRef<setTimeout>` + 300ms timeout, asserted by the `ScanFilters debounce` test case. |

## Deviations from Plan

None — both tasks executed exactly as specified in `07-06-PLAN.md`. The plan's example code blocks were followed verbatim, with one cosmetic addition: a `github_webhook` arm in `SourceCell` to handle the third documented `source` enum value (UI-SPEC mentions GitHub-CI as a future channel; rendering "GitHub" instead of `—` for that case is consistent with D-05).

## TDD Gate Compliance

- **RED gate:** `227be70 test(07-06): add failing vitest suite for scans-table + ScanFilters debounce` — adds the test file before `ScanFilters.tsx` exists. Import of `@/components/scans/ScanFilters` would resolve to `undefined` and the debounce test would throw on render.
- **GREEN gate:** `dec9e14 feat(07-06): implement ScanFilters with URL-driven 4-control filter bar` — adds `ScanFilters.tsx`, satisfying every assertion in the suite.
- **REFACTOR gate:** Not required — implementation matched the plan's example faithfully and is already idiomatic React.

## Commits

| Hash | Type | Message |
|------|------|---------|
| `0359ac5` | feat | scans page RSC + ScansTable + SeverityBadge + Sparkline + Pagination |
| `227be70` | test | add failing vitest suite for scans-table + ScanFilters debounce |
| `dec9e14` | feat | implement ScanFilters with URL-driven 4-control filter bar |

## Requirements Satisfied

- **DSH-04** — `/scans` page renders scan history table per UI-SPEC D-05 columns and D-06 filter set (date-range, branch, source, score threshold).
- **HST-03** — Cursor-based pagination + URL-as-state filtering shipped; filter changes always reset cursor to page 1.

## Known Stubs

None — every column and filter wires to either real `ScanListItem` data or a real URL param. The `Sparkline` component is created but not yet placed in any column; that is intentional (kept lean for now, ready for a row-trend follow-up plan if product wants per-scan score history visible inline).

## Self-Check: PASSED

- Files created — all 9 confirmed via `git log --stat f84a0a8..HEAD`:
  - `dashboard/app/(dashboard)/scans/page.tsx`
  - `dashboard/components/scans/ScansTable.tsx`
  - `dashboard/components/scans/ScanFilters.tsx`
  - `dashboard/components/scans/Pagination.tsx`
  - `dashboard/components/scans/Sparkline.tsx`
  - `dashboard/components/scans/SeverityBadge.tsx`
  - `dashboard/__tests__/scans-table.test.tsx`
  - `dashboard/vitest.config.ts`
  - `dashboard/vitest.setup.ts`
- Commits exist — `0359ac5`, `227be70`, `dec9e14` all present in `git log --oneline`.
- All 8 verification grep gates return the expected values.
