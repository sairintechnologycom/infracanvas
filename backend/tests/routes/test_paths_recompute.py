"""Phase 12 D-04 + D-14 — POST /v1/sites/{site_id}/paths/recompute tests.

RED until Plan 12-03 lands the on-demand recompute endpoint.

Asserts:
  * owner-only (member role → 403, owner → 202 + job_id)
  * coalescing: two POSTs within 60s for same site enqueue taskiq only once
"""
from __future__ import annotations

import pytest

pytest.importorskip("app.routes.paths")  # collection RED


@pytest.mark.asyncio
async def test_recompute_owner_only(mock_clerk, dc_site) -> None:  # type: ignore[no-untyped-def]
    """D-14 — member role → 403; owner role → 202 + job_id."""
    pytest.skip("Plan 12-03 to wire require_role('owner') on recompute")
    # member_token = mock_clerk.token_for_team(dc_site.team_id, role="member")
    # owner_token = mock_clerk.token_for_team(dc_site.team_id, role="owner")
    # async with httpx.AsyncClient(app=app, base_url="http://test") as client:
    #     r1 = await client.post(
    #         f"/v1/sites/{dc_site.id}/paths/recompute",
    #         headers={"Authorization": f"Bearer {member_token}"},
    #     )
    #     assert r1.status_code == 403
    #     r2 = await client.post(
    #         f"/v1/sites/{dc_site.id}/paths/recompute",
    #         headers={"Authorization": f"Bearer {owner_token}"},
    #     )
    #     assert r2.status_code == 202
    #     assert "job_id" in r2.json()


@pytest.mark.asyncio
async def test_recompute_coalesces(mock_clerk, dc_site) -> None:  # type: ignore[no-untyped-def]
    """D-04 — two POSTs within 60s for same site → both 202; second has
    coalesced=True; taskiq enqueued only once."""
    pytest.skip("Plan 12-03 to implement coalescing (per-site lock)")
    # token = mock_clerk.token_for_team(dc_site.team_id, role="owner")
    # async with httpx.AsyncClient(app=app, base_url="http://test") as client:
    #     r1 = await client.post(
    #         f"/v1/sites/{dc_site.id}/paths/recompute",
    #         headers={"Authorization": f"Bearer {token}"},
    #     )
    #     r2 = await client.post(
    #         f"/v1/sites/{dc_site.id}/paths/recompute",
    #         headers={"Authorization": f"Bearer {token}"},
    #     )
    # assert r1.status_code == 202
    # assert r2.status_code == 202
    # assert r2.json().get("coalesced") is True
    # assert mock_taskiq_kiq.call_count == 1
