"""scans column extensions for GitHub repo connector + dedup partial index.

Revision ID: 008_scan_github_columns
Revises: 007_github_installations
Create Date: 2026-05-03

Phase 7.5 D-12, D-13. Adds six nullable columns to ``scans`` so that scans
originating from a GitHub App installation carry the full provenance needed
for dedup, debug, and the dashboard's "scanned from GitHub" affordances:

  - ``source_path``         : where the worker cloned the repo into the
                              ephemeral working directory (debug aid).
  - ``error_message``       : populated on status='failed' so the API can
                              surface a concise reason (D-13).
  - ``github_installation_id``: the GitHub App installation that produced
                              the scan (FK is logical only — RLS keeps
                              cross-team rows from being matched).
  - ``github_repo``         : "owner/name" — used by the dedup partial
                              index + dashboard "from repo" badge.
  - ``github_branch``       : branch ref (e.g. ``main``) the scan was
                              produced from.
  - ``github_sha``          : exact 40-char commit SHA (immutable identity).

Also creates ``idx_scans_github_dedup`` — a PARTIAL index on
``(team_id, github_repo, github_sha, created_at DESC)`` filtered to
``status='ready'``. Used by the API to avoid re-running an identical scan
when a user kicks off the same SHA twice in quick succession (D-12).

Mirrors 005_scan_metadata_columns.py for column shape; partial-index
predicate keeps the index small (only successful scans contribute to the
dedup decision).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_scan_github_columns"
down_revision: Union[str, None] = "007_github_installations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scans", sa.Column("source_path", sa.Text(), nullable=True))
    op.add_column("scans", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column(
        "scans",
        sa.Column("github_installation_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "scans", sa.Column("github_repo", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "scans", sa.Column("github_branch", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "scans", sa.Column("github_sha", sa.String(length=40), nullable=True)
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_scans_github_dedup "
        "ON scans(team_id, github_repo, github_sha, created_at DESC) "
        "WHERE status = 'ready'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_scans_github_dedup")
    op.drop_column("scans", "github_sha")
    op.drop_column("scans", "github_branch")
    op.drop_column("scans", "github_repo")
    op.drop_column("scans", "github_installation_id")
    op.drop_column("scans", "error_message")
    op.drop_column("scans", "source_path")
