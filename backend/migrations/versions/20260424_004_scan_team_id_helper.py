"""scan_team_id() SECURITY DEFINER helper for the worker indexer path

Revision ID: 004_scan_team_id_helper
Revises: 003_teams_lookup_policy
Create Date: 2026-04-24

Mirrors the ``team_by_clerk_org()`` pattern introduced in migration 003,
but for the worker side: the indexing task receives ``scan_id`` only —
no Clerk JWT, no upstream team resolver — yet it must determine the
target team's id to set ``app.current_team_id`` and run the UPDATE under
RLS-scoped policy.

Three options were considered (see Plan 06-06 SUMMARY § rationale):

* Open a permissive USING(true) SELECT policy on scans — REJECTED
  (cross-team blast radius if a code path leaks through).
* Run the worker as the owner role with BYPASSRLS — REJECTED (single
  worker bug bypasses every team isolation check).
* SECURITY DEFINER SQL function returning ONLY ``scans.team_id`` for the
  given scan id — CHOSEN. Returns a UUID, no sensitive cross-team data.
  Locked down with REVOKE FROM PUBLIC + GRANT EXECUTE TO infracanvas_app.

The worker uses the returned ``team_id`` to call
``set_config('app.current_team_id', :t, true)`` on a fresh team-scoped
session, then performs the actual UPDATE through the regular RLS-scoped
write path. T-06-07b mitigation: this function returns one column from
one row identified by primary key — strictly narrower than a full row read.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_scan_team_id_helper"
down_revision: Union[str, None] = "003_teams_lookup_policy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION scan_team_id(p_scan_id uuid)
        RETURNS uuid
        LANGUAGE sql
        SECURITY DEFINER
        STABLE
        SET search_path = public
        AS $$
          SELECT team_id FROM scans WHERE id = p_scan_id
        $$;
        """
    )
    # Tighten exposure: revoke broad PUBLIC grant added by SECURITY DEFINER
    # default, then grant EXECUTE only to the application role used by the
    # worker process. Migrator/owner role retains EXECUTE implicitly.
    op.execute("REVOKE ALL ON FUNCTION scan_team_id(uuid) FROM PUBLIC;")
    op.execute("GRANT EXECUTE ON FUNCTION scan_team_id(uuid) TO infracanvas_app;")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS scan_team_id(uuid);")
