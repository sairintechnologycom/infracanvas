"""Integration tests for ``GET /v1/github/repos`` (Phase 7.5 D-10b).

Asserts:

* q-filter — substring match against ``full_name`` (server-side, since
  the install token can't hit /search/repositories).
* Cache hit — pre-populating fakeredis short-circuits the GitHub call.
* Rate-limit translation — GitHub 403/429 → 503 + Retry-After header.
* Installation membership — installation_id not owned by the team → 404
  (no GitHub call attempted).

The route uses :func:`app.integrations.github.client.list_installation_repos`
which accepts ``redis_client=`` for test injection. We monkeypatch
``_get_redis`` so the route also gets the fakeredis instance even though
the route signature doesn't pass it through explicitly.
"""
from __future__ import annotations

import json
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


@pytest.fixture
def patch_redis_singleton(monkeypatch: pytest.MonkeyPatch, fake_redis: Any) -> Any:
    """Replace ``_get_redis`` so the route's cache lookup hits fakeredis.

    The plan's helper has a ``redis_client=`` kwarg for tests, but the
    route doesn't pass it through (the route just calls
    ``list_installation_repos(installation_id, q)``). Patching the
    module-level singleton is the cleanest way to intercept.
    """
    from app.integrations.github import client as gh_client

    gh_client._get_redis.cache_clear()
    monkeypatch.setattr(gh_client, "_get_redis", lambda: fake_redis)
    return fake_redis


async def test_repos_q_filter(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
    seed_session: Any,
    respx_github: Any,
    gh_settings_patched: Any,
    installation_id: int,
    patch_redis_singleton: Any,
) -> None:
    """q='prod' returns only repos whose full_name contains 'prod'."""
    await _seed_install(seed_session, team_a.id, install_id=installation_id)

    # Token mint POST.
    respx_github.post(
        f"/app/installations/{installation_id}/access_tokens"
    ).mock(return_value=httpx.Response(200, json={"token": "ghs_test_repos"}))
    # Repos GET — three repos, only one matches 'prod'.
    respx_github.get("/installation/repositories").mock(
        return_value=httpx.Response(
            200,
            json={
                "repositories": [
                    {
                        "full_name": "acme/staging-svc",
                        "default_branch": "main",
                        "private": False,
                    },
                    {
                        "full_name": "acme/prod-api",
                        "default_branch": "main",
                        "private": True,
                    },
                    {
                        "full_name": "acme/dev-tools",
                        "default_branch": "main",
                        "private": False,
                    },
                ]
            },
        )
    )

    headers = auth_headers_factory(team_a.clerk_org_id)
    r = app_client.get(
        f"/v1/github/repos?installation_id={installation_id}&q=prod",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["full_name"] == "acme/prod-api"
    assert body[0]["private"] is True


async def test_repos_cache_hit(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
    seed_session: Any,
    respx_github: Any,
    gh_settings_patched: Any,
    fake_redis: Any,
    installation_id: int,
    patch_redis_singleton: Any,
) -> None:
    """Pre-populated cache → ZERO GitHub HTTP calls."""
    await _seed_install(seed_session, team_a.id, install_id=installation_id)

    cached_payload = [
        {
            "full_name": "acme/cached-repo",
            "default_branch": "main",
            "private": False,
        }
    ]
    await fake_redis.set(
        f"gh:repos:{installation_id}:*", json.dumps(cached_payload)
    )

    # Register routes BUT they should not be hit. assert_all_called=False
    # on respx_github already, so absence of calls is fine.
    token_route = respx_github.post(
        f"/app/installations/{installation_id}/access_tokens"
    ).mock(return_value=httpx.Response(200, json={"token": "ghs_test_unused"}))
    repos_route = respx_github.get("/installation/repositories").mock(
        return_value=httpx.Response(200, json={"repositories": []})
    )

    headers = auth_headers_factory(team_a.clerk_org_id)
    r = app_client.get(
        f"/v1/github/repos?installation_id={installation_id}", headers=headers
    )
    assert r.status_code == 200, r.text
    assert r.json() == cached_payload
    # ZERO GitHub calls when cache hot.
    assert not token_route.called
    assert not repos_route.called


async def test_repos_ratelimit_503(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
    seed_session: Any,
    respx_github: Any,
    gh_settings_patched: Any,
    installation_id: int,
    patch_redis_singleton: Any,
) -> None:
    """GitHub 403 with X-RateLimit-Remaining=0 → endpoint 503 + Retry-After."""
    await _seed_install(seed_session, team_a.id, install_id=installation_id)

    respx_github.post(
        f"/app/installations/{installation_id}/access_tokens"
    ).mock(return_value=httpx.Response(200, json={"token": "ghs_test_rl"}))
    respx_github.get("/installation/repositories").mock(
        return_value=httpx.Response(
            403,
            headers={
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": "1700000000",
            },
            json={"message": "API rate limit exceeded"},
        )
    )

    headers = auth_headers_factory(team_a.clerk_org_id)
    r = app_client.get(
        f"/v1/github/repos?installation_id={installation_id}", headers=headers
    )
    assert r.status_code == 503, r.text
    assert r.json()["detail"] == "github_rate_limited"
    assert r.headers.get("retry-after") == "60"


def test_repos_requires_auth(app_client: Any) -> None:
    """Missing Clerk JWT → 401."""
    r = app_client.get("/v1/github/repos?installation_id=99887766")
    assert r.status_code == 401


async def test_repos_unknown_installation_404(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
    patch_redis_singleton: Any,
) -> None:
    """installation_id not in the team's github_installations → 404."""
    headers = auth_headers_factory(team_a.clerk_org_id)
    r = app_client.get(
        "/v1/github/repos?installation_id=99999999", headers=headers
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "installation_not_found"
