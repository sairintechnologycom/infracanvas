"""Thin httpx wrapper for the 4-5 GitHub API calls Phase 7.5 makes.

We intentionally do NOT use a typed SDK (PyGithub/githubkit). Five endpoints
suffice: list installation repos, list branches, get HEAD sha, get installation
metadata, plus the App-JWT installation-token-mint (in auth.py).

Repo list cached 60s in Upstash Redis at key
``gh:repos:{installation_id}:{q or '*'}`` (D-10b). The 60s TTL is the
lossy-cache sweet spot per CONTEXT — the typeahead can chew rate limit fast,
and 60s of staleness is acceptable for "did I push a new repo just now?".

Tokens flow ONLY through the Authorization header and the return value of
:func:`mint_installation_token`. They are NEVER passed into structlog binds
(threat T-07.5-03-01).
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any
from urllib.parse import quote

import httpx
import structlog
from redis.asyncio import Redis

from app.integrations.github.auth import (
    GITHUB_API_BASE,
    mint_app_jwt,
    mint_installation_token,
)
from app.settings import settings

_log = structlog.get_logger("app.integrations.github")

_REPO_LIST_TTL_S = 60
_DEFAULT_TIMEOUT_S = 10.0
_INSTALL_REPOS_PER_PAGE = 100
_RESPONSE_REPO_CAP = 30  # CONTEXT D-05: first ~30 repos by pushed_at desc


@lru_cache(maxsize=1)
def _get_redis() -> Redis:
    """Lazy singleton async Redis client. Reused across calls.

    decode_responses=True so that ``get`` returns ``str`` not ``bytes`` —
    matches the encoding fakeredis is configured with in the test fixture.
    """
    client: Redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return client


def _gh_headers(token: str) -> dict[str, str]:
    """Standard GitHub REST headers — bearer token + content negotiation."""
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def list_installation_repos(
    installation_id: int,
    q: str | None = None,
    *,
    redis_client: Redis | None = None,
) -> list[dict[str, Any]]:
    """List repos visible to install. 60s cache. Substring filter on q.

    The cache key includes ``q`` so different searches don't collide. Cache
    miss flow:

      1. Mint installation token (auth.py).
      2. GET /installation/repositories?per_page=100&sort=pushed&direction=desc.
      3. Apply server-side substring filter on full_name (lower-cased).
      4. Cap at first 30 entries.
      5. Setex with 60s TTL.

    Pass ``redis_client=fake_redis`` from tests to avoid the singleton
    lru_cache trapping the real-Redis URL between tests.
    """
    client = redis_client or _get_redis()
    cache_key = f"gh:repos:{installation_id}:{q or '*'}"
    cached = await client.get(cache_key)
    if cached is not None:
        return json.loads(cached)  # type: ignore[no-any-return]

    token = await mint_installation_token(installation_id)
    async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S) as http_client:
        r = await http_client.get(
            f"{GITHUB_API_BASE}/installation/repositories",
            headers=_gh_headers(token),
            params={
                "per_page": _INSTALL_REPOS_PER_PAGE,
                "sort": "pushed",
                "direction": "desc",
            },
        )
        r.raise_for_status()
        repos = r.json()["repositories"]

    if q:
        ql = q.lower()
        repos = [repo for repo in repos if ql in repo["full_name"].lower()]

    out: list[dict[str, Any]] = [
        {
            "full_name": repo["full_name"],
            "default_branch": repo["default_branch"],
            "private": repo["private"],
        }
        for repo in repos[:_RESPONSE_REPO_CAP]
    ]
    await client.setex(cache_key, _REPO_LIST_TTL_S, json.dumps(out))
    return out


async def list_branches(
    installation_id: int, repo: str
) -> list[dict[str, str]]:
    """List branches for repo='owner/name'. No cache (D-10c).

    Branches change frequently and are typically <30 per repo, so a 250ms
    fetch on repo-select is cheap enough to skip caching.
    """
    owner, name = repo.split("/", 1)
    token = await mint_installation_token(installation_id)
    async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S) as client:
        r = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{name}/branches",
            headers=_gh_headers(token),
            params={"per_page": 100},
        )
        r.raise_for_status()
        branches = r.json()
    return [
        {"name": b["name"], "commit_sha": b["commit"]["sha"]}
        for b in branches
    ]


async def get_head_sha(
    installation_id: int, repo: str, branch: str
) -> str:
    """Resolve current HEAD sha for repo@branch (one GitHub API call).

    Branch is URL-encoded with ``safe=""`` so 'feature/foo' becomes
    'feature%2Ffoo' — without this, GitHub treats the slash as a path
    segment and returns the wrong ref (or 404). Mitigates T-07.5-03-05.
    """
    owner, name = repo.split("/", 1)
    token = await mint_installation_token(installation_id)
    encoded_branch = quote(branch, safe="")
    async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S) as client:
        r = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{name}/git/ref/heads/{encoded_branch}",
            headers=_gh_headers(token),
        )
        r.raise_for_status()
        sha: str = r.json()["object"]["sha"]
        return sha


async def get_installation_metadata(installation_id: int) -> dict[str, Any]:
    """Fetch installation account metadata. Uses App JWT (NOT installation token).

    Per GitHub Apps API, /app/installations/{id} requires App-level auth —
    the installation hasn't necessarily been provisioned with the
    permissions needed to introspect itself.
    """
    app_jwt = mint_app_jwt()
    async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S) as client:
        r = await client.get(
            f"{GITHUB_API_BASE}/app/installations/{installation_id}",
            headers=_gh_headers(app_jwt),
        )
        r.raise_for_status()
        payload: dict[str, Any] = r.json()
        return payload
