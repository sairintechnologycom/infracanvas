"""dc_sites table + site-token hashed storage (Phase 10 DCA-05).

Revision ID: 010_dc_sites
Revises: 009_slack_webhook_url
Create Date: 2026-05-07
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010_dc_sites"
down_revision: str | None = "009_slack_webhook_url"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("dc_sites",
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
        sa.Column("name", sa.Text(), nullable=False),
        # SHA-256 hex of raw site token — deterministic, used for indexed SELECT
        # (same pattern as share_links.token_lookup_hash, migration 006 lines 53-54)
        sa.Column("token_lookup_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "dc_sites_token_lookup_hash_key", "dc_sites", ["token_lookup_hash"]
    )
    op.create_index("ix_dc_sites_team_id", "dc_sites", ["team_id"])
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON dc_sites TO infracanvas_app;")
    op.execute("ALTER TABLE dc_sites ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE dc_sites FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY dc_sites_team_isolation ON dc_sites
          USING (team_id = current_setting('app.current_team_id', true)::uuid)
          WITH CHECK (team_id = current_setting('app.current_team_id', true)::uuid);
        """
    )

    # SECURITY DEFINER lookup for the unauthenticated site-token validation path.
    # Mirrors share_link_by_token() from migration 006 exactly.
    # Looks up by token_lookup_hash (SHA-256) — fast unique indexed lookup.
    # RLS on dc_sites blocks raw infracanvas_app SELECTs without team context;
    # this function bypasses RLS for the cross-team hash lookup that establishes
    # the principal (we don't know the team until after we find the row).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION dc_site_by_token_hash(p_lookup_hash text)
        RETURNS dc_sites
        LANGUAGE sql
        SECURITY DEFINER
        STABLE
        SET search_path = public
        AS $$
          SELECT * FROM dc_sites
          WHERE token_lookup_hash = p_lookup_hash
          LIMIT 1;
        $$;
        """
    )
    op.execute(
        "REVOKE ALL ON FUNCTION dc_site_by_token_hash(text) FROM PUBLIC;"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION dc_site_by_token_hash(text) TO infracanvas_app;"
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS dc_site_by_token_hash(text);")
    op.execute("DROP POLICY IF EXISTS dc_sites_team_isolation ON dc_sites;")
    op.drop_index("ix_dc_sites_team_id", table_name="dc_sites")
    op.drop_constraint("dc_sites_token_lookup_hash_key", "dc_sites", type_="unique")
    op.drop_table("dc_sites")
