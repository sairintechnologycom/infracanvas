# Phase 8: GitHub Webhook + Auto-scan — Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Add the auto-trigger layer on top of Phase 7.5's manual scan pipeline. When a user pushes to a connected GitHub repo's default branch, a signed push webhook arrives at a new `POST /v1/webhooks/github` endpoint, gets HMAC-SHA256 verified, creates a `scans` row with `source='webhook'`, and enqueues the existing `scan_repo` taskiq job (7-kwarg contract unchanged — no worker changes). On scan completion, if the result contains ≥1 Critical finding, fire a Slack alert to the team's configured webhook URL.

**In scope:**
- `POST /v1/webhooks/github` — GitHub push webhook handler (HMAC-SHA256 verification)
- Push filtering: default branch only; ping events and deleted-branch pushes silently 200 OK
- One scan per push event using the `after` sha (HEAD); no dedup
- New `scans.source = 'webhook'` value
- New `teams.slack_webhook_url TEXT NULL` column + `PATCH /v1/integrations/slack` endpoint
- Slack HTTP POST fired inside `scan_repo` worker when `source='webhook'` and ≥1 Critical finding
- Dashboard: wire the existing Slack webhook URL stub in `/settings/integrations` to the new endpoint
- Dashboard: 'Auto-scan' badge on scan rows/detail where `source='webhook'`

**Out of scope:**
- Branch-level filter configuration per installation — deferred
- Idempotency guard on `X-GitHub-Delivery` header — deferred (no dedup philosophy matches Phase 7.5 D-08)
- Per-team rate limiting on webhook enqueues — revisit only if abuse emerges
- Slack alerts for manually-triggered scans (`source='github'` or `source='cli'`) — alert fires for webhook source only
- GitLab / Bitbucket / Azure DevOps webhooks — v1.2 Enterprise
- GitHub PR Bot (diff comment + status check) — v1.2 (PRB-01..02)

</domain>

<decisions>
## Implementation Decisions

### Push event filtering
- **D-01:** Default branch only. Handler reads `ref` from the push payload; compare against `refs/heads/{default_branch}`. The `default_branch` value is already stored (or available via GitHub API) from the installation's repo metadata. Non-default branch pushes: 200 OK, no-op.
- **D-02:** One scan per push event, HEAD sha. Use the webhook payload's `after` field as the `sha` kwarg. A 5-commit batch push enqueues exactly one `scan_repo` job.
- **D-03:** Ping events (`X-GitHub-Event: ping`) and deleted-branch pushes (payload `after` = `0000000000000000000000000000000000000000`) → 200 OK, no-op. Follows the Clerk webhook handler's "swallow unknown events" pattern.

### Slack integration
- **D-04:** Store Slack webhook URL as `teams.slack_webhook_url TEXT NULL` column. One URL per team, consistent with the existing RLS model (team-scoped column, SET LOCAL GUC before UPDATE). One new migration (009).
- **D-05:** Backend endpoint `PATCH /v1/integrations/slack` — accepts `{webhook_url}` body, validates the URL (must start with `https://hooks.slack.com/`), updates `teams.slack_webhook_url`. Matches the `TODO Phase 8: POST /v1/integrations/slack` comment already in the dashboard integrations page stub. Use PATCH (idempotent re-save).
- **D-06:** Slack alert fires **only for webhook-triggered scans** (`source='webhook'`). Fires inside the `scan_repo` worker after `finalize_scan` succeeds, when the scan summary contains ≥1 Critical finding AND `teams.slack_webhook_url IS NOT NULL`. Manual on-demand scans (`source='github'`) do not trigger alerts.

### Webhook dedup
- **D-07:** No dedup — scan every push event. Consistent with Phase 7.5 D-08 ("no dedup on repeat clicks"). Every push event enqueues a `scan_repo` job. Stripe meter is the natural cost ceiling. Per-team rate-limiting deferred unless abuse emerges.
- **D-08:** No idempotency guard on `X-GitHub-Delivery` header. Redelivered events create a second scan row (different `scan_id`, no data corruption). Duplicate scans appear in history, which is acceptable for the MVP.

### Scan source label
- **D-09:** New `source='webhook'` value alongside existing `'github'` (manual GitHub scan) and `'cli'`. `scans.source` is a plain `TEXT` column — no Postgres enum constraint — so adding the new value requires only adding it to the `ScanStatus`-equivalent enum in Python code (no migration needed beyond the Phase 6 definition). The webhook handler creates the `scans` row with `source='webhook'`.
- **D-10:** Dashboard shows an 'Auto-scan' badge (new badge variant keyed on `source === 'webhook'`) in both the scan history list (`ScansTable` rows) and the scan detail `MetadataHeader`. Branch + shortened commit sha (`sha.slice(0, 7)`) displayed in metadata alongside the badge. Minimal frontend work — add the badge variant to the existing source-badge pattern.

### Claude's Discretion
- **Slack HTTP client:** `httpx.AsyncClient` (already a dependency in the worker) vs `slack-sdk`. Planner picks — `httpx` is likely cleaner given the existing stack.
- **Slack message format:** Block Kit vs simple text payload. Planner picks a sensible structure (repo, branch, sha, critical count, scan link).
- **Webhook route location:** Extend existing `backend/app/routes/webhooks.py` (adds a GitHub router alongside the Clerk router) vs a new `routes/github_webhook.py`. Planner picks — extending `webhooks.py` is consistent with the existing file's purpose.
- **Migration number:** Sequential after Phase 7.5's 008. Planner assigns (likely 009 for `slack_webhook_url`).
- **`default_branch` resolution:** The push payload includes `repository.default_branch`. Planner decides whether to use that directly vs fetching from `github_installations` table metadata. Using the payload field is simpler and avoids a DB read.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project context
- `.planning/PROJECT.md` — project constraints (solo founder, $10–104/mo budget, security boundaries)
- `.planning/REQUIREMENTS.md` — milestone-wide requirements (WBH-01, WBH-02, WBH-03)
- `.planning/ROADMAP.md` — Phase 8 row (success criteria: push triggers scan within 30s; scan lands in Neon + R2 with commit SHA; Slack fires on ≥1 Critical)

### Prior phase decisions (MUST read)
- `.planning/phases/06-saas-backend-foundation/06-CONTEXT.md` — D-01..D-21: teams/RLS/R2/taskiq/Fly/structlog patterns. Especially D-02 (SET LOCAL GUC), D-12 (Fly hosting), D-13 (Upstash Redis queue), D-18..D-21 (Sentry/structlog/Axiom/request-ID propagation).
- `.planning/phases/07.5-github-repo-connector/07.5-CONTEXT.md` — D-01..D-17: GitHub App auth, scan_repo 7-kwarg contract, R2 key shape, pending→ready flow, mint-per-scan token strategy. **Phase 8 reuses `scan_repo` unchanged.**

### Existing code (key files to read before planning)
- `backend/app/queue/tasks/scan_repo.py` — the `@broker.task` that Phase 8 enqueues from the webhook route. 7-kwarg signature: `scan_id, installation_id, repo, branch, sha, path, team_id`. Slack firing logic lands at the end of this file's happy path.
- `backend/app/routes/webhooks.py` — existing Clerk webhook route. Phase 8 adds a sibling GitHub webhook router here. Note the raw-bytes pattern (never `.json()` before HMAC verify).
- `backend/app/auth/webhooks.py` — Svix HMAC verify pattern. GitHub uses `X-Hub-Signature-256` with `hmac.compare_digest` — not Svix, but same raw-bytes discipline.
- `backend/app/settings.py` — `github_app_webhook_secret` already present (empty default, unused until Phase 8).
- `backend/app/db/models.py` — `Team`, `Scan`, `GithubInstallation` ORM classes. `Scan.source` is a `TEXT` column; add `'webhook'` to the Python enum. `Team` gets `slack_webhook_url`.
- `dashboard/app/(dashboard)/settings/integrations/page.tsx` — Slack stub block at line ~100. `TODO Phase 8: POST /v1/integrations/slack { webhook_url }` comment is the exact wiring point.
- `dashboard/components/scans/` — existing source badge / scan row components where 'Auto-scan' badge variant lands.

### GitHub webhook documentation
- GitHub push event payload schema: `repository.default_branch`, `after` (HEAD sha), `ref` (branch ref), `deleted` (boolean for branch deletion events), `X-GitHub-Event` header, `X-Hub-Signature-256` header (HMAC-SHA256 of raw body with webhook secret).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scan_repo` taskiq task (7-kwarg) — Phase 8's webhook handler is a new *caller*; the worker itself is unchanged. Slack firing logic appended to `scan_repo`'s happy path.
- `backend/app/routes/webhooks.py` pattern — raw-body read, HMAC verify, dispatch by event type, 200 swallow for unknown events. Replicate for GitHub's `X-Hub-Signature-256`.
- `finalize_scan` helper in `backend/app/services/scans.py` — already called inside `scan_repo`; Slack fire happens *after* `await finalize_scan(...)` succeeds.
- `backendFetch` + Clerk JWT pattern in `dashboard/lib/backend.ts` — new `PATCH /api/integrations/slack` proxy route follows the same CC-13 pattern as existing proxy routes.
- Existing `InstallButton`, `RepoCombobox`, `BranchPicker` in `dashboard/components/integrations/` — Slack save form follows the same client component pattern.

### Established Patterns
- **Raw bytes webhook verify (never `.json()` first):** Documented in `backend/app/routes/webhooks.py` module docstring as a critical pitfall (RESEARCH § F2). Must apply to GitHub webhook handler too.
- **SET LOCAL GUC before every team-scoped DB write:** Phase 6 D-02. The `PATCH /v1/integrations/slack` route must `SET LOCAL app.current_team_id` before UPDATE `teams`.
- **Taskiq job dispatch:** CC-4 pattern — `await scan_repo.kicker().with_labels(...).kiq(...)` with all 7 kwargs by name.
- **structlog + Sentry tags:** Phase 6 D-21. `scan_repo`'s `log_ctx.bind(...)` already tags `team_id`, `repo`, `branch`, `sha`. Slack fire adds a `slack_notified=True/False` tag.
- **Fly.io worker process:** Phase 6 D-12. No infra changes — `scan_repo` runs on the existing Fly worker. Webhook route runs on the `api` process.

### Integration Points
- `backend/app/routes/webhooks.py` → add `router_github` APIRouter at `POST /v1/webhooks/github`
- `backend/app/db/models.py` → `Team` model gets `slack_webhook_url` column; `ScanSource` enum gets `'webhook'`
- `backend/migrations/` → migration 009: `ALTER TABLE teams ADD COLUMN slack_webhook_url TEXT NULL`
- `backend/app/queue/tasks/scan_repo.py` → after `finalize_scan`, read `teams.slack_webhook_url` and fire Slack if `source='webhook'` and Critical count ≥ 1
- `dashboard/app/(dashboard)/settings/integrations/page.tsx` → wire the Slack save button to `PATCH /api/integrations/slack`
- `dashboard/app/api/integrations/slack/route.ts` → new proxy route
- `dashboard/components/scans/` → 'Auto-scan' badge variant for `source === 'webhook'`

</code_context>

<specifics>
## Specific Requirements

- Webhook handler must read raw bytes before any JSON parsing — same discipline as the Clerk webhook handler (`body = await request.body()` pattern). Documented as a critical pitfall.
- Default branch comparison: use `repository.default_branch` from the push payload directly (avoids a DB read).
- Deleted-branch detection: check `payload["deleted"] == True` or `payload["after"] == "0" * 40`.
- `PATCH /v1/integrations/slack` must validate that `webhook_url` starts with `https://hooks.slack.com/` before saving (prevent storing arbitrary URLs that could be used for SSRF).
- Slack message must include: repo name, branch, commit sha (7-char), Critical finding count, and a direct link to `/scans/{scan_id}` in the dashboard.

</specifics>

<deferred>
## Deferred Ideas

- **Branch filter configuration per installation** — user-configurable branch allowlist (e.g., scan `main` + `release/*`). Own phase if demand arises.
- **Idempotency on `X-GitHub-Delivery`** — Redis key guard to skip redelivered events. Add if duplicate-scan UX becomes a complaint.
- **Per-team webhook enqueue rate limiting** — add if abuse emerges; Stripe meter is the cost ceiling for now.
- **Slack alerts for manual scans** — user decision: webhook-only. If the team wants alerts for all Critical scans, revisit in a later phase.
- **Additional alert channels** (PagerDuty, email, MS Teams) — separate integrations table warranted at that point. Not needed now.
- **GitHub PR Bot** — diff comment + status check on PR push — v1.2 (PRB-01..02).
- **GitLab / Bitbucket / Azure DevOps webhooks** — v1.2 Enterprise.

</deferred>

---

*Phase: 8 — GitHub Webhook + Auto-scan*
*Context gathered: 2026-05-05*
