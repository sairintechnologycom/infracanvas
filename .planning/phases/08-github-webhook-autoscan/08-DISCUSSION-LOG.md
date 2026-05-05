# Phase 8: GitHub Webhook + Auto-scan — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-05
**Phase:** 8 — GitHub Webhook + Auto-scan
**Areas discussed:** Push filtering, Slack storage, Webhook dedup, Scan source label

---

## Push filtering

### Q1: Which branch pushes should trigger an auto-scan?

| Option | Description | Selected |
|--------|-------------|----------|
| Default branch only | Only fire on pushes to the repo's default branch. Compare `ref` to `refs/heads/{default_branch}` from payload. | ✓ |
| Any branch | Every push to every branch triggers a scan. High volume, expensive. | |
| Configurable per installation | Let users pick a branch filter. Requires schema + UI — scope risk. | |

**User's choice:** Default branch only

---

### Q2: Multi-commit push batches — scan HEAD or each commit?

| Option | Description | Selected |
|--------|-------------|----------|
| One scan per push event, HEAD sha | Use `after` field. One job regardless of commit count. | ✓ |
| Scan each commit individually | Iterate `commits[]`, enqueue one scan per sha. Expensive for batched pushes. | |

**User's choice:** One scan per push event, HEAD sha

---

### Q3: Ping events and deleted-branch push handling?

| Option | Description | Selected |
|--------|-------------|----------|
| 200 OK, no-op | Silently acknowledge with 200 and no scan. Same as Clerk webhook swallow pattern. | ✓ |
| Log and 200 OK | Same but emit structlog INFO line for Axiom observability. | |

**User's choice:** 200 OK, no-op

---

## Slack storage

### Q4: Where should the Slack webhook URL be stored?

| Option | Description | Selected |
|--------|-------------|----------|
| teams.slack_webhook_url column | Add TEXT NULL column to teams table. Minimal change, team-scoped. | ✓ |
| Separate integrations table | (team_id, provider, config jsonb). Extensible but YAGNI risk. | |
| Env-var global | Single URL for all teams. Doesn't work for multi-tenant SaaS. | |

**User's choice:** teams.slack_webhook_url column

---

### Q5: What backend endpoint should the Slack 'Save' button call?

| Option | Description | Selected |
|--------|-------------|----------|
| PATCH /v1/integrations/slack | New endpoint, matches existing TODO comment in dashboard stub. | ✓ |
| PATCH /v1/teams/me | Extend a team settings endpoint. Phase 6 doesn't have one — adds scope. | |

**User's choice:** PATCH /v1/integrations/slack

---

### Q6: When should the Slack alert fire?

| Option | Description | Selected |
|--------|-------------|----------|
| Webhook-triggered scans only | Only source='webhook'. No noise from manual scans. | ✓ |
| All scans with Critical findings | Any source fires. Simpler but alerts on user-initiated scans. | |

**User's choice:** Webhook-triggered scans only

---

## Webhook dedup

### Q7: Rapid push events to the same branch — deduplicate?

| Option | Description | Selected |
|--------|-------------|----------|
| No dedup — scan every push event | Consistent with Phase 7.5 D-08. Stripe meter is the cost ceiling. | ✓ |
| Dedup within 60s — only latest sha | Skip if pending scan exists for same repo/branch. Adds complexity. | |
| Dedup within 30s — drop duplicates | Similar but tighter window. Complicates the otherwise-simple handler. | |

**User's choice:** No dedup — scan every push event

---

### Q8: Idempotency guard on X-GitHub-Delivery header?

| Option | Description | Selected |
|--------|-------------|----------|
| No idempotency guard | Redelivered events create a second scan row. Acceptable for MVP. | ✓ |
| Guard on X-GitHub-Delivery | Redis key TTL 1hr. Adds a read on every webhook call. | |

**User's choice:** No idempotency guard

---

## Scan source label

### Q9: How to label webhook-triggered scans in the DB?

| Option | Description | Selected |
|--------|-------------|----------|
| New source='webhook' value | Clean distinction alongside 'github' and 'cli'. | ✓ |
| Reuse source='github' + trigger_type column | More normalized but adds a column for a 1-bit distinction. | |
| Reuse source='github' with no distinction | All GitHub scans look the same. Contradicts the Slack decision. | |

**User's choice:** New source='webhook' value

---

### Q10: How should webhook scans appear in the dashboard?

| Option | Description | Selected |
|--------|-------------|----------|
| 'Auto-scan' badge + branch/commit | New badge variant for source='webhook'. Minimal frontend work. | ✓ |
| No UI distinction | Webhook scans look identical to manual scans. Saves frontend work. | |

**User's choice:** 'Auto-scan' badge + branch/commit

---

## Claude's Discretion

- **Slack HTTP client:** `httpx.AsyncClient` (already a dependency) vs `slack-sdk`. Planner picks.
- **Slack message format:** Block Kit vs simple text. Planner picks a sensible structure.
- **Webhook route location:** Extend `routes/webhooks.py` vs new `routes/github_webhook.py`. Planner picks.
- **Migration number:** Sequential after Phase 7.5's 008. Planner assigns (likely 009).
- **`default_branch` resolution:** Use `repository.default_branch` from the push payload directly vs fetching from DB. Planner decides (payload field is simpler).

## Deferred Ideas

- Branch filter configuration per installation
- Idempotency guard on `X-GitHub-Delivery`
- Per-team webhook enqueue rate limiting
- Slack alerts for manually-triggered scans
- Additional alert channels (PagerDuty, email, MS Teams)
- GitHub PR Bot — v1.2 (PRB-01..02)
- GitLab / Bitbucket / Azure DevOps webhooks — v1.2 Enterprise
