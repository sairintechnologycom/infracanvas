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


# ---------------------------------------------------------------------------
# Phase 7.5 (GH-01..GH-04, D-06/D-15): GitHub App settings fields.
# Defaults must be empty strings so the test env doesn't crash on import
# and Phase 7.5 can land before real Fly secrets are provisioned.
# ---------------------------------------------------------------------------


def test_github_app_fields_have_safe_empty_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GitHub App settings fields exist on Settings with empty-string defaults.

    Without GITHUB_APP_* env vars set, the four fields must default to "" so
    importing app.settings doesn't fail in environments that haven't yet
    provisioned the GitHub App secrets (e.g., dev before App registration).
    """
    _apply(monkeypatch, CLERK_ALLOWED_ORIGINS="http://localhost:3000")
    # Drop any test-env stubs so we exercise the true defaults.
    for var in (
        "GITHUB_APP_ID",
        "GITHUB_APP_PRIVATE_KEY",
        "GITHUB_APP_WEBHOOK_SECRET",
        "GITHUB_APP_SLUG",
    ):
        monkeypatch.delenv(var, raising=False)

    s = Settings()  # type: ignore[call-arg]
    assert hasattr(s, "github_app_id")
    assert hasattr(s, "github_app_private_key")
    assert hasattr(s, "github_app_webhook_secret")
    assert hasattr(s, "github_app_slug")
    assert s.github_app_id == ""
    assert s.github_app_private_key == ""
    assert s.github_app_webhook_secret == ""
    assert s.github_app_slug == ""


def test_github_app_fields_read_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """When GITHUB_APP_* env vars are set, Settings picks them up."""
    _apply(
        monkeypatch,
        CLERK_ALLOWED_ORIGINS="http://localhost:3000",
        GITHUB_APP_ID="98765",
        GITHUB_APP_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nfake\n-----END PRIVATE KEY-----",
        GITHUB_APP_WEBHOOK_SECRET="whsec_gh_abc",
        GITHUB_APP_SLUG="infracanvas-test",
    )
    s = Settings()  # type: ignore[call-arg]
    assert s.github_app_id == "98765"
    assert "BEGIN PRIVATE KEY" in s.github_app_private_key
    assert s.github_app_webhook_secret == "whsec_gh_abc"
    assert s.github_app_slug == "infracanvas-test"


def test_conftest_stubs_provide_github_app_defaults() -> None:
    """The repo-wide conftest env-stub block must seed GITHUB_APP_* so any
    test that imports app.settings.settings (the module-level singleton)
    sees safe values.

    Without this, every existing test would have to monkeypatch the GitHub
    App env vars, which we explicitly want to avoid.
    """
    from app.settings import settings as live_settings

    # The conftest stub sets GITHUB_APP_ID="12345"; PRIVATE_KEY remains "".
    assert live_settings.github_app_id == "12345"
    assert live_settings.github_app_webhook_secret == "test-webhook-secret"
    assert live_settings.github_app_slug == "infracanvas-dev"
