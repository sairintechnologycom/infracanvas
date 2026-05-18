"""Phase 12 D-04 + D-14 — POST /v1/sites/{site_id}/paths/recompute tests.

GREEN once Plan 12-03 (this plan) lands the on-demand recompute endpoint.

Asserts:
  * owner-only (member role → 403, owner → 202 + job_id OR 503 when the
    Plan 12-06 compute module isn't deployed yet)
  * coalescing: a recent computed_paths row within 60s triggers a
    coalesced response (no taskiq enqueue)
  * Warning 7: when ``app.queue.tasks.path_compute`` cannot be imported
    the response is 503 ``compute job not yet deployed`` (no fake
    job_id)
"""
from __future__ import annotations

import builtins
import hashlib
import secrets
import sys
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
# Helpers (mirror test_routes_firewall_read.py shape)
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
        clerk_org_id=f"org_pathrecomp_{secrets.token_hex(6)}{name_suffix}",
        name=f"Path Recompute Team{name_suffix}",
        stripe_customer_id=f"cus_pathrecomp{name_suffix}",
    )
    async with seed_session.begin():
        seed_session.add(team)
    raw_token = "ic_site_" + secrets.token_urlsafe(32)
    site = DCSite(
        id=uuid.uuid4(),
        team_id=team.id,
        name="Path Recompute Site",
        token_lookup_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
    )
    async with seed_session.begin():
        seed_session.add(site)
    return team, site, raw_token


async def _seed_recent_computed_path(
    seed_session: AsyncSession,
    team_id: uuid.UUID,
    site_id: uuid.UUID,
) -> None:
    """Seed one ``computed_paths`` row with ``computed_at = NOW()`` so the
    60-second coalesce window triggers."""
    now = datetime.now(tz=UTC)
    async with seed_session.begin():
        await seed_session.execute(
            text(
                "INSERT INTO computed_paths (path_id, team_id, site_id, "
                "pair_src_cidr, pair_dst_cidr, direction, hops, "
                "match_evidence, computed_at) VALUES "
                "(:pid, :tid, :sid, '10.0.0.0/24', '10.1.0.0/24', 'forward', "
                "'[]'::jsonb, '{}'::jsonb, :ts)"
            ),
            {
                "pid": str(uuid.uuid4()),
                "tid": str(team_id),
                "sid": str(site_id),
                "ts": now,
            },
        )


# ---------------------------------------------------------------------------
# D-14 — owner-only
# ---------------------------------------------------------------------------


async def test_recompute_owner_only(
    pg_container: Any,
    seed_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    mock_clerk: Any,
) -> None:
    """D-14 — member role → 403; owner role → 202 + job_id (or 503 when
    Plan 12-06 compute module not yet deployed; both are acceptable owner
    paths and demonstrate ``require_role('owner')`` passed)."""
    _patch_clerk(monkeypatch, mock_clerk)
    team, site, _tok = await _seed_team_and_site(seed_session)

    with _build_app_client(pg_container, monkeypatch) as client:
        # Member → 403 (require_role rejects)
        member_jwt = mock_clerk.sign_jwt(
            sub="u_member",
            org_id=team.clerk_org_id,
            role="member",
            azp="https://infracanvas.app",
        )
        r_member = client.post(
            f"/v1/sites/{site.id}/paths/recompute",
            headers={"Authorization": f"Bearer {member_jwt}"},
        )
        assert r_member.status_code == 403, r_member.text

        # Owner → 202 OR 503 (Warning 7 — compute module not yet deployed
        # in this build is acceptable; what matters is owner role passed
        # the require_role gate, NOT 403)
        owner_jwt = mock_clerk.sign_jwt(
            sub="u_owner",
            org_id=team.clerk_org_id,
            role="owner",
            azp="https://infracanvas.app",
        )
        r_owner = client.post(
            f"/v1/sites/{site.id}/paths/recompute",
            headers={"Authorization": f"Bearer {owner_jwt}"},
        )
        assert r_owner.status_code in (202, 503), r_owner.text
        if r_owner.status_code == 202:
            assert "job_id" in r_owner.json()
        else:
            assert r_owner.json()["detail"] == "compute job not yet deployed"


# ---------------------------------------------------------------------------
# D-04 — coalescing (within 60s, second POST is coalesced)
# ---------------------------------------------------------------------------


async def test_recompute_coalesces(
    pg_container: Any,
    seed_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    mock_clerk: Any,
) -> None:
    """D-04 — a recent computed_paths row (< 60s old) triggers the coalesce
    branch on the next POST → 202 with ``coalesced=True``.

    We seed the row directly (rather than triggering the compute task)
    so the test is hermetic and doesn't depend on Plan 12-06.
    """
    _patch_clerk(monkeypatch, mock_clerk)
    team, site, _tok = await _seed_team_and_site(seed_session)
    # Seed a fresh computed_path row → coalesce branch fires
    await _seed_recent_computed_path(seed_session, team.id, site.id)

    with _build_app_client(pg_container, monkeypatch) as client:
        owner_jwt = mock_clerk.sign_jwt(
            sub="u_owner",
            org_id=team.clerk_org_id,
            role="owner",
            azp="https://infracanvas.app",
        )
        r = client.post(
            f"/v1/sites/{site.id}/paths/recompute",
            headers={"Authorization": f"Bearer {owner_jwt}"},
        )
    assert r.status_code == 202, r.text
    body = r.json()
    assert body.get("coalesced") is True
    assert "job_id" in body
    assert body["job_id"].startswith("coalesced-")


# ---------------------------------------------------------------------------
# Warning 7 — 503 when path_compute module missing (no fake job_id)
# ---------------------------------------------------------------------------


async def test_recompute_returns_503_when_compute_module_missing(
    pg_container: Any,
    seed_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    mock_clerk: Any,
) -> None:
    """Warning 7 — when ``app.queue.tasks.path_compute`` is not importable,
    POST /paths/recompute returns HTTP 503 with detail ``"compute job
    not yet deployed"``. No fake ``job_id`` is minted.

    Forces ImportError via two layers (both required because Plan 12-06
    may have landed the real module by the time this test runs):
      1. Remove ``app.queue.tasks.path_compute`` from ``sys.modules`` if
         it's been imported.
      2. Patch ``builtins.__import__`` to raise ImportError on attempts
         to import that exact dotted path.
    """
    _patch_clerk(monkeypatch, mock_clerk)
    team, site, _tok = await _seed_team_and_site(seed_session)

    # Strip any cached import
    sys.modules.pop("app.queue.tasks.path_compute", None)

    real_import = builtins.__import__

    def _blocking_import(name: str, *args: Any, **kwargs: Any) -> Any:
        # The handler does `from app.queue.tasks.path_compute import ...`
        # which calls __import__("app.queue.tasks.path_compute", ...).
        if name == "app.queue.tasks.path_compute":
            raise ImportError(
                f"forced ImportError for test: {name} not yet deployed"
            )
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocking_import)

    with _build_app_client(pg_container, monkeypatch) as client:
        owner_jwt = mock_clerk.sign_jwt(
            sub="u_owner",
            org_id=team.clerk_org_id,
            role="owner",
            azp="https://infracanvas.app",
        )
        r = client.post(
            f"/v1/sites/{site.id}/paths/recompute",
            headers={"Authorization": f"Bearer {owner_jwt}"},
        )
    assert r.status_code == 503, r.text
    assert r.json() == {"detail": "compute job not yet deployed"}
