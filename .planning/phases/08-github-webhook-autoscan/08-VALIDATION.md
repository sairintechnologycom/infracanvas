---
phase: 8
slug: 08-github-webhook-autoscan
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-05
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (backend)** | pytest + httpx + respx + fakeredis |
| **Framework (dashboard)** | vitest + @testing-library/react |
| **Backend config** | `backend/pyproject.toml` |
| **Dashboard config** | `dashboard/vitest.config.ts` |
| **Backend quick run** | `cd backend && pytest tests/ -x -q --ignore=tests/integrations` |
| **Dashboard quick run** | `cd dashboard && npx vitest run --reporter=dot` |
| **Backend full suite** | `cd backend && pytest tests/ -q` |
| **Dashboard full suite** | `cd dashboard && npx vitest run` |
| **Estimated runtime** | ~45s backend, ~30s dashboard |

---

## Sampling Rate

- **After every task commit:** Run backend quick run + dashboard quick run
- **After every plan wave:** Run full backend + dashboard suite
- **Before `/gsd-verify-work`:** Both full suites must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 8-01-01 | 01 | 1 | WBH-01 | T-8-01 | HMAC-invalid → 403 (timing-safe compare_digest) | unit | `pytest tests/api/test_github_webhook.py -x -q` | ❌ W0 | ⬜ pending |
| 8-01-02 | 01 | 1 | WBH-01 | — | Ping event → 200 OK, no scan row inserted | unit | `pytest tests/api/test_github_webhook.py -x -q` | ❌ W0 | ⬜ pending |
| 8-01-03 | 01 | 1 | WBH-01 | — | Deleted-branch push → 200 OK, no scan row | unit | `pytest tests/api/test_github_webhook.py -x -q` | ❌ W0 | ⬜ pending |
| 8-01-04 | 01 | 1 | WBH-01 | — | Non-default branch → 200 OK, no scan row | unit | `pytest tests/api/test_github_webhook.py -x -q` | ❌ W0 | ⬜ pending |
| 8-01-05 | 01 | 1 | WBH-01 | — | Happy path → scans row source='webhook', job enqueued with 7 kwargs | unit | `pytest tests/api/test_github_webhook.py -x -q` | ❌ W0 | ⬜ pending |
| 8-02-01 | 02 | 1 | WBH-02 | T-8-02 | migration 009 upgrade/downgrade reversible; slack_webhook_url NULL default | integration | `pytest tests/integrations/ -k "migration_009" -x -q` | ❌ W0 | ⬜ pending |
| 8-02-02 | 02 | 1 | WBH-03 | — | ScanSource.webhook value present in Python enum; Scan.source='webhook' accepted | unit | `pytest tests/ -k "scan_source" -x -q` | ❌ W0 | ⬜ pending |
| 8-03-01 | 03 | 2 | WBH-03 | — | source='webhook' + ≥1 Critical → Slack POST fired with repo/branch/sha/count/link | unit | `pytest tests/jobs/test_scan_repo.py -x -q` | ✅ | ⬜ pending |
| 8-03-02 | 03 | 2 | WBH-03 | — | source='github' + Critical → NO Slack fire | unit | `pytest tests/jobs/test_scan_repo.py -x -q` | ✅ | ⬜ pending |
| 8-03-03 | 03 | 2 | WBH-03 | — | source='webhook' + 0 Critical → NO Slack fire | unit | `pytest tests/jobs/test_scan_repo.py -x -q` | ✅ | ⬜ pending |
| 8-03-04 | 03 | 2 | WBH-03 | T-8-03 | slack_webhook_url NULL → no fire; scan still succeeds | unit | `pytest tests/jobs/test_scan_repo.py -x -q` | ✅ | ⬜ pending |
| 8-03-05 | 03 | 2 | WBH-03 | T-8-03 | httpx Slack POST failure → logged, scan NOT failed (resilience) | unit | `pytest tests/jobs/test_scan_repo.py -x -q` | ✅ | ⬜ pending |
| 8-04-01 | 04 | 2 | WBH-03 | T-8-04 | valid hooks.slack.com URL saved; PATCH returns 200 | unit | `pytest tests/api/test_integrations_slack.py -x -q` | ❌ W0 | ⬜ pending |
| 8-04-02 | 04 | 2 | WBH-03 | T-8-04 | non-hooks.slack.com URL → 422 (SSRF guard) | unit | `pytest tests/api/test_integrations_slack.py -x -q` | ❌ W0 | ⬜ pending |
| 8-04-03 | 04 | 2 | WBH-03 | — | missing webhook_url body → 422 | unit | `pytest tests/api/test_integrations_slack.py -x -q` | ❌ W0 | ⬜ pending |
| 8-05-01 | 05 | 3 | WBH-03 | — | source='webhook' renders 'Auto-scan' badge in ScansTable | unit | `cd dashboard && npx vitest run --reporter=dot -t "auto-scan"` | ❌ W0 | ⬜ pending |
| 8-05-02 | 05 | 3 | WBH-03 | — | source='github' renders 'Manual' badge (no regression) | unit | `cd dashboard && npx vitest run --reporter=dot -t "source badge"` | ✅ | ⬜ pending |
| 8-05-03 | 05 | 3 | WBH-03 | — | MetadataHeader shows Auto-scan badge + branch + sha for source='webhook' | unit | `cd dashboard && npx vitest run --reporter=dot -t "metadata"` | ✅ | ⬜ pending |
| 8-06-01 | 06 | 3 | WBH-03 | — | Slack form submit calls PATCH /api/integrations/slack with webhook_url | unit | `cd dashboard && npx vitest run --reporter=dot -t "slack"` | ❌ W0 | ⬜ pending |
| 8-06-02 | 06 | 3 | WBH-03 | — | Slack form success → shows confirmation toast | unit | `cd dashboard && npx vitest run --reporter=dot -t "slack"` | ❌ W0 | ⬜ pending |
| 8-06-03 | 06 | 3 | WBH-03 | — | Slack form error (non-200) → shows error state inline | unit | `cd dashboard && npx vitest run --reporter=dot -t "slack"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/api/test_github_webhook.py` — 5 stubs for WBH-01 webhook handler
- [ ] `tests/integrations/test_migration_009.py` — alembic upgrade/downgrade test
- [ ] `tests/api/test_integrations_slack.py` — 3 stubs for PATCH /v1/integrations/slack
- [ ] `dashboard/__tests__/components/scans/SourceBadge.test.tsx` — Auto-scan badge stubs
- [ ] `dashboard/__tests__/settings/integrations-slack.test.tsx` — Slack form stubs
- [ ] `tests/jobs/test_scan_repo.py` — already exists; add 5 new test stubs for Slack fire

*Existing backend test infrastructure (conftest.py, fixtures) covers auth, DB, respx. No new framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GitHub push to connected repo triggers scan within 30s | WBH-01 | Requires live GitHub App + real push event | Configure GitHub App webhook URL to Fly.io endpoint; push a commit; verify scan appears in dashboard within 30s |
| Slack alert fires on live Critical scan | WBH-03 | Requires live Slack webhook URL + real Terraform with Critical finding | Configure Slack webhook; push Terraform with open S3 bucket; verify Slack message received |

---

## Threat Model Notes

| Threat Ref | Description | Mitigation |
|------------|-------------|------------|
| T-8-01 | Forged GitHub webhook — attacker POSTs crafted payload | HMAC-SHA256 verify with `hmac.compare_digest` (timing-safe) before any payload processing |
| T-8-02 | SQL injection via webhook payload fields | All DB inserts parameterized via SQLAlchemy ORM; no raw SQL with payload data |
| T-8-03 | Slack SSRF — team saves arbitrary URL as webhook | URL prefix validation: must start with `https://hooks.slack.com/` |
| T-8-04 | Slack fire leaks scan data to unauthorized channel | Slack only fires for team's own configured URL; URL stored under RLS-enforced teams row |
| T-8-05 | Path traversal via webhook repo/branch fields | scan_repo's existing traversal guard (`.resolve().relative_to()`) covers webhook-dispatched jobs |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING (❌) references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
