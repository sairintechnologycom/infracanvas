"""Integration tests for the scan ingest pipeline (API-010..014).

These test the full POST → PUT → commit → GET flow against the
PostgreSQL testcontainer, moto-backed R2, the SDK-boundary Stripe
client mock (see test_stripe_meter for rationale), and a fixture-local
Clerk JWKS keypair.

All tests in this module carry the ``rls`` marker — they require the
``pg_container`` fixture (real Postgres with migrations applied).
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any

import boto3
import pytest
from botocore.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import Scan, Team
from app.util.ids import new_uuid7

pytestmark = pytest.mark.rls


_VALID_GRAPH = json.dumps(
    {
        "nodes": [],
        "edges": [],
        "summary": {
            "total_resources": 0,
            "findings": {"critical": 0, "high": 0, "medium": 0, "info": 0},
            "estimated_monthly_cost": 0.0,
            "score": 100,
        },
        "metadata": {},
    }
).encode()


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ---------------------------------------------------------------------------
# Helpers — wire the fixtures to app code that doesn't naturally see them.
# ---------------------------------------------------------------------------


def _moto_s3_client() -> Any:
    """Return a stock boto3 S3 client bound to moto's fake credentials.

    Reused by every test that needs to drive R2 directly (e.g. simulating
    the client-side PUT to the presigned URL by talking to moto). moto
    intercepts at the botocore layer, so this client and the one the app
    uses share state once the app's get_r2_client is overridden.
    """
    return boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4"),
    )


@pytest.fixture(autouse=True)
def _wire_r2_to_moto(monkeypatch: pytest.MonkeyPatch, mock_r2: Any) -> None:
    """Replace ``app.storage.r2.get_r2_client`` with a moto-compatible client
    and point ``settings.r2_bucket`` at the moto bucket. Auto-applied for
    every test in this module.
    """
    from app.settings import settings
    from app.storage import r2 as r2_mod

    r2_mod.get_r2_client.cache_clear()
    monkeypatch.setattr(settings, "r2_bucket", mock_r2.bucket)

    moto_client = _moto_s3_client()

    def _client_override():  # type: ignore[no-untyped-def]
        return moto_client

    monkeypatch.setattr(r2_mod, "get_r2_client", _client_override)


@pytest.fixture
def stub_stripe_meter(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Replace ``stripe_meter._client`` with a SDK-shape capturing stub.

    Returns a dict with ``calls`` (list of (params, options)) and
    ``next_failure`` (set to True to make the next call raise StripeError).
    Stripe-python v15 routes V2 calls through ``requests`` not ``httpx``,
    so respx-based mocking won't catch them — we attack at the SDK
    boundary instead. See test_stripe_meter.py for the same pattern.
    """
    import stripe

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
def patch_clerk_jwks(monkeypatch: pytest.MonkeyPatch, mock_clerk: Any) -> None:
    """Point app.auth.clerk._jwks_client at the fixture-local JWKS endpoint
    AND align settings.clerk_issuer with mock_clerk's signed iss claim."""
    import app.auth.clerk as clerk_mod
    from jwt import PyJWKClient

    monkeypatch.setattr(clerk_mod, "_jwks_client", PyJWKClient(mock_clerk.jwks_url))
    from app.settings import settings

    # mock_clerk.sign_jwt embeds iss="https://clerk.infracanvas.app".
    monkeypatch.setattr(settings, "clerk_issuer", "https://clerk.infracanvas.app")
    monkeypatch.setattr(
        settings, "clerk_allowed_origins", ["https://infracanvas.app"]
    )


@pytest.fixture
async def team_a(seed_session: Any) -> Team:
    """Seed a Team A row via the BYPASSRLS seed session.

    seed_session is connected as ``infracanvas_test`` (BYPASSRLS) so the
    insert succeeds without setting the team GUC. Random clerk_org_id
    per test (random suffix, not UUIDv7-derived — UUIDv7 prefixes share
    timestamps within the same second and would collide) so the
    session-scoped pg_container can host successive test runs without
    UNIQUE violations.
    """
    import secrets

    tid = new_uuid7()
    t = Team(
        id=tid,
        clerk_org_id=f"org_scans_a_{secrets.token_hex(6)}",
        name="Team A",
        stripe_customer_id="cus_a",
    )
    async with seed_session.begin():
        seed_session.add(t)
    return t


@pytest.fixture
async def team_b(seed_session: Any) -> Team:
    import secrets

    tid = new_uuid7()
    t = Team(
        id=tid,
        clerk_org_id=f"org_scans_b_{secrets.token_hex(6)}",
        name="Team B",
        stripe_customer_id="cus_b",
    )
    async with seed_session.begin():
        seed_session.add(t)
    return t


@pytest.fixture
def auth_headers_factory(mock_clerk: Any):
    """Return a function that mints a Bearer header for a given clerk_org_id."""

    def _make(org_id: str, role: str = "admin", sub: str = "u1") -> dict[str, str]:
        token = mock_clerk.sign_jwt(sub=sub, org_id=org_id, role=role)
        return {"Authorization": f"Bearer {token}"}

    return _make


@pytest.fixture
def app_client(
    patch_clerk_jwks: None, pg_container: Any, monkeypatch: pytest.MonkeyPatch
) -> Any:
    """Construct a TestClient against a fresh app instance.

    Uses ``NullPool`` for the async engine so each request gets a fresh
    connection on whatever event loop TestClient is using — TestClient
    spins up a per-request anyio portal and a long-lived async pool would
    bind connections to a now-closed loop, raising "Future attached to a
    different loop" / "Event loop is closed" on the second request.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from app.db import session as sess_mod
    from app.main import create_app
    from app.settings import settings

    host = pg_container.get_container_host_ip()
    port = pg_container.get_exposed_port(5432)
    dbname = pg_container.dbname if hasattr(pg_container, "dbname") else "test"
    db_url = (
        f"postgresql+asyncpg://infracanvas_app:app@{host}:{port}/{dbname}"
    )
    monkeypatch.setattr(settings, "database_url", db_url)

    # Build an engine with NullPool so connections are created and closed
    # per-request (no cross-loop reuse).
    test_engine = create_async_engine(db_url, poolclass=NullPool)
    test_sm = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=sess_mod.AsyncSession
    )
    monkeypatch.setattr(sess_mod, "_engine", test_engine)
    monkeypatch.setattr(sess_mod, "_Session", test_sm)

    app = create_app()
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_upload_create_commit_get_happy_path(
    app_client: Any,
    team_a: Team,
    auth_headers_factory: Any,
    mock_r2: Any,
    stub_stripe_meter: dict[str, Any],
) -> None:
    """API-010: full POST /v1/scans → PUT pending/ → commit → GET flow.

    Asserts: 200 on each step, Stripe meter event captured exactly once
    with the scan_id, post-commit R2 move (final exists, pending gone),
    GET returns presigned URL.
    """
    headers = auth_headers_factory(team_a.clerk_org_id)

    r1 = app_client.post(
        "/v1/scans", headers=headers, json={"content_type": "application/json"}
    )
    assert r1.status_code == 200, r1.text
    scan_id = r1.json()["scan_id"]

    # Simulate the client-side PUT directly into moto.
    pending_key = f"pending/{scan_id}.json"
    final_key = f"teams/{team_a.id}/scans/{scan_id}.json"
    _moto_s3_client().put_object(
        Bucket=mock_r2.bucket,
        Key=pending_key,
        Body=_VALID_GRAPH,
        ContentType="application/json",
    )

    r2c = app_client.post(
        f"/v1/scans/{scan_id}/commit",
        headers=headers,
        json={"sha256": _sha(_VALID_GRAPH)},
    )
    assert r2c.status_code == 200, r2c.text
    body = r2c.json()
    assert body["status"] == "ready"
    assert body["size_bytes"] == len(_VALID_GRAPH)

    # Post-commit move: final exists, pending gone.
    head_final = _moto_s3_client().head_object(
        Bucket=mock_r2.bucket, Key=final_key
    )
    assert head_final["ContentLength"] == len(_VALID_GRAPH)
    with pytest.raises(Exception):
        _moto_s3_client().head_object(Bucket=mock_r2.bucket, Key=pending_key)

    # GET works.
    r3 = app_client.get(f"/v1/scans/{scan_id}", headers=headers)
    assert r3.status_code == 200
    assert "presigned_get_url" in r3.json()

    # Stripe meter captured exactly once with identifier=scan_id, value=1.
    calls = stub_stripe_meter["calls"]
    assert len(calls) == 1
    assert calls[0]["params"]["event_name"] == "infracanvas.scan"
    assert calls[0]["params"]["identifier"] == scan_id
    assert str(calls[0]["params"]["payload"]["value"]) == "1"
    assert calls[0]["options"]["idempotency_key"] == scan_id


def test_commit_rejects_oversized(
    app_client: Any,
    team_a: Team,
    auth_headers_factory: Any,
    mock_r2: Any,
    stub_stripe_meter: dict[str, Any],
) -> None:
    """API-011: commit returns 413 when R2 HEAD ContentLength > 25MB."""
    headers = auth_headers_factory(team_a.clerk_org_id)

    r1 = app_client.post("/v1/scans", headers=headers, json={})
    scan_id = r1.json()["scan_id"]

    huge = b"x" * (26 * 1024 * 1024)
    _moto_s3_client().put_object(
        Bucket=mock_r2.bucket,
        Key=f"pending/{scan_id}.json",
        Body=huge,
        ContentType="application/json",
    )

    r = app_client.post(
        f"/v1/scans/{scan_id}/commit",
        headers=headers,
        json={"sha256": _sha(huge)},
    )
    assert r.status_code == 413
    # No meter event posted on size rejection.
    assert stub_stripe_meter["calls"] == []


def test_commit_rejects_malformed_graph(
    app_client: Any,
    team_a: Team,
    auth_headers_factory: Any,
    mock_r2: Any,
    stub_stripe_meter: dict[str, Any],
) -> None:
    """API-012: commit returns 422 when the R2 object is not a valid
    ResourceGraph (Pydantic model_validate_json fails)."""
    headers = auth_headers_factory(team_a.clerk_org_id)

    r1 = app_client.post("/v1/scans", headers=headers, json={})
    scan_id = r1.json()["scan_id"]

    junk = b'{"not_a_resource_graph": true, "nodes": "should_be_a_list"}'
    _moto_s3_client().put_object(
        Bucket=mock_r2.bucket,
        Key=f"pending/{scan_id}.json",
        Body=junk,
        ContentType="application/json",
    )

    r = app_client.post(
        f"/v1/scans/{scan_id}/commit",
        headers=headers,
        json={"sha256": _sha(junk)},
    )
    assert r.status_code == 422
    assert stub_stripe_meter["calls"] == []


def test_cross_team_get_returns_404(
    app_client: Any,
    team_a: Team,
    team_b: Team,
    auth_headers_factory: Any,
    mock_r2: Any,
    stub_stripe_meter: dict[str, Any],
) -> None:
    """API-013 / RLS-006: team B requesting team A's scan_id → 404 (not 403
    per D-10 — the existence of the scan is not leaked across tenants)."""
    h_a = auth_headers_factory(team_a.clerk_org_id, sub="u_a")
    h_b = auth_headers_factory(team_b.clerk_org_id, sub="u_b")

    r1 = app_client.post("/v1/scans", headers=h_a, json={})
    scan_id = r1.json()["scan_id"]
    _moto_s3_client().put_object(
        Bucket=mock_r2.bucket,
        Key=f"pending/{scan_id}.json",
        Body=_VALID_GRAPH,
        ContentType="application/json",
    )
    r_commit = app_client.post(
        f"/v1/scans/{scan_id}/commit",
        headers=h_a,
        json={"sha256": _sha(_VALID_GRAPH)},
    )
    assert r_commit.status_code == 200, r_commit.text

    # Team B attempts to GET team A's scan.
    r_cross = app_client.get(f"/v1/scans/{scan_id}", headers=h_b)
    assert r_cross.status_code == 404


async def test_commit_rollback_on_stripe_failure(
    app_client: Any,
    team_a: Team,
    auth_headers_factory: Any,
    mock_r2: Any,
    stub_stripe_meter: dict[str, Any],
    seed_session: Any,
) -> None:
    """API-014: Stripe meter failure rolls back the scans INSERT.

    Caller's commit returns 502 (meter_failed); the scans table contains
    no row for this scan_id (DB tx aborted by the StripeError).
    """
    headers = auth_headers_factory(team_a.clerk_org_id)
    stub_stripe_meter["next_failure"] = True

    r1 = app_client.post("/v1/scans", headers=headers, json={})
    scan_id = r1.json()["scan_id"]
    _moto_s3_client().put_object(
        Bucket=mock_r2.bucket,
        Key=f"pending/{scan_id}.json",
        Body=_VALID_GRAPH,
        ContentType="application/json",
    )

    r = app_client.post(
        f"/v1/scans/{scan_id}/commit",
        headers=headers,
        json={"sha256": _sha(_VALID_GRAPH)},
    )
    assert r.status_code == 502

    # No row in scans for this id (rollback worked).
    from uuid import UUID

    async with seed_session.begin():
        result = await seed_session.execute(
            select(Scan).where(Scan.id == UUID(scan_id))
        )
        assert result.scalar_one_or_none() is None
