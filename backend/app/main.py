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
from app.routes import health
from app.routes import webhooks as wh_routes

configure_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """App lifespan — later plans wire Sentry init (07) and DB engine (03) here."""
    yield


def create_app() -> FastAPI:
    """Build the FastAPI app. Factory shape keeps uvicorn and pytest symmetric."""
    app = FastAPI(title="InfraCanvas Backend", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestContextMiddleware)  # outermost
    app.include_router(health.router)
    app.include_router(wh_routes.router)
    return app


app = create_app()
