# Phase 7.1 Deferred Items

Out-of-scope discoveries logged during plan execution. Not fixed in the
plan that surfaced them — must be addressed by a subsequent plan or a
dedicated cleanup pass.

| Discovered | Plan | File | Issue | Disposition |
|------------|------|------|-------|-------------|
| 2026-04-30 | 07.1-01 | dashboard/app/layout.tsx | `Inter` is imported from `next/font/google` but unused after Geist migration. Causes `next build` to fail typecheck (`'Inter' is declared but its value is never read`). | Out-of-scope for plan 01 (file not in `files_modified`; modified externally on working tree as part of broader 7.1 streams). Defer to plan that owns layout.tsx restructuring or a final cleanup pass before phase verifier. |
| 2026-04-30 | 07.1-03 | dashboard/lib/backend.ts → dashboard/components/scans/{ScanPickerModal,CompareButton}.tsx | `lib/backend.ts` imports `@clerk/nextjs/server` (server-only). The transitive client import chain `CompareButton → ScanPickerModal → backend.ts` makes `next build` fail: `'server-only' cannot be imported from a Client Component module.` | Out-of-scope for plan 03 (none of these files are in plan 03's `files_modified`; pre-existing on the worktree base — not introduced by this plan's ScanFilters / SettingsLayout migrations). Vitest suite is green on the affected components; failure is purely a Next.js build/RSC boundary issue. Must be fixed by a plan that owns the scan-compare flow refactor (likely splitting `lib/backend.ts` into server- and client-safe modules) before the phase verifier runs. |
