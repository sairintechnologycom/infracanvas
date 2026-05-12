"""TTL prune for ``firewall_ruleset_snapshots`` (Phase 11 RESEARCH Risk Landmine #2).

Default retention is 14 days. Override via the ``FIREWALL_SNAPSHOT_TTL_DAYS``
env var (per-customer override path for longer retention contracts).

Child rows (``firewall_rules`` / ``firewall_nat_rules`` / ``firewall_objects``)
cascade via FK ``ondelete=CASCADE`` (migration 011) — a single ``DELETE FROM
firewall_ruleset_snapshots`` is sufficient to sweep all four tables.

RLS posture: the prune walks every team in ``teams`` and sets
``app.current_team_id`` to that team's id (via parameterized
``set_config('app.current_team_id', :t, true)``) before issuing the DELETE.
This keeps the prune entirely inside the same trust posture as the rest of
the application (no BYPASSRLS role required).

T-11-02-05 mitigation: prevents the storage explosion path documented in
``11-RESEARCH.md`` §"Risk Landmines" #2 (~800GB / 30 days worst case at the
upper-bound enterprise rule-base / pull-rate envelope).
"""
from __future__ import annotations

import os

import structlog
from sqlalchemy import text

from app.db.session import get_sessionmaker
from app.queue.broker import broker

_log = structlog.get_logger("app.tasks.firewall_prune")


@broker.task(task_name="firewall_prune")
async def prune_firewall_snapshots() -> dict[str, int]:
    """Delete ``firewall_ruleset_snapshots`` rows older than TTL.

    Returns
    -------
    dict
        ``{"deleted": N, "ttl_days": D}`` — N is the total parent rows
        pruned across all teams. D is the resolved TTL (env override or
        the 14-day default).

    Notes
    -----
    * ``ttl_days`` is sourced from ``FIREWALL_SNAPSHOT_TTL_DAYS`` (env) and
      cast to ``int`` before being interpolated into the SQL ``INTERVAL``
      literal — no SQL-injection surface (the value is already an int by
      the time it touches the query string).
    * ``team_id`` IS parameter-bound (``:t``) into ``set_config``; never
      interpolated.
    * Runs in a single async session; each team gets its own transaction
      so a partial failure does not roll back already-pruned teams.
    """
    ttl_days = int(os.environ.get("FIREWALL_SNAPSHOT_TTL_DAYS", "14"))
    sm = get_sessionmaker()
    total_deleted = 0
    async with sm() as session:
        team_rows = (await session.execute(text("SELECT id FROM teams"))).all()
        team_ids = [str(row[0]) for row in team_rows]
        for team_id in team_ids:
            async with session.begin():
                await session.execute(
                    text("SELECT set_config('app.current_team_id', :t, true)"),
                    {"t": team_id},
                )
                result = await session.execute(
                    text(
                        "DELETE FROM firewall_ruleset_snapshots "
                        f"WHERE snapshot_ts < NOW() - INTERVAL '{ttl_days} days'"
                    )
                )
                total_deleted += result.rowcount or 0
    _log.info(
        "firewall_snapshots_pruned",
        deleted=total_deleted,
        ttl_days=ttl_days,
        teams_scanned=len(team_ids),
    )
    return {"deleted": total_deleted, "ttl_days": ttl_days}
