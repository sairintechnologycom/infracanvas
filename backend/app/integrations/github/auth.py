"""GitHub App authentication helpers (D-06).

Mints 5-minute App JWTs (RS256) and exchanges them for ~1hr installation
access tokens. Tokens are NEVER persisted — the worker calls these helpers
fresh per scan, embeds the result in a clone URL, and lets it expire.

References:
* https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-json-web-token-jwt-for-a-github-app
* https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation
* Plan 07.5-CONTEXT.md D-06 (mint-per-scan, no DB persistence)
"""
from __future__ import annotations

import time

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from app.settings import settings

GITHUB_API_BASE = "https://api.github.com"

# Constants — public for tests but treated as private to the module by callers.
_APP_JWT_TTL_S = 5 * 60
_IAT_SKEW_S = 60  # GitHub-doc-recommended clock-skew buffer
_DEFAULT_TIMEOUT_S = 10.0


def mint_app_jwt() -> str:
    """5-minute App JWT, RS256. iat -60s clock-skew buffer per GitHub docs.

    Reads settings.github_app_id (numeric, as a string) and
    settings.github_app_private_key (multi-line PEM). Both are populated
    from Fly secrets in dev/prod and from per-test fixtures in tests
    (see backend/tests/integrations/github/conftest.py).
    """
    loaded = load_pem_private_key(
        settings.github_app_private_key.encode(), password=None
    )
    if not isinstance(loaded, RSAPrivateKey):
        raise TypeError(
            "GITHUB_APP_PRIVATE_KEY must be an RSA key (RS256 signing required)"
        )
    private_key: RSAPrivateKey = loaded
    now = int(time.time())
    return jwt.encode(
        {
            "iat": now - _IAT_SKEW_S,
            "exp": now + _APP_JWT_TTL_S,
            "iss": settings.github_app_id,
        },
        private_key,
        algorithm="RS256",
    )


async def mint_installation_token(installation_id: int) -> str:
    """Exchange App JWT for an installation access token (~1hr TTL).

    The returned token is the only credential needed for clone URLs and
    /installation/* / /repos/* GitHub calls. NEVER log this value (T-07.5-03-01).
    """
    app_jwt = mint_app_jwt()
    async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S) as client:
        r = await client.post(
            f"{GITHUB_API_BASE}/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        r.raise_for_status()
        token: str = r.json()["token"]
        return token
