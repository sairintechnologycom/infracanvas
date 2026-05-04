"""POST /v1/scans/from-github — Phase 7.5 D-10e + D-13.

Single-handler module mounted under ``prefix="/v1/scans"`` so the URL is
``/v1/scans/from-github``. Lives in its own module per PATTERNS CC-13
recommendation — ``app/routes/scans.py`` is already 600+ lines and a
fifth large endpoint there would push past clean separation.

Auth gate:

* ``require_role("owner", "admin", "member")`` — basic_member is
  excluded for this endpoint (T-07.5-05-06): a basic_member trigger
  would fire a Stripe meter event the role isn't authorised to incur.
  Mirrors the ``commit_scan`` role list in ``app/routes/scans.py`` so
  the two billing-meterable surfaces stay symmetric.

Flow:

1. Membership check — RLS-scoped lookup against ``github_installations``
   rejects cross-team installation_ids (T-07.5-05-02 mitigation) BEFORE
   the GitHub call. One DB roundtrip is much cheaper than burning a
   GitHub rate-limit token + an installation-token mint.
2. Resolve HEAD sha via ``get_head_sha`` (one GitHub call). 404 →
   surface as 404 ``branch_not_found`` so the dashboard can prompt the
   user to pick a different branch.
3. INSERT pending scans row with the github_* provenance columns. UUIDv7
   for the scan_id (lexically chronological — list-order friendly).
4. Lazy import + enqueue ``scan_repo`` taskiq job (CC-4 dispatch shape).
   Lazy because Plan 06 (scan_repo) hasn't landed yet — the route still
   needs to compile and the import error would otherwise be fatal at
   module-load. Tests stub the import via ``sys.modules`` registration.
5. On enqueue failure: flip the just-inserted row pending → failed with
   ``error_message='enqueue_failed'`` so the polling page (Plan 11)
   surfaces the failure rather than spinning indefinitely on a pending
   row that nothing will ever pick up. Then 503 ``enqueue_failed``.

Threat model dispositions handled inline:

* T-07.5-05-01 (path/repo tampering) — Pydantic strict regex on ``repo``
  + max_length=1024 on ``path`` (Plan 03 schema).
* T-07.5-05-02 (cross-team install_id) — membership check at step 1.
* T-07.5-05-03 (DoS via rapid clicks) — accepted; Stripe meter is the
  cost ceiling.
* T-07.5-05-04 (path traversal) — bounded here by max_length; the
  resolve-and-startswith check is the worker's job (Plan 06).
* T-07.5-05-05 (orphan pending leak) — accepted; only visible to caller.
* T-07.5-05-06 (basic_member elevation) — excluded from role list.
"""
from __future__ import annotations

from uuid import UUID

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text

from app.auth.clerk import ClerkPrincipal, require_role
from app.auth.deps import resolve_team_from_clerk_org
from app.db.models import Team
from app.db.session import get_sessionmaker
from app.integrations.github.client import get_head_sha
from app.schemas.github import ScanFromGitHubReq, ScanFromGitHubResp
from app.util.ids import new_uuid7

router = APIRouter(prefix="/v1/scans", tags=["scans"])
_log = structlog.get_logger("app.scans_from_github")

# Same role list as ``commit_scan`` — basic_member excluded since the
# endpoint causes a billing-meter event downstream (T-07.5-05-06).
_WRITE_ROLES = ("owner", "admin", "member")


@router.post("/from-github", response_model=ScanFromGitHubResp)
async def scan_from_github_endpoint(
    body: ScanFromGitHubReq,
    principal: ClerkPrincipal = Depends(  # noqa: B008
        require_role(*_WRITE_ROLES)
    ),
    team: Team = Depends(resolve_team_from_clerk_org),  # noqa: B008
) -> ScanFromGitHubResp:
    """Trigger a GitHub-sourced scan: resolve HEAD, insert pending row, enqueue."""
    sm = get_sessionmaker()

    # 1. Membership probe — the installation must belong to the caller's
    # team. Done in its own short tx so the connection isn't held across
    # the (slower) GitHub call below.
    async with sm() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team.id)},
        )
        found = await session.execute(
            text(
                "SELECT 1 FROM github_installations "
                "WHERE github_installation_id = :iid"
            ),
            {"iid": body.installation_id},
        )
        if found.scalar_one_or_none() is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "installation_not_found"
            )

    # 2. Resolve HEAD sha (one GitHub API call). 404 → branch_not_found.
    try:
        sha = await get_head_sha(body.installation_id, body.repo, body.branch)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"branch_not_found:{body.repo}@{body.branch}",
            ) from e
        raise

    # 3. INSERT pending scans row with github_* provenance.
    scan_id: UUID = new_uuid7()
    async with sm() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team.id)},
        )
        await session.execute(
            text(
                """
                INSERT INTO scans (
                    id, team_id, r2_key, status, source, source_path,
                    github_installation_id, github_repo, github_branch,
                    github_sha
                ) VALUES (
                    :id, :team_id, '', 'pending', 'github', :path,
                    :iid, :repo, :branch, :sha
                )
                """
            ),
            {
                "id": str(scan_id),
                "team_id": str(team.id),
                "path": body.path,
                "iid": body.installation_id,
                "repo": body.repo,
                "branch": body.branch,
                "sha": sha,
            },
        )

    # 4. Lazy import + enqueue (CC-4 dispatch shape).
    # Import is deferred so this module compiles before Plan 06 lands
    # ``app.queue.tasks.scan_repo``. Tests stub the import via sys.modules.
    try:
        from app.queue.tasks.scan_repo import (  # type: ignore[import-not-found,import-untyped,unused-ignore]
            scan_repo,
        )

        rid = structlog.contextvars.get_contextvars().get("request_id", "")
        await (
            scan_repo.kicker()
            .with_labels(request_id=rid)
            .kiq(
                scan_id=str(scan_id),
                installation_id=body.installation_id,
                repo=body.repo,
                branch=body.branch,
                sha=sha,
                path=body.path,
                team_id=str(team.id),
            )
        )
    except Exception as e:  # noqa: BLE001 — must not orphan pending row
        _log.error(
            "scan_from_github.enqueue_failed",
            scan_id=str(scan_id),
            error=repr(e),
        )
        # Flip pending → failed so the polling page surfaces the error.
        # Best-effort: if even THIS update fails the row is left pending,
        # but the 503 still informs the client. Lifecycle reconciler is
        # the long-term backstop.
        async with sm() as session, session.begin():
            await session.execute(
                text("SELECT set_config('app.current_team_id', :t, true)"),
                {"t": str(team.id)},
            )
            await session.execute(
                text(
                    "UPDATE scans SET status='failed', "
                    "error_message='enqueue_failed' "
                    "WHERE id = :id AND status = 'pending'"
                ),
                {"id": str(scan_id)},
            )
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "enqueue_failed"
        ) from e

    _log.info(
        "scan_from_github.enqueued",
        scan_id=str(scan_id),
        team_id=str(team.id),
        installation_id=body.installation_id,
        repo=body.repo,
        branch=body.branch,
        sha=sha,
    )
    return ScanFromGitHubResp(scan_id=scan_id)
