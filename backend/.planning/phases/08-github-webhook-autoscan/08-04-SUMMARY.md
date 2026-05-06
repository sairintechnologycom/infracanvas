---
phase: 08-github-webhook-autoscan
plan: "08-04"
subsystem: api
tags: [fastapi, slack, webhook, rls, pydantic, tdd]

# Dependency graph
requires:
  - phase: 08-github-webhook-autoscan
    provides: Phase 8 foundation — GitHub webhook handler (08-01), scan_repo worker (08-02, 08-03)
provides:
  - "PATCH /v1/integrations/slack endpoint — validates URL prefix, sets RLS GUC, writes teams.slack_webhook_url"
  - "3 pytest tests (RED→GREEN) covering valid URL, invalid URL, missing field"
affects:
  - dashboard/app/api/integrations/slack/route.ts (plan 06 proxy consumer)
  - scan_repo worker (reads slack_webhook_url from teams table to send alerts)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "require_principal override (stable dep key) for mock-only tests that need auth bypass without Postgres"
    - "Double async-CM pattern: async with sm() as session, session.begin()"
    - "URL prefix validation before DB write — SSRF guard (T-8-04-01)"

key-files:
  created:
    - backend/app/routes/integrations.py
    - backend/tests/api/test_integrations.py
  modified:
    - backend/app/main.py

key-decisions:
  - "Override require_principal (not require_role closure) in dependency_overrides — closures returned by the require_role factory are new objects each call; only require_principal is a stable, importable reference that works as a dict key"

patterns-established:
  - "URL-prefix SSRF guard: validate webhook URL starts with trusted host before any DB write; 422 HTTP_UNPROCESSABLE_ENTITY on failure"
  - "RLS GUC pattern: SELECT set_config('app.current_team_id', :t, true) before UPDATE so Postgres RLS policies scope the write to the caller's team"

requirements-completed:
  - WBH-03

# Metrics
duration: 6min
completed: 2026-05-05
---

# Phase 8 Plan 04: Integrations Slack Webhook Endpoint Summary

**PATCH /v1/integrations/slack with URL-prefix SSRF guard, RLS GUC scoping, and require_role auth gate — 3/3 TDD tests green**

## Performance

- **Duration:** 6 min
- **Started:** 2026-05-05T12:36:22Z
- **Completed:** 2026-05-05T12:41:44Z
- **Tasks:** 2 (TDD RED + TDD GREEN)
- **Files modified:** 3

## Accomplishments

- Created `backend/app/routes/integrations.py` with `save_slack_webhook` handler implementing the full WBH-03 contract
- URL validation rejects any URL not starting with `https://hooks.slack.com/` → 422 (T-8-04-01 SSRF mitigation)
- RLS GUC `set_config('app.current_team_id', :t, true)` scopes the UPDATE to the authenticated team's row (T-8-04-02)
- `require_role("owner", "admin", "member")` gate blocks unauthenticated/unprivileged writes (T-8-04-03)
- Router registered in `backend/app/main.py` — endpoint reachable at `/v1/integrations/slack`
- 3 pytest tests (TDD RED → GREEN): valid URL → 200, invalid URL → 422, missing field → 422

## Task Commits

1. **Task 1: TDD RED — 3 failing tests** - `cc163b5` (test)
2. **Task 2: TDD GREEN — implement integrations.py + register router** - `dfec285` (feat)

**Plan metadata:** `(docs commit follows)`

## TDD Gate Compliance

- RED gate commit: `cc163b5` — `test(08-04): add 3 failing tests for PATCH /v1/integrations/slack (TDD RED)`
- GREEN gate commit: `dfec285` — `feat(08-04): implement PATCH /v1/integrations/slack — 3/3 tests green`

## Files Created/Modified

- `backend/app/routes/integrations.py` — PATCH /v1/integrations/slack handler with SlackWebhookBody Pydantic model, URL prefix validation, RLS GUC, UPDATE query
- `backend/tests/api/test_integrations.py` — 3 tests (no Postgres testcontainer needed; auth + DB mocked via dependency_overrides + monkeypatch)
- `backend/app/main.py` — added `from app.routes import integrations as integrations_routes` + `app.include_router(integrations_routes.router)`

## Decisions Made

- **Override `require_principal` not `require_role` in dependency_overrides**: `require_role` is a factory that returns a new closure each call — using it as a dict key in `dependency_overrides` creates an object that doesn't match the one registered at route-definition time. Overriding `require_principal` (the stable, importable callable that all `require_role` closures chain through) is the correct approach.

## Deviations from Plan

None — plan executed exactly as written. The test fixture pattern was adapted to use `require_principal` override (instead of the plan's example `require_role(...)` key) based on FastAPI dependency resolution semantics, but this is correctness rather than scope change.

## Issues Encountered

- Python 3.11 is the shell default; the backend requires Python 3.12. Used the existing project venv at `backend/.venv` (Python 3.12.13) to run pytest. No packages needed installation.
- Coverage gate reports failure on the whole-suite total (38% vs 80% required) — this is a pre-existing condition affecting all test runs in this project, not introduced by this plan.

## Known Stubs

None — `save_slack_webhook` writes the URL to `teams.slack_webhook_url` via a real (mocked in tests) UPDATE query. No placeholder values or hardcoded returns.

## Threat Flags

No new network endpoints, auth paths, or schema changes beyond what the plan's threat model covers. `PATCH /v1/integrations/slack` is already in the threat model at T-8-04-01..03.

## Next Phase Readiness

- `PATCH /v1/integrations/slack` is live and tested — ready for the dashboard proxy (`dashboard/app/api/integrations/slack/route.ts`) to wire through
- `teams.slack_webhook_url` is now writable via API; `scan_repo` worker (08-03) can read it to send Critical-findings Slack alerts
- Phase 8 wave 2 complete (plans 08-03 + 08-04 both done)

## Self-Check: PASSED

- backend/app/routes/integrations.py: FOUND
- backend/tests/api/test_integrations.py: FOUND
- .planning/phases/08-github-webhook-autoscan/08-04-SUMMARY.md: FOUND
- commit cc163b5: FOUND
- commit dfec285: FOUND

---
*Phase: 08-github-webhook-autoscan*
*Completed: 2026-05-05*
