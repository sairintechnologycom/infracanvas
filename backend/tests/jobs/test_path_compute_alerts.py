"""Phase 12 NFN-02 — path-compute alert fan-out tests.

RED until Plan 12-06 wires the path-compute job into the Phase 8 Slack dispatcher.
"""
from __future__ import annotations

import pytest

pytest.importorskip("app.queue.tasks.path_compute")  # collection RED


@pytest.mark.asyncio
async def test_fires_on_new() -> None:
    """NFN-02: new asymmetry_finding with impact_firewall_count >= 1 →
    send_team_slack called once with payload containing 'Asymmetric path detected'.
    """
    pytest.skip("Plan 12-06 to wire NFN-02 alert dispatch on new findings")
    # finding = _mk_asymmetry_finding(impact_firewall_count=2)
    # await recompute_paths_for_site(site_id, on_demand=False)
    # assert mock_send_team_slack.call_count == 1
    # payload = mock_send_team_slack.call_args.kwargs["message"]
    # assert "Asymmetric path detected" in payload


@pytest.mark.asyncio
async def test_no_fire_when_unchanged() -> None:
    """NFN-02: finding present in 2 consecutive recomputes without cause change →
    send_team_slack called 0 times on the second run (debounce by transition)."""
    pytest.skip("Plan 12-06 to debounce alerts on unchanged findings")
    # await recompute_paths_for_site(site_id, on_demand=False)  # t1
    # mock_send_team_slack.reset_mock()
    # await recompute_paths_for_site(site_id, on_demand=False)  # t2 same finding
    # assert mock_send_team_slack.call_count == 0


@pytest.mark.asyncio
async def test_slack_failure_swallowed() -> None:
    """NFN-02: Slack POST raises → job completes successfully and
    ``sentry_sdk.capture_exception`` is called once."""
    pytest.skip("Plan 12-06 to swallow Slack failures (Phase 8 dispatcher pattern)")
    # mock_send_team_slack.side_effect = ConnectionError("boom")
    # # Should not raise — alert failure must NOT fail the recompute job
    # await recompute_paths_for_site(site_id, on_demand=False)
    # assert mock_sentry_capture.call_count == 1
