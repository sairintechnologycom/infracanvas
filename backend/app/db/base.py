"""SQLAlchemy 2.0 declarative base.

Kept separate from models.py so that Alembic's env.py can import `Base` (and
its metadata) without pulling in the actual table definitions directly — the
table modules are then imported explicitly to register themselves on the
metadata object.
"""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
