"""012_route_flow_tables: route_records + netflow_records.

Phase 12 D-15 / Pitfall 1 — backend persistence for Phase 10 agent push
(routes + NetFlow). The Phase 10 agent.py handlers were stubs ("logs
only — Phase 11 persists"); Phase 11 only landed firewall tables. Phase
12 closes that gap so the path-compute job has inputs.

v1.1 scope per RESEARCH Q2 RESOLVED: netflow_records carries ENDPOINT
fields only. exporter_interface / exit_interface columns + Go agent
emitter extension are deferred to v1.2.

RLS posture mirrors Phase 11 D-08 / migration 011 verbatim:
  - team_id column on each row
  - ENABLE + FORCE ROW LEVEL SECURITY
  - team_isolation policy keyed on
    current_setting('app.current_team_id', true)::uuid
  - GRANT SELECT/INSERT/UPDATE/DELETE to infracanvas_app

Revision ID: 012_route_flow_tables
Revises: 011_firewall_tables
Create Date: 2026-05-18
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012_route_flow_tables"
down_revision: str | None = "011_firewall_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. route_records — snapshot-per-pull routes ingested from DC agent.
    op.create_table(
        "route_records",
        sa.Column(
            "record_id",
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
        sa.Column("device_host", sa.Text(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("prefix", sa.Text(), nullable=False),
        sa.Column("next_hop", sa.Text(), nullable=False),
        sa.Column("protocol", sa.Text(), nullable=False),
        sa.Column("metric", sa.Integer(), server_default="0", nullable=False),
        sa.Column("as_path", sa.Text(), server_default="", nullable=False),
    )
    op.create_index(
        "ix_route_records_latest",
        "route_records",
        ["site_id", "device_host", sa.text("collected_at DESC")],
    )
    op.execute("ALTER TABLE route_records ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE route_records FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY route_records_team_isolation ON route_records
          USING (team_id = current_setting('app.current_team_id', true)::uuid)
          WITH CHECK (team_id = current_setting('app.current_team_id', true)::uuid);
        """
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON route_records TO infracanvas_app;")

    # 2. netflow_records — v1.1 endpoint-only schema per RESEARCH Q2 RESOLVED.
    #    exporter_interface / exit_interface deferred to v1.2 migration
    #    alongside Go agent emitter.
    op.create_table(
        "netflow_records",
        sa.Column(
            "record_id",
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
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("src_ip", postgresql.INET(), nullable=False),
        sa.Column("dst_ip", postgresql.INET(), nullable=False),
        sa.Column("src_port", sa.Integer(), nullable=False),
        sa.Column("dst_port", sa.Integer(), nullable=False),
        sa.Column("protocol", sa.SmallInteger(), nullable=False),
        sa.Column("bytes", sa.BigInteger(), nullable=False),
        sa.Column("packets", sa.BigInteger(), nullable=False),
    )
    op.create_index(
        "ix_netflow_records_window",
        "netflow_records",
        ["site_id", sa.text("collected_at DESC")],
    )
    op.create_index(
        "ix_netflow_records_flow_key",
        "netflow_records",
        ["src_ip", "dst_ip", "src_port", "dst_port", "protocol"],
    )
    op.execute("ALTER TABLE netflow_records ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE netflow_records FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY netflow_records_team_isolation ON netflow_records
          USING (team_id = current_setting('app.current_team_id', true)::uuid)
          WITH CHECK (team_id = current_setting('app.current_team_id', true)::uuid);
        """
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON netflow_records TO infracanvas_app;")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS netflow_records_team_isolation ON netflow_records;")
    op.drop_index("ix_netflow_records_flow_key", table_name="netflow_records")
    op.drop_index("ix_netflow_records_window", table_name="netflow_records")
    op.drop_table("netflow_records")
    op.execute("DROP POLICY IF EXISTS route_records_team_isolation ON route_records;")
    op.drop_index("ix_route_records_latest", table_name="route_records")
    op.drop_table("route_records")
