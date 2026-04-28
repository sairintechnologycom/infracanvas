"""share_links table, RLS policies, share_link_by_token() SECURITY DEFINER helper

Revision ID: 006_share_links
Revises: 005_scan_metadata_columns
Create Date: 2026-04-28

Design notes:
- token_lookup_hash (SHA-256 of raw token) enables O(1) indexed lookup without
  iterating all rows to run bcrypt.checkpw. bcrypt verification happens in Python
  after fetching the row by token_lookup_hash.
- share_link_by_token() SECURITY DEFINER lets the unauthenticated public path
  read share_links without opening a permissive SELECT RLS policy. Mirrors
  team_by_clerk_org() from migration 003 exactly.
- RLS team_isolation policy covers all authenticated paths (create / delete).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006_share_links"
down_revision: Union[str, None] = "005_scan_metadata_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "share_links",
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
        sa.Column(
            "scan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("scans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # bcrypt hash of raw token (cost 12) — used for bcrypt.checkpw after row fetch
        sa.Column("token_hash", sa.String(255), nullable=False),
        # SHA-256 hex of raw token — deterministic, used for indexed SELECT
        sa.Column("token_lookup_hash", sa.String(64), nullable=False),
        # bcrypt hash of password (nullable — None means no password)
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        # Clerk user ID (string — not a UUID FK — matches Clerk's format)
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Indexes
    op.create_unique_constraint(
        "share_links_token_lookup_hash_key", "share_links", ["token_lookup_hash"]
    )
    op.create_unique_constraint(
        "share_links_token_hash_key", "share_links", ["token_hash"]
    )
    op.create_index("ix_share_links_team_id", "share_links", ["team_id"])
    op.create_index("ix_share_links_scan_id", "share_links", ["scan_id"])
    op.create_index("ix_share_links_expires_at", "share_links", ["expires_at"])

    # Grant to app role
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON share_links TO infracanvas_app;"
    )

    # Enable + FORCE RLS (same pattern as 002_rls_setup.py)
    op.execute("ALTER TABLE share_links ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE share_links FORCE ROW LEVEL SECURITY;")

    # Team isolation policy — covers all authenticated paths (INSERT/SELECT/UPDATE/DELETE)
    op.execute(
        """
        CREATE POLICY share_links_team_isolation ON share_links
          USING (team_id = current_setting('app.current_team_id', true)::uuid)
          WITH CHECK (team_id = current_setting('app.current_team_id', true)::uuid);
        """
    )

    # SECURITY DEFINER lookup for public unauthenticated path.
    # Mirrors team_by_clerk_org() from migration 003 lines 75-91 exactly.
    # Looks up by token_lookup_hash (SHA-256) — fast indexed lookup.
    # bcrypt verification of token_hash happens in Python after this returns the row.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION share_link_by_token(p_lookup_hash text)
        RETURNS share_links
        LANGUAGE sql
        SECURITY DEFINER
        STABLE
        SET search_path = public
        AS $$
          SELECT * FROM share_links
          WHERE token_lookup_hash = p_lookup_hash
            AND revoked_at IS NULL
          LIMIT 1;
        $$;
        """
    )
    op.execute(
        "REVOKE ALL ON FUNCTION share_link_by_token(text) FROM PUBLIC;"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION share_link_by_token(text) TO infracanvas_app;"
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS share_link_by_token(text);")
    op.execute("DROP POLICY IF EXISTS share_links_team_isolation ON share_links;")
    op.drop_index("ix_share_links_expires_at", table_name="share_links")
    op.drop_index("ix_share_links_scan_id", table_name="share_links")
    op.drop_index("ix_share_links_team_id", table_name="share_links")
    op.drop_constraint(
        "share_links_token_hash_key", "share_links", type_="unique"
    )
    op.drop_constraint(
        "share_links_token_lookup_hash_key", "share_links", type_="unique"
    )
    op.drop_table("share_links")
