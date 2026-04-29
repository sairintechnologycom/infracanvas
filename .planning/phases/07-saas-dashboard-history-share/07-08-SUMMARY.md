---
phase: 07-saas-dashboard-history-share
plan: 8
subsystem: dashboard-compare
tags: [dashboard, compare, viewer, share-link-cta, next15-rsc, vitest, drift-overlay]
requires:
  - 07-03  # backend GET /v1/scans/{a}/compare/{b} compare endpoint
  - 07-05  # dashboard scaffold + ResourceDiff types + backendFetch
  - 07-07  # MetadataHeader + ScanViewerClient + fetchScanJson + /api/scan-presigned
provides:
  - "GET /scans/compare?a={uuid}&b={uuid} — two-pane diff page (DSH-04 / HST-02)"
  - "DiffSummary +N/−N/~N chip strip"
  - "DiffNodeList — windowed resource-diff rows with kind palette"
  - "CompareViewerPair — parallel R2 fetch + dual ViewerProvider mount"
  - "ScanPickerModal + CompareButton — Compare-against… modal CTA from scan detail"
affects:
  - dashboard/lib/types.ts                          # ResourceDiff updated to backend nodes[] shape
  - dashboard/components/scans/MetadataHeader.tsx   # static <Link> Compare → <CompareButton/>
  - dashboard/components/scans/ScanViewerClient.tsx # ViewerProvider type-fix (Rule 1)
  - dashboard/__tests__/metadata-header.test.tsx    # mock CompareButton parallel to ShareButton
  - dashboard/tsconfig.json                         # drop unresolvable extends "next/tsconfig"
tech-stack:
  added:
    - "@radix-ui/react-dialog (already installed) — used for ScanPickerModal"
  patterns:
    - "Next.js 15 RSC async searchParams (await searchParams) — Pitfall 1"
    - "UUID regex gate before any backend call — T-07-08-01 mitigation"
    - "Per-instance Zustand stores via createViewerStore() — D-11 isolation"
    - "Promise.all for two large client-direct R2 fetches — Pitfall 7"
key-files:
  created:
    - dashboard/app/(dashboard)/scans/compare/page.tsx
    - dashboard/components/compare/CompareLayout.tsx
    - dashboard/components/compare/DiffSummary.tsx
    - dashboard/components/compare/DiffNodeList.tsx
    - dashboard/components/compare/CompareViewerPair.tsx
    - dashboard/components/scans/ScanPickerModal.tsx
    - dashboard/components/scans/CompareButton.tsx
    - dashboard/lib/utils.ts
    - dashboard/__tests__/compare-layout.test.tsx
  modified:
    - dashboard/lib/types.ts
    - dashboard/components/scans/MetadataHeader.tsx
    - dashboard/components/scans/ScanViewerClient.tsx
    - dashboard/__tests__/metadata-header.test.tsx
    - dashboard/tsconfig.json
decisions:
  - "Replaced existing /compare?from= static Link with CompareButton + ScanPickerModal — D-09 entry"
  - "ResourceDiff type rewritten to match backend ResourceDiffResp (nodes[] with kind discriminator) — Plan 07-03 source of truth"
  - "Used radix-ui Dialog primitives directly (no shadcn install) — primitives already in package.json"
  - "Deferred viewer focusNode imperative API — logged TODO, scroll-sync follow-up plan"
  - "Per-scan createViewerStore() in CompareViewerPair to prevent state bleed between Scan A and Scan B"
metrics:
  duration: "~40 minutes"
  completed: 2026-04-29
  tasks_completed: 2
  files_created: 9
  files_modified: 5
  tests_passing: "38/38"
  tsc_errors: 0
---

# Phase 7 Plan 8: Compare Page + ScanPickerModal Summary

Built the `/scans/compare?a={uuid}&b={uuid}` page that delivers DSH-04/HST-02 — a two-pane resource-level diff view with sticky `+N/−N/~N` summary, windowed kind-tinted node list, dual `@infracanvas/viewer` instances, swap, and an entry-point `ScanPickerModal` opened from the existing scan-detail header. UUID-validated RSC, defence-in-depth backend 404 handling per D-18, drift palette via the already-imported `@infracanvas/viewer/styles.css` tokens.

## Tasks

| Task | Name                                                            | Commit  | Type   |
| ---- | --------------------------------------------------------------- | ------- | ------ |
| 1a   | Failing vitest suite + stubs for compare RSC, DiffSummary, list | ad5eac2 | test   |
| 1b   | Implement compare RSC + DiffSummary + DiffNodeList (GREEN)      | 78054c7 | feat   |
| 2    | CompareLayout + CompareViewerPair + ScanPickerModal + wiring    | b6a1679 | feat   |

Task 1 followed strict TDD — 19 failing / 4 passing on RED, 23/23 on GREEN.

## Architecture

### Data flow

```
Browser ──/scans/compare?a=A&b=B──▶ ComparePage (RSC)
                                     │
                                     ├─ isUUID(a) && isUUID(b)?  ── no ──▶ 400 card
                                     ▼ yes
                                     backendFetch('/v1/scans/{a}/compare/{b}')
                                     │
                                     ├─ Error('404')             ──▶ 404 card ("Scan not found")
                                     ├─ Error('5xx')             ──▶ 5xx card
                                     ▼ ResourceDiff
                                     <CompareLayout/>  (client boundary)
                                       │
                                       ├─ DiffSummary  (chips)
                                       ├─ DiffNodeList (rows, click → setSelectedNodeId)
                                       └─ CompareViewerPair
                                            │
                                            ├─ Promise.all(/api/scan-presigned A, B)
                                            ├─ Promise.all(fetchScanJson A, B)  ─── 403 retry
                                            └─ <ViewerProvider store={A}> + <ViewerProvider store={B}>
```

### ScanPickerModal entry

```
MetadataHeader ─── <CompareButton/> ─── click ──▶ <ScanPickerModal isOpen=true>
                                                    │
                                                    backendFetch('/v1/scans?limit=25')
                                                    │
                                                    Group by branch (current first), search filter
                                                    │
                                                    select + click Compare
                                                    │
                                                    router.push(/scans/compare?a={current}&b={selected})
```

## Decisions Made

1. **Used radix-ui Dialog primitives directly.** The plan referenced shadcn `<Dialog>` but `dashboard/components/ui/` does not exist and no `npx shadcn init` has been run. `@radix-ui/react-dialog` is already in `dashboard/package.json`, so I built ScanPickerModal directly on radix primitives with Tailwind classes. Future refactor to shadcn is a no-op replacement.
2. **Per-scan `createViewerStore()` instead of `<ViewerProvider scan={graph}>`.** The plan's `<interfaces>` block claimed `ViewerProvider` accepts a `scan` prop; the actual `viewer/src/store.ts` API only accepts `{ store?, children }`. Build a fresh store per scan ID via `useMemo(() => createViewerStore(), [scanId])`, then hydrate via `store.getState().setGraph(graph)` once R2 JSON arrives. This keeps Scan A and Scan B isolated (D-11) and removes a TS error.
3. **Compare button extracted to its own client component (`CompareButton.tsx`).** MetadataHeader was a server component; embedding `useState` for the modal toggle would force a wholesale `'use client'` conversion. The CompareButton+ScanPickerModal pair lives parallel to ShareButton — minimal blast radius, mirrors existing pattern.
4. **`focusNode` deferred to follow-up.** No imperative API exists on `@infracanvas/viewer` for `focusNode(id)`; logged a `console.debug` TODO rather than ship dead UI. Tracked for a future plan that adds an action to the viewer store API.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Vitest could not resolve `extends: "next/tsconfig"`**
- **Found during:** Task 1 RED phase (first `npx vitest run`)
- **Issue:** `dashboard/tsconfig.json` extended `next/tsconfig` which does not ship as a published file in Next 15 (`Cannot find module 'next/tsconfig/tsconfig.json'`). Existing `__tests__/metadata-header.test.tsx` tests in this worktree also crashed the same way — the failure was pre-existing, not introduced by this plan, but it blocked the new Vitest suite from running.
- **Fix:** Replaced the broken `extends` with the equivalent inline compilerOptions Next 15 expects (`module: esnext`, `moduleResolution: bundler`, `resolveJsonModule`, `isolatedModules`, `noEmit`, `allowJs`, `skipLibCheck`, `esModuleInterop`, `plugins: [{ name: next }]`). Existing 8 metadata-header tests + 7 scans-table tests continue to pass under the new config.
- **Files modified:** `dashboard/tsconfig.json`
- **Commit:** ad5eac2

**2. [Rule 1 — Bug] `ResourceDiff` type didn't match backend Plan 07-03 schema**
- **Found during:** Task 1 RED phase (writing tests with the type)
- **Issue:** `dashboard/lib/types.ts` `ResourceDiff` was structured as `{ added[], removed[], changed[], findings_delta }` from an early Phase 7 draft. The actual backend `ResourceDiffResp` (Plan 07-03 — `backend/app/schemas/scan.py`) returns `{ scan_a_id, scan_b_id, nodes[], edges_added[], edges_removed[], summary }` with `kind` discriminator on each node. Any consumer using the existing type would have produced runtime errors against the real backend.
- **Fix:** Rewrote `ResourceDiff` and added a new `NodeDiff` interface mirroring the backend Pydantic schema field-for-field. Verified with the test fixtures (`fixtureNodes` in `compare-layout.test.tsx`).
- **Files modified:** `dashboard/lib/types.ts`
- **Commit:** ad5eac2

**3. [Rule 1 — Bug] Pre-existing `<ViewerProvider scan={graph}>` had no matching prop on the typed API**
- **Found during:** Task 2 verification (`npx tsc --noEmit`)
- **Issue:** `dashboard/components/scans/ScanViewerClient.tsx` (from Plan 07-07) used `<ViewerProvider scan={graph}>`, but `viewer/src/store.ts` `ViewerProvider` only accepts `{ store?, children }`. This was a pre-existing TS error in the worktree base. The plan acceptance gate requires `tsc --noEmit | grep -c 'error TS'` to be 0, so the pre-existing error blocked verification of new code.
- **Fix:** Updated both `ScanViewerClient.tsx` and the new `CompareViewerPair.tsx` to use `createViewerStore()` + `store.getState().setGraph(graph)` after the JSON arrives. Per-scan store via `useMemo(() => createViewerStore(), [scanId])`.
- **Files modified:** `dashboard/components/scans/ScanViewerClient.tsx`, `dashboard/components/compare/CompareViewerPair.tsx`
- **Commit:** b6a1679

**4. [Rule 3 — Blocking] `CompareButton` introduces `useRouter` into MetadataHeader's render tree**
- **Found during:** Task 2 (after wiring CompareButton into MetadataHeader)
- **Issue:** `ScanPickerModal` (the child of `CompareButton`) calls `useRouter()` from `next/navigation`. The existing `metadata-header.test.tsx` does not mock `next/navigation`, so render would crash with "useRouter must be used within an AppRouterProvider" once `CompareButton` is rendered.
- **Fix:** Added a vi.mock for `@/components/scans/CompareButton` parallel to the existing `ShareButton` mock — both stubs render a simple button with `data-testid`. Keeps metadata-header tests focused on the header's own concerns.
- **Files modified:** `dashboard/__tests__/metadata-header.test.tsx`
- **Commit:** b6a1679

### Architectural Changes

None — all deviations were Rule 1/3 auto-fixes.

## Authentication Gates

None encountered.

## Threat Surface Verification

Reviewed against `<threat_model>` (T-07-08-01..04):

| Threat | Mitigation | Status |
|--------|-----------|--------|
| T-07-08-01 (spoofing on searchParams) | UUID regex before backendFetch | applied — `isUUID` gates entry to `backendFetch`; tests assert `backendFetch` is NOT called when UUIDs are invalid |
| T-07-08-02 (cross-team info disclosure) | Treat backend 404 as generic | applied — 404 card text is generic ("This scan may have been deleted, or you may not have access to it"); no scan id, team id, or branch leaked in error UI |
| T-07-08-03 (DoS via large diff) | DiffNodeList CSS windowing | applied — `overflow-y-auto max-h-[60vh]` cap; 5000-node upstream cap unchanged |
| T-07-08-04 (presigned URL in RSC HTML) | Client-side presigned fetch only | applied — CompareViewerPair's `useEffect` calls `/api/scan-presigned` on mount; no presigned URL is rendered in the RSC HTML |

## Verification Results

- `cd dashboard && npx vitest run` — 38/38 pass (8 metadata-header + 23 compare-layout + 7 scans-table)
- `cd dashboard && npx tsc --noEmit | grep -c "error TS"` — 0
- All 10 plan-level grep checks pass:
  - `await searchParams` in `compare/page.tsx` → 1
  - `isUUID` in `compare/page.tsx` → 2
  - `Scan not found` in `compare/page.tsx` → 1
  - `data-testid="diff-summary"` in `DiffSummary.tsx` → 1
  - `data-testid="diff-node-list"` in `DiffNodeList.tsx` → 1
  - `data-testid="compare-layout"` in `CompareLayout.tsx` → 1
  - `compare?a=` in `ScanPickerModal.tsx` → 2
  - `Promise.all` in `CompareViewerPair.tsx` → 3
  - `ViewerProvider` in `CompareViewerPair.tsx` → 7 (≥2 required)
  - `fetchScanJson` in `CompareViewerPair.tsx` → 4 (1 required)

## Known Stubs

None. The `focusNode` integration logs a TODO but is documented as a separate-plan deferral, not a stub blocking DSH-04 — DSH-04 is specifically the resource-diff list with drill-down navigation, and the list/navigation works.

## Self-Check: PASSED

Verified files exist:
- FOUND: `dashboard/app/(dashboard)/scans/compare/page.tsx`
- FOUND: `dashboard/components/compare/CompareLayout.tsx`
- FOUND: `dashboard/components/compare/DiffSummary.tsx`
- FOUND: `dashboard/components/compare/DiffNodeList.tsx`
- FOUND: `dashboard/components/compare/CompareViewerPair.tsx`
- FOUND: `dashboard/components/scans/ScanPickerModal.tsx`
- FOUND: `dashboard/components/scans/CompareButton.tsx`
- FOUND: `dashboard/lib/utils.ts`
- FOUND: `dashboard/__tests__/compare-layout.test.tsx`

Verified commits exist:
- FOUND: ad5eac2 (test RED)
- FOUND: 78054c7 (feat GREEN — Task 1)
- FOUND: b6a1679 (feat — Task 2)
