"""RLS setup: infracanvas_app role, grants, ENABLE + FORCE RLS, team isolation policies

Revision ID: 002_rls_setup
Revises: 001_initial_schema
Create Date: 2026-04-24

NOTE (research callout #1): Neon offers transaction-mode pooler only. The
`SET LOCAL app.current_team_id = ...` pattern (implemented in
backend/app/db/session.py::team_scoped_session) is scoped to BEGIN...COMMIT
and is safe under transaction-mode pooling — the pool-checkout unit IS the tx.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_rls_setup"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the application role (idempotent) — explicitly NOBYPASSRLS.
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'infracanvas_app') THEN
            CREATE ROLE infracanvas_app WITH LOGIN NOBYPASSRLS;
          END IF;
        END $$;
        """
    )
    # Belt-and-braces: re-assert NOBYPASSRLS even if role pre-existed.
    op.execute("ALTER ROLE infracanvas_app NOBYPASSRLS;")

    # Schema + table grants. No GRANT TO PUBLIC anywhere.
    op.execute("GRANT USAGE ON SCHEMA public TO infracanvas_app;")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON teams, scans TO infracanvas_app;")
    op.execute(
        """
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
          GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO infracanvas_app;
        """
    )

    # Enable + FORCE RLS on both tables. FORCE applies RLS to the table owner
    # too — without it, the owner (migrator role) would bypass policies and
    # leave a latent escalation path if any admin endpoint ever reused that
    # connection string.
    op.execute("ALTER TABLE teams ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE teams FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE scans ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE scans FORCE ROW LEVEL SECURITY;")

    # Team-scoped policies. `true` second arg to current_setting → returns
    # NULL (not error) when the GUC is unset; the UUID cast then yields NULL
    # and no row matches, giving safe-by-default zero-row visibility.
    op.execute(
        """
        CREATE POLICY teams_self ON teams
          USING (id = current_setting('app.current_team_id', true)::uuid)
          WITH CHECK (id = current_setting('app.current_team_id', true)::uuid);
        """
    )
    op.execute(
        """
        CREATE POLICY scans_team_isolation ON scans
          USING (team_id = current_setting('app.current_team_id', true)::uuid)
          WITH CHECK (team_id = current_setting('app.current_team_id', true)::uuid);
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS scans_team_isolation ON scans;")
    op.execute("DROP POLICY IF EXISTS teams_self ON teams;")
    op.execute("ALTER TABLE scans NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE scans DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE teams NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE teams DISABLE ROW LEVEL SECURITY;")
    op.execute("REVOKE ALL ON teams, scans FROM infracanvas_app;")
    op.execute("REVOKE USAGE ON SCHEMA public FROM infracanvas_app;")
    # Leave the role itself — may still be attached to active sessions.
