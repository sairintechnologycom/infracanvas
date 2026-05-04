"""Tests for ``app.integrations.github.client`` — httpx wrapper + Redis cache.

Eight tests cover:

  1. list_installation_repos with no q — returns all repos, caches under '*' key
  2. list_installation_repos with q — substring filter + 30-row cap
  3. list_installation_repos cache hit — pre-populated key short-circuits the
     GitHub call (respx asserts ZERO calls)
  4. list_branches — returns [{name, commit_sha}] from GitHub branches list
  5. get_head_sha happy — returns sha from /git/ref/heads/{branch}
  6. get_head_sha 404 — raises HTTPStatusError (caller route translates)
  7. get_installation_metadata — uses App JWT (NOT installation token)
  8. get_head_sha branch with slash (feature/foo) — URL-encoded as %2F
"""
from __future__ import annotations

import json

import httpx
import pytest

from app.integrations.github.client import (
    get_head_sha,
    get_installation_metadata,
    list_branches,
    list_installation_repos,
)


def _mock_install_token(respx_github, installation_id: int) -> None:
    """Register the App-JWT → installation-token POST that every API path triggers."""
    respx_github.post(
        f"/app/installations/{installation_id}/access_tokens"
    ).mock(return_value=httpx.Response(201, json={"token": "ghs_test"}))


def _make_repos(count: int) -> list[dict]:
    return [
        {
            "id": i,
            "full_name": f"org/repo-{i:03d}",
            "default_branch": "main",
            "private": (i % 2 == 0),
        }
        for i in range(count)
    ]


@pytest.mark.asyncio
async def test_list_installation_repos_no_q(
    gh_settings_patched, respx_github, fake_redis, installation_id
):
    """No q → returns all (≤30) repos and caches under gh:repos:{id}:*."""
    _mock_install_token(respx_github, installation_id)
    repos = _make_repos(30)
    respx_github.get("/installation/repositories").mock(
        return_value=httpx.Response(200, json={"repositories": repos})
    )

    result = await list_installation_repos(
        installation_id, redis_client=fake_redis
    )

    assert len(result) == 30
    for entry in result:
        assert set(entry.keys()) == {"full_name", "default_branch", "private"}
    cached = await fake_redis.get(f"gh:repos:{installation_id}:*")
    assert cached is not None
    assert json.loads(cached) == result
    # 60s TTL
    ttl = await fake_redis.ttl(f"gh:repos:{installation_id}:*")
    assert 1 <= ttl <= 60


@pytest.mark.asyncio
async def test_list_installation_repos_q_filter(
    gh_settings_patched, respx_github, fake_redis, installation_id
):
    """With q='001' → substring filter (case-insensitive); cap at 30 after filter."""
    _mock_install_token(respx_github, installation_id)
    # 100 repos; q='001' matches 'org/repo-001' only; must produce a single result.
    repos = _make_repos(100)
    respx_github.get("/installation/repositories").mock(
        return_value=httpx.Response(200, json={"repositories": repos})
    )

    result = await list_installation_repos(
        installation_id, q="001", redis_client=fake_redis
    )

    assert len(result) == 1
    assert result[0]["full_name"] == "org/repo-001"
    cached = await fake_redis.get(f"gh:repos:{installation_id}:001")
    assert cached is not None


@pytest.mark.asyncio
async def test_list_installation_repos_cache_hit(
    gh_settings_patched, respx_github, fake_redis, installation_id
):
    """Pre-populated cache → returns cached value, makes ZERO GitHub calls."""
    pre = [
        {"full_name": "org/cached", "default_branch": "main", "private": False}
    ]
    await fake_redis.setex(
        f"gh:repos:{installation_id}:*", 60, json.dumps(pre)
    )

    # Register routes that should NEVER be called (would 500 if hit anyway).
    install_route = respx_github.post(
        f"/app/installations/{installation_id}/access_tokens"
    ).mock(return_value=httpx.Response(500))
    repos_route = respx_github.get("/installation/repositories").mock(
        return_value=httpx.Response(500)
    )

    result = await list_installation_repos(
        installation_id, redis_client=fake_redis
    )

    assert result == pre
    assert install_route.call_count == 0
    assert repos_route.call_count == 0


@pytest.mark.asyncio
async def test_list_branches(
    gh_settings_patched, respx_github, installation_id
):
    """Returns [{name, commit_sha}] for all branches from /repos/{r}/branches."""
    _mock_install_token(respx_github, installation_id)
    branches = [
        {"name": f"branch-{i}", "commit": {"sha": f"sha{i}" * 5}}
        for i in range(5)
    ]
    respx_github.get("/repos/org/repo/branches").mock(
        return_value=httpx.Response(200, json=branches)
    )

    result = await list_branches(installation_id, "org/repo")

    assert len(result) == 5
    assert result[0] == {"name": "branch-0", "commit_sha": "sha0" * 5}
    assert all(set(b.keys()) == {"name", "commit_sha"} for b in result)


@pytest.mark.asyncio
async def test_get_head_sha(
    gh_settings_patched, respx_github, installation_id
):
    """Returns the sha string from /repos/{r}/git/ref/heads/{branch}."""
    _mock_install_token(respx_github, installation_id)
    respx_github.get("/repos/org/repo/git/ref/heads/main").mock(
        return_value=httpx.Response(
            200,
            json={"ref": "refs/heads/main", "object": {"sha": "abc123def"}},
        )
    )

    sha = await get_head_sha(installation_id, "org/repo", "main")

    assert sha == "abc123def"


@pytest.mark.asyncio
async def test_get_head_sha_404(
    gh_settings_patched, respx_github, installation_id
):
    """404 from GitHub raises HTTPStatusError (route layer translates to HTTPException)."""
    _mock_install_token(respx_github, installation_id)
    respx_github.get("/repos/org/repo/git/ref/heads/missing").mock(
        return_value=httpx.Response(404, json={"message": "Not Found"})
    )

    with pytest.raises(httpx.HTTPStatusError):
        await get_head_sha(installation_id, "org/repo", "missing")


@pytest.mark.asyncio
async def test_get_installation_metadata(
    gh_settings_patched, respx_github, installation_id
):
    """Uses App JWT (not installation token) to fetch /app/installations/{id}."""
    # We REGISTER the install-token POST to detect erroneous use; it must NOT
    # be called.
    install_token_route = respx_github.post(
        f"/app/installations/{installation_id}/access_tokens"
    ).mock(return_value=httpx.Response(500))

    metadata_route = respx_github.get(
        f"/app/installations/{installation_id}"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "id": installation_id,
                "account": {"login": "foo", "type": "Organization"},
            },
        )
    )

    result = await get_installation_metadata(installation_id)

    assert result["account"] == {"login": "foo", "type": "Organization"}
    assert metadata_route.called
    assert install_token_route.call_count == 0
    request = metadata_route.calls.last.request
    auth_header = request.headers["authorization"]
    # Bearer is the App JWT; we asserted call_count==0 on the install-token
    # POST, so this Bearer must be the App JWT.
    assert auth_header.startswith("Bearer ")


@pytest.mark.asyncio
async def test_branch_with_slash(
    gh_settings_patched, respx_github, installation_id
):
    """Branch 'feature/foo' is URL-encoded so the slash isn't a path segment."""
    _mock_install_token(respx_github, installation_id)
    # Register the ENCODED form: 'feature%2Ffoo'. respx matches the raw URL.
    respx_github.get(
        "/repos/org/repo/git/ref/heads/feature%2Ffoo"
    ).mock(
        return_value=httpx.Response(
            200, json={"object": {"sha": "encoded-ok"}}
        )
    )

    sha = await get_head_sha(installation_id, "org/repo", "feature/foo")

    assert sha == "encoded-ok"
