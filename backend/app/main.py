"""FastAPI app factory + lifespan.

``RequestContextMiddleware`` is registered as the OUTERMOST middleware (first
``add_middleware`` call) so every subsequent middleware and every route
handler runs inside its ``request_id`` contextvar. Clerk auth (Plan 04)
plugs in as a FastAPI ``Depends(...)`` inside this middleware, NOT as
another middleware layer.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.obs.logging import configure_logging
from app.obs.middleware import RequestContextMiddleware
from app.obs.sentry import init_sentry
from app.routes import agent as agent_routes
from app.routes import firewalls as firewalls_routes
from app.routes import github as github_routes
from app.routes import health, scans_from_github
from app.routes import integrations as integrations_routes
from app.routes import paths as paths_routes  # Phase 12 D-14
from app.routes import scans as scan_routes
from app.routes import share as share_routes
from app.routes import webhooks as wh_routes

configure_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """App lifespan — Sentry init (Plan 06-07) and DB engine (Plan 03) attach here."""
    init_sentry(role="api")
    yield


def create_app() -> FastAPI:
    """Build the FastAPI app. Factory shape keeps uvicorn and pytest symmetric."""
    app = FastAPI(title="InfraCanvas Backend", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestContextMiddleware)  # outermost
    app.include_router(health.router)
    app.include_router(wh_routes.router)
    app.include_router(scan_routes.router)
    app.include_router(share_routes.router, prefix="/v1")
    app.include_router(github_routes.router)
    app.include_router(scans_from_github.router)
    app.include_router(integrations_routes.router)
    app.include_router(agent_routes.router)
    app.include_router(firewalls_routes.router)
    app.include_router(paths_routes.router)
    return app


app = create_app()
