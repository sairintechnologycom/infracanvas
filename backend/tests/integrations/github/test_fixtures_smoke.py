"""Smoke tests for the Phase 7.5 GitHub fixtures (Plan 02 acceptance).

Verifies each shared fixture in ``conftest.py`` constructs cleanly and
returns the expected shape. These are NOT replacement for downstream
behavior tests — they exist solely so Plan 02 can prove the fixture
infrastructure is sound before Plan 03+ relies on it.
"""
from __future__ import annotations

import pytest


def test_rsa_private_key_is_pkcs8_pem(rsa_private_key: bytes) -> None:
    """Ephemeral key is bytes and looks like a PKCS8 PEM."""
    assert isinstance(rsa_private_key, bytes)
    assert b"-----BEGIN PRIVATE KEY-----" in rsa_private_key
    assert b"-----END PRIVATE KEY-----" in rsa_private_key


def test_app_id_and_installation_id(app_id: str, installation_id: int) -> None:
    assert app_id == "12345"
    assert installation_id == 99887766


def test_respx_github_router_intercepts(respx_github) -> None:
    """Router is reachable and registers routes on api.github.com."""
    import httpx

    respx_github.get("/zen").respond(200, text="ok")
    with httpx.Client(base_url="https://api.github.com") as client:
        resp = client.get("/zen")
    assert resp.status_code == 200
    assert resp.text == "ok"


@pytest.mark.asyncio
async def test_fake_redis_set_get_roundtrip(fake_redis) -> None:
    """fakeredis async client supports basic SET/GET roundtrip."""
    await fake_redis.set("k", "v")
    assert await fake_redis.get("k") == "v"


def test_gh_settings_patched_overrides_singleton(gh_settings_patched) -> None:
    """gh_settings_patched monkeypatches the live Settings singleton."""
    from app.settings import settings

    assert settings.github_app_id == "12345"
    assert settings.github_app_private_key.startswith("-----BEGIN PRIVATE KEY-----")
    assert settings.github_app_slug == "infracanvas-test"
    # Same singleton object the test received.
    assert gh_settings_patched is settings
