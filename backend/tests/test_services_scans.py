"""Unit tests for ``app/services/scans.py`` — Phase 7.5 Plan 05.

The ``finalize_scan`` helper is invoked from BOTH the existing
``commit_scan`` route (CLI direct upload path, D-09) AND the future
``scan_repo`` taskiq job (Phase 7.5 D-13). The invariant we lock here:

  every committed scan row fires exactly one Stripe meter event in the
  same logical step that flips the row to ``status='ready'``.

Idempotency: a second call on a row already in ``ready`` is a no-op
(no double-meter). Stripe failures propagate so the caller can either
return 502 (route) or fail the job (worker).

These tests run against a real Postgres testcontainer (the
``pytestmark = pytest.mark.rls`` marker) so the UPDATE …
WHERE status != 'ready' RETURNING id semantics are exercised end to end.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
import stripe
from sqlalchemy import text

from app.db.models import Scan, ScanStatus, Team
from app.util.ids import new_uuid7

pytestmark = pytest.mark.rls


# ---------------------------------------------------------------------------
# Local fixtures (mirror tests/test_scans.py shapes; we duplicate to keep
# this module independent of the API-layer fixtures.)
# ---------------------------------------------------------------------------


@pytest.fixture
def stub_stripe_meter(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """SDK-boundary stub for ``stripe_meter._client``.

    ``calls`` records (params, options) tuples; set ``next_failure=True``
    to make the next call raise StripeError.
    """
    from app.billing import stripe_meter

    state: dict[str, Any] = {"calls": [], "next_failure": False}

    class _MeterEvents:
        def create(self, *, params: Any, options: Any = None) -> Any:
            if state["next_failure"]:
                state["next_failure"] = False
                raise stripe.error.APIError("simulated_meter_failure")
            state["calls"].append({"params": dict(params), "options": options})
            return None

    class _Billing:
        meter_events = _MeterEvents()

    class _V2:
        billing = _Billing()

    class _Client:
        v2 = _V2()

    monkeypatch.setattr(stripe_meter, "_client", lambda: _Client())
    return state


@pytest.fixture
async def seeded_team(seed_session: Any) -> Team:
    """Fresh Team row via BYPASSRLS seed_session — random clerk_org_id
    so successive runs against the session-scoped pg_container don't
    collide on the UNIQUE index."""
    import secrets

    tid = new_uuid7()
    t = Team(
        id=tid,
        clerk_org_id=f"org_finalize_{secrets.token_hex(6)}",
        name="Finalize Team",
        stripe_customer_id="cus_finalize",
    )
    async with seed_session.begin():
        seed_session.add(t)
    return t


async def _insert_pending_scan(seed_session: Any, team_id: UUID) -> UUID:
    """Insert a fresh ``pending`` scan row via the BYPASSRLS seed
    session and return its id. r2_key is left blank — the helper writes it."""
    sid = new_uuid7()
    async with seed_session.begin():
        seed_session.add(
            Scan(
                id=sid,
                team_id=team_id,
                r2_key="",  # placeholder; helper sets it
                status=ScanStatus.pending,
            )
        )
    return sid


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_finalize_scan_updates_pending_to_ready_and_fires_meter(
    pg_container: Any,
    seed_session: Any,
    seeded_team: Team,
    stub_stripe_meter: dict[str, Any],
) -> None:
    """Happy path: pending → ready, r2 metadata written, meter event posted exactly once."""
    from app.db.session import get_sessionmaker
    from app.services.scans import finalize_scan

    sid = await _insert_pending_scan(seed_session, seeded_team.id)
    sm = get_sessionmaker()
    final_key = f"teams/{seeded_team.id}/scans/{sid}.json"

    async with sm() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(seeded_team.id)},
        )
        await finalize_scan(
            session,
            scan_id=sid,
            team_id=seeded_team.id,
            stripe_customer_id=seeded_team.stripe_customer_id or "",
            r2_key=final_key,
            sha256="a" * 64,
            size_bytes=1234,
            summary_json={"score": 99},
        )

    # Re-read via seed_session (BYPASSRLS).
    async with seed_session.begin():
        row = (
            await seed_session.execute(
                text(
                    "SELECT status, r2_key, sha256, size_bytes, summary_json "
                    "FROM scans WHERE id = :id"
                ),
                {"id": str(sid)},
            )
        ).one()

    assert row.status == "ready"
    assert row.r2_key == final_key
    assert row.sha256 == "a" * 64
    assert row.size_bytes == 1234
    assert row.summary_json == {"score": 99}

    # Meter fired exactly once with our scan_id.
    calls = stub_stripe_meter["calls"]
    assert len(calls) == 1
    assert calls[0]["params"]["identifier"] == str(sid)
    assert calls[0]["options"]["idempotency_key"] == str(sid)


async def test_finalize_scan_idempotent_when_already_ready(
    pg_container: Any,
    seed_session: Any,
    seeded_team: Team,
    stub_stripe_meter: dict[str, Any],
) -> None:
    """Second call on a row already in 'ready' is a no-op — no double-meter."""
    from app.db.session import get_sessionmaker
    from app.services.scans import finalize_scan

    sid = await _insert_pending_scan(seed_session, seeded_team.id)
    sm = get_sessionmaker()
    final_key = f"teams/{seeded_team.id}/scans/{sid}.json"

    async def _call() -> None:
        async with sm() as session, session.begin():
            await session.execute(
                text("SELECT set_config('app.current_team_id', :t, true)"),
                {"t": str(seeded_team.id)},
            )
            await finalize_scan(
                session,
                scan_id=sid,
                team_id=seeded_team.id,
                stripe_customer_id=seeded_team.stripe_customer_id or "",
                r2_key=final_key,
                sha256="b" * 64,
                size_bytes=42,
                summary_json=None,
            )

    await _call()
    await _call()  # second invocation — must NOT fire meter again

    calls = stub_stripe_meter["calls"]
    assert len(calls) == 1, f"expected exactly 1 meter event, got {len(calls)}"


async def test_finalize_scan_propagates_stripe_error(
    pg_container: Any,
    seed_session: Any,
    seeded_team: Team,
    stub_stripe_meter: dict[str, Any],
) -> None:
    """Stripe failure re-raises so caller can surface 502 (route) or fail (worker)."""
    from app.db.session import get_sessionmaker
    from app.services.scans import finalize_scan

    sid = await _insert_pending_scan(seed_session, seeded_team.id)
    sm = get_sessionmaker()
    stub_stripe_meter["next_failure"] = True

    with pytest.raises(stripe.error.StripeError):
        async with sm() as session, session.begin():
            await session.execute(
                text("SELECT set_config('app.current_team_id', :t, true)"),
                {"t": str(seeded_team.id)},
            )
            await finalize_scan(
                session,
                scan_id=sid,
                team_id=seeded_team.id,
                stripe_customer_id=seeded_team.stripe_customer_id or "",
                r2_key=f"teams/{seeded_team.id}/scans/{sid}.json",
                sha256="c" * 64,
                size_bytes=7,
                summary_json=None,
            )

    # The enclosing session.begin() rolled back on the StripeError so the
    # row should still be 'pending' (no half-state).
    async with seed_session.begin():
        row = (
            await seed_session.execute(
                text("SELECT status FROM scans WHERE id = :id"),
                {"id": str(sid)},
            )
        ).one()
    assert row.status == "pending"
