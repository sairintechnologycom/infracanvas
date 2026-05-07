"""DC Agent site-token authentication (Phase 10 DCA-05).

Parallel auth path to require_principal (Clerk JWT). Same Authorization: Bearer
header convention; different token type. Validates via SHA-256 lookup hash
against dc_sites.token_lookup_hash (same pattern as share_links — migration 006).
"""
from __future__ import annotations

import hashlib

from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DCSite
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

    Uses ``raw_session`` (no ``app.current_team_id`` GUC set) — by design,
    since we don't yet know the team. The token_lookup_hash unique index
    provides cross-team lookup; only the owning team's row can match. After
    this dep resolves, downstream handlers MUST set ``app.current_team_id``
    before any further RLS-scoped data access.

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
        select(DCSite).where(DCSite.token_lookup_hash == lookup_hash)
    )
    site = result.scalar_one_or_none()
    if site is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_site_token")
    return DCSitePrincipal(team_id=str(site.team_id), site_id=str(site.id))
