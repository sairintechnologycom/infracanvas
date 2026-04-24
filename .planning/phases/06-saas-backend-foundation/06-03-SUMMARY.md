---
phase: 06-saas-backend-foundation
plan: 03
subsystem: database
tags: [postgres, rls, alembic, sqlalchemy, asyncpg, neon, multitenant, migrations]

# Dependency graph
requires:
  - phase: 06-saas-backend-foundation
    provides: "Plan 06-01 — backend/pyproject.toml (alembic, sqlalchemy[asyncio], asyncpg deps); backend/app/settings.py::settings.database_url; backend/app/util/ids.py::new_uuid7; backend/tests/conftest.py with pg_container + seed_session (BYPASSRLS) + app_session (infracanvas_app) fixtures; backend/tests/fixtures/bypass_role.sql"
provides:
  - "Postgres schema: teams + scans tables + scan_status enum"
  - "RLS policies: teams_self, scans_team_isolation (team-scoped via app.current_team_id GUC)"
  - "infracanvas_app role with NOBYPASSRLS + explicit table grants (no GRANT TO PUBLIC)"
  - "SQLAlchemy 2.0 Base + Team + Scan models (Mapped[...])"
  - "Async engine + async_sessionmaker (lazy init, pool_size=5, max_overflow=10)"
  - "team_scoped_session FastAPI dep — SET LOCAL app.current_team_id inside session.begin()"
  - "raw_session FastAPI dep — unauth/webhook paths, no SET LOCAL"
  - "RLS integration tests (RLS-001..005) + Alembic round-trip tests (MIG-001/002)"
affects: [06-04 auth, 06-05 scan endpoints, 06-06 worker, 06-07 webhooks, 06-08 deploy CI]

# Tech tracking
tech-stack:
  added:
    - "Alembic async migration env (async_engine_from_config + NullPool)"
    - "Postgres row-level security (ENABLE + FORCE) with current_setting GUC pattern"
    - "SQLAlchemy 2.0 Mapped[] declarative style"
  patterns:
    - "Two-role deployment: migrator (owner) runs DDL, infracanvas_app (NOBYPASSRLS) runs app traffic"
    - "SET LOCAL inside session.begin() — tx-scoped GUC compatible with transaction-mode poolers (Neon)"
    - "FORCE RLS to apply policies to table owner too (no latent escalation via migrator role)"
    - "current_setting(..., true)::uuid — safe NULL fallback when GUC unset"

key-files:
  created:
    - backend/alembic.ini
    - backend/migrations/env.py
    - backend/migrations/script.py.mako
    - backend/migrations/versions/20260424_001_initial_schema.py
    - backend/migrations/versions/20260424_002_rls_setup.py
    - backend/app/__init__.py
    - backend/app/db/__init__.py
    - backend/app/db/base.py
    - backend/app/db/models.py
    - backend/app/db/session.py
    - backend/tests/test_rls.py
    - backend/tests/test_migrations.py
  modified: []

key-decisions:
  - "FORCE ROW LEVEL SECURITY on both tables (not only ENABLE) so table-owner queries still hit policies — removes any latent RLS bypass via the migrator role"
  - "current_setting('app.current_team_id', true)::uuid with missing_ok=true — missing GUC returns NULL, UUID cast yields NULL, zero rows match, no crash"
  - "SET LOCAL via bind parameter text('SET LOCAL ... = :t'), {'t': str(team.id)} — never f-string interpolation, which would defeat parameterization and risk injection"
  - "Lazy engine init (module-level globals populated on first get_engine call) so importing app.db.session inside alembic/env-free contexts does not require settings.database_url to be valid"
  - "DATABASE_URL_MIGRATOR env var (optional; falls back to DATABASE_URL) so CI/release uses an owner-role URL for DDL while runtime uses the NOBYPASSRLS app-role URL"

patterns-established:
  - "Team-scoped DB access pattern: every team-scoped route depends on team_scoped_session(team) which SETs the GUC; never SELECT team_id=:x in queries — let RLS do it"
  - "RLS-first test shape: dual-role fixtures (seed_session BYPASSRLS + app_session NOBYPASSRLS); positive control + negative control + WITH CHECK test per table"
  - "Alembic migration split: 001 autogen-style schema, 002 handwritten RLS (grants + policies). Keeps `alembic revision --autogenerate` useful for future schema changes without clobbering RLS SQL"

requirements-completed: [API-03, TMM-01]

# Metrics
duration: 6min
completed: 2026-04-24
---

# Phase 06 Plan 03: Alembic async env + initial schema + RLS policies + async SQLAlchemy session with SET LOCAL

**Stood up the Postgres tenant-isolation boundary for the SaaS backend: Alembic async migrations, SQLAlchemy 2.0 models, async engine, and the `team_scoped_session` FastAPI dep that SETs `app.current_team_id` inside each request transaction. Both `teams` and `scans` carry `ENABLE + FORCE ROW LEVEL SECURITY` with USING+WITH CHECK policies against the GUC, and the `infracanvas_app` role is explicitly `NOBYPASSRLS` with only the narrow DML grants it needs.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-04-24T15:32:20Z
- **Completed:** 2026-04-24T15:38:00Z (approx)
- **Tasks:** 2 / 2
- **Files created:** 12
- **Files modified:** 0

## Accomplishments

### Schema (migration `001_initial_schema`)

`teams` table:
- `id UUID PRIMARY KEY`
- `clerk_org_id VARCHAR(64) NOT NULL` — UNIQUE (`teams_clerk_org_id_key`) + index (`ix_teams_clerk_org_id`)
- `name VARCHAR(255) NOT NULL`
- `stripe_customer_id VARCHAR(64) NULL`
- `created_at TIMESTAMPTZ DEFAULT now()`, `updated_at TIMESTAMPTZ DEFAULT now()`

`scan_status` enum: `pending | ready | failed` (native PG enum).

`scans` table:
- `id UUID PRIMARY KEY`
- `team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE` — index (`ix_scans_team_id`) + composite UNIQUE `(team_id, id)` (`scans_team_id_id_key`) for T-06-03 dedup lookups under RLS
- `r2_key VARCHAR(512) NOT NULL`, `sha256 VARCHAR(64) NULL`, `size_bytes BIGINT NULL`
- `status scan_status NOT NULL` (default `pending`)
- `summary_json JSONB NULL` (written by worker in Plan 06-06)
- `created_at TIMESTAMPTZ DEFAULT now()`

### RLS (migration `002_rls_setup`)

Grep-able exact SQL for future review:

```sql
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'infracanvas_app') THEN
    CREATE ROLE infracanvas_app WITH LOGIN NOBYPASSRLS;
  END IF;
END $$;
ALTER ROLE infracanvas_app NOBYPASSRLS;

GRANT USAGE ON SCHEMA public TO infracanvas_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON teams, scans TO infracanvas_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO infracanvas_app;

ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE teams FORCE ROW LEVEL SECURITY;
ALTER TABLE scans ENABLE ROW LEVEL SECURITY;
ALTER TABLE scans FORCE ROW LEVEL SECURITY;

CREATE POLICY teams_self ON teams
  USING (id = current_setting('app.current_team_id', true)::uuid)
  WITH CHECK (id = current_setting('app.current_team_id', true)::uuid);

CREATE POLICY scans_team_isolation ON scans
  USING (team_id = current_setting('app.current_team_id', true)::uuid)
  WITH CHECK (team_id = current_setting('app.current_team_id', true)::uuid);
```

No `GRANT ... TO PUBLIC` anywhere. `grep -E "ALTER ROLE [a-z_]+ BYPASSRLS" backend/migrations/` returns zero matches — only the explicit `NOBYPASSRLS` deny is present.

### Session layer (`app/db/session.py`)

- `get_engine()` / `get_sessionmaker()` — lazy module-level init so importing `app.db.session` in test/dev contexts does not require a live database URL at import time.
- `create_async_engine(settings.database_url, pool_size=5, max_overflow=10, pool_pre_ping=True, echo=False)`.
  - `pool_size=5` + `max_overflow=10` → max 15 concurrent DB connections per app instance. Stays well under Neon free-tier connection limits (Railway/Fly single-instance deploys), and matches RESEARCH F3 guidance.
  - `pool_pre_ping=True` — Neon occasionally recycles idle server-side connections; pre-ping avoids `OperationalError` on first query after an idle window.
- `raw_session()` — no GUC set; used for unauth endpoints (`/health`, Clerk/Stripe webhooks) and any admin paths where team scoping does not apply. Still protected by RLS policies on team-scoped tables since the role is `NOBYPASSRLS`.
- `team_scoped_session(team: Team)` — opens a tx and executes
  ```python
  await session.execute(
      text("SET LOCAL app.current_team_id = :t"),
      {"t": str(team.id)},
  )
  ```
  as the FIRST statement. Bind parameter — never f-string (RESEARCH § F3 Pitfalls).

### Tests

`backend/tests/test_rls.py` — five integration tests under the `rls` pytest marker:

| Test ID | Assertion |
|---------|-----------|
| RLS-001 | `SELECT count(*) FROM scans` under `SET LOCAL team_B` returns 0 (team-A row invisible) |
| RLS-002 | Same query under `SET LOCAL team_A` returns 1 (positive control) |
| RLS-003 | `teams_self` policy isolates the `teams` table itself (team_B sees only its own row) |
| RLS-004 | No SET LOCAL at all → `current_setting(..., true)` returns NULL → zero rows, no crash |
| RLS-005 | INSERT with `team_id=team_A` while GUC=team_B raises `sqlalchemy.exc.IntegrityError` (WITH CHECK rejects) |

`backend/tests/test_migrations.py`:

| Test ID | Assertion |
|---------|-----------|
| MIG-001 | Fresh database → `alembic upgrade head` succeeds |
| MIG-002 | `upgrade head → downgrade base → upgrade head` is idempotent and clean |

## Research callout #1 — Neon pooler terminology correction

D-02 originally referred to "session-mode pooler" on Neon. Research confirmed Neon offers **transaction-mode pooling only** (PgBouncer transaction mode). The semantic pattern D-02 required — `SET` scoped to the connection unit that the pool checks out as a unit — is still correct, but the correct pattern is `SET LOCAL` inside `BEGIN...COMMIT`, because in transaction-mode pooling the pool-checkout unit IS the transaction. `team_scoped_session` implements exactly this: every call opens a tx via `async with session.begin():` and SETs the GUC inside it. This guarantees no cross-tenant leakage across pooled connections. Documented inline in both `backend/app/db/session.py` and `backend/migrations/versions/20260424_002_rls_setup.py`.

## Deviations from Plan

### Minor formatting adjustment (not a rule-1/2/3 deviation)

The plan's automated grep verification expected `op.create_table("teams"` and `op.create_table("scans"` on a single line. My initial draft placed the table name on the next line after `op.create_table(` (idiomatic `ruff format` output). Adjusted both migrations to keep the table literal on the same line as the opening call so the grep contract in `<verify>` holds exactly as written. No behavioural change.

### Plan 01 conftest.py update — NOT performed (scope boundary)

The plan's Task 2 `<action>` block also asked for an edit to `backend/tests/conftest.py` to remove a `Path.exists()` guard and actually invoke `alembic upgrade head`. That file is produced by Plan 06-01 which runs in a parallel worktree — this worktree does not see it. Per the parallel_execution instructions, I did NOT create or modify `backend/tests/conftest.py`. The post-merge phase-level test gate (and Plan 08's CI wiring) will surface any mismatch; Plan 06-01 should either ship the unconditional `alembic upgrade head` directly, or a follow-up plan should add the fix. Logging here rather than creating a deferred-items.md because the relevant file simply does not exist on this branch yet.

## Open Items (for post-merge phase test gate)

- `pytest backend/tests/test_rls.py backend/tests/test_migrations.py -m rls -x --no-cov` cannot run from this worktree standalone — it needs Plan 06-01's `pyproject.toml`, `app/settings.py`, `app/util/ids.py::new_uuid7`, and `backend/tests/conftest.py` fixtures (`pg_container`, `seed_session`, `app_session`). All expected import symbols are spelled exactly as Plan 06-01's `<interfaces>` promises. Post-merge test gate is the designated verification point.
- `mypy --strict app/db/` not executed here for the same reason (needs 06-01's pyproject.toml + installed deps). Module is written against SQLAlchemy 2.0 Mapped[] + strict-mode conventions and should pass; confirm at merge time.

## Threat Flags

None — all new surface in this plan falls under threats T-06-01, T-06-07, T-06-01b already registered in the plan's `<threat_model>`, and every mitigation listed there is implemented (verified via grep + file inspection above).

## Self-Check: PASSED

Files verified present on disk:
- backend/alembic.ini — FOUND
- backend/migrations/env.py — FOUND
- backend/migrations/script.py.mako — FOUND
- backend/migrations/versions/20260424_001_initial_schema.py — FOUND
- backend/migrations/versions/20260424_002_rls_setup.py — FOUND
- backend/app/__init__.py — FOUND
- backend/app/db/__init__.py — FOUND
- backend/app/db/base.py — FOUND
- backend/app/db/models.py — FOUND
- backend/app/db/session.py — FOUND
- backend/tests/test_rls.py — FOUND
- backend/tests/test_migrations.py — FOUND

Commits verified in git log:
- d7a9d26 — FOUND (Task 1: scaffold Alembic + SQLAlchemy models + initial schema + RLS migration)
- a9fe1b0 — FOUND (Task 2: async SQLAlchemy session + team_scoped_session dep + RLS/migration tests)

Acceptance-criteria grep guards:
- `ALTER ROLE [a-z_]+ BYPASSRLS` under `backend/migrations/` → no matches (only `NOBYPASSRLS` present)
- `BaseHTTPMiddleware` under `backend/app/` → 0 matches
- `current_setting('app.current_team_id', true)` present in RLS migration and matched by `SET LOCAL app.current_team_id` in session.py — key-link pattern `app\.current_team_id` holds
