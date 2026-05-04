"""Fixtures local to ``tests/api/`` — GitHub-flavoured analogues of the
fixtures in ``tests/integrations/github/conftest.py``.

We keep these here (rather than promoting them to ``tests/conftest.py``)
because they're only relevant to the GitHub-routes API tests; promoting
would add unnecessary import cost to every other test module.

Fixtures exposed (mirror the names + semantics from
``tests/integrations/github/conftest.py`` so the same patterns Plan 03
established work here):

  - ``app_id``           — placeholder GitHub App id for JWT iss claim.
  - ``installation_id``  — placeholder install id (matches Plan 02 default).
  - ``respx_github``     — respx router scoped to ``api.github.com``.
  - ``fake_redis``       — fakeredis async client for cache tests.
  - ``gh_settings_patched`` — monkeypatches settings.github_app_* with the
                              ephemeral RSA key from ``mock_clerk``-style
                              keypair generation (re-uses the parent
                              ``mock_clerk`` fixture's RSA gen approach but
                              isolated so tests don't need both).
"""
from __future__ import annotations

import fakeredis.aioredis
import pytest
import respx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


@pytest.fixture(scope="session")
def rsa_private_key() -> bytes:
    """Ephemeral RSA-2048 PEM bytes for App JWT signing."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


@pytest.fixture
def app_id() -> str:
    return "12345"


@pytest.fixture
def installation_id() -> int:
    return 99887766


@pytest.fixture
def respx_github():
    with respx.mock(
        base_url="https://api.github.com", assert_all_called=False
    ) as router:
        yield router


@pytest.fixture
async def fake_redis():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    try:
        yield client
    finally:
        await client.flushdb()
        await client.aclose()


@pytest.fixture
def gh_settings_patched(monkeypatch, rsa_private_key, app_id):
    from app.settings import settings

    monkeypatch.setattr(settings, "github_app_id", app_id)
    monkeypatch.setattr(settings, "github_app_private_key", rsa_private_key.decode())
    monkeypatch.setattr(settings, "github_app_slug", "infracanvas-test")
    return settings


# ---------------------------------------------------------------------------
# App client + Clerk + Postgres scaffolding (mirrors test_scans.py).
# ---------------------------------------------------------------------------


@pytest.fixture
def patch_clerk_jwks(monkeypatch: pytest.MonkeyPatch, mock_clerk):
    """Point app.auth.clerk._jwks_client at the fixture-local JWKS endpoint
    AND align settings.clerk_issuer with mock_clerk's signed iss claim.

    Mirrors test_scans.py::patch_clerk_jwks.
    """
    import app.auth.clerk as clerk_mod
    from jwt import PyJWKClient

    monkeypatch.setattr(clerk_mod, "_jwks_client", PyJWKClient(mock_clerk.jwks_url))
    from app.settings import settings

    monkeypatch.setattr(settings, "clerk_issuer", "https://clerk.infracanvas.app")
    monkeypatch.setattr(
        settings, "clerk_allowed_origins", ["https://infracanvas.app"]
    )


@pytest.fixture
def app_client(
    patch_clerk_jwks: None, pg_container, monkeypatch: pytest.MonkeyPatch
):
    """TestClient against a fresh app instance (NullPool engine).

    Mirrors test_scans.py::app_client — see its docstring for the
    cross-event-loop rationale.
    """
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

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

    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers_factory(mock_clerk):
    """Mints a Bearer header for a given clerk_org_id."""

    def _make(org_id: str, role: str = "admin", sub: str = "u_gh") -> dict[str, str]:
        token = mock_clerk.sign_jwt(sub=sub, org_id=org_id, role=role)
        return {"Authorization": f"Bearer {token}"}

    return _make


@pytest.fixture
async def team_a(seed_session):
    """Seed Team A via BYPASSRLS seed_session (analogue of test_scans.py)."""
    import secrets

    from app.db.models import Team
    from app.util.ids import new_uuid7

    tid = new_uuid7()
    t = Team(
        id=tid,
        clerk_org_id=f"org_gh_a_{secrets.token_hex(6)}",
        name="GH Team A",
        stripe_customer_id="cus_gh_a",
    )
    async with seed_session.begin():
        seed_session.add(t)
    return t


@pytest.fixture
async def team_b(seed_session):
    import secrets

    from app.db.models import Team
    from app.util.ids import new_uuid7

    tid = new_uuid7()
    t = Team(
        id=tid,
        clerk_org_id=f"org_gh_b_{secrets.token_hex(6)}",
        name="GH Team B",
        stripe_customer_id="cus_gh_b",
    )
    async with seed_session.begin():
        seed_session.add(t)
    return t
