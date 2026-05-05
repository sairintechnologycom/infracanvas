---
phase: 08-github-webhook-autoscan
plan: "08-02"
subsystem: api
tags: [webhook, hmac, github, fastapi, pytest, tdd]

# Dependency graph
requires:
  - phase: 07.5-github-repo-connector
    provides: scan_repo 7-kwarg taskiq job contract, get_sessionmaker pattern, RLS GUC set_config pattern

provides:
  - "POST /v1/webhooks/github — GitHub push webhook handler with HMAC-SHA256 verify"
  - "7 pytest tests covering all 7 decision branches (HMAC fail, empty secret, ping, non-push, deleted-branch, non-default-branch, happy path)"
  - "Threat mitigations T-8-02-01 through T-8-02-08 all implemented"

affects:
  - 08-03  # Slack integration in scan_repo uses source='webhook' value
  - 08-04  # Dashboard badge uses source='webhook' value
  - phase-verifier

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Raw-bytes discipline: await request.body() BEFORE any json.loads() or HMAC in webhook handlers"
    - "Empty-secret guard: return HTTP 500 before HMAC computation when github_app_webhook_secret is empty"
    - "Constant-time HMAC comparison: hmac.compare_digest (never == string compare)"
    - "Event filter order: empty-secret guard → HMAC → ping → non-push → json.loads → deleted → non-default → DB"
    - "SECURITY DEFINER team resolution: team_id_for_installation(bigint) resolves team without RLS bootstrapping problem"
    - "test_client fixture naming: use webhook_client not test_client to avoid grep-c count inflation"

key-files:
  created:
    - backend/tests/api/test_github_webhook.py
  modified:
    - backend/app/routes/webhooks.py

key-decisions:
  - "Lazy import for scan_repo (from app.queue.tasks.scan_repo import scan_repo inside try block) — same pattern as scans_from_github.py, allows the module to compile before the taskiq task file exists and enables sys.modules patching in tests"
  - "settings imported at module top-level (not lazy inside function) — consistent with all other route modules; monkeypatching the singleton works regardless"
  - "webhook_client fixture name (not test_client) — avoids grep -c 'def test_' counting the fixture as a test function, keeping the count at exactly 7"
  - "hmac.compare_digest appears twice in webhooks.py (once in docstring threat model, once in code) — count of 2 is intentional; docstring documents T-8-02-02 explicitly"

patterns-established:
  - "GitHub webhook tests are pure unit tests (no Postgres testcontainer) — DB layer mocked via get_sessionmaker patch + sys.modules scan_repo stub"
  - "Empty-secret 500 guard runs BEFORE hmac.new() — prevents hmac.new(b'', ...) from accepting any payload when secret is unconfigured"
  - "Non-push events filtered BEFORE json.loads() — prevents KeyError crashes from push-specific keys absent on installation/check_run payloads"

requirements-completed:
  - WBH-01
  - WBH-02

# Metrics
duration: 8min
completed: 2026-05-05
---

# Phase 8 Plan 02: GitHub Webhook Handler Summary

**POST /v1/webhooks/github with HMAC-SHA256 verify, 8-step event filter chain, RLS-scoped INSERT, and scan_repo enqueue — all 7 TDD tests green**

## Performance

- **Duration:** 8 min
- **Started:** 2026-05-05T06:41:14Z
- **Completed:** 2026-05-05T06:49:30Z
- **Tasks:** 2 (TDD RED + TDD GREEN)
- **Files modified:** 2

## Accomplishments

- Wrote 7 failing pytest tests covering all decision branches of the webhook handler (RED phase)
- Implemented `POST /v1/webhooks/github` in `backend/app/routes/webhooks.py` — all 7 tests pass (GREEN phase)
- Implemented all 8 threat mitigations from the plan's threat model (T-8-02-01 through T-8-02-08)
- Lazy import of `scan_repo` matches the established `scans_from_github.py` pattern, enabling clean sys.modules patching in tests

## Task Commits

Each task was committed atomically:

1. **Task 1: TDD RED — 7 failing tests** - `1e85616` (test)
2. **Task 2: TDD GREEN — implementation + fixture rename** - `d4b1f75` (feat)

## Files Created/Modified

- `backend/tests/api/test_github_webhook.py` — 7 pytest tests for webhook handler: `_sign` HMAC helper, `webhook_client` fixture, `_push_payload` builder, tests for invalid HMAC (401), unconfigured secret (500), ping (200), non-push (200), deleted-branch (200), non-default-branch (200), happy-path (200 + INSERT + kiq)
- `backend/app/routes/webhooks.py` — Added `POST /github` handler to existing router: raw-bytes read, empty-secret 500 guard, HMAC-SHA256 `hmac.compare_digest`, ping/non-push/deleted/non-default filters, `team_id_for_installation()` SQL lookup, RLS GUC `set_config`, INSERT scans `source='webhook'`, lazy `scan_repo` enqueue with enqueue-failure failsafe

## Decisions Made

- **Lazy scan_repo import inside try block** (same pattern as `scans_from_github.py`): allows the module to compile when the taskiq worker file doesn't exist yet; tests inject via `sys.modules` before the import fires.
- **settings at module top level** (not lazy inside function): consistent with all other route modules; `monkeypatch.setattr(settings, "github_app_webhook_secret", ...)` on the singleton propagates regardless of import location.
- **webhook_client fixture name**: The acceptance criteria checks `grep -c "def test_"` which would count `test_client` as a test function (count = 8 instead of 7). Renamed to `webhook_client` to keep count at exactly 7.
- **hmac.compare_digest appears in docstring + code**: Count of 2 is correct — the docstring documents T-8-02-02 explicitly (deliberate documentation); the code uses it at line 97.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed fakeredis dependency**
- **Found during:** Task 1 (running RED tests)
- **Issue:** `tests/api/conftest.py` imports `fakeredis.aioredis` but `fakeredis` was not installed in the Python 3.12 environment
- **Fix:** `python3.12 -m pip install fakeredis --break-system-packages`; then installed full `[dev]` extras to get all test deps
- **Files modified:** None (environment dependency only)
- **Verification:** `python3.12 -m pytest tests/api/test_github_webhook.py --collect-only` collected 7 tests without errors
- **Committed in:** No file change needed; environment fix only

**2. [Rule 1 - Bug] Renamed test_client fixture to webhook_client**
- **Found during:** Task 2 (post-GREEN acceptance criteria check)
- **Issue:** `grep -c "def test_"` returned 8 (not 7) because the fixture named `test_client` matched the grep pattern
- **Fix:** Renamed fixture from `test_client` → `webhook_client` and updated all 7 usage sites in test bodies
- **Files modified:** `backend/tests/api/test_github_webhook.py`
- **Verification:** `grep -c "def test_" tests/api/test_github_webhook.py` now returns 7; all 7 tests still pass
- **Committed in:** d4b1f75 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 Rule 3 blocking dependency, 1 Rule 1 bug fix)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered

- Python 3.11.1 (system Python) failed `pip install -e ".[dev]"` due to `>=3.12` constraint in `pyproject.toml`. Resolved by switching to `python3.12` (available at `/opt/homebrew/bin/python3.12`) for all pytest invocations.

## Known Stubs

None — the webhook handler is fully implemented with no placeholders.

## Threat Flags

The new `POST /v1/webhooks/github` endpoint creates a new network surface. All threats are covered by the plan's threat model (T-8-02-01 through T-8-02-08) and are mitigated in the implementation. No additional unplanned surface.

## Next Phase Readiness

- `POST /v1/webhooks/github` is live and registered in `main.py` via the existing `wh_routes.router`
- `source='webhook'` value written to `scans.source` — Plan 08-03 (Slack alert) reads this column to decide whether to fire
- Plan 08-01 (migration 009) must also be in HEAD for `team_id_for_installation()` SECURITY DEFINER function to exist at runtime; Wave 1 wave-merge handles this

## Self-Check: PASSED

| Item | Status |
|------|--------|
| backend/tests/api/test_github_webhook.py | FOUND |
| backend/app/routes/webhooks.py | FOUND |
| 08-02-SUMMARY.md | FOUND |
| Commit 1e85616 (TDD RED) | FOUND |
| Commit d4b1f75 (TDD GREEN) | FOUND |
| 7 tests pass | CONFIRMED |

---
*Phase: 08-github-webhook-autoscan*
*Completed: 2026-05-05*
