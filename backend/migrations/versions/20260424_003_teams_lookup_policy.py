"""team_by_clerk_org() SECURITY DEFINER helper + per-operation teams RLS policies

Revision ID: 003_teams_lookup_policy
Revises: 002_rls_setup
Create Date: 2026-04-24

Replaces the single ``teams_self`` policy from migration 002 with
per-operation policies so the SELECT path on ``teams`` stays strictly
scoped to ``app.current_team_id``, while INSERT (webhook-only) is
permissive — protected upstream by Svix signature verification on
``/v1/webhooks/clerk`` (T-06-02).

Adds ``team_by_clerk_org(text)`` SECURITY DEFINER SQL function so the
``resolve_team_from_clerk_org`` dependency can fetch a single team row by
``clerk_org_id`` without opening a permissive SELECT policy. Caller is
authenticated by Clerk JWT validation (T-06-06b mitigation in plan
threat register).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_teams_lookup_policy"
down_revision: Union[str, None] = "002_rls_setup"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop the broad teams_self from migration 002 — replaced below
    #    with per-operation policies.
    op.execute("DROP POLICY IF EXISTS teams_self ON teams;")

    # 2. SELECT stays strict — only rows matching app.current_team_id GUC.
    op.execute(
        """
        CREATE POLICY teams_select_self ON teams FOR SELECT
          USING (id = current_setting('app.current_team_id', true)::uuid);
        """
    )

    # 3. INSERT: webhook-only path. Permissive WITH CHECK is acceptable
    #    because the only caller, /v1/webhooks/clerk, is gated upstream by
    #    Svix HMAC signature verification (T-06-02). No other code path
    #    inserts into teams.
    op.execute(
        """
        CREATE POLICY teams_webhook_insert ON teams FOR INSERT
          WITH CHECK (true);
        """
    )

    # 4. UPDATE/DELETE stay strict — only the team itself can mutate its row.
    op.execute(
        """
        CREATE POLICY teams_mutate_update ON teams FOR UPDATE
          USING (id = current_setting('app.current_team_id', true)::uuid)
          WITH CHECK (id = current_setting('app.current_team_id', true)::uuid);
        """
    )
    op.execute(
        """
        CREATE POLICY teams_mutate_delete ON teams FOR DELETE
          USING (id = current_setting('app.current_team_id', true)::uuid);
        """
    )

    # 5. SECURITY DEFINER lookup. Returns the single team row matching
    #    clerk_org_id; bypasses RLS only for this narrow read.
    #    Caller already validated as that clerk_org_id by require_principal,
    #    so this is auth-by-authentication, not auth-by-RLS.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION team_by_clerk_org(p_clerk_org_id text)
        RETURNS teams
        LANGUAGE sql
        SECURITY DEFINER
        STABLE
        SET search_path = public
        AS $$
          SELECT * FROM teams WHERE clerk_org_id = p_clerk_org_id LIMIT 1;
        $$;
        """
    )
    op.execute("REVOKE ALL ON FUNCTION team_by_clerk_org(text) FROM PUBLIC;")
    op.execute(
        "GRANT EXECUTE ON FUNCTION team_by_clerk_org(text) TO infracanvas_app;"
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS team_by_clerk_org(text);")
    op.execute("DROP POLICY IF EXISTS teams_select_self ON teams;")
    op.execute("DROP POLICY IF EXISTS teams_webhook_insert ON teams;")
    op.execute("DROP POLICY IF EXISTS teams_mutate_update ON teams;")
    op.execute("DROP POLICY IF EXISTS teams_mutate_delete ON teams;")
    op.execute(
        """
        CREATE POLICY teams_self ON teams
          USING (id = current_setting('app.current_team_id', true)::uuid)
          WITH CHECK (id = current_setting('app.current_team_id', true)::uuid);
        """
    )
