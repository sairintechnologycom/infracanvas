"""Async SQLAlchemy engine + session factory + team_scoped_session FastAPI dep.

`team_scoped_session` is the single canonical entry point for team-scoped
database access from FastAPI handlers. It opens a transaction, SETs the
`app.current_team_id` GUC via `SET LOCAL` as the FIRST statement inside the
tx, and yields the session. RLS policies in migration 002 then evaluate
`current_setting('app.current_team_id', true)::uuid` against the caller's
team id on every row read/write — cross-team access is impossible.

Research callout #1 (Neon pooler): Neon offers only transaction-mode
pooling. `SET LOCAL` is scoped to BEGIN...COMMIT, so the pool-checkout unit
(the tx) and the GUC scope align. No cross-tenant leakage via pooled
connections.

Pool sizing: `pool_size=5`, `max_overflow=10` → max 15 connections per app
instance. Neon's free-tier limit is well above this, and Railway
single-instance deploys keep us under any per-project cap. Pre-ping enabled
because long-lived connections to Neon occasionally get recycled server-side.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.settings import settings

if TYPE_CHECKING:
    from app.db.models import Team

_engine: AsyncEngine | None = None
_Session: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Lazily construct the async engine + sessionmaker on first use."""
    global _engine, _Session
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            echo=False,
        )
        _Session = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    if _Session is None:
        get_engine()
    assert _Session is not None
    return _Session


async def raw_session() -> AsyncIterator[AsyncSession]:
    """No-RLS-context session — use for unauth endpoints (health, webhooks)
    and admin/migration paths where team scoping does not apply. RLS policies
    will still deny access to team-scoped tables unless the caller holds a
    BYPASSRLS role, so this is safe by default."""
    async with get_sessionmaker()() as session:
        async with session.begin():
            yield session


async def team_scoped_session(
    team: "Team",
) -> AsyncIterator[AsyncSession]:
    """FastAPI dep: opens a tx and executes
        SET LOCAL app.current_team_id = '<team.id>'
    as the first statement so RLS policies evaluate against it. Uses a
    bind parameter (never f-string interpolation — RESEARCH F3 Pitfalls).

    Plan 04 will compose this with `Depends(resolve_team_from_clerk_org)`
    to inject the Team; for now callers pass it directly.
    """
    async with get_sessionmaker()() as session:
        async with session.begin():
            await session.execute(
                text("SET LOCAL app.current_team_id = :t"),
                {"t": str(team.id)},
            )
            yield session
