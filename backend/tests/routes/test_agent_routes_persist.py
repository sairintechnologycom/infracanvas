"""Phase 12 Blocker-1 regression — POST /v1/agent/routes + /v1/agent/flows
must persist rows under RLS.

RED until Plan 12-02 lands the route_records + netflow_records tables and
the ingest handlers' persistence logic.

Pattern B DB probe applied: SELECT set_config('app.current_team_id', ...) is
run BEFORE any SQL probe (mirrors test_routes_firewall.py:109-119).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text  # noqa: F401  (used in skipped impl snippets)

# RED guard — until Plan 12-02 lands ``RouteRecordORM`` + ``NetFlowRecordORM``,
# the persistence assertions cannot run. Skip whole module at collection so we
# don't error on ``db_session`` fixture pre-conditions either.
try:
    from app.db.models import NetFlowRecordORM, RouteRecordORM  # noqa: F401
except ImportError:
    pytest.skip(
        "Plan 12-02 to land RouteRecordORM + NetFlowRecordORM",
        allow_module_level=True,
    )


@pytest.mark.asyncio
async def test_push_routes_persists(dc_site, dc_site_token, db_session) -> None:  # type: ignore[no-untyped-def]
    """Blocker 1 regression: POST /v1/agent/routes with valid site-token +
    3 routes → 202; SQL probe of route_records returns 3 rows for
    (site_id, device_host).

    Pattern B (mirrors test_routes_firewall.py:109-119):
        async with db_session.begin():
            await db_session.execute(text(
                "SELECT set_config('app.current_team_id', :t, true)"
            ), {"t": str(dc_site.team_id)})
            count = (await db_session.execute(text(
                "SELECT COUNT(*) FROM route_records WHERE site_id = :s"
            ), {"s": str(dc_site.id)})).scalar()
    """
    pytest.skip("Plan 12-02 to land route_records table + persistence")
    # payload = {"device_host": "router-1", "routes": [
    #     mk_route_record("10.1.0.0/16", "192.168.1.1"),
    #     mk_route_record("10.2.0.0/16", "192.168.1.2"),
    #     mk_route_record("10.3.0.0/16", "192.168.1.3"),
    # ]}
    # async with httpx.AsyncClient(app=app, base_url="http://test") as client:
    #     r = await client.post(
    #         "/v1/agent/routes",
    #         json=payload,
    #         headers={"Authorization": f"Bearer {dc_site_token}"},
    #     )
    # assert r.status_code == 202
    # async with db_session.begin():
    #     await db_session.execute(text(
    #         "SELECT set_config('app.current_team_id', :t, true)"
    #     ), {"t": str(dc_site.team_id)})
    #     count = (await db_session.execute(text(
    #         "SELECT COUNT(*) FROM route_records "
    #         "WHERE site_id = :s AND device_host = :h"
    #     ), {"s": str(dc_site.id), "h": "router-1"})).scalar()
    # assert count == 3


@pytest.mark.asyncio
async def test_push_flows_persists(dc_site, dc_site_token, db_session) -> None:  # type: ignore[no-untyped-def]
    """Blocker 1 regression: POST /v1/agent/flows with 5 flows → 202;
    SQL probe of netflow_records returns 5 rows (Pattern B applied).

    Pattern B (mirrors test_routes_firewall.py:109-119):
        async with db_session.begin():
            await db_session.execute(text(
                "SELECT set_config('app.current_team_id', :t, true)"
            ), {"t": str(dc_site.team_id)})
            count = (await db_session.execute(text(
                "SELECT COUNT(*) FROM netflow_records WHERE site_id = :s"
            ), {"s": str(dc_site.id)})).scalar()
    """
    pytest.skip("Plan 12-02 to land netflow_records table + persistence")
    # payload = {"flows": [mk_flow("10.1.0.5", "10.2.0.5") for _ in range(5)]}
    # async with httpx.AsyncClient(app=app, base_url="http://test") as client:
    #     r = await client.post(
    #         "/v1/agent/flows",
    #         json=payload,
    #         headers={"Authorization": f"Bearer {dc_site_token}"},
    #     )
    # assert r.status_code == 202
    # async with db_session.begin():
    #     await db_session.execute(text(
    #         "SELECT set_config('app.current_team_id', :t, true)"
    #     ), {"t": str(dc_site.team_id)})
    #     count = (await db_session.execute(text(
    #         "SELECT COUNT(*) FROM netflow_records WHERE site_id = :s"
    #     ), {"s": str(dc_site.id)})).scalar()
    # assert count == 5
