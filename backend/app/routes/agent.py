"""DC Agent routes (Phase 10 DCA-05).

POST /v1/sites              — Clerk-authed, owner role; one-time site_token issuance
POST /v1/agent/routes       — site-token-authed; agent push for routing data
POST /v1/agent/flows        — site-token-authed; agent push for NetFlow records

Security posture:
- POST /v1/sites uses require_role("owner") (T-10-02-04 mitigation)
- Agent push routes use require_site_token, NOT require_principal (Pitfall 6)
- site_token plaintext returned ONCE; only SHA-256 hash stored (T-10-02-01, -03)
- T-10-02-06: payload bounds enforced in RoutesPushBody/FlowsPushBody (max 10 000)
"""
from __future__ import annotations

import hashlib
import secrets
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, status
from sqlalchemy import insert, text

from app.auth.clerk import ClerkPrincipal, require_role
from app.auth.deps import resolve_team_from_clerk_org
from app.auth.site_token import DCSitePrincipal, require_site_token
from app.db.models import DCSite, Team
from app.db.session import get_sessionmaker
from app.schemas.agent import (
    CreateSiteBody,
    CreateSiteResp,
    FlowsPushBody,
    RoutesPushBody,
)

router = APIRouter(prefix="/v1", tags=["agent"])
_log = structlog.get_logger("app.agent")

_OWNER_ROLES = ("owner",)


@router.post("/sites", status_code=status.HTTP_201_CREATED, response_model=CreateSiteResp)
async def create_site(
    body: CreateSiteBody,
    principal: ClerkPrincipal = Depends(require_role(*_OWNER_ROLES)),  # noqa: B008
    team: Team = Depends(resolve_team_from_clerk_org),  # noqa: B008
) -> CreateSiteResp:
    """Create a new DC site for the team and return a one-time plaintext token.

    Per CONTEXT.md D-03: token is returned ONCE; only its SHA-256 hash is stored.
    T-10-02-01: secrets.token_urlsafe(32) provides 32 bytes of entropy.
    T-10-02-03: only SHA-256 lookup hash persisted — plaintext never stored.
    T-10-02-04: require_role("owner") gate.
    """
    raw_token = "ic_site_" + secrets.token_urlsafe(32)
    lookup_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    site_id = uuid4()

    sm = get_sessionmaker()
    async with sm() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team.id)},
        )
        await session.execute(
            insert(DCSite).values(
                id=site_id,
                team_id=team.id,
                name=body.name,
                token_lookup_hash=lookup_hash,
            )
        )

    _log.info(
        "dc_site_created",
        team_id=str(team.id),
        site_id=str(site_id),
        principal_id=principal.user_id,
    )
    return CreateSiteResp(
        site_id=str(site_id),
        name=body.name,
        site_token=raw_token,
    )


@router.post("/agent/routes", status_code=status.HTTP_202_ACCEPTED)
async def push_routes(
    body: RoutesPushBody,
    principal: DCSitePrincipal = Depends(require_site_token),  # noqa: B008
) -> dict[str, bool]:
    """Receive a routing-table batch from a DC agent. Phase 10 logs only — Phase 11 persists."""
    _log.info(
        "agent_routes_received",
        site_id=principal.site_id,
        team_id=principal.team_id,
        device_host=body.device_host,
        count=len(body.routes),
    )
    return {"ok": True}


@router.post("/agent/flows", status_code=status.HTTP_202_ACCEPTED)
async def push_flows(
    body: FlowsPushBody,
    principal: DCSitePrincipal = Depends(require_site_token),  # noqa: B008
) -> dict[str, bool]:
    """Receive a NetFlow batch from a DC agent. Phase 10 logs only — Phase 11 persists."""
    _log.info(
        "agent_flows_received",
        site_id=principal.site_id,
        team_id=principal.team_id,
        count=len(body.flows),
    )
    return {"ok": True}
