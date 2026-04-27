"""Clerk → Svix webhook signature verification + event dispatch.

`/v1/webhooks/clerk` (see :mod:`app.routes.webhooks`) reads the raw request
bytes, builds a ``svix-id``/``svix-timestamp``/``svix-signature`` headers
dict, and calls :func:`verify_and_dispatch`. The Svix library performs
timing-safe HMAC compare with ±5min timestamp skew tolerance — bad
signature raises :class:`svix.webhooks.WebhookVerificationError`, which we
translate to ``PermissionError`` for the route layer to convert to 401.

Handlers:

* ``organization.created`` — INSERT into ``teams`` with
  ``ON CONFLICT DO NOTHING`` (idempotent across Svix retries / dupes).
  Also creates a Stripe customer (idempotent via metadata search).
* ``organization.updated`` — resolve team via the SECURITY DEFINER
  ``team_by_clerk_org`` function, ``SET LOCAL`` the team GUC, then
  UPDATE the name.
* ``organization.deleted`` — same path; soft-delete by renaming to
  ``[deleted]`` (Phase 6 doesn't hard-delete to avoid orphaning scans).

All other event types are silently swallowed — Clerk may dispatch more
event types than we subscribe to, and a ``500`` would force Svix into
retry loops for events we deliberately don't care about.
"""

from __future__ import annotations

from typing import Any

import stripe
import structlog
from sqlalchemy import insert as sa_insert
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession
from svix.webhooks import Webhook, WebhookVerificationError

from app.db.models import Team
from app.settings import settings
from app.util.ids import new_uuid7

_log = structlog.get_logger("app.webhooks")


def _verifier() -> Webhook:
    """Construct a Svix Webhook verifier with the configured secret."""
    return Webhook(settings.clerk_webhook_secret)


async def verify_and_dispatch(
    body: bytes, headers: dict[str, str], session: AsyncSession
) -> None:
    """Verify the Svix signature and dispatch to a per-event handler.

    Raises:
        PermissionError: signature invalid / missing headers / timestamp skew.
            Route layer translates to 401.
    """
    try:
        payload = _verifier().verify(body, headers)
    except WebhookVerificationError as e:
        raise PermissionError("bad_signature") from e

    evt_type = payload.get("type")
    data = payload.get("data") or {}
    _log.info(
        "clerk_webhook",
        event_type=evt_type,
        clerk_org_id=data.get("id"),
    )

    if evt_type == "organization.created":
        await _upsert_team_on_created(session, data)
    elif evt_type == "organization.updated":
        await _upsert_team_on_updated(session, data)
    elif evt_type == "organization.deleted":
        await _soft_delete_team(session, data)
    # Other event types intentionally swallowed (return 200 from caller).


def _create_stripe_customer(clerk_org_id: str, name: str) -> str:
    """Create or retrieve a Stripe customer for ``clerk_org_id``.

    Idempotent: searches by ``metadata['clerk_org_id']`` first; only POSTs
    a new customer if none found. Falls through gracefully when the search
    API is unavailable (e.g. older Stripe accounts that haven't enabled it).
    """
    stripe.api_key = settings.stripe_secret_key
    try:
        found = stripe.Customer.search(
            query=f"metadata['clerk_org_id']:'{clerk_org_id}'"
        )
        if getattr(found, "data", None):
            return found.data[0].id
    except Exception:  # noqa: BLE001 — search may not be enabled; fall back to create
        pass

    cust = stripe.Customer.create(
        name=name,
        metadata={"clerk_org_id": clerk_org_id},
    )
    return cust.id


async def _upsert_team_on_created(
    session: AsyncSession, data: dict[str, Any]
) -> None:
    """Create the team row + a matching Stripe customer.

    Idempotency strategy: probe via the SECURITY DEFINER ``team_by_clerk_org``
    function first (RLS-safe lookup); if a row already exists for this
    clerk_org_id (Svix retry / dupe delivery), no-op. Otherwise, plain INSERT
    permitted by the ``teams_webhook_insert`` policy (WITH CHECK true).

    Why not ``ON CONFLICT DO NOTHING``: PostgreSQL's INSERT...ON CONFLICT
    executor checks the UPDATE policy WITH CHECK clause for the conflict
    target row even with DO NOTHING (the planner pre-evaluates the UPDATE
    branch). Our strict ``teams_mutate_update`` policy requires the
    ``app.current_team_id`` GUC to match — fails in the webhook path because
    no GUC is set. Probe-then-insert sidesteps this without weakening the
    UPDATE policy.

    Authorization is supplied entirely by the upstream Svix signature
    verification — only this code path can reach this INSERT.
    """
    clerk_org_id = data["id"]
    name = data.get("name") or clerk_org_id

    # Idempotency probe — SECURITY DEFINER bypasses RLS for this read only.
    existing = (
        await session.execute(
            text("SELECT (team_by_clerk_org(:org)).id AS id"),
            {"org": clerk_org_id},
        )
    ).first()
    if existing is not None and existing.id is not None:
        _log.info("org_created_replay_ignored", clerk_org_id=clerk_org_id)
        return

    stripe_customer_id = _create_stripe_customer(clerk_org_id, name)

    await session.execute(
        sa_insert(Team).values(
            id=new_uuid7(),
            clerk_org_id=clerk_org_id,
            name=name,
            stripe_customer_id=stripe_customer_id,
        )
    )


async def _resolve_team_id(session: AsyncSession, clerk_org_id: str) -> str | None:
    """Look up team.id via team_by_clerk_org() SECURITY DEFINER function.

    Returns None when the team row does not exist (e.g. a stray
    ``organization.updated`` arrives before the corresponding
    ``organization.created`` was processed). Caller logs and returns 200.
    """
    row = (
        await session.execute(
            text("SELECT (team_by_clerk_org(:org)).id AS id"),
            {"org": clerk_org_id},
        )
    ).first()
    if row is None or row.id is None:
        return None
    return str(row.id)


async def _upsert_team_on_updated(
    session: AsyncSession, data: dict[str, Any]
) -> None:
    """Update team name on Clerk org rename.

    Resolves team.id via team_by_clerk_org() helper, sets the GUC, then
    issues UPDATE. Without the GUC the strict ``teams_mutate_update``
    policy would block the change.
    """
    clerk_org_id = data["id"]
    name = data.get("name") or clerk_org_id

    team_id = await _resolve_team_id(session, clerk_org_id)
    if team_id is None:
        _log.warning("org_updated_team_missing", clerk_org_id=clerk_org_id)
        return

    # Use set_config() function so the bind parameter survives — asyncpg's
    # wire protocol cannot parameterize ``SET LOCAL = $1`` directly.
    # Third arg ``true`` = is_local (tx-scoped), matching SET LOCAL semantics.
    await session.execute(
        text("SELECT set_config('app.current_team_id', :t, true)"),
        {"t": team_id},
    )
    await session.execute(
        update(Team).where(Team.clerk_org_id == clerk_org_id).values(name=name)
    )


async def _soft_delete_team(
    session: AsyncSession, data: dict[str, Any]
) -> None:
    """Soft-delete on org deletion by renaming to ``[deleted]``.

    Phase 6 does not hard-delete: scans referencing the team would be
    orphaned, and we may want to retain billing history. A future plan
    can introduce a proper deleted_at column.
    """
    clerk_org_id = data["id"]
    team_id = await _resolve_team_id(session, clerk_org_id)
    if team_id is None:
        return

    # set_config() — see _upsert_team_on_updated for asyncpg-parameter rationale.
    await session.execute(
        text("SELECT set_config('app.current_team_id', :t, true)"),
        {"t": team_id},
    )
    await session.execute(
        update(Team)
        .where(Team.clerk_org_id == clerk_org_id)
        .values(name="[deleted]")
    )
