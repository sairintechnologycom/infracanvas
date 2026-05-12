"""011_firewall_tables: firewall_ruleset_snapshots + firewall_rules + firewall_nat_rules + firewall_objects.

Phase 11 — D-08/D-09/D-10/D-15 (snapshot-per-pull hybrid schema, agent-minted snapshot_id).

Phase 12 forward-feed contract (D-15) — DO NOT RENAME these columns without
coordinated migration + Phase 12 path-computation update:
  firewall_rules: src_cidr, dst_cidr, action, protocol, ports, src_zone, dst_zone, position
  firewall_nat_rules: src_translation, dst_translation, interface_in, interface_out

RLS posture (D-08 + T-11-02-02):
  - firewall_ruleset_snapshots carries `team_id` directly + a USING/WITH CHECK
    policy keyed on current_setting('app.current_team_id', true)::uuid.
  - Child tables (firewall_rules / firewall_nat_rules / firewall_objects) have
    no `team_id` column (D-08 keeps schema lean); their `_team_isolation` policy
    enforces team-scope via `snapshot_id IN (SELECT snapshot_id FROM
    firewall_ruleset_snapshots WHERE team_id = ...)` so a tenant cannot see
    child rows whose parent belongs to a different team.

Retention (T-11-02-05 mitigation): firewall_ruleset_snapshots rows are pruned
by app.tasks.firewall_prune at FIREWALL_SNAPSHOT_TTL_DAYS (default 14). Child
rows cascade via FK ondelete=CASCADE — a single parent DELETE removes them.

Revision ID: 011_firewall_tables
Revises: 010_dc_sites
Create Date: 2026-05-12
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011_firewall_tables"
down_revision: str | None = "010_dc_sites"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. firewall_ruleset_snapshots — parent table, team-scoped.
    #    snapshot_id is agent-minted (RESEARCH Pattern 2) — backend uses
    #    ON CONFLICT DO NOTHING on snapshot_id (in route handlers, Plan 11-03)
    #    to make the three push endpoints independent and idempotent.
    op.create_table(
        "firewall_ruleset_snapshots",
        sa.Column(
            "snapshot_id",
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
            "site_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dc_sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("firewall_id", sa.Text(), nullable=False),
        sa.Column("vendor", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("snapshot_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_fw_ruleset_team_id",
        "firewall_ruleset_snapshots",
        ["team_id"],
    )
    # Composite index for Plan 11-04's DISTINCT ON / latest-per-firewall read.
    op.create_index(
        "ix_fw_ruleset_latest",
        "firewall_ruleset_snapshots",
        ["site_id", "firewall_id", sa.text("snapshot_ts DESC")],
    )
    op.execute("ALTER TABLE firewall_ruleset_snapshots ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE firewall_ruleset_snapshots FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY firewall_ruleset_snapshots_team_isolation ON firewall_ruleset_snapshots
          USING (team_id = current_setting('app.current_team_id', true)::uuid)
          WITH CHECK (team_id = current_setting('app.current_team_id', true)::uuid);
        """
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON firewall_ruleset_snapshots TO infracanvas_app;")

    # 2. firewall_rules — child, team-scope enforced via parent JOIN in policy.
    op.create_table(
        "firewall_rules",
        sa.Column(
            "rule_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "snapshot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "firewall_ruleset_snapshots.snapshot_id", ondelete="CASCADE"
            ),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("src_zone", sa.Text(), nullable=True),
        sa.Column("dst_zone", sa.Text(), nullable=True),
        sa.Column("src_cidr", sa.Text(), nullable=False),
        sa.Column("dst_cidr", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("protocol", sa.Text(), nullable=True),
        sa.Column("ports", sa.Text(), nullable=True),
        sa.Column("raw_blob", postgresql.JSONB(), nullable=False),
    )
    op.create_index(
        "ix_fw_rules_snapshot",
        "firewall_rules",
        ["snapshot_id", "position"],
    )
    op.execute("ALTER TABLE firewall_rules ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE firewall_rules FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY firewall_rules_team_isolation ON firewall_rules
          USING (
            snapshot_id IN (
              SELECT snapshot_id FROM firewall_ruleset_snapshots
              WHERE team_id = current_setting('app.current_team_id', true)::uuid
            )
          )
          WITH CHECK (
            snapshot_id IN (
              SELECT snapshot_id FROM firewall_ruleset_snapshots
              WHERE team_id = current_setting('app.current_team_id', true)::uuid
            )
          );
        """
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON firewall_rules TO infracanvas_app;"
    )

    # 3. firewall_nat_rules — same shape as firewall_rules with NAT columns.
    op.create_table(
        "firewall_nat_rules",
        sa.Column(
            "nat_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "snapshot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "firewall_ruleset_snapshots.snapshot_id", ondelete="CASCADE"
            ),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("src_translation", sa.Text(), nullable=True),
        sa.Column("dst_translation", sa.Text(), nullable=True),
        sa.Column("interface_in", sa.Text(), nullable=True),
        sa.Column("interface_out", sa.Text(), nullable=True),
        sa.Column("raw_blob", postgresql.JSONB(), nullable=False),
    )
    op.create_index(
        "ix_fw_nat_snapshot",
        "firewall_nat_rules",
        ["snapshot_id", "position"],
    )
    op.execute("ALTER TABLE firewall_nat_rules ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE firewall_nat_rules FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY firewall_nat_rules_team_isolation ON firewall_nat_rules
          USING (
            snapshot_id IN (
              SELECT snapshot_id FROM firewall_ruleset_snapshots
              WHERE team_id = current_setting('app.current_team_id', true)::uuid
            )
          )
          WITH CHECK (
            snapshot_id IN (
              SELECT snapshot_id FROM firewall_ruleset_snapshots
              WHERE team_id = current_setting('app.current_team_id', true)::uuid
            )
          );
        """
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON firewall_nat_rules TO infracanvas_app;")

    # 4. firewall_objects — host/network/group/service definitions (D-09).
    op.create_table(
        "firewall_objects",
        sa.Column(
            "object_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "snapshot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "firewall_ruleset_snapshots.snapshot_id", ondelete="CASCADE"
            ),
            nullable=False,
        ),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("raw_blob", postgresql.JSONB(), nullable=False),
    )
    op.create_index(
        "ix_fw_objects_snapshot",
        "firewall_objects",
        ["snapshot_id", "kind", "name"],
    )
    op.execute("ALTER TABLE firewall_objects ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE firewall_objects FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY firewall_objects_team_isolation ON firewall_objects
          USING (
            snapshot_id IN (
              SELECT snapshot_id FROM firewall_ruleset_snapshots
              WHERE team_id = current_setting('app.current_team_id', true)::uuid
            )
          )
          WITH CHECK (
            snapshot_id IN (
              SELECT snapshot_id FROM firewall_ruleset_snapshots
              WHERE team_id = current_setting('app.current_team_id', true)::uuid
            )
          );
        """
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON firewall_objects TO infracanvas_app;"
    )


def downgrade() -> None:
    # Reverse order — child tables first so FK constraints don't block the drop.
    op.execute("DROP POLICY IF EXISTS firewall_objects_team_isolation ON firewall_objects;")
    op.drop_table("firewall_objects")
    op.execute("DROP POLICY IF EXISTS firewall_nat_rules_team_isolation ON firewall_nat_rules;")
    op.drop_table("firewall_nat_rules")
    op.execute("DROP POLICY IF EXISTS firewall_rules_team_isolation ON firewall_rules;")
    op.drop_table("firewall_rules")
    op.execute("DROP POLICY IF EXISTS firewall_ruleset_snapshots_team_isolation ON firewall_ruleset_snapshots;")
    op.drop_table("firewall_ruleset_snapshots")
