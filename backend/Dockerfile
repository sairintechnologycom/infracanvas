# syntax=docker/dockerfile:1.7
# InfraCanvas backend (Phase 6, Plan 06-08).
#
# Build context expectation: repo root (so cli/ and backend/ are siblings).
# Build invocation:
#   docker build -f backend/Dockerfile -t infracanvas-backend .
#   flyctl deploy -c fly.dev.toml         # Fly resolves dockerfile = "backend/Dockerfile" with repo-root context.
#
# Path-dep rationale (RESEARCH § F6, CONTEXT D-16): backend/pyproject.toml declares
# `infracanvas @ file:../cli`, so the cli/ tree must be present alongside backend/
# at build time. We COPY cli/ to /cli first, install it, then install backend/.

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        ca-certificates \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy cli/ first so the `infracanvas @ file:../cli` path-dep in
# backend/pyproject.toml resolves before we install backend/.
COPY cli /cli
COPY backend /app

RUN pip install --upgrade pip \
    && pip install /cli \
    && pip install -e /app

# Default smoke command. Fly's [processes] api/worker entries override this in
# practice (RESEARCH § F11); kept here so `docker run` boots a usable API.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
