"""Phase 12 D-15 — RLS posture tests for the 5 new path-compute tables.

RED until Plan 12-02 lands migration 012_route_flow_tables (RLS ENABLE+FORCE +
team_id_isolation policy on each of: route_records, netflow_records,
computed_paths, asymmetry_findings, path_divergence_findings).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text  # noqa: F401  (used in skipped impl snippets)

# RED guard — until Plan 12-02 lands ``RouteRecordORM`` (and siblings), no RLS posture
# can be asserted. Skip the whole module at collection so we don't error on the
# ``db_session`` fixture pre-condition.
try:
    from app.db.models import RouteRecordORM  # noqa: F401
except ImportError:
    pytest.skip(
        "Plan 12-02 to land RouteRecordORM + 4 siblings + RLS migration",
        allow_module_level=True,
    )


_TABLES = [
    "route_records",
    "netflow_records",
    "computed_paths",
    "asymmetry_findings",
    "path_divergence_findings",
]


@pytest.mark.asyncio
async def test_route_records_has_rls(db_session) -> None:  # type: ignore[no-untyped-def]
    """D-15 — route_records has rls_enabled=true, rls_forced=true, policy team_id_isolation."""
    pytest.skip("Plan 12-02 to land migration 012_route_flow_tables")
    # row = (await db_session.execute(text(
    #     "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = 'route_records'"
    # ))).one()
    # assert row.relrowsecurity is True
    # assert row.relforcerowsecurity is True
    # policy_count = (await db_session.execute(text(
    #     "SELECT COUNT(*) FROM pg_policies "
    #     "WHERE tablename = 'route_records' AND policyname = 'team_id_isolation'"
    # ))).scalar()
    # assert policy_count == 1


@pytest.mark.asyncio
async def test_netflow_records_has_rls(db_session) -> None:  # type: ignore[no-untyped-def]
    """D-15 — netflow_records RLS ENABLE+FORCE+team_id_isolation policy."""
    pytest.skip("Plan 12-02 to land RLS on netflow_records")


@pytest.mark.asyncio
async def test_computed_paths_has_rls(db_session) -> None:  # type: ignore[no-untyped-def]
    """D-15 — computed_paths RLS ENABLE+FORCE+team_id_isolation policy."""
    pytest.skip("Plan 12-02 to land RLS on computed_paths")


@pytest.mark.asyncio
async def test_asymmetry_findings_has_rls(db_session) -> None:  # type: ignore[no-untyped-def]
    """D-15 — asymmetry_findings RLS ENABLE+FORCE+team_id_isolation policy."""
    pytest.skip("Plan 12-02 to land RLS on asymmetry_findings")


@pytest.mark.asyncio
async def test_path_divergence_findings_has_rls(db_session) -> None:  # type: ignore[no-untyped-def]
    """D-15 — path_divergence_findings RLS ENABLE+FORCE+team_id_isolation policy."""
    pytest.skip("Plan 12-02 to land RLS on path_divergence_findings")
