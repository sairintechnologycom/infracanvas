"""Phase 12 D-16 — TTL prune for computed_paths and resolved findings.

Mirrors ``backend/app/queue/tasks/firewall_prune.py`` — daily team-walk
under the RLS GUC. The job performs three DELETEs per team:

  - ``DELETE FROM computed_paths WHERE computed_at < NOW() - INTERVAL N days``
    (default 14, mirrors firewall snapshot TTL).
  - ``DELETE FROM asymmetry_findings WHERE resolved_at IS NOT NULL
    AND resolved_at < NOW() - INTERVAL M days`` — D-16 lifecycle keeps
    open findings forever and sweeps resolved ones after audit retention.
  - ``DELETE FROM path_divergence_findings`` with the same resolved-only
    predicate.

Env vars:
  ``PATH_SNAPSHOT_TTL_DAYS`` — default 14 (mirrors Phase 11 firewall prune).
  ``PATH_FINDING_TTL_DAYS``  — default 30 (resolved findings kept 30d for audit).

Cron: ``0 4 * * *`` UTC (one hour after firewall_prune at ``0 3``,
avoids contention).

RLS posture: the prune walks every team in ``teams`` and sets
``app.current_team_id`` to that team's id via parameter-bound
``set_config('app.current_team_id', :t, true)`` before each DELETE.
The whole prune runs inside the application's NOBYPASSRLS trust posture.
"""
from __future__ import annotations

import os

import structlog
from sqlalchemy import text

from app.db.session import get_sessionmaker
from app.queue.broker import broker

_log = structlog.get_logger("app.tasks.path_compute_prune")


@broker.task(task_name="path_compute_prune", schedule=[{"cron": "0 4 * * *"}])
async def prune_path_compute() -> dict[str, int]:
    """Daily 04:00 UTC prune of computed_paths + resolved findings.

    Returns
    -------
    dict
        ``{"paths_deleted": P, "findings_deleted": F, "ttl_days": D}``
        — P is the total computed_paths rows pruned across all teams,
        F is the total resolved findings rows (asymmetry + divergence)
        pruned, D is the resolved path TTL.

    Notes
    -----
    * Both TTL values are cast to ``int`` before being interpolated into
      the SQL ``INTERVAL`` literal — no SQL-injection surface (the value
      is an int by the time it touches the query string).
    * ``team_id`` IS parameter-bound (``:t``) into ``set_config``; never
      interpolated.
    * Each team gets its own transaction so a partial failure does not
      roll back already-pruned teams.
    """
    path_ttl_days = int(os.environ.get("PATH_SNAPSHOT_TTL_DAYS", "14"))
    finding_ttl_days = int(os.environ.get("PATH_FINDING_TTL_DAYS", "30"))
    sm = get_sessionmaker()
    paths_deleted = 0
    findings_deleted = 0
    async with sm() as session:
        team_rows = (await session.execute(text("SELECT id FROM teams"))).all()
        team_ids = [str(row[0]) for row in team_rows]
        for team_id in team_ids:
            async with session.begin():
                await session.execute(
                    text("SELECT set_config('app.current_team_id', :t, true)"),
                    {"t": team_id},
                )
                r1 = await session.execute(
                    text(
                        "DELETE FROM computed_paths "
                        f"WHERE computed_at < NOW() - INTERVAL '{path_ttl_days} days'"
                    )
                )
                paths_deleted += r1.rowcount or 0
                r2 = await session.execute(
                    text(
                        "DELETE FROM asymmetry_findings "
                        "WHERE resolved_at IS NOT NULL "
                        f"AND resolved_at < NOW() - INTERVAL '{finding_ttl_days} days'"
                    )
                )
                findings_deleted += r2.rowcount or 0
                r3 = await session.execute(
                    text(
                        "DELETE FROM path_divergence_findings "
                        "WHERE resolved_at IS NOT NULL "
                        f"AND resolved_at < NOW() - INTERVAL '{finding_ttl_days} days'"
                    )
                )
                findings_deleted += r3.rowcount or 0
    _log.info(
        "path_compute_prune_complete",
        paths_deleted=paths_deleted,
        findings_deleted=findings_deleted,
        path_ttl_days=path_ttl_days,
        finding_ttl_days=finding_ttl_days,
        teams_scanned=len(team_ids),
    )
    return {
        "paths_deleted": paths_deleted,
        "findings_deleted": findings_deleted,
        "ttl_days": path_ttl_days,
    }
