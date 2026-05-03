# Phase 7.5 — Deferred Items

Items discovered during plan execution that are out-of-scope for the current
plan but should be addressed by a later plan or the phase verifier cleanup pass.

## Pre-existing TypeScript errors (out of Plan 07.5-01 scope)

| File | Error | Discovered | Out-of-scope plan |
|------|-------|------------|-------------------|
| `dashboard/__tests__/scan-filters.test.tsx:2:18` | `TS6133: 'screen' is declared but its value is never read.` | 2026-05-03 (Plan 07.5-01) | Pre-existing on `dev/local-no-auth` branch before this plan; surfaces when running `npx tsc --noEmit`. Trivially fixable by removing the unused `screen` import. Owned by a future test-cleanup plan or phase verifier sweep. |
