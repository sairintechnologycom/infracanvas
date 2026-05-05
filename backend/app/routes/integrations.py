"""PATCH /v1/integrations/slack — save Slack incoming webhook URL for the team.

Phase 8: WBH-03. Validates URL prefix before storage to prevent SSRF
(T-8-04-01). RLS GUC scopes the UPDATE to the authenticated team only
(T-8-04-02). ``require_role`` gate blocks unauthenticated writes (T-8-04-03).
"""
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

_WRITE_ROLES = ("owner", "admin", "member")


class SlackWebhookBody(BaseModel):
    webhook_url: str


@router.patch("/slack", status_code=200)
async def save_slack_webhook(
    body: SlackWebhookBody,
    principal: ClerkPrincipal = Depends(require_role(*_WRITE_ROLES)),  # noqa: B008
    team: Team = Depends(resolve_team_from_clerk_org),  # noqa: B008
) -> dict[str, str]:
    """Save or update the team's Slack incoming webhook URL.

    Validates the URL starts with ``https://hooks.slack.com/`` to prevent
    SSRF via worker-side POST to an attacker-controlled host (T-8-04-01).
    Sets RLS GUC before UPDATE so the write is scoped to the authenticated
    team's row only (T-8-04-02).
    """
    if not body.webhook_url.startswith("https://hooks.slack.com/"):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Invalid Slack webhook URL: must start with https://hooks.slack.com/",
        )

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

    _log.info("slack_webhook_saved", team_id=str(team.id))
    return {"message": "Slack webhook saved"}
