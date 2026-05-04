"""Shared scan finalization logic — Stripe metering + row state flip.

Used by:

* :func:`app.routes.scans.commit_scan` — CLI direct upload path
  (Phase 6 D-09). The route INSERTs the row pre-finalized in ``ready``
  state and then calls :func:`fire_scan_meter_or_502` for the meter
  event so a Stripe failure cleanly translates to HTTP 502.
* :func:`app.queue.tasks.scan_repo.scan_repo` — GitHub-triggered
  worker scan (Phase 7.5 D-13). The worker INSERTed the row in
  ``pending`` state at enqueue time, then calls :func:`finalize_scan`
  to UPDATE → ``ready`` and fire the meter atomically.

Phase 6 D-08/D-09 invariant: every committed scan row carries exactly
one Stripe meter event for the same ``scan_id``. The two helpers below
preserve that invariant from both code paths — extracted here so the
SDK-boundary stub (see ``stub_stripe_meter`` in ``tests/test_scans.py``
and ``tests/test_services_scans.py``) can verify it in isolation.

Idempotency posture (matches D-09 / TMM-02 dual-key Stripe semantics):

* :func:`finalize_scan` uses ``UPDATE … WHERE status != 'ready'``
  RETURNING — a second call on a row already promoted to ``ready`` is
  a silent no-op (no double-meter).
* :func:`fire_scan_meter_or_502` is a thin wrapper around
  :func:`record_scan_meter_event` that translates ``StripeError`` into
  ``HTTPException(502, "meter_failed")`` for the route caller. The
  worker uses :func:`finalize_scan` directly and lets the StripeError
  propagate so SmartRetryMiddleware can retry the job.

Tx ownership: callers manage the surrounding ``session.begin()`` and
the ``app.current_team_id`` GUC — these helpers DO NOT open or commit
transactions of their own. Required so the meter call lives inside the
same DB tx that flipped the row's state (D-09 invariant: a Stripe
failure must roll back the state flip).
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

import stripe
import structlog
from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.stripe_meter import record_scan_meter_event

_log = structlog.get_logger("app.services.scans")


async def finalize_scan(
    session: AsyncSession,
    *,
    scan_id: UUID | str,
    team_id: UUID | str,
    stripe_customer_id: str,
    r2_key: str,
    sha256: str,
    size_bytes: int,
    summary_json: dict[str, Any] | None = None,
) -> None:
    """Flip a pending scan row to ``ready`` and fire its Stripe meter event.

    Idempotent: if the row is already ``ready``, the UPDATE matches zero
    rows and the meter call is skipped (the meter already fired on the
    first invocation).

    Caller MUST be inside ``session.begin()`` and MUST have set
    ``app.current_team_id`` already so RLS allows the UPDATE. We do not
    manage tx boundaries here — the caller is responsible for commit /
    rollback (a Stripe failure raised here will abort the enclosing tx,
    preserving the D-09 "no row without a meter" invariant).

    Args:
        session: open async SQLAlchemy session inside an active begin().
        scan_id: UUIDv7 of the pending scan row.
        team_id: owning team UUID — kept for log context (RLS already
            enforces isolation via ``app.current_team_id``).
        stripe_customer_id: Stripe customer id from
            ``Team.stripe_customer_id``; passed straight to
            :func:`record_scan_meter_event`.
        r2_key: final R2 object key for the scan blob.
        sha256: hex SHA-256 of the uploaded blob.
        size_bytes: blob size in bytes.
        summary_json: optional pre-computed scan summary; persisted to
            the row's ``summary_json`` JSONB column for fast list-page
            rendering without re-fetching the blob.

    Raises:
        stripe.error.StripeError: any Stripe failure. The enclosing
            ``session.begin()`` will roll back, leaving the row in
            ``pending`` (or whatever state it was in) so a retry path
            can re-attempt.
    """
    sid = str(scan_id)
    tid = str(team_id)

    result = await session.execute(
        text(
            """
            UPDATE scans
            SET status = 'ready',
                r2_key = :r2_key,
                sha256 = :sha256,
                size_bytes = :size_bytes,
                summary_json = CAST(:summary_json AS jsonb)
            WHERE id = :id AND status != 'ready'
            RETURNING id
            """
        ),
        {
            "id": sid,
            "r2_key": r2_key,
            "sha256": sha256,
            "size_bytes": size_bytes,
            # asyncpg won't cast a Python dict to jsonb implicitly via the
            # bound parameter — pass JSON text and CAST inside the SQL.
            "summary_json": (
                None if summary_json is None else _json_dumps(summary_json)
            ),
        },
    )
    updated = result.scalar_one_or_none()
    if updated is None:
        _log.info("finalize_scan.already_ready", scan_id=sid, team_id=tid)
        return

    try:
        await record_scan_meter_event(
            scan_id=sid, stripe_customer_id=stripe_customer_id or ""
        )
    except stripe.error.StripeError as e:  # type: ignore[attr-defined]
        _log.error(
            "finalize_scan.meter_failed",
            scan_id=sid,
            team_id=tid,
            error=repr(e),
        )
        raise


async def fire_scan_meter_or_502(
    *, scan_id: UUID | str, stripe_customer_id: str
) -> None:
    """Route-side meter call: translate Stripe failures into HTTP 502.

    Used by :func:`app.routes.scans.commit_scan` after the row INSERT —
    the route INSERTs in ``ready`` state directly (CLI commit path) so
    only the meter step needs the 502 translation. Worker callers should
    use :func:`finalize_scan` instead.

    Raises:
        fastapi.HTTPException: status 502 ``meter_failed`` on Stripe error.
    """
    try:
        await record_scan_meter_event(
            scan_id=str(scan_id),
            stripe_customer_id=stripe_customer_id or "",
        )
    except stripe.error.StripeError as e:  # type: ignore[attr-defined]
        _log.error("meter_event_failed", scan_id=str(scan_id), error=repr(e))
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "meter_failed"
        ) from e


def _json_dumps(payload: dict[str, Any]) -> str:
    """Local JSON encoder — kept private so callers don't depend on it."""
    import json

    return json.dumps(payload, separators=(",", ":"), default=str)
