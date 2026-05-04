"""Integration tests for ``POST /v1/scans/from-github`` (Phase 7.5 D-10e + D-13).

Asserts:

* Happy path — POST {installation_id, repo, branch} → 200 {scan_id};
  pending row inserted with source='github' + github_* provenance columns;
  scan_repo.kicker().kiq(...) called once with all 7 contracted kwargs.
* Subpath — body.path='./infra' is persisted as source_path.
* Branch resolution — GitHub 404 on ``/git/ref/heads/{branch}`` surfaces
  as 404 ``branch_not_found`` (resolution failure mid-flight, no row written).
* Cross-team install probe — installation_id not in the caller's team's
  github_installations → 404 ``installation_not_found`` (no GitHub call,
  no row written).
* Role gate — basic_member → 403 (commit-class write, mirrors
  scans.py::commit_scan role list).
* Repo regex — Pydantic strict regex on ``repo`` rejects ``"bad"`` (no
  slash) with 422 (boundary validator, before route body).
* Enqueue failure — taskiq kiq() raising flips the just-inserted row to
  ``status='failed'`` with ``error_message='enqueue_failed'`` (no orphan
  pending) and surfaces 503 ``enqueue_failed`` to the client.
* GET /v1/scans/{id} extended response shape — pending row returns
  status, error_message=null, source_path, github_* columns,
  presigned_get_url=null (only signed when status=ready).
* GET /v1/scans/{id} failed row — error_message surfaces.
* GET /v1/scans/{id} ready row — presigned_get_url is non-null.

The scan_repo task lives in Plan 06 which has not yet landed; the
route imports it lazily (``from app.queue.tasks.scan_repo import
scan_repo`` inside the enqueue try block). Tests stub via
``monkeypatch.setattr('app.routes.scans_from_github.scan_repo', stub)``
to avoid hitting the not-yet-existing module. NOTE: the patch target is
the LOCAL binding inside the route module (after the lazy import has
landed it there). For tests that must run before the lazy import has
ever been resolved, we patch ``sys.modules`` directly so the import
succeeds with our stub.
"""
from __future__ import annotations

import sys
import types
from typing import Any
from uuid import UUID

import httpx
import pytest
from sqlalchemy import text

pytestmark = pytest.mark.rls


# ---------------------------------------------------------------------------
# Helpers — seed an installation row, build a stub scan_repo module.
# ---------------------------------------------------------------------------


async def _seed_install(
    seed_session: Any, team_id: Any, *, install_id: int
) -> None:
    await seed_session.execute(
        text(
            """
            INSERT INTO github_installations
                (id, team_id, github_installation_id, github_account_login,
                 github_account_type, installed_by_user_id)
            VALUES (gen_random_uuid(), :team_id, :iid, 'acme',
                    'Organization', 'u_install')
            """
        ),
        {"team_id": str(team_id), "iid": install_id},
    )
    await seed_session.commit()


class _RecordingKicker:
    """Captures kicker().with_labels(...).kiq(...) calls without running anything."""

    def __init__(self, store: dict[str, Any], *, raise_on_kiq: bool = False) -> None:
        self._store = store
        self._raise = raise_on_kiq

    def with_labels(self, **labels: Any) -> _RecordingKicker:
        self._store.setdefault("labels", {}).update(labels)
        return self

    async def kiq(self, **kwargs: Any) -> None:
        if self._raise:
            raise RuntimeError("simulated_broker_failure")
        self._store["kiq_count"] = self._store.get("kiq_count", 0) + 1
        self._store.setdefault("kiq_kwargs", []).append(kwargs)


class _StubScanRepo:
    def __init__(self, store: dict[str, Any], *, raise_on_kiq: bool = False) -> None:
        self._store = store
        self._raise = raise_on_kiq

    def kicker(self) -> _RecordingKicker:
        return _RecordingKicker(self._store, raise_on_kiq=self._raise)


def _install_scan_repo_stub(
    monkeypatch: pytest.MonkeyPatch, *, raise_on_kiq: bool = False
) -> dict[str, Any]:
    """Inject a stub ``app.queue.tasks.scan_repo`` module before the lazy import.

    The route does ``from app.queue.tasks.scan_repo import scan_repo`` inside
    the enqueue try block. For tests, we register a fake module in
    ``sys.modules`` so that import resolves to our stub without triggering the
    not-yet-existent Plan 06 module. Returns the recording dict.
    """
    store: dict[str, Any] = {}
    stub_mod = types.ModuleType("app.queue.tasks.scan_repo")
    stub_mod.scan_repo = _StubScanRepo(store, raise_on_kiq=raise_on_kiq)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "app.queue.tasks.scan_repo", stub_mod)
    return store


# ---------------------------------------------------------------------------
# POST /v1/scans/from-github tests
# ---------------------------------------------------------------------------


async def test_scan_from_github_happy(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
    seed_session: Any,
    respx_github: Any,
    gh_settings_patched: Any,
    installation_id: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST resolves HEAD sha, INSERTs pending row, enqueues scan_repo."""
    await _seed_install(seed_session, team_a.id, install_id=installation_id)
    store = _install_scan_repo_stub(monkeypatch)

    # Token mint + HEAD-sha resolution.
    respx_github.post(
        f"/app/installations/{installation_id}/access_tokens"
    ).mock(return_value=httpx.Response(200, json={"token": "ghs_test_fg"}))
    respx_github.get("/repos/acme/infra/git/ref/heads/main").mock(
        return_value=httpx.Response(
            200, json={"object": {"sha": "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"}}
        )
    )

    headers = auth_headers_factory(team_a.clerk_org_id)
    r = app_client.post(
        "/v1/scans/from-github",
        headers=headers,
        json={
            "installation_id": installation_id,
            "repo": "acme/infra",
            "branch": "main",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    scan_id = UUID(body["scan_id"])

    # Row inspect via BYPASSRLS.
    row = (
        await seed_session.execute(
            text(
                "SELECT status, source, source_path, github_installation_id, "
                "github_repo, github_branch, github_sha, error_message, team_id "
                "FROM scans WHERE id = :id"
            ),
            {"id": str(scan_id)},
        )
    ).one()
    assert row.status == "pending"
    assert row.source == "github"
    assert row.source_path == "."
    assert row.github_installation_id == installation_id
    assert row.github_repo == "acme/infra"
    assert row.github_branch == "main"
    assert row.github_sha == "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
    assert row.error_message is None
    assert row.team_id == team_a.id

    # Enqueue happened with the full CC-4 kwarg shape.
    assert store.get("kiq_count") == 1
    kw = store["kiq_kwargs"][0]
    assert kw["scan_id"] == str(scan_id)
    assert kw["installation_id"] == installation_id
    assert kw["repo"] == "acme/infra"
    assert kw["branch"] == "main"
    assert kw["sha"] == "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
    assert kw["path"] == "."
    assert kw["team_id"] == str(team_a.id)


async def test_scan_from_github_subpath_persisted(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
    seed_session: Any,
    respx_github: Any,
    gh_settings_patched: Any,
    installation_id: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """body.path='./infra' is persisted to scans.source_path verbatim."""
    await _seed_install(seed_session, team_a.id, install_id=installation_id)
    _install_scan_repo_stub(monkeypatch)

    respx_github.post(
        f"/app/installations/{installation_id}/access_tokens"
    ).mock(return_value=httpx.Response(200, json={"token": "ghs_subpath"}))
    respx_github.get("/repos/acme/infra/git/ref/heads/main").mock(
        return_value=httpx.Response(200, json={"object": {"sha": "f" * 40}})
    )

    headers = auth_headers_factory(team_a.clerk_org_id)
    r = app_client.post(
        "/v1/scans/from-github",
        headers=headers,
        json={
            "installation_id": installation_id,
            "repo": "acme/infra",
            "branch": "main",
            "path": "./infra",
        },
    )
    assert r.status_code == 200, r.text
    sid = UUID(r.json()["scan_id"])

    row = (
        await seed_session.execute(
            text("SELECT source_path FROM scans WHERE id = :id"),
            {"id": str(sid)},
        )
    ).one()
    assert row.source_path == "./infra"


async def test_scan_from_github_branch_404(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
    seed_session: Any,
    respx_github: Any,
    gh_settings_patched: Any,
    installation_id: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GitHub 404 on git/ref/heads/{branch} → endpoint 404 + no row written."""
    await _seed_install(seed_session, team_a.id, install_id=installation_id)
    _install_scan_repo_stub(monkeypatch)

    respx_github.post(
        f"/app/installations/{installation_id}/access_tokens"
    ).mock(return_value=httpx.Response(200, json={"token": "ghs_b404"}))
    respx_github.get("/repos/acme/infra/git/ref/heads/no-such").mock(
        return_value=httpx.Response(404, json={"message": "Not Found"})
    )

    headers = auth_headers_factory(team_a.clerk_org_id)
    r = app_client.post(
        "/v1/scans/from-github",
        headers=headers,
        json={
            "installation_id": installation_id,
            "repo": "acme/infra",
            "branch": "no-such",
        },
    )
    assert r.status_code == 404, r.text
    assert "branch_not_found" in r.json()["detail"]

    rows = (
        await seed_session.execute(
            text("SELECT 1 FROM scans WHERE team_id = :t"),
            {"t": str(team_a.id)},
        )
    ).all()
    assert rows == []


async def test_scan_from_github_unknown_installation_404(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
    seed_session: Any,
    respx_github: Any,
    gh_settings_patched: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """installation_id not in caller's github_installations → 404 + no GitHub call."""
    _install_scan_repo_stub(monkeypatch)
    token_route = respx_github.post(
        "/app/installations/55555555/access_tokens"
    ).mock(return_value=httpx.Response(200, json={"token": "ghs_never"}))

    headers = auth_headers_factory(team_a.clerk_org_id)
    r = app_client.post(
        "/v1/scans/from-github",
        headers=headers,
        json={
            "installation_id": 55555555,
            "repo": "acme/infra",
            "branch": "main",
        },
    )
    assert r.status_code == 404, r.text
    assert r.json()["detail"] == "installation_not_found"
    assert not token_route.called


async def test_scan_from_github_basic_member_forbidden(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
    seed_session: Any,
    installation_id: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """basic_member role cannot trigger a billing-meterable scan (T-07.5-05-06)."""
    await _seed_install(seed_session, team_a.id, install_id=installation_id)
    _install_scan_repo_stub(monkeypatch)

    headers = auth_headers_factory(team_a.clerk_org_id, role="basic_member")
    r = app_client.post(
        "/v1/scans/from-github",
        headers=headers,
        json={
            "installation_id": installation_id,
            "repo": "acme/infra",
            "branch": "main",
        },
    )
    assert r.status_code == 403, r.text


async def test_scan_from_github_repo_pattern_422(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pydantic strict regex rejects 'bad' (no slash) with 422 before route body."""
    _install_scan_repo_stub(monkeypatch)
    headers = auth_headers_factory(team_a.clerk_org_id)
    r = app_client.post(
        "/v1/scans/from-github",
        headers=headers,
        json={
            "installation_id": 1,
            "repo": "bad",
            "branch": "main",
        },
    )
    assert r.status_code == 422, r.text


async def test_scan_from_github_enqueue_failure_flips_failed(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
    seed_session: Any,
    respx_github: Any,
    gh_settings_patched: Any,
    installation_id: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """taskiq kiq() raising → row flipped to failed + 503 enqueue_failed."""
    await _seed_install(seed_session, team_a.id, install_id=installation_id)
    _install_scan_repo_stub(monkeypatch, raise_on_kiq=True)

    respx_github.post(
        f"/app/installations/{installation_id}/access_tokens"
    ).mock(return_value=httpx.Response(200, json={"token": "ghs_eq"}))
    respx_github.get("/repos/acme/infra/git/ref/heads/main").mock(
        return_value=httpx.Response(200, json={"object": {"sha": "a" * 40}})
    )

    headers = auth_headers_factory(team_a.clerk_org_id)
    r = app_client.post(
        "/v1/scans/from-github",
        headers=headers,
        json={
            "installation_id": installation_id,
            "repo": "acme/infra",
            "branch": "main",
        },
    )
    assert r.status_code == 503, r.text
    assert r.json()["detail"] == "enqueue_failed"

    # Exactly one row exists for this team — flipped to 'failed' with error_message.
    rows = (
        await seed_session.execute(
            text(
                "SELECT status, error_message FROM scans WHERE team_id = :t"
            ),
            {"t": str(team_a.id)},
        )
    ).all()
    assert len(rows) == 1
    assert rows[0].status == "failed"
    assert rows[0].error_message == "enqueue_failed"


# ---------------------------------------------------------------------------
# Extended GET /v1/scans/{id} response shape tests
# ---------------------------------------------------------------------------


async def test_get_scan_extended_fields_pending(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
    seed_session: Any,
    respx_github: Any,
    gh_settings_patched: Any,
    installation_id: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /v1/scans/{id} surfaces all six new fields; presigned_get_url is null
    when status='pending'."""
    await _seed_install(seed_session, team_a.id, install_id=installation_id)
    _install_scan_repo_stub(monkeypatch)

    respx_github.post(
        f"/app/installations/{installation_id}/access_tokens"
    ).mock(return_value=httpx.Response(200, json={"token": "ghs_get"}))
    respx_github.get("/repos/acme/infra/git/ref/heads/main").mock(
        return_value=httpx.Response(200, json={"object": {"sha": "1" * 40}})
    )

    headers = auth_headers_factory(team_a.clerk_org_id)
    post = app_client.post(
        "/v1/scans/from-github",
        headers=headers,
        json={
            "installation_id": installation_id,
            "repo": "acme/infra",
            "branch": "main",
        },
    )
    assert post.status_code == 200, post.text
    sid = post.json()["scan_id"]

    get = app_client.get(f"/v1/scans/{sid}", headers=headers)
    assert get.status_code == 200, get.text
    body = get.json()
    assert body["status"] == "pending"
    assert body["error_message"] is None
    assert body["source_path"] == "."
    assert body["github_installation_id"] == installation_id
    assert body["github_repo"] == "acme/infra"
    assert body["github_branch"] == "main"
    assert body["github_sha"] == "1" * 40
    # Pending row → presigned URL must be null (no R2 object yet).
    assert body["presigned_get_url"] is None


async def test_get_scan_failed_with_error_message(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
    seed_session: Any,
) -> None:
    """A scan in status='failed' with an error_message surfaces both fields."""
    from app.db.models import Scan, ScanStatus
    from app.util.ids import new_uuid7

    sid = new_uuid7()
    scan = Scan(
        id=sid,
        team_id=team_a.id,
        r2_key="",
        status=ScanStatus.failed,
        error_message="clone timeout",
        source="github",
        source_path=".",
        github_installation_id=12345,
        github_repo="acme/api",
        github_branch="release",
        github_sha="b" * 40,
    )
    async with seed_session.begin():
        seed_session.add(scan)

    headers = auth_headers_factory(team_a.clerk_org_id)
    r = app_client.get(f"/v1/scans/{sid}", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "failed"
    assert body["error_message"] == "clone timeout"
    assert body["github_installation_id"] == 12345
    assert body["github_repo"] == "acme/api"
    assert body["github_branch"] == "release"
    assert body["github_sha"] == "b" * 40
    # Failed row also has no R2 object → presigned URL is null.
    assert body["presigned_get_url"] is None


async def test_get_scan_ready_signs_url(
    app_client: Any,
    team_a: Any,
    auth_headers_factory: Any,
    seed_session: Any,
) -> None:
    """A 'ready' row with r2_key set → presigned_get_url is non-null."""
    from app.db.models import Scan, ScanStatus
    from app.util.ids import new_uuid7

    sid = new_uuid7()
    scan = Scan(
        id=sid,
        team_id=team_a.id,
        r2_key=f"teams/{team_a.id}/scans/{sid}.json",
        status=ScanStatus.ready,
        sha256="d" * 64,
        size_bytes=4096,
    )
    async with seed_session.begin():
        seed_session.add(scan)

    headers = auth_headers_factory(team_a.clerk_org_id)
    r = app_client.get(f"/v1/scans/{sid}", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ready"
    assert body["presigned_get_url"] is not None
    assert body["presigned_get_url"].startswith("http")
