"""Tests for ``app.integrations.github.auth`` — App JWT + installation token mint.

Covers landmines from the planning research:

* RS256 algorithm (NOT HS256 — load_pem_private_key would refuse the wrong type
  but pyjwt would happily HMAC if we passed a string, so the algorithm header
  matters).
* iat -60s clock-skew buffer per GitHub docs (test 1).
* iss claim is the numeric App id from settings (test 2).
* X-GitHub-Api-Version + Accept headers on the token-mint POST (test 3).
* raise_for_status on 4xx / 5xx (test 4).
* pyjwt[crypto] extra is installed — without it pyjwt would raise
  NotImplementedError on RS256 (landmine 4 from the research doc).
"""
from __future__ import annotations

import time

import httpx
import jwt
import pytest
import respx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from app.integrations.github.auth import (
    GITHUB_API_BASE,
    mint_app_jwt,
    mint_installation_token,
)


def _public_pem(rsa_private_key: bytes) -> bytes:
    """Derive PEM-encoded public key from the test RSA private key."""
    private_key = load_pem_private_key(rsa_private_key, password=None)
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def test_mint_app_jwt(gh_settings_patched, rsa_private_key, app_id):
    """mint_app_jwt() returns an RS256-signed JWT with iat/exp/iss claims."""
    token = mint_app_jwt()
    assert isinstance(token, str)

    public_pem = _public_pem(rsa_private_key)
    decoded = jwt.decode(
        token, public_pem, algorithms=["RS256"], options={"verify_aud": False}
    )

    now = int(time.time())
    # iat should be ~60s in the past (clock-skew buffer per GitHub docs)
    assert now - 65 <= decoded["iat"] <= now - 55, decoded["iat"]
    # exp should be ~5 min in the future (300s, with a small tolerance)
    assert now + 295 <= decoded["exp"] <= now + 305, decoded["exp"]
    # iss is the numeric App id (string) from settings
    assert decoded["iss"] == app_id

    # Algorithm header must be RS256
    headers = jwt.get_unverified_header(token)
    assert headers["alg"] == "RS256"


def test_mint_app_jwt_uses_settings(gh_settings_patched, monkeypatch):
    """Patching settings.github_app_id changes the iss claim downstream."""
    from app.settings import settings

    monkeypatch.setattr(settings, "github_app_id", "777999")
    token = mint_app_jwt()
    decoded_iss = jwt.decode(
        token, options={"verify_signature": False, "verify_aud": False}
    )["iss"]
    assert decoded_iss == "777999"


@pytest.mark.asyncio
async def test_mint_installation_token_happy(
    gh_settings_patched, respx_github, installation_id
):
    """POST /app/installations/{id}/access_tokens returns the token string."""
    route = respx_github.post(
        f"/app/installations/{installation_id}/access_tokens"
    ).mock(
        return_value=httpx.Response(
            201,
            json={
                "token": "ghs_abcdef",
                "expires_at": "2026-05-03T15:00:00Z",
            },
        )
    )

    result = await mint_installation_token(installation_id)

    assert result == "ghs_abcdef"
    assert route.called
    request = route.calls.last.request
    auth_header = request.headers["authorization"]
    assert auth_header.startswith("Bearer "), auth_header
    assert request.headers["accept"] == "application/vnd.github+json"
    assert request.headers["x-github-api-version"] == "2022-11-28"


@pytest.mark.asyncio
async def test_mint_installation_token_403(
    gh_settings_patched, respx_github, installation_id
):
    """Non-2xx response raises HTTPStatusError (raise_for_status path)."""
    respx_github.post(
        f"/app/installations/{installation_id}/access_tokens"
    ).mock(return_value=httpx.Response(403, json={"message": "forbidden"}))

    with pytest.raises(httpx.HTTPStatusError):
        await mint_installation_token(installation_id)


def test_pyjwt_crypto_extra(rsa_private_key):
    """pyjwt[crypto] is importable and signs RS256 (landmine 4 guard).

    Without the [crypto] extra, ``jwt.encode(..., algorithm='RS256')`` raises
    ``NotImplementedError: Algorithm 'RS256' could not be found``. This test
    fails loud if the extra ever gets removed from pyproject.
    """
    private_key = load_pem_private_key(rsa_private_key, password=None)
    token = jwt.encode({"iss": "smoke"}, private_key, algorithm="RS256")
    assert isinstance(token, str) and token.count(".") == 2

    # And verify roundtrip with the public key
    public_pem = _public_pem(rsa_private_key)
    assert jwt.decode(token, public_pem, algorithms=["RS256"]) == {"iss": "smoke"}


# Plan 02 conftest base_url is https://api.github.com — keep the constant in sync.
def test_github_api_base_constant():
    """auth.GITHUB_API_BASE is the expected absolute URL — re-exported by client.py."""
    assert GITHUB_API_BASE == "https://api.github.com"
