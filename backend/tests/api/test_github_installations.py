"""Integration tests for ``GET /v1/github/installations`` (Phase 7.5 D-10a).

Asserts:

* RLS isolation — team A's GET only returns team A's rows even when
  team B has rows seeded in the same database.
* Order — rows ordered by ``installed_at DESC`` (most recent install first).

Why these tests are pinned to ``api/`` (not ``integrations/github/``):
they exercise the FastAPI dep stack (``require_role`` +
``resolve_team_from_clerk_org`` + RLS-scoped session), which is HTTP-layer
behaviour. The pure-Python helpers in ``app.integrations.github`` are
covered by ``tests/integrations/github/`` separately.
"""
from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.rls


async def _seed_install(
    seed_session: Any,
    team_id: Any,
    *,
    install_id: int,
    login: str,
    installed_at_offset_seconds: int = 0,
) -> None:
    """Insert a github_installations row via BYPASSRLS seed_session.

    ``installed_at_offset_seconds`` is added to ``now()`` so the test can
    deterministically order rows for the ORDER BY assertion.
    """
    await seed_session.execute(
        text(
            """
            INSERT INTO github_installations
                (id, team_id, github_installation_id, github_account_login,
                 github_account_type, installed_by_user_id, installed_at)
            VALUES (gen_random_uuid(), :team_id, :iid, :login,
                    'Organization', 'u_install',
                    now() + (:off || ' seconds')::interval)
            """
        ),
        {
            "team_id": str(team_id),
            "iid": install_id,
            "login": login,
            "off": str(installed_at_offset_seconds),
        },
    )
    await seed_session.commit()


async def test_installations_rls_isolation(
    app_client: Any,
    team_a: Any,
    team_b: Any,
    auth_headers_factory: Any,
    seed_session: Any,
) -> None:
    """Seed installations for both teams; team A's GET returns only team A's row."""
    await _seed_install(
        seed_session, team_a.id, install_id=11111, login="org-a-login"
    )
    await _seed_install(
        seed_session, team_b.id, install_id=22222, login="org-b-login"
    )

    headers_a = auth_headers_factory(team_a.clerk_org_id, sub="u_a")
    r = app_client.get("/v1/github/installations", headers=headers_a)
    assert r.status_code == 200, r.text

    body = r.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["installation_id"] == 11111
    assert body[0]["github_account_login"] == "org-a-login"
    assert body[0]["github_account_type"] == "Organization"


async def test_installations_orders_recent_first(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
    seed_session: Any,
) -> None:
    """Two installs for team A, the second installed later → returned first."""
    # First install (older).
    await _seed_install(
        seed_session,
        team_a.id,
        install_id=33333,
        login="older-org",
        installed_at_offset_seconds=-3600,  # 1 hour ago
    )
    # Second install (newer).
    await _seed_install(
        seed_session,
        team_a.id,
        install_id=44444,
        login="newer-org",
        installed_at_offset_seconds=0,
    )

    headers = auth_headers_factory(team_a.clerk_org_id)
    r = app_client.get("/v1/github/installations", headers=headers)
    assert r.status_code == 200, r.text

    body = r.json()
    assert len(body) == 2
    # Newest (offset=0) comes first.
    assert body[0]["installation_id"] == 44444
    assert body[1]["installation_id"] == 33333


def test_installations_requires_auth(app_client: Any) -> None:
    """Missing Clerk JWT → 401 missing_bearer."""
    r = app_client.get("/v1/github/installations")
    assert r.status_code == 401
    assert r.json()["detail"] == "missing_bearer"


def test_installations_basic_member_allowed(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
) -> None:
    """basic_member role can read installations (D-10a — read scope)."""
    headers = auth_headers_factory(
        team_a.clerk_org_id, role="basic_member", sub="u_basic"
    )
    r = app_client.get("/v1/github/installations", headers=headers)
    # Empty list is fine — we just want a 200 (basic_member NOT 403).
    assert r.status_code == 200, r.text
    assert r.json() == []
