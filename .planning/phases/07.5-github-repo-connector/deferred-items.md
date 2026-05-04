# Phase 7.5 — Deferred Items

Items discovered during plan execution that are out-of-scope for the current
plan but should be addressed by a later plan or the phase verifier cleanup pass.

## Pre-existing TypeScript errors (out of Plan 07.5-01 scope)

| File | Error | Discovered | Out-of-scope plan |
|------|-------|------------|-------------------|
| `dashboard/__tests__/scan-filters.test.tsx:2:18` | `TS6133: 'screen' is declared but its value is never read.` | 2026-05-03 (Plan 07.5-01) | Pre-existing on `dev/local-no-auth` branch before this plan; surfaces when running `npx tsc --noEmit`. Trivially fixable by removing the unused `screen` import. Owned by a future test-cleanup plan or phase verifier sweep. |

## Pre-existing ruff UP017 warnings (out of Plan 07.5-05 scope)

| File | Error | Discovered | Out-of-scope plan |
|------|-------|------------|-------------------|
| `backend/app/routes/scans.py:411,422,436,441` | `UP017 Use datetime.UTC alias` (4 occurrences referring to `timezone.utc` in cursor/filter parsing) | 2026-05-04 (Plan 07.5-05) | Pre-existing on `dev/local-no-auth`. Plan 05 only refactors `commit_scan`'s meter call site — these `list_scans` warnings are unrelated to the touched code. Trivial mechanical fix (`from datetime import UTC` + `tzinfo=UTC`); owned by a backend lint-sweep plan. |
