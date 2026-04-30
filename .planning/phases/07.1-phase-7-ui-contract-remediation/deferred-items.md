# Phase 7.1 Deferred Items

Out-of-scope discoveries logged during plan execution. Not fixed in the
plan that surfaced them — must be addressed by a subsequent plan or a
dedicated cleanup pass.

| Discovered | Plan | File | Issue | Disposition |
|------------|------|------|-------|-------------|
| 2026-04-30 | 07.1-01 | dashboard/app/layout.tsx | `Inter` is imported from `next/font/google` but unused after Geist migration. Causes `next build` to fail typecheck (`'Inter' is declared but its value is never read`). | Out-of-scope for plan 01 (file not in `files_modified`; modified externally on working tree as part of broader 7.1 streams). Defer to plan that owns layout.tsx restructuring or a final cleanup pass before phase verifier. |
