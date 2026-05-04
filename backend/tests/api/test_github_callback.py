"""Integration tests for ``GET /v1/github/install-callback`` (Phase 7.5 D-10d).

Asserts:

* Verb is GET (per RESEARCH § Open Q5 — GitHub redirects with GET, not
  POST; CONTEXT D-10d's ``POST`` is a typo). Tests issue ``app_client.get``
  and rely on FastAPI's method allow-list to surface a 405 if the route
  ever gets re-mounted as POST.
* State CSRF guard: ``state == clerk_org_id`` (per PATTERNS divergence
  note — InstallButton sends Clerk ``organization.id``; the backend's
  ``resolve_team_from_clerk_org`` already maps that to a Team, so we
  compare against ``team.clerk_org_id`` server-side). Mismatched state
  returns 403 ``state_mismatch`` and writes nothing to the DB.
* Install reverify: the route fetches ``GET /app/installations/{id}``
  with an App JWT (NOT installation token) before persisting, so a forged
  callback URL pointing at a non-existent installation returns a redirect
  with ``?install=failed`` and skips the DB write.
* Idempotent upsert: second callback with the same
  ``(team_id, installation_id)`` triggers ON CONFLICT DO UPDATE — no
  UNIQUE violation, login/type fields refreshed.
* Redirect targets: 302 with Location ending in
  ``/settings/integrations?install=success`` (or ``=failed`` on 404).
"""
from __future__ import annotations

from typing import Any

import httpx
import pytest
from sqlalchemy import text

pytestmark = pytest.mark.rls


@pytest.fixture
def callback_dashboard_url(monkeypatch: pytest.MonkeyPatch) -> str:
    """Pin the dashboard URL for redirect-Location assertions."""
    url = "https://dashboard.test.invalid"
    monkeypatch.setenv("DASHBOARD_URL", url)
    return url


def _callback_url(installation_id: int, state: str, action: str = "install") -> str:
    return (
        f"/v1/github/install-callback?installation_id={installation_id}"
        f"&setup_action={action}&state={state}"
    )


async def test_install_callback_state_mismatch_403(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
    seed_session: Any,
    respx_github: Any,
    gh_settings_patched: Any,
    callback_dashboard_url: str,
) -> None:
    """state != team.clerk_org_id → 403; no DB write; no GitHub call."""
    headers = auth_headers_factory(team_a.clerk_org_id)
    install_call = respx_github.get("/app/installations/99887766").mock(
        return_value=httpx.Response(
            200, json={"account": {"login": "x", "type": "User"}}
        )
    )

    r = app_client.get(
        _callback_url(99887766, "wrong-org-id"),
        headers=headers,
        follow_redirects=False,
    )
    assert r.status_code == 403, r.text
    assert r.json()["detail"] == "state_mismatch"
    # No GitHub call should have been issued.
    assert not install_call.called

    # Confirm no row was inserted.
    rows = (
        await seed_session.execute(
            text(
                "SELECT 1 FROM github_installations WHERE team_id = :t"
            ),
            {"t": str(team_a.id)},
        )
    ).all()
    assert rows == []


def test_install_callback_unauthenticated(
    app_client: Any,
    callback_dashboard_url: str,
) -> None:
    """No Clerk JWT → 401 (require_principal raises before state check)."""
    r = app_client.get(
        _callback_url(99887766, "any-state"), follow_redirects=False
    )
    assert r.status_code == 401


async def test_install_callback_install_reverified_via_app_jwt(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
    seed_session: Any,
    respx_github: Any,
    gh_settings_patched: Any,
    callback_dashboard_url: str,
) -> None:
    """Successful callback re-fetches /app/installations/{id} with App JWT.

    Asserts the route hit the App-JWT-authed metadata endpoint AND did
    NOT mint an installation token (which would be the wrong auth flow
    for /app/installations/{id}). See client.py::get_installation_metadata.
    """
    headers = auth_headers_factory(team_a.clerk_org_id)

    install_route = respx_github.get("/app/installations/99887766").mock(
        return_value=httpx.Response(
            200,
            json={
                "account": {"login": "reverified-org", "type": "Organization"}
            },
        )
    )
    # Should NOT be called for install-callback.
    token_route = respx_github.post(
        "/app/installations/99887766/access_tokens"
    ).mock(return_value=httpx.Response(200, json={"token": "ghs_unused"}))

    r = app_client.get(
        _callback_url(99887766, team_a.clerk_org_id),
        headers=headers,
        follow_redirects=False,
    )
    assert r.status_code == 302, r.text
    # Bearer header on the metadata call should be the App JWT (not an
    # installation token; test_client.py asserts the discrimination).
    assert install_route.called
    assert install_route.call_count == 1
    bearer = install_route.calls.last.request.headers["authorization"]
    assert bearer.startswith("Bearer ")
    # JWT segments use '.' separators; installation tokens don't.
    assert bearer.count(".") == 2
    # Token-mint endpoint never hit — install-callback uses App JWT only.
    assert not token_route.called


async def test_install_callback_upsert(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
    seed_session: Any,
    respx_github: Any,
    gh_settings_patched: Any,
    callback_dashboard_url: str,
) -> None:
    """Valid state → row inserted with the verified account metadata."""
    headers = auth_headers_factory(team_a.clerk_org_id, sub="user_install_456")

    respx_github.get("/app/installations/99887766").mock(
        return_value=httpx.Response(
            200, json={"account": {"login": "acme-corp", "type": "Organization"}}
        )
    )

    r = app_client.get(
        _callback_url(99887766, team_a.clerk_org_id),
        headers=headers,
        follow_redirects=False,
    )
    assert r.status_code == 302, r.text

    rows = (
        await seed_session.execute(
            text(
                "SELECT github_installation_id, github_account_login, "
                "github_account_type, installed_by_user_id "
                "FROM github_installations WHERE team_id = :t"
            ),
            {"t": str(team_a.id)},
        )
    ).all()
    assert len(rows) == 1
    iid, login, gtype, uid = rows[0]
    assert iid == 99887766
    assert login == "acme-corp"
    assert gtype == "Organization"
    assert uid == "user_install_456"


async def test_install_callback_redirects_success(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
    seed_session: Any,
    respx_github: Any,
    gh_settings_patched: Any,
    callback_dashboard_url: str,
) -> None:
    """302 with Location ending in /settings/integrations?install=success."""
    headers = auth_headers_factory(team_a.clerk_org_id)
    respx_github.get("/app/installations/99887766").mock(
        return_value=httpx.Response(
            200, json={"account": {"login": "x", "type": "User"}}
        )
    )

    r = app_client.get(
        _callback_url(99887766, team_a.clerk_org_id),
        headers=headers,
        follow_redirects=False,
    )
    assert r.status_code == 302
    location = r.headers["location"]
    assert location == (
        f"{callback_dashboard_url}/settings/integrations?install=success"
    )


async def test_install_callback_idempotent(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
    seed_session: Any,
    respx_github: Any,
    gh_settings_patched: Any,
    callback_dashboard_url: str,
) -> None:
    """Second callback with same (team, install_id) does ON CONFLICT DO UPDATE."""
    headers = auth_headers_factory(team_a.clerk_org_id)

    # First call — login is "old-name".
    respx_github.get("/app/installations/99887766").mock(
        return_value=httpx.Response(
            200,
            json={"account": {"login": "old-name", "type": "Organization"}},
        )
    )
    r1 = app_client.get(
        _callback_url(99887766, team_a.clerk_org_id),
        headers=headers,
        follow_redirects=False,
    )
    assert r1.status_code == 302

    # Second call — same install_id, login renamed to "new-name".
    respx_github.get("/app/installations/99887766").mock(
        return_value=httpx.Response(
            200,
            json={"account": {"login": "new-name", "type": "Organization"}},
        )
    )
    r2 = app_client.get(
        _callback_url(99887766, team_a.clerk_org_id),
        headers=headers,
        follow_redirects=False,
    )
    assert r2.status_code == 302

    # Exactly one row, with the refreshed login.
    rows = (
        await seed_session.execute(
            text(
                "SELECT github_account_login FROM github_installations "
                "WHERE team_id = :t"
            ),
            {"t": str(team_a.id)},
        )
    ).all()
    assert len(rows) == 1
    assert rows[0][0] == "new-name"


async def test_install_callback_install_404(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
    seed_session: Any,
    respx_github: Any,
    gh_settings_patched: Any,
    callback_dashboard_url: str,
) -> None:
    """GitHub 404 on metadata fetch → redirect with ?install=failed; no DB write."""
    headers = auth_headers_factory(team_a.clerk_org_id)
    respx_github.get("/app/installations/99887766").mock(
        return_value=httpx.Response(404, json={"message": "Not Found"})
    )

    r = app_client.get(
        _callback_url(99887766, team_a.clerk_org_id),
        headers=headers,
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert r.headers["location"] == (
        f"{callback_dashboard_url}/settings/integrations?install=failed"
    )

    rows = (
        await seed_session.execute(
            text(
                "SELECT 1 FROM github_installations WHERE team_id = :t"
            ),
            {"t": str(team_a.id)},
        )
    ).all()
    assert rows == []
