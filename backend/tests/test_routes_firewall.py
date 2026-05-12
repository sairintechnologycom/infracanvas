"""Wave 0 RED test stubs for Phase 11 firewall push endpoints.

Collection-RED until Plan 11-02 (migration) + 11-03 (routes) + 11-04 (schemas)
land ``firewall_ruleset_snapshots`` table + ``app.routes.firewalls`` /
``app.routes.agent`` extension.

Endpoints under test:
- POST /v1/agent/firewall-rules (D-18 #1)
- POST /v1/agent/firewall-nat (D-18 #2)
- POST /v1/agent/firewall-objects (D-18 #3)

All three accept ``Authorization: Bearer <site_token>`` (Pattern A, reused
from Phase 10 ``require_site_token``) and persist into team-RLS-scoped
tables under the caller's resolved ``team_id``.

Pattern E (RESEARCH): agent-minted ``snapshot_id`` deduplicates the parent
``firewall_ruleset_snapshots`` row via ``ON CONFLICT DO NOTHING``.
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
# Helpers (mirror test_agent.py shape — Pattern B context-set on DB probes)
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
        clerk_org_id=f"org_fw_{secrets.token_hex(6)}",
        name="Firewall Test Team",
        stripe_customer_id="cus_fw_test",
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
        name="Firewall Test Site",
        token_lookup_hash=lookup_hash,
    )
    async with seed_session.begin():
        seed_session.add(site)
    return site


def _rules_body(site_id: str, snapshot_id: str) -> dict[str, Any]:
    return {
        "site_id": site_id,
        "snapshot_id": snapshot_id,
        "firewall_id": "asa-edge-01",
        "vendor": "cisco-asa",
        "source": "asa-rest",
        "snapshot_ts": "2026-05-12T07:00:00Z",
        "rules": [
            {
                "position": 1,
                "src_zone": "outside",
                "dst_zone": "dmz",
                "src_cidr": "0.0.0.0/0",
                "dst_cidr": "10.1.1.10/32",
                "action": "permit",
                "protocol": "tcp",
                "ports": "80",
                "raw_blob": {"ruleId": 268435457},
            }
        ],
    }


def _nat_body(site_id: str, snapshot_id: str) -> dict[str, Any]:
    return {
        "site_id": site_id,
        "snapshot_id": snapshot_id,
        "firewall_id": "asa-edge-01",
        "vendor": "cisco-asa",
        "source": "asa-rest",
        "snapshot_ts": "2026-05-12T07:00:00Z",
        "nat_rules": [
            {
                "position": 1,
                "src_translation": "10.1.1.10 -> 203.0.113.10",
                "dst_translation": None,
                "interface_in": "inside",
                "interface_out": "outside",
                "raw_blob": {"objectId": "nat-rule-1"},
            }
        ],
    }


def _objects_body(site_id: str, snapshot_id: str) -> dict[str, Any]:
    return {
        "site_id": site_id,
        "snapshot_id": snapshot_id,
        "firewall_id": "asa-edge-01",
        "vendor": "cisco-asa",
        "source": "asa-rest",
        "snapshot_ts": "2026-05-12T07:00:00Z",
        "objects": [
            {
                "name": "web-server",
                "kind": "host",
                "value": {"ip": "10.1.1.10"},
                "raw_blob": {},
            }
        ],
    }


# ---------------------------------------------------------------------------
# T-11-XX-AUTH — missing bearer is 401 from require_site_token (Pattern A)
# ---------------------------------------------------------------------------


def test_push_rejects_missing_bearer() -> None:
    """D-19: all three push endpoints require Authorization: Bearer.

    Collection-RED until Plan 11-03 lands the routes; once routes exist
    but auth is missing, expect 401 missing_bearer from require_site_token.
    """
    from app.main import create_app

    site_id = str(uuid.uuid4())
    snapshot_id = str(uuid.uuid4())

    with TestClient(create_app()) as client:
        for path, body in (
            ("/v1/agent/firewall-rules", _rules_body(site_id, snapshot_id)),
            ("/v1/agent/firewall-nat", _nat_body(site_id, snapshot_id)),
            ("/v1/agent/firewall-objects", _objects_body(site_id, snapshot_id)),
        ):
            r = client.post(path, json=body)
            assert r.status_code == 401, f"{path}: expected 401, got {r.status_code}"
            assert r.json()["detail"] == "missing_bearer", f"{path}: detail mismatch"


# ---------------------------------------------------------------------------
# D-08 + D-18 — push rules persists into firewall_ruleset_snapshots + firewall_rules
# ---------------------------------------------------------------------------


async def test_push_firewall_rules_writes_snapshot_and_rules(
    pg_container: Any,
    seed_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-08 + D-18: rules push writes one parent row + N child rows.

    Probes use ``set_config('app.current_team_id', :t, true)`` BEFORE any
    SELECT (Pattern B — RLS context-set inside the transaction).
    """
    team = await _seed_team(seed_session)
    raw_token = "ic_site_" + secrets.token_urlsafe(32)
    site = await _seed_dc_site(seed_session, team.id, raw_token)
    snapshot_id = str(uuid.uuid4())

    with _build_app_client(pg_container, monkeypatch) as client:
        r = client.post(
            "/v1/agent/firewall-rules",
            json=_rules_body(str(site.id), snapshot_id),
            headers={"Authorization": f"Bearer {raw_token}"},
        )
    assert r.status_code == 202, r.text
    assert r.json() == {"ok": True}

    # Probe under team's RLS context (Pattern B)
    async with seed_session.begin():
        await seed_session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team.id)},
        )
        snap_count = (
            await seed_session.execute(
                text(
                    "SELECT count(*) FROM firewall_ruleset_snapshots "
                    "WHERE snapshot_id = :sid"
                ),
                {"sid": snapshot_id},
            )
        ).scalar()
        rule_count = (
            await seed_session.execute(
                text("SELECT count(*) FROM firewall_rules WHERE snapshot_id = :sid"),
                {"sid": snapshot_id},
            )
        ).scalar()
    assert snap_count == 1, "parent snapshot row must be inserted"
    assert rule_count == 1, "child rule row must be inserted"


# ---------------------------------------------------------------------------
# Pattern E — idempotent snapshot_id (ON CONFLICT DO NOTHING)
# ---------------------------------------------------------------------------


async def test_idempotent_snapshot_id(
    pg_container: Any,
    seed_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pattern E: posting the same snapshot_id twice must not duplicate the parent.

    Removes ordering coupling between the three endpoints — whichever
    arrives first creates the parent, subsequent pushes skip via
    ON CONFLICT DO NOTHING.
    """
    team = await _seed_team(seed_session)
    raw_token = "ic_site_" + secrets.token_urlsafe(32)
    site = await _seed_dc_site(seed_session, team.id, raw_token)
    snapshot_id = str(uuid.uuid4())

    with _build_app_client(pg_container, monkeypatch) as client:
        r1 = client.post(
            "/v1/agent/firewall-rules",
            json=_rules_body(str(site.id), snapshot_id),
            headers={"Authorization": f"Bearer {raw_token}"},
        )
        r2 = client.post(
            "/v1/agent/firewall-rules",
            json=_rules_body(str(site.id), snapshot_id),
            headers={"Authorization": f"Bearer {raw_token}"},
        )
    assert r1.status_code == 202
    assert r2.status_code == 202

    async with seed_session.begin():
        await seed_session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team.id)},
        )
        count = (
            await seed_session.execute(
                text(
                    "SELECT count(*) FROM firewall_ruleset_snapshots "
                    "WHERE snapshot_id = :sid"
                ),
                {"sid": snapshot_id},
            )
        ).scalar()
    assert count == 1, (
        "Pattern E: ON CONFLICT DO NOTHING — second push must not duplicate parent"
    )


# ---------------------------------------------------------------------------
# D-18 — three endpoints share one snapshot_id (any-order, parent created once)
# ---------------------------------------------------------------------------


async def test_three_endpoints_share_snapshot_id(
    pg_container: Any,
    seed_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-18: posting to rules + nat + objects with the same snapshot_id
    creates the parent exactly once and populates all three child tables."""
    team = await _seed_team(seed_session)
    raw_token = "ic_site_" + secrets.token_urlsafe(32)
    site = await _seed_dc_site(seed_session, team.id, raw_token)
    snapshot_id = str(uuid.uuid4())
    hdr = {"Authorization": f"Bearer {raw_token}"}

    with _build_app_client(pg_container, monkeypatch) as client:
        # Order intentionally not 1-2-3 — must work in any order
        r_objects = client.post(
            "/v1/agent/firewall-objects",
            json=_objects_body(str(site.id), snapshot_id),
            headers=hdr,
        )
        r_rules = client.post(
            "/v1/agent/firewall-rules",
            json=_rules_body(str(site.id), snapshot_id),
            headers=hdr,
        )
        r_nat = client.post(
            "/v1/agent/firewall-nat",
            json=_nat_body(str(site.id), snapshot_id),
            headers=hdr,
        )
    assert r_objects.status_code == 202
    assert r_rules.status_code == 202
    assert r_nat.status_code == 202

    async with seed_session.begin():
        await seed_session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team.id)},
        )
        parent = (
            await seed_session.execute(
                text(
                    "SELECT count(*) FROM firewall_ruleset_snapshots "
                    "WHERE snapshot_id = :sid"
                ),
                {"sid": snapshot_id},
            )
        ).scalar()
        rules = (
            await seed_session.execute(
                text("SELECT count(*) FROM firewall_rules WHERE snapshot_id = :sid"),
                {"sid": snapshot_id},
            )
        ).scalar()
        nats = (
            await seed_session.execute(
                text(
                    "SELECT count(*) FROM firewall_nat_rules "
                    "WHERE snapshot_id = :sid"
                ),
                {"sid": snapshot_id},
            )
        ).scalar()
        objs = (
            await seed_session.execute(
                text(
                    "SELECT count(*) FROM firewall_objects WHERE snapshot_id = :sid"
                ),
                {"sid": snapshot_id},
            )
        ).scalar()
    assert parent == 1, "parent row created exactly once across three pushes"
    assert rules >= 1, "rules child rows populated"
    assert nats >= 1, "nat child rows populated"
    assert objs >= 1, "objects child rows populated"


# ---------------------------------------------------------------------------
# D-09 — objects table kind enum + value JSONB
# ---------------------------------------------------------------------------


async def test_push_firewall_objects_persists(
    pg_container: Any,
    seed_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-09: firewall_objects rows carry kind enum + value JSONB."""
    team = await _seed_team(seed_session)
    raw_token = "ic_site_" + secrets.token_urlsafe(32)
    site = await _seed_dc_site(seed_session, team.id, raw_token)
    snapshot_id = str(uuid.uuid4())

    with _build_app_client(pg_container, monkeypatch) as client:
        r = client.post(
            "/v1/agent/firewall-objects",
            json=_objects_body(str(site.id), snapshot_id),
            headers={"Authorization": f"Bearer {raw_token}"},
        )
    assert r.status_code == 202, r.text

    async with seed_session.begin():
        await seed_session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team.id)},
        )
        result = await seed_session.execute(
            text(
                "SELECT kind, value FROM firewall_objects "
                "WHERE snapshot_id = :sid AND name = 'web-server'"
            ),
            {"sid": snapshot_id},
        )
        row = result.first()
    assert row is not None, "firewall_objects row must be inserted"
    assert row[0] == "host", "kind enum must round-trip"
