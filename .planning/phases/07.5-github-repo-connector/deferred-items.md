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

## Phase verifier warnings (deferred at phase close 2026-05-05)

Surfaced by `gsd-verifier` against `.planning/phases/07.5-github-repo-connector/07.5-VERIFICATION.md`. None are blockers; phase 7.5 closed on operator-approved manual smoke + 5/5 must-haves verified with file:line evidence. Captured here so they surface in `/gsd-progress` and can be picked up in a small cleanup plan or rolled into Phase 8 hardening.

| File | Issue | Discovered | Owner |
|------|-------|------------|-------|
| `backend/tests/test_services_scans.py` (3 finalize_scan unit tests) | `InvalidCatalogNameError` — test calls `get_sessionmaker()` without monkeypatching the engine that `tests/api/conftest.py:128` shims; testcontainer wiring gap, NOT a production-code defect. Production code is exercised end-to-end by `tests/jobs/test_scan_repo.py` (13/13 pass). | 2026-05-05 (Phase 7.5 verifier) | Test-infra cleanup plan. Apply the same engine-shim fixture pattern from `tests/api/conftest.py:128` to `tests/test_services_scans.py`'s session setup. |
| `backend/app/services/scans.py:134,162` | mypy `--warn-unused-ignores` flags two `# type: ignore[attr-defined]` comments on `except stripe.error.StripeError` as no-longer-needed (likely because mypy's stripe stubs were upgraded after they were added during the pause-work resume on 2026-05-04). | 2026-05-05 (Phase 7.5 verifier) | Backend lint sweep — remove the two type-ignore comments and re-run `mypy --strict app/services/scans.py` to confirm clean. |
| `backend/app/storage/r2.py::get_bytes` | mypy `no-any-return` — function annotated to return `bytes` but inner expression resolves to `Any`. Likely missing a cast on the boto3 result or the function signature needs `# type: ignore[no-any-return]`. | 2026-05-05 (Phase 7.5 verifier) | Backend lint sweep — add explicit cast or refine annotations on the boto3 `get_object` response handling. |
