"""Tests for ``GET /v1/scans/{a}/compare/{b}`` — server-side scan diff (Plan 07-03).

Test IDs:

    CMP-001  unit: compute_diff on identical graphs returns all-unchanged nodes
    CMP-002  unit: compute_diff with all-added nodes (graph_a empty)
    CMP-003  unit: compute_diff with mixed added/removed/changed
    CMP-004  unit: edges_added / edges_removed are diffed by tuple identity
    CMP-005  integration: same-team scans return 200 with correct diff shape
    CMP-006  integration: cross-team scan_a returns 404 (D-18)
    CMP-007  integration: cross-team scan_b returns 404 (D-18)
    CMP-008  integration: scan_a == scan_b returns 200 with all-unchanged summary
    CMP-009  integration: missing R2 blob → 404 ``object_not_found``

Unit tests use ``SimpleNamespace`` graph stand-ins because ``compute_diff``
is duck-typed against ``.nodes`` / ``.edges`` collections — the function
contract does not require real ``ResourceGraph`` instances. This keeps the
unit suite zero-dependency.

Integration tests follow the pattern in ``test_scans_list.py``: local autouse
hooks for moto-backed R2 + Clerk JWKS, ``app_client`` TestClient on a fresh
NullPool engine, and a ``seed_scan_factory`` that inserts via the BYPASSRLS
seed session.
"""
from __future__ import annotations

import json
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import boto3
import pytest
import pytest_asyncio
from botocore.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Scan, ScanStatus, Team
from app.services.diff import compute_diff
from app.util.ids import new_uuid7


# ---------------------------------------------------------------------------
# Unit tests — pure compute_diff, no fixtures.
# ---------------------------------------------------------------------------


def _make_graph(nodes: list[dict], edges: list[dict] | None = None) -> Any:
    """Build a duck-typed ResourceGraph stand-in for unit tests.

    ``compute_diff`` accesses ``.nodes`` / ``.edges`` / per-node
    ``.id`` and ``.attributes`` / per-edge ``.source``, ``.target``,
    ``.relationship``. SimpleNamespace satisfies that without the
    Pydantic model overhead.
    """
    node_objs = [
        SimpleNamespace(
            id=n["id"],
            type=n.get("type", "aws_instance"),
            attributes=n.get("attributes", {}),
        )
        for n in nodes
    ]
    edge_objs = [
        SimpleNamespace(
            source=e["source"],
            target=e["target"],
            relationship=e.get("relationship", "depends_on"),
        )
        for e in (edges or [])
    ]
    return SimpleNamespace(nodes=node_objs, edges=edge_objs)


def test_compute_diff_identical() -> None:
    """CMP-001: identical graphs yield all-unchanged nodes, no edge diffs."""
    node = {
        "id": "res-1",
        "attributes": {"ami": "ami-123", "instance_type": "t3.micro"},
    }
    graph = _make_graph([node])
    a_id = uuid.uuid4()
    b_id = uuid.uuid4()
    result = compute_diff(graph, graph, scan_a_id=a_id, scan_b_id=b_id)
    assert result.summary["unchanged"] == 1
    assert result.summary["added"] == 0
    assert result.summary["removed"] == 0
    assert result.summary["changed"] == 0
    assert result.edges_added == []
    assert result.edges_removed == []
    assert result.scan_a_id == a_id
    assert result.scan_b_id == b_id
    # Single node, kind=="unchanged", changed_fields empty.
    assert len(result.nodes) == 1
    nd = result.nodes[0]
    assert nd.kind == "unchanged"
    assert nd.changed_fields == []


def test_compute_diff_all_added() -> None:
    """CMP-002: all nodes in graph_b not in graph_a are 'added'."""
    graph_a = _make_graph([])
    graph_b = _make_graph(
        [
            {"id": "res-1", "attributes": {"ami": "ami-123"}},
            {"id": "res-2", "attributes": {"ami": "ami-456"}},
        ]
    )
    result = compute_diff(
        graph_a, graph_b, scan_a_id=uuid.uuid4(), scan_b_id=uuid.uuid4()
    )
    assert result.summary["added"] == 2
    assert result.summary["removed"] == 0
    assert result.summary["unchanged"] == 0
    assert result.summary["changed"] == 0
    for nd in result.nodes:
        assert nd.kind == "added"
        assert nd.before is None
        assert nd.after is not None


def test_compute_diff_mixed() -> None:
    """CMP-003: mixed added/removed/changed produces correct kinds/changed_fields."""
    graph_a = _make_graph(
        [
            {"id": "kept", "attributes": {"x": 1}},
            {"id": "removed", "attributes": {"x": 2}},
            {"id": "changed", "attributes": {"x": 3, "y": "old"}},
        ]
    )
    graph_b = _make_graph(
        [
            {"id": "kept", "attributes": {"x": 1}},
            {"id": "added", "attributes": {"x": 9}},
            {"id": "changed", "attributes": {"x": 3, "y": "new"}},
        ]
    )
    result = compute_diff(
        graph_a, graph_b, scan_a_id=uuid.uuid4(), scan_b_id=uuid.uuid4()
    )
    kinds = {nd.id: nd.kind for nd in result.nodes}
    assert kinds["kept"] == "unchanged"
    assert kinds["removed"] == "removed"
    assert kinds["added"] == "added"
    assert kinds["changed"] == "changed"

    changed_nd = next(nd for nd in result.nodes if nd.id == "changed")
    assert "y" in changed_nd.changed_fields
    assert "x" not in changed_nd.changed_fields  # x is same → not in changed_fields

    # Removed node carries before, no after.
    removed_nd = next(nd for nd in result.nodes if nd.id == "removed")
    assert removed_nd.before is not None
    assert removed_nd.after is None
    # Added node carries after, no before.
    added_nd = next(nd for nd in result.nodes if nd.id == "added")
    assert added_nd.before is None
    assert added_nd.after is not None

    assert result.summary == {"added": 1, "removed": 1, "changed": 1, "unchanged": 1}


def test_compute_diff_edges() -> None:
    """CMP-004: edges_added / edges_removed are tuple-set diffed."""
    graph_a = _make_graph(
        [{"id": "a"}, {"id": "b"}, {"id": "c"}],
        edges=[
            {"source": "a", "target": "b", "relationship": "depends_on"},
            {"source": "b", "target": "c", "relationship": "depends_on"},
        ],
    )
    graph_b = _make_graph(
        [{"id": "a"}, {"id": "b"}, {"id": "c"}],
        edges=[
            # a→b survives; b→c removed; new a→c added.
            {"source": "a", "target": "b", "relationship": "depends_on"},
            {"source": "a", "target": "c", "relationship": "depends_on"},
        ],
    )
    result = compute_diff(
        graph_a, graph_b, scan_a_id=uuid.uuid4(), scan_b_id=uuid.uuid4()
    )
    added_keys = {(e["source"], e["target"], e["relationship"]) for e in result.edges_added}
    removed_keys = {
        (e["source"], e["target"], e["relationship"]) for e in result.edges_removed
    }
    assert added_keys == {("a", "c", "depends_on")}
    assert removed_keys == {("b", "c", "depends_on")}


# ---------------------------------------------------------------------------
# Integration tests — real DB + moto R2 + Clerk JWKS mock.
# ---------------------------------------------------------------------------

pytestmark_integration = pytest.mark.rls


def _moto_s3_client() -> Any:
    return boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4"),
    )


@pytest.fixture
def wire_r2_to_moto(monkeypatch: pytest.MonkeyPatch, mock_r2: Any) -> Any:
    """Replace ``app.storage.r2.get_r2_client`` with a moto-compatible client.

    Returns the moto client so the test can directly seed scan blobs at the
    keys the compare handler will read.
    """
    from app.settings import settings
    from app.storage import r2 as r2_mod

    r2_mod.get_r2_client.cache_clear()
    monkeypatch.setattr(settings, "r2_bucket", mock_r2.bucket)

    moto_client = _moto_s3_client()

    def _client_override():  # type: ignore[no-untyped-def]
        return moto_client

    monkeypatch.setattr(r2_mod, "get_r2_client", _client_override)
    return moto_client


@pytest.fixture
def patch_clerk_jwks(monkeypatch: pytest.MonkeyPatch, mock_clerk: Any) -> None:
    """Point ``app.auth.clerk._jwks_client`` at the fixture-local JWKS endpoint."""
    import app.auth.clerk as clerk_mod
    from jwt import PyJWKClient

    monkeypatch.setattr(clerk_mod, "_jwks_client", PyJWKClient(mock_clerk.jwks_url))
    from app.settings import settings

    monkeypatch.setattr(settings, "clerk_issuer", "https://clerk.infracanvas.app")
    monkeypatch.setattr(
        settings, "clerk_allowed_origins", ["https://infracanvas.app"]
    )


@pytest_asyncio.fixture
async def team_a(seed_session: AsyncSession) -> Team:
    t = Team(
        id=new_uuid7(),
        clerk_org_id=f"org_cmp_a_{secrets.token_hex(6)}",
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
        clerk_org_id=f"org_cmp_b_{secrets.token_hex(6)}",
        name="Team B",
        stripe_customer_id="cus_b",
    )
    async with seed_session.begin():
        seed_session.add(t)
    return t


@pytest.fixture
def auth_headers_factory(mock_clerk: Any):
    """Mint a Bearer header for a given clerk_org_id."""

    def _make(org_id: str, role: str = "admin", sub: str = "u1") -> dict[str, str]:
        token = mock_clerk.sign_jwt(sub=sub, org_id=org_id, role=role)
        return {"Authorization": f"Bearer {token}"}

    return _make


@pytest.fixture
def app_client(
    patch_clerk_jwks: None, pg_container: Any, monkeypatch: pytest.MonkeyPatch
) -> Any:
    """TestClient against a fresh app instance with a NullPool async engine."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

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

    app = create_app()
    with TestClient(app) as c:
        yield c


def _valid_graph_blob(nodes: list[dict] | None = None, edges: list[dict] | None = None) -> bytes:
    """Build a minimum-shape valid ResourceGraph JSON blob accepted by Pydantic."""
    return json.dumps(
        {
            "nodes": nodes or [],
            "edges": edges or [],
            "summary": {
                "total_resources": len(nodes or []),
                "findings": {"critical": 0, "high": 0, "medium": 0, "info": 0},
                "estimated_monthly_cost": 0.0,
                "score": 100,
            },
            "metadata": {},
        }
    ).encode()


@pytest_asyncio.fixture
async def seed_scan_with_blob(
    seed_session: AsyncSession,
    team_a: Team,
    wire_r2_to_moto: Any,
    mock_r2: Any,
):
    """Insert a Scan row + matching R2 object so compare can fetch the bytes.

    Returns an async factory: ``await seed_scan_with_blob(team=team_a, blob=...)``.
    Defaults: team=team_a, blob=empty-graph, status=ready.
    """
    counter = {"n": 0}
    base_ts = datetime.now(timezone.utc) - timedelta(days=30)

    async def _factory(
        *,
        team: Team | None = None,
        blob: bytes | None = None,
        status: ScanStatus = ScanStatus.ready,
    ) -> Scan:
        counter["n"] += 1
        owning_team = team or team_a
        if blob is None:
            blob = _valid_graph_blob()
        scan_id = new_uuid7()
        r2_key = f"teams/{owning_team.id}/scans/{scan_id}.json"
        # Put bytes into the moto bucket at the key compare_scans will read.
        wire_r2_to_moto.put_object(Bucket=mock_r2.bucket, Key=r2_key, Body=blob)
        scan = Scan(
            id=scan_id,
            team_id=owning_team.id,
            r2_key=r2_key,
            sha256=secrets.token_hex(32),
            size_bytes=len(blob),
            status=status,
            branch=None,
            commit_sha=None,
            source="cli",
            created_at=base_ts + timedelta(seconds=counter["n"]),
        )
        async with seed_session.begin():
            seed_session.add(scan)
        return scan

    return _factory


# --- Integration tests ---


@pytest.mark.rls
async def test_compare_scans_same_team(
    app_client: Any,
    team_a: Team,
    auth_headers_factory: Any,
    seed_scan_with_blob: Any,
) -> None:
    """CMP-005: same-team compare returns 200 with ResourceDiffResp shape."""
    blob_a = _valid_graph_blob(
        nodes=[
            {
                "id": "res-1",
                "type": "aws_instance",
                "name": "res-1",
                "provider": "aws",
                "attributes": {"ami": "ami-123"},
            }
        ],
    )
    blob_b = _valid_graph_blob(
        nodes=[
            {
                "id": "res-1",
                "type": "aws_instance",
                "name": "res-1",
                "provider": "aws",
                "attributes": {"ami": "ami-999"},
            },
            {
                "id": "res-2",
                "type": "aws_instance",
                "name": "res-2",
                "provider": "aws",
                "attributes": {"ami": "ami-new"},
            },
        ],
    )
    scan_a = await seed_scan_with_blob(blob=blob_a)
    scan_b = await seed_scan_with_blob(blob=blob_b)
    headers = auth_headers_factory(team_a.clerk_org_id)
    resp = app_client.get(
        f"/v1/scans/{scan_a.id}/compare/{scan_b.id}", headers=headers
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "nodes" in data
    assert "edges_added" in data
    assert "edges_removed" in data
    assert "summary" in data
    assert "scan_a_id" in data
    assert "scan_b_id" in data
    for key in ("added", "removed", "changed", "unchanged"):
        assert key in data["summary"]
    # res-1 changed (ami differs); res-2 added.
    assert data["summary"]["changed"] == 1
    assert data["summary"]["added"] == 1


@pytest.mark.rls
async def test_compare_scans_cross_team_scan_a(
    app_client: Any,
    team_a: Team,
    team_b: Team,
    auth_headers_factory: Any,
    seed_scan_with_blob: Any,
) -> None:
    """CMP-006: scan_a belonging to team B returns 404 (D-18: don't leak)."""
    scan_a_b = await seed_scan_with_blob(team=team_b)  # owned by team B
    scan_b_a = await seed_scan_with_blob(team=team_a)  # owned by team A
    # Authenticate as team A.
    headers = auth_headers_factory(team_a.clerk_org_id)
    resp = app_client.get(
        f"/v1/scans/{scan_a_b.id}/compare/{scan_b_a.id}", headers=headers
    )
    assert resp.status_code == 404


@pytest.mark.rls
async def test_compare_scans_cross_team_scan_b(
    app_client: Any,
    team_a: Team,
    team_b: Team,
    auth_headers_factory: Any,
    seed_scan_with_blob: Any,
) -> None:
    """CMP-007: scan_b belonging to team B returns 404."""
    scan_a_a = await seed_scan_with_blob(team=team_a)
    scan_b_b = await seed_scan_with_blob(team=team_b)
    headers = auth_headers_factory(team_a.clerk_org_id)
    resp = app_client.get(
        f"/v1/scans/{scan_a_a.id}/compare/{scan_b_b.id}", headers=headers
    )
    assert resp.status_code == 404


@pytest.mark.rls
async def test_compare_scans_identical(
    app_client: Any,
    team_a: Team,
    auth_headers_factory: Any,
    seed_scan_with_blob: Any,
) -> None:
    """CMP-008: comparing a scan against itself returns all-unchanged summary."""
    scan = await seed_scan_with_blob(
        blob=_valid_graph_blob(
            nodes=[
                {
                    "id": "res-1",
                    "type": "aws_instance",
                    "name": "res-1",
                    "provider": "aws",
                    "attributes": {"ami": "ami-123"},
                }
            ]
        )
    )
    headers = auth_headers_factory(team_a.clerk_org_id)
    resp = app_client.get(
        f"/v1/scans/{scan.id}/compare/{scan.id}", headers=headers
    )
    assert resp.status_code == 200, resp.text
    summary = resp.json()["summary"]
    assert summary["added"] == 0
    assert summary["removed"] == 0
    assert summary["changed"] == 0
    # Single node, all-unchanged.
    assert summary["unchanged"] == 1


@pytest.mark.rls
async def test_compare_scans_missing_blob(
    app_client: Any,
    team_a: Team,
    auth_headers_factory: Any,
    seed_session: AsyncSession,
    wire_r2_to_moto: Any,
    mock_r2: Any,
) -> None:
    """CMP-009: scan row exists but R2 blob is missing → 404 object_not_found."""
    # Insert a scan row whose r2_key points at a non-existent object.
    scan_id = new_uuid7()
    other_id = new_uuid7()
    missing_key = f"teams/{team_a.id}/scans/{scan_id}.json"
    other_key = f"teams/{team_a.id}/scans/{other_id}.json"
    # Seed only the second blob so one of the two reads fails.
    wire_r2_to_moto.put_object(
        Bucket=mock_r2.bucket, Key=other_key, Body=_valid_graph_blob()
    )
    async with seed_session.begin():
        seed_session.add(
            Scan(
                id=scan_id,
                team_id=team_a.id,
                r2_key=missing_key,
                sha256=secrets.token_hex(32),
                size_bytes=10,
                status=ScanStatus.ready,
                source="cli",
            )
        )
        seed_session.add(
            Scan(
                id=other_id,
                team_id=team_a.id,
                r2_key=other_key,
                sha256=secrets.token_hex(32),
                size_bytes=10,
                status=ScanStatus.ready,
                source="cli",
            )
        )
    headers = auth_headers_factory(team_a.clerk_org_id)
    resp = app_client.get(
        f"/v1/scans/{scan_id}/compare/{other_id}", headers=headers
    )
    assert resp.status_code == 404
