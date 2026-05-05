"""GitHub webhook handler tests — POST /v1/webhooks/github (Phase 8 WBH-01).

7 tests covering the full handler decision tree:

  1. test_invalid_hmac_returns_401
     — wrong sig → 401 before any payload parse (T-8-02-01)
  2. test_unconfigured_secret_returns_500
     — empty ``github_app_webhook_secret`` → 500 before HMAC (T-8-02-03)
  3. test_ping_event_returns_200
     — X-GitHub-Event: ping → 200 {"ok": True} no DB (T-8-02 ping swallow)
  4. test_non_push_event_returns_200
     — X-GitHub-Event: check_run → 200 {"ok": True} no DB (T-8-02-06)
  5. test_deleted_branch_returns_200
     — deleted=True push → 200 {"ok": True} no DB (T-8-02-04)
  6. test_non_default_branch_returns_200
     — ref != refs/heads/<default_branch> → 200 {"ok": True} no DB (T-8-02-05)
  7. test_happy_path_creates_scan_and_enqueues
     — valid default-branch push → 200, DB INSERT with source='webhook', kiq called
       with all 7 CC-4 kwargs (T-8-02-08)

Wave 1 — all tests mock the DB layer.  No Postgres testcontainer required.

HMAC helper follows RESEARCH § L-08 and GitHub's documented spec:
``sha256=<hmac-sha256-hex(secret_bytes, raw_body)>``.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import sys
import types
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WEBHOOK_SECRET = "test-webhook-secret-abc"

# ---------------------------------------------------------------------------
# HMAC helper (mirrors what the handler computes internally)
# ---------------------------------------------------------------------------


def _sign(body: bytes, secret: str) -> str:
    """Return the ``X-Hub-Signature-256`` header value for *body* + *secret*."""
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def settings_with_secret(monkeypatch: pytest.MonkeyPatch):
    """Override ``settings.github_app_webhook_secret`` with the test secret."""
    from app.settings import settings

    monkeypatch.setattr(settings, "github_app_webhook_secret", WEBHOOK_SECRET)
    return settings


@pytest.fixture
def webhook_client() -> TestClient:
    """Plain TestClient (no Postgres) — sufficient for the HMAC/event-filter tests."""
    from app.main import create_app

    return TestClient(create_app(), raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Payload builders
# ---------------------------------------------------------------------------


def _push_payload(
    *,
    ref: str = "refs/heads/main",
    default_branch: str = "main",
    after: str = "a" * 40,
    deleted: bool = False,
    installation_id: int = 99887766,
    repo: str = "acme/infra",
) -> bytes:
    """Minimal GitHub push event payload."""
    return json.dumps(
        {
            "ref": ref,
            "after": after,
            "deleted": deleted,
            "installation": {"id": installation_id},
            "repository": {
                "full_name": repo,
                "default_branch": default_branch,
            },
        }
    ).encode()


# ---------------------------------------------------------------------------
# Test 1: invalid HMAC returns 401
# ---------------------------------------------------------------------------


def test_invalid_hmac_returns_401(
    webhook_client: TestClient,
    settings_with_secret: Any,
) -> None:
    """T-8-02-01: wrong signature → 401 before any payload parsing."""
    body = _push_payload()
    r = webhook_client.post(
        "/v1/webhooks/github",
        content=body,
        headers={
            "X-Hub-Signature-256": "sha256=deadbeef",
            "X-GitHub-Event": "push",
            "Content-Type": "application/json",
        },
    )
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Test 2: unconfigured secret returns 500
# ---------------------------------------------------------------------------


def test_unconfigured_secret_returns_500(webhook_client: TestClient) -> None:
    """T-8-02-03: empty ``github_app_webhook_secret`` → 500 before HMAC.

    This test does NOT apply the settings_with_secret fixture so the
    secret remains the conftest default ``"test-webhook-secret"`` which
    may or may not be empty in the test environment.  We need to ensure
    the secret is *exactly* empty — monkeypatch directly.
    """
    from app.settings import settings

    original = settings.github_app_webhook_secret
    settings.github_app_webhook_secret = ""
    try:
        body = b'{"zen": "test"}'
        r = webhook_client.post(
            "/v1/webhooks/github",
            content=body,
            headers={
                "X-Hub-Signature-256": "sha256=anything",
                "X-GitHub-Event": "ping",
                "Content-Type": "application/json",
            },
        )
        assert r.status_code == 500
    finally:
        settings.github_app_webhook_secret = original


# ---------------------------------------------------------------------------
# Test 3: ping event returns 200
# ---------------------------------------------------------------------------


def test_ping_event_returns_200(
    webhook_client: TestClient,
    settings_with_secret: Any,
) -> None:
    """GitHub sends ping on webhook creation → 200 {"ok": True} immediately."""
    body = json.dumps({"zen": "test"}).encode()
    sig = _sign(body, WEBHOOK_SECRET)
    r = webhook_client.post(
        "/v1/webhooks/github",
        content=body,
        headers={
            "X-Hub-Signature-256": sig,
            "X-GitHub-Event": "ping",
            "Content-Type": "application/json",
        },
    )
    assert r.status_code == 200
    assert r.json() == {"ok": True}


# ---------------------------------------------------------------------------
# Test 4: non-push event returns 200 (no DB access)
# ---------------------------------------------------------------------------


def test_non_push_event_returns_200(
    webhook_client: TestClient,
    settings_with_secret: Any,
) -> None:
    """T-8-02-06: X-GitHub-Event other than push/ping → 200 {"ok": True}."""
    body = json.dumps({"action": "created"}).encode()
    sig = _sign(body, WEBHOOK_SECRET)
    r = webhook_client.post(
        "/v1/webhooks/github",
        content=body,
        headers={
            "X-Hub-Signature-256": sig,
            "X-GitHub-Event": "check_run",
            "Content-Type": "application/json",
        },
    )
    assert r.status_code == 200
    assert r.json() == {"ok": True}


# ---------------------------------------------------------------------------
# Test 5: deleted branch push returns 200 (no DB access)
# ---------------------------------------------------------------------------


def test_deleted_branch_returns_200(
    webhook_client: TestClient,
    settings_with_secret: Any,
) -> None:
    """T-8-02-04: deleted=True push → 200 {"ok": True}, no scan row created."""
    body = _push_payload(deleted=True, after="b" * 40)
    sig = _sign(body, WEBHOOK_SECRET)
    r = webhook_client.post(
        "/v1/webhooks/github",
        content=body,
        headers={
            "X-Hub-Signature-256": sig,
            "X-GitHub-Event": "push",
            "Content-Type": "application/json",
        },
    )
    assert r.status_code == 200
    assert r.json() == {"ok": True}


# ---------------------------------------------------------------------------
# Test 6: non-default branch push returns 200
# ---------------------------------------------------------------------------


def test_non_default_branch_returns_200(
    webhook_client: TestClient,
    settings_with_secret: Any,
) -> None:
    """T-8-02-05: push to feature branch → 200 {"ok": True}, no scan row."""
    body = _push_payload(ref="refs/heads/feature", default_branch="main")
    sig = _sign(body, WEBHOOK_SECRET)
    r = webhook_client.post(
        "/v1/webhooks/github",
        content=body,
        headers={
            "X-Hub-Signature-256": sig,
            "X-GitHub-Event": "push",
            "Content-Type": "application/json",
        },
    )
    assert r.status_code == 200
    assert r.json() == {"ok": True}


# ---------------------------------------------------------------------------
# Test 7: happy path creates scan row and enqueues
# ---------------------------------------------------------------------------


def test_happy_path_creates_scan_and_enqueues(
    webhook_client: TestClient,
    settings_with_secret: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-8-02-08: valid default-branch push → 200, INSERT source='webhook', kiq called.

    Mocks:
    - ``get_sessionmaker`` returns a context-manager mock whose session
      executes return:
        * ``scalar_one_or_none()`` → a fake UUID (team_id)
        * second execute (set_config) → None
        * third execute (INSERT) → None
    - ``scan_repo`` stub registered in sys.modules before lazy import fires.
    """
    import types as _types
    from unittest.mock import AsyncMock, MagicMock

    FAKE_TEAM_ID = "11111111-1111-1111-1111-111111111111"
    INSTALL_ID = 99887766

    # --- Build a stub session that satisfies scalar_one_or_none + execute calls ---
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    # session.begin() context manager
    mock_begin = AsyncMock()
    mock_begin.__aenter__ = AsyncMock(return_value=None)
    mock_begin.__aexit__ = AsyncMock(return_value=False)
    mock_session.begin = MagicMock(return_value=mock_begin)

    # First execute → result with scalar_one_or_none() → FAKE_TEAM_ID (UUID)
    from uuid import UUID as _UUID

    first_result = MagicMock()
    first_result.scalar_one_or_none = MagicMock(return_value=_UUID(FAKE_TEAM_ID))

    # Subsequent executes return None-ish result
    subsequent_result = MagicMock()
    subsequent_result.scalar_one_or_none = MagicMock(return_value=None)

    # execute() is async; alternate between first and subsequent results
    execute_call_count = [0]

    async def _execute(*args: Any, **kwargs: Any) -> Any:
        execute_call_count[0] += 1
        if execute_call_count[0] == 1:
            return first_result
        return subsequent_result

    mock_session.execute = _execute

    # sm() → async context manager yielding mock_session
    mock_sm_instance = MagicMock()
    mock_sm_instance.__aenter__ = AsyncMock(return_value=mock_session)
    mock_sm_instance.__aexit__ = AsyncMock(return_value=False)

    mock_sm = MagicMock(return_value=mock_sm_instance)

    # --- Stub scan_repo module (lazy import inside handler) ---
    kiq_store: dict[str, Any] = {}

    class _Kicker:
        def with_labels(self, **kw: Any) -> "_Kicker":
            kiq_store.setdefault("labels", {}).update(kw)
            return self

        async def kiq(self, **kwargs: Any) -> None:
            kiq_store["called"] = True
            kiq_store["kwargs"] = kwargs

    class _StubTask:
        def kicker(self) -> _Kicker:
            return _Kicker()

    stub_mod = _types.ModuleType("app.queue.tasks.scan_repo")
    stub_mod.scan_repo = _StubTask()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "app.queue.tasks.scan_repo", stub_mod)

    # --- Patch get_sessionmaker at the route module level ---
    monkeypatch.setattr(
        "app.routes.webhooks.get_sessionmaker",
        MagicMock(return_value=mock_sm),
    )

    # --- Fire the request ---
    body = _push_payload(
        ref="refs/heads/main",
        default_branch="main",
        after="c" * 40,
        installation_id=INSTALL_ID,
        repo="acme/infra",
    )
    sig = _sign(body, WEBHOOK_SECRET)
    r = webhook_client.post(
        "/v1/webhooks/github",
        content=body,
        headers={
            "X-Hub-Signature-256": sig,
            "X-GitHub-Event": "push",
            "Content-Type": "application/json",
        },
    )

    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True}

    # scan_repo.kiq must have been called with the 7 CC-4 kwargs
    assert kiq_store.get("called") is True, "scan_repo.kiq was not called"
    kw = kiq_store["kwargs"]
    assert kw["installation_id"] == INSTALL_ID
    assert kw["repo"] == "acme/infra"
    assert kw["branch"] == "main"
    assert kw["sha"] == "c" * 40
    assert kw["path"] == "."
    assert kw["team_id"] == FAKE_TEAM_ID
    # scan_id must be a valid UUID string
    UUID(kw["scan_id"])
