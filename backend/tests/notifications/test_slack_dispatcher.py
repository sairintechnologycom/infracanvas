"""Phase 12 NFN-02 — Phase 8 Slack dispatcher reuse tests.

RED until Plan 12-06 surfaces ``app.notifications.slack.send_team_slack``
(may be re-exported from the existing Phase 8 dispatcher).

Synthetic webhook URL only (T-12-01-03 mitigation — never a real workspace URL).
"""
from __future__ import annotations

import pytest

pytest.importorskip("app.notifications.slack")  # collection RED


_FAKE_SLACK_URL = "https://hooks.slack.com/test"  # T-12-01-03 synthetic only


@pytest.mark.asyncio
async def test_send_team_slack_posts_to_team_url() -> None:
    """NFN-02: team with slack_webhook_url=<synthetic> → send_team_slack POSTs
    JSON with ``text=message`` to that URL."""
    pytest.skip("Plan 12-06 to wire send_team_slack against Phase 8 dispatcher")
    # team = _mk_team(slack_webhook_url=_FAKE_SLACK_URL)
    # respx_router = respx.mock(base_url=_FAKE_SLACK_URL)
    # route = respx_router.post("").mock(return_value=Response(200, json={"ok": True}))
    # await send_team_slack(team, message="Asymmetric path detected")
    # assert route.called
    # body = json.loads(route.calls[0].request.content)
    # assert body["text"] == "Asymmetric path detected"


@pytest.mark.asyncio
async def test_send_team_slack_no_url_no_op() -> None:
    """NFN-02: team with slack_webhook_url=None → no HTTP call, returns None."""
    pytest.skip("Plan 12-06 to no-op when team has no webhook URL")
    # team = _mk_team(slack_webhook_url=None)
    # result = await send_team_slack(team, message="anything")
    # assert result is None
    # # respx asserts no calls made


@pytest.mark.asyncio
async def test_send_team_slack_failure_swallowed() -> None:
    """NFN-02: httpx raises ConnectionError → no exception escapes,
    sentry_sdk.capture_exception called once."""
    pytest.skip("Plan 12-06 to swallow Slack failures (Phase 8 pattern)")
    # team = _mk_team(slack_webhook_url=_FAKE_SLACK_URL)
    # respx_router.post("").mock(side_effect=ConnectionError("boom"))
    # # MUST NOT RAISE
    # await send_team_slack(team, message="anything")
    # assert mock_sentry_capture.call_count == 1
