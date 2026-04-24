"""Contract tests for /healthz + /readyz (API-001..API-003).

These tests run against the pure Starlette TestClient (no DB / Redis / R2),
so they are fast (<1s) and have no Testcontainers fixtures.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_healthz_returns_ok() -> None:
    """API-001: GET /healthz returns 200 with status=ok and git_sha."""
    with TestClient(create_app()) as client:
        r = client.get("/healthz")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "git_sha" in body


def test_healthz_echoes_request_id() -> None:
    """API-002: /healthz echoes client-supplied X-Request-ID header."""
    with TestClient(create_app()) as client:
        rid = "req-test-12345"
        r = client.get("/healthz", headers={"X-Request-ID": rid})
        assert r.status_code == 200
        assert r.headers.get("x-request-id") == rid


def test_healthz_generates_request_id_when_missing() -> None:
    """API-003: middleware generates a UUIDv7-shaped request id when client omits it."""
    with TestClient(create_app()) as client:
        r = client.get("/healthz")
        rid = r.headers.get("x-request-id")
        assert rid is not None
        # UUIDv7 canonical length 36 with dashes.
        assert len(rid) == 36 and rid.count("-") == 4


def test_readyz_returns_ready() -> None:
    """API-004: GET /readyz returns 200 with status=ready after lifespan startup."""
    with TestClient(create_app()) as client:
        r = client.get("/readyz")
        assert r.status_code == 200
        assert r.json() == {"status": "ready"}
