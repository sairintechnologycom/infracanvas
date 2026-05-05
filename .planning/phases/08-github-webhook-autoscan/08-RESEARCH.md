# Phase 8: GitHub Webhook + Auto-scan — Research

**Researched:** 2026-05-05
**Domain:** GitHub webhook HMAC verification, push-event filtering, taskiq dispatch, Slack HTTP alerting, Alembic migration, Next.js proxy routes, dashboard badge variants
**Confidence:** HIGH — all findings verified directly against codebase; no assumed patterns

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Default branch only. Compare `ref` against `refs/heads/{repository.default_branch}` from the payload. Non-default → 200 OK no-op.
- **D-02:** One scan per push event using the `after` field as `sha`. A batch push of 5 commits enqueues exactly one `scan_repo` job.
- **D-03:** Ping events (`X-GitHub-Event: ping`) and deleted-branch pushes (`after == "0"*40`) → 200 OK no-op.
- **D-04:** `teams.slack_webhook_url TEXT NULL` — one URL per team. Migration 009.
- **D-05:** `PATCH /v1/integrations/slack` — validates URL starts with `https://hooks.slack.com/`. Uses SET LOCAL GUC before UPDATE.
- **D-06:** Slack fires only for `source='webhook'` scans with ≥1 Critical finding AND `slack_webhook_url IS NOT NULL`. Fires inside `scan_repo` after `finalize_scan` succeeds.
- **D-07:** No dedup — every push event enqueues a `scan_repo` job.
- **D-08:** No idempotency guard on `X-GitHub-Delivery`. Redelivered events create a second scan row.
- **D-09:** New `source='webhook'` value. `scans.source` is plain `TEXT` — no Postgres enum change needed. Python-side enum/constant gets the new value.
- **D-10:** Dashboard 'Auto-scan' badge keyed on `source === 'webhook'` in both `ScansTable` rows and `MetadataHeader`. Branch + `sha.slice(0, 7)` displayed alongside the badge.

### Claude's Discretion
- Slack HTTP client: `httpx.AsyncClient` vs `slack-sdk`. Use `httpx` — already imported in the worker stack.
- Slack message format: Block Kit vs simple text. Planner picks a sensible Block Kit structure.
- Webhook route location: Extend `backend/app/routes/webhooks.py` (adds a GitHub router alongside the Clerk router) vs a new file. Extending `webhooks.py` is consistent.
- Migration number: 009 (sequential after 008_scan_github_columns).
- `default_branch` resolution: Use `repository.default_branch` from payload directly — avoids a DB read.

### Deferred Ideas (OUT OF SCOPE)
- Branch filter configuration per installation
- Idempotency on `X-GitHub-Delivery`
- Per-team webhook rate limiting
- Slack alerts for manual scans
- Additional alert channels (PagerDuty, email, MS Teams)
- GitHub PR Bot
- GitLab / Bitbucket / Azure DevOps webhooks
</user_constraints>

---

## Summary

Phase 8 adds three interconnected capabilities on top of Phase 7.5's scan pipeline: a GitHub push webhook handler, a Slack alert channel, and dashboard surfacing for webhook-sourced scans.

The codebase is well-prepared. `settings.github_app_webhook_secret` already exists (provisioned in Phase 7.5 D-15, unused until now). The `scan_repo` taskiq job is complete and its 7-kwarg dispatch contract is locked. The Slack stub form is pre-wired in `/settings/integrations/page.tsx` with a `TODO Phase 8` comment and a working `<input type="url">`. The `SourceCell` component in `ScansTable.tsx` already has a `github_webhook` branch rendered as "GitHub" — it needs renaming to `'webhook'` and display text to `'Auto-scan'`. `MetadataHeader.tsx` has no source badge at all yet.

The key architectural insight: **the webhook handler is a new caller of the existing `scan_repo` job — the worker itself is only modified at its tail (Slack fire after `finalize_scan`)**. No changes to the 7-kwarg signature. The `path` kwarg defaults to `'.'` for webhook-sourced scans since no subpath is configured per-installation (Phase 8 scope).

**Primary recommendation:** Implement in this order: (1) migration 009, (2) ORM update, (3) PATCH /v1/integrations/slack, (4) POST /v1/webhooks/github, (5) scan_repo Slack tail, (6) dashboard proxy + form wiring, (7) dashboard badge.

---

## Implementation Path (per component)

### 1. Migration 009: `teams.slack_webhook_url`

**Current state:** Migrations run through `008_scan_github_columns` (adds six GitHub provenance columns to `scans`). The `teams` table has `id`, `clerk_org_id`, `name`, `stripe_customer_id`, `created_at`, `updated_at`. No Slack column.

**Implementation path:**

File: `backend/migrations/versions/20260505_009_teams_slack_webhook.py`

```python
revision: str = "009_teams_slack_webhook"
down_revision = "008_scan_github_columns"

def upgrade() -> None:
    op.add_column("teams", sa.Column("slack_webhook_url", sa.Text(), nullable=True))

def downgrade() -> None:
    op.drop_column("teams", "slack_webhook_url")
```

No RLS changes needed. The existing `teams` RLS policy (`current_setting('app.current_team_id', true)::uuid = id`) already enforces team-scoped access. The `PATCH /v1/integrations/slack` route uses `SET LOCAL app.current_team_id` before UPDATE, exactly as the scan_repo worker does for `stripe_customer_id` reads (verified in `scan_repo.py` lines 263-276).

**ORM update:** Add to `Team` model in `backend/app/db/models.py`:
```python
slack_webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
```

**Python source enum:** `scans.source` is `Mapped[str | None]` (plain `TEXT`, confirmed in `models.py` line 68). Add `webhook = "webhook"` to the `ScanSource`-equivalent constant/enum wherever `'github'` and `'cli'` are defined. No Postgres migration needed for this — the column is unconstrained text.

---

### 2. `PATCH /v1/integrations/slack`

**Current state:** No integrations router exists. `main.py` registers: `health`, `webhooks`, `scans`, `share`, `github`, `scans_from_github`. The route must be added.

**Implementation path:**

New file: `backend/app/routes/integrations.py`
- `router = APIRouter(prefix="/v1/integrations", tags=["integrations"])`
- Auth gate: `require_role("owner", "admin")` — URL change is an account-level setting, restrict to owners/admins.
- Pydantic request body: `class SlackWebhookReq(BaseModel): webhook_url: str`
- Validation: `if not body.webhook_url.startswith("https://hooks.slack.com/"): raise HTTPException(422, "invalid_slack_url")`
- DB pattern (mirrors `scan_repo.py` lines 261-276):
  ```python
  async with sm() as session, session.begin():
      await session.execute(
          text("SELECT set_config('app.current_team_id', :t, true)"),
          {"t": str(team.id)},
      )
      await session.execute(
          text("UPDATE teams SET slack_webhook_url = :url WHERE id = :id"),
          {"url": body.webhook_url, "id": str(team.id)},
      )
  ```
- Return: `{"message": "Slack webhook saved"}` with status 200.

Register in `main.py`: `app.include_router(integrations_routes.router)`

**SSRF note (from CONTEXT.md specifics):** The `https://hooks.slack.com/` prefix check is the SSRF mitigation. No additional network validation needed — storing an arbitrary URL that we later POST to is the threat. The prefix constraint is the full guard.

---

### 3. `POST /v1/webhooks/github`

**Current state:** `backend/app/routes/webhooks.py` has one router at prefix `/v1/webhooks` with a single `POST /clerk` endpoint. The raw-bytes pattern is documented and implemented: `body = await request.body()` before any JSON parsing.

**Implementation path:**

Add to `backend/app/routes/webhooks.py` (or a sibling router in the same file):

```python
import hashlib
import hmac
import json as _json

from app.settings import settings

@router.post("/github", status_code=200)
async def github_webhook(request: Request) -> dict[str, bool]:
    body = await request.body()  # RAW BYTES — never .json() first

    # 1. HMAC-SHA256 verify
    sig_header = request.headers.get("X-Hub-Signature-256", "")
    expected = "sha256=" + hmac.new(
        settings.github_app_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(sig_header, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bad_signature")

    # 2. Ping event — swallow
    event = request.headers.get("X-GitHub-Event", "")
    if event == "ping":
        return {"ok": True}

    # 3. Parse (AFTER verification)
    try:
        payload = _json.loads(body)
    except _json.JSONDecodeError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid_json") from e

    # 4. Deleted-branch guard (D-03)
    if payload.get("deleted") is True or payload.get("after") == "0" * 40:
        return {"ok": True}

    # 5. Default-branch filter (D-01)
    ref = payload.get("ref", "")
    default_branch = payload.get("repository", {}).get("default_branch", "")
    if ref != f"refs/heads/{default_branch}":
        return {"ok": True}

    # 6. Extract fields
    installation_id: int = payload["installation"]["id"]
    repo: str = payload["repository"]["full_name"]
    branch: str = default_branch
    sha: str = payload["after"]
    team_id = ...  # see "Team ID Resolution" below
    scan_id = new_uuid7()

    # 7. INSERT pending scans row with source='webhook'
    # 8. Enqueue scan_repo (7-kwarg contract, path='.')
    # 9. Return 200
    return {"ok": True}
```

**Team ID Resolution (critical design point):** The push payload does NOT carry a Clerk team_id. The mapping is: `installation_id → github_installations.team_id`. The webhook handler must do a DB lookup:

```sql
SELECT set_config('app.current_team_id', id::text, true)  -- not available yet
SELECT team_id FROM github_installations
WHERE github_installation_id = :iid
LIMIT 1
```

This lookup must use a bypass-RLS session (or the `infracanvas_app` role without GUC set) since the webhook arrives with no user context. Looking at the `scan_repo` worker pattern: it uses `get_sessionmaker()` and sets the GUC from the already-known `team_id`. The webhook handler learns `team_id` from the lookup itself.

**Pattern:** Use `raw_session` (the dependency that doesn't require auth) or open a fresh sessionmaker session. Since `github_installations` has RLS, but the webhook arrives without a team context, the handler needs a BYPASSRLS read OR must use the SECURITY DEFINER helper approach. The cleanest solution:

```python
# Use raw sessionmaker, SET LOCAL to a sentinel first, then query by installation_id
# using a SECURITY DEFINER function (like scan_team_id() pattern from Phase 6 D-04).
# Simpler alternative: read raw_session without GUC, query github_installations
# without RLS enforcement (use a SECURITY DEFINER or infracanvas_owner role read).
```

**Verified pattern from Phase 7.5:** `scans_from_github.py` does the membership probe inside a team-scoped session (team_id known from Clerk JWT). For webhooks, team_id is unknown until we resolve the installation. Two options:

- **Option A (recommended):** New SECURITY DEFINER function `team_id_for_installation(bigint)` — same approach as `scan_team_id()` from migration 004. Returns `team_id` without requiring GUC. The webhook uses `raw_session` and calls this function.
- **Option B:** Add a query that runs as the migration owner role (BYPASSRLS) in the webhook context. Requires the session factory to support elevated role for this specific query.

Option A is consistent with the established pattern in this codebase. The planner must decide and add the SECURITY DEFINER function to migration 009 or a separate migration 009b.

**Enqueue pattern** (from `scans_from_github.py` lines 149-167):
```python
from app.queue.tasks.scan_repo import scan_repo
await (
    scan_repo.kicker()
    .with_labels(request_id=rid)
    .kiq(
        scan_id=str(scan_id),
        installation_id=installation_id,
        repo=repo,
        branch=branch,
        sha=sha,
        path=".",           # webhook scans always scan root (Phase 8 scope)
        team_id=str(team_id),
    )
)
```

**Missing `github_app_webhook_secret` guard:** `settings.github_app_webhook_secret` defaults to `""` (confirmed line 49 of settings.py). If the secret is empty, `hmac.compare_digest` against an empty-secret HMAC will pass for any payload signed with an empty key. The handler should short-circuit with 500 (or log a warning) when the secret is unconfigured.

---

### 4. `scan_repo.py` Slack Integration

**Current state:** `scan_repo` happy path ends at line 297 with `log_ctx.info("scan_repo.success", ...)`. The `finalize_scan` call is at lines 281-290 inside a `session.begin()` block. After that block closes, the scan is `ready`. Slack fire goes between the `log_ctx.info("scan_repo.success", ...)` call and the `finally` block.

**Source value availability:** The `scan_repo` function signature has 7 kwargs: `scan_id, installation_id, repo, branch, sha, path, team_id`. There is NO `source` kwarg. To know whether `source='webhook'`, the worker must read it from the `scans` row. This fits the existing pattern of reading `team_row` from the DB inside the session block.

**Two approaches:**

- **Option A (no signature change):** Read `source` and `slack_webhook_url` together from the DB in the existing session block at step 8. Extend the SELECT to include `scans.source` AND `teams.slack_webhook_url`:
  ```sql
  SELECT t.slack_webhook_url, s.source
  FROM teams t, scans s
  WHERE t.id = :team_id AND s.id = :scan_id
  ```
  Then fire Slack after `finalize_scan` if `source == 'webhook'`.

- **Option B:** Read `slack_webhook_url` and `source` in a fresh session block after `finalize_scan` succeeds. Cleaner separation but one extra DB roundtrip.

**Option A is recommended** — it piggybacks on the existing DB open, keeping the session-count flat.

**Critical count extraction:** `summary_json` is already computed by `_extract_summary(payload_bytes)` at line 249 and passed to `finalize_scan`. The critical count lives at `summary_json["findings"]["critical"]` if `summary_json` is not None. Example:
```python
critical_count = (
    (summary_json or {}).get("findings", {}).get("critical", 0)
)
```

**Slack HTTP call pattern:**
```python
import httpx

async with httpx.AsyncClient(timeout=5.0) as client:
    resp = await client.post(
        slack_webhook_url,
        json={
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn",
                 "text": f"*InfraCanvas Alert* — `{repo}` `{branch}` `{sha[:7]}`\n"
                         f"*{critical_count} Critical* finding(s) detected.\n"
                         f"<https://infracanvas.app/scans/{scan_id}|View scan>"}},
            ]
        },
    )
    resp.raise_for_status()
```

**httpx availability:** `httpx` is already imported in `scans_from_github.py` and is a declared dependency of the backend. It is NOT currently imported in `scan_repo.py` — it must be added to imports.

**Failure handling (D-06):** Slack HTTP failure must be caught, logged, and NOT re-raised. The scan is already `ready`; Slack is best-effort. Pattern:
```python
try:
    # fire Slack
    log_ctx.info("scan_repo.slack_notified", slack_notified=True)
except Exception as slack_exc:  # noqa: BLE001
    log_ctx.warning("scan_repo.slack_failed", error=repr(slack_exc))
    sentry_sdk.capture_exception(slack_exc)
# DO NOT raise — scan success is already committed
```

**Structlog tag:** Add `slack_notified=True/False` to the success log per CONTEXT.md code context (Phase 6 D-21 pattern).

---

### 5. Dashboard: `PATCH /api/integrations/slack` Proxy Route

**Current state:** Dashboard API routes live in `dashboard/app/api/`. The `backendFetch` utility in `dashboard/lib/backend.ts` handles Clerk Bearer token forwarding. Pattern verified from `dashboard/app/api/scans/from-github/route.ts`.

**New file:** `dashboard/app/api/integrations/slack/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { backendFetch } from '@/lib/backend'

export async function PATCH(req: NextRequest) {
  let body: unknown
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 })
  }
  try {
    const data = await backendFetch<{ message: string }>(
      '/v1/integrations/slack',
      { method: 'PATCH', body: JSON.stringify(body) },
    )
    return NextResponse.json(data)
  } catch (err) {
    const message = err instanceof Error ? err.message : '500'
    const status = ['422', '401'].includes(message) ? Number(message) : 500
    return NextResponse.json({ error: 'request_failed' }, { status })
  }
}
```

**Dashboard form wiring:** The stub form in `integrations/page.tsx` (lines 109-131) needs to call the proxy. The `onSubmit` handler currently has `// TODO Phase 8: POST /v1/integrations/slack { webhook_url }`. Replace with a `fetch('/api/integrations/slack', { method: 'PATCH', body: JSON.stringify({ webhook_url: formData.get('slack_webhook') }) })` call. Add loading/success/error state. The form uses `name="slack_webhook"` on the input.

**Component pattern:** Given the integrations page is already `'use client'`, the Slack form wiring stays inline in `page.tsx` — no need for a separate `SlackWebhookForm` component unless it gets complex. The `ScanTriggerForm` precedent shows how client-side fetch + state works in this page. Add `useState` for `slackSaving`, `slackSaved`, `slackError`.

---

### 6. Dashboard: Auto-scan Badge

**Current state (ScansTable.tsx):** The `SourceCell` component (lines 31-57) already has three branches: `'cli'`, `'manual'`, `'github_webhook'`. The `'github_webhook'` branch renders `Upload` icon + "GitHub" text. This is the wrong value and wrong label for Phase 8 — Phase 7.5 uses `source='github'` (not `'github_webhook'`). The `'webhook'` value (D-09) needs a new branch.

**Action:** Add a fourth branch for `source === 'webhook'`:
```tsx
if (source === 'webhook') {
  return (
    <div className="flex items-center gap-1.5">
      <Zap size={14} className="text-violet-500" />
      <span className="text-sm text-slate-600">Auto-scan</span>
    </div>
  )
}
```

The `github_webhook` branch can remain for backward-compat or be removed if no rows use it. The `'github'` value (Phase 7.5 manual scans) renders as neither `'cli'` nor `'manual'` nor `'webhook'` — it falls through to the `—` fallback. **This is a pre-existing gap**: Phase 7.5's `source='github'` has no dedicated display. Phase 8 only adds `'webhook'`; the `'github'` display gap is out of scope.

**Current state (MetadataHeader.tsx):** No source badge exists (lines 41-113 confirmed). D-10 requires adding an 'Auto-scan' badge here. Insert between `commit_sha` span and the score pill:

```tsx
{scan.source === 'webhook' && (
  <span
    className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium bg-violet-100 text-violet-700"
    data-testid="auto-scan-badge"
  >
    Auto-scan
  </span>
)}
```

**TypeScript type:** `ScanGetResp` and `ScanListItem` must include `source?: string | null` — verify in `dashboard/lib/types.ts`. If absent, add it.

---

## Gotchas & Landmines

### L-01: Raw body consumed before JSON parse (CRITICAL)
`await request.body()` in FastAPI buffers and returns the raw bytes. Unlike `request.json()`, calling `request.body()` is safe to call once and re-use the bytes. The existing Clerk handler does this correctly. The GitHub handler MUST follow the same pattern — `body = await request.body()` first, then HMAC verify, THEN `json.loads(body)`. Never call `await request.json()` in a webhook handler.

**Verified:** The module docstring for `webhooks.py` explicitly documents this as `RESEARCH § F2 critical pitfall`. The pattern is entrenched.

### L-02: Empty webhook secret passes HMAC check
`settings.github_app_webhook_secret` defaults to `""`. `hmac.new(b"", body, sha256)` produces a valid HMAC for empty-key payloads. An attacker who knows the secret is empty can forge any payload. Add a startup guard: if the secret is empty when a GitHub push arrives, return 500 and log an error rather than silently accepting all payloads.

```python
if not settings.github_app_webhook_secret:
    log.error("github_webhook.secret_not_configured")
    raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "webhook_secret_not_configured")
```

### L-03: Team ID resolution requires BYPASSRLS or SECURITY DEFINER
The push webhook carries `installation.id` but NOT `team_id`. The `github_installations` table has RLS requiring `app.current_team_id` to be set — but we don't know `team_id` until we read the row. This is a bootstrapping problem. The codebase resolves the analogous problem for scans via a `SECURITY DEFINER` function (`scan_team_id()` in migration 004). Migration 009 must add `team_id_for_installation(bigint) RETURNS uuid SECURITY DEFINER` or equivalent. Without this, the webhook handler cannot look up the team without bypassing RLS entirely.

### L-04: `path` kwarg for webhook scans
The `scan_repo` job takes `path` as a kwarg (the subdirectory within the cloned repo to scan). For webhook-sourced scans, no per-installation subpath is configured in Phase 8. Use `path='.'` as the default. This means the entire repo is scanned. If a team previously configured a subpath for manual scans via `ScanTriggerForm`, webhook scans will ignore that — they always scan root. This is a documented Phase 8 limitation (subpath per installation is deferred).

### L-05: `SourceCell` in ScansTable has `'github_webhook'` not `'webhook'`
The current code has `if (source === 'github_webhook')` at line 48 of `ScansTable.tsx`. Phase 7.5 sets `source='github'` for manual scans. Phase 8 sets `source='webhook'`. Neither matches `'github_webhook'`. The `'github_webhook'` branch is dead code. Phase 8 adds `source === 'webhook'`; leave `'github_webhook'` in place or remove it — but do NOT rely on it for the new badge.

### L-06: `finalize_scan` returns `None`, not a summary
`finalize_scan` does not return the critical count. The critical count must be derived from `summary_json` which is computed BEFORE `finalize_scan` is called (line 249 of `scan_repo.py`: `summary_json = _extract_summary(payload_bytes)`). This variable is already in scope when the Slack fire code runs — no additional DB read needed for the count.

### L-07: Slack HTTP call timeout
Slack webhooks occasionally have elevated latency. Without a timeout, a slow Slack response can hold the worker thread indefinitely. Use `httpx.AsyncClient(timeout=5.0)` — 5 seconds is sufficient for a webhook POST and won't materially delay job completion.

### L-08: `hmac.new` vs `hmac.HMAC`
Python's `hmac` module: `hmac.new(key, msg, digestmod)` is the constructor. `key` must be `bytes`. `settings.github_app_webhook_secret` is a `str` — must call `.encode()`. The raw body is already `bytes`. Do NOT use `hmac.digest()` (available Python 3.7+) — stick with `hmac.new(...).hexdigest()` for clarity and testability.

### L-09: Non-push events (other than ping)
GitHub sends other event types to the webhook endpoint (e.g., `push`, `installation`, `check_run`). The handler only processes `push`. Non-push, non-ping events should return 200 OK (swallow pattern). Check `X-GitHub-Event` header: if it's not `'push'` and not `'ping'`, return `{"ok": True}` immediately after HMAC verification.

### L-10: `scans_from_github.py` lazy import pattern
`scans_from_github.py` uses a lazy import for `scan_repo` (`from app.queue.tasks.scan_repo import scan_repo` inside the function body) to avoid circular import issues. The webhook handler should use the same lazy import pattern for consistency. However, since `scan_repo.py` exists now (Phase 7.5 complete), a top-level import would also work. The lazy pattern is safer.

---

## Test Patterns

### Backend: HMAC verification tests

The Clerk webhook test (`test_webhooks.py`) uses the `svix` library to sign bodies. For GitHub, use Python's `hmac` directly:

```python
import hashlib
import hmac as _hmac

def _gh_signed_headers(body: bytes, secret: str, event: str = "push") -> dict[str, str]:
    digest = _hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return {
        "X-Hub-Signature-256": f"sha256={digest}",
        "X-GitHub-Event": event,
        "Content-Type": "application/json",
    }

SECRET = "test-webhook-secret-abc"
```

Tests use `monkeypatch.setattr(settings, "github_app_webhook_secret", SECRET)`.

No Postgres container needed for most webhook tests — the handler is stateless for the HMAC/ping/filter checks. Only the happy-path dispatch test needs DB (to create the `github_installations` row and the `scans` INSERT).

### Backend: scan_repo Slack tests

```python
# Mock httpx at the module level (respx or monkeypatch)
import respx
import httpx

@pytest.mark.anyio
async def test_slack_fires_on_webhook_source_with_critical(monkeypatch, ...):
    # Set up: scan row with source='webhook', summary_json with critical>0
    # Mock: slack_webhook_url on team row = "https://hooks.slack.com/test"
    # Mock: httpx.AsyncClient.post (via respx or monkeypatch)
    with respx.mock:
        slack_route = respx.post("https://hooks.slack.com/test").mock(
            return_value=httpx.Response(200)
        )
        await scan_repo(scan_id=..., ...)
        assert slack_route.called

@pytest.mark.anyio
async def test_slack_does_not_fire_on_github_source(monkeypatch, ...):
    # source='github' (manual scan) → Slack must NOT fire

@pytest.mark.anyio
async def test_slack_does_not_fire_when_no_critical(monkeypatch, ...):
    # source='webhook', critical=0 → no Slack POST

@pytest.mark.anyio
async def test_slack_does_not_fire_when_url_null(monkeypatch, ...):
    # source='webhook', critical=3, slack_webhook_url=None → no POST

@pytest.mark.anyio
async def test_slack_failure_does_not_fail_scan(monkeypatch, ...):
    # Slack POST raises httpx.ConnectError → scan still succeeds, no re-raise
```

The `_exec_factory` pattern from `test_scan_repo.py` (the `_FakeProc` / subprocess mock) is the established approach for stubbing subprocess calls in the worker. Slack tests extend the happy-path fixture with the Slack mocks on top.

### Backend: PATCH /v1/integrations/slack tests

```python
def test_valid_url_saves(app_client, auth_headers_factory, team_a, seed_install):
    r = app_client.patch(
        "/v1/integrations/slack",
        json={"webhook_url": "https://hooks.slack.com/services/T/B/xyz"},
        headers=auth_headers_factory(team_a.clerk_org_id),
    )
    assert r.status_code == 200

def test_invalid_url_rejected(app_client, auth_headers_factory, team_a):
    r = app_client.patch(
        "/v1/integrations/slack",
        json={"webhook_url": "https://evil.example.com/steal"},
        headers=auth_headers_factory(team_a.clerk_org_id),
    )
    assert r.status_code == 422

def test_missing_url_rejected(app_client, auth_headers_factory, team_a):
    r = app_client.patch(
        "/v1/integrations/slack",
        json={},
        headers=auth_headers_factory(team_a.clerk_org_id),
    )
    assert r.status_code == 422
```

### Dashboard: Slack form tests

Pattern mirrors `settings-integrations-page.test.tsx`. The fetch mock targets `/api/integrations/slack` with method `PATCH`:

```typescript
it('Slack form submit calls PATCH proxy', async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => [] })  // installations
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ message: 'Slack webhook saved' }) })  // slack PATCH
  vi.stubGlobal('fetch', fetchMock)
  // render, fill input, submit
  // assert fetchMock called with PATCH + correct body
})

it('Slack form shows success state after save', async () => { ... })

it('Slack form shows error on 422', async () => { ... })
```

### Dashboard: Auto-scan badge tests

```typescript
// ScansTable badge test
it('source=webhook renders Auto-scan cell', async () => {
  const { ScansTable } = await import('@/components/scans/ScansTable')
  const data = makeData({ source: 'webhook' })
  render(<ScansTable data={data} currentParams={{}} />)
  expect(screen.getByText('Auto-scan')).toBeInTheDocument()
})

it('source=cli renders CLI cell (regression)', async () => {
  const { ScansTable } = await import('@/components/scans/ScansTable')
  const data = makeData({ source: 'cli' })
  render(<ScansTable data={data} currentParams={{}} />)
  expect(screen.getByText('CLI')).toBeInTheDocument()
})

// MetadataHeader badge test
it('source=webhook renders auto-scan-badge', async () => {
  const { MetadataHeader } = await import('@/components/scans/MetadataHeader')
  const scan = makeScan({ source: 'webhook' })
  render(<MetadataHeader scan={scan} />)
  expect(screen.getByTestId('auto-scan-badge')).toBeInTheDocument()
})

it('source=github does not render auto-scan-badge', async () => {
  const { MetadataHeader } = await import('@/components/scans/MetadataHeader')
  const scan = makeScan({ source: 'github' })
  render(<MetadataHeader scan={scan} />)
  expect(screen.queryByTestId('auto-scan-badge')).not.toBeInTheDocument()
})
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Backend framework | pytest + anyio (async tests) |
| Backend config file | `backend/pyproject.toml` (pytest section) |
| Backend quick run | `cd backend && pytest tests/api/test_github_webhook.py -x` |
| Backend full suite | `cd backend && pytest` |
| Dashboard framework | Vitest 4.1.4 + @testing-library/react |
| Dashboard config file | `dashboard/vitest.config.ts` |
| Dashboard quick run | `cd dashboard && npx vitest run __tests__/scans-table.test.tsx` |
| Dashboard full suite | `cd dashboard && npx vitest run` |

### Phase Requirements → Test Map

| Req | Behavior | Test Type | Automated Command | File |
|-----|----------|-----------|-------------------|------|
| WBH-01a | Bad HMAC → 401 | unit | `pytest tests/api/test_github_webhook.py::test_bad_signature_returns_401 -x` | Wave 0 |
| WBH-01b | Good HMAC + push → enqueues scan_repo | integration (rls) | `pytest tests/api/test_github_webhook.py::test_push_happy_path -x -m rls` | Wave 0 |
| WBH-01c | Ping → 200 no-op | unit | `pytest tests/api/test_github_webhook.py::test_ping_no_op -x` | Wave 0 |
| WBH-01d | Deleted branch → 200 no-op | unit | `pytest tests/api/test_github_webhook.py::test_deleted_branch_no_op -x` | Wave 0 |
| WBH-01e | Non-default branch → 200 no-op | unit | `pytest tests/api/test_github_webhook.py::test_non_default_branch_no_op -x` | Wave 0 |
| WBH-02a | source='webhook' + Critical → Slack fires | unit | `pytest tests/jobs/test_scan_repo.py::test_slack_fires_on_webhook -x` | Wave 0 |
| WBH-02b | source='github' + Critical → no Slack | unit | `pytest tests/jobs/test_scan_repo.py::test_slack_no_fire_github_source -x` | Wave 0 |
| WBH-02c | source='webhook' + 0 Critical → no Slack | unit | `pytest tests/jobs/test_scan_repo.py::test_slack_no_fire_no_critical -x` | Wave 0 |
| WBH-02d | slack_webhook_url NULL → no Slack | unit | `pytest tests/jobs/test_scan_repo.py::test_slack_no_fire_null_url -x` | Wave 0 |
| WBH-02e | Slack HTTP failure → scan still succeeds | unit | `pytest tests/jobs/test_scan_repo.py::test_slack_failure_no_reraise -x` | Wave 0 |
| WBH-03a | Migration 009 upgrade/downgrade | integration | `pytest tests/test_migrations.py -x -m rls` | Wave 0 |
| WBH-03b | PATCH valid URL → 200 | integration (rls) | `pytest tests/api/test_integrations_slack.py::test_valid_url_saves -x -m rls` | Wave 0 |
| WBH-03c | PATCH invalid URL → 422 | unit | `pytest tests/api/test_integrations_slack.py::test_invalid_url_rejected -x` | Wave 0 |
| WBH-03d | Dashboard Slack form submit | unit | `npx vitest run __tests__/settings-integrations-page.test.tsx` | Wave 0 |
| WBH-03e | Auto-scan badge source=webhook | unit | `npx vitest run __tests__/scans-table.test.tsx` | Wave 0 |
| WBH-03f | MetadataHeader auto-scan badge | unit | `npx vitest run __tests__/metadata-header.test.tsx` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/api/test_github_webhook.py -x && npx vitest run __tests__/scans-table.test.tsx __tests__/metadata-header.test.tsx`
- **Per wave merge:** `pytest && npx vitest run`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps (files that must be created before implementation)
- [ ] `backend/tests/api/test_github_webhook.py` — WBH-01 a-e tests
- [ ] `backend/tests/api/test_integrations_slack.py` — WBH-03 b-c tests
- [ ] `backend/tests/jobs/test_scan_repo.py` — extend existing file with WBH-02 a-e tests (file exists, add new test functions)
- [ ] `dashboard/__tests__/settings-integrations-page.test.tsx` — extend existing file with Slack form tests (file exists, add new describe block)
- [ ] `dashboard/__tests__/metadata-header.test.tsx` — extend existing file with auto-scan badge test (file exists, add new test)

---

## Open Questions

### OQ-01: Team ID resolution mechanism for webhook handler
**What we know:** The webhook arrives without Clerk auth. `github_installations.team_id` must be resolved from `github_installation_id`. The table has RLS requiring `app.current_team_id` GUC — a bootstrapping problem.

**What's unclear:** Does a `team_id_for_installation()` SECURITY DEFINER function already exist, or does migration 009 need to create it? Migration 004 (`scan_team_id()`) covers the CLI scan path. Searching migration 007 (`github_installations`) would confirm whether such a helper was already added.

**Recommendation:** Planner should read migration 007 to confirm. If no such function exists, add it to migration 009. The function signature: `CREATE FUNCTION team_id_for_installation(install_id BIGINT) RETURNS UUID LANGUAGE sql SECURITY DEFINER STABLE AS $$ SELECT team_id FROM github_installations WHERE github_installation_id = install_id LIMIT 1; $$`.

**Alternative:** If a SECURITY DEFINER function is undesirable, the webhook handler could use the `database_url_migrator` (BYPASSRLS) connection — but this violates the principle of least privilege and the pattern established by D-02.

### OQ-02: Unknown installation_id handling
**What we know:** If a push arrives for an installation that isn't in `github_installations` (e.g., the install-callback webhook hasn't processed yet, or the installation was deleted), the team lookup returns NULL.

**What's unclear:** Should this return 200 OK (swallow) or 404/500?

**Recommendation:** Return 200 OK with a structured log warning `github_webhook.installation_not_found`. Returning non-2xx causes GitHub to mark the delivery as failed and retry — which is undesirable for a data inconsistency.

### OQ-03: `'github'` source display gap in ScansTable
**What we know:** `SourceCell` has branches for `'cli'`, `'manual'`, `'github_webhook'` (dead code). Manual GitHub scans set `source='github'`. None of the branches match `'github'` — it falls to the `—` fallback.

**What's unclear:** Is this intentional (Phase 7.5 oversight) or out of scope for Phase 8?

**Recommendation:** Out of scope per CONTEXT.md. Phase 8 only adds `'webhook'`. Flag as a follow-up.

---

## Environment Availability

| Dependency | Required By | Available | Notes |
|------------|------------|-----------|-------|
| Python 3.12 | Backend webhook handler | Confirmed (pyproject.toml) | `hmac`, `hashlib` stdlib — no new install |
| `httpx` | Slack POST in scan_repo | Confirmed (backend deps) | Already used in `scans_from_github.py`; add import to `scan_repo.py` |
| `respx` | Slack HTTP mock in tests | Confirmed (test deps, used in GitHub client tests) | `pip install respx` already done |
| Alembic | Migration 009 | Confirmed (migrations/ exists, 008 is head) | `alembic revision` + `alembic upgrade head` |
| Vitest | Dashboard badge tests | Confirmed (vitest 4.1.4) | Existing test infra covers this |
| GitHub App webhook secret | Webhook HMAC verify | Confirmed (settings.py line 49, defaults to `""`) | Fly secret `GITHUB_APP_WEBHOOK_SECRET` must be set in dev + prod |

**Missing dependencies with no fallback:** None — all required tools are present.

**Fly secret required before end-to-end test:** `GITHUB_APP_WEBHOOK_SECRET` must be set via `fly secrets set GITHUB_APP_WEBHOOK_SECRET=...` in both dev and prod environments before the webhook handler can accept live GitHub traffic.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (webhook auth) | HMAC-SHA256 `hmac.compare_digest` — constant-time, no timing leak |
| V3 Session Management | no | Webhook is sessionless |
| V4 Access Control | yes | SET LOCAL GUC before DB write; team isolation via RLS |
| V5 Input Validation | yes | URL prefix validation for Slack (`https://hooks.slack.com/`); Pydantic body schema on PATCH |
| V6 Cryptography | yes (HMAC) | `hashlib.sha256` via stdlib — never hand-rolled |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Forged GitHub push payload | Spoofing | HMAC-SHA256 verify before any payload parse (raw body discipline) |
| Empty webhook secret accepting all payloads | Tampering | Startup guard: 500 if secret is empty when webhook arrives |
| SSRF via arbitrary Slack URL | Spoofing | `https://hooks.slack.com/` prefix validation on PATCH |
| Cross-team installation_id abuse | Elevation | RLS + SECURITY DEFINER lookup; team_id resolved from DB, not from payload |
| Replay attack (redelivered `X-GitHub-Delivery`) | Repudiation | Accepted (D-08): duplicate rows, no data corruption, user-visible in history |

---

## Sources

### Primary (HIGH confidence — verified against codebase)
- `backend/app/routes/webhooks.py` — raw-bytes pattern, router structure
- `backend/app/queue/tasks/scan_repo.py` — 7-kwarg signature, session pattern, `_extract_summary`, failure handling
- `backend/app/settings.py` — `github_app_webhook_secret` field (line 49)
- `backend/app/db/models.py` — `Team` and `Scan` ORM, `scans.source` as plain TEXT
- `backend/app/services/scans.py` — `finalize_scan` returns None, session contract
- `backend/app/routes/scans_from_github.py` — dispatch pattern, SET LOCAL GUC, lazy import, enqueue shape
- `backend/migrations/versions/20260503_008_scan_github_columns.py` — migration file pattern
- `dashboard/app/(dashboard)/settings/integrations/page.tsx` — Slack stub at lines 100-131
- `dashboard/components/scans/ScansTable.tsx` — `SourceCell` with `'github_webhook'` dead branch
- `dashboard/components/scans/MetadataHeader.tsx` — no source badge currently
- `backend/app/main.py` — router registration, no integrations router yet
- `backend/tests/test_webhooks.py` — `_signed_headers` helper, `app_with_pg` fixture pattern
- `backend/tests/api/conftest.py` — `app_client`, `auth_headers_factory`, `team_a` fixture patterns
- `backend/tests/jobs/test_scan_repo.py` — `_FakeProc`, `_exec_factory` patterns for subprocess mocking
- `dashboard/__tests__/settings-integrations-page.test.tsx` — `makeFetchMock`, `vi.stubGlobal` pattern
- `dashboard/__tests__/scans-table.test.tsx` — `makeScan` factory, test structure
- `dashboard/lib/backend.ts` — `backendFetch` utility

### Tertiary (LOW confidence — architectural inference)
- Team ID resolution bootstrapping problem: inferred from RLS model + missing `team_id_for_installation` function. Needs verification against migration 007 content. [ASSUMED that the function does not yet exist — planner should verify]

---

## Metadata

**Confidence breakdown:**
- Webhook HMAC pattern: HIGH — verified against existing Clerk handler and Python stdlib
- scan_repo Slack tail: HIGH — existing function fully read; insertion point clear
- Migration 009: HIGH — pattern verified against 008
- Dashboard proxy + form: HIGH — pattern verified against existing `from-github/route.ts`
- Dashboard badge: HIGH — SourceCell and MetadataHeader fully read
- Team ID resolution: MEDIUM — bootstrapping problem identified; specific solution (SECURITY DEFINER function) is [ASSUMED] pending migration 007 read

**Research date:** 2026-05-05
**Valid until:** 2026-06-05 (stable backend patterns; Slack API shape is stable)
