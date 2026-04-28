"""Thin bcrypt wrapper for token and password hashing.

Uses run_in_threadpool at the call site (routes) to avoid blocking the
event loop — bcrypt is CPU-bound. These functions are synchronous by design.
"""
from __future__ import annotations

import bcrypt

_BCRYPT_COST = 12


def hash_value(value: str) -> str:
    """Hash a string value with bcrypt cost 12. Returns the hash as a str."""
    return bcrypt.hashpw(value.encode(), bcrypt.gensalt(rounds=_BCRYPT_COST)).decode()


def verify_value(value: str, hashed: str) -> bool:
    """Verify a plaintext value against a bcrypt hash.

    Uses a constant-time comparison (bcrypt.checkpw) to mitigate timing attacks.
    If the hash is empty or invalid, returns False (never raises).
    """
    try:
        return bcrypt.checkpw(value.encode(), hashed.encode())
    except Exception:
        return False
