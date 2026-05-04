"""Integration tests for ``GET /v1/github/branches`` (Phase 7.5 D-10c).

Asserts:

* Happy path — three branches → returned shape ``[{name, commit_sha}, ...]``.
* Owner/name split — ``repo='org/foo-bar'`` is parsed correctly into the
  GitHub URL ``/repos/org/foo-bar/branches``.
* 404 propagation — repo or branch not found → endpoint 404.
* Pattern guard — invalid ``repo`` (no slash, traversal) → 422 (FastAPI
  pattern validation rejects before the route body executes).
* Installation membership — installation_id not owned → 404.

The route does NOT cache (D-10c — branches change frequently and are
typically <30 per repo).
"""
from __future__ import annotations

from typing import Any

import httpx
import pytest
from sqlalchemy import text

pytestmark = pytest.mark.rls


async def _seed_install(
    seed_session: Any, team_id: Any, *, install_id: int
) -> None:
    await seed_session.execute(
        text(
            """
            INSERT INTO github_installations
                (id, team_id, github_installation_id, github_account_login,
                 github_account_type, installed_by_user_id)
            VALUES (gen_random_uuid(), :team_id, :iid, 'acme',
                    'Organization', 'u_install')
            """
        ),
        {"team_id": str(team_id), "iid": install_id},
    )
    await seed_session.commit()


async def test_branches_happy(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
    seed_session: Any,
    respx_github: Any,
    gh_settings_patched: Any,
    installation_id: int,
) -> None:
    """Three branches → response shape [{name, commit_sha}, ...]."""
    await _seed_install(seed_session, team_a.id, install_id=installation_id)

    respx_github.post(
        f"/app/installations/{installation_id}/access_tokens"
    ).mock(return_value=httpx.Response(200, json={"token": "ghs_test_branches"}))
    respx_github.get("/repos/acme/widgets/branches").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"name": "main", "commit": {"sha": "a" * 40}},
                {"name": "develop", "commit": {"sha": "b" * 40}},
                {"name": "release/1.0", "commit": {"sha": "c" * 40}},
            ],
        )
    )

    headers = auth_headers_factory(team_a.clerk_org_id)
    r = app_client.get(
        f"/v1/github/branches?installation_id={installation_id}&repo=acme/widgets",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) == 3
    assert body[0] == {"name": "main", "commit_sha": "a" * 40}
    assert body[2] == {"name": "release/1.0", "commit_sha": "c" * 40}


async def test_branches_owner_name_split(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
    seed_session: Any,
    respx_github: Any,
    gh_settings_patched: Any,
    installation_id: int,
) -> None:
    """repo='org/foo-bar' → GitHub URL /repos/org/foo-bar/branches."""
    await _seed_install(seed_session, team_a.id, install_id=installation_id)

    respx_github.post(
        f"/app/installations/{installation_id}/access_tokens"
    ).mock(return_value=httpx.Response(200, json={"token": "ghs_test_split"}))
    branches_route = respx_github.get(
        "/repos/org/foo-bar/branches"
    ).mock(
        return_value=httpx.Response(
            200, json=[{"name": "main", "commit": {"sha": "d" * 40}}]
        )
    )

    headers = auth_headers_factory(team_a.clerk_org_id)
    r = app_client.get(
        f"/v1/github/branches?installation_id={installation_id}&repo=org/foo-bar",
        headers=headers,
    )
    assert r.status_code == 200
    assert branches_route.called


async def test_branches_404(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
    seed_session: Any,
    respx_github: Any,
    gh_settings_patched: Any,
    installation_id: int,
) -> None:
    """GitHub 404 → endpoint 404 repo_or_branch_not_found."""
    await _seed_install(seed_session, team_a.id, install_id=installation_id)

    respx_github.post(
        f"/app/installations/{installation_id}/access_tokens"
    ).mock(return_value=httpx.Response(200, json={"token": "ghs_test_404"}))
    respx_github.get("/repos/acme/missing/branches").mock(
        return_value=httpx.Response(404, json={"message": "Not Found"})
    )

    headers = auth_headers_factory(team_a.clerk_org_id)
    r = app_client.get(
        f"/v1/github/branches?installation_id={installation_id}&repo=acme/missing",
        headers=headers,
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "repo_or_branch_not_found"


def test_branches_pattern_guard(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
) -> None:
    """repo='../../etc/passwd' fails the regex pattern guard → 422."""
    headers = auth_headers_factory(team_a.clerk_org_id)
    r = app_client.get(
        "/v1/github/branches?installation_id=99887766&repo=../../etc/passwd",
        headers=headers,
    )
    # FastAPI's Pydantic Query pattern validation returns 422.
    assert r.status_code == 422


async def test_branches_unknown_installation_404(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
) -> None:
    """installation_id not in the team's installations → 404."""
    headers = auth_headers_factory(team_a.clerk_org_id)
    r = app_client.get(
        "/v1/github/branches?installation_id=99999999&repo=acme/widgets",
        headers=headers,
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "installation_not_found"
