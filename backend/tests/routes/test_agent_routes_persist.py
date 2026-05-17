"""Phase 12 Blocker-1 regression — POST /v1/agent/routes + /v1/agent/flows
must persist rows under RLS.

Plan 12-02 lands ``route_records`` + ``netflow_records`` tables and wires
both ingest handlers to ``pg_insert`` under a team-scoped RLS GUC.

Pattern B DB probe applied: ``SELECT set_config('app.current_team_id',
:t, true)`` is run BEFORE any SQL probe (mirrors
``test_routes_firewall.py:191-237``). Pattern is necessary even with the
``seed_session`` fixture being BYPASSRLS, because the RLS probes serve
as documentation of the production trust posture.
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

# RED guard — until Plan 12-02 lands ``RouteRecordORM`` + ``NetFlowRecordORM``,
# the persistence assertions cannot run. Skip whole module at collection so we
# don't error on fixture pre-conditions either.
try:
    from app.db.models import DCSite, NetFlowRecordORM, RouteRecordORM, Team  # noqa: F401
except ImportError:
    pytest.skip(
        "Plan 12-02 to land RouteRecordORM + NetFlowRecordORM",
        allow_module_level=True,
    )

pytestmark = pytest.mark.rls


# ---------------------------------------------------------------------------
# Helpers (mirror test_routes_firewall.py shape — Pattern B context-set on probes)
# ---------------------------------------------------------------------------


def _build_app_client(
    pg_container: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    """Build a NullPool TestClient wired to the testcontainer's app role."""
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


async def _seed_team(seed_session: AsyncSession) -> Team:
    team = Team(
        id=uuid.uuid4(),
        clerk_org_id=f"org_pc_{secrets.token_hex(6)}",
        name="Path Compute Test Team",
        stripe_customer_id="cus_pc_test",
    )
    async with seed_session.begin():
        seed_session.add(team)
    return team


async def _seed_dc_site(
    seed_session: AsyncSession,
    team_id: uuid.UUID,
    raw_token: str,
) -> DCSite:
    lookup_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    site = DCSite(
        id=uuid.uuid4(),
        team_id=team_id,
        name="Path Compute Test Site",
        token_lookup_hash=lookup_hash,
    )
    async with seed_session.begin():
        seed_session.add(site)
    return site


def _routes_body(site_id: str) -> dict[str, Any]:
    return {
        "site_id": site_id,
        "collected_at": "2026-05-18T07:00:00Z",
        "device_host": "router-1",
        "routes": [
            {
                "prefix": "10.1.0.0/16",
                "next_hop": "192.168.1.1",
                "protocol": "bgp",
                "metric": 100,
                "as_path": "",
            },
            {
                "prefix": "10.2.0.0/16",
                "next_hop": "192.168.1.2",
                "protocol": "bgp",
                "metric": 100,
                "as_path": "",
            },
            {
                "prefix": "10.3.0.0/16",
                "next_hop": "192.168.1.3",
                "protocol": "bgp",
                "metric": 100,
                "as_path": "",
            },
        ],
    }


def _flows_body(site_id: str) -> dict[str, Any]:
    return {
        "site_id": site_id,
        "collected_at": "2026-05-18T07:00:00Z",
        "flows": [
            {
                "src_ip": f"10.1.0.{i}",
                "dst_ip": f"10.2.0.{i}",
                "src_port": 12345,
                "dst_port": 443,
                "protocol": 6,
                "bytes": 1000,
                "packets": 1,
            }
            for i in range(1, 6)
        ],
    }


# ---------------------------------------------------------------------------
# Blocker-1: routes push persists under RLS GUC (Pattern B)
# ---------------------------------------------------------------------------


async def test_push_routes_persists(
    pg_container: Any,
    seed_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Blocker 1 regression: POST /v1/agent/routes with valid site-token +
    3 routes → 202; SQL probe of route_records returns 3 rows for
    (site_id, device_host).

    Pattern B (mirrors test_routes_firewall.py:215-237):
        async with seed_session.begin():
            await seed_session.execute(text(
                "SELECT set_config('app.current_team_id', :t, true)"
            ), {"t": str(team.id)})
            count = (await seed_session.execute(text(
                "SELECT COUNT(*) FROM route_records WHERE site_id = :s"
            ), {"s": str(site.id)})).scalar()
    """
    team = await _seed_team(seed_session)
    raw_token = "ic_site_" + secrets.token_urlsafe(32)
    site = await _seed_dc_site(seed_session, team.id, raw_token)

    with _build_app_client(pg_container, monkeypatch) as client:
        r = client.post(
            "/v1/agent/routes",
            json=_routes_body(str(site.id)),
            headers={"Authorization": f"Bearer {raw_token}"},
        )
    assert r.status_code == 202, r.text
    assert r.json() == {"ok": True}

    async with seed_session.begin():
        await seed_session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team.id)},
        )
        count = (
            await seed_session.execute(
                text(
                    "SELECT COUNT(*) FROM route_records "
                    "WHERE site_id = :s AND device_host = :h"
                ),
                {"s": str(site.id), "h": "router-1"},
            )
        ).scalar()
    assert count == 3, "all 3 routes must persist under RLS GUC"


# ---------------------------------------------------------------------------
# Blocker-1: flows push persists under RLS GUC (v1.1 endpoint-only)
# ---------------------------------------------------------------------------


async def test_push_flows_persists(
    pg_container: Any,
    seed_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Blocker 1 regression: POST /v1/agent/flows with 5 flows → 202;
    SQL probe of netflow_records returns 5 rows (Pattern B applied).

    v1.1 endpoint-only per RESEARCH Q2 RESOLVED — netflow_records carries
    only src_ip/dst_ip/ports/protocol/bytes/packets; edge-hop fields
    deferred to v1.2.

    Pattern B (mirrors test_routes_firewall.py:215-237):
        async with seed_session.begin():
            await seed_session.execute(text(
                "SELECT set_config('app.current_team_id', :t, true)"
            ), {"t": str(team.id)})
            count = (await seed_session.execute(text(
                "SELECT COUNT(*) FROM netflow_records WHERE site_id = :s"
            ), {"s": str(site.id)})).scalar()
    """
    team = await _seed_team(seed_session)
    raw_token = "ic_site_" + secrets.token_urlsafe(32)
    site = await _seed_dc_site(seed_session, team.id, raw_token)

    with _build_app_client(pg_container, monkeypatch) as client:
        r = client.post(
            "/v1/agent/flows",
            json=_flows_body(str(site.id)),
            headers={"Authorization": f"Bearer {raw_token}"},
        )
    assert r.status_code == 202, r.text
    assert r.json() == {"ok": True}

    async with seed_session.begin():
        await seed_session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team.id)},
        )
        count = (
            await seed_session.execute(
                text("SELECT COUNT(*) FROM netflow_records WHERE site_id = :s"),
                {"s": str(site.id)},
            )
        ).scalar()
    assert count == 5, "all 5 flows must persist under RLS GUC"
