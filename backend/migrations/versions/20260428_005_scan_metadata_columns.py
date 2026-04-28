"""scan metadata columns: branch, commit_sha, source

Revision ID: 005_scan_metadata_columns
Revises: 004_scan_team_id_helper
Create Date: 2026-04-28
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_scan_metadata_columns"
down_revision: Union[str, None] = "004_scan_team_id_helper"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scans", sa.Column("branch", sa.String(length=255), nullable=True))
    op.add_column("scans", sa.Column("commit_sha", sa.String(length=40), nullable=True))
    op.add_column("scans", sa.Column("source", sa.String(length=32), nullable=True))
    op.create_index("ix_scans_branch", "scans", ["branch"])
    op.create_index("ix_scans_source", "scans", ["source"])


def downgrade() -> None:
    op.drop_index("ix_scans_source", table_name="scans")
    op.drop_index("ix_scans_branch", table_name="scans")
    op.drop_column("scans", "source")
    op.drop_column("scans", "commit_sha")
    op.drop_column("scans", "branch")
