"""Integration tests for ``GET /v1/scans`` — list endpoint with filters
and cursor pagination (Plan 07-02).

Test IDs:
    LST-001  basic list returns items and no next_cursor when <= limit
    LST-002  search filter matches on branch (ILIKE)
    LST-003  search filter matches on commit_sha (ILIKE)
    LST-004  status filter returns only matching rows
    LST-005  created_after / created_before range filter
    LST-006  cursor pagination: page 1 sets next_cursor; page 2 advances
    LST-007  last page (rows <= limit) returns next_cursor=None
    LST-008  cross-team isolation: team B sees zero of team A's scans
    LST-009  invalid created_after returns 422
    LST-010  limit > 100 returns 422 (FastAPI Query validation)

Fixtures (``app_client``, ``team_a``, ``team_b``, ``auth_headers_factory``,
``mock_r2``, ``stub_stripe_meter``, ``patch_clerk_jwks``, ``seed_session``)
are reused from conftest.py and test_scans.py — but the autouse R2 wiring
and Clerk JWKS patching live in test_scans.py, not here. To keep this
module self-contained, we redeclare the equivalent autouse hooks below.

All tests carry the ``rls`` marker — they need a real Postgres testcontainer.
"""
from __future__ import annotations

import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import boto3
import pytest
import pytest_asyncio
from botocore.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Scan, ScanStatus, Team
from app.util.ids import new_uuid7

pytestmark = pytest.mark.rls


# ---------------------------------------------------------------------------
# Local autouse hooks — mirror test_scans.py so this module can run in
# isolation (`pytest tests/test_scans_list.py`) without depending on
# test_scans.py being collected.
# ---------------------------------------------------------------------------


def _moto_s3_client() -> Any:
    return boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4"),
    )


@pytest.fixture(autouse=True)
def _wire_r2_to_moto(monkeypatch: pytest.MonkeyPatch, mock_r2: Any) -> None:
    """Replace ``app.storage.r2.get_r2_client`` with a moto-compatible client.

    list_scans never calls R2 — it only emits SQL. We still wire R2 to moto
    so that any incidental R2 client construction (lazy module init) does
    not blow up on missing real credentials.
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
def patch_clerk_jwks(monkeypatch: pytest.MonkeyPatch, mock_clerk: Any) -> None:
    """Point ``app.auth.clerk._jwks_client`` at the fixture-local JWKS endpoint
    AND align ``settings.clerk_issuer`` with mock_clerk's signed iss claim."""
    import app.auth.clerk as clerk_mod
    from jwt import PyJWKClient

    monkeypatch.setattr(clerk_mod, "_jwks_client", PyJWKClient(mock_clerk.jwks_url))
    from app.settings import settings

    monkeypatch.setattr(settings, "clerk_issuer", "https://clerk.infracanvas.app")
    monkeypatch.setattr(
        settings, "clerk_allowed_origins", ["https://infracanvas.app"]
    )


# ---------------------------------------------------------------------------
# Team fixtures (BYPASSRLS seed) — random clerk_org_id per test so the
# session-scoped pg_container can host successive runs without UNIQUE
# violations.
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def team_a(seed_session: AsyncSession) -> Team:
    t = Team(
        id=new_uuid7(),
        clerk_org_id=f"org_lst_a_{secrets.token_hex(6)}",
        name="Team A",
        stripe_customer_id="cus_a",
    )
    async with seed_session.begin():
        seed_session.add(t)
    return t


@pytest_asyncio.fixture
async def team_b(seed_session: AsyncSession) -> Team:
    t = Team(
        id=new_uuid7(),
        clerk_org_id=f"org_lst_b_{secrets.token_hex(6)}",
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
    connection on whatever event loop TestClient is using.
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
# seed_scan_factory — local fixture that inserts Scan rows for a given team
# via the BYPASSRLS seed session. Uses a separate counter for created_at so
# rows are deterministically ordered when the test does not specify times.
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def seed_scan_factory(seed_session: AsyncSession, team_a: Team):
    """Async factory: ``await seed_scan_factory(branch=..., status=...)``.

    Defaults: team_id=team_a.id, status=ready, source="cli", random sha,
    deterministic created_at (each call advances by 1 second to avoid ties).
    Returns the inserted Scan model row.
    """
    counter = {"n": 0}
    base_ts = datetime.now(timezone.utc) - timedelta(days=30)

    async def _factory(
        *,
        team_id: uuid.UUID | None = None,
        branch: str | None = None,
        commit_sha: str | None = None,
        source: str | None = "cli",
        status: ScanStatus | str = ScanStatus.ready,
        size_bytes: int | None = 1024,
        created_at: datetime | None = None,
    ) -> Scan:
        counter["n"] += 1
        if created_at is None:
            created_at = base_ts + timedelta(seconds=counter["n"])
        if isinstance(status, str):
            status = ScanStatus(status)
        scan_id = new_uuid7()
        tid = team_id or team_a.id
        scan = Scan(
            id=scan_id,
            team_id=tid,
            r2_key=f"teams/{tid}/scans/{scan_id}.json",
            sha256=secrets.token_hex(32),
            size_bytes=size_bytes,
            status=status,
            branch=branch,
            commit_sha=commit_sha,
            source=source,
            created_at=created_at,
        )
        async with seed_session.begin():
            seed_session.add(scan)
        return scan

    return _factory


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_list_scans_basic(
    app_client: Any,
    team_a: Team,
    auth_headers_factory: Any,
    seed_scan_factory: Any,
) -> None:
    """LST-001: single seeded scan is returned; next_cursor is None."""
    await seed_scan_factory(branch="main")
    headers = auth_headers_factory(team_a.clerk_org_id)
    resp = app_client.get("/v1/scans", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "items" in data
    assert "next_cursor" in data
    assert len(data["items"]) >= 1
    assert data["next_cursor"] is None


async def test_list_scans_search_branch(
    app_client: Any,
    team_a: Team,
    auth_headers_factory: Any,
    seed_scan_factory: Any,
) -> None:
    """LST-002: ?search= performs ILIKE match on branch."""
    await seed_scan_factory(branch="feature/xyz", source="cli")
    await seed_scan_factory(branch="main", source="cli")
    headers = auth_headers_factory(team_a.clerk_org_id)
    resp = app_client.get("/v1/scans?search=feature", headers=headers)
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) >= 1
    # All rows returned must match somewhere across branch/commit_sha/source.
    for it in items:
        haystack = " ".join(
            (it.get("branch") or "", it.get("commit_sha") or "", it.get("source") or "")
        ).lower()
        assert "feature" in haystack


async def test_list_scans_search_commit_sha(
    app_client: Any,
    team_a: Team,
    auth_headers_factory: Any,
    seed_scan_factory: Any,
) -> None:
    """LST-003: ?search= performs ILIKE match on commit_sha."""
    await seed_scan_factory(commit_sha="abc123deadbeef", source="cli")
    await seed_scan_factory(commit_sha="000000", source="cli")
    headers = auth_headers_factory(team_a.clerk_org_id)
    resp = app_client.get("/v1/scans?search=abc123", headers=headers)
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["commit_sha"] == "abc123deadbeef"


async def test_list_scans_status_filter(
    app_client: Any,
    team_a: Team,
    auth_headers_factory: Any,
    seed_scan_factory: Any,
) -> None:
    """LST-004: ?status=ready returns only ready scans."""
    await seed_scan_factory(status=ScanStatus.ready)
    await seed_scan_factory(status=ScanStatus.failed)
    await seed_scan_factory(status=ScanStatus.pending)
    headers = auth_headers_factory(team_a.clerk_org_id)
    resp = app_client.get("/v1/scans?status=ready", headers=headers)
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) >= 1
    assert all(i["status"] == "ready" for i in items)


async def test_list_scans_date_range(
    app_client: Any,
    team_a: Team,
    auth_headers_factory: Any,
    seed_scan_factory: Any,
) -> None:
    """LST-005: created_after / created_before narrow by created_at."""
    now = datetime.now(timezone.utc)
    after_ts = now - timedelta(days=10)
    before_ts = now - timedelta(days=1)
    # Inside the (after, before) window.
    await seed_scan_factory(
        branch="in-range",
        created_at=now - timedelta(days=5),
    )
    # Outside (older than after_ts).
    await seed_scan_factory(
        branch="too-old",
        created_at=now - timedelta(days=20),
    )
    headers = auth_headers_factory(team_a.clerk_org_id)
    # URL-encode the ISO timestamps because raw '+' gets decoded as space.
    after_q = quote(after_ts.isoformat(), safe="")
    before_q = quote(before_ts.isoformat(), safe="")
    resp = app_client.get(
        f"/v1/scans?created_after={after_q}&created_before={before_q}",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    branches = {i["branch"] for i in items if i.get("branch")}
    assert "in-range" in branches
    assert "too-old" not in branches
    # Spot-check timestamps fall inside the window.
    for i in items:
        ts = datetime.fromisoformat(i["created_at"])
        assert ts >= after_ts
        assert ts <= before_ts


async def test_list_scans_cursor_pagination(
    app_client: Any,
    team_a: Team,
    auth_headers_factory: Any,
    seed_scan_factory: Any,
) -> None:
    """LST-006: page 1 with limit=1 returns next_cursor; page 2 advances."""
    for i in range(3):
        await seed_scan_factory(branch=f"b{i}")
    headers = auth_headers_factory(team_a.clerk_org_id)
    resp1 = app_client.get("/v1/scans?limit=1", headers=headers)
    assert resp1.status_code == 200, resp1.text
    data1 = resp1.json()
    assert len(data1["items"]) == 1
    assert data1["next_cursor"] is not None

    resp2 = app_client.get(
        f"/v1/scans?limit=1&cursor={data1['next_cursor']}", headers=headers
    )
    assert resp2.status_code == 200, resp2.text
    data2 = resp2.json()
    assert len(data2["items"]) == 1
    # Pages must not repeat the same scan id.
    assert data1["items"][0]["id"] != data2["items"][0]["id"]


async def test_list_scans_last_page_no_cursor(
    app_client: Any,
    team_a: Team,
    auth_headers_factory: Any,
    seed_scan_factory: Any,
) -> None:
    """LST-007: when fewer than limit rows remain, next_cursor is None."""
    await seed_scan_factory()
    await seed_scan_factory()
    headers = auth_headers_factory(team_a.clerk_org_id)
    resp = app_client.get("/v1/scans?limit=100", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["next_cursor"] is None


async def test_list_scans_cross_team_isolation(
    app_client: Any,
    team_a: Team,
    team_b: Team,
    auth_headers_factory: Any,
    seed_scan_factory: Any,
) -> None:
    """LST-008: scans seeded for team A are not visible to team B."""
    # team_a seeded with several scans via the factory (default team).
    await seed_scan_factory(branch="a-only-1")
    await seed_scan_factory(branch="a-only-2")
    headers_b = auth_headers_factory(team_b.clerk_org_id, sub="u_b")
    resp = app_client.get("/v1/scans", headers=headers_b)
    assert resp.status_code == 200, resp.text
    # team B sees zero items — RLS hides team A's rows.
    assert resp.json()["items"] == []
    assert resp.json()["next_cursor"] is None


async def test_list_scans_invalid_date(
    app_client: Any,
    team_a: Team,
    auth_headers_factory: Any,
) -> None:
    """LST-009: non-ISO created_after returns 422."""
    headers = auth_headers_factory(team_a.clerk_org_id)
    resp = app_client.get(
        "/v1/scans?created_after=not-a-date", headers=headers
    )
    assert resp.status_code == 422


async def test_list_scans_limit_too_large(
    app_client: Any,
    team_a: Team,
    auth_headers_factory: Any,
) -> None:
    """LST-010: limit > 100 returns 422 (FastAPI Query validation)."""
    headers = auth_headers_factory(team_a.clerk_org_id)
    resp = app_client.get("/v1/scans?limit=101", headers=headers)
    assert resp.status_code == 422
