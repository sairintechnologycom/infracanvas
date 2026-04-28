"""Row-level security integration tests.

These tests require Testcontainers Postgres (marker: rls).
They validate the D-05 contract: infracanvas_app cannot read or write
across teams, even with direct SQL — RLS is the enforcement boundary.

Fixtures `seed_session` (BYPASSRLS test role) and `app_session`
(infracanvas_app NOBYPASSRLS role) are provided by backend/tests/conftest.py
(Plan 06-01). `new_uuid7` is the UUIDv7 helper from Plan 06-01.
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
import sqlalchemy.exc
from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Scan, ScanStatus, Team
from app.util.ids import new_uuid7

pytestmark = pytest.mark.rls


@pytest_asyncio.fixture
async def two_teams(seed_session: AsyncSession) -> tuple[Team, Team]:
    """Create team A + team B via seed_session (BYPASSRLS role)."""
    team_a = Team(
        id=new_uuid7(),
        clerk_org_id=f"org_a_{uuid.uuid4().hex[:8]}",
        name="Team A",
    )
    team_b = Team(
        id=new_uuid7(),
        clerk_org_id=f"org_b_{uuid.uuid4().hex[:8]}",
        name="Team B",
    )
    seed_session.add_all([team_a, team_b])
    # Flush teams first so the FK target rows exist before the scan INSERT.
    # Without this, asyncpg sees the scan INSERT before the teams INSERT and
    # raises ForeignKeyViolationError.
    await seed_session.flush()
    scan_a = Scan(
        id=new_uuid7(),
        team_id=team_a.id,
        r2_key=f"teams/{team_a.id}/scans/1.json",
        size_bytes=1024,
        status=ScanStatus.ready,
    )
    seed_session.add(scan_a)
    # Commit (not just flush) so a *separate* connection — the app_session
    # engine running as the NOBYPASSRLS infracanvas_app role — can see the
    # seed rows. flush() only writes to the open transaction.
    await seed_session.commit()
    return team_a, team_b


async def test_rls_cross_team_scans_blocked(
    two_teams: tuple[Team, Team], app_session: AsyncSession
) -> None:
    """RLS-001: infracanvas_app with SET LOCAL team_B returns 0 rows for team_A's scans."""
    _team_a, team_b = two_teams
    async with app_session.begin():
        await app_session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team_b.id)},
        )
        result = await app_session.execute(text("SELECT count(*) FROM scans"))
        count = result.scalar_one()
        assert count == 0, (
            f"Expected 0 team-B-visible scans, got {count} (RLS leaked team-A row)"
        )


async def test_rls_same_team_scans_visible(
    two_teams: tuple[Team, Team], app_session: AsyncSession
) -> None:
    """RLS-002: infracanvas_app with SET LOCAL team_A returns team_A's rows (positive control)."""
    team_a, _team_b = two_teams
    async with app_session.begin():
        await app_session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team_a.id)},
        )
        result = await app_session.execute(text("SELECT count(*) FROM scans"))
        assert result.scalar_one() == 1


async def test_rls_cross_team_teams_blocked(
    two_teams: tuple[Team, Team], app_session: AsyncSession
) -> None:
    """RLS-003: teams table itself is RLS-scoped — team_B context sees only team_B row."""
    _team_a, team_b = two_teams
    async with app_session.begin():
        await app_session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team_b.id)},
        )
        result = await app_session.execute(text("SELECT id FROM teams"))
        rows = result.fetchall()
        assert len(rows) == 1 and rows[0][0] == team_b.id


async def test_rls_no_context_returns_zero(
    two_teams: tuple[Team, Team], app_session: AsyncSession
) -> None:
    """RLS-004: with no SET LOCAL (current_setting returns NULL), policy matches zero rows."""
    async with app_session.begin():
        # DO NOT SET LOCAL — verifies the `true` in current_setting doesn't crash the query
        result = await app_session.execute(text("SELECT count(*) FROM scans"))
        assert result.scalar_one() == 0


async def test_rls_insert_with_wrong_team_id_blocked(
    two_teams: tuple[Team, Team], app_session: AsyncSession
) -> None:
    """RLS-005: INSERT of a scan with team_id != current context → policy WITH CHECK violation."""
    team_a, team_b = two_teams
    async with app_session.begin():
        await app_session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team_b.id)},
        )
        # RLS WITH CHECK violation surfaces as InsufficientPrivilegeError
        # (SQLSTATE 42501), which SQLAlchemy maps to ProgrammingError — NOT
        # IntegrityError. We accept either DBAPIError subclass to stay
        # tolerant of future driver wrapping changes.
        with pytest.raises((sqlalchemy.exc.ProgrammingError, sqlalchemy.exc.IntegrityError)):
            await app_session.execute(
                insert(Scan).values(
                    id=new_uuid7(),
                    team_id=team_a.id,  # wrong team!
                    r2_key="teams/attack/scans/1.json",
                    status=ScanStatus.ready,
                )
            )
