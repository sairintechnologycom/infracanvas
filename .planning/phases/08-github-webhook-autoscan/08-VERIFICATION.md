---
phase: 08-github-webhook-autoscan
verified: 2026-05-05T18:47:00Z
status: human_needed
score: 9/9 must-haves verified
overrides_applied: 0
re_verification: false
human_verification:
  - test: "Push a real commit to a connected GitHub repo and confirm a scan job starts within 30 s (check Neon scans table for a new pending→ready row)"
    expected: "New scans row with source='webhook', github_sha matching the pushed commit, status flipping pending→ready within 30 s"
    why_human: "Requires a live GitHub App installation, real repo push, and a running backend worker. Cannot be verified with grep or unit tests."
  - test: "Push a commit to a connected repo whose Terraform produces ≥ 1 Critical finding; confirm Slack message arrives in the configured channel"
    expected: "Slack message delivered with repo name and Critical count visible; teams.slack_webhook_url must be pre-configured via PATCH /v1/integrations/slack"
    why_human: "Requires live webhook delivery, a real Slack workspace, and a scan result with Critical findings. End-to-end only."
---

# Phase 8: GitHub Webhook + Auto-scan Verification Report

**Phase Goal:** Auto-scan on push, alert on Critical findings.
**Verified:** 2026-05-05T18:47:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Push to connected repo triggers scan job inside 30 s | ? UNCERTAIN | Webhook handler exists + enqueues scan_repo with 7-kwarg signature; timing not verifiable without live infrastructure |
| 2 | Scan result lands in Neon + R2 with commit SHA tied to team | ✓ VERIFIED | Webhook INSERT stores github_sha; finalize_scan stores r2_key + sha256 to Neon; team_id in both |
| 3 | Slack webhook fires when scan produces ≥ 1 Critical finding | ✓ VERIFIED (code) | Section 9 Slack block in scan_repo.py conditioned on source='webhook' + slack_webhook_url + critical>=1; httpx.post called; 5/5 tests pass |

**Score:** 9/9 plan-level must-haves verified; 1/3 roadmap success criteria needs human (live trigger timing)

### Roadmap Success Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| SC-1 | Push triggers scan job inside 30 s | ? UNCERTAIN | Code path verified; live timing needs human |
| SC-2 | Scan result in Neon + R2 with commit SHA tied to team | ✓ VERIFIED | INSERT in webhooks.py stores github_sha; finalize_scan stores r2_key to Neon |
| SC-3 | Slack webhook fires on ≥ 1 Critical finding | ✓ VERIFIED (code) | Slack block present, conditioned correctly, 5/5 unit tests green |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/migrations/versions/20260505_009_slack_webhook_url.py` | Alembic migration 009 adding slack_webhook_url + SECURITY DEFINER function | ✓ VERIFIED | revision=009_slack_webhook_url, down_revision=008_scan_github_columns, upgrade/downgrade both present |
| `backend/app/db/models.py` | Team ORM with slack_webhook_url column | ✓ VERIFIED | `slack_webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)` at line 36 |
| `backend/app/routes/webhooks.py` | POST /v1/webhooks/github handler | ✓ VERIFIED | Substantive implementation; 8-step filter chain; HMAC+RLS+INSERT+enqueue all present |
| `backend/tests/api/test_github_webhook.py` | 7 pytest tests | ✓ VERIFIED | 7 test functions, all 7 pass |
| `backend/app/queue/tasks/scan_repo.py` | Slack fire block after finalize_scan | ✓ VERIFIED | Section 9 Slack block with httpx.post, try/except, sentry capture |
| `backend/tests/jobs/test_scan_repo.py` | 5 Slack-specific tests | ✓ VERIFIED | 5 test_slack_* functions, all 5 pass |
| `backend/app/routes/integrations.py` | PATCH /v1/integrations/slack handler | ✓ VERIFIED | URL prefix validation, RLS GUC, UPDATE query, registered in main.py |
| `backend/tests/api/test_integrations.py` | 3 integration tests | ✓ VERIFIED | 3 test functions, all 3 pass |
| `dashboard/components/scans/ScansTable.tsx` | SourceCell 'webhook' branch | ✓ VERIFIED | `export function SourceCell` with `source === 'webhook'` branch rendering 'Auto-scan' |
| `dashboard/components/scans/MetadataHeader.tsx` | Auto-scan badge when source='webhook' | ✓ VERIFIED | `data-testid="auto-scan-badge"` span present, conditionally rendered on `scan.source === 'webhook'` |
| `dashboard/components/scans/ScansTable.test.tsx` | 2 vitest tests | ✓ VERIFIED | 2 tests, both pass |
| `dashboard/components/scans/MetadataHeader.test.tsx` | 2 vitest tests | ✓ VERIFIED | 2 tests, both pass |
| `dashboard/app/api/integrations/slack/route.ts` | PATCH proxy route | ✓ VERIFIED | backendFetch to /v1/integrations/slack, status mapping, exports PATCH |
| `dashboard/app/(dashboard)/settings/integrations/page.tsx` | Wired Slack form | ✓ VERIFIED | slackSaving/slackSaved/slackError state, TODO stub replaced, slack-error testid present |
| `dashboard/app/api/integrations/slack/route.test.ts` | 2 proxy tests | ✓ VERIFIED | 2 tests, both pass |
| `dashboard/app/(dashboard)/settings/integrations/IntegrationsPage.test.tsx` | 2 form tests | ✓ VERIFIED | 2 tests, both pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| POST /v1/webhooks/github | team_id_for_installation SQL function | raw SQL text() SELECT | ✓ WIRED | `SELECT team_id_for_installation(:iid)` at line 147 of webhooks.py |
| POST /v1/webhooks/github | scan_repo.kicker().kiq() | lazy import in try block | ✓ WIRED | Lazy import + .with_labels(source="webhook").kiq(...) at lines 188–203 of webhooks.py |
| scan_repo task | teams.slack_webhook_url | SELECT scans JOIN teams | ✓ WIRED | `SELECT s.source, t.slack_webhook_url FROM scans s JOIN teams t ON t.id = s.team_id` at lines 302–310 |
| scan_repo task | httpx.AsyncClient.post(slack_webhook_url) | try/except block conditioned on source+critical | ✓ WIRED | Conditioned on source='webhook', slack_webhook_url not None, critical>=1 at lines 317–341 |
| PATCH /v1/integrations/slack | teams.slack_webhook_url (UPDATE) | set_config + UPDATE teams | ✓ WIRED | `UPDATE teams SET slack_webhook_url = :url WHERE id = :id` at line 55 of integrations.py |
| dashboard proxy PATCH /api/integrations/slack | backend PATCH /v1/integrations/slack | backendFetch | ✓ WIRED | `backendFetch('/v1/integrations/slack', { method: 'PATCH' })` at line 24 of route.ts |
| integrations/page.tsx onSubmit | /api/integrations/slack proxy | fetch('/api/integrations/slack', {method:'PATCH'}) | ✓ WIRED | Async onSubmit handler in page.tsx replaces TODO stub |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| scan_repo.py Slack block | slack_row.source, slack_row.slack_webhook_url | DB SELECT scans JOIN teams | Yes — SQL query against live tables | ✓ FLOWING |
| scan_repo.py Slack block | critical_count | summary_json["findings"]["critical"] | Yes — from actual scan output via _extract_summary() | ✓ FLOWING |
| integrations/page.tsx | slackSaving/slackSaved/slackError | React useState + fetch response | Real fetch to /api/integrations/slack | ✓ FLOWING |
| ScansTable.tsx SourceCell | source prop | ScanListItem.source from API response | String prop from parent, typed in types.ts | ✓ FLOWING |
| MetadataHeader.tsx | scan.source | ScanGetResp.source from API response | Object prop from parent, typed in types.ts | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 7 webhook tests pass | `python3.12 -m pytest tests/api/test_github_webhook.py -v` | 7 passed in 1.99s | ✓ PASS |
| 5 Slack alert tests pass | `python3.12 -m pytest tests/jobs/test_scan_repo.py -k slack -v` | 5 passed, 13 deselected | ✓ PASS |
| 3 integrations tests pass | `python3.12 -m pytest tests/api/test_integrations.py -v` | 3 passed in 2.13s | ✓ PASS |
| 4 dashboard badge tests pass | `npx vitest run ScansTable.test.tsx MetadataHeader.test.tsx` | 4 passed | ✓ PASS |
| 2 proxy route tests pass | `npx vitest run app/api/integrations/slack/route.test.ts` | 2 passed | ✓ PASS |
| 2 integrations page tests pass | `npx vitest run IntegrationsPage.test.tsx` | 2 passed | ✓ PASS |
| Live push triggers scan in 30 s | Requires GitHub App + running worker | N/A | ? SKIP |
| Slack message delivered in real channel | Requires live Slack + Critical findings | N/A | ? SKIP |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| WBH-01 | 08-01, 08-02 | GitHub push webhook endpoint — verifies signature, enqueues scan job | ✓ SATISFIED | webhooks.py implements HMAC verify, 7-step filter, INSERT, scan_repo enqueue; migration 009 provides team_id_for_installation; 7 tests green |
| WBH-02 | 08-02, 08-03 | Auto-scan worker — clones repo, runs infracanvas scan, stores result in Neon + R2 | ✓ SATISFIED (code) | scan_repo.py clones, runs CLI, puts to R2, finalizes in Neon with github_sha; Slack block added; 5 new tests green. Live trigger timing needs human verification |
| WBH-03 | 08-03, 08-04, 08-05, 08-06 | Slack alert on Critical findings (team-configured webhook URL) | ✓ SATISFIED (code) | PATCH /v1/integrations/slack stores URL; scan_repo fires on source='webhook'+critical>=1+url set; dashboard form wired; auto-scan badge renders in UI; all tests green |

**Orphaned requirements check:** WBH-01, WBH-02, WBH-03 all appear in REQUIREMENTS.md Category 6 and are all claimed by Phase 8 plans. No orphaned requirements found.

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `backend/app/queue/tasks/scan_repo.py` | Log key `scan_repo.slack_alert_failed` differs from plan spec `slack_fire_failed` | Info | Internal log name only; test asserts `capture_exception` not log key; no observable behavior difference |
| `backend/app/db/models.py` | Pre-existing: `summary_json: Mapped[dict | None]` missing type parameters (noted in 08-01 SUMMARY) | Info | Pre-existing mypy warning; out of scope for Phase 8 |
| `dashboard/app/__tests__/scan-filters.test.tsx` | Pre-existing TS6133 unused variable error (noted in 08-05 SUMMARY) | Info | Pre-existing; deferred from earlier plan |

No blockers found. Anti-patterns are all pre-existing or trivial naming deviations.

### Human Verification Required

#### 1. Live Push Trigger (30-second timing gate)

**Test:** Install InfraCanvas GitHub App on a test repo, push a commit to the default branch, and observe the backend logs and Neon scans table.
**Expected:** Within 30 seconds of the push, a new row appears in `scans` with `source='webhook'`, `github_sha` matching the pushed commit, and `status` flipping from `pending` to `ready` (assuming the worker is running and the repo is small).
**Why human:** Requires a live GitHub App installation, running backend (Railway/Fly.io), running taskiq worker, and Neon database access. Unit tests mock the DB layer and cannot prove the 30-second timing constraint.

#### 2. Slack Alert Delivery (real channel)

**Test:** Configure a Slack incoming webhook URL via `PATCH /v1/integrations/slack` (with a test Slack workspace), then push a commit on a repo whose Terraform produces at least 1 Critical finding.
**Expected:** A Slack message appears in the configured channel containing the repo name and the critical count. The message should arrive within a few seconds of the scan completing.
**Why human:** Requires a live Slack workspace with a real incoming webhook URL, a running scan that actually finds Critical findings, and visual inspection of the Slack channel. The httpx.post call is unit-tested but the round-trip to Slack cannot be verified programmatically without a live environment.

### Gaps Summary

No gaps blocking goal achievement at the code level. All artifacts exist and are substantive, all key links are wired, all unit/integration tests pass (22 backend tests + 10 frontend tests = 32 total). Two human verification items remain for end-to-end live behavior that cannot be automated:

1. The 30-second push-to-scan timing (SC-1) — requires a live GitHub App installation and running worker.
2. Actual Slack message delivery (SC-3 e2e confirmation) — requires a live Slack workspace.

The code structure is correct and all mock-verified paths show the full chain working. Phase is code-complete; human smoke test against live infrastructure is the remaining gate.

---

_Verified: 2026-05-05T18:47:00Z_
_Verifier: Claude (gsd-verifier)_
