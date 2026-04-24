"""Liveness + readiness endpoints.

- ``GET /healthz`` — process is running; returns git SHA for deploy tracing.
- ``GET /readyz`` — app lifespan startup completed (Phase 6 uses a trivial
  body; later plans may probe DB/Redis).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.settings import settings

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "git_sha": settings.git_sha}


@router.get("/readyz")
async def readyz() -> dict[str, str]:
    # Phase 6 readyz is trivial; later plans may add DB/Redis probes.
    return {"status": "ready"}
