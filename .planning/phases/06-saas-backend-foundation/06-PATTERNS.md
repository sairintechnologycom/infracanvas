# Phase 6: SaaS Backend Foundation — Pattern Map

**Mapped:** 2026-04-24
**Files analyzed:** 35 (backend/ new files)
**Analogs found:** 8 partial/role-match (in `cli/`) / 35 total — most backend files have NO local analog and MUST follow RESEARCH.md code sketches verbatim.

**Key framing:** Phase 6 stands up a fundamentally new package (`backend/`). The most valuable analogs live in `cli/`:
- **`cli/pyproject.toml`** — lint/typecheck/coverage config style (strongest analog)
- **`cli/infracanvas/graph/models.py`** — Pydantic v2 model style (and cross-package import target)
- **`cli/infracanvas/main.py`** — CLI error routing + stderr/exit-code discipline that translates to FastAPI exception handlers + structlog
- **`cli/tests/conftest.py`** — per-module coverage gate pattern to replicate for `backend/app/*`
- **`cli/infracanvas/config.py`** — tiny Pydantic v2 settings model pattern (precursor to pydantic-settings)
- **`cli/infracanvas/security/models.py`** — per-module data model file pattern
- **`cli/infracanvas/graph/builder.py`** — "validate/construct typed model from untyped input" pattern (precursor to backend's `ResourceGraph` re-validation)

Everything else (FastAPI routers, SQLAlchemy async sessions, Alembic migrations, RLS SQL, taskiq workers, Svix handlers, presigned-URL helpers, Stripe v2 meter clients, pure-ASGI middleware, Sentry init) is **NO_ANALOG** — planner references RESEARCH.md §Fn code sketches as authoritative templates.

---

## File Classification

Source of file list: RESEARCH.md § `backend/` Layout (lines 992–1050).

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `backend/pyproject.toml` | config | build/lint | `cli/pyproject.toml` | **exact** |
| `backend/Dockerfile` | config | build | none in repo | NO_ANALOG |
| `backend/fly.dev.toml` | config | deploy | none in repo | NO_ANALOG |
| `backend/fly.prod.toml` | config | deploy | none in repo | NO_ANALOG |
| `backend/alembic.ini` | config | migrations | none in repo | NO_ANALOG |
| `backend/migrations/env.py` | migration-runner | schema | none in repo | NO_ANALOG |
| `backend/migrations/script.py.mako` | template | schema | none in repo | NO_ANALOG |
| `backend/migrations/versions/20260424_001_rls_setup.py` | migration (raw SQL) | schema | none in repo | NO_ANALOG |
| `backend/migrations/versions/20260424_002_initial_schema.py` | migration (autogen) | schema | none in repo | NO_ANALOG |
| `backend/app/main.py` | app-factory | lifecycle | `cli/infracanvas/main.py` (Typer app factory) | role-match (CLI app ≠ FastAPI, but "app factory + startup wiring" shape translates) |
| `backend/app/settings.py` | config-model | request-scope | `cli/infracanvas/config.py` | role-match (Pydantic settings model) |
| `backend/app/auth/clerk.py` | middleware/dep | request-response | none in repo | NO_ANALOG (use RESEARCH §F1 sketch) |
| `backend/app/auth/webhooks.py` | service | event-driven | none in repo | NO_ANALOG (use RESEARCH §F2 sketch) |
| `backend/app/db/session.py` | middleware/dep | CRUD | none in repo | NO_ANALOG (use RESEARCH §F3 sketch) |
| `backend/app/db/models.py` | model (SQLAlchemy) | CRUD | `cli/infracanvas/graph/models.py` (Pydantic) | partial (model-file shape + StrEnum; but SA `Mapped[]` vs Pydantic `BaseModel`) |
| `backend/app/schemas/scan.py` | schema (Pydantic) | request-response | `cli/infracanvas/graph/models.py` | **exact** (Pydantic v2 model style) |
| `backend/app/schemas/team.py` | schema (Pydantic) | request-response | `cli/infracanvas/graph/models.py` | **exact** |
| `backend/app/routes/health.py` | router | request-response | `cli/infracanvas/main.py` (typer command) | role-match |
| `backend/app/routes/scans.py` | router | request-response + CRUD + file-I/O | `cli/infracanvas/main.py::scan` command | role-match (error taxonomy + exit-code → HTTPException translation) |
| `backend/app/routes/teams.py` | router | CRUD | same as scans | role-match |
| `backend/app/routes/webhooks.py` | router | event-driven | none in repo | NO_ANALOG (RESEARCH §F2) |
| `backend/app/storage/r2.py` | service (client wrapper) | file-I/O | none in repo | NO_ANALOG (RESEARCH §F5) |
| `backend/app/billing/stripe_meter.py` | service (client wrapper) | request-response | none in repo | NO_ANALOG (RESEARCH §F8) |
| `backend/app/queue/broker.py` | config (queue) | pub-sub | none in repo | NO_ANALOG (RESEARCH §F7) |
| `backend/app/queue/tasks/__init__.py` | module-index | pub-sub | none in repo | NO_ANALOG |
| `backend/app/queue/tasks/indexing.py` | worker | event-driven / batch | `cli/infracanvas/graph/builder.py` | partial (both "read ResourceGraph → derive denormalized summary counts"; task body is domain-reusable) |
| `backend/app/obs/sentry.py` | config (init) | cross-cutting | none in repo | NO_ANALOG (RESEARCH §F10) |
| `backend/app/obs/logging.py` | config (init) | cross-cutting | `cli/infracanvas/main.py` (Rich console init) | partial (init-at-import pattern; structlog replaces Rich for JSON output) |
| `backend/app/obs/middleware.py` | middleware (ASGI) | request-response | none in repo | NO_ANALOG (RESEARCH §F9 — pure ASGI, NOT BaseHTTPMiddleware) |
| `backend/app/util/ids.py` | utility | — | none in repo | NO_ANALOG (RESEARCH §F13, one-liner wrapper over `uuid_utils`) |
| `backend/tests/conftest.py` | test (fixtures) | — | `cli/tests/conftest.py` | partial (the per-module coverage hook copies directly; Testcontainers + role-switch fixtures are NEW) |
| `backend/tests/test_auth.py` | test | AUTH-* | none in repo | NO_ANALOG (RESEARCH §F14) |
| `backend/tests/test_rls.py` | test | RLS-* | none in repo | NO_ANALOG (RESEARCH §F14) |
| `backend/tests/test_scans.py` | test | API-* | `cli/tests/test_cli_contract.py` | role-match (contract test style + test-ID docstrings) |
| `backend/tests/test_stripe_meter.py` | test | MET-* | none in repo | NO_ANALOG |
| `backend/tests/test_tasks.py` | test | JOB-* | none in repo | NO_ANALOG |
| `backend/tests/test_webhooks.py` | test | WBH-* | none in repo | NO_ANALOG |
| `backend/tests/test_migrations.py` | test | MIG-* | none in repo | NO_ANALOG |
| `backend/tests/test_obs.py` | test | OBS-* | none in repo | NO_ANALOG |
| `backend/tests/test_storage.py` | test | STO-* (moto) | none in repo | NO_ANALOG |

---

## Pattern Assignments

### `backend/pyproject.toml` (config, build/lint)

**Analog:** `cli/pyproject.toml`
**Match quality:** exact — backend mirrors the style blocks verbatim, swaps `[project].dependencies` for the FastAPI stack.

**Copy-through blocks (from `cli/pyproject.toml`):**

1. **Build system** (lines 1–6) — same Hatchling layout; swap package name:
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["app"]   # backend package is app/, not infracanvas/
```

2. **Ruff** (lines 84–89) — copy verbatim:
```toml
[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
```

3. **MyPy strict** (lines 91–99) — copy verbatim, add new override entries for `taskiq.*`, `uuid_utils.*`, `svix.*` (follow the `[[tool.mypy.overrides]]` pattern already used for `hcl2.*`):
```toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true

[[tool.mypy.overrides]]
module = ["taskiq.*", "taskiq_redis.*", "svix.*"]
ignore_missing_imports = true
```

4. **Coverage gate pattern** (lines 61–82) — copy verbatim, swap `infracanvas.security/cost/drift` for backend module prefixes (`app.auth`, `app.routes`, `app.db`, `app.queue.tasks`, `app.billing`, `app.storage`):
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = "--cov=app --cov-branch --cov-report=term-missing --cov-fail-under=80"

[tool.coverage.run]
branch = true
source = ["app"]
omit = ["app/__main__.py", "*/tests/*"]

[tool.coverage.report]
fail_under = 80
show_missing = true
skip_covered = false
exclude_lines = ["pragma: no cover", "raise NotImplementedError", "if TYPE_CHECKING:"]
```

5. **Python floor** — `requires-python = ">=3.12"` (copy from line 19).

6. **Dependencies** — REPLACE wholesale; see RESEARCH.md § Standard Stack (lines 933–983) for the pinned list (FastAPI ~=0.115, SQLAlchemy ~=2.0.36, taskiq ~=0.11.0, stripe >=11.0,<16.0, etc.).

7. **Cross-package import of ResourceGraph** (per RESEARCH §F6): add `"infracanvas @ file:../cli"` to `[project].dependencies` with the note that a `cli-runtime` extra split may be needed (see "No Analog" below).

---

### `backend/app/schemas/scan.py` & `backend/app/schemas/team.py` (schema, request-response)

**Analog:** `cli/infracanvas/graph/models.py`
**Match quality:** exact — same Pydantic v2 idiom (`BaseModel`, `Field(default_factory=...)`, `StrEnum` for enums, `dict[str, object]` for open JSON payloads, `from __future__ import annotations`).

**Imports pattern** (from `cli/infracanvas/graph/models.py` lines 1–7):
```python
"""Pydantic v2 models for InfraCanvas resource graph."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field
```

**Enum pattern** (lines 10–14):
```python
class Severity(StrEnum):
    critical = "critical"
    high = "high"
    medium = "medium"
    info = "info"
```
→ Backend `ScanStatus(StrEnum)` with `pending`, `ready`, `failed` (matches RESEARCH.md §F4 scan_status enum).

**Model pattern — required fields + defaults + factories** (lines 17–25, 66–77):
```python
class Finding(BaseModel):
    rule_id: str
    severity: Severity
    title: str
    description: str
    remediation: str
    evidence: dict[str, object] = {}
    source: str = "security"
    framework_ids: list[str] = []


class GraphSummary(BaseModel):
    total_resources: int = 0
    findings: dict[str, int] = Field(
        default_factory=lambda: {"critical": 0, "high": 0, "medium": 0, "info": 0}
    )
    estimated_monthly_cost: float = 0.0
    score: int = 100
```

**Apply to backend request/response models:**
```python
# backend/app/schemas/scan.py
class ScanCreateReq(BaseModel):
    content_type: str = "application/json"

class ScanCreateResp(BaseModel):
    scan_id: UUID
    presigned_put_url: str
    expires_at: datetime

class ScanCommitReq(BaseModel):
    sha256: str

class ScanGetResp(BaseModel):
    id: UUID
    team_id: UUID
    status: ScanStatus
    presigned_get_url: str
    size_bytes: int
    created_at: datetime
```

**Important additions for backend** (NOT in CLI analog — from RESEARCH §D2 D-type safety):
- Add `model_config = ConfigDict(strict=True, extra="forbid")` to every request body. CLI models omit this; backend hardens against unexpected fields.

---

### `backend/app/settings.py` (config-model, request-scope)

**Analog:** `cli/infracanvas/config.py`
**Match quality:** role-match — both are tiny Pydantic config models. Backend swaps `BaseModel` for `pydantic_settings.BaseSettings` (env-var reading) but shape is identical.

**Core pattern from `cli/infracanvas/config.py` lines 1–16:**
```python
"""InfraCanvas project configuration (.infracanvas.yml)."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class InfraCanvasConfig(BaseModel):
    severity_threshold: str = "high"
    ignore_rules: list[str] = []
    output_dir: str = "."
    open_browser: bool = True
    provider: str = "aws"
```

**Graceful-default loading** (lines 19–30):
```python
def load_config(directory: Path) -> InfraCanvasConfig:
    """Load .infracanvas.yml from directory or any parent up to home dir."""
    config_file = _find_config_file(directory)
    if not config_file:
        return InfraCanvasConfig()
    try:
        data = yaml.safe_load(config_file.read_text())
        if not isinstance(data, dict):
            return InfraCanvasConfig()
        return InfraCanvasConfig.model_validate(data)
    except (yaml.YAMLError, ValueError):
        return InfraCanvasConfig()
```

**Apply to `backend/app/settings.py`:** use `BaseSettings` (from `pydantic-settings`) instead of `BaseModel` — reads `CLERK_JWKS_URL`, `DATABASE_URL`, `R2_*`, `REDIS_URL`, `STRIPE_SECRET_KEY`, `SENTRY_DSN`, `ENV` (dev|prod). One class; exposed as module-level `settings = Settings()`. Graceful-default idiom from CLI does NOT apply — backend env must be complete at startup; fail loud if missing.

---

### `backend/app/db/models.py` (model, CRUD — SQLAlchemy 2.0)

**Analog:** `cli/infracanvas/graph/models.py` (Pydantic) + `cli/infracanvas/security/models.py` (per-module model-file shape).
**Match quality:** partial — SQLAlchemy `Mapped[...]`/`mapped_column` is a different API surface from Pydantic `BaseModel`, but the FILE STRUCTURE (one module per concern, docstring header, `from __future__ import annotations`, StrEnum for enums) copies cleanly.

**File-structure pattern from `cli/infracanvas/security/models.py`:**
```python
"""Security rule data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from infracanvas.graph.models import Severity
```

**StrEnum reuse pattern** (line 8 of security/models.py): import shared enums from the canonical source module. Apply the same idiom to backend — `ScanStatus` lives in `app/db/models.py` and is imported into `app/schemas/scan.py` rather than redeclared.

**Authoritative SQLAlchemy 2.0 shape:** RESEARCH.md §F4 code sketch (lines 352–380) — copy the `Team` and `Scan` classes verbatim, extend with remaining tables per RLS policy needs.

---

### `backend/app/routes/scans.py` (router, request-response + CRUD + file-I/O)

**Analog:** `cli/infracanvas/main.py::scan` command (lines 304–513).
**Match quality:** role-match — different framework (Typer vs FastAPI), but the **error taxonomy + exit-code discipline** translates directly to HTTPException status codes, and the flag-combination-validation pattern translates to Pydantic body validators.

**Error routing pattern** (from `cli/infracanvas/main.py` lines 387–411):
```python
# CLI:
if not directory.is_dir():
    _err_console.print(f"[red]Error:[/red] {directory} is not a directory")
    raise typer.Exit(code=2)

if open_flag and format != "html":
    _err_console.print(
        "[red]Error:[/red] --open requires --format html (current: --format "
        f"{format}). Drop --open or use --format html."
    )
    raise typer.Exit(code=2)
```

**Translates to backend** (FastAPI):
```python
if body.size_bytes > 25 * 1024 * 1024:
    raise HTTPException(413, {"error": "too_large", "size_bytes": body.size_bytes})
```

**Error-severity map:**

| CLI (exit code) | Backend (HTTP status) | Semantic |
|-----------------|-----------------------|----------|
| `typer.Exit(code=2)` | `HTTPException(422)` | user error / bad input |
| `typer.Exit(code=1)` | `HTTPException(404)` | missing resource |
| Uncaught exception | `HTTPException(500)` | system error |

**stderr vs stdout discipline** (CLI lines 40–42):
```python
console = Console()
_ci_console = Console(stderr=True)   # CI mode diagnostics
_err_console = Console(stderr=True)  # error messages (WRG-01 D-03)
```
→ Backend equivalent: structlog writes JSON to stdout (Axiom drain); Sentry captures errors separately. Access log goes through the pure-ASGI middleware (RESEARCH §F9), NOT uvicorn's default (`--no-access-log`).

**Authoritative commit handler body:** RESEARCH.md § Code Examples (lines 1056–1115). Copy the full handler verbatim — it already composes F3 (session), F5 (R2), F6 (ResourceGraph), F8 (meter event), F9 (request_id propagation) correctly.

**Typer command shape → FastAPI route shape crosswalk:**
```python
# CLI (main.py line 304):
@app.command()
def scan(directory: Annotated[Path, typer.Argument(...)], ...) -> None:
    ...

# Backend:
@router.post("/v1/scans", response_model=ScanCreateResp)
async def create_scan(
    body: ScanCreateReq,
    principal: ClerkPrincipal = Depends(require_role("owner", "admin", "member")),
    team: Team = Depends(resolve_team_from_clerk_org),
    session: AsyncSession = Depends(team_scoped_session),
) -> ScanCreateResp: ...
```

---

### `backend/app/queue/tasks/indexing.py` (worker, event-driven / batch)

**Analog:** `cli/infracanvas/graph/builder.py` — both "parse typed input → derive summary counts from nodes" operations.
**Match quality:** partial — the **domain logic** of iterating `graph.nodes` and computing `finding_counts` already exists in `cli/infracanvas/main.py::_run_scan` (lines 201–225):

```python
# Existing CLI pattern (main.py lines 202–226):
finding_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "info": 0}
for node in graph.nodes:
    for f in node.findings:
        finding_counts[f.severity.value] += 1

score = 100 - (
    finding_counts["critical"] * 20
    + finding_counts["high"] * 10
    + finding_counts["medium"] * 5
    + finding_counts["info"] * 1
)
score = max(0, score)

graph.summary = GraphSummary(
    total_resources=len(graph.nodes),
    findings=finding_counts,
    estimated_monthly_cost=0.0,
    score=score,
)
```

**Apply to backend indexing task:** after downloading the R2 blob and validating to `ResourceGraph`, run the **same counting loop** and write `{finding_counts, total_resources, score}` into `scans.summary_json` (JSONB column). Do NOT duplicate the loop — plan should refactor `_run_scan`'s summary computation into `infracanvas.graph.summary.compute_summary(graph) -> GraphSummary` so both CLI and backend import it. This closes the only cross-package domain overlap cleanly.

**Task shell** (from RESEARCH §F7, lines 530–535):
```python
@broker.task(retry_on_error=True, max_retries=3, delay=5)
async def enqueue_scan_indexing(scan_id: str, request_id: str) -> None:
    ...
```

---

### `backend/tests/conftest.py` (test fixtures)

**Analog:** `cli/tests/conftest.py`
**Match quality:** partial — the **per-module coverage gate hook** (lines 78–122) copies directly with the module-prefix list swapped. Testcontainers + role-switch fixtures are NEW (no analog).

**Copy-through block: `pytest_sessionfinish` hook** (lines 78–122). Swap `PER_MODULE_GATES` values:
```python
# CLI version (line 16–20):
PER_MODULE_GATES: dict[str, float] = {
    "infracanvas/security": 80.0,
    "infracanvas/cost": 80.0,
    "infracanvas/drift": 80.0,
}

# Backend version:
PER_MODULE_GATES: dict[str, float] = {
    "app/auth":    80.0,
    "app/routes":  80.0,
    "app/db":      80.0,
    "app/queue":   80.0,
    "app/billing": 80.0,
    "app/storage": 80.0,
    "app/obs":     80.0,
}
```

The entire `_module_percents` function (lines 23–75) and the `pytest_sessionfinish` body (lines 78–122) copy verbatim — they're framework-agnostic and enforce the Phase-4 D-15 discipline in `backend/`.

**New fixtures (NO_ANALOG) — follow RESEARCH §F14 (lines 895–928):**
- `pg_container` (session-scoped Testcontainers Postgres 16)
- `app_session` (connects as `infracanvas_app`, RLS active)
- `seed_session` (connects as `infracanvas_test`, BYPASSRLS)
- `mock_clerk` (fixture-local RSA keypair + fake JWKS via `httpx.MockTransport`)
- `mock_r2` (moto S3 mock)
- `mock_stripe` (respx against `stripe.api_base`)
- `mock_svix` (use `svix.Webhook.sign()` to produce valid test signatures — no mock needed)

---

### `backend/tests/test_scans.py` (test, API-*)

**Analog:** `cli/tests/test_cli_contract.py` (contract-test file) — also informed by docstring convention from the existing CLI test files.
**Match quality:** role-match — contract-test file shape + **test-ID-in-docstring convention** (`B-001`, `E-002` from CLI; backend uses `API-*`, `AUTH-*`, `RLS-*`, `MET-*`, `JOB-*`, `WBH-*`, `MIG-*`, `OBS-*` per RESEARCH §F14 lines 889–896).

**Docstring convention from CLI tests** (established project norm — referenced in CLAUDE.md § Comments):
```python
def test_something():
    """B-001: CLI should reject non-existent directory with exit 2."""
    ...
```

**Apply to backend:**
```python
async def test_upload_happy_path(mock_clerk, mock_r2, mock_stripe, app_session):
    """API-010: POST /v1/scans returns presigned PUT URL for authenticated caller."""
    ...

async def test_commit_rejects_oversized(mock_clerk, mock_r2, mock_stripe, app_session):
    """API-015: POST /v1/scans/{id}/commit returns 413 when R2 HEAD ContentLength > 25MB."""
    ...

async def test_rls_isolates_across_teams(seed_session, app_session):
    """RLS-001: read as infracanvas_app with wrong team context returns 0 rows."""
    ...
```

---

## Shared Patterns

### Python toolchain (Ruff + MyPy)

**Source:** `cli/pyproject.toml` lines 84–99
**Apply to:** `backend/pyproject.toml` (verbatim copy of `[tool.ruff]`, `[tool.ruff.lint]`, `[tool.mypy]` blocks)
**Rationale:** CLAUDE.md § Conventions mandates `E F I N W UP` Ruff rules, line 100, MyPy strict. Single-package consistency across monorepo.

### Pydantic v2 model style

**Source:** `cli/infracanvas/graph/models.py` (all classes)
**Apply to:** every `backend/app/schemas/*.py` file AND every Pydantic model inside routes/auth/webhooks.
**Idioms to copy:**
- `from __future__ import annotations` at top
- `StrEnum` (not `Enum`) for string-valued enums
- `Field(default_factory=...)` for mutable defaults (lists, dicts)
- `dict[str, object]` (lowercase; no `typing.Dict`) for open payloads
- No `model_config` on CLI models → **backend ADDS `ConfigDict(strict=True, extra="forbid")` on every request-body model** (backend-specific hardening).

### Error routing: user error → 422; missing → 404; system → 500

**Source:** `cli/infracanvas/main.py` stderr/exit-code pattern (lines 40–42 + exit code usage throughout)
**Apply to:** all `backend/app/routes/*` handlers — pre-validate inputs, raise `HTTPException(422)` on user mistakes, `HTTPException(404)` on missing resources (including RLS-invisible rows per D-10 — "404, not 403, to avoid leaking existence"), let unexpected exceptions surface to Sentry → 500.
**Rationale:** matches the semantic categories already used in the CLI; keeps error-handling mental model uniform across the monorepo.

### Per-module coverage gate (≥80% line + branch)

**Source:** `cli/tests/conftest.py` lines 1–122
**Apply to:** `backend/tests/conftest.py` — copy the whole `pytest_sessionfinish` hook + `_module_percents` helper; swap the `PER_MODULE_GATES` dict to backend module prefixes.
**Rationale:** Phase 4 D-15 discipline carries into backend; CONTEXT § "Established Patterns" requires parallel coverage posture.

### Test-ID-in-docstring convention

**Source:** CLAUDE.md § Comments — "Test case descriptions in docstrings with test IDs (e.g., B-001, E-002, E-007)". Observed across every `cli/tests/test_*.py`.
**Apply to:** all `backend/tests/test_*.py` — use prefixes per RESEARCH §F14: `API-*`, `AUTH-*`, `RLS-*`, `MET-*`, `JOB-*`, `WBH-*`, `MIG-*`, `OBS-*`, `STO-*`.
**Rationale:** Per-requirement test map (RESEARCH lines 1247–1260) cross-references these IDs; grep-ability across PR reviews.

### Cross-package `ResourceGraph` import

**Source:** `cli/infracanvas/graph/models.py` (defines `ResourceGraph`)
**Apply to:** `backend/app/routes/scans.py` commit handler + `backend/app/queue/tasks/indexing.py`
**Mechanism:** RESEARCH §F6 — `infracanvas @ file:../cli` path dependency in `backend/pyproject.toml`, then `from infracanvas.graph.models import ResourceGraph`.
**Caveat:** backend planner should include a subtask to split `cli/pyproject.toml` deps so `typer`/`rich`/`networkx`/`python-hcl2` go into a `[project.optional-dependencies] cli-runtime = [...]` extra — otherwise backend container bloats. Alternative = JSON Schema snapshot (rejected unless split is >1 task per RESEARCH §F6).

### Shared domain helper: summary computation

**Source:** `cli/infracanvas/main.py::_run_scan` lines 201–226 (the finding-count + score loop)
**Apply to:** `backend/app/queue/tasks/indexing.py` (worker's denormalization job)
**Action:** refactor the CLI's inline loop into `infracanvas.graph.summary.compute_summary(graph) -> GraphSummary` and import from both places. This is the ONE place where Phase 6 should touch `cli/` to avoid duplicating the scoring rubric.

---

## No Analog Found

Files with no close match in the codebase. Planner MUST reference RESEARCH.md §Fn code sketches as authoritative templates. Each entry includes the RESEARCH section to copy from.

| File | Role | Data Flow | Authoritative Template | Reason |
|------|------|-----------|------------------------|--------|
| `backend/Dockerfile` | config | build | RESEARCH §F11 + standard `python:3.12-slim` | No container work in repo yet |
| `backend/fly.dev.toml`, `fly.prod.toml` | config | deploy | RESEARCH §F11 lines 773–816 | First Fly deployment |
| `backend/alembic.ini`, `migrations/env.py` | migration | schema | RESEARCH §F3 lines 301–317 + §F4 | First SQL DB in repo |
| `backend/migrations/versions/*_rls_setup.py` | migration | schema | RESEARCH §F3 lines 243–266 (raw SQL) | No prior RLS work |
| `backend/app/auth/clerk.py` | middleware/dep | request-response | RESEARCH §F1 lines 132–177 | No auth in repo |
| `backend/app/auth/webhooks.py`, `routes/webhooks.py` | service/router | event-driven | RESEARCH §F2 lines 198–223 | No webhooks in repo |
| `backend/app/db/session.py` | middleware/dep | CRUD | RESEARCH §F3 lines 270–295 | No SQLAlchemy yet |
| `backend/app/storage/r2.py` | service | file-I/O | RESEARCH §F5 lines 409–441 | No object storage yet |
| `backend/app/billing/stripe_meter.py` | service | request-response | RESEARCH §F8 lines 585–605 | No payments yet |
| `backend/app/queue/broker.py` | config | pub-sub | RESEARCH §F7 lines 509–529 | No queue yet |
| `backend/app/obs/sentry.py` | config | cross-cutting | RESEARCH §F10 lines 721–742 | No Sentry yet |
| `backend/app/obs/middleware.py` | middleware (ASGI) | request-response | RESEARCH §F9 lines 652–676 | CRITICAL: must be pure ASGI, NOT BaseHTTPMiddleware (P1 pitfall) |
| `backend/app/util/ids.py` | utility | — | RESEARCH §F13 lines 866–876 | No UUIDv7 usage yet |
| `backend/tests/test_rls.py`, `test_stripe_meter.py`, `test_tasks.py`, `test_webhooks.py`, `test_migrations.py`, `test_obs.py`, `test_storage.py`, `test_auth.py` | test | various | RESEARCH §F14 + §Validation Architecture | All test domains are new |

---

## Metadata

**Analog search scope:** `cli/` (primary), `viewer/` (skipped — TypeScript, wrong language), `.planning/` (context only, not code).
**Files scanned (key analogs):**
- `cli/pyproject.toml` (100 lines)
- `cli/infracanvas/graph/models.py` (180 lines)
- `cli/infracanvas/main.py` (1019 lines — sampled sections 1–513, 880–1018)
- `cli/infracanvas/graph/builder.py` (header sampled)
- `cli/infracanvas/config.py` (45 lines)
- `cli/infracanvas/security/models.py` (29 lines)
- `cli/tests/conftest.py` (122 lines)

**Pattern extraction date:** 2026-04-24
**Early-stop reason:** 5 strong analogs identified (`cli/pyproject.toml`, `cli/infracanvas/graph/models.py`, `cli/infracanvas/main.py`, `cli/tests/conftest.py`, `cli/infracanvas/config.py`) covering the recurring cross-cutting needs (toolchain config, Pydantic style, error routing, coverage gate, settings shape). Remaining files are fundamentally new domains — additional CLI searches yielded diminishing returns; RESEARCH.md provides the authoritative code sketches.
