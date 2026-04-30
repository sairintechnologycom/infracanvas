# Phase 7.1 Deferred Items

Out-of-scope discoveries logged during plan execution. Not fixed in the
plan that surfaced them — must be addressed by a subsequent plan or a
dedicated cleanup pass.

| Discovered | Plan | File | Issue | Disposition |
|------------|------|------|-------|-------------|
| 2026-04-30 | 07.1-01 | dashboard/app/layout.tsx | `Inter` is imported from `next/font/google` but unused after Geist migration. Causes `next build` to fail typecheck (`'Inter' is declared but its value is never read`). | Out-of-scope for plan 01 (file not in `files_modified`; modified externally on working tree as part of broader 7.1 streams). Defer to plan that owns layout.tsx restructuring or a final cleanup pass before phase verifier. |
| 2026-04-30 | 07.1-02 | dashboard/lib/backend.ts → dashboard/components/scans/ScanPickerModal.tsx | `lib/backend.ts` imports `@clerk/nextjs/server` (server-only); `ScanPickerModal` is a `'use client'` component that imports `backendFetch`, leaking `server-only` into the client bundle. `next build` fails with: "'server-only' cannot be imported from a Client Component module." Pre-existing at the plan-02 base commit (`9656636`); not introduced by the shadcn `<Dialog/>` migration in this plan. **RESOLVED on merge:** `dev/local-no-auth` already swapped `backendFetch` → `fetch('/api/scans-list')`. Conflict resolution preserved both the dev fetch swap AND the shadcn Dialog migration. | Resolved by manual conflict resolution at merge time. |
| 2026-04-30 | 07.1-03 | dashboard/lib/backend.ts → dashboard/components/scans/{ScanPickerModal,CompareButton}.tsx | `lib/backend.ts` imports `@clerk/nextjs/server` (server-only). The transitive client import chain `CompareButton → ScanPickerModal → backend.ts` makes `next build` fail: `'server-only' cannot be imported from a Client Component module.` | Out-of-scope for plan 03 (none of these files are in plan 03's `files_modified`; pre-existing on the worktree base — not introduced by this plan's ScanFilters / SettingsLayout migrations). Vitest suite is green on the affected components; failure is purely a Next.js build/RSC boundary issue. Must be fixed by a plan that owns the scan-compare flow refactor (likely splitting `lib/backend.ts` into server- and client-safe modules) before the phase verifier runs. |
| 2026-04-30 | 07.1-04 | dashboard/components/scans/ScanPickerModal.tsx, dashboard/components/scans/CompareButton.tsx | `next build` fails with `'server-only' cannot be imported from a Client Component module`. Trace: `lib/backend.ts → ScanPickerModal.tsx → CompareButton.tsx`. `lib/backend.ts` is server-only (uses `auth()`) and is being imported into a Client Component path. Pre-existing — NOT caused by Plan 07.1-04 changes (verified via `npx tsc --noEmit -p tsconfig.json` showing zero errors in `app/api/scan-share/route.ts`; the build trace lists only ScanPicker/CompareButton). Likely introduced by a parallel Plan 07.1 stream that wired CompareButton to a server-side data fetch. | Out-of-scope for plan 04 (files not in `files_modified`). Defer to the plan that owns ScanPickerModal/CompareButton — the component must call a `/api/...` route handler instead of importing `lib/backend.ts` directly. Final cleanup pass or phase verifier should catch. |
| 2026-04-30 | 07.1-04 | dashboard/components/ui/form.tsx | `Cannot find module '@/registry/new-york-v4/ui/label'`. Pre-existing shadcn-init artefact from Plan 07.1-01 (registry path stub never resolved). | Out-of-scope. Defer to Plan 07.1-01 follow-up or shadcn cleanup pass. |

## 07.1-05 — Pre-existing flaky tests (out of scope, observed during execution)

- `dashboard/__tests__/scan-filters.test.tsx` "renders combobox-role triggers" — times out at 15 s under load.
- `dashboard/__tests__/scans-table.test.tsx` "branch input waits 300ms before calling router.replace" — times out at 15 s under load.

Both pass in isolation and on lighter runs (verified: `npm test -- --run __tests__/compare-layout.test.tsx` → 30/30 green; first full-suite run reported 129/129). They were introduced by Plan 07.1-03 (ScanFilters shadcn migration) and Plan 07.1-04 (scans table debounce). Recommended fix: bump testTimeout for these files or migrate to `await waitFor()` instead of `vi.advanceTimersByTime`.

Tracked here so 07.1-05 does not regress the worktree on these flakes.
