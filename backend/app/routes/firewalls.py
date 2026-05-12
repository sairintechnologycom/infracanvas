"""Phase 11 D-11 — read API for firewall snapshots.

Returns the latest ``FirewallRulesetSnapshot`` per ``firewall_id`` under a
site, with attached ``rules`` + ``nat_rules`` + ``objects``. RLS-scoped to
the caller's team via Clerk JWT + ``app.current_team_id`` GUC (Pattern B
from PATTERNS.md §"backend/app/routes/firewalls.py" and the read-side
analog from ``backend/app/routes/github.py`` ``list_installations_endpoint``).

Endpoints:

* ``GET /v1/sites/{site_id}/firewall-rules`` — latest-per-device snapshot
  envelope ``list[FirewallSnapshotResponse]``.

Auth posture (CC-2):

* ``Depends(require_role(*_READ_ROLES))`` — Clerk JWT required;
  ``test_requires_clerk_jwt`` regression-tests 401 on missing JWT.
* ``Depends(resolve_team_from_clerk_org)`` — Team resolved from JWT ``org_id``.
* ``set_config('app.current_team_id', :t, true)`` inside the transaction
  (Pattern B) — RLS isolates every query to the caller's team.

Cross-team isolation (T-11-04-01):

* Site-membership probe runs FIRST. RLS isolates the ``DCSite`` lookup to
  the caller's team — a cross-team ``site_id`` returns 404
  ``site_not_found_or_no_access`` (not 403; mirrors
  ``github.py:144-152`` ``list_repos_endpoint``) to avoid leaking
  existence of sites in other teams.

Logging (T-11-04-03):

* Allowlist — only ``team_id`` / ``site_id`` / ``snapshot_count``. No rule
  contents.
"""
from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, text

from app.auth.clerk import ClerkPrincipal, require_role
from app.auth.deps import resolve_team_from_clerk_org
from app.db.models import (
    DCSite,
    FirewallNATRuleORM,
    FirewallObjectORM,
    FirewallRuleORM,
    Team,
)
from app.db.session import get_sessionmaker
from app.schemas.firewall import FirewallNATRule, FirewallObject, FirewallRule

router = APIRouter(prefix="/v1", tags=["firewalls"])
_log = structlog.get_logger("app.firewalls")

_READ_ROLES = ("owner", "admin", "member", "basic_member")


class FirewallSnapshotResponse(BaseModel):
    """Per-device snapshot envelope returned by the read API.

    Mirrors the push-side envelope shape (``FirewallRulesPushBody`` +
    siblings in ``app.schemas.firewall``) so the read contract stays
    aligned with the agent ``→`` backend wire contract documented in
    ``agent/internal/push/types.go``.
    """

    snapshot_id: str
    site_id: str
    firewall_id: str
    vendor: str
    source: str
    snapshot_ts: str  # ISO 8601 (matches push-side wire contract)
    rules: list[FirewallRule]
    nat_rules: list[FirewallNATRule]
    objects: list[FirewallObject]


@router.get(
    "/sites/{site_id}/firewall-rules",
    response_model=list[FirewallSnapshotResponse],
)
async def get_site_firewall_rules(
    site_id: uuid.UUID,
    principal: ClerkPrincipal = Depends(require_role(*_READ_ROLES)),  # noqa: B008
    team: Team = Depends(resolve_team_from_clerk_org),  # noqa: B008
) -> list[FirewallSnapshotResponse]:
    """Return the latest snapshot per ``firewall_id`` under ``site_id``.

    Latest-per-device is computed via ``DISTINCT ON (firewall_id)
    ORDER BY firewall_id, snapshot_ts DESC`` — index-only against
    ``ix_fw_ruleset_latest (site_id, firewall_id, snapshot_ts DESC)``
    (Plan 11-02 migration 011).

    Cross-team ``site_id`` → 404 ``site_not_found_or_no_access`` (RLS
    isolates the ``DCSite`` probe to the caller's team).
    """
    _ = principal  # role check enforced by the dependency; not used downstream
    sm = get_sessionmaker()
    async with sm() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team.id)},
        )

        # Site-membership probe FIRST (mirrors github.py:144-152
        # list_repos_endpoint). RLS scopes this lookup to the caller's
        # team — a cross-team site_id resolves to None → 404.
        exists = await session.execute(
            select(DCSite.id).where(DCSite.id == site_id)
        )
        if exists.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="site_not_found_or_no_access",
            )

        # Latest snapshot per firewall_id (D-11). Uses the composite
        # ix_fw_ruleset_latest index for an index-only DISTINCT ON.
        latest_snapshots_q = text(
            """
            SELECT DISTINCT ON (firewall_id)
                snapshot_id, site_id, firewall_id, vendor, source, snapshot_ts
            FROM firewall_ruleset_snapshots
            WHERE site_id = :site_id
            ORDER BY firewall_id, snapshot_ts DESC
            """
        )
        snapshot_rows = (
            await session.execute(latest_snapshots_q, {"site_id": str(site_id)})
        ).mappings().all()

        if not snapshot_rows:
            _log.info(
                "firewall_rules_listed",
                team_id=str(team.id),
                site_id=str(site_id),
                snapshot_count=0,
            )
            return []

        snapshot_ids = [r["snapshot_id"] for r in snapshot_rows]

        # Fetch children for all latest snapshots — one round-trip per
        # child kind (N+0 not N+3 because IN-list covers every snapshot).
        rules_result = await session.execute(
            select(FirewallRuleORM)
            .where(FirewallRuleORM.snapshot_id.in_(snapshot_ids))
            .order_by(FirewallRuleORM.snapshot_id, FirewallRuleORM.position)
        )
        nat_result = await session.execute(
            select(FirewallNATRuleORM)
            .where(FirewallNATRuleORM.snapshot_id.in_(snapshot_ids))
            .order_by(FirewallNATRuleORM.snapshot_id, FirewallNATRuleORM.position)
        )
        obj_result = await session.execute(
            select(FirewallObjectORM)
            .where(FirewallObjectORM.snapshot_id.in_(snapshot_ids))
            .order_by(
                FirewallObjectORM.snapshot_id,
                FirewallObjectORM.kind,
                FirewallObjectORM.name,
            )
        )

        rules_by_snap: dict[uuid.UUID, list[FirewallRule]] = {}
        for r in rules_result.scalars().all():
            rules_by_snap.setdefault(r.snapshot_id, []).append(
                FirewallRule(
                    position=r.position,
                    src_zone=r.src_zone,
                    dst_zone=r.dst_zone,
                    src_cidr=r.src_cidr,
                    dst_cidr=r.dst_cidr,
                    action=r.action,
                    protocol=r.protocol,
                    ports=r.ports,
                    raw_blob=r.raw_blob,
                )
            )
        nat_by_snap: dict[uuid.UUID, list[FirewallNATRule]] = {}
        for n in nat_result.scalars().all():
            nat_by_snap.setdefault(n.snapshot_id, []).append(
                FirewallNATRule(
                    position=n.position,
                    src_translation=n.src_translation,
                    dst_translation=n.dst_translation,
                    interface_in=n.interface_in,
                    interface_out=n.interface_out,
                    raw_blob=n.raw_blob,
                )
            )
        objs_by_snap: dict[uuid.UUID, list[FirewallObject]] = {}
        for o in obj_result.scalars().all():
            objs_by_snap.setdefault(o.snapshot_id, []).append(
                FirewallObject(
                    kind=o.kind,
                    name=o.name,
                    value=o.value,
                    raw_blob=o.raw_blob,
                )
            )

    _log.info(
        "firewall_rules_listed",
        team_id=str(team.id),
        site_id=str(site_id),
        snapshot_count=len(snapshot_rows),
    )

    return [
        FirewallSnapshotResponse(
            snapshot_id=str(s["snapshot_id"]),
            site_id=str(s["site_id"]),
            firewall_id=s["firewall_id"],
            vendor=s["vendor"],
            source=s["source"],
            snapshot_ts=s["snapshot_ts"].isoformat().replace("+00:00", "Z"),
            rules=rules_by_snap.get(s["snapshot_id"], []),
            nat_rules=nat_by_snap.get(s["snapshot_id"], []),
            objects=objs_by_snap.get(s["snapshot_id"], []),
        )
        for s in snapshot_rows
    ]
