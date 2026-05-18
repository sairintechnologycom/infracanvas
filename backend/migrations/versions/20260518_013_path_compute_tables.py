"""013_path_compute_tables: computed_paths + asymmetry_findings + path_divergence_findings.

Phase 12 D-15 / D-16 — three storage targets for the path-compute job:

  - computed_paths        snapshot-per-pull path rows per (site_id, pair_src_cidr,
                          pair_dst_cidr, direction, computed_at); D-16 snapshot
                          semantics enforced via UNIQUE constraint.
  - asymmetry_findings    root-caused asymmetry rows (D-08/D-09 cause enum +
                          D-10 impact fields + D-16 reconciliation lifecycle).
  - path_divergence_findings  NetFlow-observed paths that disagree with the
                              computed model (D-07 / D-16).

D-08/D-09 — asymmetry_findings.cause is enum-gated via CHECK constraint over
('BGP_LOCAL_PREF','ROUTE_LEAK','NAT_ASYMMETRY','UNKNOWN','NET-010'). Pydantic
body validation rejects bad values at the boundary; the CHECK is defense in
depth. The 'NET-010' value was added in-place during Plan 12-06 (Warning 6) so
Python-detector NET-010 findings land in the same table and surface through
the Plan 12-03 GET /asymmetries read API.

D-16 lifecycle — both findings tables carry first_seen_at + last_seen_at
NOT NULL and resolved_at TIMESTAMPTZ NULL so the reconcile pass can flip
finding status without deleting the row (audit-safe).

RLS posture mirrors Phase 11 migration 011 / Pattern C verbatim:
  - team_id column on each row
  - ENABLE + FORCE ROW LEVEL SECURITY
  - team_isolation policy keyed on
    current_setting('app.current_team_id', true)::uuid
  - GRANT SELECT/INSERT/UPDATE/DELETE to infracanvas_app

Revision ID: 013_path_compute_tables
Revises: 012_route_flow_tables
Create Date: 2026-05-18
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "013_path_compute_tables"
down_revision: str | None = "012_route_flow_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. computed_paths — snapshot-per-pull path rows (D-15 / D-16).
    op.create_table(
        "computed_paths",
        sa.Column(
            "path_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "team_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("teams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "site_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dc_sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pair_src_cidr", sa.Text(), nullable=False),
        sa.Column("pair_dst_cidr", sa.Text(), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column(
            "hops",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "match_evidence",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "direction IN ('forward','return')",
            name="ck_computed_paths_direction",
        ),
        sa.UniqueConstraint(
            "site_id",
            "pair_src_cidr",
            "pair_dst_cidr",
            "direction",
            "computed_at",
            name="uq_computed_paths_snapshot",
        ),
    )
    op.create_index(
        "ix_computed_paths_latest",
        "computed_paths",
        [
            "site_id",
            "pair_src_cidr",
            "pair_dst_cidr",
            "direction",
            sa.text("computed_at DESC"),
        ],
    )
    op.execute("ALTER TABLE computed_paths ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE computed_paths FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY computed_paths_team_isolation ON computed_paths
          USING (team_id = current_setting('app.current_team_id', true)::uuid)
          WITH CHECK (team_id = current_setting('app.current_team_id', true)::uuid);
        """
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON computed_paths TO infracanvas_app;")

    # 2. asymmetry_findings — root-caused asymmetry rows.
    op.create_table(
        "asymmetry_findings",
        sa.Column(
            "finding_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "team_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("teams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "site_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dc_sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("forward_path_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("return_path_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cause", sa.Text(), nullable=False),
        sa.Column("cause_confidence", sa.Numeric(), nullable=False),
        sa.Column(
            "evidence",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "impact_bytes_per_sec",
            sa.Numeric(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "impact_firewall_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "cause IN ('BGP_LOCAL_PREF','ROUTE_LEAK','NAT_ASYMMETRY','UNKNOWN','NET-010')",
            name="ck_asymmetry_findings_cause",
        ),
    )
    op.create_index(
        "ix_asymmetry_findings_latest",
        "asymmetry_findings",
        ["site_id", sa.text("last_seen_at DESC"), "cause"],
    )
    op.execute("ALTER TABLE asymmetry_findings ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE asymmetry_findings FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY asymmetry_findings_team_isolation ON asymmetry_findings
          USING (team_id = current_setting('app.current_team_id', true)::uuid)
          WITH CHECK (team_id = current_setting('app.current_team_id', true)::uuid);
        """
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON asymmetry_findings TO infracanvas_app;"
    )

    # 3. path_divergence_findings — observed-vs-expected NetFlow disagreements.
    op.create_table(
        "path_divergence_findings",
        sa.Column(
            "finding_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "team_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("teams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "site_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dc_sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expected_path_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "observed_path",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "evidence",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_path_divergence_findings_latest",
        "path_divergence_findings",
        ["site_id", sa.text("last_seen_at DESC")],
    )
    op.execute("ALTER TABLE path_divergence_findings ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE path_divergence_findings FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY path_divergence_findings_team_isolation ON path_divergence_findings
          USING (team_id = current_setting('app.current_team_id', true)::uuid)
          WITH CHECK (team_id = current_setting('app.current_team_id', true)::uuid);
        """
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON path_divergence_findings TO infracanvas_app;"
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS path_divergence_findings_team_isolation "
        "ON path_divergence_findings;"
    )
    op.drop_index(
        "ix_path_divergence_findings_latest", table_name="path_divergence_findings"
    )
    op.drop_table("path_divergence_findings")
    op.execute(
        "DROP POLICY IF EXISTS asymmetry_findings_team_isolation ON asymmetry_findings;"
    )
    op.drop_index("ix_asymmetry_findings_latest", table_name="asymmetry_findings")
    op.drop_table("asymmetry_findings")
    op.execute("DROP POLICY IF EXISTS computed_paths_team_isolation ON computed_paths;")
    op.drop_index("ix_computed_paths_latest", table_name="computed_paths")
    op.drop_table("computed_paths")
