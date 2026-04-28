"""Tests for app.settings env parsing."""
from __future__ import annotations

import pytest

from app.settings import Settings


REQUIRED_ENV: dict[str, str] = {
    "CLERK_ISSUER": "https://test.clerk.invalid",
    "CLERK_JWKS_URL": "https://test.clerk.invalid/.well-known/jwks.json",
    "CLERK_WEBHOOK_SECRET": "whsec_test",
    "DATABASE_URL": "postgresql+asyncpg://u:p@h/db",
    "R2_ACCOUNT_ID": "a",
    "R2_ACCESS_KEY_ID": "k",
    "R2_SECRET_ACCESS_KEY": "s",
    "R2_BUCKET": "b",
    "REDIS_URL": "redis://localhost:6379/0",
    "STRIPE_SECRET_KEY": "sk_test_x",
}


def _apply(monkeypatch: pytest.MonkeyPatch, **overrides: str) -> None:
    # Drop the conftest-stamped JSON list so the per-case origin string wins.
    monkeypatch.delenv("CLERK_ALLOWED_ORIGINS", raising=False)
    for key, value in {**REQUIRED_ENV, **overrides}.items():
        monkeypatch.setenv(key, value)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("http://localhost:3000", ["http://localhost:3000"]),
        (
            "http://localhost:3000,https://app.infracanvas.dev",
            ["http://localhost:3000", "https://app.infracanvas.dev"],
        ),
        ("  a , b ,c  ", ["a", "b", "c"]),
        ('["http://localhost:3000"]', ["http://localhost:3000"]),
    ],
)
def test_clerk_allowed_origins_accepts_csv_and_json(
    monkeypatch: pytest.MonkeyPatch, raw: str, expected: list[str]
) -> None:
    """CLERK_ALLOWED_ORIGINS must accept comma-separated AND JSON-array env values.

    Regression: pydantic-settings JSON-decodes ``list[str]`` env values before
    ``mode='before'`` validators run, so a plain CSV string raised SettingsError.
    """
    _apply(monkeypatch, CLERK_ALLOWED_ORIGINS=raw)
    s = Settings()  # type: ignore[call-arg]
    assert s.clerk_allowed_origins == expected
