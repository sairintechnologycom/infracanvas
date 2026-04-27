"""Centralized Sentry initialization for the API and worker processes.

OBS-02 final wiring (Phase 6 Plan 06-07).

Single Sentry project — discriminated by the ``process_role`` tag (per
RESEARCH § F10 discretion recommendation: one project, two tags). The
``api`` and ``worker`` processes call :func:`init_sentry` once each at
startup; the SDK then auto-instruments FastAPI + Starlette + asyncpg via
the integration list. Logging is wired with ``level=None,
event_level=None`` because structlog (Plan 02) owns log emission and we
explicitly do NOT want arbitrary log strings captured as Sentry events
(T-06-08c mitigation — keeps PII out of Sentry).

The function is idempotent (guarded by a module-level flag) and a no-op
when ``settings.sentry_dsn`` is unset, so dev-local pytest / uvicorn runs
work without DSN configuration.

team_id / user_id / clerk_org_id / request_id tags are NOT set here — the
auth dep (:func:`app.auth.clerk.require_principal`) and
:class:`app.obs.middleware.RequestContextMiddleware` already bind them on
every request. This module only sets the process-level ``process_role``
tag so all events from a given process carry it.
"""

from __future__ import annotations

import sentry_sdk
from sentry_sdk.integrations.asyncpg import AsyncPGIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from app.settings import settings

_initialized = False


def init_sentry(role: str = "api") -> None:
    """Idempotent Sentry SDK initialization.

    Args:
        role: ``"api"`` or ``"worker"`` — set as the ``process_role`` tag
            on every event so a single Sentry project can serve both
            processes (per RESEARCH § F10).

    Behavior:
        * No-op when ``settings.sentry_dsn`` is falsy (dev-local).
        * Idempotent — second call does NOT re-init the SDK; it only
          updates the ``process_role`` tag (cheap rebind).
        * ``send_default_pii=False`` + ``LoggingIntegration(level=None,
          event_level=None)`` — structlog owns log emission; Sentry
          captures only exceptions and explicit ``capture_*`` calls.
        * Sample rates: ``traces_sample_rate=0.1``,
          ``profiles_sample_rate=0.1`` (D-20).
    """
    global _initialized
    if _initialized:
        # Cheap rebind — useful in tests and on a hypothetical re-fork
        # where the role differs from a prior init in the same process.
        sentry_sdk.set_tag("process_role", role)
        return
    if not settings.sentry_dsn:
        # Dev-local: mark as initialized so a follow-up call is also a
        # no-op (avoids re-walking the falsy branch on every request).
        _initialized = True
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.env,
        release=settings.git_sha,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        send_default_pii=False,  # we attach user via set_user manually
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
            AsyncPGIntegration(),
            # structlog owns logs; do NOT capture log strings as events.
            LoggingIntegration(level=None, event_level=None),
        ],
    )
    sentry_sdk.set_tag("process_role", role)
    _initialized = True
