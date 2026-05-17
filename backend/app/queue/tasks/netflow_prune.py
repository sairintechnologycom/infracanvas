"""Phase 12 — NetFlow record TTL prune (24h default, every 15 min on offset).

Flow volume is orders of magnitude larger than route/firewall data; TTL
defaults to 24h, not 14d. Cron offset ``7,22,37,52 * * * *`` avoids
colliding with the path_compute ``*/15`` schedule (Pitfall 5 —
SELECT-while-DELETE race window minimized).

Env vars:
  ``NETFLOW_RECORD_TTL_HOURS`` — default 24.

RLS posture: walks every team in ``teams`` and sets
``app.current_team_id`` via parameter-bound
``set_config('app.current_team_id', :t, true)`` before issuing the DELETE.
"""
from __future__ import annotations

import os

import structlog
from sqlalchemy import text

from app.db.session import get_sessionmaker
from app.queue.broker import broker

_log = structlog.get_logger("app.tasks.netflow_prune")


@broker.task(task_name="netflow_prune", schedule=[{"cron": "7,22,37,52 * * * *"}])
async def prune_netflow_records() -> dict[str, int]:
    """Every 15 min (offset from path_compute) — DELETE netflow_records older than TTL.

    Returns
    -------
    dict
        ``{"deleted": N, "ttl_hours": H}`` — N is the total rows pruned
        across all teams; H is the resolved TTL.

    Notes
    -----
    * ``ttl_hours`` is cast to ``int`` before being interpolated into the
      SQL ``INTERVAL`` literal — no SQL-injection surface.
    * ``team_id`` IS parameter-bound (``:t``) into ``set_config``; never
      interpolated.
    """
    ttl_hours = int(os.environ.get("NETFLOW_RECORD_TTL_HOURS", "24"))
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
                        "DELETE FROM netflow_records "
                        f"WHERE collected_at < NOW() - INTERVAL '{ttl_hours} hours'"
                    )
                )
                total_deleted += result.rowcount or 0
    _log.info(
        "netflow_prune_complete",
        records_deleted=total_deleted,
        ttl_hours=ttl_hours,
        teams_scanned=len(team_ids),
    )
    return {"deleted": total_deleted, "ttl_hours": ttl_hours}
