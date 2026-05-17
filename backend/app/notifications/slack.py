"""Team-scoped Slack webhook dispatcher (extracted from scan_repo.py:299-341).

Two callers in Phase 12:
* scan_repo (Phase 8 Critical-findings alert) — collapses inline block.
* path_compute (Phase 12 NFN-02 asymmetry alert) — new call site (Plan 12-06).

Failure posture (locked from Phase 8 behavior):
* Swallow + structlog.warn + sentry_sdk.capture_exception.
* Never re-raise — a bad Slack endpoint must NOT abort the calling task.

Pattern G logging allowlist:
* Logs {log_ctx_key}.slack_alert_sent (no fields) on success.
* Logs {log_ctx_key}.slack_alert_failed with error=repr(exc) — never logs
  the webhook URL or message content (operator-private).
"""
from __future__ import annotations

import httpx
import sentry_sdk
import structlog
from sqlalchemy import text

from app.db.session import get_sessionmaker

_log = structlog.get_logger("app.notifications.slack")


async def send_team_slack(
    *,
    team_id: str,
    message: str,
    log_ctx_key: str,
) -> None:
    """Look up team's slack_webhook_url under RLS, POST message, swallow + Sentry-capture.

    Args:
        team_id: UUID string; sets ``app.current_team_id`` RLS GUC.
        message: Slack JSON ``text`` payload — already formatted by caller.
        log_ctx_key: prefix for structlog event names (e.g. ``scan_repo``,
            ``path_compute``) so traceability survives the extraction.

    Behaviour:
        * No-op (returns without HTTP) when the team row is missing or has
          ``slack_webhook_url IS NULL``.
        * Posts ``json={"text": message}`` with ``timeout=5.0``.
        * On success: emits ``{log_ctx_key}.slack_alert_sent`` (no fields).
        * On failure: emits ``{log_ctx_key}.slack_alert_failed`` with
          ``error=repr(exc)`` and calls ``sentry_sdk.capture_exception``.
          Never re-raises — the caller (taskiq task) must not abort on a
          bad Slack endpoint.
    """
    sm = get_sessionmaker()
    async with sm() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": team_id},
        )
        row = (
            await session.execute(
                text("SELECT slack_webhook_url FROM teams WHERE id = :id"),
                {"id": team_id},
            )
        ).one_or_none()
    if row is None or row.slack_webhook_url is None:
        return
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                row.slack_webhook_url,
                json={"text": message},
                timeout=5.0,
            )
        _log.info(f"{log_ctx_key}.slack_alert_sent")
    except Exception as exc:  # noqa: BLE001 — Phase 8 swallow contract
        _log.warning(f"{log_ctx_key}.slack_alert_failed", error=repr(exc))
        sentry_sdk.capture_exception(exc)
