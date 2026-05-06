---
phase: 07-saas-dashboard-history-share
plan: 02
subsystem: backend-api
tags: [fastapi, sqlalchemy, postgres, rls, pagination, scans]

# Dependency graph
requires:
  - phase: 07-saas-dashboard-history-share
    plan: 01
    provides: Scan.branch / Scan.commit_sha / Scan.source ORM columns + ScanListItemResp + ScanListResp shapes + ix_scans_branch + ix_scans_source btree indexes
  - phase: 06-saas-backend-foundation
    provides: require_role / resolve_team_from_clerk_org / team_scoped session pattern (set_config app.current_team_id) / RLS policies on scans
provides:
  - GET /v1/scans paginated list endpoint (response_model=ScanListResp)
  - Cursor pagination protocol — base64url(JSON{t, i}) of (created_at, id), sorted DESC, no offset drift
  - Filter contract — search (ILIKE branch/commit_sha/source), environment→source, status, created_after/before (ISO 8601)
  - Test fixtures consumable by 07-03 / 07-04: seed_scan_factory pattern, app_client + auth_headers_factory wiring
affects: [07-03 scans-compare, 07-05 dashboard-scaffold, 07-06 scans-list-ui (frontend consumer), 07-08 compare-frontend]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Keyset (cursor) pagination: ORDER BY (created_at DESC, id DESC) + WHERE (created_at, id) < (cursor.t, cursor.i) — stable across inserts, no offset drift"
    - "Tolerant cursor decode: tampered/malformed cursors silently fall back to page 1 (RLS still applies — T-07-02-04)"
    - "FastAPI Query(le=...) validators serve as DoS guard before handler executes (T-07-02-02)"
    - "Test module declares its own autouse R2-wiring + Clerk-JWKS hooks so it runs in isolation (no implicit dependency on test_scans.py collection order)"

key-files:
  created:
    - backend/tests/test_scans_list.py
  modified:
    - backend/app/routes/scans.py

key-decisions:
  - "Cursor encodes (created_at, id) — id is the tiebreaker so two rows with identical created_at don't get duplicated or skipped across pages"
  - "limit+1 fetch trick — query asks for limit+1 rows and uses the (limit+1)th's existence as the has_more signal; the (limit+1)th row is never returned to the client. Avoids a separate COUNT() query"
  - "Cursor decode is intentionally permissive (Exception → None) rather than raising 422 — keeps the URL surface forgiving for hand-crafted requests; security relies on RLS, not cursor validation"
  - "environment query param maps to source (per CONTEXT.md D-06: environment is a placeholder dimension reusing the source channel column for v1)"
  - "scan_status param uses alias='status' — keeps the URL surface using the natural ?status= name while the Python identifier doesn't shadow fastapi.status"
  - "Manual ValueError → 422 raises for created_after / created_before instead of relying on FastAPI's pydantic-style datetime parsing — gives control over the error code shape AND keeps the column type str|None at the FastAPI layer (Pydantic-coerced datetime would have introduced timezone-naivety mismatches with the DB's TIMESTAMPTZ column)"
  - "List rows do NOT include presigned URLs (per Plan 01 ScanListItemResp shape) — list-page responses are bounded and we don't sign N URLs per page request; UI fetches detail (which includes the URL) on row click"
  - "Read-only endpoint emits no Stripe meter event (per D-19 / Phase 6 D-08: metering fires only on scan upload)"

patterns-established:
  - "set_config('app.current_team_id', :t, true) inside session.begin() block is the canonical RLS scoping pattern for read endpoints (mirrors get_scan, commit_scan)"
  - "ScanListItemResp.model_validate(row) works directly because Plan 01 set ConfigDict(from_attributes=True)"
  - "Test files that need a TestClient redeclare _wire_r2_to_moto + patch_clerk_jwks locally rather than relying on cross-file fixture autouse — avoids surprising collection-order dependencies"

requirements-completed: [HST-01]

# Metrics
duration: ~22min
completed: 2026-04-28
---

# Phase 07 Plan 02: Scan List Endpoint Summary

**Adds `GET /v1/scans` to the FastAPI app — cursor-paginated, team-scoped via RLS, four filter params (search ILIKE, environment, status, created_after/before), with 10 integration tests covering the full happy path + cross-team isolation + 422 validation gates.**

## Performance

- **Duration:** ~22 min
- **Started:** 2026-04-28 (executor wall clock)
- **Tasks:** 2
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- `list_scans` handler appended to `backend/app/routes/scans.py` — registered on the existing `router = APIRouter(prefix="/v1/scans")` via `@router.get("")`, so the route lands at `GET /v1/scans` with no further `app.include_router` plumbing needed.
- Cursor pagination implemented via the keyset `WHERE (created_at, id) < (cursor.t, cursor.i)` pattern — stable, no offset drift, no row duplication across pages.
- Four filter params wired as SQLAlchemy WHERE clauses with parameterised binding: `search` (ILIKE on branch / commit_sha / source via `or_`), `environment` (eq on source), `status` (eq on Scan.status), and `created_after` / `created_before` (range on created_at with explicit ISO 8601 → 422 conversion).
- `limit` is FastAPI-validated with `Query(default=20, ge=1, le=100)` — limit > 100 returns 422 before the handler executes (T-07-02-02 mitigation).
- `_encode_cursor` / `_decode_cursor` helpers added — base64url(JSON) of `{t: created_at-iso, i: scan_id}`. Decode is tolerant: a tampered cursor falls back to page 1 rather than raising; RLS continues to enforce team isolation independent of cursor contents.
- New test module `backend/tests/test_scans_list.py` — 10 tests (LST-001..010) covering: basic list, ILIKE on branch, ILIKE on commit_sha, status filter, date-range filter, cursor pagination across two pages, last-page-no-cursor sentinel, cross-team RLS isolation (team B sees zero of team A's scans), invalid created_after → 422, limit > 100 → 422.
- Test module is fully self-contained — declares its own `_wire_r2_to_moto` and `patch_clerk_jwks` autouse fixtures plus its own `team_a` / `team_b` / `auth_headers_factory` / `app_client` / `seed_scan_factory` scoped fixtures, so `pytest tests/test_scans_list.py` works in isolation.
- `seed_scan_factory` advances a deterministic created_at counter so successive seeds within one test get strictly-ordered timestamps (eliminates pagination flake from same-second ties).
- All 67 backend tests pass (was 57 before; 10 new); no regression in any other module.

## Task Commits

1. **Task 1: Implement list_scans handler in scans.py** — `5f354d0` (feat)
2. **Task 2: Write test_scans_list.py integration tests** — `34a23bf` (test)

_Plan metadata commit (SUMMARY) follows separately._

## Files Created/Modified

- `backend/app/routes/scans.py` — added `_DEFAULT_LIMIT` / `_MAX_LIMIT` constants, `_encode_cursor` / `_decode_cursor` helpers, and the `list_scans` handler at `@router.get("")`. Also extended the existing imports (`from sqlalchemy import and_, or_, select, text`, `from fastapi import APIRouter, Depends, HTTPException, Query, status`, `import base64, json`, plus `ScanListItemResp` / `ScanListResp` from `app.schemas.scan`).
- `backend/tests/test_scans_list.py` — created. 10 async integration tests + 5 fixtures (autouse R2 wire, patch_clerk_jwks, team_a, team_b, auth_headers_factory, app_client, seed_scan_factory). All carry `pytestmark = pytest.mark.rls`.

## Decisions Made

- Use `Query(alias="status")` so the public URL stays `?status=...` while the Python identifier `scan_status` avoids shadowing `fastapi.status`.
- Encode the cursor as base64url-JSON `{t, i}` rather than just an opaque ID — keeps the cursor self-describing for debugging without exposing schema details (cursor strings are still treated as opaque by the client).
- Validate `created_after` / `created_before` via manual `datetime.fromisoformat(...).replace(tzinfo=timezone.utc)` rather than typing the params as `datetime` directly. FastAPI's auto-parse would have produced a less controllable 422 shape and risked timezone-naivety mismatches against the `TIMESTAMPTZ` column. The explicit form gives a clean `invalid_created_after` / `invalid_created_before` error code per param.
- Use the `limit+1 fetch` trick rather than a separate `COUNT()` to determine if `next_cursor` should be set — one query, predictable plan, no second roundtrip.
- Local test fixtures redeclared rather than imported from `test_scans.py` — pytest collection-order dependencies between test files are a known footgun; redeclaring is ~50 lines of duplication for guaranteed isolation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 – Bug] LST-005 URL-encoding of `+00:00` in ISO timestamps**
- **Found during:** Task 2 (first pytest run)
- **Issue:** `datetime.now(timezone.utc).isoformat()` produces `...+00:00`. When interpolated raw into a query string and parsed by Starlette's URL parser, `+` is decoded as space, so the handler received `... 00:00` and `datetime.fromisoformat` raised `ValueError` → 422. The handler is correct; the test was passing a malformed URL.
- **Fix:** Wrap each ISO string in `urllib.parse.quote(..., safe="")` before splicing into the query string. Test now passes; the bug was test-side, not handler-side.
- **Files modified:** `backend/tests/test_scans_list.py` (added `from urllib.parse import quote` and quoted the two timestamps in `test_list_scans_date_range`).
- **Commit:** `34a23bf` (committed as part of the test file — the original failing first-pass was never committed, only the fixed version).

**Total deviations:** 1 auto-fixed (Rule 1, test-side); 0 architectural decisions deferred to user.
**Impact on plan:** None — plan executed exactly as specified for the handler; the test-side fix is invisible to the contract.

## Authentication Gates

None — no auth flow required for this plan beyond the standard Clerk JWT (already wired by Phase 6 / Plan 01).

## Issues Encountered

- The test environment runs Python 3.14 system-wide while the backend venv is 3.12. Direct `python -c "from app.routes.scans import list_scans"` outside the test environment cannot satisfy `app.settings` env-var requirements without stubbing. Resolution: rely on the test suite's `conftest.py` env-var stubs to exercise the import path — `pytest tests/test_scans_list.py` collecting + importing the test file (which imports the handler transitively) is the canonical importability proof. All 10 tests passed → handler is importable, registered, and behaviour-correct.

## User Setup Required

None — no external service configuration changes. Existing Clerk / R2 / Stripe / Postgres setup unchanged.

## Next Phase Readiness

- **Plan 07-03 (scan compare endpoint)** is unblocked: the compare handler will reuse the same `set_config('app.current_team_id', :t, true)` + RLS scoping pattern demonstrated by `list_scans` and the `seed_scan_factory` fixture pattern from `test_scans_list.py`.
- **Plan 07-05 (dashboard scaffold)** is unblocked: the home dashboard's recent-scans table and `/scans` page now have a real backend to call (`GET /v1/scans?limit=N`).
- **Plan 07-06 (scans list UI)** is unblocked: the four filter affordances (search / environment / status / date range) the dashboard table will render are all in place.
- **Plan 07-08 (compare frontend)** is partially unblocked: the scan picker UI in the compare page can already populate from `GET /v1/scans` even before 07-03's compare endpoint lands.

## Self-Check: PASSED

- `[ -f backend/app/routes/scans.py ]` → FOUND
- `[ -f backend/tests/test_scans_list.py ]` → FOUND
- `git log --oneline | grep 5f354d0` → FOUND (Task 1)
- `git log --oneline | grep 34a23bf` → FOUND (Task 2)
- `grep -c '^async def test_\|^def test_' backend/tests/test_scans_list.py` → 10
- `grep -c 'next_cursor' backend/tests/test_scans_list.py` → 12 (≥ 4 required)
- `grep -n 'LST-008' backend/tests/test_scans_list.py` → 2 matches (docstring header + per-test docstring)
- `grep -nE 'async def list_scans' backend/app/routes/scans.py` → 1 match
- `grep -c 'ScanListResp' backend/app/routes/scans.py` → 4 (import + decorator + return-annotation + return-call; ≥ 2 required)
- `grep -c '_encode_cursor' backend/app/routes/scans.py` → 2 (def + call)
- `grep -c 'ilike' backend/app/routes/scans.py` → 3 (one per searched column)
- `grep -c "set_config.*current_team_id" backend/app/routes/scans.py` → 4 (commit_scan + commit-response + get_scan + list_scans)
- `pytest tests/test_scans_list.py -x -q --no-cov` → 10 passed in 35.79s
- `pytest tests/ -x -q --no-cov` → 67 passed in 59.24s (no regression; was 57 before)

---
*Phase: 07-saas-dashboard-history-share*
*Completed: 2026-04-28*
