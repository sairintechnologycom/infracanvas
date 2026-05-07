---
phase: 10
plan: "02"
subsystem: backend/agent
tags: [dc-agent, site-token, rls, alembic, fastapi, auth]
dependency_graph:
  requires: ["10-01"]
  provides: ["backend POST /v1/sites", "backend POST /v1/agent/routes", "backend POST /v1/agent/flows", "dc_site_by_token_hash SECDEF fn"]
  affects: ["10-07 (Go agent push target)", "Phase 11 dashboard site management"]
tech_stack:
  added: ["dc_site_by_token_hash SECURITY DEFINER SQL function (migration 010)"]
  patterns: ["SHA-256 token lookup hash (mirrors share_link_by_token migration 006)", "FORCE RLS + SECURITY DEFINER bypass for cross-team token resolution", "require_site_token FastAPI dep parallel to require_principal", "NullPool TestClient for asyncpg in pytest"]
key_files:
  created:
    - backend/migrations/versions/20260507_010_dc_sites.py
    - backend/app/auth/site_token.py
    - backend/app/schemas/agent.py
    - backend/app/routes/agent.py
  modified:
    - backend/app/db/models.py
    - backend/app/main.py
    - backend/tests/test_agent.py
decisions:
  - "Added dc_site_by_token_hash() SECURITY DEFINER function to migration 010 — required because dc_sites has FORCE ROW LEVEL SECURITY and require_site_token cannot set app.current_team_id before resolving the team from the token (circular dependency). Mirrors share_link_by_token() from migration 006."
  - "require_site_token uses raw_session + text() SQL call to SECURITY DEFINER fn, not ORM SELECT — ORM would trigger RLS and fail without team context."
  - "All 8 test_agent.py tests are async def (asyncio_mode=auto with testcontainer fixtures requires this); two no-DB tests (missing_bearer) remain sync def using TestClient(create_app())."
metrics:
  duration: "~35 minutes (active execution)"
  completed: "2026-05-07"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 7
---

# Phase 10 Plan 02: DC Agent Backend — Site-Token Auth + Agent Endpoints Summary

Site-token issuance (POST /v1/sites with SHA-256 hash storage), SECURITY DEFINER cross-team token resolution, and agent push endpoints (POST /v1/agent/routes + POST /v1/agent/flows) with full RLS isolation — all 8 backend test stubs flipped from SKIPPED to PASSING.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Migration + ORM model + site_token dep + schemas | f1ac250 | migration 010, models.py, site_token.py, schemas/agent.py |
| 2 | Agent routes + main.py wiring + GREEN test flip | f631c7b | routes/agent.py, main.py, test_agent.py, site_token.py (updated), migration (updated) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added SECURITY DEFINER function dc_site_by_token_hash() to migration 010**

- **Found during:** Task 1 (discovered during Task 2 verification — tests returning `invalid_site_token` even with properly seeded dc_sites rows)
- **Issue:** dc_sites has `FORCE ROW LEVEL SECURITY` with `dc_sites_team_isolation` policy requiring `app.current_team_id = token's team`. But `require_site_token` doesn't know the team until AFTER it finds the row — circular dependency. Direct `infracanvas_app` SELECT returns 0 rows without team context set.
- **Fix:** Added `dc_site_by_token_hash(p_lookup_hash text)` SECURITY DEFINER function to migration 010 (exact pattern from `share_link_by_token()` in migration 006 and `team_by_clerk_org()` in migration 003). Updated `require_site_token` to call `SELECT id, team_id FROM dc_site_by_token_hash(:h)` instead of direct table SELECT.
- **Files modified:** `backend/migrations/versions/20260507_010_dc_sites.py`, `backend/app/auth/site_token.py`
- **Commits:** f1ac250 (migration), f631c7b (site_token.py final)

**2. [Rule 3 - Blocking] Async test functions required for DB-dependent tests**

- **Found during:** Task 2 test execution
- **Issue:** `asyncio_mode="auto"` in pyproject.toml means async generator fixtures (pg_container, seed_session, app_session) require `async def` test functions. Initial design used sync def with `asyncio.get_event_loop().run_until_complete()` which raised `RuntimeError: There is no current event loop`.
- **Fix:** Rewrote all 6 DB-dependent test functions as `async def`. The 2 no-DB tests (missing_bearer) remain `sync def` using `TestClient(create_app())`.
- **Files modified:** `backend/tests/test_agent.py`
- **Commit:** f631c7b

**3. [Rule 1 - Bug] Ruff I001 import ordering in test_agent.py**

- **Found during:** Task 2 pre-commit linting
- **Issue:** `from jwt import PyJWKClient` must come before `import app.auth.clerk` per isort (third-party before first-party).
- **Fix:** Swapped import order in `_patch_clerk()` helper's local imports.
- **Files modified:** `backend/tests/test_agent.py`
- **Commit:** f631c7b

## Test Results

```
tests/test_agent.py::test_create_site_returns_one_time_token PASSED
tests/test_agent.py::test_create_site_requires_owner_role PASSED
tests/test_agent.py::test_push_routes_rejects_missing_bearer PASSED
tests/test_agent.py::test_push_routes_rejects_invalid_site_token PASSED
tests/test_agent.py::test_push_routes_accepts_valid_site_token PASSED
tests/test_agent.py::test_push_flows_rejects_missing_bearer PASSED
tests/test_agent.py::test_push_flows_accepts_valid_site_token PASSED
tests/test_agent.py::test_dc_sites_rls_isolates_teams PASSED

8 passed in 6.71s
```

All 8 stubs from Plan 10-01 flipped from SKIPPED to PASSING.

## Known Stubs

None. All endpoints return meaningful responses:
- POST /v1/sites: returns site_id, name, one-time site_token
- POST /v1/agent/routes: returns {"ok": True} + logs batch (Phase 11 will persist)
- POST /v1/agent/flows: returns {"ok": True} + logs batch (Phase 11 will persist)

The log-only behavior for routes/flows push is intentional per plan: "Phase 10 logs only — Phase 11 persists."

## Threat Flags

None beyond what was declared in the plan's threat model. The dc_site_by_token_hash() SECURITY DEFINER function is scoped to infracanvas_app EXECUTE only — PUBLIC revoked. RLS isolation test (TMM-01) confirmed team_a rows invisible under team_b context.

## Pre-existing Issues (Out of Scope)

- `app/db/models.py:66`: mypy "Missing type parameters for generic type dict" — pre-existing
- `app/auth/clerk.py:128`: mypy missing return type — pre-existing
- `tests/test_services_scans.py::test_finalize_scan_*`: pre-existing failure unrelated to this plan

These were confirmed pre-existing by checking they fail on the same code paths before Plan 10-02 changes. Logged for deferred resolution.

## Self-Check: PASSED

Files exist:
- backend/migrations/versions/20260507_010_dc_sites.py: FOUND
- backend/app/db/models.py (DCSite class): FOUND
- backend/app/auth/site_token.py: FOUND
- backend/app/schemas/agent.py: FOUND
- backend/app/routes/agent.py: FOUND
- backend/app/main.py (agent_routes wired): FOUND
- backend/tests/test_agent.py (8 tests): FOUND

Commits exist:
- f1ac250: FOUND (Task 1)
- f631c7b: FOUND (Task 2)
