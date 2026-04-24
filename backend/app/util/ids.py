"""UUIDv7 factory — stdlib-compatible wrapper over uuid_utils."""

from __future__ import annotations

import uuid

from uuid_utils.compat import uuid7


def new_uuid7() -> uuid.UUID:
    """Generate a UUIDv7 (lexically chronological).

    Returns stdlib ``uuid.UUID`` for SQLAlchemy ``PgUUID`` column compatibility
    (RESEARCH § P9). ``uuid_utils.compat.uuid7`` returns a stdlib ``uuid.UUID``
    so it slots directly into the type system without coercion.
    """
    return uuid7()
