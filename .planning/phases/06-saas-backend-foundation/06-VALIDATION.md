---
phase: 6
slug: saas-backend-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-24
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend/) + pytest-asyncio + testcontainers-postgres + moto |
| **Config file** | `backend/pyproject.toml` [tool.pytest.ini_options] (Wave 0 installs) |
| **Quick run command** | `cd backend && pytest -m "not slow" -x` |
| **Full suite command** | `cd backend && pytest --cov=app --cov-branch --cov-fail-under=80` |
| **Estimated runtime** | ~45s quick / ~3min full (Testcontainers cold-start dominates) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest -m "not slow" -x`
- **After every plan wave:** Run `cd backend && pytest --cov=app --cov-branch --cov-fail-under=80`
- **Before `/gsd-verify-work`:** Full suite must be green; `fly deploy --dry-run` validates `fly.toml`
- **Max feedback latency:** 45 seconds (quick) / 180 seconds (full)

---

## Per-Task Verification Map

*Populated by planner from PLAN.md task breakdown. Template row:*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 6-01-01 | 01 | 0 | Wave 0 | — | pytest scaffold exists | infra | `test -f backend/pyproject.toml` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/pyproject.toml` — Ruff/MyPy/pytest config mirroring cli/pyproject.toml
- [ ] `backend/tests/conftest.py` — shared fixtures (testcontainers Postgres, moto R2, Clerk JWT fixture, taskiq in-memory broker)
- [ ] `backend/tests/fixtures/bypass_role.sql` — test-only SQL that creates `infracanvas_test` role WITH BYPASSRLS for seed fixtures
- [ ] `backend/alembic.ini` + `backend/alembic/env.py` (async variant per SQLAlchemy cookbook)
- [ ] Framework install: `uv pip install fastapi uvicorn sqlalchemy[asyncio] asyncpg alembic pytest pytest-asyncio testcontainers[postgresql] moto aioboto3 stripe svix sentry-sdk[fastapi] structlog taskiq taskiq-redis uuid_utils pyjwt[crypto]`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Stripe live-mode meter event lands in Stripe dashboard | TMM-02 | Prod Stripe account required; test-mode events don't cross into live. | After prod deploy, trigger one scan commit; open Stripe Dashboard → Billing → Meters → `infracanvas.scan` → confirm event with identifier=scan_id within 60s. |
| Axiom dataset receives structured logs from Fly | OBS-01 | Requires Fly log drain + Axiom ingest token wired; no in-process hook. | After prod deploy, hit `GET /health`; within 60s query Axiom `['infracanvas'] \| where request_id == "<uuid>"` → one row with team_id bound. |
| Sentry captures an exception from prod FastAPI | OBS-02 | Requires live Sentry DSN + real request. | After prod deploy, trigger `GET /v1/_debug/boom` (dev-only endpoint removed before GA); Sentry issue appears within 60s with `team_id` tag. |
| Fly `release_command = "alembic upgrade head"` blocks traffic on migration failure | API-01, D-15 | Requires real Fly deploy; local can't simulate release_command rollback. | Merge a deliberately-broken migration to a staging branch; `fly deploy` — verify new Machine is NOT promoted and old Machine still serves traffic. |

---

## Validation Dimensions (Nyquist)

*Sourced from 06-RESEARCH.md § Validation Architecture. 10 dimensions — 8 required + 2 bonus.*

| # | Dimension | Primary Artifact | Command / Evidence |
|---|-----------|------------------|-------------------|
| 1 | Functional correctness | Contract test per endpoint (`test_scan_upload_flow.py`) | `pytest backend/tests/api/` — every route has happy + 4xx paths |
| 2 | Type safety | MyPy strict + Pydantic v2 request/response models | `cd backend && mypy --strict app/` exits 0 |
| 3 | Integration / external contracts | OpenAPI snapshot + Svix signature fixture + Stripe v2 payload fixture | `pytest backend/tests/contracts/` — `schemathesis run openapi.json` in CI |
| 4 | RLS enforcement (CRITICAL) | `RLS-*` integration tests using real Postgres via Testcontainers + dual role seeding | `pytest backend/tests/rls/ -m rls` — must pass against un-mocked Postgres |
| 5 | Observability signal presence | Log-capture test that greps JSON output for `request_id`, `team_id`, `user_id`; Sentry-mock asserts `set_tag` calls | `pytest backend/tests/observability/` |
| 6 | Billing idempotency | Meter-event replay test: post commit twice with same scan_id → exactly 1 meter event recorded (moto-stripe mock) | `pytest backend/tests/billing/ -m meters` |
| 7 | Migration rollback | Alembic downgrade round-trip for every revision (up → down → up clean) | `pytest backend/tests/migrations/` runs `alembic upgrade head && alembic downgrade base && alembic upgrade head` |
| 8 | Deploy / release_command | `fly deploy --dry-run` + lint of `fly.toml`; CI job parses `[processes]` blocks | `python scripts/validate_fly_toml.py backend/fly.toml` |
| 9 (bonus) | Request-ID continuity across sync→async boundary | Integration test: upload commit → worker job → assert both log streams share request_id | `pytest backend/tests/observability/test_request_id_propagation.py` |
| 10 (bonus) | R2 presigned URL correctness | moto-based test: signed PUT enforces object key prefix; signed GET TTL ≤ 300s | `pytest backend/tests/storage/` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
