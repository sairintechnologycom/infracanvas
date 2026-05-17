# Phase 12: Path Computation + Asymmetric Routing — Pattern Map

**Mapped:** 2026-05-17
**Files analyzed:** 28 (new + modified)
**Analogs found:** 26 / 28 (2 partial — pytricia trie + LPM module are net-new)

## File Classification

### Backend — New files

| File | Role | Data Flow | Closest Analog | Match Quality |
|------|------|-----------|----------------|---------------|
| `backend/migrations/versions/20260518_012_route_flow_tables.py` | migration | DDL | `backend/migrations/versions/20260510_011_firewall_tables.py` | exact (table + RLS + GRANT) |
| `backend/migrations/versions/20260518_013_path_compute_tables.py` | migration | DDL | `backend/migrations/versions/20260510_011_firewall_tables.py` | exact (snapshot-per-pull + RLS pattern) |
| `backend/app/schemas/paths.py` | schema | request-response | `backend/app/schemas/firewall.py` | exact (Pydantic v2 BaseModel, bounded lists) |
| `backend/app/routes/paths.py` | route | request-response | `backend/app/routes/firewalls.py` | exact (Clerk JWT + RLS GUC + site-membership probe) |
| `backend/app/notifications/slack.py` | service | event-driven | `backend/app/queue/tasks/scan_repo.py:299-341` (inline → extract) | exact (extract existing inline) |
| `backend/app/queue/tasks/path_compute.py` | taskiq task | batch | `backend/app/queue/tasks/firewall_prune.py` | exact (cron + team-walk + RLS GUC) |
| `backend/app/queue/tasks/path_compute_prune.py` | taskiq task | batch | `backend/app/queue/tasks/firewall_prune.py` | exact (TTL prune pattern verbatim) |
| `backend/app/security/pathcompute/__init__.py` | package init | — | `cli/infracanvas/security/__init__.py` | role-match |
| `backend/app/security/pathcompute/lpm.py` | pure compute | transform | (no analog — pytricia wrapper) | none — use library |
| `backend/app/security/pathcompute/forward.py` | pure compute | transform | `cli/infracanvas/security/engine.py` (rule-eval shape) | partial — pure-fn pattern |
| `backend/app/security/pathcompute/pair.py` | pure compute | transform | RESEARCH §Pattern 2 | partial — small new module |
| `backend/app/security/pathcompute/correlate.py` | pure compute | transform | RESEARCH §Pattern 3 | partial — small new module |
| `backend/app/security/pathcompute/asymmetry.py` | pure compute | transform | RESEARCH §Pattern 4 | partial |
| `backend/app/security/pathcompute/classify.py` | pure compute | transform | RESEARCH §Pattern 5 (evidence-scored) | partial |
| `backend/app/security/pathcompute/impact.py` | pure compute | transform | `cli/infracanvas/cost/` (scalar-output detector pattern) | role-match |

### Backend — Modified files

| File | Role | Data Flow | Closest Analog | Match Quality |
|------|------|-----------|----------------|---------------|
| `backend/app/db/models.py` | model | ORM | existing `FirewallRulesetSnapshot` (lines 195-237) + `FirewallRuleORM` (lines 239-266) | exact (extend in same file) |
| `backend/app/schemas/agent.py` | schema | request-response | existing `FlowRecord` lines 56-65 | exact (add `exporter_interface`, `exit_interface`) |
| `backend/app/routes/agent.py` | route | request-response | existing `push_firewall_rules` lines 174-228 | exact (replace stub `push_routes`/`push_flows`) |
| `backend/app/queue/tasks/scan_repo.py` | taskiq task | event-driven | lines 299-341 (collapse to one-liner) | exact (call extracted helper) |
| `backend/app/main.py` | route registration | wiring | existing firewall router include | exact |

### CLI — New / modified files

| File | Role | Data Flow | Closest Analog | Match Quality |
|------|------|-----------|----------------|---------------|
| `cli/infracanvas/security/network/__init__.py` | package init | — | `cli/infracanvas/security/__init__.py` | role-match |
| `cli/infracanvas/security/network/net_010.py` | detector | transform | `cli/infracanvas/security/engine.py` (Finding-emit shape) | role-match |
| `cli/tests/test_flowmap_network_rules.py` | test | — | existing `test_net_010_reserved_for_phase_3b` (line 71) | exact (flip + extend) |
| `cli/tests/test_security.py` | test | — | existing rule-count assertion (line 64) | exact (verify count holds at 51 — D-11 keeps NET-010 OUT of YAML catalog) |

### Viewer — Modified files

| File | Role | Data Flow | Closest Analog | Match Quality |
|------|------|-----------|----------------|---------------|
| `viewer/src/components/flowmap/edges/PathEdge.tsx` | component | render | itself (lines 18-29 dual-lane style) | exact (extend existing) |
| `viewer/src/components/flowmap/PathDetailPanel.tsx` | component | render | itself (tabs array lines 61-67) | exact (extend `tabs` with conditional Asymmetry tab) |
| `viewer/src/store.ts` | store | state | existing `selectedPath` slice (line 42) | exact (extend store action) |
| `viewer/src/__tests__/flowmap/PathEdge.test.tsx` | test | — | itself (synthetic EdgeProps pattern) | exact |
| `viewer/src/__tests__/flowmap/PathDetailPanel.test.tsx` | test | — | itself + node-tab variants | exact |

---

## Pattern Assignments

### `backend/migrations/versions/20260518_012_route_flow_tables.py` (migration, DDL)

**Analog:** `backend/migrations/versions/20260510_011_firewall_tables.py`

**Module docstring + revision-id pattern** (lines 1-38):
```python
"""012_route_flow_tables: route_records + netflow_records.

Phase 12 D-15/Pitfall 1 — backend persistence for Phase 10 agent push
(routes + NetFlow). The Phase 10 agent.py handlers were stubs ("logs
only — Phase 11 persists"); Phase 11 only landed firewall tables. Phase
12 closes that gap so the path-compute job has inputs.

RLS posture mirrors Phase 11 D-08 / migration 011 verbatim:
  - team_id column on each row
  - ENABLE + FORCE ROW LEVEL SECURITY
  - team_isolation policy keyed on
    current_setting('app.current_team_id', true)::uuid
  - GRANT SELECT/INSERT/UPDATE/DELETE to infracanvas_app

Revision ID: 012_route_flow_tables
Revises: 011_firewall_tables
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012_route_flow_tables"
down_revision: str | None = "011_firewall_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
```

**Table + RLS policy + GRANT pattern** (lines 41-97 — copy verbatim, swap table + column names):
```python
op.create_table(
    "route_records",
    sa.Column("record_id", postgresql.UUID(as_uuid=True), primary_key=True,
              server_default=sa.text("gen_random_uuid()"), nullable=False),
    sa.Column("team_id", postgresql.UUID(as_uuid=True),
              sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
    sa.Column("site_id", postgresql.UUID(as_uuid=True),
              sa.ForeignKey("dc_sites.id", ondelete="CASCADE"), nullable=False),
    sa.Column("device_host", sa.Text(), nullable=False),
    sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("prefix", sa.Text(), nullable=False),
    sa.Column("next_hop", sa.Text(), nullable=False),
    sa.Column("protocol", sa.Text(), nullable=False),
    sa.Column("metric", sa.Integer(), server_default="0", nullable=False),
    sa.Column("as_path", sa.Text(), server_default="", nullable=False),
)
op.create_index(
    "ix_route_records_latest",
    "route_records",
    ["site_id", "device_host", sa.text("collected_at DESC")],
)
op.execute("ALTER TABLE route_records ENABLE ROW LEVEL SECURITY;")
op.execute("ALTER TABLE route_records FORCE ROW LEVEL SECURITY;")
op.execute("""
    CREATE POLICY route_records_team_isolation ON route_records
      USING (team_id = current_setting('app.current_team_id', true)::uuid)
      WITH CHECK (team_id = current_setting('app.current_team_id', true)::uuid);
""")
op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON route_records TO infracanvas_app;")
```

**NetFlow table — same pattern with INET + composite indexes** (per RESEARCH Pitfall 1 schema):
- Add `exporter_interface TEXT NULL` + `exit_interface TEXT NULL` for D-05 edge-hop matching (REQUIRED — see RESEARCH Q2).
- Two indexes: `(site_id, collected_at DESC)` for window scan, `(src_ip, dst_ip, src_port, dst_port, protocol)` for flow-key lookups.

**Downgrade pattern** (lines 255-264 — child tables first, drop policy then table):
```python
def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS netflow_records_team_isolation ON netflow_records;")
    op.drop_table("netflow_records")
    op.execute("DROP POLICY IF EXISTS route_records_team_isolation ON route_records;")
    op.drop_table("route_records")
```

---

### `backend/migrations/versions/20260518_013_path_compute_tables.py` (migration, DDL)

**Analog:** `backend/migrations/versions/20260510_011_firewall_tables.py` (parent + child shape with snapshot-per-pull semantics)

**Three tables** (`computed_paths`, `asymmetry_findings`, `path_divergence_findings`):
- All RLS via verbatim Pattern C (see above) — `team_id` column + ENABLE + FORCE + policy + GRANT.
- `computed_paths` UNIQUE constraint per D-16 snapshot-per-pull: `UNIQUE (site_id, pair_src_cidr, pair_dst_cidr, direction, computed_at)`.
- Findings tables include `first_seen_at`, `last_seen_at`, `resolved_at NULL` for D-16 reconciliation semantics (mirror Phase 11 D-10 lifecycle).
- `cause` column on `asymmetry_findings` uses `CHECK (cause IN ('BGP_LOCAL_PREF','ROUTE_LEAK','NAT_ASYMMETRY','UNKNOWN'))` enum-pattern (Phase 11 used same pattern via `vendor`/`source` validation at Pydantic boundary; SQL CHECK is acceptable for closed enums).
- JSONB columns: `hops`, `match_evidence`, `evidence`, `observed_path` (mirror `raw_blob` JSONB usage in `firewall_rules`).

**Index for "latest computed paths per pair" read** (mirrors `ix_fw_ruleset_latest`):
```python
op.create_index(
    "ix_computed_paths_latest",
    "computed_paths",
    ["site_id", "pair_src_cidr", "pair_dst_cidr", "direction", sa.text("computed_at DESC")],
)
```

---

### `backend/app/db/models.py` (MODIFIED — append new ORMs)

**Analog:** existing `FirewallRulesetSnapshot` lines 195-237 + `FirewallRuleORM` lines 239-266

**ORM shape pattern** (verbatim from `FirewallRulesetSnapshot` lines 213-237):
```python
class RouteRecordORM(Base):
    """Phase 12 D-15 / Pitfall 1 — snapshot-per-pull route records from DC agent.

    Full-replace per (site_id, device_host, collected_at) — same shape as
    Phase 11 firewall_ruleset_snapshots lifecycle. Pruned by
    app.tasks.netflow_prune at NETFLOW_RECORD_TTL_HOURS (default 24).
    """

    __tablename__ = "route_records"

    record_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("dc_sites.id", ondelete="CASCADE"),
        nullable=False,
    )
    device_host: Mapped[str] = mapped_column(Text, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    prefix: Mapped[str] = mapped_column(Text, nullable=False)
    next_hop: Mapped[str] = mapped_column(Text, nullable=False)
    protocol: Mapped[str] = mapped_column(Text, nullable=False)
    metric: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    as_path: Mapped[str] = mapped_column(Text, nullable=False, default="")
```

Add `NetFlowRecordORM`, `ComputedPathORM`, `AsymmetryFindingORM`, `PathDivergenceFindingORM` using the same shape.

**Naming convention** (lines 239-242 explain `ORM` suffix):
> The `ORM` suffix avoids the symbol collision with the un-suffixed Pydantic `FirewallRule` (`app.schemas.firewall`).

→ Apply: `RouteRecordORM` / `NetFlowRecordORM` / `ComputedPathORM` / `AsymmetryFindingORM` / `PathDivergenceFindingORM` (Pydantic re-exports in `schemas/paths.py` use bare names).

---

### `backend/app/schemas/agent.py` (MODIFIED — extend FlowRecord)

**Analog:** existing `FlowRecord` lines 56-65 (verbatim shape)

**Add two optional fields for D-05 edge-hop matching** (RESEARCH Pattern 3 Note + Q2):
```python
class FlowRecord(BaseModel):
    """A single NetFlow v9/IPFIX record collected by the UDP listener.

    Phase 12 D-05 — exporter_interface + exit_interface populated when the
    agent's UDP listener reads them from the NetFlow header; null when the
    exporter does not emit them. Required for D-05 endpoint+edge-hop match.
    """

    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: int
    bytes: int
    packets: int
    exporter_interface: str | None = None   # Phase 12 D-05 (NEW)
    exit_interface: str | None = None       # Phase 12 D-05 (NEW)
```

> Backwards-compatible: Phase 10 agent binaries continue to push without these fields and Pydantic defaults them to `None`. Phase 12 path-compute treats `None` as "no edge-hop signal" and falls back to endpoint-only match for that flow.

---

### `backend/app/schemas/paths.py` (NEW)

**Analog:** `backend/app/schemas/firewall.py` (entire file — copy module docstring shape + Pydantic v2 patterns)

**Module docstring template** (mirror `firewall.py` lines 1-20):
```python
"""Pydantic schemas for Phase 12 path-compute read API.

Locked contracts consumed by both `backend/app/routes/paths.py` and the
viewer dashboard fetch wiring (Phase 12 FMV-02). Field names are stable
forward-feed contract for the viewer hydration into Zustand
`selectedPath` — do not rename without coordinated viewer update.

Re-exports `NetworkPath` and `PathHop` from `cli/infracanvas/graph/
models.py` (Pitfall 9 — import-not-redeclare) so route handlers,
viewer fetcher, and CLI offline scans use the SAME shape.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

# Re-export to give backend a single import path; cli is already a
# backend dep (`infracanvas @ file:../cli` in `backend/pyproject.toml`).
from infracanvas.graph.models import NetworkPath, PathHop  # noqa: F401
```

**Response model pattern** (mirror `FirewallSnapshotResponse` from `routes/firewalls.py:62-79`):
```python
class AsymmetryFindingResponse(BaseModel):
    """Per-pair asymmetry finding returned by GET /v1/sites/{site_id}/asymmetries."""

    finding_id: str
    site_id: str
    forward_path_id: str
    return_path_id: str
    cause: str  # 'BGP_LOCAL_PREF'|'ROUTE_LEAK'|'NAT_ASYMMETRY'|'UNKNOWN'
    cause_confidence: float
    evidence: dict
    impact_bytes_per_sec: float
    impact_firewall_count: int
    first_seen_at: str  # ISO 8601
    last_seen_at: str   # ISO 8601
    resolved_at: str | None = None
```

**Recompute request/response** (mirror `CreateSiteResp` from `schemas/agent.py:21-30`):
```python
class RecomputeResp(BaseModel):
    """Response for POST /v1/sites/{site_id}/paths/recompute.

    202 Accepted + job_id (taskiq pattern); caller polls via existing
    job-status endpoint if needed. Coalesces concurrent calls — same
    site_id within 60s returns the in-flight job_id.
    """

    job_id: str
    site_id: str
    coalesced: bool = False
```

---

### `backend/app/routes/paths.py` (NEW)

**Analog:** `backend/app/routes/firewalls.py` (entire file — verbatim auth + RLS GUC + site-membership probe pattern)

**Module docstring pattern** (mirror `firewalls.py` lines 1-34):
```python
"""Phase 12 D-14 — read API for computed paths + asymmetry findings.

Endpoints:
* GET  /v1/sites/{site_id}/paths            — latest computed paths per pair
* GET  /v1/sites/{site_id}/asymmetries      — current asymmetry findings
* POST /v1/sites/{site_id}/paths/recompute  — on-demand recompute (owner)

Auth posture (mirrors firewalls.py / Phase 11 CC-2):
* Depends(require_role(*_READ_ROLES)) — Clerk JWT required (401 on missing).
* Depends(resolve_team_from_clerk_org) — Team resolved from JWT org_id.
* set_config('app.current_team_id', :t, true) inside the transaction —
  RLS isolates every query to the caller's team (Pattern B).

Cross-team isolation (T-12 equivalent of T-11-04-01):
* Site-membership probe runs FIRST. RLS isolates the DCSite lookup; a
  cross-team site_id returns 404 site_not_found_or_no_access (not 403)
  to avoid leaking site existence in other teams. Verbatim mirror of
  firewalls.py:109-119.

Logging allowlist (mirrors T-11-04-03):
* Only team_id / site_id / path_count / finding_count. Never hop content
  or evidence blobs.
"""
```

**Imports pattern** (verbatim from `firewalls.py:35-57`):
```python
from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, text

from app.auth.clerk import ClerkPrincipal, require_role
from app.auth.deps import resolve_team_from_clerk_org
from app.db.models import (
    AsymmetryFindingORM,
    ComputedPathORM,
    DCSite,
    PathDivergenceFindingORM,
    Team,
)
from app.db.session import get_sessionmaker
from app.schemas.paths import (
    AsymmetryFindingResponse,
    NetworkPath,
    PathDivergenceResponse,
    RecomputeResp,
)

router = APIRouter(prefix="/v1", tags=["paths"])
_log = structlog.get_logger("app.paths")

_READ_ROLES = ("owner", "admin", "member", "basic_member")
_OWNER_ROLES = ("owner",)
```

**Site-membership probe + RLS GUC pattern** (verbatim from `firewalls.py:101-119`):
```python
@router.get("/sites/{site_id}/paths", response_model=list[NetworkPath])
async def get_site_paths(
    site_id: uuid.UUID,
    principal: ClerkPrincipal = Depends(require_role(*_READ_ROLES)),  # noqa: B008
    team: Team = Depends(resolve_team_from_clerk_org),  # noqa: B008
) -> list[NetworkPath]:
    _ = principal
    sm = get_sessionmaker()
    async with sm() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team.id)},
        )
        # Site-membership probe FIRST — RLS scopes lookup to caller's team
        exists = await session.execute(
            select(DCSite.id).where(DCSite.id == site_id)
        )
        if exists.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="site_not_found_or_no_access",
            )
        # ... main query against ComputedPathORM with DISTINCT ON (pair, direction)
```

**Owner-gated POST recompute** (mirror `create_site` from `agent.py:63-105` for `require_role("owner")`):
```python
@router.post(
    "/sites/{site_id}/paths/recompute",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=RecomputeResp,
)
async def recompute_site_paths(
    site_id: uuid.UUID,
    principal: ClerkPrincipal = Depends(require_role(*_OWNER_ROLES)),  # noqa: B008
    team: Team = Depends(resolve_team_from_clerk_org),  # noqa: B008
) -> RecomputeResp:
    """D-14 + D-04 on-demand recompute. Coalesces concurrent calls per site_id."""
    # ... site-membership probe FIRST (same pattern)
    # ... then enqueue: await recompute_paths_for_site.kiq(site_id=site_id, on_demand=True)
```

---

### `backend/app/routes/agent.py` (MODIFIED — replace `push_routes` + `push_flows` stubs)

**Analog:** existing `push_firewall_rules` in this file (lines 174-228)

**Replace docstring** (CRITICAL — fix Pitfall 2):
- Old (line 113, 129): `"... Phase 10 logs only — Phase 11 persists."`
- New: `"... Phase 12 persists; payload validated via Pydantic, INSERT under RLS GUC."`

**Persistence pattern — copy verbatim from `push_firewall_rules` lines 190-217**:
```python
@router.post("/agent/routes", status_code=status.HTTP_202_ACCEPTED)
async def push_routes(
    body: RoutesPushBody,
    principal: DCSitePrincipal = Depends(require_site_token),  # noqa: B008
) -> dict[str, bool]:
    """Phase 12 D-15 — persist route batch under RLS GUC.

    Snapshot-per-pull semantics: this push REPLACES all rows for
    (site_id, device_host) older than this collected_at (planner picks
    delete-then-insert vs upsert+prune; mirror Phase 11 D-10 lifecycle).

    Pattern G credential allowlist: logs site_id / team_id / device_host /
    collected_at / count. Never logs raw route content.
    """
    collected_at = datetime.fromisoformat(body.collected_at.replace("Z", "+00:00"))
    sm = get_sessionmaker()
    async with sm() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(principal.team_id)},
        )
        if body.routes:
            await session.execute(
                pg_insert(RouteRecordORM).values([
                    {
                        "record_id": uuid.uuid4(),
                        "team_id": uuid.UUID(principal.team_id),
                        "site_id": uuid.UUID(body.site_id),
                        "device_host": body.device_host,
                        "collected_at": collected_at,
                        "prefix": r.prefix,
                        "next_hop": r.next_hop,
                        "protocol": r.protocol,
                        "metric": r.metric,
                        "as_path": r.as_path,
                    }
                    for r in body.routes
                ])
            )
    _log.info(
        "agent_routes_received",
        site_id=str(principal.site_id),
        team_id=str(principal.team_id),
        device_host=body.device_host,
        collected_at=body.collected_at,
        count=len(body.routes),
    )
    return {"ok": True}
```

`push_flows` follows the identical shape using `NetFlowRecordORM`.

---

### `backend/app/notifications/slack.py` (NEW — extract from inline)

**Analog:** `backend/app/queue/tasks/scan_repo.py:299-341` (inline Slack dispatcher — extract verbatim)

**Source (inline today)** — lines 299-341:
```python
sm9 = get_sessionmaker()
async with sm9() as slack_session:
    slack_row = (await slack_session.execute(
        text("SELECT s.source, t.slack_webhook_url "
             "FROM scans s JOIN teams t ON t.id = s.team_id "
             "WHERE s.id = :id"),
        {"id": scan_id},
    )).one_or_none()
# ... critical_count check ...
try:
    async with httpx.AsyncClient() as http_client:
        await http_client.post(
            slack_row.slack_webhook_url,
            json={"text": (
                f":rotating_light: *Critical findings detected* in `{repo}`\n"
                f"{critical_count} Critical finding(s) found. "
                f"View scan: /scans/{scan_id}"
            )},
            timeout=5.0,
        )
    log_ctx.info("scan_repo.slack_alert_sent", repo=repo)
except Exception as slack_exc:
    log_ctx.warning("scan_repo.slack_alert_failed", error=repr(slack_exc))
    sentry_sdk.capture_exception(slack_exc)
```

**Extract to** (verbatim from RESEARCH §Pattern 6):
```python
# backend/app/notifications/slack.py — NEW MODULE
"""Team-scoped Slack webhook dispatcher (extracted from scan_repo.py:299-341).

Two callers in Phase 12:
* scan_repo (Phase 8 Critical-findings alert) — collapses inline block.
* path_compute (Phase 12 NFN-02 asymmetry alert) — new call site.

Failure posture: swallow + structlog.warn + sentry_sdk.capture_exception.
Never re-raise — a bad Slack endpoint must NOT abort the calling task.
"""
from __future__ import annotations

import httpx
import sentry_sdk
import structlog
from sqlalchemy import text

from app.db.session import get_sessionmaker

_log = structlog.get_logger("app.notifications.slack")


async def send_team_slack(*, team_id: str, message: str, log_ctx_key: str) -> None:
    """Look up team's slack_webhook_url, POST message; swallow + Sentry-capture."""
    sm = get_sessionmaker()
    async with sm() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": team_id},
        )
        row = (await session.execute(
            text("SELECT slack_webhook_url FROM teams WHERE id = :id"),
            {"id": team_id},
        )).one_or_none()
    if row is None or row.slack_webhook_url is None:
        return
    try:
        async with httpx.AsyncClient() as client:
            await client.post(row.slack_webhook_url, json={"text": message}, timeout=5.0)
        _log.info(f"{log_ctx_key}.slack_alert_sent")
    except Exception as exc:
        _log.warning(f"{log_ctx_key}.slack_alert_failed", error=repr(exc))
        sentry_sdk.capture_exception(exc)
```

Then `scan_repo.py:299-341` collapses to:
```python
if slack_row.source == "webhook" and critical_count >= 1:
    await send_team_slack(
        team_id=str(team_id),
        message=(
            f":rotating_light: *Critical findings detected* in `{repo}`\n"
            f"{critical_count} Critical finding(s) found. View scan: /scans/{scan_id}"
        ),
        log_ctx_key="scan_repo",
    )
```

---

### `backend/app/queue/tasks/path_compute.py` (NEW — taskiq cron task)

**Analog:** `backend/app/queue/tasks/firewall_prune.py` (cron task + team-walk + RLS GUC, lines 30-80)

**Imports + module-level pattern** (verbatim from `firewall_prune.py` lines 20-30):
```python
from __future__ import annotations

import os
from uuid import UUID

import structlog
from sqlalchemy import text

from app.db.session import get_sessionmaker
from app.queue.broker import broker

_log = structlog.get_logger("app.tasks.path_compute")
_K_DEFAULT = int(os.environ.get("PATH_COMPUTE_TOP_K", "200"))
```

**Cron task + team-walk + RLS GUC pattern** (mirror `prune_firewall_snapshots` lines 33-80):
```python
@broker.task(
    task_name="recompute_paths_all_sites",
    schedule=[{"cron": "*/15 * * * *"}],   # D-04 — every 15 min
)
async def recompute_paths_all_sites() -> dict[str, int]:
    """D-04 fan-out: enqueue per-site compute under each team's RLS context."""
    sm = get_sessionmaker()
    enqueued = 0
    async with sm() as session:
        team_rows = (await session.execute(text("SELECT id FROM teams"))).all()
        team_ids = [str(row[0]) for row in team_rows]
        for team_id in team_ids:
            async with session.begin():
                await session.execute(
                    text("SELECT set_config('app.current_team_id', :t, true)"),
                    {"t": team_id},
                )
                site_rows = (
                    await session.execute(text("SELECT id FROM dc_sites"))
                ).all()
            for (site_id,) in site_rows:
                await recompute_paths_for_site.kiq(site_id=site_id)
                enqueued += 1
    _log.info("path_recompute_fanout", sites=enqueued, teams_scanned=len(team_ids))
    return {"enqueued": enqueued}


@broker.task(task_name="recompute_paths_for_site")
async def recompute_paths_for_site(
    site_id: UUID, *, on_demand: bool = False
) -> dict[str, int]:
    """D-04 per-site compute: top-K NetFlow pairs → forward+return paths →
    asymmetry detect → classify → impact score → reconcile findings →
    NFN-02 alert on transitions."""
    # ... structured logging allowlist: site_id, pair_count, asymmetry_count
```

**Cron offset for prune coordination** (Pitfall 5):
```python
@broker.task(
    task_name="netflow_records_prune",
    schedule=[{"cron": "7,22,37,52 * * * *"}],   # offset from path_compute
)
async def prune_netflow_records() -> dict[str, int]:
    ...  # verbatim shape from firewall_prune
```

---

### `backend/app/queue/tasks/path_compute_prune.py` (NEW)

**Analog:** `backend/app/queue/tasks/firewall_prune.py` (verbatim — change table name + TTL env var)

Copy entire `firewall_prune.py`, substitute:
- `firewall_ruleset_snapshots` → `computed_paths`
- `FIREWALL_SNAPSHOT_TTL_DAYS` → `PATH_SNAPSHOT_TTL_DAYS` (default 14, per CONTEXT discretion)
- `snapshot_ts` → `computed_at`
- task name `firewall_prune` → `path_compute_prune`
- Logger name `app.tasks.firewall_prune` → `app.tasks.path_compute_prune`

For NetFlow prune, parallel module with `NETFLOW_RECORD_TTL_HOURS` (default 24, per RESEARCH Runtime State Inventory).

---

### `backend/app/security/pathcompute/lpm.py` (NEW — pytricia wrapper)

**Analog:** None (greenfield — but use pytricia per RESEARCH "Don't Hand-Roll")

**Shape:** Pure function module, no I/O, returns deterministic next-hop per (src_ip, dst_ip).

**Required docstring elements** (per Pitfall 3):
- Document ECMP resolution rule: "pick lexicographically lowest next-hop, mirroring `vty show ip route` line-order behavior."
- Pull pytricia install assertion in `__init__.py` (skip if not installed → fall back to per-row scan with warning).

---

### `backend/app/security/pathcompute/{forward,pair,correlate,asymmetry,classify,impact}.py` (NEW)

**Analog:** RESEARCH §Code Examples Patterns 2-5 (already documented inline)

**Pattern (apply to all six pure-compute modules):**
- `from __future__ import annotations` (project standard)
- Top-of-module structlog logger: `_log = structlog.get_logger("app.security.pathcompute.<name>")`
- Pure functions: input types from `app.schemas.paths` (NetworkPath, PathHop) + ORM rows for routes/NAT.
- Outputs: dataclass-or-Pydantic for cross-module returns; raw tuples acceptable for helpers.
- Per-rule try/except inside `correlate.py` for CIDR parsing (Pitfall 8 — `firewall_rules.src_cidr` is TEXT not INET).

**Classifier specifics** (`classify.py` — per D-08/D-09 + RESEARCH Pattern 5):
- `score_nat(forward, ret, nat_rules) -> float` (0.0-1.0)
- `score_leak(forward_routes, ret_routes) -> float`
- `score_local_pref(forward_routes, ret_routes) -> float`
- `classify(...)` returns `(cause: str, confidence: float, evidence: dict)` with `UNKNOWN` fallback (D-09).
- Tiebreaker precedence dict: `{"NAT_ASYMMETRY": 0, "ROUTE_LEAK": 1, "BGP_LOCAL_PREF": 2}` (D-08 fixed order).
- Threshold constant: `_CAUSE_THRESHOLD = 0.4` (env-overridable per CONTEXT discretion).

---

### `cli/infracanvas/security/network/net_010.py` (NEW Python detector)

**Analog:** `cli/infracanvas/security/engine.py` (Finding-emit shape) + RESEARCH §Specifics sketch

**Finding emission shape** (mirror `NetworkFinding` from `cli/infracanvas/graph/models.py:99-122`):
```python
"""NET-010 / ASY-03 — stateful firewall sees only one leg of an
asymmetric pair (D-11).

Python detector (NOT YAML rule) per Phase 12 D-11. The YAML rule engine
cannot express "compare two path objects" without materially expanding
operators for one rule — see Phase 12 RESEARCH §"Don't Hand-Roll".

Catalog integration: emits NetworkFinding with rule_id="NET-010" and
source="network" so findings aggregate through the existing pipeline
(Phase 2 D-09 / Phase 3 D-12). The rules catalog YAML count stays at 51
(this is a Python detector, not a YAML rule — see Pitfall 7).
"""
from __future__ import annotations

from infracanvas.graph.models import NetworkFinding, NetworkPath


def detect_stateful_firewall_asymmetry(
    forward: NetworkPath,
    ret: NetworkPath,
    stateful_firewalls: set[str],
) -> list[NetworkFinding]:
    """Fire NET-010 when a stateful firewall is on exactly one path leg."""
    fwd_nodes = {h.node_id for h in forward.hops}
    ret_nodes = {h.node_id for h in ret.hops}
    one_legged = (fwd_nodes ^ ret_nodes) & stateful_firewalls
    findings: list[NetworkFinding] = []
    for node_id in sorted(one_legged):
        findings.append(NetworkFinding(
            source_ip=forward.hops[0].source_ip if forward.hops else "",
            dest_ip=forward.hops[-1].dest_ip if forward.hops else "",
            protocol="",
            port=0,
            severity="high",
            title=f"Stateful firewall {node_id} sees only one leg of asymmetric pair",
            description=(
                f"Forward path {forward.id} and return path {ret.id} traverse "
                f"different stateful firewalls. {node_id} will drop return "
                f"traffic with no matching session entry."
            ),
            remediation=(
                "Symmetrize routing so both legs traverse the same stateful "
                "firewall, OR disable stateful inspection on this asymmetric pair."
            ),
            rule_id="NET-010",
            source="network",
            path_id=forward.id,
            hop_id=node_id,
            evidence={"forward_only": sorted(fwd_nodes - ret_nodes & {node_id}),
                      "return_only": sorted(ret_nodes - fwd_nodes & {node_id})},
        ))
    return findings
```

---

### `cli/tests/test_flowmap_network_rules.py` (MODIFIED — Pitfall 6)

**Analog:** existing `test_net_010_reserved_for_phase_3b` lines 71-77

**KEEP the YAML-catalog assertion** (D-11 + Pitfall 6: NET-010 is a Python detector, NOT a YAML rule — the YAML catalog assertion stays valid):
```python
def test_net_010_not_in_yaml_catalog_phase_12(self):
    """Phase 12 D-11: NET-010 is a Python detector, NOT a YAML rule.

    The path-aware compare-two-paths logic is in
    `infracanvas.security.network.net_010` (Python). The YAML catalog
    intentionally does not carry NET-010 — see test_net_010_python_detector_active.
    """
    rules = load_rules()
    ids = {r.id for r in rules}
    assert "NET-010" not in ids, (
        "NET-010 is a Python detector (Phase 12 D-11), NOT a YAML rule. "
        "If you intend to add a YAML version, update the rules-catalog "
        "count test in test_security.py and re-verify Phase 12 D-11."
    )
```

**ADD new test** asserting Python detector exists + emits finding with `rule_id="NET-010"`:
```python
def test_net_010_python_detector_active(self):
    """Phase 12 D-11: NET-010 detector module exists and emits findings."""
    from infracanvas.security.network.net_010 import detect_stateful_firewall_asymmetry
    # ... synthesize forward + return + stateful_firewalls fixture ...
    findings = detect_stateful_firewall_asymmetry(forward, ret, {"fw-a"})
    assert any(f.rule_id == "NET-010" for f in findings)
    assert all(f.source == "network" for f in findings)
```

---

### `cli/tests/test_security.py` (MODIFIED — Pitfall 7 verify)

**Analog:** existing rule-count assertion line 64

**Verify count stays 51** (NET-010 ships as Python detector outside YAML catalog — D-11 + Pitfall 7):
- If the existing assertion is `>= 51`, no change needed.
- If `== 51`, no change needed (Python detector outside catalog).
- If `== 52`, the plan must downgrade back to 51 (D-11 keeps NET-010 out of YAML catalog).

> Planner: confirm the existing assertion text before modifying. The intent per D-11 is that the YAML catalog count is UNCHANGED.

---

### `viewer/src/components/flowmap/edges/PathEdge.tsx` (MODIFIED — dual-strand + dashed-red)

**Analog:** itself (lines 18-29 forward/return strand styles)

**Existing dual-lane pattern** (verbatim — lines 18-29):
```tsx
const forwardStyle = {
  stroke: '#3B82F6',
  strokeWidth: 1.75,
  fill: 'none',
  transform: 'translate(0, -3px)',
} as const
const returnStyle = {
  stroke: '#F97316',
  strokeWidth: 1.75,
  fill: 'none',
  transform: 'translate(0, 3px)',
} as const
```

**Extend `PathEdgeData` interface** (lines 3-6):
```tsx
interface PathEdgeData {
  direction?: 'forward' | 'return' | 'both'
  pathId?: string
  /** Phase 12 FMV-02 — when true, render this leg with red dashed stroke */
  asymmetricForward?: boolean
  asymmetricReturn?: boolean
}
```

**Conditional style override** (insert after lines 18-29):
```tsx
const ASYMMETRIC_STROKE = '#DC2626'  // tailwind red-600
const ASYMMETRIC_DASH = '4 3'         // 4-on 3-off

const fwdEffective = asymmetricForward
  ? { ...forwardStyle, stroke: ASYMMETRIC_STROKE, strokeDasharray: ASYMMETRIC_DASH }
  : forwardStyle
const retEffective = asymmetricReturn
  ? { ...returnStyle,  stroke: ASYMMETRIC_STROKE, strokeDasharray: ASYMMETRIC_DASH }
  : returnStyle
```

**Apply to existing BaseEdge** (lines 36-43, 44-51 — swap `style={forwardStyle}` for `style={fwdEffective}`).

---

### `viewer/src/components/flowmap/PathDetailPanel.tsx` (MODIFIED — Asymmetry tab)

**Analog:** itself (lines 61-67 tabs array — conditional inclusion pattern)

**Existing conditional-tab pattern** (verbatim — lines 59-67):
```tsx
const hasRoutes = ROUTES_ELIGIBLE_TYPES.has(node.type);
const hasCost = node.cost.monthly_usd > 0;
const tabs: Array<{ id: Tab; label: string; icon: typeof FileText }> = [
  { id: 'overview', label: 'Overview', icon: FileText },
  { id: 'findings', label: `Findings (${node.findings.length})`, icon: Shield },
  { id: 'attributes', label: 'Attributes', icon: Code },
  ...(hasRoutes ? [{ id: 'routes' as const, label: 'Routes', icon: List }] : []),
  ...(hasCost ? [{ id: 'cost' as const, label: 'Cost', icon: DollarSign }] : []),
];
```

**Extend** (per Pitfall 12 Option (a) — extend existing panel, don't fork):
```tsx
type Tab = 'overview' | 'findings' | 'attributes' | 'routes' | 'cost' | 'asymmetry';

// Add to existing constants
const selectedPath = useViewerStoreOrSingleton((s) => s.selectedPath);
const hasAsymmetry = selectedPath !== null && /* asymmetry attached to path */;

const tabs = [
  // ... existing tabs ...
  ...(hasAsymmetry ? [{ id: 'asymmetry' as const, label: 'Asymmetry', icon: AlertTriangle }] : []),
];

// Add content branch
{activeTab === 'asymmetry' && hasAsymmetry && <AsymmetryTab path={selectedPath!} />}
```

**Side-by-side hop table sub-component pattern** (mirror `RoutesTab` lines 200-272 — table with `<thead>`/`<tbody>` + per-row delta highlight):
- Two columns: Forward hop / Return hop, indexed by hop_index.
- Mismatched rows: background `#7F1D1D40` (red tint, opacity).
- Same `color: '#94A3B8'` / `borderTop: '1px solid #252d3d'` styling tokens.

---

### `viewer/src/store.ts` (MODIFIED — verify `selectedPath`, extend hydration)

**Analog:** itself (lines 42-43 `selectedPath` slice + line 61 `setSelectedPath` action — already present)

**Confirmed present** (lines 42, 61, and corresponding action in stateCreator):
```ts
selectedPath: NetworkPath | null;
setSelectedPath: (path: NetworkPath | null) => void;
```

> No new store slice required. The `selectedPath` slice already exists from Phase 3. Phase 12 FMV-02 reuses it for asymmetry display. The CONTEXT mention of `selectedEdge` was a misnomer — the store keys on `selectedPath` (a NetworkPath object), not a raw edge id.

**Optional addition** (planner picks): a `hydratePathsFromApi(siteId)` action that fetches `/v1/sites/{site_id}/paths` and populates `graph.network_paths` for dashboard-only rendering. Mirror existing `setGraph` action shape.

---

### `viewer/src/__tests__/flowmap/PathEdge.test.tsx` (MODIFIED — asymmetric assertions)

**Analog:** itself (lines 10-28 synthetic EdgeProps pattern — Pitfall 11)

**Extend `renderEdge` to accept asymmetric flags** (mirror existing helper lines 10-28):
```tsx
function renderEdge(
  direction: 'forward' | 'return' | 'both',
  asymmetric: { forward?: boolean; return?: boolean } = {},
) {
  const props = {
    // ... existing fields ...
    data: { direction, asymmetricForward: asymmetric.forward, asymmetricReturn: asymmetric.return },
  } as unknown as EdgeProps
  return render(<svg><PathEdge {...props} /></svg>)
}
```

**Add tests** (mirror lines 35-51 — pattern: render then assert stroke attribute):
```tsx
test('asymmetricForward=true renders forward path with red dashed stroke', () => {
  const { container } = renderEdge('both', { forward: true })
  const paths = container.querySelectorAll('path')
  // Find the forward path by marker-end attribute, assert stroke + dasharray
  const fwd = Array.from(paths).find(p => p.getAttribute('marker-end')?.includes('forward'))
  expect(fwd?.getAttribute('stroke')).toBe('#DC2626')
  expect(fwd?.getAttribute('stroke-dasharray')).toBeTruthy()
})
```

> Critical: do NOT render `<ReactFlow>` — jsdom can't measure nodes (existing comment lines 5-9).

---

## Shared Patterns

### Pattern A — RLS team isolation (verbatim from Phase 11)
**Source:** `backend/migrations/versions/20260510_011_firewall_tables.py:88-97` (parent table) + lines 131-152 (child join policy)
**Apply to:** Every new table in migrations 012 + 013

```sql
ALTER TABLE <name> ENABLE ROW LEVEL SECURITY;
ALTER TABLE <name> FORCE ROW LEVEL SECURITY;
CREATE POLICY <name>_team_isolation ON <name>
  USING (team_id = current_setting('app.current_team_id', true)::uuid)
  WITH CHECK (team_id = current_setting('app.current_team_id', true)::uuid);
GRANT SELECT, INSERT, UPDATE, DELETE ON <name> TO infracanvas_app;
```

**FORCE** (line 89) catches any future `BYPASSRLS` role regressions — keep it on every Phase 12 table.

### Pattern B — RLS GUC set inside transaction
**Source:** `backend/app/routes/firewalls.py:103-107` + `agent.py:82-85` + `firewall_prune.py:62-66`
**Apply to:** Every route handler, every taskiq task body that touches RLS-scoped tables

```python
async with sm() as session, session.begin():
    await session.execute(
        text("SELECT set_config('app.current_team_id', :t, true)"),
        {"t": str(team.id)},  # or str(principal.team_id) for site-token paths
    )
    # ... real queries here ...
```

### Pattern C — Site-membership probe FIRST (cross-team 404)
**Source:** `backend/app/routes/firewalls.py:109-119`
**Apply to:** Every Phase 12 read endpoint (`GET /v1/sites/{site_id}/paths`, `GET /v1/sites/{site_id}/asymmetries`, `POST /v1/sites/{site_id}/paths/recompute`)

```python
exists = await session.execute(select(DCSite.id).where(DCSite.id == site_id))
if exists.scalar_one_or_none() is None:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="site_not_found_or_no_access",
    )
```

Returns 404 (not 403) to avoid leaking site existence — RLS already scopes the probe to the caller's team, so cross-team `site_id` resolves to None.

### Pattern D — Site-token Bearer auth (agent push)
**Source:** `backend/app/auth/site_token.py:38-75` (`require_site_token` dependency)
**Apply to:** Any new agent push endpoint (Phase 12 adds NONE — only consumes existing routes/flows; just reuse `Depends(require_site_token)` if any new ingest emerges)

```python
principal: DCSitePrincipal = Depends(require_site_token),  # noqa: B008
```

After this dep resolves, the handler MUST call Pattern B (`set_config('app.current_team_id', ...)`) before any RLS-scoped query.

### Pattern E — Clerk JWT auth (dashboard read)
**Source:** `backend/app/routes/firewalls.py:88-89`
**Apply to:** All three Phase 12 read endpoints

```python
principal: ClerkPrincipal = Depends(require_role(*_READ_ROLES)),  # noqa: B008
team: Team = Depends(resolve_team_from_clerk_org),  # noqa: B008
```

For the owner-gated recompute endpoint, use `require_role("owner")` (mirror `create_site` from `agent.py:66`).

### Pattern F — Taskiq cron task with team-walk
**Source:** `backend/app/queue/tasks/firewall_prune.py:33-80`
**Apply to:** `path_compute.py` recompute job + `path_compute_prune.py` + `netflow_records_prune` task

```python
@broker.task(task_name="<name>", schedule=[{"cron": "<expr>"}])
async def <name>() -> dict[str, int]:
    sm = get_sessionmaker()
    async with sm() as session:
        team_rows = (await session.execute(text("SELECT id FROM teams"))).all()
        team_ids = [str(row[0]) for row in team_rows]
        for team_id in team_ids:
            async with session.begin():
                await session.execute(
                    text("SELECT set_config('app.current_team_id', :t, true)"),
                    {"t": team_id},
                )
                # ... per-team work here ...
    _log.info("<event>", ...)
    return {"<count>": N}
```

### Pattern G — Logging credential allowlist
**Source:** `firewalls.py` module docstring lines 30-33 + every `_log.info` call in `routes/agent.py`
**Apply to:** Every new route handler + taskiq task

Allowed log fields: `team_id`, `site_id`, `snapshot_id`, `firewall_id`, `vendor`, `source`, `count`, `path_count`, `finding_count`.
**Never log:** `as_path` raw content, NetFlow IPs (operator-private), `evidence` JSONB blobs, slack webhook URL, raw_blob.

### Pattern H — Idempotent push via ON CONFLICT DO NOTHING
**Source:** `backend/app/routes/agent.py:144-171` (`_upsert_snapshot_parent` helper)
**Apply to:** Phase 12 `push_routes` / `push_flows` if planner chooses upsert vs delete-then-insert for snapshot-per-pull semantics

```python
stmt = pg_insert(<ORM>).values(...).on_conflict_do_nothing(index_elements=["<pk>"])
await session.execute(stmt)
```

### Pattern I — Pydantic v2 bounded list (DoS-prevention)
**Source:** `backend/app/schemas/firewall.py:79` (`rules: list[FirewallRule] = Field(..., max_length=50000)`)
**Apply to:** Any new push body schema. For Phase 12 reads, no max needed on responses (server controls size).

### Pattern J — Slack dispatcher reuse (after extraction)
**Source:** `backend/app/notifications/slack.py` (NEW — Phase 12 creates from `scan_repo.py:299-341`)
**Apply to:** `path_compute.py` NFN-02 alert + `scan_repo.py` Phase 8 alert (refactor)

```python
from app.notifications.slack import send_team_slack

await send_team_slack(
    team_id=str(team_id),
    message=NFN_02_TEMPLATE.format(...),
    log_ctx_key="path_compute",
)
```

NFN-02 message template (per CONTEXT §Specifics):
```
🔴 Asymmetric path detected — site {site_name}
Pair: {src_cidr} → {dst_cidr}
Cause: {cause}  (confidence {confidence:.0%})
Impact: {bytes_per_sec_human} / {firewall_count} stateful firewall(s)
View: {dashboard_url}/sites/{site_id}/asymmetries/{finding_id}
```

### Pattern K — ORM naming with `ORM` suffix
**Source:** `backend/app/db/models.py:240-245` (docstring explaining `FirewallRuleORM` vs Pydantic `FirewallRule`)
**Apply to:** Every new ORM in Phase 12

`RouteRecordORM`, `NetFlowRecordORM`, `ComputedPathORM`, `AsymmetryFindingORM`, `PathDivergenceFindingORM` — Pydantic re-exports (`NetworkPath`, `PathHop`) keep bare names.

### Pattern L — Pydantic model import-not-redeclare
**Source:** `cli/infracanvas/graph/models.py:125-150` (`PathHop`, `NetworkPath` — already shaped for this phase)
**Apply to:** `backend/app/schemas/paths.py`

Per Pitfall 9 — `cli` is already a backend dep (`infracanvas @ file:../cli` in `backend/pyproject.toml`). Re-export via:
```python
from infracanvas.graph.models import NetworkPath, PathHop  # noqa: F401
```

### Pattern M — Viewer conditional tab inclusion
**Source:** `viewer/src/components/flowmap/PathDetailPanel.tsx:65-66`
**Apply to:** Phase 12 Asymmetry tab

```tsx
...(<condition> ? [{ id: '<id>' as const, label: '<label>', icon: <Icon> }] : []),
```

### Pattern N — Viewer test pattern (bypass ReactFlow)
**Source:** `viewer/src/__tests__/flowmap/PathEdge.test.tsx:5-28` (synthetic EdgeProps)
**Apply to:** Phase 12 FMV-02 viewer tests

jsdom cannot measure nodes; render `<PathEdge>` directly inside `<svg>` with synthetic `EdgeProps`. Same applies to any edge-aware test.

---

## No Analog Found

| File | Role | Reason |
|------|------|--------|
| `backend/app/security/pathcompute/lpm.py` | pytricia wrapper | No existing trie code in the repo. Use `pytricia` library per RESEARCH "Don't Hand-Roll" + Pitfall 3 (ECMP determinism rule). Planner ships a thin Python wrapper. |
| `backend/app/security/pathcompute/forward.py` | hop expansion | Net-new compute logic. RESEARCH §Pattern 2 gives the function sketch; no codebase analog beyond "pure module with `from __future__ import annotations` + structlog logger." |

These two files have no in-repo analog but follow RESEARCH §Code Examples shapes verbatim. Planner must NOT invent additional structure.

---

## Metadata

**Analog search scope:**
- `backend/migrations/versions/` (12 files scanned, Phase 11 migration is the canonical analog)
- `backend/app/routes/` (9 files; firewalls.py + agent.py are the canonical analogs)
- `backend/app/queue/tasks/` (3 files; firewall_prune.py + scan_repo.py:299-341 are the canonical analogs)
- `backend/app/schemas/` (5 files; firewall.py + agent.py are the canonical analogs)
- `backend/app/auth/` (4 files; site_token.py is the agent-push analog, clerk.py is the dashboard-read analog)
- `backend/app/db/models.py` (single file; FirewallRulesetSnapshot + FirewallRuleORM are the canonical analogs)
- `viewer/src/components/flowmap/` (3 components + tests scanned; PathEdge.tsx + PathDetailPanel.tsx are the in-place modification targets)
- `viewer/src/store.ts` (selectedPath slice already present from Phase 3 — no schema gap)
- `cli/infracanvas/security/` (rules + engine confirmed; no path-aware Python detector exists yet — Phase 12 creates `network/` subpackage)
- `cli/tests/test_flowmap_network_rules.py` + `cli/tests/test_security.py` (reservation tests confirmed at line 71 + line 64 respectively)

**Files scanned:** 28 source files across backend/viewer/cli + 12 migration files + 8 viewer tests

**Pattern extraction date:** 2026-05-17

**Confidence:** HIGH — every Phase 12 backend file has a Phase 10/11 analog at ≥ "role-match" quality; viewer changes are extensions of existing modules; the two "no analog" files (lpm.py, forward.py) are documented as such with library guidance.
