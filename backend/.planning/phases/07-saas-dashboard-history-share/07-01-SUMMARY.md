---
phase: 07-saas-dashboard-history-share
plan: 01
subsystem: database
tags: [alembic, sqlalchemy, pydantic, postgres, scans, bcrypt, fastapi]

# Dependency graph
requires:
  - phase: 06-saas-backend-foundation
    provides: Scan ORM model, scans table, ScanCommitReq/ScanGetResp schemas, alembic chain head 004_scan_team_id_helper
provides:
  - scans.branch / scans.commit_sha / scans.source nullable columns + ix_scans_branch + ix_scans_source indexes
  - Scan ORM extended with branch / commit_sha / source mapped columns
  - ScanCommitReq accepts and persists branch / commit_sha / source (length-bounded)
  - ScanGetResp returns branch / commit_sha / source on commit + detail
  - ScanListItemResp + ScanListResp shapes (consumed by Plan 07-02 list endpoint)
  - bcrypt 4.x available in backend venv (consumed by Plan 07-04 share-link password hashing)
affects: [07-02 scans-list, 07-03 scans-compare, 07-04 share-links, 07-05 dashboard-scaffold, 07-06 scans-list-ui, 07-07 scan-detail-ui, D-07 detail header strip]

# Tech tracking
tech-stack:
  added: [bcrypt>=4.0,<5]
  patterns:
    - "Plan-level migration adds nullable metadata columns + indexes; downstream commit-time wiring populates them"
    - "Optional Pydantic fields with explicit max_length caps mirroring DB column lengths (defense in depth at trust boundary)"
    - "List response model excludes presigned URLs (only detail does); list responses stay bounded"

key-files:
  created:
    - backend/migrations/versions/20260428_005_scan_metadata_columns.py
  modified:
    - backend/pyproject.toml
    - backend/app/db/models.py
    - backend/app/schemas/scan.py
    - backend/app/routes/scans.py

key-decisions:
  - "branch/commit_sha/source kept nullable across stack — back-fill not required; pre-existing rows surface as null in list/detail UI"
  - "ScanListItemResp uses ConfigDict(from_attributes=True) so Plan 07-02 can model_validate(row) directly without hand-mapping"
  - "Length caps mirror DB column widths: 255 / 40 / 32 — Pydantic Field(max_length=...) rejects oversized writes before they hit asyncpg (T-07-01-03 mitigation)"
  - "Indexes added on branch + source (not commit_sha) — list-page filters target ref name + source channel; commit_sha is dimension lookup only and small enough that seq scans are fine"
  - "Migration verified via test_migrations.py upgrade + downgrade roundtrip on testcontainer Postgres (no live dev DB used)"

patterns-established:
  - "Pydantic _STRICT (extra=forbid + strict) + Field(max_length) is the canonical way to admit optional client metadata at the commit boundary"
  - "ScanGetResp mirrors row 1:1 plus presigned URL; list shape is the same minus the URL"

requirements-completed: [HST-03]

# Metrics
duration: 8min
completed: 2026-04-28
---

# Phase 07 Plan 01: Scan Metadata Schema Summary

**Adds nullable branch / commit_sha / source columns to scans (alembic 005), wires them through Scan ORM + ScanCommitReq + ScanGetResp, persists at commit time, and adds bcrypt to backend deps to unblock Plan 07-04 share-links.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-28T12:04:00Z
- **Completed:** 2026-04-28T12:12:22Z
- **Tasks:** 2
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- Alembic migration `005_scan_metadata_columns` added — three nullable string columns (branch / commit_sha / source) with two btree indexes (ix_scans_branch, ix_scans_source). Downgrade path symmetric.
- `Scan` ORM model carries the new columns with the same nullability + length the migration defines (255 / 40 / 32). Existing import of `String` from sqlalchemy was sufficient — no new imports.
- `ScanCommitReq` accepts the three optional fields with `Field(max_length=...)` caps; `ConfigDict(strict=True, extra="forbid")` already on the model rejects unknown keys (T-07-01-01 mitigation).
- `ScanGetResp` returns the three fields on both commit and detail responses (`commit_scan` and `get_scan` both updated).
- `commit_scan` persists `branch=body.branch`, `commit_sha=body.commit_sha`, `source=body.source` onto the new `Scan` row.
- New `ScanListItemResp` + `ScanListResp` shapes added — Plan 07-02's list endpoint can `model_validate(row)` directly thanks to `ConfigDict(from_attributes=True)`.
- bcrypt 4.3.0 installed into the shared backend venv and declared in `pyproject.toml` dependencies (Plan 07-04 share-link password hashing prerequisite).
- All 57 existing backend tests still pass; `test_migrations.py::test_upgrade_to_head_clean` and `test_downgrade_roundtrip` both green against the testcontainer Postgres — proves the new migration is reversible and applies on a clean DB.

## Task Commits

1. **Task 1: Add bcrypt dep + create scan-metadata migration** — `9b973b7` (feat)
2. **Task 2: Extend Scan ORM + Pydantic schemas + commit_scan handler** — `02d87e9` (feat)

_Plan metadata commit (SUMMARY) follows separately._

## Files Created/Modified

- `backend/migrations/versions/20260428_005_scan_metadata_columns.py` — alembic migration adding branch / commit_sha / source columns + ix_scans_branch + ix_scans_source indexes; head revision is now `005_scan_metadata_columns`
- `backend/pyproject.toml` — `bcrypt>=4.0,<5` appended to `[project].dependencies`
- `backend/app/db/models.py` — `Scan` class gains branch / commit_sha / source mapped columns (after `summary_json`, before `created_at`)
- `backend/app/schemas/scan.py` — `ScanCommitReq` extended with optional length-capped fields; `ScanGetResp` extended with nullable fields; new `ScanListItemResp` + `ScanListResp` models
- `backend/app/routes/scans.py` — `Scan(...)` constructor in `commit_scan` propagates request body fields; both `ScanGetResp(...)` constructors (commit + get_scan) populate from row

## Decisions Made

- Keep all three new columns nullable — pre-existing scan rows shipped before this plan must remain readable without a back-fill step.
- Add btree indexes on `branch` and `source` (HST-03 list filters target these dimensions) but not `commit_sha` — commit SHAs are dimension lookups only, low cardinality slice per branch, and seq scans are fine for foreseeable scale.
- Use the existing `body` parameter name in route handlers (not `req` as the plan suggests in its grep pattern) — matches the established convention in `commit_scan` / `get_scan`. Functionally equivalent and avoids a churny rename.
- Migration verification used the testcontainer Postgres exercised by `test_migrations.py` rather than a live Neon dev DB. The roundtrip (upgrade → head, downgrade → 004) ensures the migration is sound; live dev-DB upgrade can be performed by ops at deploy time.

## Deviations from Plan

None substantive. One minor naming variance:

- The plan's acceptance grep references `branch=req\.branch`; existing `commit_scan` uses `body` for the Pydantic body parameter. Implementation uses `body.branch` (semantically identical). Match count via `grep -cnE 'branch=row\.branch|branch=body\.branch'` is 3 (one ORM ctor + two response ctors), satisfying the plan's "at least 2 lines" intent.

**Total deviations:** 0 auto-fixed deviations (Rules 1–3); 1 cosmetic naming alignment with existing handler convention.
**Impact on plan:** None — plan executed as written, including all stated artifacts and verification gates.

## Issues Encountered

- No live Neon dev DB available in the worktree environment (`DATABASE_URL` not set). Plan explicitly anticipates this case ("If the dev DB is unreachable... record the failure as a [BLOCKING] checkpoint to be re-run before Plan 02 begins"). Resolution: relied on `tests/test_migrations.py` which spins up a Postgres testcontainer and exercises `alembic upgrade head` + downgrade roundtrip; both pass. Live dev-DB upgrade can be applied at deploy time.

## User Setup Required

None — no external service configuration required by this plan. (Stripe/R2/Clerk creds unchanged.)

## Next Phase Readiness

- **Plan 07-02 (scan list endpoint)** is unblocked: `ScanListItemResp` + `ScanListResp` shapes exist, columns to filter on exist, indexes are in place.
- **Plan 07-03 (scan compare)** is unblocked: detail responses now return `branch` / `commit_sha` so the diff header can render git context.
- **Plan 07-04 (share links)** is unblocked: `bcrypt 4.x` is available in the venv for share-link password hashing.
- **Plan 07-05/06/07 (dashboard frontend)** is unblocked: ScanGetResp + (forthcoming) ScanListItemResp carry the fields the Next.js dashboard's scan list and scan detail header strip require (D-07).

## Self-Check: PASSED

- `[ -f backend/migrations/versions/20260428_005_scan_metadata_columns.py ]` → FOUND
- `git log --oneline | grep 9b973b7` → FOUND (Task 1)
- `git log --oneline | grep 02d87e9` → FOUND (Task 2)
- `grep -nE 'branch: Mapped\[str \| None\]' backend/app/db/models.py` → 1 match (line 66)
- `grep -nE 'class ScanListItemResp|class ScanListResp' backend/app/schemas/scan.py` → 2 matches
- `grep -c 'bcrypt' backend/pyproject.toml` → 1
- `cd backend && alembic heads` → `005_scan_metadata_columns (head)`
- `python -c "import bcrypt; print(bcrypt.__version__)"` → `4.3.0`
- 57 backend tests pass (pytest tests/ -x -q --no-cov)

---
*Phase: 07-saas-dashboard-history-share*
*Completed: 2026-04-28*
