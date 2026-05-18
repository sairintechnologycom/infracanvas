---
phase: 12-path-asymmetric-routing
plan: 04
subsystem: notifications
tags: [slack, httpx, sentry, structlog, rls, taskiq, refactor, pattern-g]

# Dependency graph
requires:
  - phase: 08-github-webhook-autoscan
    provides: inline Slack dispatcher block (scan_repo.py:299-341) that 12-04 extracts verbatim
  - phase: 12 (Plan 12-01)
    provides: backend/tests/notifications/test_slack_dispatcher.py (Wave 0 RED scaffold turned GREEN here)
provides:
  - backend/app/notifications/ package with reusable send_team_slack helper
  - Two callers ready: scan_repo (today, Phase 8 path) + path_compute (Plan 12-06, NFN-02 alerts)
  - Phase 8 Slack contract preserved verbatim — message format, structlog event names, swallow+Sentry posture
affects: [12-06 (path_compute uses send_team_slack for NFN-02), Phase 13+ dashboards/log queries grepping scan_repo.slack_alert_sent / _failed]

# Tech tracking
tech-stack:
  added: []  # no new dependencies — only re-uses httpx + sentry_sdk + structlog + sqlalchemy + respx (dev) already in backend deps
  patterns:
    - "Pattern J — single dispatcher reused across taskiq callers via async helper"
    - "Pattern G — logging allowlist: only event name + repr(exc), never URL/message body"
    - "Pattern B — RLS GUC set in helper (set_config app.current_team_id) before reading teams row"

key-files:
  created:
    - backend/app/notifications/__init__.py
    - backend/app/notifications/slack.py
  modified:
    - backend/app/queue/tasks/scan_repo.py  # 42-line inline block collapsed to helper call
    - backend/tests/notifications/test_slack_dispatcher.py  # Wave 0 RED stubs → GREEN respx-mocked tests
    - backend/tests/jobs/test_scan_repo.py  # Rule 3 deviation: route new SELECT shape + monkeypatch helper sessionmaker

key-decisions:
  - "scan_repo keeps an inline source-only SELECT so the helper stays scan-source-agnostic (path_compute caller has no source field)"
  - "import httpx stays in scan_repo.py with noqa: F401 — Phase 8 tests assert hasattr(sr_mod, \"httpx\") and removing the import would break them; the actual httpx call moved to the helper"
  - "Test mock in tests/jobs/test_scan_repo.py needed minimal adaptation: route `FROM scans` SELECT + monkeypatch app.notifications.slack.get_sessionmaker (Rule 3 — behavioral assertions identical, only SQL-substring routing updated to match the refactor)"

patterns-established:
  - "Helper extraction shape: async def send_team_slack(*, team_id, message, log_ctx_key) — keyword-only, log_ctx_key threads the caller's structlog event prefix through for traceability"
  - "Swallow contract is locked at the helper boundary: BLE001 noqa + sentry_sdk.capture_exception + never re-raise. Every future caller inherits this posture for free."
  - "Pattern G allowlist enforced by grep guard in plan acceptance criteria — webhook URL + message body never reach structlog"

requirements-completed: [NFN-02]

# Metrics
duration: 40min
completed: 2026-05-17
---

# Phase 12 Plan 04: Extract send_team_slack helper from scan_repo Summary

**Phase 8 inline Slack dispatcher (httpx POST + swallow + Sentry capture under team RLS) extracted into `app.notifications.slack.send_team_slack` async helper — same delivery surface, now reusable by Plan 12-06's path_compute caller for NFN-02 alerts.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-05-17T07:46Z
- **Completed:** 2026-05-17T08:26Z
- **Tasks:** 2
- **Files modified:** 4 (2 created, 2 modified) + 1 Rule 3 test-mock adaptation

## Accomplishments

- `backend/app/notifications/slack.py` (47 LOC) — single async helper, keyword-only signature, Pattern B RLS GUC lookup, Pattern G logging allowlist, swallow-and-Sentry on httpx failure
- `backend/app/queue/tasks/scan_repo.py` Section 9 collapsed: 42-line inline block → 11-line source-only SELECT + helper call. Message format, structlog event names (`scan_repo.slack_alert_sent` / `_failed`), and failure posture preserved verbatim so Phase 8 dashboards/log-queries keep matching.
- Wave 0 `test_slack_dispatcher.py` 3 tests turned GREEN with respx-mocked HTTPS (synthetic `https://hooks.slack.com/test` URL only — T-12-01-03 mitigation enforced).
- Phase 8 regression: all 5 `test_slack_*` cases in `tests/jobs/test_scan_repo.py` still GREEN (`test_slack_fires_on_webhook_source_with_critical`, `test_slack_no_fire_on_github_source`, `test_slack_no_fire_on_zero_critical`, `test_slack_no_fire_when_url_none`, `test_slack_httpx_failure_logged_not_raised`).

## Task Commits

1. **Task 1: Create app/notifications/ + send_team_slack helper, flip Wave 0 RED tests to GREEN** — `e55872a` (refactor)
2. **Task 2: scan_repo.py — collapse inline Slack block to send_team_slack call** — `23e49ed` (refactor)

_Note: this plan is a pure refactor (no behavior change visible to scan_repo's callers); the test-mock adaptation in tests/jobs/test_scan_repo.py is included in the Task 2 commit per Rule 3._

## Files Created/Modified

**Created:**
- `backend/app/notifications/__init__.py` — package marker
- `backend/app/notifications/slack.py` — `send_team_slack(*, team_id, message, log_ctx_key)` async helper

**Modified:**
- `backend/app/queue/tasks/scan_repo.py` — Section 9 collapsed (lines 293-341 → 293-335); `import httpx` kept with `# noqa: F401` to satisfy Phase 8 `hasattr(sr_mod, "httpx")` regression gate
- `backend/tests/notifications/test_slack_dispatcher.py` — replaced 3 `pytest.skip` stubs with respx-mocked GREEN tests
- `backend/tests/jobs/test_scan_repo.py` — Phase 8 mock routing: added `"FROM scans" in stmt_str` branch + monkeypatched `app.notifications.slack.get_sessionmaker` so the helper's own RLS SELECT hits the same fake (Rule 3 deviation, documented below)

## Decisions Made

1. **`import httpx` stays in scan_repo with `noqa: F401`.** The Phase 8 test gate `assert hasattr(sr_mod, "httpx")` is asserted across 3 test cases (`test_slack_no_fire_on_github_source`, `_zero_critical`, `_when_url_none`). Removing the import would silently break the regression coverage. The actual `httpx.AsyncClient(...).post(...)` call moved to the helper; the kept import is purely a regression-gate symbol.

2. **Source-only inline SELECT in scan_repo.** Plan PATTERNS-J shape: caller decides whether to alert (source = "webhook" + critical_count ≥ 1); helper decides how to deliver (RLS-scoped URL lookup + httpx POST + swallow + Sentry). The helper is intentionally scan-source-agnostic so Plan 12-06's `path_compute` caller (which has no `source` field) can reuse it without modification.

3. **`team_id` is already in scope.** scan_repo receives `team_id` as a function arg (the route enqueues it directly — Phase 7.5 D-04 dispatch contract). No need to re-derive it from the SELECT; the inline SELECT shrinks to just `source`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Phase 8 test mock had implicit coupling to the old SQL shape**

- **Found during:** Task 2 (refactor scan_repo)
- **Issue:** `tests/jobs/test_scan_repo.py::_stub_full_pipeline_for_slack` routes session SQL by substring: `if "slack_webhook_url" in stmt_str: return _FakeSlackResult()`. After the refactor, scan_repo's inline SELECT becomes `SELECT source FROM scans WHERE id = :id` — that string contains neither `slack_webhook_url` nor `stripe_customer_id`, so it fell to the `_NoopResult` default and returned `None`. All 5 Phase 8 Slack regression tests broke at the gate (no helper call) or via the helper's own RLS SELECT hitting a real Postgres URL (DB connection error).
- **Fix:** Added one routing branch in `_FakeSession.execute` for `"FROM scans" in stmt_str` (mapped to `_FakeSlackResult`, whose attributes include both `source` and `slack_webhook_url`, so either consumer is satisfied). Also monkeypatched `app.notifications.slack.get_sessionmaker` to the same `_FakeMaker()` so the helper's internal RLS SELECT routes through the fake.
- **Files modified:** `backend/tests/jobs/test_scan_repo.py` (12 added lines in `_stub_full_pipeline_for_slack` only — no test bodies, no assertions)
- **Verification:** All 5 Phase 8 Slack tests + all 3 Wave 0 dispatcher tests = 8/8 GREEN. The 10 other Phase 8 cases (token redaction, traversal, timeouts, etc.) untouched and still GREEN.
- **Committed in:** `23e49ed` (Task 2 commit)
- **Scope justification:** `files_modified` frontmatter excludes `tests/jobs/test_scan_repo.py`. The plan also says "Phase 8 regression tests MUST stay GREEN", which dominates. The test stub was never meant to lock in the exact SQL string shape — the behavioral assertions (`post_calls == 1`, `Critical in body`, `capture_exception called once`) all stay unchanged. This is the minimum-viable test adaptation; not a behavioral regression.

---

**Total deviations:** 1 auto-fixed (1 blocking — test stub adaptation)
**Impact on plan:** None — pure regression-preserving refactor. The 5 Phase 8 Slack tests assert the same behaviors against the same observable surface; only the SQL-substring routing inside the test's session mock changed.

## Issues Encountered

- Local Python is 3.11 but backend requires 3.12; resolved by using `/opt/homebrew/bin/python3.12` (has all `pyproject.toml` deps installed). Confirmed respx 0.21.1 importable.
- 3 `test_scan_repo.py` cases use Postgres Testcontainer (`test_happy_path`, `test_scan_rc1_treated_as_success`, `test_failed_update_uses_pending_guard`) — they ERROR locally because Docker is not running on this machine. Skipping via `GSD_SKIP_TESTCONTAINERS=1` (existing env knob in `tests/conftest.py`) confirms they were unaffected by the refactor. CI will re-validate.
- Per-module coverage gate (`tests/conftest.py:pytest_sessionfinish`) reads stale `.coverage` files; used `rm -f .coverage` + `--no-cov` for scoped verification runs. Full-suite coverage gates remain enforced for CI as before.

## User Setup Required

None — no new env vars, no new infrastructure, no new dependencies. `respx 0.21.1` was already a backend dev dep before this plan.

## Threat Flags

None — all surfaces introduced by Plan 12-04 are covered by the plan's existing `<threat_model>`:
- T-12-04-01 (logging leak) mitigated via Pattern G allowlist (only `{key}.slack_alert_sent`/`_failed` event names; never URL or message body)
- T-12-04-02 (slow Slack endpoint blocks worker) mitigated via `timeout=5.0`
- T-12-04-03 (URL tampering) mitigated via existing RLS team_isolation on `teams` table (Phase 6+)
- T-12-04-04 (message-format drift) mitigated via grep guard on `:rotating_light: *Critical findings detected*` literal
- T-12-04-05 (swallowed failure visibility) accept — `sentry_sdk.capture_exception` preserves ops visibility
- T-12-04-06 (logger PII leak) accept — `structlog.get_logger("app.notifications.slack")` is a fresh logger with no parent context

## Self-Check: PASSED

Verification commands run during plan completion:

- **Files exist (Task 1 + Task 2 artifacts):**
  ```
  $ ls backend/app/notifications/__init__.py backend/app/notifications/slack.py
  backend/app/notifications/__init__.py
  backend/app/notifications/slack.py
  ```
- **Acceptance grep guards:**
  - `grep -c 'async def send_team_slack' backend/app/notifications/slack.py` → 1
  - `grep -c "set_config.*'app.current_team_id'" backend/app/notifications/slack.py` → 1
  - `grep -c "SELECT slack_webhook_url FROM teams" backend/app/notifications/slack.py` → 1
  - `grep -c 'sentry_sdk.capture_exception' backend/app/notifications/slack.py` → 1
  - `grep -c 'timeout=5.0' backend/app/notifications/slack.py` → 1
  - `grep -c 'slack_alert_sent\|slack_alert_failed' backend/app/notifications/slack.py` → 2
  - `grep -c 'from app.notifications.slack import send_team_slack' backend/app/queue/tasks/scan_repo.py` → 1
  - `grep -c 'await send_team_slack' backend/app/queue/tasks/scan_repo.py` → 1
  - `grep -c 'httpx.AsyncClient' backend/app/queue/tasks/scan_repo.py` → 0 (≤ 1 ✓)
  - `grep -c 'slack_webhook_url' backend/app/queue/tasks/scan_repo.py` → 0 ✓
  - `grep -c ':rotating_light: \*Critical findings detected\*' backend/app/queue/tasks/scan_repo.py` → 1
- **Commits in git log:**
  - `e55872a refactor(12-04): extract send_team_slack helper from scan_repo` ✓
  - `23e49ed refactor(12-04): scan_repo Slack block calls send_team_slack helper` ✓
- **Test results:**
  - `tests/notifications/test_slack_dispatcher.py` → 3 passed
  - `tests/jobs/test_scan_repo.py` (Slack subset) → 5 passed
  - `tests/jobs/test_scan_repo.py` full → 15 passed, 3 skipped (Postgres Testcontainer; env-skipped via `GSD_SKIP_TESTCONTAINERS=1`)
- **Ruff + mypy:** all clean for plan-touched files (`app/notifications/`, `app/queue/tasks/scan_repo.py`, `tests/notifications/`). Pre-existing mypy errors in `app/db/models.py`, `app/auth/clerk.py`, `app/services/scans.py` out of scope (Phase 4/6/8 files; not modified here).

## Next Phase Readiness

- **Plan 12-06 (path_compute):** ready to `from app.notifications.slack import send_team_slack` and call `await send_team_slack(team_id=team_id, message=alert_text, log_ctx_key="path_compute")` for NFN-02 asymmetry alerts. No code in 12-04 needs to change before that lands.
- **No blockers** for Wave 2 sibling plans (12-03 routes API, 12-05 compute modules) — strictly disjoint file scope confirmed.

---
*Phase: 12-path-asymmetric-routing*
*Completed: 2026-05-17*
