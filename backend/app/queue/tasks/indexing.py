"""``enqueue_scan_indexing`` — post-commit denormalization of scans.summary_json.

Background contract (Plan 06-06):

1. HTTP commit handler at ``POST /v1/scans/{id}/commit`` finishes the atomic
   tx (DB INSERT + Stripe meter) and calls
   ``enqueue_scan_indexing.kicker().with_labels(request_id=rid).kiq(scan_id=...)``
   AFTER the DB tx commits.
2. The worker process pops the message off Redis. ``RequestIdMiddleware``
   rebinds ``request_id`` + ``scan_id`` into structlog contextvar so all
   subsequent logs in the task body share the original HTTP trace id.
3. The task body:

   a. Looks up the scan's ``team_id`` via the SECURITY DEFINER helper
      ``scan_team_id(uuid)`` (migration 004). The worker has no Clerk
      principal — there is no upstream ``resolve_team_from_clerk_org`` to
      consult — and a regular ``SELECT * FROM scans WHERE id=...`` would
      be blocked by RLS (no GUC set yet).
   b. Opens a team-scoped session: ``set_config('app.current_team_id',
      <team_id>, true)`` so the rest of the work runs under normal RLS
      policy, exactly like an HTTP-side team-scoped handler.
   c. Downloads the scan blob from R2 (``r2.get_bytes``), validates against
      :class:`infracanvas.graph.models.ResourceGraph`, computes the
      shared-with-CLI ``compute_summary``, and writes the JSON dict into
      ``scans.summary_json``.

The Phase 7 scan-list UI reads ``summary_json`` directly so the list
endpoint never re-parses scan blobs at request time.

Retries: ``retry_on_error=True, max_retries=3, delay=5`` — rides on the
broker's :class:`SmartRetryMiddleware` (jittered exponential backoff,
capped at 120 s). Validation errors are NOT retryable (the blob is
permanently malformed), so we ``return`` rather than ``raise`` after
:class:`pydantic.ValidationError` — the task ends success-state, summary
stays null, on-call is notified via the ``indexing_validation_failed``
log line.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog
from botocore.exceptions import ClientError
from pydantic import ValidationError
from sqlalchemy import select, text, update

from infracanvas.graph.models import ResourceGraph
from infracanvas.graph.summary import compute_summary

from app.db.models import Scan
from app.db.session import get_sessionmaker
from app.queue.broker import broker
from app.storage import r2

_log = structlog.get_logger("app.worker.indexing")


@broker.task(retry_on_error=True, max_retries=3, delay=5)
async def enqueue_scan_indexing(scan_id: str) -> None:
    """Populate ``scans.summary_json`` for a freshly-committed scan.

    Two-phase DB access:

    * Phase 1 — team_id discovery via ``scan_team_id(uuid)`` SECURITY
      DEFINER helper. Worker has no Clerk principal, so RLS would block a
      direct select. The helper is locked down at GRANT level to the
      application role.
    * Phase 2 — team-scoped session that does the actual UPDATE under
      normal RLS policy via ``set_config('app.current_team_id', :t, true)``.

    R2 reads use :func:`asyncio.to_thread` because boto3 is blocking; we
    must not block the worker event loop.

    Returns ``None``. Raises (so SmartRetryMiddleware retries) only on
    transient failures (R2 ``ClientError``, DB connectivity issues).
    Validation failures and "scan vanished" cases return cleanly with a
    structured log so retries don't pile up on a permanent fault.
    """
    scan_uuid = uuid.UUID(scan_id)
    sm = get_sessionmaker()

    # ---- Phase 1: team_id lookup via SECURITY DEFINER helper. -----------
    # Run under raw_session() (no GUC); the helper bypasses RLS by design
    # and returns only the team_id column for the matching row.
    async with sm() as session:
        async with session.begin():
            result = await session.execute(
                text("SELECT scan_team_id(:s)"),
                {"s": str(scan_uuid)},
            )
            team_id: Any = result.scalar_one_or_none()

    if team_id is None:
        # Scan row vanished between commit and indexing. Possible only if
        # an upstream cleanup ran in the gap, which Phase 6 has no path
        # for; log + bail without retrying.
        _log.warning("scan_missing_for_indexing", scan_id=scan_id)
        return

    # ---- Phase 2: team-scoped session, the canonical RLS-scoped pattern.
    async with sm() as session:
        async with session.begin():
            # ``set_config(..., is_local=true)`` matches the HTTP-side
            # ``team_scoped_session`` pattern; asyncpg-safe parameter bind.
            await session.execute(
                text("SELECT set_config('app.current_team_id', :t, true)"),
                {"t": str(team_id)},
            )

            scan_row = (
                await session.execute(
                    select(Scan).where(Scan.id == scan_uuid)
                )
            ).scalar_one_or_none()
            if scan_row is None:
                # Should never happen — Phase 1 said the row exists. If it
                # does, RLS likely changed under us; do not retry.
                _log.warning("scan_disappeared_phase2", scan_id=scan_id)
                return

            # R2 fetch — blocking boto3 → off the event loop.
            try:
                blob = await asyncio.to_thread(r2.get_bytes, scan_row.r2_key)
            except ClientError as e:
                # Transient R2 fault → raise so SmartRetryMiddleware retries.
                _log.warning(
                    "indexing_r2_fetch_failed",
                    scan_id=scan_id,
                    r2_key=scan_row.r2_key,
                    error=repr(e),
                )
                raise

            try:
                graph = ResourceGraph.model_validate_json(blob)
            except ValidationError as e:
                # Permanent — the blob shape is wrong; retrying won't fix.
                # Log with bounded errors[] so we don't blow the log line size.
                _log.error(
                    "indexing_validation_failed",
                    scan_id=scan_id,
                    errors=e.errors()[:5],
                )
                return

            summary = compute_summary(graph)
            await session.execute(
                update(Scan)
                .where(Scan.id == scan_uuid)
                .values(summary_json=summary.model_dump())
            )
            _log.info(
                "indexing_complete",
                scan_id=scan_id,
                total_resources=summary.total_resources,
                score=summary.score,
            )
