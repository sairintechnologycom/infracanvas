"""Phase 12 D-04 + D-14 — POST /v1/sites/{site_id}/paths/recompute tests.

GREEN once Plan 12-03 lands the on-demand recompute endpoint.

Asserts:
  * owner-only (member role → 403, owner → 202 + job_id; Plan 12-06
    landed the compute module so the 503-fallback path is gone)
  * coalescing: a recent computed_paths row within 60s triggers a
    coalesced response (no taskiq enqueue)

Plan 12-06 Warning 7 follow-up: the prior
``test_recompute_returns_503_when_compute_module_missing`` test
exercised an inline ``try/except ImportError`` placeholder which Plan
12-06 deleted in favor of a hard module-level import. The test was
removed in the same commit; cross-build deploy-state honesty is now an
import-time concern (FastAPI surfaces a startup error if the taskiq
module is missing).
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
    """D-14 — member role → 403; owner role → 202 + job_id.

    Plan 12-06 follow-up: the 503-fallback path is gone — the compute
    module is imported at module load. We patch ``recompute_paths_for_site.kiq``
    to a no-op async so the test doesn't need a live Redis broker.
    """
    _patch_clerk(monkeypatch, mock_clerk)
    team, site, _tok = await _seed_team_and_site(seed_session)

    # Stub out the taskiq enqueue so the test does not need Redis.
    from unittest.mock import AsyncMock

    from app.queue.tasks import path_compute as _pc

    monkeypatch.setattr(
        _pc.recompute_paths_for_site, "kiq", AsyncMock(return_value=None)
    )

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

        # Owner → 202 + job_id (the require_role gate passed; the kiq
        # enqueue is mocked so the test is hermetic).
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
        assert r_owner.status_code == 202, r_owner.text
        assert "job_id" in r_owner.json()


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
# Plan 12-06 Warning 7 follow-up
# ---------------------------------------------------------------------------
#
# The prior ``test_recompute_returns_503_when_compute_module_missing`` test
# was deleted in the same commit that removed the inline ``try/except
# ImportError → 503`` placeholder from ``app.routes.paths``. The hard
# module-level import means missing compute jobs fail loudly at FastAPI
# startup rather than at request time — which is the right posture.
