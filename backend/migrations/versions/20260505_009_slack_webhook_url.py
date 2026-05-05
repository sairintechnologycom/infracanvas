"""Add slack_webhook_url to teams + team_id_for_installation SECURITY DEFINER function.

Revision ID: 009_slack_webhook_url
Revises: 008_scan_github_columns
Create Date: 2026-05-05

Phase 8 D-04. Adds ``slack_webhook_url TEXT NULL`` to the ``teams`` table.
This column stores the Slack incoming webhook URL for the team (nullable —
``None`` means no Slack integration is configured). The value is set via
``PATCH /v1/integrations/slack`` and read by the ``scan_repo`` worker to
fire an alert when a webhook-triggered scan contains >=1 Critical finding.

Also creates the ``team_id_for_installation(bigint) RETURNS uuid`` function
with ``SECURITY DEFINER``. This function is required by the GitHub webhook
handler (``POST /v1/webhooks/github``) which runs WITHOUT an RLS context —
there is no Clerk JWT available before the team_id is known, so the handler
cannot call ``set_config('app.current_team_id', ...)`` first. The SECURITY
DEFINER function bypasses RLS to do a direct lookup from
``github_installations`` and returns the owning team's UUID.

Security scope of the function is deliberately narrow:
- Only SELECTs ``team_id`` from ``github_installations`` (single column)
- Single equality predicate on ``github_installation_id = $1``
- No joins to other teams' data
- STABLE + LIMIT 1 for efficiency
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_slack_webhook_url"
down_revision: Union[str, None] = "008_scan_github_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("teams", sa.Column("slack_webhook_url", sa.Text(), nullable=True))

    op.execute(
        """
        CREATE OR REPLACE FUNCTION team_id_for_installation(p_installation_id bigint)
        RETURNS uuid
        LANGUAGE sql
        SECURITY DEFINER
        STABLE
        AS $$
            SELECT team_id
            FROM github_installations
            WHERE github_installation_id = p_installation_id
            LIMIT 1;
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS team_id_for_installation(bigint)")
    op.drop_column("teams", "slack_webhook_url")
