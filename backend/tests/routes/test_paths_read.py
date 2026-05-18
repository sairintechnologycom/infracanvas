"""Phase 12 D-14 — read API tests for GET /v1/sites/{site_id}/paths +
GET /v1/sites/{site_id}/asymmetries.

GREEN once Plan 12-03 (this plan) lands ``app.routes.paths``.

Auth/RLS posture mirrors Phase 11 ``test_routes_firewall_read.py`` verbatim:
  * Clerk JWT required (401 without).
  * Cross-team site_id → 404 ``site_not_found_or_no_access`` (Pattern C).
  * DB seed wraps INSERT in ``set_config('app.current_team_id', ...)``
    (Pattern B) when seeding via the team-scoped ``app_session`` — but
    here we use ``seed_session`` (BYPASSRLS) for simpler cross-team seed.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

pytest.importorskip("app.routes.paths")  # auto-unskip once module lands (now: GREEN)

from app.db.models import DCSite, Team  # noqa: E402

pytestmark = pytest.mark.rls


# ---------------------------------------------------------------------------
# Helpers (mirror test_routes_firewall_read.py shape — Pattern B + Pattern C)
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
        clerk_org_id=f"org_pathread_{secrets.token_hex(6)}{name_suffix}",
        name=f"Path Read Team{name_suffix}",
        stripe_customer_id=f"cus_pathread{name_suffix}",
    )
    async with seed_session.begin():
        seed_session.add(team)
    raw_token = "ic_site_" + secrets.token_urlsafe(32)
    site = DCSite(
        id=uuid.uuid4(),
        team_id=team.id,
        name="Path Read Site",
        token_lookup_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
    )
    async with seed_session.begin():
        seed_session.add(site)
    return team, site, raw_token


async def _seed_computed_path(
    seed_session: AsyncSession,
    team_id: uuid.UUID,
    site_id: uuid.UUID,
    *,
    src: str = "10.0.0.0/24",
    dst: str = "10.1.0.0/24",
    direction: str = "forward",
    computed_at: datetime | None = None,
) -> None:
    """Seed one ``computed_paths`` row via raw SQL (no ORM table import dep)."""
    if computed_at is None:
        computed_at = datetime(2026, 5, 17, 7, 0, 0, tzinfo=UTC)
    async with seed_session.begin():
        await seed_session.execute(
            text(
                "INSERT INTO computed_paths (path_id, team_id, site_id, "
                "pair_src_cidr, pair_dst_cidr, direction, hops, "
                "match_evidence, computed_at) VALUES "
                "(:pid, :tid, :sid, :src, :dst, :dir, '[]'::jsonb, "
                "'{}'::jsonb, :ts)"
            ),
            {
                "pid": str(uuid.uuid4()),
                "tid": str(team_id),
                "sid": str(site_id),
                "src": src,
                "dst": dst,
                "dir": direction,
                "ts": computed_at,
            },
        )


async def _seed_asymmetry(
    seed_session: AsyncSession,
    team_id: uuid.UUID,
    site_id: uuid.UUID,
    *,
    cause: str = "NAT_ASYMMETRY",
    impact_firewall_count: int = 1,
) -> None:
    """Seed one ``asymmetry_findings`` row (open — resolved_at NULL)."""
    now = datetime.now(tz=UTC)
    async with seed_session.begin():
        await seed_session.execute(
            text(
                "INSERT INTO asymmetry_findings (finding_id, team_id, site_id, "
                "forward_path_id, return_path_id, cause, cause_confidence, "
                "evidence, impact_bytes_per_sec, impact_firewall_count, "
                "first_seen_at, last_seen_at, resolved_at) VALUES "
                "(:fid, :tid, :sid, :fpid, :rpid, :cause, 0.9, "
                "'{}'::jsonb, 1000, :mfc, :ts, :ts, NULL)"
            ),
            {
                "fid": str(uuid.uuid4()),
                "tid": str(team_id),
                "sid": str(site_id),
                "fpid": str(uuid.uuid4()),
                "rpid": str(uuid.uuid4()),
                "cause": cause,
                "mfc": impact_firewall_count,
                "ts": now,
            },
        )


# ---------------------------------------------------------------------------
# D-14 — GET /v1/sites/{site_id}/paths (latest-per-pair)
# ---------------------------------------------------------------------------


async def test_get_paths_returns_200_happy(
    pg_container: Any,
    seed_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    mock_clerk: Any,
) -> None:
    """D-14 — Clerk JWT + valid site_id with 2 computed_paths rows → 200 + list of length 2."""
    _patch_clerk(monkeypatch, mock_clerk)
    team, site, _tok = await _seed_team_and_site(seed_session)
    await _seed_computed_path(
        seed_session,
        team.id,
        site.id,
        src="10.0.0.0/24",
        dst="10.1.0.0/24",
        direction="forward",
    )
    await _seed_computed_path(
        seed_session,
        team.id,
        site.id,
        src="10.0.0.0/24",
        dst="10.1.0.0/24",
        direction="return",
    )

    with _build_app_client(pg_container, monkeypatch) as client:
        jwt = mock_clerk.sign_jwt(
            sub="u_owner",
            org_id=team.clerk_org_id,
            role="admin",
            azp="https://infracanvas.app",
        )
        r = client.get(
            f"/v1/sites/{site.id}/paths",
            headers={"Authorization": f"Bearer {jwt}"},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list)
    assert len(body) == 2, f"D-14: expected 2 latest paths (one per direction), got {len(body)}"
    directions = sorted(p["direction"] for p in body)
    assert directions == ["forward", "return"]


async def test_get_paths_cross_team_returns_404(
    pg_container: Any,
    seed_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    mock_clerk: Any,
) -> None:
    """Pattern C T-12-CC-1 — site-membership probe FIRST; cross-team site_id
    resolves to None under RLS → 404 ``site_not_found_or_no_access`` (not 403)."""
    _patch_clerk(monkeypatch, mock_clerk)
    # Team B owns the site
    team_b, site_b, _tb = await _seed_team_and_site(seed_session, name_suffix="_b")
    # Team A queries Team B's site
    team_a, _site_a, _ta = await _seed_team_and_site(seed_session, name_suffix="_a")

    with _build_app_client(pg_container, monkeypatch) as client:
        jwt_a = mock_clerk.sign_jwt(
            sub="u_a",
            org_id=team_a.clerk_org_id,
            role="admin",
            azp="https://infracanvas.app",
        )
        r = client.get(
            f"/v1/sites/{site_b.id}/paths",
            headers={"Authorization": f"Bearer {jwt_a}"},
        )
    assert r.status_code == 404, r.text
    assert r.json()["detail"] == "site_not_found_or_no_access"
    _ = team_b  # silence unused — kept for debugging context


def test_get_paths_missing_jwt_returns_401() -> None:
    """D-14 — no Authorization header → 401.

    No ``pg_container`` dependency — the JWT check fires before any DB
    access so this test runs in any environment (matches the Phase 11
    ``test_requires_clerk_jwt`` shape).
    """
    from app.main import create_app

    site_id = str(uuid.uuid4())
    with TestClient(create_app()) as client:
        r = client.get(f"/v1/sites/{site_id}/paths")
    assert r.status_code == 401, r.text


# ---------------------------------------------------------------------------
# D-14 — GET /v1/sites/{site_id}/asymmetries (cause filter, NET-010 surfaces)
# ---------------------------------------------------------------------------


async def test_asymmetries_filter_by_cause(
    pg_container: Any,
    seed_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    mock_clerk: Any,
) -> None:
    """D-14 — ?cause=NAT_ASYMMETRY filters response to NAT findings only.

    Warning 6 forward-test: also seed a NET-010 row but DO NOT filter for
    it — the unfiltered call should surface both NAT + ROUTE_LEAK rows.
    """
    _patch_clerk(monkeypatch, mock_clerk)
    team, site, _tok = await _seed_team_and_site(seed_session)
    await _seed_asymmetry(seed_session, team.id, site.id, cause="NAT_ASYMMETRY")
    await _seed_asymmetry(seed_session, team.id, site.id, cause="ROUTE_LEAK")

    with _build_app_client(pg_container, monkeypatch) as client:
        jwt = mock_clerk.sign_jwt(
            sub="u_owner",
            org_id=team.clerk_org_id,
            role="admin",
            azp="https://infracanvas.app",
        )
        # Filtered: only NAT
        r = client.get(
            f"/v1/sites/{site.id}/asymmetries?cause=NAT_ASYMMETRY",
            headers={"Authorization": f"Bearer {jwt}"},
        )
        assert r.status_code == 200, r.text
        rows = r.json()
        assert isinstance(rows, list)
        assert len(rows) == 1
        assert rows[0]["cause"] == "NAT_ASYMMETRY"

        # Unfiltered: both surface
        r2 = client.get(
            f"/v1/sites/{site.id}/asymmetries",
            headers={"Authorization": f"Bearer {jwt}"},
        )
        assert r2.status_code == 200, r2.text
        causes = sorted(row["cause"] for row in r2.json())
        assert causes == ["NAT_ASYMMETRY", "ROUTE_LEAK"]
