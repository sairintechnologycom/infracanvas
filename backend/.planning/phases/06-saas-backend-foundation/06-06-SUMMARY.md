---
phase: 06-saas-backend-foundation
plan: 06
subsystem: queue
tags: [taskiq, redis, background-jobs, indexing, request-id, dlq, sentry]

# Dependency graph
requires:
  - phase: 06-saas-backend-foundation
    provides: |
      Plan 06-01 — backend/pyproject.toml (taskiq + taskiq-redis deps); tests/conftest.py with in_memory_broker fixture.
      Plan 06-02 — app/obs/middleware.py request_id contextvar pattern.
      Plan 06-03 — app/db/session.py raw_session, app/db/models.py Scan + ScanStatus, set_config('app.current_team_id', ...) helper.
      Plan 06-05 — app/storage/r2.py download helpers, app/schemas/scan.py validate_resource_graph, app/routes/scans.py lazy enqueue placeholder.
provides:
  - "taskiq RedisStreamBroker via app/queue/broker.py — single broker singleton"
  - "RequestIdMiddleware (taskiq) — propagates request_id label from kicker into worker structlog contextvar"
  - "DLQ middleware — emits dlq.message_dropped log on retry-exhausted exceptions"
  - "Sentry middleware hook (placeholder; Plan 06-07 finalizes the SDK init)"
  - "enqueue_scan_indexing(scan_id) task — post-commit summary denormalization"
  - "scan_team_id(uuid) SECURITY DEFINER helper — worker team_id lookup without Clerk principal"
  - "Migration 004 — scan_team_id() function granted to infracanvas_app"
affects: [06-07 sentry instruments worker process, 06-08 deploy adds worker process block + Redis URL]

# Tech tracking
tech-stack:
  added:
    - "taskiq RedisStreamBroker (transport)"
    - "taskiq middleware pipeline (request_id, DLQ, Sentry)"
    - "Postgres SECURITY DEFINER function for worker team scoping"
  patterns:
    - "Lazy import of task module inside route handler so /v1/scans is importable when broker is unavailable"
    - "kicker().with_labels(request_id=rid).kiq(...) — labels survive Redis hop and are read by RequestIdMiddleware on worker side"
    - "Worker DB context: scan_team_id() lookup → set_config GUC → raw_session — no BYPASSRLS role needed"

key-files:
  created:
    - backend/app/queue/__init__.py
    - backend/app/queue/broker.py
    - backend/app/queue/middleware.py
    - backend/app/queue/tasks/__init__.py
    - backend/app/queue/tasks/indexing.py
    - backend/migrations/versions/20260424_004_scan_team_id_helper.py
    - backend/tests/test_tasks.py
  modified: []

# Plan execution
tasks_completed: 2
commits:
  - hash: 0064c85
    message: "feat(06-06): taskiq broker + request_id/DLQ/Sentry middlewares"
  - hash: HEAD
    message: "feat(06-06): scan indexing task + scan_team_id helper migration + tests"

# Verification
tests:
  test_tasks_passing: 3
  test_tasks_skipped: 1
  full_suite_passing: 25
  full_suite_skipped: 17
  full_suite_failures: 0
  notes: |
    `pytest tests/test_tasks.py -q --no-cov` → 3 passed, 1 skipped.
    Full backend suite (`GSD_SKIP_TESTCONTAINERS=1 pytest -q --no-cov`) →
    25 passed, 17 skipped, 0 failures.
    Skipped tests are Postgres testcontainer-dependent (test_rls,
    test_migrations) plus one DB-bound test_tasks case — same skip pattern
    documented in 06-05 Deferred Items.

# Notes
notes: |
  - The 06-06 executor agent was killed by the user mid-run after
    completing the 1st atomic commit (broker + middlewares) and writing
    the indexing task + migration + tests. The orchestrator finished the
    plan inline: ran the test suite, confirmed no regressions, committed
    the remaining files, and wrote this SUMMARY.
  - Recovery commit message preserves attribution to plan 06-06 work.
  - Wave 2 (06-04, 06-05, 06-06) is now complete. Wave 3 (06-07 Sentry,
    06-08 deploy) can proceed.

# Deferred Items
deferred:
  - "Postgres testcontainer-dependent tests (test_rls, test_migrations) remain skipped under GSD_SKIP_TESTCONTAINERS=1 — same as 06-05 deferred."
  - "Sentry middleware in app/queue/middleware.py is a structural placeholder; Plan 06-07 finalizes sentry-sdk init for the worker process."
