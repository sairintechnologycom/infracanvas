"""Pydantic schemas for Phase 12 path-compute read API.

Locked contracts consumed by ``backend/app/routes/paths.py`` and (later)
the viewer dashboard fetch wiring (Phase 12 FMV-02). Field names are a
stable forward-feed contract for the viewer hydration into Zustand
``selectedPath`` — do not rename without a coordinated viewer update.

Re-exports ``NetworkPath`` + ``PathHop`` from
``cli/infracanvas/graph/models.py`` (Pitfall 9 — import-not-redeclare)
so route handlers, viewer fetcher, and CLI offline scans use the SAME
shape. The cli is already a backend dep via
``infracanvas @ file:../cli`` in ``backend/pyproject.toml`` (line 50).

D-15 column contract on the response models below — DO NOT rename
fields without coordinated viewer update. ``cause`` is open-string at
the Pydantic layer (the DB CHECK constraint enforces the enum) so
NET-010 rows persisted by Plan 12-06 surface here without an additional
schema migration (Warning 6).
"""
from __future__ import annotations

# Re-export to give backend a single import path; cli is already a backend
# dep (``infracanvas @ file:../cli``). Per Pitfall 9 the NetworkPath /
# PathHop shapes are imported, not redeclared, so the CLI offline scans
# and the backend read API stay byte-aligned.
from infracanvas.graph.models import NetworkPath, PathHop  # noqa: F401
from pydantic import BaseModel


class PathsListItem(BaseModel):
    """One row in ``GET /v1/sites/{site_id}/paths`` response.

    Latest computed path per ``(pair_src_cidr, pair_dst_cidr, direction)``
    triple — the route handler emits one ``PathsListItem`` per latest row
    via ``DISTINCT ON`` against the ``ix_computed_paths_latest`` index.
    """

    path_id: str
    site_id: str
    pair_src_cidr: str
    pair_dst_cidr: str
    direction: str  # 'forward' | 'return'
    hops: list[dict]  # serialized PathHop list (JSONB → list[dict])
    match_evidence: dict
    computed_at: str  # ISO 8601


class AsymmetryFindingResponse(BaseModel):
    """Per-pair asymmetry finding returned by ``GET /v1/sites/{site_id}/asymmetries``.

    D-15 column contract — DO NOT rename fields without coordinated viewer
    update. ``cause`` is open-string at the Pydantic layer (DB CHECK
    constraint enforces the enum) so NET-010 cause rows (Warning 6)
    surface here without an additional schema migration.
    """

    finding_id: str
    site_id: str
    forward_path_id: str
    return_path_id: str
    cause: str  # 'BGP_LOCAL_PREF'|'ROUTE_LEAK'|'NAT_ASYMMETRY'|'UNKNOWN'|'NET-010'
    cause_confidence: float
    evidence: dict
    impact_bytes_per_sec: float
    impact_firewall_count: int
    first_seen_at: str  # ISO 8601
    last_seen_at: str  # ISO 8601
    resolved_at: str | None = None


class PathDivergenceResponse(BaseModel):
    """NetFlow-observed-vs-computed divergence finding (D-07).

    Returned by future read endpoints (Plan 12-06+); declared here so the
    Pydantic surface is complete for the viewer hydration contract.
    """

    finding_id: str
    site_id: str
    expected_path_id: str
    observed_path: dict
    evidence: dict
    first_seen_at: str  # ISO 8601
    last_seen_at: str  # ISO 8601
    resolved_at: str | None = None


class RecomputeResp(BaseModel):
    """Response for ``POST /v1/sites/{site_id}/paths/recompute``.

    202 Accepted + ``job_id`` (taskiq pattern); caller polls via the
    existing job-status endpoint if needed. Coalesces concurrent calls —
    same ``site_id`` within the in-flight window returns the in-flight
    ``job_id`` + ``coalesced=True``.
    """

    job_id: str
    site_id: str
    coalesced: bool = False
