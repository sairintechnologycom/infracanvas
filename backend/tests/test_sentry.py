"""Sentry initialization contract tests (SENTRY-001..SENTRY-005).

Validates Phase 6 Plan 06-07's centralized :func:`app.obs.sentry.init_sentry`:

* SENTRY-001: no-op when ``settings.sentry_dsn`` is falsy.
* SENTRY-002: with DSN set, ``sentry_sdk.init`` is called with the four
  integrations (FastApi, Starlette, AsyncPG, Logging) and the documented
  sample rates / release / environment.
* SENTRY-003: idempotent — second call does NOT re-init (only updates
  the ``process_role`` tag).
* SENTRY-004: FastAPI lifespan startup invokes ``init_sentry(role="api")``.
* SENTRY-005: after the Clerk auth dep runs, the Sentry scope carries
  ``user_id``, ``clerk_org_id``, ``request_id`` tags (proven against the
  shared ``mock_clerk`` fixture wired by :mod:`tests.test_auth`).

No DB or Postgres testcontainer needed — these are pure SDK / ASGI
contract tests using FastAPI's TestClient + ``unittest.mock`` patches.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
import sentry_sdk
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jwt import PyJWKClient

from app.main import create_app
from app.obs import sentry as sentry_mod
from app.settings import settings


@pytest.fixture(autouse=True)
def _reset_sentry_init_flag() -> Any:
    """Reset the module-level _initialized flag around every test.

    init_sentry is idempotent in production — once per process. Tests
    need to rerun the init logic, so we manually toggle the guard flag.
    """
    sentry_mod._initialized = False
    yield
    sentry_mod._initialized = False


def test_init_sentry_noop_when_dsn_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """SENTRY-001: init_sentry with empty DSN is a no-op (sentry_sdk.init NOT called)."""
    monkeypatch.setattr(settings, "sentry_dsn", None)
    with patch("app.obs.sentry.sentry_sdk.init") as mock_init:
        sentry_mod.init_sentry(role="api")
        mock_init.assert_not_called()
    # _initialized still toggles True so a follow-up call also short-circuits.
    assert sentry_mod._initialized is True


def test_init_sentry_calls_sdk_init_with_integrations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SENTRY-002: with DSN set, sentry_sdk.init called with FastApi + Starlette +
    asyncpg + Logging integrations + traces 0.1 / profiles 0.1 / release / env."""
    monkeypatch.setattr(settings, "sentry_dsn", "https://test@sentry.io/1")
    monkeypatch.setattr(settings, "env", "test")
    monkeypatch.setattr(settings, "git_sha", "abc123")
    with (
        patch("app.obs.sentry.sentry_sdk.init") as mock_init,
        patch("app.obs.sentry.sentry_sdk.set_tag") as mock_tag,
    ):
        sentry_mod.init_sentry(role="api")
        assert mock_init.call_count == 1
        kwargs = mock_init.call_args.kwargs
        assert kwargs["traces_sample_rate"] == 0.1
        assert kwargs["profiles_sample_rate"] == 0.1
        assert kwargs["environment"] == "test"
        assert kwargs["release"] == "abc123"
        assert kwargs["send_default_pii"] is False
        integration_classnames = {type(i).__name__ for i in kwargs["integrations"]}
        assert "FastApiIntegration" in integration_classnames
        assert "StarletteIntegration" in integration_classnames
        assert "AsyncPGIntegration" in integration_classnames
        assert "LoggingIntegration" in integration_classnames
        mock_tag.assert_any_call("process_role", "api")


def test_init_sentry_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    """SENTRY-003: second call does not re-init (only updates role tag)."""
    monkeypatch.setattr(settings, "sentry_dsn", "https://test@sentry.io/1")
    with (
        patch("app.obs.sentry.sentry_sdk.init") as mock_init,
        patch("app.obs.sentry.sentry_sdk.set_tag") as mock_tag,
    ):
        sentry_mod.init_sentry(role="api")
        sentry_mod.init_sentry(role="worker")
        # init only called once total — second call is a no-op for SDK init.
        assert mock_init.call_count == 1
        # set_tag called twice (once per init call) — second updates process_role.
        tag_calls = [c.args for c in mock_tag.call_args_list]
        assert ("process_role", "api") in tag_calls
        assert ("process_role", "worker") in tag_calls


def test_fastapi_lifespan_initializes_sentry(monkeypatch: pytest.MonkeyPatch) -> None:
    """SENTRY-004: FastAPI lifespan startup calls init_sentry(role="api")."""
    monkeypatch.setattr(settings, "sentry_dsn", "https://test@sentry.io/1")
    with patch("app.obs.sentry.sentry_sdk.init") as mock_init:
        with TestClient(create_app()):
            pass
        assert mock_init.call_count == 1
        assert mock_init.call_args.kwargs["environment"] == settings.env


def test_sentry_tags_after_auth(
    mock_clerk: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SENTRY-005: after require_principal runs, Sentry scope has user_id,
    clerk_org_id, request_id tags (Plan 04 dep — verified end-to-end here).

    team_id tagging lives in resolve_team_from_clerk_org (Plan 04 follow-up
    dep) — out of scope for this assertion.
    """
    # Wire the mock_clerk JWKS into the auth module's module-level client.
    monkeypatch.setattr(
        "app.auth.clerk._jwks_client",
        PyJWKClient(mock_clerk.jwks_url, cache_keys=True, lifespan=3600),
    )
    monkeypatch.setattr(settings, "clerk_issuer", "https://clerk.infracanvas.app")
    monkeypatch.setattr(settings, "clerk_allowed_origins", ["https://infracanvas.app"])

    captured: dict[str, Any] = {"tags": {}, "user": None}

    def _set_tag(k: str, v: Any) -> None:
        captured["tags"][k] = v

    def _set_user(u: Any) -> None:
        captured["user"] = u

    monkeypatch.setattr(sentry_sdk, "set_tag", _set_tag)
    monkeypatch.setattr(sentry_sdk, "set_user", _set_user)

    from app.auth.clerk import require_principal
    from app.obs.middleware import RequestContextMiddleware

    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/p")
    async def p(_: Any = Depends(require_principal)) -> dict[str, bool]:
        return {"ok": True}

    with TestClient(app) as c:
        tok = mock_clerk.sign_jwt(sub="u1", org_id="org_s", role="admin")
        r = c.get(
            "/p",
            headers={
                "Authorization": f"Bearer {tok}",
                "X-Request-ID": "rid-sentry-test",
            },
        )
        assert r.status_code == 200, r.text

    assert captured["user"] == {"id": "u1"}
    assert captured["tags"].get("clerk_org_id") == "org_s"
    assert captured["tags"].get("request_id") == "rid-sentry-test"
