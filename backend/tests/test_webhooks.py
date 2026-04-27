"""Clerk webhook handler contract tests (WBH-001..WBH-004).

Exercises POST /v1/webhooks/clerk against:
- bad-signature → 401
- valid organization.created → INSERT teams + Stripe customer
- replay (same body, different msg_id) → idempotent (one row)
- organization.updated → UPDATE name

Uses Postgres testcontainer (``rls`` marker) because RLS policies +
SECURITY DEFINER function must be live for the INSERT/UPDATE paths.
Stripe customer creation is monkeypatched at the
``stripe.Customer.search`` / ``stripe.Customer.create`` symbols so no
network traffic happens (more reliable than HTTP-level mocking against
the stripe-python client's polymorphic request flow).
"""

from __future__ import annotations

import datetime as _dt
import json
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from svix.webhooks import Webhook

from app.db.models import Team
from app.main import create_app
from app.settings import settings

pytestmark = pytest.mark.rls  # needs Postgres testcontainer


def _signed_headers(
    body: bytes, secret: str, msg_id: str = "msg_test_1"
) -> dict[str, str]:
    """Sign ``body`` with the given Svix secret and return the canonical
    {svix-id, svix-timestamp, svix-signature} header triple."""
    wh = Webhook(secret)
    ts_dt = _dt.datetime.fromtimestamp(int(time.time()), tz=_dt.timezone.utc)
    sig = wh.sign(msg_id=msg_id, timestamp=ts_dt, data=body.decode())
    return {
        "svix-id": msg_id,
        "svix-timestamp": str(int(ts_dt.timestamp())),
        "svix-signature": sig,
    }


@pytest.fixture
def stub_stripe(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Monkeypatch stripe.Customer.search/create so no HTTP fires.

    Returns a counters dict the test can inspect; ``create`` always
    returns a synthetic ``cus_test_<n>`` id, ``search`` always returns
    an empty result set so the create branch fires.
    """
    import stripe

    state: dict[str, Any] = {"create_calls": 0, "search_calls": 0, "ids": []}

    class _Empty:
        data: list[Any] = []

    class _Cust:
        def __init__(self, id_: str) -> None:
            self.id = id_

    def _search(query: str = "", **_: Any) -> _Empty:  # noqa: ARG001
        state["search_calls"] += 1
        return _Empty()

    def _create(**kwargs: Any) -> _Cust:
        state["create_calls"] += 1
        cid = f"cus_test_{state['create_calls']}"
        state["ids"].append(cid)
        return _Cust(cid)

    monkeypatch.setattr(stripe.Customer, "search", staticmethod(_search))
    monkeypatch.setattr(stripe.Customer, "create", staticmethod(_create))
    return state


@pytest.fixture
def app_with_pg(
    monkeypatch: pytest.MonkeyPatch,
    pg_container: Any,
) -> Any:
    """Build a FastAPI app pinned to the test Postgres container.

    Forces ``app.db.session`` to use the infracanvas_app NOBYPASSRLS URL
    of the testcontainer instead of the .env-stub default, then resets
    the cached engine so it reads the new URL on next use.
    """
    host = pg_container.get_container_host_ip()
    port = pg_container.get_exposed_port(5432)
    dbname = pg_container.dbname if hasattr(pg_container, "dbname") else "test"
    app_url = f"postgresql+asyncpg://infracanvas_app:app@{host}:{port}/{dbname}"
    monkeypatch.setattr(settings, "database_url", app_url)
    # Reset the lazy engine so the new URL is honoured.
    import app.db.session as session_mod

    monkeypatch.setattr(session_mod, "_engine", None)
    monkeypatch.setattr(session_mod, "_Session", None)
    return create_app()


async def test_bad_signature_returns_401(
    monkeypatch: pytest.MonkeyPatch,
    stub_stripe: dict[str, Any],
    app_with_pg: Any,
) -> None:
    """WBH-001: POST /v1/webhooks/clerk with bad Svix signature → 401."""
    monkeypatch.setattr(settings, "clerk_webhook_secret", "whsec_" + "A" * 32)
    with TestClient(app_with_pg) as c:
        r = c.post(
            "/v1/webhooks/clerk",
            content=b'{"type":"organization.created"}',
            headers={
                "svix-id": "x",
                "svix-timestamp": "1",
                "svix-signature": "v1,invalid",
            },
        )
        assert r.status_code == 401


async def test_organization_created_upserts_team(
    monkeypatch: pytest.MonkeyPatch,
    stub_stripe: dict[str, Any],
    seed_session: Any,
    app_with_pg: Any,
) -> None:
    """WBH-002: valid organization.created inserts teams row + Stripe customer."""
    secret = "whsec_" + "A" * 32
    monkeypatch.setattr(settings, "clerk_webhook_secret", secret)

    body = json.dumps(
        {
            "type": "organization.created",
            "data": {"id": "org_test_wbh002", "name": "Acme Corp"},
        }
    ).encode()
    headers = _signed_headers(body, secret)

    with TestClient(app_with_pg) as c:
        r = c.post("/v1/webhooks/clerk", content=body, headers=headers)
        assert r.status_code == 200, r.text

    # Verify via seed_session (BYPASSRLS) — confirm the row landed.
    result = await seed_session.execute(
        select(Team).where(Team.clerk_org_id == "org_test_wbh002")
    )
    team = result.scalar_one()
    assert team.name == "Acme Corp"
    assert team.stripe_customer_id  # synthetic id from stub
    assert stub_stripe["create_calls"] == 1


async def test_organization_created_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
    stub_stripe: dict[str, Any],
    seed_session: Any,
    app_with_pg: Any,
) -> None:
    """WBH-003: same webhook delivered twice → one row (ON CONFLICT DO NOTHING)."""
    secret = "whsec_" + "A" * 32
    monkeypatch.setattr(settings, "clerk_webhook_secret", secret)

    body = json.dumps(
        {
            "type": "organization.created",
            "data": {"id": "org_test_wbh003", "name": "Beta"},
        }
    ).encode()

    with TestClient(app_with_pg) as c:
        h1 = _signed_headers(body, secret, msg_id="msg_1")
        h2 = _signed_headers(body, secret, msg_id="msg_2")
        assert c.post("/v1/webhooks/clerk", content=body, headers=h1).status_code == 200
        assert c.post("/v1/webhooks/clerk", content=body, headers=h2).status_code == 200

    result = await seed_session.execute(
        select(Team).where(Team.clerk_org_id == "org_test_wbh003")
    )
    rows = result.scalars().all()
    assert len(rows) == 1


async def test_organization_updated_applies(
    monkeypatch: pytest.MonkeyPatch,
    stub_stripe: dict[str, Any],
    seed_session: Any,
    app_with_pg: Any,
) -> None:
    """WBH-004: organization.updated updates team name."""
    secret = "whsec_" + "A" * 32
    monkeypatch.setattr(settings, "clerk_webhook_secret", secret)

    body_c = json.dumps(
        {
            "type": "organization.created",
            "data": {"id": "org_test_wbh004", "name": "OldName"},
        }
    ).encode()
    body_u = json.dumps(
        {
            "type": "organization.updated",
            "data": {"id": "org_test_wbh004", "name": "NewName"},
        }
    ).encode()

    with TestClient(app_with_pg) as c:
        c.post(
            "/v1/webhooks/clerk",
            content=body_c,
            headers=_signed_headers(body_c, secret, "msg_c"),
        )
        c.post(
            "/v1/webhooks/clerk",
            content=body_u,
            headers=_signed_headers(body_u, secret, "msg_u"),
        )

    result = await seed_session.execute(
        select(Team).where(Team.clerk_org_id == "org_test_wbh004")
    )
    assert result.scalar_one().name == "NewName"
