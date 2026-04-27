"""Team resolution dependency.

`resolve_team_from_clerk_org` looks up the :class:`Team` row matching the
authenticated principal's ``clerk_org_id`` so downstream deps (e.g.
``team_scoped_session``) have a Team to scope queries with.

**Chicken-and-egg with RLS:** the team-scoped SELECT policy on ``teams``
requires ``app.current_team_id`` to already be set, but we don't know the
team's id until we look it up. We resolve this via migration 003's
``team_by_clerk_org(text)`` SECURITY DEFINER SQL function, which bypasses
RLS *only* for this single read. Authorization is supplied by the JWT
already validated upstream (the caller demonstrably holds the
``clerk_org_id`` claim).

REVOKE ALL FROM PUBLIC + GRANT EXECUTE TO infracanvas_app on the function,
combined with the strict per-op SELECT/UPDATE/DELETE policies on
``teams``, prevents cross-tenant leakage everywhere except this narrow
read path.
"""

from __future__ import annotations

import sentry_sdk
import structlog
from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.clerk import ClerkPrincipal, require_principal
from app.db.models import Team
from app.db.session import raw_session


async def resolve_team_from_clerk_org(
    principal: ClerkPrincipal = Depends(require_principal),
    session: AsyncSession = Depends(raw_session),
) -> Team:
    """Load the :class:`Team` row matching ``principal.clerk_org_id``.

    Calls ``SELECT * FROM team_by_clerk_org(:org)`` — a SECURITY DEFINER
    function (migration 003) — to satisfy the lookup without opening a
    permissive SELECT policy on ``teams``.

    Raises:
        HTTPException 404 ``team_not_provisioned`` — webhook hasn't run
            yet for this org. Client should retry after a brief delay; the
            organization.created Svix delivery normally arrives within
            seconds of org creation.

    Side effects: binds ``team_id`` to the structlog contextvar and sets
    the matching Sentry tag for the remainder of the request.
    """
    result = await session.execute(
        text(
            "SELECT id, clerk_org_id, name, stripe_customer_id, "
            "created_at, updated_at "
            "FROM team_by_clerk_org(:org)"
        ),
        {"org": principal.clerk_org_id},
    )
    row = result.mappings().first()
    if row is None or row.get("id") is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "team_not_provisioned")
    team = Team(**dict(row))
    structlog.contextvars.bind_contextvars(team_id=str(team.id))
    sentry_sdk.set_tag("team_id", str(team.id))
    return team
