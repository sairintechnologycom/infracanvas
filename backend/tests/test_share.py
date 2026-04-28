"""Tests for share-link endpoints (07-04, SHR-01..SHR-02).

Test IDs:
  SHR-001  create share link returns token + share_url (no password)
  SHR-002  create share link with password — token returned, password_hash not in response
  SHR-003  GET /v1/share-links/{token} no-password link returns has_password=False + presigned URL
  SHR-004  GET /v1/share-links/{token} password link returns has_password=True, NO scan metadata
  SHR-005  POST /v1/share-links/{token}/unlock correct password returns presigned URL
  SHR-006  POST /v1/share-links/{token}/unlock wrong password returns 401
  SHR-007  DELETE /v1/scans/{id}/share-links/{share_id} revokes; subsequent GET returns 410
  SHR-008  GET expired share link returns 410
  SHR-009  rate limit: 6th unlock attempt returns 429
  SHR-010  unauthenticated create returns 401/403

The full create→public-GET→unlock→revoke flow runs against the Postgres
testcontainer (with migration 006 applied via the auto-upgrade in
``conftest.pg_container``). Wire-level fixtures (``app_client``,
``auth_headers_factory``, ``team_a``, ``mock_r2``, ``stub_stripe_meter``,
``patch_clerk_jwks``) are imported from the shared test_scans pattern.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3
import pytest
from botocore.config import Config
from fastapi.testclient import TestClient

from app.db.models import Team
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


def _moto_s3_client() -> Any:
    """Return a stock boto3 S3 client bound to moto's fake credentials."""
    return boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4"),
    )


# ---------------------------------------------------------------------------
# Per-test fixtures (mirror test_scans.py pattern).
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _wire_r2_to_moto(monkeypatch: pytest.MonkeyPatch, mock_r2: Any) -> None:
    """Replace ``app.storage.r2.get_r2_client`` with a moto-compatible client."""
    from app.settings import settings
    from app.storage import r2 as r2_mod

    r2_mod.get_r2_client.cache_clear()
    monkeypatch.setattr(settings, "r2_bucket", mock_r2.bucket)

    moto_client = _moto_s3_client()

    def _client_override():  # type: ignore[no-untyped-def]
        return moto_client

    monkeypatch.setattr(r2_mod, "get_r2_client", _client_override)


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    """Clear the in-process rate-limit dict between tests (T-07-04-02)."""
    from app.routes import share as share_mod

    share_mod._rate_store.clear()


@pytest.fixture
def stub_stripe_meter(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """SDK-boundary Stripe meter stub (mirrors test_scans.py)."""
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
    """Point app.auth.clerk._jwks_client at the fixture-local JWKS endpoint."""
    import app.auth.clerk as clerk_mod
    from jwt import PyJWKClient

    monkeypatch.setattr(clerk_mod, "_jwks_client", PyJWKClient(mock_clerk.jwks_url))
    from app.settings import settings

    monkeypatch.setattr(settings, "clerk_issuer", "https://clerk.infracanvas.app")
    monkeypatch.setattr(
        settings, "clerk_allowed_origins", ["https://infracanvas.app"]
    )


@pytest.fixture
async def team_a(seed_session: Any) -> Team:
    """Seed a Team A row via the BYPASSRLS seed session."""
    import secrets

    tid = new_uuid7()
    t = Team(
        id=tid,
        clerk_org_id=f"org_share_a_{secrets.token_hex(6)}",
        name="Team A (share)",
        stripe_customer_id="cus_share_a",
    )
    async with seed_session.begin():
        seed_session.add(t)
    return t


@pytest.fixture
def auth_headers_factory(mock_clerk: Any):
    """Return a function that mints a Bearer header for a given clerk_org_id."""

    def _make(org_id: str, role: str = "admin", sub: str = "u_share_1") -> dict[str, str]:
        token = mock_clerk.sign_jwt(sub=sub, org_id=org_id, role=role)
        return {"Authorization": f"Bearer {token}"}

    return _make


@pytest.fixture
def app_client(
    patch_clerk_jwks: None, pg_container: Any, monkeypatch: pytest.MonkeyPatch
) -> Any:
    """Construct a TestClient against a fresh app instance with NullPool."""
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

    test_engine = create_async_engine(db_url, poolclass=NullPool)
    test_sm = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=sess_mod.AsyncSession
    )
    monkeypatch.setattr(sess_mod, "_engine", test_engine)
    monkeypatch.setattr(sess_mod, "_Session", test_sm)

    app = create_app()
    with TestClient(app) as c:
        yield c


def _seed_committed_scan(
    app_client: Any,
    headers: dict[str, str],
    mock_r2: Any,
) -> str:
    """Drive the full POST /v1/scans → PUT pending → commit flow.

    Returns the scan_id (str). Uses moto for R2, the stub_stripe_meter
    fixture must be active for the commit to succeed.
    """
    r1 = app_client.post(
        "/v1/scans", headers=headers, json={"content_type": "application/json"}
    )
    assert r1.status_code == 200, r1.text
    scan_id = r1.json()["scan_id"]

    _moto_s3_client().put_object(
        Bucket=mock_r2.bucket,
        Key=f"pending/{scan_id}.json",
        Body=_VALID_GRAPH,
        ContentType="application/json",
    )
    r_commit = app_client.post(
        f"/v1/scans/{scan_id}/commit",
        headers=headers,
        json={"sha256": _sha(_VALID_GRAPH)},
    )
    assert r_commit.status_code == 200, r_commit.text
    return scan_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


# --- SHR-001: create share link, no password ---
def test_create_share_link_no_password(
    app_client: Any,
    team_a: Team,
    auth_headers_factory: Any,
    mock_r2: Any,
    stub_stripe_meter: dict[str, Any],
) -> None:
    """SHR-001: create returns token + share_url + id; token is present once."""
    headers = auth_headers_factory(team_a.clerk_org_id)
    scan_id = _seed_committed_scan(app_client, headers, mock_r2)

    resp = app_client.post(
        f"/v1/scans/{scan_id}/share-links",
        json={},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "token" in data
    assert "share_url" in data
    assert "id" in data
    # secrets.token_urlsafe(32) yields ~43-char base64-url string
    assert len(data["token"]) > 10


# --- SHR-002: create share link with password ---
def test_create_share_link_with_password(
    app_client: Any,
    team_a: Team,
    auth_headers_factory: Any,
    mock_r2: Any,
    stub_stripe_meter: dict[str, Any],
) -> None:
    """SHR-002: password-protected link — token present, no password_hash leaked."""
    headers = auth_headers_factory(team_a.clerk_org_id)
    scan_id = _seed_committed_scan(app_client, headers, mock_r2)

    resp = app_client.post(
        f"/v1/scans/{scan_id}/share-links",
        json={"password": "s3cr3t"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "token" in data
    assert "password_hash" not in data  # never returned
    assert "password" not in data


# --- SHR-003: GET public landing, no-password link ---
def test_get_share_landing_no_password(
    app_client: Any,
    team_a: Team,
    auth_headers_factory: Any,
    mock_r2: Any,
    stub_stripe_meter: dict[str, Any],
) -> None:
    """SHR-003: no-password link landing returns has_password=False + presigned URL."""
    headers = auth_headers_factory(team_a.clerk_org_id)
    scan_id = _seed_committed_scan(app_client, headers, mock_r2)

    create_resp = app_client.post(
        f"/v1/scans/{scan_id}/share-links",
        json={},
        headers=headers,
    )
    token = create_resp.json()["token"]

    land_resp = app_client.get(f"/v1/share-links/{token}")  # no auth headers
    assert land_resp.status_code == 200, land_resp.text
    data = land_resp.json()
    assert data["has_password"] is False
    assert data["presigned_get_url"] is not None
    assert data["scan_id"] is not None


# --- SHR-004: GET public landing, password link — no scan metadata ---
def test_get_share_landing_password_protected(
    app_client: Any,
    team_a: Team,
    auth_headers_factory: Any,
    mock_r2: Any,
    stub_stripe_meter: dict[str, Any],
) -> None:
    """SHR-004: password-protected landing returns has_password=True, no scan metadata (D-15)."""
    headers = auth_headers_factory(team_a.clerk_org_id)
    scan_id = _seed_committed_scan(app_client, headers, mock_r2)

    create_resp = app_client.post(
        f"/v1/scans/{scan_id}/share-links",
        json={"password": "secret"},
        headers=headers,
    )
    token = create_resp.json()["token"]

    land_resp = app_client.get(f"/v1/share-links/{token}")
    assert land_resp.status_code == 200, land_resp.text
    data = land_resp.json()
    assert data["has_password"] is True
    # D-15: scan data must NOT be present when password is required
    assert data.get("scan_id") is None
    assert data.get("presigned_get_url") is None


# --- SHR-005: unlock with correct password ---
def test_unlock_correct_password(
    app_client: Any,
    team_a: Team,
    auth_headers_factory: Any,
    mock_r2: Any,
    stub_stripe_meter: dict[str, Any],
) -> None:
    """SHR-005: correct password returns presigned URL + scan metadata."""
    headers = auth_headers_factory(team_a.clerk_org_id)
    scan_id = _seed_committed_scan(app_client, headers, mock_r2)

    create_resp = app_client.post(
        f"/v1/scans/{scan_id}/share-links",
        json={"password": "correct"},
        headers=headers,
    )
    token = create_resp.json()["token"]

    unlock_resp = app_client.post(
        f"/v1/share-links/{token}/unlock",
        json={"password": "correct"},
    )
    assert unlock_resp.status_code == 200, unlock_resp.text
    data = unlock_resp.json()
    assert "presigned_get_url" in data
    assert "scan_id" in data


# --- SHR-006: unlock with wrong password returns 401 ---
def test_unlock_wrong_password(
    app_client: Any,
    team_a: Team,
    auth_headers_factory: Any,
    mock_r2: Any,
    stub_stripe_meter: dict[str, Any],
) -> None:
    """SHR-006: wrong password returns 401 Unauthorized."""
    headers = auth_headers_factory(team_a.clerk_org_id)
    scan_id = _seed_committed_scan(app_client, headers, mock_r2)

    create_resp = app_client.post(
        f"/v1/scans/{scan_id}/share-links",
        json={"password": "correct"},
        headers=headers,
    )
    token = create_resp.json()["token"]

    unlock_resp = app_client.post(
        f"/v1/share-links/{token}/unlock",
        json={"password": "wrong"},
    )
    assert unlock_resp.status_code == 401


# --- SHR-007: DELETE revokes; GET returns 410 ---
def test_revoke_share_link(
    app_client: Any,
    team_a: Team,
    auth_headers_factory: Any,
    mock_r2: Any,
    stub_stripe_meter: dict[str, Any],
) -> None:
    """SHR-007: DELETE revokes link; subsequent GET returns 410 Gone."""
    headers = auth_headers_factory(team_a.clerk_org_id)
    scan_id = _seed_committed_scan(app_client, headers, mock_r2)

    create_resp = app_client.post(
        f"/v1/scans/{scan_id}/share-links",
        json={},
        headers=headers,
    )
    data = create_resp.json()
    token = data["token"]
    share_id = data["id"]

    # Revoke
    del_resp = app_client.delete(
        f"/v1/scans/{scan_id}/share-links/{share_id}",
        headers=headers,
    )
    assert del_resp.status_code == 204, del_resp.text

    # Subsequent GET must return 410 (revoked). share_link_by_token() does
    # NOT filter on revoked_at — the route layer inspects revoked_at and
    # raises 410, per acceptance criterion SHR-007 + threat T-07-04-06.
    land_resp = app_client.get(f"/v1/share-links/{token}")
    assert land_resp.status_code == 410, land_resp.text


# --- SHR-008: expired share link returns 410 ---
def test_expired_share_link_returns_410(
    app_client: Any,
    team_a: Team,
    auth_headers_factory: Any,
    mock_r2: Any,
    stub_stripe_meter: dict[str, Any],
) -> None:
    """SHR-008: link with expires_at in the past returns 410 Gone."""
    headers = auth_headers_factory(team_a.clerk_org_id)
    scan_id = _seed_committed_scan(app_client, headers, mock_r2)

    past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    create_resp = app_client.post(
        f"/v1/scans/{scan_id}/share-links",
        json={"expires_at": past},
        headers=headers,
    )
    token = create_resp.json()["token"]

    land_resp = app_client.get(f"/v1/share-links/{token}")
    assert land_resp.status_code == 410, land_resp.text


# --- SHR-009: rate limit on /unlock ---
def test_unlock_rate_limit(
    app_client: Any,
    team_a: Team,
    auth_headers_factory: Any,
    mock_r2: Any,
    stub_stripe_meter: dict[str, Any],
) -> None:
    """SHR-009: 6th unlock attempt within window returns 429."""
    from app.routes.share import _RATE_LIMIT_MAX

    headers = auth_headers_factory(team_a.clerk_org_id)
    scan_id = _seed_committed_scan(app_client, headers, mock_r2)

    create_resp = app_client.post(
        f"/v1/scans/{scan_id}/share-links",
        json={"password": "correct"},
        headers=headers,
    )
    token = create_resp.json()["token"]

    # Exhaust rate limit with wrong-password attempts
    for _ in range(_RATE_LIMIT_MAX):
        app_client.post(
            f"/v1/share-links/{token}/unlock",
            json={"password": "wrong"},
        )

    # Next attempt must be rate-limited
    resp = app_client.post(
        f"/v1/share-links/{token}/unlock",
        json={"password": "wrong"},
    )
    assert resp.status_code == 429, resp.text


# --- SHR-010: unauthenticated create returns 401/403 ---
def test_create_share_link_no_auth(app_client: Any) -> None:
    """SHR-010: missing auth on create returns 401 or 403."""
    # Use a random scan_id — auth rejects before any DB lookup.
    fake_scan_id = new_uuid7()
    resp = app_client.post(
        f"/v1/scans/{fake_scan_id}/share-links",
        json={},
        # no headers
    )
    assert resp.status_code in (401, 403)
