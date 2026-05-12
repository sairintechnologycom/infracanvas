"""DC Agent routes (Phase 10 DCA-05 + Phase 11 firewall ingest).

POST /v1/sites                    — Clerk-authed, owner role; one-time site_token issuance
POST /v1/agent/routes             — site-token-authed; agent push for routing data
POST /v1/agent/flows              — site-token-authed; agent push for NetFlow records
POST /v1/agent/firewall-rules     — Phase 11 D-08/D-18 firewall access-rule ingest
POST /v1/agent/firewall-nat       — Phase 11 D-07/D-18 firewall NAT ingest
POST /v1/agent/firewall-objects   — Phase 11 D-09/D-18 firewall objects ingest

Security posture:
- POST /v1/sites uses require_role("owner") (T-10-02-04 mitigation)
- Agent push routes use require_site_token, NOT require_principal (Pitfall 6)
- site_token plaintext returned ONCE; only SHA-256 hash stored (T-10-02-01, -03)
- T-10-02-06: payload bounds enforced in RoutesPushBody/FlowsPushBody (max 10 000)
- T-11-02-01: firewall push bodies bounded at 50 000 per list (Phase 11 schemas)
- Phase 11 firewall handlers set RLS GUC (Pattern B) and use ON CONFLICT DO NOTHING
  on snapshot_id (Pattern E — idempotent parent insert across the 3 endpoints)
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, status
from sqlalchemy import insert, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.clerk import ClerkPrincipal, require_role
from app.auth.deps import resolve_team_from_clerk_org
from app.auth.site_token import DCSitePrincipal, require_site_token
from app.db.models import (
    DCSite,
    FirewallNATRuleORM,
    FirewallObjectORM,
    FirewallRuleORM,
    FirewallRulesetSnapshot,
    Team,
)
from app.db.session import get_sessionmaker
from app.schemas.agent import (
    CreateSiteBody,
    CreateSiteResp,
    FlowsPushBody,
    RoutesPushBody,
)
from app.schemas.firewall import (
    FirewallNATPushBody,
    FirewallObjectsPushBody,
    FirewallRulesPushBody,
)

router = APIRouter(prefix="/v1", tags=["agent"])
_log = structlog.get_logger("app.agent")

_OWNER_ROLES = ("owner",)


@router.post("/sites", status_code=status.HTTP_201_CREATED, response_model=CreateSiteResp)
async def create_site(
    body: CreateSiteBody,
    principal: ClerkPrincipal = Depends(require_role(*_OWNER_ROLES)),  # noqa: B008
    team: Team = Depends(resolve_team_from_clerk_org),  # noqa: B008
) -> CreateSiteResp:
    """Create a new DC site for the team and return a one-time plaintext token.

    Per CONTEXT.md D-03: token is returned ONCE; only its SHA-256 hash is stored.
    T-10-02-01: secrets.token_urlsafe(32) provides 32 bytes of entropy.
    T-10-02-03: only SHA-256 lookup hash persisted — plaintext never stored.
    T-10-02-04: require_role("owner") gate.
    """
    raw_token = "ic_site_" + secrets.token_urlsafe(32)
    lookup_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    site_id = uuid4()

    sm = get_sessionmaker()
    async with sm() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team.id)},
        )
        await session.execute(
            insert(DCSite).values(
                id=site_id,
                team_id=team.id,
                name=body.name,
                token_lookup_hash=lookup_hash,
            )
        )

    _log.info(
        "dc_site_created",
        team_id=str(team.id),
        site_id=str(site_id),
        principal_id=principal.user_id,
    )
    return CreateSiteResp(
        site_id=str(site_id),
        name=body.name,
        site_token=raw_token,
    )


@router.post("/agent/routes", status_code=status.HTTP_202_ACCEPTED)
async def push_routes(
    body: RoutesPushBody,
    principal: DCSitePrincipal = Depends(require_site_token),  # noqa: B008
) -> dict[str, bool]:
    """Receive a routing-table batch from a DC agent. Phase 10 logs only — Phase 11 persists."""
    _log.info(
        "agent_routes_received",
        site_id=principal.site_id,
        team_id=principal.team_id,
        device_host=body.device_host,
        count=len(body.routes),
    )
    return {"ok": True}


@router.post("/agent/flows", status_code=status.HTTP_202_ACCEPTED)
async def push_flows(
    body: FlowsPushBody,
    principal: DCSitePrincipal = Depends(require_site_token),  # noqa: B008
) -> dict[str, bool]:
    """Receive a NetFlow batch from a DC agent. Phase 10 logs only — Phase 11 persists."""
    _log.info(
        "agent_flows_received",
        site_id=principal.site_id,
        team_id=principal.team_id,
        count=len(body.flows),
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# Phase 11 — firewall ingest (Pattern E idempotent + Pattern B RLS GUC-set)
# ---------------------------------------------------------------------------


async def _upsert_snapshot_parent(
    session: AsyncSession,
    body: FirewallRulesPushBody | FirewallNATPushBody | FirewallObjectsPushBody,
    principal: DCSitePrincipal,
) -> None:
    """Pattern E (RESEARCH Pattern 2) — idempotent parent insert.

    The three firewall push handlers may arrive in any order; whichever
    lands first creates the ``firewall_ruleset_snapshots`` parent row, the
    others skip via ``ON CONFLICT DO NOTHING`` on ``snapshot_id``. This
    removes ordering coupling between the rules / nat / objects endpoints
    and makes agent retries safe (T-11-03-04 mitigation).
    """
    snapshot_ts = datetime.fromisoformat(body.snapshot_ts.replace("Z", "+00:00"))
    stmt = (
        pg_insert(FirewallRulesetSnapshot)
        .values(
            snapshot_id=uuid.UUID(body.snapshot_id),
            team_id=uuid.UUID(principal.team_id),
            site_id=uuid.UUID(body.site_id),
            firewall_id=body.firewall_id,
            vendor=body.vendor,
            source=body.source,
            snapshot_ts=snapshot_ts,
        )
        .on_conflict_do_nothing(index_elements=["snapshot_id"])
    )
    await session.execute(stmt)


@router.post("/agent/firewall-rules", status_code=status.HTTP_202_ACCEPTED)
async def push_firewall_rules(
    body: FirewallRulesPushBody,
    principal: DCSitePrincipal = Depends(require_site_token),  # noqa: B008
) -> dict[str, bool]:
    """Phase 11 D-08/D-18 — receive firewall access-rule snapshot from DC agent.

    Idempotent on snapshot_id (Pattern E). Persists FirewallRulesetSnapshot
    parent + FirewallRuleORM children atomically. RLS-scoped to caller's
    team via ``app.current_team_id`` GUC set inside the transaction
    (Pattern B). Returns 202 Accepted on success.

    Pattern G — credential allowlist: logs only site_id, team_id,
    snapshot_id, firewall_id, vendor, source, count. NEVER logs token
    material or rule body content.
    """
    sm = get_sessionmaker()
    async with sm() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(principal.team_id)},
        )
        await _upsert_snapshot_parent(session, body, principal)
        if body.rules:
            await session.execute(
                pg_insert(FirewallRuleORM).values(
                    [
                        {
                            "rule_id": uuid.uuid4(),
                            "snapshot_id": uuid.UUID(body.snapshot_id),
                            "position": r.position,
                            "src_zone": r.src_zone,
                            "dst_zone": r.dst_zone,
                            "src_cidr": r.src_cidr,
                            "dst_cidr": r.dst_cidr,
                            "action": r.action,
                            "protocol": r.protocol,
                            "ports": r.ports,
                            "raw_blob": r.raw_blob,
                        }
                        for r in body.rules
                    ]
                )
            )
    _log.info(
        "agent_firewall_rules_received",
        site_id=str(principal.site_id),
        team_id=str(principal.team_id),
        snapshot_id=body.snapshot_id,
        firewall_id=body.firewall_id,
        vendor=body.vendor,
        source=body.source,
        count=len(body.rules),
    )
    return {"ok": True}


@router.post("/agent/firewall-nat", status_code=status.HTTP_202_ACCEPTED)
async def push_firewall_nat(
    body: FirewallNATPushBody,
    principal: DCSitePrincipal = Depends(require_site_token),  # noqa: B008
) -> dict[str, bool]:
    """Phase 11 D-07/D-18 — receive firewall NAT snapshot from DC agent.

    Pattern E idempotent on snapshot_id; Pattern B RLS GUC-set inside
    transaction. Persists FirewallRulesetSnapshot parent (ON CONFLICT
    DO NOTHING) + FirewallNATRuleORM children atomically.
    """
    sm = get_sessionmaker()
    async with sm() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(principal.team_id)},
        )
        await _upsert_snapshot_parent(session, body, principal)
        if body.nat_rules:
            await session.execute(
                pg_insert(FirewallNATRuleORM).values(
                    [
                        {
                            "nat_id": uuid.uuid4(),
                            "snapshot_id": uuid.UUID(body.snapshot_id),
                            "position": n.position,
                            "src_translation": n.src_translation,
                            "dst_translation": n.dst_translation,
                            "interface_in": n.interface_in,
                            "interface_out": n.interface_out,
                            "raw_blob": n.raw_blob,
                        }
                        for n in body.nat_rules
                    ]
                )
            )
    _log.info(
        "agent_firewall_nat_received",
        site_id=str(principal.site_id),
        team_id=str(principal.team_id),
        snapshot_id=body.snapshot_id,
        firewall_id=body.firewall_id,
        vendor=body.vendor,
        source=body.source,
        count=len(body.nat_rules),
    )
    return {"ok": True}


@router.post("/agent/firewall-objects", status_code=status.HTTP_202_ACCEPTED)
async def push_firewall_objects(
    body: FirewallObjectsPushBody,
    principal: DCSitePrincipal = Depends(require_site_token),  # noqa: B008
) -> dict[str, bool]:
    """Phase 11 D-09/D-18 — receive firewall object snapshot from DC agent.

    Pattern E idempotent on snapshot_id; Pattern B RLS GUC-set inside
    transaction. Persists FirewallRulesetSnapshot parent (ON CONFLICT
    DO NOTHING) + FirewallObjectORM children atomically. ``kind`` is
    validated by Pydantic at the boundary (host|network|group|service).
    """
    sm = get_sessionmaker()
    async with sm() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(principal.team_id)},
        )
        await _upsert_snapshot_parent(session, body, principal)
        if body.objects:
            await session.execute(
                pg_insert(FirewallObjectORM).values(
                    [
                        {
                            "object_id": uuid.uuid4(),
                            "snapshot_id": uuid.UUID(body.snapshot_id),
                            "kind": o.kind,
                            "name": o.name,
                            "value": o.value,
                            "raw_blob": o.raw_blob,
                        }
                        for o in body.objects
                    ]
                )
            )
    _log.info(
        "agent_firewall_objects_received",
        site_id=str(principal.site_id),
        team_id=str(principal.team_id),
        snapshot_id=body.snapshot_id,
        firewall_id=body.firewall_id,
        vendor=body.vendor,
        source=body.source,
        count=len(body.objects),
    )
    return {"ok": True}
