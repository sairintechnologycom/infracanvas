"""Clerk and GitHub webhook endpoints.

``POST /v1/webhooks/clerk`` reads the raw request body bytes (NEVER
deserializes via the parsed-JSON helper — Svix HMAC must verify the
byte-exact payload before any deserialisation, RESEARCH § F2 critical
pitfall) and forwards to :func:`app.auth.webhooks.verify_and_dispatch`.

Bad signature → 401 ``bad_signature``. Successful dispatch → 200
``{"ok": true}``. Unknown event types are also 200 (handler swallows them).

``POST /v1/webhooks/github`` verifies HMAC-SHA256 from the
``X-Hub-Signature-256`` header before touching any payload (returns HTTP
401 on mismatch), guards against unconfigured secret (returns HTTP 500),
filters out non-push events, ping events, deleted-branch pushes, and
non-default-branch pushes, sets the RLS GUC before INSERT, then creates a
``scans`` row with ``source='webhook'`` and enqueues the existing
``scan_repo`` 7-kwarg job.

Threat model (Phase 8 T-8-02-*):

* T-8-02-01: Forged payload — HMAC-SHA256 is the FIRST check.
* T-8-02-02: HMAC timing oracle — ``hmac.compare_digest`` (constant-time).
* T-8-02-03: Empty secret passes any HMAC — explicit guard → HTTP 500.
* T-8-02-04: Deleted-branch push — ``deleted`` or ``after==zeros`` → 200 no-op.
* T-8-02-05: Non-default-branch push — ``ref`` comparison → 200 no-op.
* T-8-02-06: Non-push event crashes with KeyError — explicit event check → 200.
* T-8-02-07: Unknown installation_id — ``team_id_for_installation`` returns
  NULL → HTTP 404 ``installation_not_found``.
* T-8-02-08: INSERT scans under RLS without GUC → ``set_config`` called
  inside ``session.begin()`` before INSERT.
"""

from __future__ import annotations

import hashlib
import hmac
import json

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.webhooks import verify_and_dispatch
from app.db.session import get_sessionmaker, raw_session
from app.settings import settings
from app.util.ids import new_uuid7

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])

_log_gh = structlog.get_logger("app.webhooks.github")


@router.post("/clerk", status_code=200)
async def clerk_webhook(
    request: Request,
    session: AsyncSession = Depends(raw_session),
) -> dict[str, bool]:
    body = await request.body()  # RAW BYTES — never .json() (RESEARCH § F2)
    headers = {
        "svix-id": request.headers.get("svix-id", ""),
        "svix-timestamp": request.headers.get("svix-timestamp", ""),
        "svix-signature": request.headers.get("svix-signature", ""),
    }
    try:
        await verify_and_dispatch(body, headers, session)
    except PermissionError as e:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "bad_signature"
        ) from e
    return {"ok": True}


@router.post("/github", status_code=200)
async def github_webhook(request: Request) -> dict[str, bool]:
    """GitHub App push webhook — HMAC verify, filter, dispatch scan_repo.

    Reads raw bytes BEFORE any JSON parsing — critical for HMAC integrity.
    See module docstring for full threat model.
    """
    body = await request.body()  # RAW BYTES — never .json() before HMAC verify

    # 0. Empty-secret guard (T-8-02-03)
    # hmac.new(b'', ...) accepts any payload signed with an empty key —
    # an attacker who knows the secret is empty can forge any payload.
    if not settings.github_app_webhook_secret:
        _log_gh.error("github_webhook.secret_not_configured")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "webhook_secret_not_configured"
        )

    # 1. HMAC-SHA256 verify (T-8-02-01, T-8-02-02)
    sig_header = request.headers.get("X-Hub-Signature-256", "")
    expected = "sha256=" + hmac.new(
        settings.github_app_webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(sig_header, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_signature")

    # 2. Ping event — GitHub sends this on webhook creation; always 200 OK
    event = request.headers.get("X-GitHub-Event", "")
    if event == "ping":
        return {"ok": True}

    # 3. Non-push event swallow (T-8-02-06)
    # Must be after HMAC verify but before json.loads to avoid KeyError crashes
    # on payloads that don't have the push-specific keys (ref, after, etc.).
    if event != "push":
        return {"ok": True}

    # 4. Parse payload (only after HMAC passes and event is push)
    payload: dict = json.loads(body)

    # 5. Deleted-branch filter (T-8-02-04)
    if payload.get("deleted") or payload.get("after") == "0" * 40:
        return {"ok": True}

    # 6. Non-default-branch filter (T-8-02-05)
    # Use repository.default_branch from the payload directly — avoids a
    # DB read and the field is authoritative from GitHub's perspective.
    repo_meta = payload["repository"]
    if payload["ref"] != f"refs/heads/{repo_meta['default_branch']}":
        return {"ok": True}

    # 7. Extract provenance fields
    installation_id: int = payload["installation"]["id"]
    repo: str = repo_meta["full_name"]
    branch: str = repo_meta["default_branch"]
    sha: str = payload["after"]

    log_ctx = _log_gh.bind(
        installation_id=installation_id,
        repo=repo,
        branch=branch,
        sha=sha[:8],
    )

    # 8. Resolve team_id via SECURITY DEFINER function (no RLS context yet).
    # The push payload carries installation_id but NOT team_id. The function
    # team_id_for_installation() bypasses RLS to resolve team_id from the
    # github_installations table (migration 009).
    sm = get_sessionmaker()
    scan_id = new_uuid7()
    async with sm() as session, session.begin():
        row = (
            await session.execute(
                text("SELECT team_id_for_installation(:iid)"),
                {"iid": installation_id},
            )
        ).scalar_one_or_none()
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "installation_not_found")
        team_id: str = str(row)

        # 9. Set RLS GUC before INSERT (T-8-02-08, Phase 6 D-02)
        # set_config() is the parameter-safe equivalent of SET LOCAL (asyncpg
        # wire protocol cannot bind parameters to SET LOCAL).
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": team_id},
        )

        # 10. INSERT scans row with source='webhook'
        await session.execute(
            text(
                """
                INSERT INTO scans (
                    id, team_id, r2_key, status, source, source_path,
                    github_installation_id, github_repo, github_branch, github_sha
                ) VALUES (
                    :id, :team_id, '', 'pending', 'webhook', '.',
                    :iid, :repo, :branch, :sha
                )
                """
            ),
            {
                "id": str(scan_id),
                "team_id": team_id,
                "iid": installation_id,
                "repo": repo,
                "branch": branch,
                "sha": sha,
            },
        )

    # 11. Enqueue scan_repo (lazy import — same pattern as scans_from_github.py)
    # Lazy import so this module compiles when scan_repo.py doesn't exist yet.
    try:
        from app.queue.tasks.scan_repo import scan_repo  # type: ignore[import-not-found,import-untyped,unused-ignore]  # noqa: PLC0415

        await (
            scan_repo.kicker()
            .with_labels(source="webhook")
            .kiq(
                scan_id=str(scan_id),
                installation_id=installation_id,
                repo=repo,
                branch=branch,
                sha=sha,
                path=".",
                team_id=team_id,
            )
        )
    except Exception as e:  # noqa: BLE001 — must not orphan pending row
        log_ctx.error("github_webhook.enqueue_failed", error=repr(e))
        async with sm() as session, session.begin():
            await session.execute(
                text("SELECT set_config('app.current_team_id', :t, true)"),
                {"t": team_id},
            )
            await session.execute(
                text(
                    "UPDATE scans SET status='failed', error_message='enqueue_failed' "
                    "WHERE id = :id AND status = 'pending'"
                ),
                {"id": str(scan_id)},
            )
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "enqueue_failed"
        ) from e

    log_ctx.info(
        "github_webhook.enqueued",
        scan_id=str(scan_id),
        team_id=team_id,
    )
    return {"ok": True}
