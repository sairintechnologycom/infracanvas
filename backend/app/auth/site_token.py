"""DC Agent site-token authentication (Phase 10 DCA-05).

Parallel auth path to require_principal (Clerk JWT). Same Authorization: Bearer
header convention; different token type. Validates via SHA-256 lookup hash
against dc_sites.token_lookup_hash (same pattern as share_links — migration 006).

Design note: dc_sites has FORCE ROW LEVEL SECURITY with a team_isolation policy
that requires ``app.current_team_id`` to be set. Since we don't know the team
until AFTER the token lookup (the whole point is to resolve the team from the
token), we use the ``dc_site_by_token_hash()`` SECURITY DEFINER function
(migration 010) — mirroring the ``share_link_by_token()`` pattern from
migration 006 and ``team_by_clerk_org()`` from migration 003.
"""
from __future__ import annotations

import hashlib

from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import raw_session


class DCSitePrincipal(BaseModel):
    """Validated DC Agent site principal.

    Fields:
        team_id: UUID of the owning team (as string).
        site_id: UUID of the dc_sites row (as string).
    """

    team_id: str
    site_id: str


async def require_site_token(
    request: Request,
    session: AsyncSession = Depends(raw_session),  # noqa: B008
) -> DCSitePrincipal:
    """Validate Bearer site-token; resolve team_id + site_id from dc_sites.

    Uses ``dc_site_by_token_hash()`` SECURITY DEFINER function (migration 010)
    to bypass RLS for the cross-team lookup — identical pattern to
    ``share_link_by_token()`` (migration 006) and ``team_by_clerk_org()``
    (migration 003). RLS blocks direct ``infracanvas_app`` SELECTs without
    ``app.current_team_id`` set; the SECURITY DEFINER function has access to
    all rows. After this dep resolves, downstream handlers MUST set
    ``app.current_team_id`` before any further RLS-scoped data access.

    Raises:
        HTTPException 401 ``missing_bearer`` — Authorization header absent
            or does not start with ``Bearer ``.
        HTTPException 401 ``invalid_site_token`` — SHA-256 hash of supplied
            token not found in dc_sites.
    """
    h = request.headers.get("authorization", "")
    if not h.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing_bearer")
    raw_token = h.split(" ", 1)[1].strip()
    if not raw_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing_bearer")
    lookup_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    result = await session.execute(
        text(
            "SELECT id, team_id FROM dc_site_by_token_hash(:h)"
        ),
        {"h": lookup_hash},
    )
    row = result.mappings().first()
    if row is None or row.get("id") is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_site_token")
    return DCSitePrincipal(team_id=str(row["team_id"]), site_id=str(row["id"]))
