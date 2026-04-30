# Phase 7.1 Deferred Items

Out-of-scope discoveries logged during plan execution. Not fixed in the
plan that surfaced them — must be addressed by a subsequent plan or a
dedicated cleanup pass.

| Discovered | Plan | File | Issue | Disposition |
|------------|------|------|-------|-------------|
| 2026-04-30 | 07.1-01 | dashboard/app/layout.tsx | `Inter` is imported from `next/font/google` but unused after Geist migration. Causes `next build` to fail typecheck (`'Inter' is declared but its value is never read`). | Out-of-scope for plan 01 (file not in `files_modified`; modified externally on working tree as part of broader 7.1 streams). Defer to plan that owns layout.tsx restructuring or a final cleanup pass before phase verifier. |
| 2026-04-30 | 07.1-02 | dashboard/lib/backend.ts → dashboard/components/scans/ScanPickerModal.tsx | `lib/backend.ts` imports `@clerk/nextjs/server` (server-only); `ScanPickerModal` is a `'use client'` component that imports `backendFetch`, leaking `server-only` into the client bundle. `next build` fails with: "'server-only' cannot be imported from a Client Component module." Pre-existing at the plan-02 base commit (`9656636`); not introduced by the shadcn `<Dialog/>` migration in this plan. The ScanPickerModal already used `backendFetch` before plan 02; the migration preserved that call. | Out-of-scope for plan 02 (root cause is `lib/backend.ts` architecture, not the modal). Fix: route ScanPickerModal's scan-list fetch through a Next route handler (e.g. `/api/scans-list/route.ts`, which already exists per `git status` untracked dir) instead of calling `backendFetch` directly client-side. Defer to plan 07.1-09 (data-fetch / client-server split) or final cleanup pass. |
