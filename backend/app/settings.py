"""Application settings — pydantic-settings BaseSettings reading env vars.

Fails loud at module import if any required env var is missing. No graceful
defaults for secrets / URLs — per PATTERNS.md, backend env must be complete
at startup.
"""

from __future__ import annotations

import json
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    env: str = "dev"
    clerk_issuer: str
    clerk_jwks_url: str
    # ``NoDecode`` opts out of pydantic-settings' eager JSON decoding for complex
    # env values, so the validator below sees the raw string and can split CSV.
    clerk_allowed_origins: Annotated[list[str], NoDecode]
    clerk_webhook_secret: str
    database_url: str
    database_url_migrator: str | None = None
    r2_account_id: str
    r2_access_key_id: str
    r2_secret_access_key: str
    r2_bucket: str
    redis_url: str
    stripe_secret_key: str
    stripe_meter_event_name: str = "infracanvas.scan"
    sentry_dsn: str | None = None
    git_sha: str = "unknown"

    @field_validator("clerk_allowed_origins", mode="before")
    @classmethod
    def _split_csv(cls, v: object) -> object:
        """Accept ``CLERK_ALLOWED_ORIGINS`` as CSV or JSON-array from env."""
        if isinstance(v, str):
            stripped = v.strip()
            if stripped.startswith("["):
                return json.loads(stripped)
            return [s.strip() for s in stripped.split(",") if s.strip()]
        return v


settings = Settings()  # type: ignore[call-arg]  # module-level singleton; fails fast if any required env missing
