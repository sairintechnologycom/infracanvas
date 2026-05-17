"""Phase 12 D-14 — read API for computed paths + asymmetry findings + on-demand recompute.

Endpoints
---------

* ``GET  /v1/sites/{site_id}/paths``            — latest computed paths per
  pair (D-14). Optional ``?direction=forward|return`` filter.
* ``GET  /v1/sites/{site_id}/asymmetries``      — current asymmetry findings
  (D-14, D-10 sort). Optional ``?cause=...`` + ``?min_firewall_count=N``.
* ``POST /v1/sites/{site_id}/paths/recompute``  — owner-only on-demand
  recompute (D-04). 202 + ``job_id``; coalesces concurrent calls per site.

Auth posture (mirrors ``firewalls.py`` / Phase 11 Pattern E)
------------------------------------------------------------

* ``Depends(require_role(*_READ_ROLES))`` — Clerk JWT required (401 on
  missing).
* ``Depends(resolve_team_from_clerk_org)`` — Team resolved from JWT
  ``org_id``.
* ``set_config('app.current_team_id', :t, true)`` inside the transaction
  (Pattern B) — RLS isolates every query to the caller's team.

Cross-team isolation (T-12-CC-1, mirrors Phase 11 T-11-04-01)
-------------------------------------------------------------

* Site-membership probe runs FIRST (Pattern C). RLS isolates the
  ``DCSite`` lookup; a cross-team ``site_id`` returns 404
  ``site_not_found_or_no_access`` (not 403) to avoid leaking the
  existence of sites in other teams.

Warning 6 — NET-010 surfacing
-----------------------------

``GET /sites/{site_id}/asymmetries`` uses no implicit cause filter beyond
the optional ``?cause`` query param. NET-010 rows that Plan 12-06
persists into ``asymmetry_findings`` (with ``cause='NET-010'``) surface
in the same response so the viewer Asymmetry tab + dashboard list see
them without a code change.

Warning 7 — recompute deploy-state honesty
------------------------------------------

When ``app.queue.tasks.path_compute`` is not importable (Plan 12-06 has
not landed in this build), ``POST /paths/recompute`` raises HTTP 503
with detail ``"compute job not yet deployed"``. No fake ``job_id`` is
minted. Plan 12-06 removes the try/except entirely when it lands.

Logging allowlist (Pattern G)
-----------------------------

Only ``team_id`` / ``site_id`` / ``path_count`` / ``finding_count`` /
``job_id`` / ``coalesced``. Never log hop content, evidence blobs, raw
paths, or src/dst IPs.
"""
from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, text

from app.auth.clerk import ClerkPrincipal, require_role
from app.auth.deps import resolve_team_from_clerk_org
from app.db.models import DCSite, Team
from app.db.session import get_sessionmaker
from app.schemas.paths import (
    AsymmetryFindingResponse,
    PathsListItem,
    RecomputeResp,
)

router = APIRouter(prefix="/v1", tags=["paths"])
_log = structlog.get_logger("app.paths")

_READ_ROLES = ("owner", "admin", "member", "basic_member")
_OWNER_ROLES = ("owner",)


@router.get(
    "/sites/{site_id}/paths",
    response_model=list[PathsListItem],
)
async def get_site_paths(
    site_id: uuid.UUID,
    direction: str | None = Query(None, pattern="^(forward|return)$"),
    principal: ClerkPrincipal = Depends(require_role(*_READ_ROLES)),  # noqa: B008
    team: Team = Depends(resolve_team_from_clerk_org),  # noqa: B008
) -> list[PathsListItem]:
    """D-14 — latest computed paths per pair (direction filter optional).

    Latest-per-pair is computed via
    ``DISTINCT ON (pair_src_cidr, pair_dst_cidr, direction) ORDER BY ...
    computed_at DESC`` — index-only against ``ix_computed_paths_latest``
    (Plan 12-02 migration 013).

    Cross-team ``site_id`` → 404 ``site_not_found_or_no_access`` (RLS
    isolates the ``DCSite`` probe to the caller's team).
    """
    _ = principal  # role check enforced by the dependency; not used downstream
    sm = get_sessionmaker()
    async with sm() as session, session.begin():
        # Pattern B — set RLS GUC BEFORE any SELECT/INSERT in this txn
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team.id)},
        )

        # Pattern C — site-membership probe FIRST. Cross-team site_id
        # resolves to None under RLS → 404 site_not_found_or_no_access.
        exists = await session.execute(
            select(DCSite.id).where(DCSite.id == site_id)
        )
        if exists.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="site_not_found_or_no_access",
            )

        # DISTINCT ON (pair, direction) → latest computed_at per row.
        # Uses ix_computed_paths_latest composite index.
        sql = (
            "SELECT DISTINCT ON (pair_src_cidr, pair_dst_cidr, direction) "
            "path_id, site_id, pair_src_cidr, pair_dst_cidr, direction, "
            "hops, match_evidence, computed_at "
            "FROM computed_paths "
            "WHERE site_id = :sid "
        )
        params: dict[str, object] = {"sid": str(site_id)}
        if direction:
            sql += "AND direction = :dir "
            params["dir"] = direction
        sql += "ORDER BY pair_src_cidr, pair_dst_cidr, direction, computed_at DESC"
        result = await session.execute(text(sql), params)
        rows = result.mappings().all()

    _log.info(
        "paths_listed",
        team_id=str(team.id),
        site_id=str(site_id),
        path_count=len(rows),
    )

    return [
        PathsListItem(
            path_id=str(r["path_id"]),
            site_id=str(r["site_id"]),
            pair_src_cidr=r["pair_src_cidr"],
            pair_dst_cidr=r["pair_dst_cidr"],
            direction=r["direction"],
            hops=list(r["hops"]) if r["hops"] is not None else [],
            match_evidence=dict(r["match_evidence"]) if r["match_evidence"] is not None else {},
            computed_at=r["computed_at"].isoformat().replace("+00:00", "Z"),
        )
        for r in rows
    ]


@router.get(
    "/sites/{site_id}/asymmetries",
    response_model=list[AsymmetryFindingResponse],
)
async def get_site_asymmetries(
    site_id: uuid.UUID,
    # Warning 6: regex accepts NET-010 alongside the v1.1 enum members so
    # the viewer Asymmetry tab can ``?cause=NET-010`` filter when desired.
    cause: str | None = Query(
        None,
        pattern="^(BGP_LOCAL_PREF|ROUTE_LEAK|NAT_ASYMMETRY|UNKNOWN|NET-010)$",
    ),
    min_firewall_count: int = Query(0, ge=0),
    principal: ClerkPrincipal = Depends(require_role(*_READ_ROLES)),  # noqa: B008
    team: Team = Depends(resolve_team_from_clerk_org),  # noqa: B008
) -> list[AsymmetryFindingResponse]:
    """D-14 + D-10 — current asymmetries; sort by firewall_count DESC, bytes/s DESC.

    Warning 6: this endpoint deliberately does NOT filter on cause unless
    the caller specifies one. NET-010 rows persisted by Plan 12-06 (with
    ``cause='NET-010'``) surface here without code change. ``resolved_at
    IS NULL`` restricts the response to currently-open findings.
    """
    _ = principal
    sm = get_sessionmaker()
    async with sm() as session, session.begin():
        # Pattern B — RLS GUC set BEFORE any SELECT
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team.id)},
        )
        # Pattern C — site-membership probe FIRST
        exists = await session.execute(
            select(DCSite.id).where(DCSite.id == site_id)
        )
        if exists.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="site_not_found_or_no_access",
            )

        sql = (
            "SELECT finding_id, site_id, forward_path_id, return_path_id, "
            "cause, cause_confidence, evidence, impact_bytes_per_sec, "
            "impact_firewall_count, first_seen_at, last_seen_at, resolved_at "
            "FROM asymmetry_findings "
            "WHERE site_id = :sid AND resolved_at IS NULL "
            "AND impact_firewall_count >= :mfc "
        )
        params: dict[str, object] = {
            "sid": str(site_id),
            "mfc": min_firewall_count,
        }
        if cause:
            sql += "AND cause = :cause "
            params["cause"] = cause
        sql += "ORDER BY impact_firewall_count DESC, impact_bytes_per_sec DESC"
        result = await session.execute(text(sql), params)
        rows = result.mappings().all()

    _log.info(
        "asymmetries_listed",
        team_id=str(team.id),
        site_id=str(site_id),
        finding_count=len(rows),
    )

    return [
        AsymmetryFindingResponse(
            finding_id=str(r["finding_id"]),
            site_id=str(r["site_id"]),
            forward_path_id=str(r["forward_path_id"]),
            return_path_id=str(r["return_path_id"]),
            cause=r["cause"],
            cause_confidence=float(r["cause_confidence"]),
            evidence=dict(r["evidence"]) if r["evidence"] is not None else {},
            impact_bytes_per_sec=float(r["impact_bytes_per_sec"]),
            impact_firewall_count=int(r["impact_firewall_count"]),
            first_seen_at=r["first_seen_at"].isoformat().replace("+00:00", "Z"),
            last_seen_at=r["last_seen_at"].isoformat().replace("+00:00", "Z"),
            resolved_at=(
                r["resolved_at"].isoformat().replace("+00:00", "Z")
                if r["resolved_at"]
                else None
            ),
        )
        for r in rows
    ]


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
    """D-14 + D-04 — on-demand recompute. Coalesces concurrent calls per site_id.

    Coalescing strategy (CONTEXT.md discretion): if a ``computed_paths``
    row exists for this site with ``computed_at`` within the past 60
    seconds, return a coalesced ``job_id`` with ``coalesced=True`` and
    skip the enqueue; otherwise enqueue a fresh taskiq job.

    Warning 7: when ``app.queue.tasks.path_compute`` cannot be imported
    (Plan 12-06 has not landed in this build), this endpoint returns
    HTTP 503 with detail ``"compute job not yet deployed"``. No fake
    ``job_id`` is minted. Plan 12-06 removes the try/except entirely
    when it lands.
    """
    _ = principal
    sm = get_sessionmaker()
    async with sm() as session, session.begin():
        # Pattern B — RLS GUC set BEFORE any SELECT
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team.id)},
        )
        # Pattern C — site-membership probe FIRST
        exists = await session.execute(
            select(DCSite.id).where(DCSite.id == site_id)
        )
        if exists.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="site_not_found_or_no_access",
            )

        # Coalesce check — within 60s, return prior recompute's job_id
        recent = await session.execute(
            text(
                "SELECT path_id FROM computed_paths "
                "WHERE site_id = :sid "
                "AND computed_at > NOW() - INTERVAL '60 seconds' "
                "ORDER BY computed_at DESC LIMIT 1"
            ),
            {"sid": str(site_id)},
        )
        prior = recent.scalar_one_or_none()
        if prior is not None:
            coalesced_job_id = f"coalesced-{site_id}-{uuid.uuid4()}"
            _log.info(
                "recompute_coalesced",
                team_id=str(team.id),
                site_id=str(site_id),
                job_id=coalesced_job_id,
                coalesced=True,
            )
            return RecomputeResp(
                job_id=coalesced_job_id,
                site_id=str(site_id),
                coalesced=True,
            )

    # Enqueue fresh job (outside the session/transaction).
    # Warning 7 — no silent ImportError swallow. If Plan 12-06's module is
    # not present in this build, raise HTTP 503 so the caller sees a
    # truthful "not yet deployed" signal instead of a fake job_id that
    # will never run. Plan 12-06 deletes the try/except entirely.
    try:
        from app.queue.tasks.path_compute import (  # noqa: PLC0415
            recompute_paths_for_site,
        )
    except ImportError as exc:
        _log.warning(
            "recompute_compute_module_missing",
            team_id=str(team.id),
            site_id=str(site_id),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="compute job not yet deployed",
        ) from exc

    await recompute_paths_for_site.kiq(site_id=site_id, on_demand=True)
    job_id = f"path-compute-{site_id}-{uuid.uuid4()}"
    _log.info(
        "recompute_enqueued",
        team_id=str(team.id),
        site_id=str(site_id),
        job_id=job_id,
        coalesced=False,
    )
    return RecomputeResp(job_id=job_id, site_id=str(site_id), coalesced=False)
