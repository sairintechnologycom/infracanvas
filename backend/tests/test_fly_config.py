"""DEPLOY-* tests: Fly.io config invariants + Dockerfile shape."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent


def test_fly_dev_toml_passes_validator() -> None:
    """DEPLOY-001: backend/fly.dev.toml satisfies invariants."""
    r = subprocess.run(
        [sys.executable, "-m", "scripts.validate_fly_toml", "fly.dev.toml"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, f"stdout={r.stdout!r} stderr={r.stderr!r}"


def test_fly_prod_toml_passes_validator() -> None:
    """DEPLOY-002: backend/fly.prod.toml satisfies invariants."""
    r = subprocess.run(
        [sys.executable, "-m", "scripts.validate_fly_toml", "fly.prod.toml"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, f"stdout={r.stdout!r} stderr={r.stderr!r}"


def test_dockerfile_copies_cli_and_backend() -> None:
    """DEPLOY-003: Dockerfile copies both cli and backend so infracanvas path-dep resolves.

    Without `COPY cli /cli`, `pip install -e /app` fails because backend's
    pyproject.toml has `infracanvas @ file:../cli`.
    """
    content = (BACKEND / "Dockerfile").read_text()
    assert "COPY cli /cli" in content
    assert "COPY backend /app" in content
    assert "pip install /cli" in content
    assert "python:3.12-slim" in content


def test_fly_configs_share_release_command() -> None:
    """DEPLOY-004: dev + prod release_command identical (same Alembic migration set)."""
    import tomllib

    dev = tomllib.loads((BACKEND / "fly.dev.toml").read_text())
    prod = tomllib.loads((BACKEND / "fly.prod.toml").read_text())
    assert dev["deploy"]["release_command"] == prod["deploy"]["release_command"]
    assert "alembic" in dev["deploy"]["release_command"]
    assert "upgrade head" in dev["deploy"]["release_command"]


def test_fly_configs_use_distinct_app_names() -> None:
    """DEPLOY-005: dev + prod must target different Fly apps (D-14 env split)."""
    import tomllib

    dev = tomllib.loads((BACKEND / "fly.dev.toml").read_text())
    prod = tomllib.loads((BACKEND / "fly.prod.toml").read_text())
    assert dev["app"] == "infracanvas-api-dev"
    assert prod["app"] == "infracanvas-api-prod"
    assert dev["app"] != prod["app"]


def test_worker_process_not_in_http_service() -> None:
    """DEPLOY-006: worker process MUST NOT be exposed via http_service (RESEARCH § P5)."""
    import tomllib

    for cfg in ("fly.dev.toml", "fly.prod.toml"):
        doc = tomllib.loads((BACKEND / cfg).read_text())
        assert "worker" not in doc["http_service"]["processes"], (
            f"{cfg}: worker process exposed via http_service"
        )
