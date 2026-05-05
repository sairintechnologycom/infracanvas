# Phase 8: GitHub Webhook + Auto-scan — Pattern Map

**Mapped:** 2026-05-05
**Files analyzed:** 14 (6 backend new/modified, 3 backend new tests, 2 dashboard new, 3 dashboard modified)
**Analogs found:** 14 / 14

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/app/routes/webhooks.py` (modify) | route/handler | request-response | itself (Clerk handler, lines 1-41) | exact — extend same file |
| `backend/migrations/versions/20260505_009_teams_slack_webhook.py` | migration | — | `20260503_008_scan_github_columns.py` | exact |
| `backend/app/db/models.py` (modify) | model | — | itself — `Team` class lines 27-44 | exact — same class |
| `backend/app/queue/tasks/scan_repo.py` (modify) | job/worker | event-driven | itself — tail of happy path lines 281-297 | exact — append after success log |
| `backend/app/routes/integrations.py` (new) | route | request-response | `backend/app/routes/scans_from_github.py` | role-match |
| `backend/app/main.py` (modify) | config/factory | — | itself lines 20-46 | exact — add one import + include_router |
| `backend/tests/api/test_github_webhook.py` (new) | test | request-response | `backend/tests/api/test_scans_from_github.py` | role-match |
| `backend/tests/api/test_integrations_slack.py` (new) | test | request-response | `backend/tests/api/test_scans_from_github.py` | role-match |
| `backend/tests/jobs/test_scan_repo.py` (modify) | test | event-driven | itself (existing file) | exact — extend existing |
| `dashboard/app/api/integrations/slack/route.ts` (new) | proxy route | request-response | `dashboard/app/api/scans/from-github/route.ts` | exact |
| `dashboard/components/integrations/SlackWebhookForm.tsx` (new) | component | request-response | inline form in `integrations/page.tsx` lines 109-131 | role-match |
| `dashboard/app/(dashboard)/settings/integrations/page.tsx` (modify) | page/component | request-response | itself lines 109-131 (Slack stub) | exact — replace TODO |
| `dashboard/components/scans/ScansTable.tsx` (modify) | component | — | itself — `SourceCell` lines 31-57 | exact — add branch |
| `dashboard/components/scans/MetadataHeader.tsx` (modify) | component | — | itself — inline badge pattern lines 83-107 | exact — insert span |

---

## Pattern Assignments

### `backend/app/routes/webhooks.py` — GitHub webhook handler (extend)

**Analog:** `backend/app/routes/webhooks.py` (Clerk handler, lines 1-41) — add a new `@router.post("/github")` function to the same file.

**Imports pattern to add** (insert after existing imports at top):
```python
import hashlib
import hmac
import json as _json

import structlog
from fastapi import HTTPException, status

from app.settings import settings
from app.util.ids import new_uuid7
```

**Raw-bytes discipline** (lines 28 — the locked pattern, NEVER deviate):
```python
body = await request.body()  # RAW BYTES — never .json() (RESEARCH § F2)
```

**HMAC verify pattern** (GitHub uses X-Hub-Signature-256, not Svix):
```python
# Guard: unconfigured secret would pass HMAC for any payload (L-02)
if not settings.github_app_webhook_secret:
    log.error("github_webhook.secret_not_configured")
    raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "webhook_secret_not_configured")

sig_header = request.headers.get("X-Hub-Signature-256", "")
expected = "sha256=" + hmac.new(
    settings.github_app_webhook_secret.encode(),  # str → bytes (L-08)
    body,
    hashlib.sha256,
).hexdigest()
if not hmac.compare_digest(sig_header, expected):
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bad_signature")
```

**Event swallow pattern** (mirrors Clerk handler's "unknown event = 200" discipline, D-03 + L-09):
```python
event = request.headers.get("X-GitHub-Event", "")
if event == "ping":
    return {"ok": True}
if event != "push":
    return {"ok": True}
```

**Post-verify JSON parse** (ALWAYS after HMAC, NEVER before):
```python
try:
    payload = _json.loads(body)
except _json.JSONDecodeError as e:
    raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid_json") from e
```

**Push filtering** (D-01, D-03):
```python
# Deleted-branch guard (D-03)
if payload.get("deleted") is True or payload.get("after") == "0" * 40:
    return {"ok": True}

# Default-branch filter (D-01) — use payload field directly, avoids DB read
ref = payload.get("ref", "")
default_branch = payload.get("repository", {}).get("default_branch", "")
if ref != f"refs/heads/{default_branch}":
    return {"ok": True}
```

**DB INSERT pattern** (copy from `scans_from_github.py` lines 117-144, use `source='webhook'`):
```python
scan_id = new_uuid7()
sm = get_sessionmaker()
async with sm() as session, session.begin():
    await session.execute(
        text("SELECT set_config('app.current_team_id', :t, true)"),
        {"t": str(team_id)},
    )
    await session.execute(
        text("""
            INSERT INTO scans (
                id, team_id, r2_key, status, source,
                github_installation_id, github_repo, github_branch, github_sha
            ) VALUES (
                :id, :team_id, '', 'pending', 'webhook',
                :iid, :repo, :branch, :sha
            )
        """),
        {"id": str(scan_id), "team_id": str(team_id), "iid": installation_id,
         "repo": repo, "branch": branch, "sha": sha},
    )
```

**Taskiq dispatch pattern** (copy from `scans_from_github.py` lines 149-167, use `path='.'`):
```python
try:
    from app.queue.tasks.scan_repo import scan_repo  # lazy import — L-10
    rid = structlog.contextvars.get_contextvars().get("request_id", "")
    await (
        scan_repo.kicker()
        .with_labels(request_id=rid)
        .kiq(
            scan_id=str(scan_id),
            installation_id=installation_id,
            repo=repo,
            branch=branch,
            sha=sha,
            path=".",        # webhook scans always scan root (Phase 8 scope, L-04)
            team_id=str(team_id),
        )
    )
except Exception as e:  # noqa: BLE001
    _log.error("github_webhook.enqueue_failed", scan_id=str(scan_id), error=repr(e))
    raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "enqueue_failed") from e
```

**Team ID resolution note (L-03):** The webhook carries `installation.id` but not `team_id`. Migration 009 must add a `SECURITY DEFINER` function `team_id_for_installation(bigint) RETURNS uuid` (same pattern as `scan_team_id()` in migration 004). The handler calls this via `raw_session` before setting the GUC. Example query (raw, no GUC needed since SECURITY DEFINER):
```python
result = await session.execute(
    text("SELECT team_id_for_installation(:iid)"),
    {"iid": installation_id},
)
team_id = result.scalar_one_or_none()
if team_id is None:
    return {"ok": True}  # unknown installation — swallow (not an error)
```

---

### `backend/migrations/versions/20260505_009_teams_slack_webhook.py` (new)

**Analog:** `backend/migrations/versions/20260503_008_scan_github_columns.py`

**Full file structure** (copy header verbatim, adjust revision/content):
```python
"""teams.slack_webhook_url + team_id_for_installation() SECURITY DEFINER.

Revision ID: 009_teams_slack_webhook
Revises: 008_scan_github_columns
Create Date: 2026-05-05
...
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_teams_slack_webhook"
down_revision: Union[str, None] = "008_scan_github_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("teams", sa.Column("slack_webhook_url", sa.Text(), nullable=True))
    # SECURITY DEFINER helper: webhook handler resolves team_id from
    # github_installation_id without knowing team context (L-03 / RESEARCH).
    op.execute("""
        CREATE OR REPLACE FUNCTION team_id_for_installation(p_iid bigint)
        RETURNS uuid
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public
        AS $$
            SELECT team_id
            FROM github_installations
            WHERE github_installation_id = p_iid
            LIMIT 1;
        $$;
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS team_id_for_installation(bigint)")
    op.drop_column("teams", "slack_webhook_url")
```

**Key conventions from migration 008** (lines 33-43):
- `from __future__ import annotations` first
- `from typing import Sequence, Union` for revision type annotations
- `revision`, `down_revision`, `branch_labels`, `depends_on` as module-level vars
- `upgrade()` / `downgrade()` as plain functions (no class)

---

### `backend/app/db/models.py` — Team model (modify)

**Analog:** `backend/app/db/models.py` lines 27-44 — `Team` class. `stripe_customer_id` is the exact pattern for a nullable Text column.

**Column to add** (after `stripe_customer_id` line 35, same pattern):
```python
stripe_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
# ADD:
slack_webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
```

**Import already present:** `Text` is already imported at line 13: `from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Text, func`

**ScanSource enum/constant** — `Scan.source` is `Mapped[str | None]` (line 68, plain TEXT). No Postgres enum. Add `webhook = "webhook"` to wherever `'github'` and `'cli'` are defined as Python constants (search codebase for `ScanSource` or `'github'` literal usage).

---

### `backend/app/queue/tasks/scan_repo.py` — Slack tail (modify)

**Analog:** `backend/app/queue/tasks/scan_repo.py` itself — insert after `log_ctx.info("scan_repo.success", ...)` at line 292, before the `except Exception` at line 299.

**What to extend in the session block** (lines 261-290): Extend the SELECT at line 271 to also fetch `source` from the `scans` row and `slack_webhook_url` from `teams`:

```python
# Extend existing SELECT (lines 268-276) to join scans for source:
team_row = (
    await session.execute(
        text(
            "SELECT t.id, t.stripe_customer_id, t.slack_webhook_url, s.source "
            "FROM teams t, scans s "
            "WHERE t.id = :team_id AND s.id = :scan_id"
        ),
        {"team_id": team_id, "scan_id": scan_id},
    )
).one_or_none()
stripe_customer_id = team_row.stripe_customer_id if team_row is not None else ""
slack_webhook_url = team_row.slack_webhook_url if team_row is not None else None
scan_source = team_row.source if team_row is not None else None
```

**Slack fire block** (insert between `log_ctx.info("scan_repo.success", ...)` and `except Exception` — lines 292-299):
```python
import httpx  # add to top-level imports

# Slack alert: only for webhook-sourced scans with ≥1 Critical (D-06)
critical_count = (summary_json or {}).get("findings", {}).get("critical", 0)
if scan_source == "webhook" and slack_webhook_url and critical_count >= 1:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:  # L-07: 5s cap
            resp = await client.post(
                slack_webhook_url,
                json={
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": (
                                    f"*InfraCanvas Alert* — `{repo}` `{branch}` "
                                    f"`{sha[:7]}`\n"
                                    f"*{critical_count} Critical* finding(s) detected.\n"
                                    f"<https://infracanvas.app/scans/{scan_id}|View scan>"
                                ),
                            },
                        }
                    ]
                },
            )
            resp.raise_for_status()
        log_ctx.info("scan_repo.slack_notified", slack_notified=True)
    except Exception as slack_exc:  # noqa: BLE001
        log_ctx.warning("scan_repo.slack_failed", error=repr(slack_exc))
        sentry_sdk.capture_exception(slack_exc)
        # DO NOT raise — scan is already ready; Slack is best-effort
```

**`summary_json` availability:** Already computed at line 249 (`summary_json = _extract_summary(payload_bytes)`) — in scope when the Slack block runs. No extra DB read needed for the count (L-06).

**structlog bind pattern** (from lines 125-132 — add `slack_notified` tag to existing bind):
```python
log_ctx = _log.bind(
    scan_id=scan_id,
    team_id=team_id,
    ...
    # slack_notified added dynamically in the Slack block above
)
```

---

### `backend/app/routes/integrations.py` (new)

**Analog:** `backend/app/routes/scans_from_github.py` — same module shape: single-handler file, `APIRouter`, auth gate via `require_role`, structlog, `get_sessionmaker`, `text()` queries with SET LOCAL GUC.

**Imports pattern** (from `scans_from_github.py` lines 48-66):
```python
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text

from app.auth.clerk import ClerkPrincipal, require_role
from app.auth.deps import resolve_team_from_clerk_org
from app.db.models import Team
from app.db.session import get_sessionmaker

router = APIRouter(prefix="/v1/integrations", tags=["integrations"])
_log = structlog.get_logger("app.integrations")
```

**Request body schema** (Pydantic, same style as `ScanFromGitHubReq`):
```python
class SlackWebhookReq(BaseModel):
    webhook_url: str
```

**SSRF validation + SET LOCAL GUC + UPDATE pattern** (SET LOCAL pattern from `scans_from_github.py` lines 87-100):
```python
@router.patch("/slack", status_code=200)
async def patch_slack_webhook(
    body: SlackWebhookReq,
    principal: ClerkPrincipal = Depends(require_role("owner", "admin")),  # noqa: B008
    team: Team = Depends(resolve_team_from_clerk_org),  # noqa: B008
) -> dict[str, str]:
    if not body.webhook_url.startswith("https://hooks.slack.com/"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_slack_url")

    sm = get_sessionmaker()
    async with sm() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team.id)},
        )
        await session.execute(
            text("UPDATE teams SET slack_webhook_url = :url WHERE id = :id"),
            {"url": body.webhook_url, "id": str(team.id)},
        )

    _log.info("integrations.slack_saved", team_id=str(team.id))
    return {"message": "Slack webhook saved"}
```

---

### `backend/app/main.py` — register integrations router (modify)

**Analog:** `backend/app/main.py` lines 20-45 — existing router registration block.

**Import to add** (after line 24 `from app.routes import webhooks as wh_routes`):
```python
from app.routes import integrations as integrations_routes
```

**Router registration** (after `app.include_router(scans_from_github.router)` line 45):
```python
app.include_router(integrations_routes.router)
```

---

### `backend/tests/api/test_github_webhook.py` (new)

**Analog:** `backend/tests/api/test_scans_from_github.py` — same test structure: `pytestmark = pytest.mark.rls`, `_seed_install` helper, `_RecordingKicker` stub, monkeypatch for taskiq.

**HMAC signing helper** (unique to this test, based on RESEARCH § Test Patterns):
```python
import hashlib
import hmac as _hmac

SECRET = "test-webhook-secret-abc"

def _gh_signed_headers(body: bytes, secret: str = SECRET, event: str = "push") -> dict[str, str]:
    digest = _hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return {
        "X-Hub-Signature-256": f"sha256={digest}",
        "X-GitHub-Event": event,
        "Content-Type": "application/json",
    }
```

**Settings monkeypatch** (standard across all API tests, from conftest pattern):
```python
monkeypatch.setattr(settings, "github_app_webhook_secret", SECRET)
```

**Stateless tests** (HMAC/ping/filter checks): use `app_client.post("/v1/webhooks/github", ...)` directly — no DB needed. Only happy-path dispatch test needs `seed_session` for the `github_installations` row.

**Existing test patterns to copy from `test_scans_from_github.py`:**
- `pytestmark = pytest.mark.rls` (line 48)
- `_seed_install(seed_session, team_id, install_id=...)` helper (lines 56-71)
- `_RecordingKicker` stub class (lines 74+) for capturing kiq() calls without real taskiq

---

### `backend/tests/api/test_integrations_slack.py` (new)

**Analog:** `backend/tests/api/test_scans_from_github.py` — same conftest fixtures (`app_client`, `auth_headers_factory`, `team_a`, `seed_session`).

**Test structure** (three tests from RESEARCH § Test Patterns):
```python
pytestmark = pytest.mark.rls

def test_valid_url_saves(app_client, auth_headers_factory, team_a):
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

---

### `backend/tests/jobs/test_scan_repo.py` — Slack tests (extend)

**Analog:** The existing `test_scan_repo.py` file. The `_exec_factory` / `_FakeProc` subprocess mock approach is the established pattern — extend the happy-path fixture with respx Slack mocks on top.

**Import to add** at top of existing test file:
```python
import respx
import httpx
```

**Five new test functions** (one per WBH-02 requirement from RESEARCH § Test Patterns):
```python
@pytest.mark.anyio
async def test_slack_fires_on_webhook_source_with_critical(...):
    with respx.mock:
        slack_route = respx.post("https://hooks.slack.com/test").mock(
            return_value=httpx.Response(200)
        )
        await scan_repo(scan_id=..., ...)
        assert slack_route.called

@pytest.mark.anyio
async def test_slack_failure_does_not_fail_scan(...):
    # Slack POST raises httpx.ConnectError → scan result is still 'ready'
    # Assert: no exception raised from scan_repo itself
```

---

### `dashboard/app/api/integrations/slack/route.ts` (new)

**Analog:** `dashboard/app/api/scans/from-github/route.ts` — exact same proxy pattern.

**Full file** (copy structure from analog, lines 1-37):
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

**Status mapping differences from `from-github/route.ts`:** PATCH/slack maps `422` (invalid URL) and `401` (unauth). The from-github analog maps `404`, `422`, `503`. Adjust the array accordingly.

---

### `dashboard/components/integrations/SlackWebhookForm.tsx` (new)

**Analog:** Inline Slack stub form in `dashboard/app/(dashboard)/settings/integrations/page.tsx` lines 109-131 — extract and enhance with live state.

**Pattern from `ScanTriggerForm`** (existing client component in `dashboard/components/integrations/ScanTriggerForm.tsx`) for the fetch + state shape:
- `useState` for `saving`, `saved`, `error`
- `fetch('/api/integrations/slack', { method: 'PATCH', body: JSON.stringify({...}) })`
- `form onSubmit` handler with `e.preventDefault()`

**Component structure:**
```tsx
'use client'
import { useState } from 'react'

export function SlackWebhookForm() {
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const data = new FormData(e.currentTarget)
    const webhook_url = data.get('slack_webhook') as string
    setSaving(true)
    setSaved(false)
    setError(null)
    try {
      const res = await fetch('/api/integrations/slack', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ webhook_url }),
      })
      if (!res.ok) {
        const j = await res.json()
        setError(j.error ?? 'save_failed')
      } else {
        setSaved(true)
      }
    } catch {
      setError('network_error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="flex items-center gap-2 mt-3" onSubmit={handleSubmit}>
      <input
        type="url"
        name="slack_webhook"
        placeholder="https://hooks.slack.com/..."
        className="flex-1 border border-slate-200 rounded-md px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-400"
        required
      />
      <button
        type="submit"
        disabled={saving}
        className="border border-slate-300 hover:bg-slate-50 text-slate-900 text-sm font-medium px-3 py-2 rounded-md transition-colors disabled:opacity-50"
      >
        {saving ? 'Saving…' : 'Save webhook URL'}
      </button>
      {saved && <span className="text-xs text-green-600">Saved</span>}
      {error && <span className="text-xs text-red-600" role="alert">{error}</span>}
    </form>
  )
}
```

---

### `dashboard/app/(dashboard)/settings/integrations/page.tsx` — wire Slack form (modify)

**Analog:** itself — lines 109-131 (the existing Slack stub). Replace the inline form with `<SlackWebhookForm />`.

**Import to add** (after existing imports at lines 2-8):
```tsx
import { SlackWebhookForm } from '@/components/integrations/SlackWebhookForm'
```

**Replace** lines 109-131 (the `<form ... onSubmit TODO>` block) with:
```tsx
<SlackWebhookForm />
```

The surrounding Slack card `<div>` (lines 101-131) structure stays intact — only the inner form is replaced.

---

### `dashboard/components/scans/ScansTable.tsx` — Auto-scan badge (modify)

**Analog:** itself — `SourceCell` component lines 31-57. Add a fourth branch for `source === 'webhook'` before the fallback.

**Import to add** (`Zap` icon, alongside existing `Terminal`, `Upload`):
```tsx
import { Terminal, Upload, Zap } from 'lucide-react'
```

**New branch** (insert after line 55 `if (source === 'github_webhook') { ... }`, before the fallback `return`):
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

**Dead code note:** The existing `'github_webhook'` branch (lines 48-55) is dead code — Phase 7.5 uses `source='github'`, not `'github_webhook'`. Leave it in place for now (no data uses it, removing it is out of scope for Phase 8).

---

### `dashboard/components/scans/MetadataHeader.tsx` — Auto-scan badge (modify)

**Analog:** itself — the inline `findings` badge pattern at lines 83-107. Same conditional render pattern `{scan.X && (...)}`.

**No new import needed** — badge uses only Tailwind classes and no icons.

**Insert** after the `commit_sha` span (line 76) and before the `score` block (line 77):
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

**Type check:** `ScanGetResp` at `dashboard/lib/types.ts` must have `source?: string | null`. Verify — if absent, add it alongside `branch` and `commit_sha`. `ScanListItem` similarly needs `source?: string | null` (used by `ScansTable`).

---

## Shared Patterns

### SET LOCAL GUC before every team-scoped DB write
**Source:** `backend/app/routes/scans_from_github.py` lines 87-91 and `backend/app/queue/tasks/scan_repo.py` lines 264-267
**Apply to:** `integrations.py` PATCH handler, `webhooks.py` GitHub handler INSERT
```python
await session.execute(
    text("SELECT set_config('app.current_team_id', :t, true)"),
    {"t": str(team.id)},
)
```

### Structlog + Sentry tagging
**Source:** `backend/app/queue/tasks/scan_repo.py` lines 125-139
**Apply to:** `webhooks.py` GitHub handler, `integrations.py`
```python
log_ctx = _log.bind(scan_id=scan_id, team_id=team_id, repo=repo, branch=branch)
sentry_sdk.set_tag("scan_id", scan_id)
sentry_sdk.set_tag("team_id", team_id)
```

### Error handling — best-effort best practices
**Source:** `backend/app/queue/tasks/scan_repo.py` lines 299-335
**Apply to:** Slack fire block in `scan_repo.py` — catch, log, `sentry_sdk.capture_exception`, do NOT re-raise after scan is committed.
```python
except Exception as slack_exc:  # noqa: BLE001
    log_ctx.warning("scan_repo.slack_failed", error=repr(slack_exc))
    sentry_sdk.capture_exception(slack_exc)
    # DO NOT raise
```

### Dashboard proxy route shape
**Source:** `dashboard/app/api/scans/from-github/route.ts` lines 1-37
**Apply to:** `dashboard/app/api/integrations/slack/route.ts`
- `backendFetch<T>(path, { method, body })` wraps auth header forwarding
- `try/catch err instanceof Error ? err.message : '500'` for status extraction
- `NextResponse.json(data)` on success, `NextResponse.json({ error }, { status })` on failure

### Dashboard test fetch mock pattern
**Source:** `dashboard/__tests__/settings-integrations-page.test.tsx` lines 48-68
**Apply to:** `test_integrations_slack.test.tsx`, `scans-table.test.tsx` Slack badge tests
```typescript
function makeFetchMock(data: unknown, ok = true, status = 200) {
  return vi.fn().mockResolvedValue({ ok, status, json: async () => data })
}
vi.stubGlobal('fetch', makeFetchMock({ message: 'Slack webhook saved' }))
```

### Dynamic component import in Vitest tests
**Source:** `dashboard/__tests__/scans-table.test.tsx` lines 52-57
**Apply to:** All new dashboard component tests
```typescript
const { ScansTable } = await import('@/components/scans/ScansTable')
render(<ScansTable data={...} currentParams={{}} />)
```

---

## No Analog Found

All files have a close analog. No files fall into this category.

---

## Metadata

**Analog search scope:** `backend/app/routes/`, `backend/app/queue/tasks/`, `backend/migrations/versions/`, `backend/app/db/`, `backend/app/main.py`, `backend/tests/api/`, `backend/tests/jobs/`, `dashboard/app/api/`, `dashboard/components/scans/`, `dashboard/components/integrations/`, `dashboard/app/(dashboard)/settings/integrations/`, `dashboard/__tests__/`
**Files scanned:** 22
**Pattern extraction date:** 2026-05-05
