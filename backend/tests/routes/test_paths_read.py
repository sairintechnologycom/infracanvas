"""Phase 12 D-14 — read API tests for GET /v1/sites/{site_id}/paths +
GET /v1/sites/{site_id}/asymmetries.

RED until Plan 12-03 lands ``app.routes.paths``.

Auth/RLS posture mirrors Phase 11 ``test_routes_firewall_read.py`` verbatim:
  * Clerk JWT required (401 without).
  * Cross-team site_id → 404 ``site_not_found_or_no_access`` (Pattern C).
  * DB probes wrap reads in ``set_config('app.current_team_id', ...)`` (Pattern B).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text  # noqa: F401  (used in skipped implementation snippets)

pytest.importorskip("app.routes.paths")  # collection RED


@pytest.mark.asyncio
async def test_get_paths_returns_200_happy(mock_clerk, dc_site, db_session) -> None:  # type: ignore[no-untyped-def]
    """D-14 — Clerk JWT + valid site_id with 2 computed_paths rows → 200 + list of length 2."""
    pytest.skip("Plan 12-03 to implement GET /v1/sites/{site_id}/paths")
    # seed 2 computed_paths rows for dc_site under set_config('app.current_team_id', ...)
    # async with httpx.AsyncClient(app=app, base_url="http://test") as client:
    #     r = await client.get(
    #         f"/v1/sites/{dc_site.id}/paths",
    #         headers={"Authorization": f"Bearer {mock_clerk.token_for_team(dc_site.team_id)}"},
    #     )
    # assert r.status_code == 200
    # assert len(r.json()["paths"]) == 2


@pytest.mark.asyncio
async def test_get_paths_cross_team_returns_404(mock_clerk, dc_site, db_session) -> None:  # type: ignore[no-untyped-def]
    """Pattern C T-12-CC-1 — site-membership probe FIRST; cross-team site_id
    resolves to None under RLS → 404 ``site_not_found_or_no_access`` (not 403)."""
    pytest.skip("Plan 12-03 to implement Pattern C site-membership probe")
    # other_team_id = uuid4()
    # async with httpx.AsyncClient(app=app, base_url="http://test") as client:
    #     r = await client.get(
    #         f"/v1/sites/{dc_site.id}/paths",
    #         headers={"Authorization": f"Bearer {mock_clerk.token_for_team(other_team_id)}"},
    #     )
    # assert r.status_code == 404
    # assert r.json()["detail"] == "site_not_found_or_no_access"
    # # Pattern B DB probe:
    # async with db_session.begin():
    #     await db_session.execute(text(
    #         "SELECT set_config('app.current_team_id', :t, true)"
    #     ), {"t": str(other_team_id)})


@pytest.mark.asyncio
async def test_get_paths_missing_jwt_returns_401(dc_site) -> None:  # type: ignore[no-untyped-def]
    """D-14 — no Authorization header → 401."""
    pytest.skip("Plan 12-03 to wire Clerk JWT requirement")
    # async with httpx.AsyncClient(app=app, base_url="http://test") as client:
    #     r = await client.get(f"/v1/sites/{dc_site.id}/paths")
    # assert r.status_code == 401


@pytest.mark.asyncio
async def test_asymmetries_filter_by_cause(mock_clerk, dc_site, db_session) -> None:  # type: ignore[no-untyped-def]
    """D-14 — query ``?cause=NAT_ASYMMETRY`` filters response to NAT findings only.

    Pattern B DB probe (commented for downstream impl):
      async with db_session.begin():
          await db_session.execute(text(
              "SELECT set_config('app.current_team_id', :t, true)"
          ), {"t": str(dc_site.team_id)})
    """
    pytest.skip("Plan 12-03 to implement ?cause= filter on asymmetries")
    # seed: 1 NAT_ASYMMETRY + 1 ROUTE_LEAK row
    # async with httpx.AsyncClient(app=app, base_url="http://test") as client:
    #     r = await client.get(
    #         f"/v1/sites/{dc_site.id}/asymmetries?cause=NAT_ASYMMETRY",
    #         headers={"Authorization": f"Bearer {mock_clerk.token_for_team(dc_site.team_id)}"},
    #     )
    # assert r.status_code == 200
    # rows = r.json()["asymmetries"]
    # assert len(rows) == 1
    # assert rows[0]["cause"] == "NAT_ASYMMETRY"
