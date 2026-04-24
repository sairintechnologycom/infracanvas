"""Alembic async migration environment.

Minimal — imports ONLY the SQLAlchemy metadata (via app.db.base + app.db.models)
and NOT any FastAPI/Sentry/app.main modules. This keeps `alembic upgrade head`
safe to run as a Railway/Fly release_command where the web app itself is not
booted (RESEARCH § P4 lines 1155-1157).

Reads DATABASE_URL_MIGRATOR if set (owner role), else falls back to DATABASE_URL.
"""
from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.db.base import Base
from app.db import models  # noqa: F401 — register tables on Base.metadata

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

url = os.environ.get("DATABASE_URL_MIGRATOR") or os.environ["DATABASE_URL"]
config.set_main_option("sqlalchemy.url", url)

target_metadata = Base.metadata


def do_run_migrations(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as conn:
        await conn.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    raise RuntimeError("Offline mode not supported — use --sql on a sync engine if needed.")
else:
    run_migrations_online()
