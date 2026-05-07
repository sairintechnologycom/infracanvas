"""Phase 10 DC Agent backend tests — Plan 10-02 GREEN flip.

Tests: POST /v1/sites (site-token issuance + RBAC) + POST /v1/agent/routes
(site-token auth) + POST /v1/agent/flows (site-token auth) + RLS isolation
on dc_sites table.

Fixtures used from conftest.py:
- ``pg_container`` (rls marker) — Postgres testcontainer with alembic migrations
- ``seed_session`` — BYPASSRLS AsyncSession for cross-team seeding
- ``app_session`` — RLS-active AsyncSession as infracanvas_app
- ``mock_clerk`` — in-process JWKS keypair + sign_jwt() helper
- ``with_team_ctx`` — GUC-set helper for team-scoped operations

``asyncio_mode = "auto"`` (pyproject.toml) means all test functions that are
``async def`` run under anyio without explicit marks.
Tests that require the testcontainer carry ``pytestmark = pytest.mark.rls``.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.models import DCSite, Team

pytestmark = pytest.mark.rls


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_app_client(
    pg_container: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    """Build a NullPool TestClient wired to the testcontainer's infracanvas_app role.

    NullPool prevents 'Future attached to a different loop' across TestClient
    anyio portals (same pattern as test_scans.py app_client fixture).
    """
    from app.db import session as sess_mod
    from app.main import create_app
    from app.settings import settings

    host = pg_container.get_container_host_ip()
    port = pg_container.get_exposed_port(5432)
    dbname = pg_container.dbname if hasattr(pg_container, "dbname") else "test"
    db_url = f"postgresql+asyncpg://infracanvas_app:app@{host}:{port}/{dbname}"
    monkeypatch.setattr(settings, "database_url", db_url)

    test_engine = create_async_engine(db_url, poolclass=NullPool)
    test_sm = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=sess_mod.AsyncSession
    )
    monkeypatch.setattr(sess_mod, "_engine", test_engine)
    monkeypatch.setattr(sess_mod, "_Session", test_sm)
    return TestClient(create_app())


def _patch_clerk(monkeypatch: pytest.MonkeyPatch, mock_clerk: Any) -> None:
    """Redirect app.auth.clerk._jwks_client to the fixture-local JWKS endpoint."""
    from jwt import PyJWKClient

    import app.auth.clerk as clerk_mod

    monkeypatch.setattr(clerk_mod, "_jwks_client", PyJWKClient(mock_clerk.jwks_url))
    from app.settings import settings

    monkeypatch.setattr(settings, "clerk_issuer", "https://clerk.infracanvas.app")
    monkeypatch.setattr(
        settings, "clerk_allowed_origins", ["https://infracanvas.app"]
    )


async def _seed_team(seed_session: AsyncSession) -> Team:
    """Insert a fresh Team row via the BYPASSRLS seed session."""
    team = Team(
        id=uuid.uuid4(),
        clerk_org_id=f"org_agent_{secrets.token_hex(6)}",
        name="Agent Test Team",
        stripe_customer_id="cus_agent_test",
    )
    async with seed_session.begin():
        seed_session.add(team)
    return team


async def _seed_dc_site(
    seed_session: AsyncSession,
    team_id: uuid.UUID,
    raw_token: str,
) -> DCSite:
    """Insert a dc_sites row with the SHA-256 hash of ``raw_token``."""
    lookup_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    site = DCSite(
        id=uuid.uuid4(),
        team_id=team_id,
        name="Test Site",
        token_lookup_hash=lookup_hash,
    )
    async with seed_session.begin():
        seed_session.add(site)
    return site


# ---------------------------------------------------------------------------
# POST /v1/sites
# ---------------------------------------------------------------------------


async def test_create_site_returns_one_time_token(
    pg_container: Any,
    seed_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    mock_clerk: Any,
) -> None:
    """DCA-05: POST /v1/sites returns plaintext token once, stores SHA-256 hash in DB."""
    team = await _seed_team(seed_session)
    _patch_clerk(monkeypatch, mock_clerk)

    with _build_app_client(pg_container, monkeypatch) as client:
        token = mock_clerk.sign_jwt(
            sub="u_owner",
            org_id=team.clerk_org_id,
            role="owner",
            azp="https://infracanvas.app",
        )
        r = client.post(
            "/v1/sites",
            json={"name": "DC East"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 201, r.text
    body = r.json()
    assert "site_id" in body
    assert body["name"] == "DC East"
    site_token = body["site_token"]
    # Token must start with the ic_site_ prefix (from agent.py: "ic_site_" + token_urlsafe(32))
    assert site_token.startswith("ic_site_"), f"Unexpected token prefix: {site_token!r}"
    # Token must not be stored in plaintext — only SHA-256 hash in dc_sites
    lookup_hash = hashlib.sha256(site_token.encode("utf-8")).hexdigest()

    # Verify via BYPASSRLS seed_session that hash was stored correctly
    async with seed_session.begin():
        result = await seed_session.execute(
            text("SELECT token_lookup_hash FROM dc_sites WHERE id = :sid"),
            {"sid": body["site_id"]},
        )
        row = result.first()
    assert row is not None, "dc_sites row was not inserted"
    assert row[0] == lookup_hash, "DB has wrong hash — plaintext may have been stored"


async def test_create_site_requires_owner_role(
    pg_container: Any,
    seed_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    mock_clerk: Any,
) -> None:
    """DCA-05: POST /v1/sites returns 403 for non-owner Clerk roles (T-10-02-04)."""
    team = await _seed_team(seed_session)
    _patch_clerk(monkeypatch, mock_clerk)

    with _build_app_client(pg_container, monkeypatch) as client:
        token = mock_clerk.sign_jwt(
            sub="u_member",
            org_id=team.clerk_org_id,
            role="basic_member",
            azp="https://infracanvas.app",
        )
        r = client.post(
            "/v1/sites",
            json={"name": "DC West"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 403, r.text


# ---------------------------------------------------------------------------
# POST /v1/agent/routes — auth checks
# ---------------------------------------------------------------------------


def test_push_routes_rejects_missing_bearer() -> None:
    """DCA-05: POST /v1/agent/routes returns 401 missing_bearer with no auth header."""
    from app.main import create_app

    with TestClient(create_app()) as client:
        r = client.post(
            "/v1/agent/routes",
            json={
                "site_id": "00000000-0000-0000-0000-000000000000",
                "collected_at": "2026-05-07T10:00:00Z",
                "device_host": "192.168.1.1",
                "routes": [],
            },
        )
    assert r.status_code == 401
    assert r.json()["detail"] == "missing_bearer"


async def test_push_routes_rejects_invalid_site_token(
    pg_container: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DCA-05: POST /v1/agent/routes returns 401 invalid_site_token with bogus token."""
    with _build_app_client(pg_container, monkeypatch) as client:
        r = client.post(
            "/v1/agent/routes",
            json={
                "site_id": "00000000-0000-0000-0000-000000000000",
                "collected_at": "2026-05-07T10:00:00Z",
                "device_host": "192.168.1.1",
                "routes": [],
            },
            headers={"Authorization": "Bearer bogus_not_a_real_token"},
        )
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid_site_token"


async def test_push_routes_accepts_valid_site_token(
    pg_container: Any,
    seed_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DCA-05: POST /v1/agent/routes returns 202 with valid Bearer + body."""
    team = await _seed_team(seed_session)
    raw_token = "ic_site_" + secrets.token_urlsafe(32)
    await _seed_dc_site(seed_session, team.id, raw_token)

    with _build_app_client(pg_container, monkeypatch) as client:
        r = client.post(
            "/v1/agent/routes",
            json={
                "site_id": "00000000-0000-0000-0000-000000000001",
                "collected_at": "2026-05-07T10:00:00Z",
                "device_host": "192.168.1.1",
                "routes": [
                    {
                        "prefix": "10.0.0.0/8",
                        "next_hop": "192.168.1.254",
                        "protocol": "bgp",
                        "metric": 100,
                        "as_path": "65001 65002",
                    }
                ],
            },
            headers={"Authorization": f"Bearer {raw_token}"},
        )
    assert r.status_code == 202, r.text
    assert r.json() == {"ok": True}


# ---------------------------------------------------------------------------
# POST /v1/agent/flows — auth checks
# ---------------------------------------------------------------------------


def test_push_flows_rejects_missing_bearer() -> None:
    """DCA-05: POST /v1/agent/flows returns 401 missing_bearer with no auth header."""
    from app.main import create_app

    with TestClient(create_app()) as client:
        r = client.post(
            "/v1/agent/flows",
            json={
                "site_id": "00000000-0000-0000-0000-000000000000",
                "collected_at": "2026-05-07T10:00:00Z",
                "flows": [],
            },
        )
    assert r.status_code == 401
    assert r.json()["detail"] == "missing_bearer"


async def test_push_flows_accepts_valid_site_token(
    pg_container: Any,
    seed_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DCA-05: POST /v1/agent/flows returns 202 with valid Bearer + body."""
    team = await _seed_team(seed_session)
    raw_token = "ic_site_" + secrets.token_urlsafe(32)
    await _seed_dc_site(seed_session, team.id, raw_token)

    with _build_app_client(pg_container, monkeypatch) as client:
        r = client.post(
            "/v1/agent/flows",
            json={
                "site_id": "00000000-0000-0000-0000-000000000001",
                "collected_at": "2026-05-07T10:00:00Z",
                "flows": [
                    {
                        "src_ip": "10.0.0.1",
                        "dst_ip": "10.0.0.2",
                        "src_port": 12345,
                        "dst_port": 443,
                        "protocol": 6,
                        "bytes": 1024,
                        "packets": 10,
                    },
                    {
                        "src_ip": "10.0.0.3",
                        "dst_ip": "10.0.0.4",
                        "src_port": 54321,
                        "dst_port": 80,
                        "protocol": 6,
                        "bytes": 512,
                        "packets": 5,
                    },
                ],
            },
            headers={"Authorization": f"Bearer {raw_token}"},
        )
    assert r.status_code == 202, r.text
    assert r.json() == {"ok": True}


# ---------------------------------------------------------------------------
# RLS isolation
# ---------------------------------------------------------------------------


async def test_dc_sites_rls_isolates_teams(
    seed_session: AsyncSession,
    app_session: AsyncSession,
) -> None:
    """TMM-01: dc_sites query under team A's RLS context returns 0 rows for team B (T-10-02-05)."""
    team_a_id = uuid.uuid4()
    team_b_id = uuid.uuid4()

    async with seed_session.begin():
        # Insert teams directly via BYPASSRLS seed session
        await seed_session.execute(
            insert(Team).values(
                id=team_a_id,
                clerk_org_id=f"org_rls_a_{secrets.token_hex(6)}",
                name="RLS Team A",
            )
        )
        await seed_session.execute(
            insert(Team).values(
                id=team_b_id,
                clerk_org_id=f"org_rls_b_{secrets.token_hex(6)}",
                name="RLS Team B",
            )
        )
        # Insert dc_sites row for team_a
        await seed_session.execute(
            insert(DCSite).values(
                id=uuid.uuid4(),
                team_id=team_a_id,
                name="Site A",
                token_lookup_hash=hashlib.sha256(
                    f"token_for_a_{secrets.token_hex(4)}".encode()
                ).hexdigest(),
            )
        )
        # Insert dc_sites row for team_b
        await seed_session.execute(
            insert(DCSite).values(
                id=uuid.uuid4(),
                team_id=team_b_id,
                name="Site B",
                token_lookup_hash=hashlib.sha256(
                    f"token_for_b_{secrets.token_hex(4)}".encode()
                ).hexdigest(),
            )
        )

    # Query dc_sites under team_b's RLS context — must NOT see team_a's row
    async with app_session.begin():
        await app_session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team_b_id)},
        )
        result = await app_session.execute(
            text("SELECT count(*) FROM dc_sites WHERE team_id = :a_id"),
            {"a_id": str(team_a_id)},
        )
        count = result.scalar_one()

    assert count == 0, (
        f"RLS LEAK: team_b context returned {count} row(s) belonging to team_a "
        "on dc_sites — dc_sites_team_isolation policy not working"
    )

    # Positive control: team_b's own site IS visible under team_b context
    async with app_session.begin():
        await app_session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team_b_id)},
        )
        result2 = await app_session.execute(
            text("SELECT count(*) FROM dc_sites WHERE team_id = :b_id"),
            {"b_id": str(team_b_id)},
        )
        count2 = result2.scalar_one()

    assert count2 == 1, (
        f"Expected team_b to see its own dc_sites row, got {count2}"
    )
