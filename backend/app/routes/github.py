"""GitHub repo discovery + install callback (Phase 7.5 D-10a..d).

Four endpoints under ``/v1/github/*``:

* ``GET  /v1/github/installations``  — D-10a — local DB pull, RLS-isolated.
* ``GET  /v1/github/repos``          — D-10b — proxy GitHub /installation/repositories
                                       with 60s Upstash cache.
* ``GET  /v1/github/branches``       — D-10c — proxy GitHub /repos/{o}/{n}/branches.
* ``GET  /v1/github/install-callback`` — D-10d — Clerk-authed redirect target;
                                          state==clerk_org_id CSRF guard +
                                          App-JWT install reverify + idempotent
                                          upsert into github_installations.

Auth posture:

* Read endpoints (CC-2) — full ``require_role(*read_roles)`` +
  ``resolve_team_from_clerk_org`` + ``set_config('app.current_team_id', :t, true)``
  inside a single transaction. RLS enforces tenant isolation in case the
  query somehow tries to read another team's row.
* Install-callback (CC-3) — ``require_principal`` + ``resolve_team_from_clerk_org``
  WITHOUT setting the team GUC for the state check (the check happens
  before any team-scoped DB access). After state validation, the upsert
  uses the standard team-scoped session pattern.

Rate-limit translation: GitHub 403/429 (rate limit / abuse detection)
surfaces as 503 ``github_rate_limited`` + ``Retry-After: 60``. Lets the
dashboard backoff cleanly without exposing raw GitHub status.
"""
from __future__ import annotations

import os

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select, text

from app.auth.clerk import ClerkPrincipal, require_principal, require_role
from app.auth.deps import resolve_team_from_clerk_org
from app.db.models import GithubInstallation, Team
from app.db.session import get_sessionmaker
from app.integrations.github.client import (
    get_installation_metadata,
    list_branches,
    list_installation_repos,
)
from app.schemas.github import BranchResp, InstallationResp, RepoResp

router = APIRouter(prefix="/v1/github", tags=["github"])
_log = structlog.get_logger("app.github")

_READ_ROLES = ("owner", "admin", "member", "basic_member")


def _dashboard_url() -> str:
    """Resolve the dashboard base URL.

    Mirrors the pattern in :mod:`app.routes.share` (``DASHBOARD_URL`` env var
    with a localhost fallback). We read on each call rather than caching so
    test monkeypatches against the env take effect immediately.
    """
    return os.environ.get("DASHBOARD_URL", "http://localhost:3001")


def _ratelimit_to_503(exc: httpx.HTTPStatusError) -> HTTPException:
    """Translate a GitHub 403/429 into a 503 ``github_rate_limited`` response."""
    return HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "github_rate_limited",
        headers={"Retry-After": "60"},
    )


# ---------------------------------------------------------------------------
# GET /v1/github/installations  (D-10a)
# ---------------------------------------------------------------------------


@router.get("/installations", response_model=list[InstallationResp])
async def list_installations_endpoint(
    principal: ClerkPrincipal = Depends(  # noqa: B008
        require_role(*_READ_ROLES)
    ),
    team: Team = Depends(resolve_team_from_clerk_org),  # noqa: B008
) -> list[InstallationResp]:
    """List GitHub App installations for the caller's team.

    Sourced from the local ``github_installations`` table (no GitHub API
    call). Ordered by ``installed_at DESC`` so the most recently installed
    org surfaces first in the UI.
    """
    sm = get_sessionmaker()
    async with sm() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team.id)},
        )
        result = await session.execute(
            select(GithubInstallation).order_by(
                GithubInstallation.installed_at.desc()
            )
        )
        rows = list(result.scalars().all())
    return [
        InstallationResp(
            installation_id=r.github_installation_id,
            github_account_login=r.github_account_login,
            github_account_type=r.github_account_type,
            installed_at=r.installed_at,
            installed_by_user_id=r.installed_by_user_id,
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# GET /v1/github/repos  (D-10b)
# ---------------------------------------------------------------------------


@router.get("/repos", response_model=list[RepoResp])
async def list_repos_endpoint(
    installation_id: int = Query(..., gt=0),
    q: str | None = Query(default=None, max_length=100),
    principal: ClerkPrincipal = Depends(  # noqa: B008
        require_role(*_READ_ROLES)
    ),
    team: Team = Depends(resolve_team_from_clerk_org),  # noqa: B008
) -> list[RepoResp]:
    """List repos visible to a specific installation. 60s Upstash cache.

    Membership check first: the route looks up the installation in the
    ``github_installations`` table under the caller's team_id GUC so a
    cross-team probe (caller asking for an installation_id they don't
    own) returns 404 without making a GitHub API call.
    """
    sm = get_sessionmaker()
    async with sm() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team.id)},
        )
        found = await session.execute(
            select(GithubInstallation.id).where(
                GithubInstallation.github_installation_id == installation_id
            )
        )
        if found.scalar_one_or_none() is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "installation_not_found"
            )

    try:
        repos = await list_installation_repos(installation_id, q)
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (403, 429):
            raise _ratelimit_to_503(e) from e
        raise
    return [RepoResp(**r) for r in repos]


# ---------------------------------------------------------------------------
# GET /v1/github/branches  (D-10c)
# ---------------------------------------------------------------------------


@router.get("/branches", response_model=list[BranchResp])
async def list_branches_endpoint(
    installation_id: int = Query(..., gt=0),
    repo: str = Query(..., pattern=r"^[\w.\-]+/[\w.\-]+$", max_length=255),
    principal: ClerkPrincipal = Depends(  # noqa: B008
        require_role(*_READ_ROLES)
    ),
    team: Team = Depends(resolve_team_from_clerk_org),  # noqa: B008
) -> list[BranchResp]:
    """List branches for ``repo='owner/name'`` under the named installation.

    No cache — branches change frequently and the per-repo list is
    typically <30 (D-10c). The ``repo`` query parameter is regex-guarded
    by FastAPI's ``Query(pattern=...)`` so traversal/garbage strings never
    reach the GitHub call (T-07.5-04-04 mitigation).
    """
    sm = get_sessionmaker()
    async with sm() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team.id)},
        )
        found = await session.execute(
            select(GithubInstallation.id).where(
                GithubInstallation.github_installation_id == installation_id
            )
        )
        if found.scalar_one_or_none() is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "installation_not_found"
            )

    try:
        branches = await list_branches(installation_id, repo)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "repo_or_branch_not_found"
            ) from e
        if e.response.status_code in (403, 429):
            raise _ratelimit_to_503(e) from e
        raise
    return [BranchResp(**b) for b in branches]


# ---------------------------------------------------------------------------
# GET /v1/github/install-callback  (D-10d)
# ---------------------------------------------------------------------------


@router.get("/install-callback")
async def install_callback_endpoint(
    installation_id: int,
    setup_action: str,
    state: str,
    principal: ClerkPrincipal = Depends(require_principal),  # noqa: B008
    team: Team = Depends(resolve_team_from_clerk_org),  # noqa: B008
) -> RedirectResponse:
    """GitHub redirects the user's browser here after install completes.

    Verb is GET (per RESEARCH § Open Q5 — GitHub redirects with GET, not
    POST; CONTEXT D-10d's ``POST`` is a typo).

    State-CSRF guard (CC-3 / D-14 amended): the ``state`` query param is
    expected to equal the user's ``clerk_org_id`` (the Clerk organization
    they are signed into). The dashboard's InstallButton sets this value
    when constructing the GitHub install URL. Equality check closes the
    CSRF loop because an attacker would have to forge a state matching
    a clerk_org_id the victim is currently signed into.

    Defense-in-depth: even after state passes, we re-fetch
    ``/app/installations/{id}`` with a fresh App JWT to verify the
    installation actually exists with the claimed metadata. A forged
    callback URL pointing at a non-existent install hits 404 → redirect
    to ``?install=failed`` without DB write.

    Idempotent upsert: ON CONFLICT (team_id, github_installation_id) DO
    UPDATE so re-installs from the same org refresh the account
    login/type without UNIQUE violations.
    """
    expected_state = team.clerk_org_id
    if state != expected_state:
        _log.warning(
            "install_callback_state_mismatch",
            installation_id=installation_id,
            state_len=len(state),
            expected_org=expected_state,
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN, "state_mismatch")

    # Re-verify the installation via App JWT (defense vs forged URL).
    try:
        install = await get_installation_metadata(installation_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            _log.warning(
                "install_callback_install_not_found",
                installation_id=installation_id,
            )
            return RedirectResponse(
                url=f"{_dashboard_url()}/settings/integrations?install=failed",
                status_code=status.HTTP_302_FOUND,
            )
        raise

    account_login = install["account"]["login"]
    account_type = install["account"]["type"]

    sm = get_sessionmaker()
    async with sm() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team.id)},
        )
        await session.execute(
            text(
                """
                INSERT INTO github_installations
                    (id, team_id, github_installation_id, github_account_login,
                     github_account_type, installed_by_user_id)
                VALUES (gen_random_uuid(), :team_id, :iid, :login, :type, :uid)
                ON CONFLICT (team_id, github_installation_id) DO UPDATE
                SET github_account_login = EXCLUDED.github_account_login,
                    github_account_type = EXCLUDED.github_account_type
                """
            ),
            {
                "team_id": str(team.id),
                "iid": installation_id,
                "login": account_login,
                "type": account_type,
                "uid": principal.user_id,
            },
        )

    _log.info(
        "install_callback_upserted",
        installation_id=installation_id,
        team_id=str(team.id),
        github_account_login=account_login,
    )
    return RedirectResponse(
        url=f"{_dashboard_url()}/settings/integrations?install=success",
        status_code=status.HTTP_302_FOUND,
    )
