---
phase: 06-saas-backend-foundation
plan: 01
title: Backend package scaffold + Wave 0 test infrastructure
subsystem: backend-foundation
tags: [scaffold, pytest, testcontainers, coverage-gate, wave-0]
requires:
  - cli/pyproject.toml (style blocks copied verbatim — Ruff, MyPy, coverage)
  - cli/tests/conftest.py (PER_MODULE_GATES + pytest_sessionfinish hook ported)
provides:
  - "backend/ pip-installable package (infracanvas-backend 0.1.0, Python >=3.12)"
  - "Dev extras: pytest + pytest-asyncio + pytest-cov + pytest-httpserver + respx + moto[s3] + testcontainers[postgresql] + ruff + mypy"
  - "Shared pytest fixtures: pg_container, seed_session, app_session, mock_clerk, mock_r2, mock_stripe, in_memory_broker"
  - "Per-module coverage gate at 80% for app/auth, app/routes, app/db, app/queue, app/billing, app/storage, app/obs"
  - "BYPASSRLS role SQL confined to backend/tests/fixtures/bypass_role.sql (T-06-07 mitigation)"
  - "backend/.env.example template (no secrets committed)"
affects:
  - None — brand-new package; no existing files modified.
tech-stack:
  added:
    - fastapi 0.115.x
    - uvicorn[standard] 0.32.x
    - pydantic 2.9.x + pydantic-settings 2.6.x
    - sqlalchemy[asyncio] 2.0.36 + asyncpg 0.30.x + alembic 1.14.x
    - taskiq 0.11.x + taskiq-redis 1.0.x
    - boto3 1.35.x + stripe >=11,<16
    - pyjwt[crypto] 2.9.x + svix 1.41.x
    - sentry-sdk[fastapi] 2.18.x + structlog 24.4.x + orjson 3.10.x
    - uuid_utils 0.14.x
    - infracanvas @ file:../cli (cross-package ResourceGraph import)
    - dev: pytest 8.3, pytest-asyncio 0.24, pytest-cov 6.0,
      pytest-httpserver 1.1, respx 0.21, moto[s3] 5.0,
      testcontainers[postgresql] 4.8, ruff 0.7, mypy 1.13
  patterns:
    - "Hatchling build, packages=[\"app\"] (mirrors cli's hatch layout)"
    - "Ruff E F I N W UP at line 100 (project-wide convention)"
    - "MyPy strict with ignore_missing_imports for libs lacking stubs"
    - "pytest asyncio_mode=auto + markers [slow, rls, meters]"
    - "coverage --cov=app --cov-branch --cov-fail-under=80"
key-files:
  created:
    - backend/pyproject.toml
    - backend/README.md
    - backend/app/__init__.py
    - backend/tests/__init__.py
    - backend/tests/conftest.py
    - backend/tests/fixtures/__init__.py
    - backend/tests/fixtures/bypass_role.sql
    - backend/tests/test_scaffold.py
    - backend/.env.example
    - backend/.gitignore
  modified: []
decisions:
  - Used `postgresql+psycopg2` sync URL for one-shot setup DDL in pg_container (role creation must run AUTOCOMMIT; asyncpg would require an async loop for what is trivially synchronous setup). Async engine is still used for seed_session / app_session per-test connections — production path remains fully async.
  - Added GSD_SKIP_TESTCONTAINERS env flag so Wave 0 smoke (before Docker is mandatory in the developer toolbox) can still run via `pytest tests/test_scaffold.py --no-cov`. Downstream plans will unset it.
  - Added a `with_team_ctx(session, team_id)` helper in conftest alongside `app_session` so RLS-* tests (Plan 03) get a single call-site for the `SET LOCAL app.current_team_id = :t` pattern instead of re-writing it per test.
  - Kept `app/main.py` on the coverage `omit` list (startup wiring is untestable in isolation) — matches cli's `__main__.py` omit.
  - Structured `mock_stripe.captured_requests` as a list of `{url, headers, payload}` dicts so downstream MET-* tests can assert both request shape AND headers (e.g. Idempotency-Key) without re-parsing.
metrics:
  duration_minutes: ~12
  tasks_completed: 2
  files_created: 10
  lines_added: 704
  completed: 2026-04-24
---

# Phase 6 Plan 01: Backend package scaffold + Wave 0 test infrastructure Summary

Scaffolded the brand-new `backend/` Python package with an installable `pyproject.toml`, all Phase 6 dep pins from RESEARCH § Standard Stack, and a 524-line `tests/conftest.py` exposing every downstream fixture by name — so later plans can assume `pg_container`, `seed_session`, `app_session`, `mock_clerk`, `mock_r2`, `mock_stripe`, and `in_memory_broker` already exist and just import them.

## pyproject.toml diff from cli/pyproject.toml

### Copied verbatim
- `[build-system]` (swapped `packages = ["app"]`)
- `[tool.ruff]` + `[tool.ruff.lint]` (E F I N W UP, line 100, py312)
- `[tool.mypy]` strict block
- `[tool.coverage.run]` / `[tool.coverage.report]` (swapped `source = ["app"]`; added `app/main.py` to omit)
- `requires-python = ">=3.12"`

### Added (not in cli)
- `[project].name = "infracanvas-backend"` (distinct from `infracanvas`)
- `[project].dependencies` — full FastAPI stack per RESEARCH § Standard Stack:
  - `fastapi~=0.115.0`, `uvicorn[standard]~=0.32.0`
  - `pydantic~=2.9.0` + `pydantic-settings~=2.6.0`
  - `sqlalchemy[asyncio]~=2.0.36` + `asyncpg~=0.30.0` + `alembic~=1.14.0`
  - `taskiq~=0.11.0` + `taskiq-redis~=1.0.0`
  - `boto3~=1.35.0`, `stripe>=11.0,<16.0`
  - `pyjwt[crypto]~=2.9.0` + `svix~=1.41.0`
  - `sentry-sdk[fastapi]~=2.18.0` + `structlog~=24.4.0` + `orjson~=3.10.0`
  - `uuid_utils~=0.14.0`
  - `infracanvas @ file:../cli` (path dep — gives backend direct access to `ResourceGraph` Pydantic models)
- `[project.optional-dependencies].dev` consolidates the test/lint stack (cli split it into `test` + used inline ruff/mypy; backend groups everything under `dev` for a single `pip install -e '.[dev]'` command).
- `[tool.pytest.ini_options].asyncio_mode = "auto"` (new — needed for pytest-asyncio across the backend suite).
- `[tool.pytest.ini_options].markers` — adds `slow`, `rls`, `meters`.
- `[[tool.mypy.overrides]]` for `taskiq.*`, `taskiq_redis.*`, `svix.*`, `uuid_utils.*`, `moto.*`, `testcontainers.*` (cli only overrode `hcl2.*`).

### Removed (cli-specific, not applicable to backend)
- `[project.scripts] infracanvas = "infracanvas.main:app"` — backend has no console entry point (FastAPI runs under uvicorn).
- `[tool.hatch.build].artifacts` for viewer template / YAML rules — backend has no such runtime artifacts.
- `[project.optional-dependencies].shadow` and `.flowmap` — CLI-only cloud-import extras.
- Classifiers pivot from "Console" to "Web Environment / Framework :: FastAPI".

## Fixtures exposed by backend/tests/conftest.py

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `pg_container` | session | Testcontainers Postgres 16 with both `infracanvas_app` (NOBYPASSRLS) and `infracanvas_test` (BYPASSRLS) roles provisioned. Runs `alembic upgrade head` only if `backend/alembic.ini` exists (guarded so Wave 0 works before Plan 03 lands Alembic). |
| `seed_session` | per-test | Async SQLAlchemy session connected as `infracanvas_test` — for seeding cross-team rows without RLS interference. |
| `app_session` | per-test | Async SQLAlchemy session connected as `infracanvas_app` — RLS active; callers wrap in `session.begin()` and call the exported `with_team_ctx(session, team_id)` helper to apply `SET LOCAL app.current_team_id`. |
| `mock_clerk` | per-test | Fresh RSA keypair + JWKS served via pytest-httpserver at a real localhost URL so PyJWKClient can fetch it. `.sign_jwt(sub, org_id, role=...)` mints Clerk v2 tokens with keys `azp, exp, iat, iss, sub, sid, v=2, o={id, rol}` (RESEARCH § F1 shape). |
| `mock_r2` | per-test | moto `@mock_aws` bucket `infracanvas-scans-test`; AWS env vars set for fixture scope and restored on teardown. |
| `mock_stripe` | per-test | respx intercepts `POST https://api.stripe.com/v2/billing/meter_events`; `.captured_requests` list records every POST; `.assert_meter_event(event_name, identifier, value)` helper. |
| `in_memory_broker` | per-test | `taskiq.InMemoryBroker()` with `is_worker_process=True` so task bodies fire synchronously in-process. `startup`/`shutdown` bracketed. |

Plus the `with_team_ctx(session, team_id)` helper coroutine — not a fixture, but exported from conftest.py so downstream RLS-* tests import it for the `SET LOCAL` idiom.

## Per-module coverage gate

Ported byte-for-byte from `cli/tests/conftest.py` (Phase 4 D-15):
- `_module_percents(cov)` — aggregates line + branch coverage per module prefix
- `pytest_sessionfinish(session, exitstatus)` — fails the session if any prefix falls below 80%

Only changes from cli version:
- `PER_MODULE_GATES` replaced with backend prefixes: `app/auth`, `app/routes`, `app/db`, `app/queue`, `app/billing`, `app/storage`, `app/obs` (each 80.0).
- The `source = ["app"]` semantic is set in `pyproject.toml` `[tool.coverage.run]`, matching the cli's parallel configuration.

## Deviations from RESEARCH § Standard Stack pins

None. Every pin lands exactly as specified in RESEARCH.md lines 933–983:

| Package | Plan pin | Implemented pin |
|---------|----------|-----------------|
| fastapi | `~=0.115.0` | `~=0.115.0` |
| uvicorn[standard] | `~=0.32.0` | `~=0.32.0` |
| pydantic | `~=2.9.0` | `~=2.9.0` |
| pydantic-settings | `~=2.6.0` | `~=2.6.0` |
| sqlalchemy[asyncio] | `~=2.0.36` | `~=2.0.36` |
| asyncpg | `~=0.30.0` | `~=0.30.0` |
| alembic | `~=1.14.0` | `~=1.14.0` |
| taskiq | `~=0.11.0` | `~=0.11.0` |
| taskiq-redis | `~=1.0.0` | `~=1.0.0` |
| boto3 | `~=1.35.0` | `~=1.35.0` |
| stripe | `>=11.0,<16.0` | `>=11.0,<16.0` |
| pyjwt[crypto] | `~=2.9.0` | `~=2.9.0` |
| svix | `~=1.41.0` | `~=1.41.0` |
| sentry-sdk[fastapi] | `~=2.18.0` | `~=2.18.0` |
| structlog | `~=24.4.0` | `~=24.4.0` |
| orjson | `~=3.10.0` | `~=3.10.0` |
| uuid_utils | `~=0.14.0` | `~=0.14.0` |

All dev pins match RESEARCH dev table too (pytest 8.3, pytest-asyncio 0.24, pytest-cov 6.0, pytest-httpserver 1.1, respx 0.21, moto[s3] 5.0, testcontainers[postgresql] 4.8, ruff 0.7, mypy 1.13).

## Deviations from plan

None that required deviation rules. A few clarifying choices called out as decisions above (sync psycopg2 URL for one-shot role DDL; `GSD_SKIP_TESTCONTAINERS` env flag for Wave 0 smoke; `with_team_ctx` helper export) — none violate plan acceptance criteria.

## Authentication gates

None — plan is pure scaffolding, no external services touched.

## Known Stubs

None. The scaffold intentionally contains no application code yet (empty `app/__init__.py`); the single `test_scaffold.py` test proves the package imports. This is the stated Wave 0 deliverable — it is NOT a stub that blocks the plan's goal.

## Threat Flags

None. Plan 01 adds no new security-relevant surface beyond the BYPASSRLS role SQL, which is already enumerated in the plan's threat model (T-06-07) and correctly confined to `backend/tests/fixtures/bypass_role.sql`. The `GRANT ALL` scope in that file is the plan-prescribed mitigation and is tightly bounded to the test-container filesystem by its location and conftest-only load path.

## Self-Check: PASSED

**Files created (all verified on disk):**
- `backend/pyproject.toml` — FOUND (valid TOML; `python -c "import tomllib; tomllib.load(open('backend/pyproject.toml','rb'))"` exits 0)
- `backend/README.md` — FOUND
- `backend/app/__init__.py` — FOUND (empty)
- `backend/tests/__init__.py` — FOUND (empty)
- `backend/tests/conftest.py` — FOUND (524 lines; `python -c "import ast; ast.parse(open('backend/tests/conftest.py').read())"` exits 0)
- `backend/tests/fixtures/__init__.py` — FOUND (empty)
- `backend/tests/fixtures/bypass_role.sql` — FOUND (contains `ALTER ROLE infracanvas_test BYPASSRLS`)
- `backend/tests/test_scaffold.py` — FOUND (contains `SCAFFOLD-001` docstring)
- `backend/.env.example` — FOUND (contains `STRIPE_METER_EVENT_NAME=infracanvas.scan` and all F11 secrets)
- `backend/.gitignore` — FOUND (excludes `.env`, `.ruff_cache/`, caches)

**Commits (verified in git log):**
- `e0e5569` feat(06-01): scaffold backend/ package with pyproject + env template — FOUND
- `ac42e8c` test(06-01): add backend pytest conftest + 7 shared fixtures + coverage gate — FOUND

**Plan acceptance criteria:**
- `backend/pyproject.toml` parses as valid TOML — PASS
- Every RESEARCH § Standard Stack dep pin present with matching operator — PASS
- `[tool.ruff.lint] select = ["E", "F", "I", "N", "W", "UP"]` — PASS
- `[tool.mypy] strict = true` — PASS
- `[tool.pytest.ini_options] cov-fail-under=80` — PASS
- `infracanvas @ file:../cli` present — PASS
- `backend/.env.example` lists every F11 secret name (ENV, CLERK_*, DATABASE_URL*, R2_*, REDIS_URL, STRIPE_*, SENTRY_DSN, GIT_SHA) — PASS
- `backend/.gitignore` excludes `.env` — PASS
- `backend/tests/conftest.py` defines all 7 fixtures — PASS
- `pg_container` provisions both RLS roles via dual SQL (inline APP_ROLE_SQL + fixtures/bypass_role.sql) — PASS
- `PER_MODULE_GATES` has 7 entries each at 80.0 — PASS
- `pytest_sessionfinish` hook + `_module_percents` ported verbatim from cli (only prefix list + source swapped) — PASS
- `mock_clerk.sign_jwt()` produces v2 Clerk token shape — PASS
- `mock_stripe.captured_requests` captures POSTs to `/v2/billing/meter_events` — PASS
- `test_scaffold.py::test_scaffold_is_importable` with `SCAFFOLD-001` docstring — PASS
- `cd backend && python -c "import ast; ast.parse(open('tests/conftest.py').read())"` exits 0 — PASS
- BYPASSRLS role SQL lives ONLY in `backend/tests/fixtures/bypass_role.sql` (no migrations exist yet to reference it) — PASS
