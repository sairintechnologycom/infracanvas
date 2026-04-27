"""Clerk auth contract tests (AUTH-001..AUTH-006).

Exercises require_principal + require_role against the in-process Clerk
mock fixture (RSA keypair + JWKS served via pytest-httpserver). Each test
patches ``app.auth.clerk._jwks_client`` to a fresh PyJWKClient pointed at
the fixture's JWKS URL so the production module-level client (constructed
at import time against the env-stubbed URL) is bypassed.

No DB or Postgres testcontainer needed — these are pure HTTP/JWT contract
tests using FastAPI's TestClient.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jwt import PyJWKClient

from app.auth.clerk import ClerkPrincipal, require_principal, require_role
from app.obs.middleware import RequestContextMiddleware


def _jwks_client_for(jwks_url: str) -> PyJWKClient:
    """Build a PyJWKClient pointed at the mock_clerk JWKS URL."""
    return PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)


def _app_with_protected(role_gate: list[str] | None = None) -> FastAPI:
    """Build a tiny FastAPI app with one protected route gated by the
    given dependency (require_principal or require_role(*roles))."""
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)
    dep: Any = require_role(*role_gate) if role_gate else require_principal

    @app.get("/protected")
    async def protected(p: ClerkPrincipal = Depends(dep)) -> dict[str, str]:
        return {
            "user_id": p.user_id,
            "role": p.role,
            "clerk_org_id": p.clerk_org_id,
        }

    return app


@pytest.fixture
def patched_clerk(mock_clerk: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Wire mock_clerk's JWKS into the auth module + reset settings."""
    client = _jwks_client_for(mock_clerk.jwks_url)
    monkeypatch.setattr("app.auth.clerk._jwks_client", client)
    monkeypatch.setattr(
        "app.settings.settings.clerk_issuer", "https://clerk.infracanvas.app"
    )
    monkeypatch.setattr(
        "app.settings.settings.clerk_allowed_origins", ["https://infracanvas.app"]
    )
    return mock_clerk


def test_no_token_401(patched_clerk: Any) -> None:
    """AUTH-001: request with no Authorization header returns 401 missing_bearer."""
    with TestClient(_app_with_protected()) as c:
        r = c.get("/protected")
        assert r.status_code == 401


def test_expired_token_401(patched_clerk: Any) -> None:
    """AUTH-002: expired token returns 401 invalid_token."""
    token = patched_clerk.sign_jwt(sub="user_1", org_id="org_1", exp_delta=-60)
    with TestClient(_app_with_protected()) as c:
        r = c.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401


def test_tampered_signature_401(patched_clerk: Any) -> None:
    """AUTH-003: token with tampered payload is rejected with 401."""
    token = patched_clerk.sign_jwt(sub="user_1", org_id="org_1")
    # Flip one character in the signature segment to break verification.
    tampered = token[:-3] + ("A" if token[-3] != "A" else "B") + token[-2:]
    with TestClient(_app_with_protected()) as c:
        r = c.get("/protected", headers={"Authorization": f"Bearer {tampered}"})
        assert r.status_code == 401


def test_no_o_claim_403(
    patched_clerk: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AUTH-004: token with no `o` claim returns 403 no_active_organization."""
    # Mint a token without the `o` claim by signing directly.
    import time

    import jwt

    now = int(time.time())
    claims = {
        "azp": "https://infracanvas.app",
        "exp": now + 3600,
        "iat": now,
        "iss": "https://clerk.infracanvas.app",
        "sub": "user_1",
        "sid": "sess_user_1",
        "v": 2,
        # o intentionally omitted
    }
    token = jwt.encode(
        claims,
        patched_clerk.private_key_pem,
        algorithm="RS256",
        headers={"kid": patched_clerk.kid},
    )
    with TestClient(_app_with_protected()) as c:
        r = c.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403


def test_wrong_azp_401(patched_clerk: Any) -> None:
    """AUTH-005: token with azp not in allowlist returns 401 azp_mismatch."""
    token = patched_clerk.sign_jwt(
        sub="user_1", org_id="org_1", azp="https://evil.example"
    )
    with TestClient(_app_with_protected()) as c:
        r = c.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401


def test_require_role_admin_accepts(patched_clerk: Any) -> None:
    """AUTH-006a: role=admin passes require_role('admin', 'owner')."""
    token = patched_clerk.sign_jwt(sub="user_1", org_id="org_1", role="admin")
    with TestClient(_app_with_protected(role_gate=["admin", "owner"])) as c:
        r = c.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        body = r.json()
        assert body["user_id"] == "user_1"
        assert body["role"] == "admin"
        assert body["clerk_org_id"] == "org_1"


def test_require_role_basic_member_rejected(patched_clerk: Any) -> None:
    """AUTH-006b: role=basic_member rejected by require_role('admin','owner') with 403."""
    token = patched_clerk.sign_jwt(
        sub="user_1", org_id="org_1", role="basic_member"
    )
    with TestClient(_app_with_protected(role_gate=["admin", "owner"])) as c:
        r = c.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403
