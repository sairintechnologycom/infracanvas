---
phase: 08-github-webhook-autoscan
plan: "08-01"
subsystem: database
tags: [alembic, postgres, sqlalchemy, security-definer, slack]

# Dependency graph
requires:
  - phase: 07.5-github-repo-connector
    provides: "github_installations table with github_installation_id column (referenced by team_id_for_installation function)"
provides:
  - "Alembic migration 009 adding teams.slack_webhook_url TEXT NULL + team_id_for_installation(bigint) SECURITY DEFINER function"
  - "Team ORM class with slack_webhook_url: Mapped[str | None] attribute"
affects:
  - "08-02 (GitHub webhook handler — uses team_id_for_installation SQL function)"
  - "08-03 (scan_repo worker — reads teams.slack_webhook_url for Slack alert)"
  - "08-04 (PATCH /v1/integrations/slack — writes teams.slack_webhook_url)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SECURITY DEFINER SQL function for pre-auth identity resolution (bypasses RLS when JWT context unavailable)"
    - "Nullable TEXT column for optional third-party webhook URL integration"

key-files:
  created:
    - "backend/migrations/versions/20260505_009_slack_webhook_url.py"
  modified:
    - "backend/app/db/models.py"

key-decisions:
  - "SECURITY DEFINER function team_id_for_installation(bigint) scoped to single SELECT team_id from github_installations — no cross-team data reachable (T-8-01-A mitigation)"
  - "slack_webhook_url stored as TEXT NULL (not a URL type) to avoid Postgres-level URL validation — Python layer validates the https://hooks.slack.com/ prefix on write"
  - "downgrade drops function BEFORE dropping column (dependency order: function has no column dep, but ordering is explicit for safety)"

patterns-established:
  - "SECURITY DEFINER function pattern for unauthenticated webhook routes: function does narrowest possible lookup (single column, single equality predicate, LIMIT 1)"

requirements-completed:
  - WBH-01

# Metrics
duration: 2min
completed: 2026-05-05
---

# Phase 8 Plan 01: DB Foundation — slack_webhook_url + SECURITY DEFINER Function Summary

**Alembic migration 009 adds teams.slack_webhook_url TEXT NULL and team_id_for_installation(bigint) SECURITY DEFINER SQL function, enabling GitHub webhook identity resolution without an RLS context and optional Slack alert delivery**

## Performance

- **Duration:** 2 min
- **Started:** 2026-05-05T06:40:01Z
- **Completed:** 2026-05-05T06:42:02Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created migration 009 chained from 008 (`down_revision = "008_scan_github_columns"`) with reversible upgrade/downgrade
- `team_id_for_installation(bigint) RETURNS uuid LANGUAGE sql SECURITY DEFINER STABLE` — lets the GitHub webhook handler (plan 02) resolve team_id from a push event's installation_id before any RLS GUC is set
- `teams.slack_webhook_url TEXT NULL` — used by plan 04 PATCH endpoint to save URLs and by plan 03 worker to fire Slack alerts
- Team ORM class updated with `slack_webhook_url: Mapped[str | None]` — plan 03 and 04 can import it directly

## Task Commits

Each task was committed atomically:

1. **Task 1: Write migration 009** - `9ce5af2` (feat)
2. **Task 2: Add slack_webhook_url to Team ORM class** - `990e27e` (feat)

**Plan metadata:** (see final commit below)

## Files Created/Modified

- `backend/migrations/versions/20260505_009_slack_webhook_url.py` — Alembic migration 009: adds slack_webhook_url TEXT NULL to teams + creates team_id_for_installation(bigint) SECURITY DEFINER function; downgrade drops function then column
- `backend/app/db/models.py` — Team ORM class: added `slack_webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)` after stripe_customer_id

## Decisions Made

- SECURITY DEFINER function is the canonical pattern for pre-auth identity lookups in this codebase (mirrors the share_link_by_token() function from migration 006). Scope is deliberately minimal — single column SELECT, single equality predicate, no joins, LIMIT 1, STABLE.
- `slack_webhook_url` is not a separate integrations table — one URL per team is sufficient for the MVP (D-04). A separate table would be warranted when multiple alert channels are added.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `mypy app/db/models.py` reports one pre-existing error: `summary_json: Mapped[dict | None]` missing type parameters (`dict` should be `dict[str, Any]`). This was present in the original file before any changes in this plan. Out-of-scope per SCOPE BOUNDARY rule; deferred.

## User Setup Required

None — migration runs at deploy time via `alembic upgrade head`. No external service configuration required for this plan.

## Threat Surface

No new network endpoints introduced. Two threats from plan's threat model confirmed mitigated:

| Threat | Mitigation |
|--------|-----------|
| T-8-01-A: SECURITY DEFINER exfiltrates cross-team data | Function only SELECTs team_id from github_installations WHERE github_installation_id = $1 — single column, single equality predicate, no joins |
| T-8-01-B: Slack webhook URL leaked via API | Column never returned in scan list/get responses; only read internally by the worker |

## Next Phase Readiness

- Plan 02 (GitHub webhook handler) unblocked — can call `SELECT team_id_for_installation(:iid)` via raw SQL
- Plan 03 (scan_repo Slack firing) unblocked — can `SELECT slack_webhook_url FROM teams WHERE id = :team_id`
- Plan 04 (PATCH /v1/integrations/slack) unblocked — Team ORM has the column for the UPDATE
- All downstream plans in wave 2 can import `Team.slack_webhook_url` from `app.db.models`

---
*Phase: 08-github-webhook-autoscan*
*Completed: 2026-05-05*
