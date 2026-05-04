"""Shared fixtures for Phase 7.5 GitHub integration tests.

Exposes per-test infrastructure that is too expensive (RSA keypair) or
too cross-cutting (respx mock, fakeredis client, settings monkeypatch)
to repeat in every test module under ``tests/integrations/github/``.

Fixture inventory (downstream tests rely on these names — do not rename):

  - ``rsa_private_key``   — session-scoped ephemeral RSA-2048 PEM bytes
                            for App JWT signing tests (D-06).
  - ``app_id``            — function-scoped placeholder GitHub App id.
  - ``installation_id``   — function-scoped placeholder install id.
  - ``respx_github``      — function-scoped respx router rooted at
                            ``https://api.github.com`` so every GitHub
                            HTTP call in tests is hermetic.
  - ``fake_redis``        — function-scoped fakeredis async client (used
                            by repo-list cache integration tests in
                            Plan 03+).
  - ``gh_settings_patched``— monkeypatches ``app.settings.settings`` with
                            the ephemeral RSA key + placeholder ids so
                            ``mint_app_jwt`` (Plan 03) can sign without
                            a real Fly secret in CI.
"""
from __future__ import annotations

import fakeredis.aioredis
import pytest
import respx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


@pytest.fixture(scope="session")
def rsa_private_key() -> bytes:
    """Ephemeral RSA-2048 keypair for App JWT signing tests.

    Session-scoped because key generation is ~150 ms on a modern laptop
    and every Plan 03+ test that signs an App JWT needs it. Never written
    to disk; never used outside the test process.
    """
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


@pytest.fixture
def app_id() -> str:
    """Placeholder GitHub App id used by JWT iss claim tests."""
    return "12345"


@pytest.fixture
def installation_id() -> int:
    """Placeholder GitHub installation id used by callback / token tests."""
    return 99887766


@pytest.fixture
def respx_github():
    """respx mock router scoped to ``api.github.com`` only.

    ``assert_all_called=False`` lets individual tests register a route
    without requiring every test in the file to exercise it. Tests that
    DO want strict assertion can call ``respx_github.assert_all_called()``
    explicitly.
    """
    with respx.mock(
        base_url="https://api.github.com", assert_all_called=False
    ) as router:
        yield router


@pytest.fixture
async def fake_redis():
    """fakeredis async client; flushed + closed after each test.

    Used by repo-list cache integration tests in Plan 03+ to verify
    ``(installation_id, q)`` keys are cached for ~60 s without spinning
    up a real Redis container.
    """
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    try:
        yield client
    finally:
        await client.flushdb()
        await client.aclose()


@pytest.fixture
def gh_settings_patched(monkeypatch, rsa_private_key, app_id):
    """Patch ``settings.github_app_*`` with the ephemeral key for one test.

    Lets ``mint_app_jwt`` (Plan 03) sign with a real PEM without leaking
    the key beyond the test scope. The conftest at
    ``backend/tests/conftest.py`` only stubs the env vars to non-empty
    placeholder strings; tests that actually sign need this fixture.
    """
    from app.settings import settings

    monkeypatch.setattr(settings, "github_app_id", app_id)
    monkeypatch.setattr(settings, "github_app_private_key", rsa_private_key.decode())
    monkeypatch.setattr(settings, "github_app_slug", "infracanvas-test")
    return settings
