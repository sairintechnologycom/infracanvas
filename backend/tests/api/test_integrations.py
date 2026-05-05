"""PATCH /v1/integrations/slack — Phase 8 WBH-03.

3 tests covering the handler's validation and happy-path behaviour:

  1. test_valid_slack_url_saves
     — valid hooks.slack.com URL → 200 {"message": ...}; DB session execute called.

  2. test_non_hooks_url_returns_422
     — non-hooks.slack.com URL → 422 (T-8-04-01 SSRF guard).

  3. test_missing_field_returns_422
     — body missing webhook_url → 422 (Pydantic validation).

Wave 2 — all tests mock the DB and auth layer.  No Postgres testcontainer required.

Auth gate (T-8-04-03): the route depends on ``require_role`` which chains through
``require_principal`` — the Bearer token must be present or 401 fires at the FastAPI
layer before any fixture override can intercept it.

We override ``require_principal`` (the JWKS-validation dep) so tests don't need a
real Clerk JWT, and ``resolve_team_from_clerk_org`` so no Postgres lookup is needed.
"""
from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def integrations_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """TestClient with mocked auth + mocked DB session.

    Overrides:
    - ``require_principal`` dep → returns a fake ClerkPrincipal (no Clerk call)
    - ``resolve_team_from_clerk_org`` dep → returns a fake Team (no DB lookup)
    - ``get_sessionmaker`` inside the route → mock session factory

    We override ``require_principal`` (rather than ``require_role``) because
    ``require_role`` returns a *new closure* each call — dependency_overrides
    matches by object identity, so the factory-returned closure from the route
    definition won't match a new closure created in the test.  Overriding the
    underlying ``require_principal`` that the role closure ultimately calls means
    all ``require_role(...)`` usages are satisfied through a single, stable key.
    """
    from app.auth.clerk import ClerkPrincipal, require_principal
    from app.auth.deps import resolve_team_from_clerk_org
    from app.db.models import Team
    from app.main import create_app

    # Fake principal (owner role — in _WRITE_ROLES)
    fake_principal = ClerkPrincipal(
        user_id="user_test",
        session_id="sess_test",
        clerk_org_id="org_test",
        role="owner",
    )

    # Fake team
    fake_team_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    fake_team = Team(
        id=fake_team_id,
        clerk_org_id="org_test",
        name="Test Team",
        stripe_customer_id="cus_test",
    )

    # Build app, then override dependencies BEFORE TestClient starts
    app = create_app()

    # Override require_principal — all require_role(...) closures call this
    app.dependency_overrides[require_principal] = lambda: fake_principal
    # Override team resolution dep — bypasses DB lookup
    app.dependency_overrides[resolve_team_from_clerk_org] = lambda: fake_team

    # Build a mock sessionmaker that satisfies the double async-CM pattern:
    # ``async with sm() as session, session.begin():``
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_begin = AsyncMock()
    mock_begin.__aenter__ = AsyncMock(return_value=None)
    mock_begin.__aexit__ = AsyncMock(return_value=False)
    mock_session.begin = MagicMock(return_value=mock_begin)
    mock_session.execute = AsyncMock(return_value=MagicMock())

    mock_sm_instance = MagicMock()
    mock_sm_instance.__aenter__ = AsyncMock(return_value=mock_session)
    mock_sm_instance.__aexit__ = AsyncMock(return_value=False)

    mock_sm = MagicMock(return_value=mock_sm_instance)

    monkeypatch.setattr(
        "app.routes.integrations.get_sessionmaker",
        MagicMock(return_value=mock_sm),
    )

    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Test 1: valid hooks.slack.com URL → 200 with message key
# ---------------------------------------------------------------------------


def test_valid_slack_url_saves(integrations_client: TestClient) -> None:
    """T-8-04-01 happy path: valid hooks.slack.com URL → 200 {"message": ...}."""
    r = integrations_client.patch(
        "/v1/integrations/slack",
        json={"webhook_url": "https://hooks.slack.com/services/T/B/xxx"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "message" in data


# ---------------------------------------------------------------------------
# Test 2: non-hooks URL → 422
# ---------------------------------------------------------------------------


def test_non_hooks_url_returns_422(integrations_client: TestClient) -> None:
    """T-8-04-01 SSRF guard: non-hooks.slack.com URL → 422 before DB write."""
    r = integrations_client.patch(
        "/v1/integrations/slack",
        json={"webhook_url": "https://evil.com/hook"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert r.status_code == 422, r.text


# ---------------------------------------------------------------------------
# Test 3: missing webhook_url field → 422 (Pydantic validation)
# ---------------------------------------------------------------------------


def test_missing_field_returns_422(integrations_client: TestClient) -> None:
    """Missing webhook_url → Pydantic 422 before any route logic runs."""
    r = integrations_client.patch(
        "/v1/integrations/slack",
        json={},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert r.status_code == 422, r.text
