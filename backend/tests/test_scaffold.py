"""Scaffold smoke test — ensures backend/app package is importable.

Runs in Wave 0 before any real code lands; guarantees the package layout is
sane and conftest.py imports do not explode.
"""
from __future__ import annotations


def test_scaffold_is_importable() -> None:
    """SCAFFOLD-001: backend/app package imports cleanly."""
    import app  # noqa: F401
