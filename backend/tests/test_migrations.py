"""Alembic migration round-trip tests.

Uses the `pg_container` fixture from Plan 06-01's conftest.py to get a
Testcontainers Postgres with the BYPASSRLS test role pre-created. Runs
alembic up/down against the raw container URL (NOT Neon pooler) because
DDL commands need a direct connection.
"""
from __future__ import annotations

import os
import subprocess

import pytest

pytestmark = pytest.mark.rls  # shares Testcontainers dep chain


def _run_alembic(container_url: str, cmd: list[str]) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "DATABASE_URL": container_url,
        "DATABASE_URL_MIGRATOR": container_url,
    }
    return subprocess.run(
        ["alembic", *cmd],
        cwd="backend",
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def test_upgrade_to_head_clean(pg_container) -> None:  # type: ignore[no-untyped-def]
    """MIG-001: fresh database → alembic upgrade head succeeds."""
    url = pg_container.get_connection_url().replace(
        "postgresql+psycopg2", "postgresql+asyncpg"
    )
    _run_alembic(url, ["downgrade", "base"])
    _run_alembic(url, ["upgrade", "head"])  # must not raise


def test_downgrade_roundtrip(pg_container) -> None:  # type: ignore[no-untyped-def]
    """MIG-002: upgrade head → downgrade base → upgrade head is idempotent and clean."""
    url = pg_container.get_connection_url().replace(
        "postgresql+psycopg2", "postgresql+asyncpg"
    )
    _run_alembic(url, ["upgrade", "head"])
    _run_alembic(url, ["downgrade", "base"])
    _run_alembic(url, ["upgrade", "head"])  # must not raise
