"""Phase 12 D-15 — RLS posture tests for the 5 new path-compute tables.

Plan 12-02 landed migration 012_route_flow_tables + 013_path_compute_tables,
which apply ENABLE + FORCE ROW LEVEL SECURITY + <table>_team_isolation
policy on each of: route_records, netflow_records, computed_paths,
asymmetry_findings, path_divergence_findings.

The probes use ``seed_session`` (BYPASSRLS role) because pg_class /
pg_policies are catalog tables — RLS doesn't apply, and we want the
admin view of policy posture, not the team-scoped one.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# RED→GREEN guard — module-level import probe stays in place so the module
# auto-skips if a future revert removes the ORMs.
try:
    from app.db.models import (  # noqa: F401
        AsymmetryFindingORM,
        ComputedPathORM,
        NetFlowRecordORM,
        PathDivergenceFindingORM,
        RouteRecordORM,
    )
except ImportError:
    pytest.skip(
        "Plan 12-02 to land RouteRecordORM + 4 siblings + RLS migration",
        allow_module_level=True,
    )

pytestmark = pytest.mark.rls


async def _assert_rls_posture(
    session: AsyncSession, table: str, policy: str
) -> None:
    """Assert ENABLE + FORCE ROW LEVEL SECURITY + named policy exists."""
    row = (
        await session.execute(
            text(
                "SELECT relrowsecurity, relforcerowsecurity "
                "FROM pg_class WHERE relname = :t"
            ),
            {"t": table},
        )
    ).one()
    assert row.relrowsecurity is True, f"{table}.relrowsecurity must be true"
    assert row.relforcerowsecurity is True, f"{table}.relforcerowsecurity must be true"
    policy_count = (
        await session.execute(
            text(
                "SELECT COUNT(*) FROM pg_policies "
                "WHERE tablename = :t AND policyname = :p"
            ),
            {"t": table, "p": policy},
        )
    ).scalar()
    assert policy_count == 1, (
        f"{table} must have exactly one '{policy}' policy "
        f"(found {policy_count})"
    )


async def test_route_records_has_rls(seed_session: AsyncSession) -> None:
    """D-15 — route_records has rls_enabled=true, rls_forced=true, policy route_records_team_isolation."""
    await _assert_rls_posture(
        seed_session, "route_records", "route_records_team_isolation"
    )


async def test_netflow_records_has_rls(seed_session: AsyncSession) -> None:
    """D-15 — netflow_records RLS ENABLE+FORCE+netflow_records_team_isolation policy."""
    await _assert_rls_posture(
        seed_session, "netflow_records", "netflow_records_team_isolation"
    )


async def test_computed_paths_has_rls(seed_session: AsyncSession) -> None:
    """D-15 — computed_paths RLS ENABLE+FORCE+computed_paths_team_isolation policy."""
    await _assert_rls_posture(
        seed_session, "computed_paths", "computed_paths_team_isolation"
    )


async def test_asymmetry_findings_has_rls(seed_session: AsyncSession) -> None:
    """D-15 — asymmetry_findings RLS ENABLE+FORCE+asymmetry_findings_team_isolation policy."""
    await _assert_rls_posture(
        seed_session, "asymmetry_findings", "asymmetry_findings_team_isolation"
    )


async def test_path_divergence_findings_has_rls(seed_session: AsyncSession) -> None:
    """D-15 — path_divergence_findings RLS ENABLE+FORCE+path_divergence_findings_team_isolation policy."""
    await _assert_rls_posture(
        seed_session,
        "path_divergence_findings",
        "path_divergence_findings_team_isolation",
    )
