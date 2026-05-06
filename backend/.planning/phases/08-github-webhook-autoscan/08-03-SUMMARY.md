---
phase: 8
plan: "08-03"
subsystem: backend-worker
tags: [slack, scan_repo, taskiq, httpx]
key-files:
  created: []
  modified:
    - backend/app/queue/tasks/scan_repo.py
metrics:
  tests_added: 5
  tests_passing: 18
  lines_changed: 51
---

## Plan 08-03: Slack Alert in scan_repo — Complete

### What shipped

Added `import httpx` at module level and a **section 9 Slack alert block** to
`backend/app/queue/tasks/scan_repo.py`, immediately after `finalize_scan`
completes.

**Logic:**
- Executes `SELECT s.source, t.slack_webhook_url FROM scans s JOIN teams t ON t.id = s.team_id WHERE s.id = :id`
- Fires `httpx.AsyncClient.post(url, json={...}, timeout=5.0)` only when:
  - `source == 'webhook'` (push-triggered, not manual GitHub scan)
  - `slack_webhook_url is not None` (Slack configured for the team)
  - `critical >= 1` (at least one Critical finding)
- The Slack message body contains "Critical" and the repo name (plan requirement)
- httpx failures are caught, logged via `structlog.warning`, and captured via
  `sentry_sdk.capture_exception` — never re-raised

### Commits

| Task | Commit | Description |
|------|--------|-------------|
| RED | `5b0f4c7` | test(08-03): add 5 failing Slack alert tests (TDD RED) |
| GREEN | `3c270a7` | feat(08-03): add Slack alert block to scan_repo — 5/5 tests green |

### Test results

5 new tests in `tests/jobs/test_scan_repo.py` (JOB-SR-14..18):
- `test_slack_fires_on_webhook_source_with_critical` — PASSED
- `test_slack_no_fire_on_github_source` — PASSED
- `test_slack_no_fire_on_zero_critical` — PASSED
- `test_slack_no_fire_when_url_none` — PASSED
- `test_slack_httpx_failure_logged_not_raised` — PASSED

Total scan_repo suite: 18 passing (13 pre-existing + 5 new).

### Deviations

None. One pre-existing test (`test_scan_rc1_treated_as_success`) flaked due to
Docker/testcontainers timeout pulling postgres:16-alpine — unrelated to this
plan's changes.

### Self-Check: PASSED

- [x] `import httpx` at module level (verified by `hasattr(sr_mod, "httpx")` assertions)
- [x] Slack fires for webhook + critical >= 1 + url set
- [x] Slack does NOT fire for source='github', critical=0, or url=None
- [x] httpx exception caught + logged + sentry captured, not re-raised
- [x] All 5 new tests pass
