---
phase: 06-saas-backend-foundation
plan: 07
subsystem: observability
tags: [sentry, fastapi, asyncpg, taskiq, instrumentation, error-tracking, tracing]
requires:
  - phase: 06-saas-backend-foundation
    provides: |
      Plan 06-02 — app.main:create_app FastAPI factory + lifespan stub for
      attaching observability hooks; settings.sentry_dsn / settings.git_sha
      / settings.env declared in app/settings.py.
      Plan 06-04 — app/auth/clerk.py require_principal sets sentry_sdk.set_user,
      set_tag(clerk_org_id), set_tag(request_id) on each authenticated request.
      Plan 06-06 — app/queue/broker.py WORKER_STARTUP scaffolded with an
      inline sentry_sdk.init placeholder (consolidated by this plan); taskiq
      middleware pipeline already calls sentry_sdk.set_tag and
      sentry_sdk.capture_exception per task.
provides:
  - "app/obs/sentry.py::init_sentry(role) — idempotent SDK init factory"
  - "Single Sentry project discriminated by process_role tag (api | worker)"
  - "FastAPI + Starlette + AsyncPG + Logging integrations wired"
  - "traces_sample_rate=0.1 + profiles_sample_rate=0.1 (D-20)"
  - "send_default_pii=False + LoggingIntegration(level=None, event_level=None) — T-06-08c PII mitigation"
  - "Dev-local no-op when settings.sentry_dsn is unset/empty"
affects:
  - 06-08 deploy reads settings.sentry_dsn from Fly secret + sets git_sha env
  - phase 13 revisits Sentry vs Logfire/Grafana migration (deferred)

tech-stack:
  added:
    - "FastApiIntegration(transaction_style='endpoint')"
    - "StarletteIntegration(transaction_style='endpoint')"
    - "AsyncPGIntegration() — auto-instruments app/db/session raw_session queries"
    - "LoggingIntegration(level=None, event_level=None) — drops log-as-event capture"
  patterns:
    - "Module-level _initialized guard + cheap process_role rebind on idempotent re-call"
    - "Lazy import of init_sentry inside the WORKER_STARTUP handler so the broker module remains importable without sentry side effects at HTTP-process import time"
    - "Sentry tags bound by existing layers (auth dep + request middleware) — this plan does NOT re-add tag plumbing"

key-files:
  created:
    - backend/app/obs/sentry.py
    - backend/tests/test_sentry.py
  modified:
    - backend/app/main.py
    - backend/app/queue/broker.py

decisions:
  - "Single Sentry project (NOT separate api/worker projects) — discriminated by process_role tag. Per RESEARCH § F10 Claude's-discretion recommendation. Cheaper free-tier quota usage; one mental model when triaging cross-process incidents (a scan upload's HTTP commit + its background indexing task share one project, one trace, one process_role filter)."
  - "send_default_pii=False AND sentry_sdk.set_user({'id': ...}) only (no email/name) — T-06-08c PII mitigation. Email/name lookups are a Clerk-side action, not a Sentry-event annotation."
  - "LoggingIntegration(level=None, event_level=None) — explicitly disable log-event capture. Structlog owns logs. Sentry owns exceptions and explicit capture_* calls. Avoids accidental PII bleeds from log strings."
  - "Lifespan placement of init_sentry — INSIDE the asynccontextmanager body, before yield. Idempotent guard means a worker that imports app.main for any reason (e.g. shared task code) will not double-init; the worker's own WORKER_STARTUP path takes over."
  - "Profiles sampled at 0.1 — pairs with traces. Plan can dial down without code change since both come from settings if we ever introduce per-env sample rates."

metrics:
  tasks-completed: 1
  tasks-total: 1
  files-created: 2
  files-modified: 2
  lines-added: 245
  duration: ~25min
  completed: 2026-04-27
requirements: [OBS-02]
---

# Phase 6 Plan 06-07: Sentry FastAPI + asyncpg + taskiq Integration Summary

Centralized Sentry SDK initialization through `init_sentry(role)` so the API and worker processes share one configuration (integrations, sample rates, PII flag) and a single Sentry project, discriminated only by the `process_role` tag.

## What Was Built

### Task 1 — init_sentry factory + lifespan/worker wiring + 5 SENTRY-* tests (commit `3ed67c0`)

**`backend/app/obs/sentry.py`** (new, 70 lines)
- `init_sentry(role: str = "api")` — idempotent module-level factory.
- Module-level `_initialized` flag guards against double-init across:
  - lifespan startup re-runs (TestClient reentry in tests)
  - worker process forks where the broker module is imported twice
- No-op branch flips the flag too, so a follow-up call with a DSN that arrives later still short-circuits (deterministic dev-local behavior).
- Integrations list: `StarletteIntegration(transaction_style="endpoint")`, `FastApiIntegration(transaction_style="endpoint")`, `AsyncPGIntegration()`, `LoggingIntegration(level=None, event_level=None)`.
- Sample rates: `traces_sample_rate=0.1`, `profiles_sample_rate=0.1`.
- Release/env: `release=settings.git_sha`, `environment=settings.env`.
- PII flag: `send_default_pii=False` (auth dep already calls `sentry_sdk.set_user({'id': principal.user_id})` so id-only context is preserved without leaking email/name).

**`backend/app/main.py`** (modified, +2 lines)
```python
from app.obs.sentry import init_sentry
...
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_sentry(role="api")
    yield
```

**`backend/app/queue/broker.py`** (modified, -14 / +5 lines)
- Replaced the inline `sentry_sdk.init(...)` block from 06-06 with a delegating call:
  ```python
  @broker.on_event(TaskiqEvents.WORKER_STARTUP)
  async def _init_worker_sentry(_state: object) -> None:
      from app.obs.sentry import init_sentry
      init_sentry(role="worker")
  ```
- The lazy import inside the handler keeps broker module-load free of Sentry side effects, which matters because route handlers do `from app.queue.broker import broker` to enqueue tasks at request time.

**`backend/tests/test_sentry.py`** (new, 158 lines)
- `test_init_sentry_noop_when_dsn_missing` — SENTRY-001 — `sentry_sdk.init` not called; flag still toggles True.
- `test_init_sentry_calls_sdk_init_with_integrations` — SENTRY-002 — asserts the four integration class names are present, plus traces_sample_rate=0.1, profiles_sample_rate=0.1, environment, release, send_default_pii=False, and `set_tag("process_role", "api")` was issued.
- `test_init_sentry_idempotent` — SENTRY-003 — second call does NOT re-run `sentry_sdk.init`; only updates the `process_role` tag (rebind cheap).
- `test_fastapi_lifespan_initializes_sentry` — SENTRY-004 — `TestClient(create_app())` triggers exactly one init with `environment=settings.env`.
- `test_sentry_tags_after_auth` — SENTRY-005 — end-to-end through `RequestContextMiddleware` + `require_principal`, the captured Sentry scope holds `user_id`, `clerk_org_id`, `request_id` (via `mock_clerk` fixture).
- Autouse fixture `_reset_sentry_init_flag` flips the module guard around each test so the SDK init mock can fire fresh.

## Sentry Init Contract (Locked)

```
                          init_sentry(role)
                          /              \
                         /                \
              role="api"                  role="worker"
                 |                            |
                 v                            v
          app.main lifespan         broker.WORKER_STARTUP
          (HTTP process)            (taskiq worker process)
                 |                            |
                 +--------- shared ----------+
                            |
                            v
                  sentry_sdk.init(...)
                    +--- integrations: FastApi, Starlette, AsyncPG, Logging
                    +--- traces_sample_rate=0.1, profiles_sample_rate=0.1
                    +--- send_default_pii=False
                    +--- release=git_sha, environment=env
                            |
                            v
                  sentry_sdk.set_tag("process_role", role)
```

Per-request enrichment continues to live in:
- `RequestContextMiddleware` (Plan 02) — binds `request_id` contextvar (mirrored to `set_tag("request_id", ...)` by `require_principal`).
- `require_principal` (Plan 04) — `set_user({"id": user_id})`, `set_tag("clerk_org_id", ...)`.
- `resolve_team_from_clerk_org` (Plan 04 follow-up) — `set_tag("team_id", ...)`.
- `SentryTaskMiddleware` (Plan 06-06) — `set_tag("task_name", ...)`, `set_tag("request_id", ...)` on the worker side, `capture_exception` on task failure.

This plan added NO per-request tagging — the Plan 04 / 06-06 layers already do it; 06-07 only adds the SDK init.

## Threat Mitigations Applied

| Threat ID | Mitigation | Evidence |
|-----------|-----------|----------|
| T-06-08c (PII in Sentry events) | `send_default_pii=False`; `set_user({"id": ...})` only (no email/name); `LoggingIntegration(event_level=None)` so log strings are NOT captured as events | `app/obs/sentry.py` lines 64–73; SENTRY-002 asserts kwargs and integration list |
| T-06-08d (request body / JWT / Stripe secret in Sentry transaction) | Accept (per plan threat register). `FastApiIntegration(transaction_style="endpoint")` excludes request body by default; combined with `send_default_pii=False` and the structlog `scrub_sensitive` processor (Plan 02) the multi-layer mitigation is sufficient | `app/obs/sentry.py` line 65 |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocker] `mock_clerk.jwks_client_for_settings()` does not exist on the conftest fixture**
- **Found during:** Task 1 — writing test_sentry.py
- **Issue:** The plan's SENTRY-005 sketch calls `mock_clerk.jwks_client_for_settings()` but the `ClerkFixture` dataclass (`tests/conftest.py` lines 297–338) only exposes `jwks_url`, `jwks_json`, `private_key_pem`, `public_key_pem`, `kid`, and `sign_jwt(...)`. The pre-existing `tests/test_auth.py` builds the `PyJWKClient` itself via a local `_jwks_client_for(jwks_url)` helper.
- **Fix:** In `test_sentry_tags_after_auth`, construct `PyJWKClient(mock_clerk.jwks_url, cache_keys=True, lifespan=3600)` inline and `monkeypatch.setattr("app.auth.clerk._jwks_client", ...)` — same pattern as `test_auth.py::patched_clerk`.
- **Files modified:** `backend/tests/test_sentry.py`
- **Commit:** `3ed67c0`

**2. [Rule 3 — Blocker] Strict-grep verification gate `grep -c "sentry_sdk.init" broker.py == 0` was tripped by a docstring**
- **Found during:** Task 1 verification — running plan's grep checks
- **Issue:** The consolidated WORKER_STARTUP handler's docstring referenced "the inline `sentry_sdk.init` call" as a history note. The literal `sentry_sdk.init` substring there counts toward `grep -c` and breaks the verification spec's intent.
- **Fix:** Reworded the docstring to "the inline initialization call" — same semantic, no literal grep collision. Mirrors the same pattern Plan 02 used for the `BaseHTTPMiddleware` strict-grep case.
- **Files modified:** `backend/app/queue/broker.py`
- **Commit:** `3ed67c0`

**3. [Rule 2 — Test integrity] Added autouse `_reset_sentry_init_flag` fixture**
- **Found during:** Task 1 — first run of the test file produced cross-test bleed where `test_init_sentry_calls_sdk_init_with_integrations` left `_initialized=True` and the lifespan test then short-circuited.
- **Issue:** `init_sentry` is intentionally idempotent at the process level; pytest tests are not "fresh processes" — they share module state.
- **Fix:** Autouse fixture flips `sentry_mod._initialized = False` before and after each test so each test starts and ends clean. This matches the plan's intent (the plan included a similar fixture in its test sketch lines 163–167; codifying it as autouse).
- **Files modified:** `backend/tests/test_sentry.py`
- **Commit:** `3ed67c0`

### Deferred Items (out of scope per scope-boundary rule)

- **Pre-existing mypy strict error in `app/queue/broker.py:49`** — `Argument "keep_results" to "RedisAsyncResultBackend" has incompatible type "int"; expected "bool"`. Inherited from Plan 06-06 (broker construction). Not introduced by this plan; verified by running `mypy --strict app/queue/broker.py` against `HEAD~1`. Logged here so 06-08 deploy work can address it (or pin a `# type: ignore[arg-type]` after consulting the taskiq-redis maintainers' actual contract for the parameter — the runtime accepts `int seconds`).
- **OTLP / Grafana Cloud tracing migration** — explicit deferred per CONTEXT D-20. Sentry Performance covers Phase 6 needs; revisit when we outgrow it (Phase 13).

## Verification Run

```
cd backend && .venv/bin/python -m pytest tests/test_sentry.py -q --no-cov
.....                                                                    [100%]
5 passed in 1.74s
```

Full backend regression suite (no testcontainers):
```
GSD_SKIP_TESTCONTAINERS=1 .venv/bin/python -m pytest -q --no-cov
30 passed, 17 skipped, 0 failures
```

Plan grep gates:
- `grep -c init_sentry backend/app/main.py` → 2 (≥ 1 required)
- `grep -c init_sentry backend/app/queue/broker.py` → 3 (≥ 1 required)
- `grep -c sentry_sdk.init backend/app/queue/broker.py` → 0 (== 0 required)

Ruff: `ruff check app/obs/sentry.py tests/test_sentry.py app/main.py app/queue/broker.py` — All checks passed!

## Self-Check: PASSED

- `backend/app/obs/sentry.py` — FOUND
- `backend/tests/test_sentry.py` — FOUND
- `backend/app/main.py` lifespan calls `init_sentry(role="api")` — CONFIRMED
- `backend/app/queue/broker.py` WORKER_STARTUP delegates to `init_sentry(role="worker")` — CONFIRMED
- Commit `3ed67c0` (`feat(06-07): centralize Sentry init for api + worker via init_sentry`) — FOUND in `git log`
- 5 SENTRY-* tests pass — CONFIRMED
- Full backend suite (excluding testcontainer-skipped) green — 30 passed / 17 skipped / 0 failures — CONFIRMED
- No `sentry_sdk.init` call site outside `app/obs/sentry.py` — CONFIRMED via grep

## Open Items (for post-merge gate / downstream plans)

- Plan 06-08 (deploy): set `SENTRY_DSN` Fly secret + propagate `GIT_SHA` env at release time so `init_sentry` engages in prod.
- Plan 06-08 (deploy): add `process_role` filter examples to the runbook (Sentry UI URL with `process_role:worker` query param) so on-call can split incidents quickly.
- Phase 13 revisit: evaluate Logfire / Grafana Cloud tracing migration once Sentry tracing usage profile is observable for ~3 months under live traffic.
