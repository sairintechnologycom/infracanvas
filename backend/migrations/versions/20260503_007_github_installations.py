"""github_installations table + RLS team-isolation policy + grants.

Revision ID: 007_github_installations
Revises: 006_share_links
Create Date: 2026-05-03

Phase 7.5 D-11. Stores the long-lived GitHub App installation_id (opaque
integer, not a secret) per team. Token material is never persisted —
worker mints fresh installation tokens per scan via App JWT (D-06).

RLS posture (mirrors share_links / scans / Phase 6 D-02):
- ENABLE + FORCE Row-Level Security (FORCE applies to table owner too).
- Single FOR ALL policy with USING + WITH CHECK on
  ``team_id = current_setting('app.current_team_id', true)::uuid``.
- GRANT SELECT/INSERT/UPDATE/DELETE to ``infracanvas_app`` role
  (NOBYPASSRLS).

No SECURITY DEFINER helper here — every read/write happens after
``app.current_team_id`` is set in the request scope (CC-2). Worker
already receives ``team_id`` from the kicker, so no
``installation_team_id(uuid)`` helper is needed.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007_github_installations"
down_revision: Union[str, None] = "006_share_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "github_installations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "team_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("teams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("github_installation_id", sa.BigInteger(), nullable=False),
        sa.Column("github_account_login", sa.String(length=255), nullable=False),
        sa.Column("github_account_type", sa.String(length=32), nullable=False),
        sa.Column(
            "installed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("installed_by_user_id", sa.String(length=64), nullable=False),
    )

    op.create_unique_constraint(
        "github_installations_team_install_key",
        "github_installations",
        ["team_id", "github_installation_id"],
    )
    op.create_index(
        "ix_github_installations_team_id",
        "github_installations",
        ["team_id"],
    )

    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON github_installations TO infracanvas_app;"
    )

    op.execute("ALTER TABLE github_installations ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE github_installations FORCE ROW LEVEL SECURITY;")

    op.execute(
        """
        CREATE POLICY github_installations_team_isolation ON github_installations
          USING (team_id = current_setting('app.current_team_id', true)::uuid)
          WITH CHECK (team_id = current_setting('app.current_team_id', true)::uuid);
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS github_installations_team_isolation ON github_installations;"
    )
    op.drop_index(
        "ix_github_installations_team_id", table_name="github_installations"
    )
    op.drop_constraint(
        "github_installations_team_install_key",
        "github_installations",
        type_="unique",
    )
    op.drop_table("github_installations")
