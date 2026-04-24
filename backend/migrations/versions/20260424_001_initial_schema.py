"""initial schema: teams, scans, scan_status enum

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-04-24
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("clerk_org_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("stripe_customer_id", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_unique_constraint("teams_clerk_org_id_key", "teams", ["clerk_org_id"])
    op.create_index("ix_teams_clerk_org_id", "teams", ["clerk_org_id"])

    scan_status = postgresql.ENUM("pending", "ready", "failed", name="scan_status")
    scan_status.create(op.get_bind())

    op.create_table("scans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "team_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("teams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("r2_key", sa.String(512), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("size_bytes", sa.BigInteger, nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM("pending", "ready", "failed", name="scan_status", create_type=False),
            nullable=False,
        ),
        sa.Column("summary_json", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_scans_team_id", "scans", ["team_id"])
    # Composite UNIQUE enables T-06-03 dedup (team_id, id) lookups under RLS.
    op.create_unique_constraint("scans_team_id_id_key", "scans", ["team_id", "id"])


def downgrade() -> None:
    op.drop_table("scans")
    op.drop_table("teams")
    op.execute("DROP TYPE scan_status")
