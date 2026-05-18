"""Phase 12 NFN-02 — Phase 8 Slack dispatcher reuse tests.

GREEN once Plan 12-04 lands ``app.notifications.slack.send_team_slack``
(extracted from scan_repo.py:299-341).

Synthetic webhook URL only (T-12-01-03 mitigation — never a real workspace URL).
"""
from __future__ import annotations

import json
from typing import Any
from unittest import mock

import httpx
import pytest
import respx

from app.notifications import slack as slack_mod
from app.notifications.slack import send_team_slack

_FAKE_SLACK_URL = "https://hooks.slack.com/test"  # T-12-01-03 synthetic only
_FAKE_TEAM_ID = "00000000-0000-0000-0000-000000000001"


class _FakeRow:
    def __init__(self, slack_webhook_url: str | None) -> None:
        self.slack_webhook_url = slack_webhook_url


def _install_fake_sessionmaker(
    monkeypatch: pytest.MonkeyPatch,
    *,
    row: _FakeRow | None,
) -> None:
    """Monkeypatch get_sessionmaker() with a fake that returns ``row`` for
    the slack_webhook_url SELECT and no-ops set_config."""

    class _NoopResult:
        def one_or_none(self) -> None:
            return None

    class _RowResult:
        def __init__(self, r: _FakeRow | None) -> None:
            self._r = r

        def one_or_none(self) -> _FakeRow | None:
            return self._r

    class _FakeSession:
        async def __aenter__(self) -> Any:
            return self

        async def __aexit__(self, *exc: Any) -> bool:
            return False

        def begin(self) -> Any:
            class _Tx:
                async def __aenter__(self_inner) -> Any:  # noqa: N805
                    return self_inner

                async def __aexit__(self_inner, *exc: Any) -> bool:  # noqa: N805
                    return False

            return _Tx()

        async def execute(self, stmt: Any, *_args: Any, **_kwargs: Any) -> Any:
            stmt_str = str(stmt)
            if "set_config" in stmt_str:
                return _NoopResult()
            if "slack_webhook_url" in stmt_str:
                return _RowResult(row)
            return _NoopResult()

    class _FakeMaker:
        def __call__(self) -> _FakeSession:
            return _FakeSession()

    monkeypatch.setattr(slack_mod, "get_sessionmaker", lambda: _FakeMaker())


@pytest.mark.asyncio
@respx.mock
async def test_send_team_slack_posts_to_team_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NFN-02: team with slack_webhook_url=<synthetic> → send_team_slack POSTs
    JSON with ``text=message`` to that URL."""
    _install_fake_sessionmaker(
        monkeypatch, row=_FakeRow(slack_webhook_url=_FAKE_SLACK_URL)
    )

    route = respx.post(_FAKE_SLACK_URL).mock(
        return_value=httpx.Response(200, json={"ok": True})
    )

    await send_team_slack(
        team_id=_FAKE_TEAM_ID,
        message="Asymmetric path detected",
        log_ctx_key="path_compute",
    )

    assert route.called, "send_team_slack must POST to the team's webhook URL"
    body = json.loads(route.calls[0].request.content)
    assert body["text"] == "Asymmetric path detected"


@pytest.mark.asyncio
@respx.mock
async def test_send_team_slack_no_url_no_op(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NFN-02: team with slack_webhook_url=None → no HTTP call, returns None."""
    _install_fake_sessionmaker(
        monkeypatch, row=_FakeRow(slack_webhook_url=None)
    )

    # Any HTTP attempt should not match a mocked route, but respx.mock here
    # asserts no unexpected calls are made — passing means zero POSTs fired.
    result = await send_team_slack(
        team_id=_FAKE_TEAM_ID,
        message="anything",
        log_ctx_key="scan_repo",
    )
    assert result is None
    assert len(respx.calls) == 0, (
        "send_team_slack must be a no-op when slack_webhook_url is NULL"
    )


@pytest.mark.asyncio
@respx.mock
async def test_send_team_slack_failure_swallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NFN-02: httpx raises ConnectError → no exception escapes,
    sentry_sdk.capture_exception called once."""
    _install_fake_sessionmaker(
        monkeypatch, row=_FakeRow(slack_webhook_url=_FAKE_SLACK_URL)
    )

    respx.post(_FAKE_SLACK_URL).mock(
        side_effect=httpx.ConnectError("boom")
    )

    captured: list[BaseException] = []

    def _fake_capture(exc: BaseException) -> None:
        captured.append(exc)

    with mock.patch.object(
        slack_mod.sentry_sdk, "capture_exception", _fake_capture
    ):
        # MUST NOT RAISE — Phase 8 swallow contract.
        await send_team_slack(
            team_id=_FAKE_TEAM_ID,
            message="anything",
            log_ctx_key="scan_repo",
        )

    assert len(captured) == 1, (
        f"Expected sentry_sdk.capture_exception once, got {len(captured)}"
    )
    assert isinstance(captured[0], httpx.ConnectError)
