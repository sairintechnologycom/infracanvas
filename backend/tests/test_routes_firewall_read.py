"""Wave 0 RED test stubs for Phase 11 firewall read API.

Collection-RED until Plan 11-04 lands ``app.routes.firewalls``.

Endpoint under test:
- GET /v1/sites/{site_id}/firewall-rules (D-11)

Pattern B (Clerk JWT + Team-RLS context-setting):
- Auth: Clerk JWT via ``require_role("owner", "admin", "member", "basic_member")``
- Team resolution: ``resolve_team_from_clerk_org`` derives team from JWT.o.id
- DB query: ``set_config('app.current_team_id', :t, true)`` inside the txn
- Returns: latest snapshot PER firewall_id, scoped to caller's team
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.models import DCSite, Team

pytestmark = pytest.mark.rls


# ---------------------------------------------------------------------------
# Helpers (mirror test_agent.py shape)
# ---------------------------------------------------------------------------


def _build_app_client(
    pg_container: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
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
    from jwt import PyJWKClient

    import app.auth.clerk as clerk_mod

    monkeypatch.setattr(clerk_mod, "_jwks_client", PyJWKClient(mock_clerk.jwks_url))
    from app.settings import settings

    monkeypatch.setattr(settings, "clerk_issuer", "https://clerk.infracanvas.app")
    monkeypatch.setattr(
        settings, "clerk_allowed_origins", ["https://infracanvas.app"]
    )


async def _seed_team_and_site(
    seed_session: AsyncSession,
    name_suffix: str = "",
) -> tuple[Team, DCSite, str]:
    team = Team(
        id=uuid.uuid4(),
        clerk_org_id=f"org_fwread_{secrets.token_hex(6)}{name_suffix}",
        name=f"Firewall Read Team{name_suffix}",
        stripe_customer_id=f"cus_fwread{name_suffix}",
    )
    async with seed_session.begin():
        seed_session.add(team)
    raw_token = "ic_site_" + secrets.token_urlsafe(32)
    site = DCSite(
        id=uuid.uuid4(),
        team_id=team.id,
        name="Firewall Read Site",
        token_lookup_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
    )
    async with seed_session.begin():
        seed_session.add(site)
    return team, site, raw_token


# ---------------------------------------------------------------------------
# D-11 — latest-per-device read
# ---------------------------------------------------------------------------


async def test_returns_latest_per_device(
    pg_container: Any,
    seed_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    mock_clerk: Any,
    firewall_snapshot: Any,
) -> None:
    """D-11: GET returns only the newest snapshot per firewall_id.

    Seeds two snapshots for the same firewall_id at different snapshot_ts
    via the ``firewall_snapshot`` conftest fixture, asserts the read API
    surfaces ONLY the newer one.
    """
    _patch_clerk(monkeypatch, mock_clerk)
    seeded = await firewall_snapshot(
        seed_session,
        firewall_id="asa-edge-01",
        snapshots=[
            {"snapshot_ts": "2026-05-12T06:00:00Z", "rule_count": 5},
            {"snapshot_ts": "2026-05-12T07:00:00Z", "rule_count": 7},  # newer
        ],
    )
    team_id = seeded["team_id"]
    site_id = seeded["site_id"]
    org_id = seeded["clerk_org_id"]

    with _build_app_client(pg_container, monkeypatch) as client:
        jwt = mock_clerk.sign_jwt(
            sub="u_owner",
            org_id=org_id,
            role="admin",
            azp="https://infracanvas.app",
        )
        r = client.get(
            f"/v1/sites/{site_id}/firewall-rules",
            headers={"Authorization": f"Bearer {jwt}"},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    # Exactly one snapshot envelope back for firewall_id=asa-edge-01
    assert isinstance(body, list)
    fw = [s for s in body if s.get("firewall_id") == "asa-edge-01"]
    assert len(fw) == 1, f"D-11: expected one latest snapshot per device, got {len(fw)}"
    assert fw[0]["snapshot_ts"] == "2026-05-12T07:00:00Z"
    assert len(fw[0]["rules"]) == 7
    _ = team_id  # silence unused — kept for debugging context


# ---------------------------------------------------------------------------
# Pattern C — RLS cross-team isolation
# ---------------------------------------------------------------------------


async def test_cross_team_isolation(
    pg_container: Any,
    seed_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    mock_clerk: Any,
    firewall_snapshot: Any,
) -> None:
    """Pattern C: Team A's Clerk JWT cannot read Team B's snapshots.

    Seeds a snapshot under Team B, then queries with a Team A JWT —
    response must be empty (RLS policy + site-id-not-found = 404 or
    empty list per the route's exact shape; this test locks the
    *non-empty A would be a security breach* invariant).
    """
    _patch_clerk(monkeypatch, mock_clerk)
    # Seed under Team B
    seeded_b = await firewall_snapshot(
        seed_session,
        firewall_id="asa-team-b-fw",
        snapshots=[{"snapshot_ts": "2026-05-12T07:00:00Z", "rule_count": 3}],
    )
    site_b = seeded_b["site_id"]

    # Create Team A (no snapshots seeded for A)
    team_a, _site_a, _tok = await _seed_team_and_site(seed_session, name_suffix="_a")

    with _build_app_client(pg_container, monkeypatch) as client:
        jwt_a = mock_clerk.sign_jwt(
            sub="u_a",
            org_id=team_a.clerk_org_id,
            role="admin",
            azp="https://infracanvas.app",
        )
        r = client.get(
            f"/v1/sites/{site_b}/firewall-rules",
            headers={"Authorization": f"Bearer {jwt_a}"},
        )
    # Either 404 (site not visible under A's RLS context) or 200 with empty list.
    # Both are acceptable per the routes/github.py precedent — never 200 with B's data.
    assert r.status_code in (200, 404), r.text
    if r.status_code == 200:
        body = r.json()
        assert body == [], "RLS breach: Team A must not see Team B's snapshots"


# ---------------------------------------------------------------------------
# Pattern B — Clerk JWT required
# ---------------------------------------------------------------------------


def test_requires_clerk_jwt() -> None:
    """Pattern B: missing Clerk Bearer JWT returns 401."""
    from app.main import create_app

    site_id = str(uuid.uuid4())
    with TestClient(create_app()) as client:
        r = client.get(f"/v1/sites/{site_id}/firewall-rules")
    assert r.status_code == 401, r.text
