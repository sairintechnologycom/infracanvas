"""Pydantic v2 schemas for ``POST /v1/scans``, commit, and ``GET /v1/scans/{id}``.

All request models use ``ConfigDict(strict=True, extra="forbid")`` per
PATTERNS.md backend-hardening: strict prevents implicit coercion of
unexpected types (e.g. integer ``1`` flowing into a string field), and
``extra="forbid"`` rejects unknown keys at the boundary so a client
cannot pass through fields the validator does not recognise.

Response models intentionally relax this: the server is the source of
truth, and we want forward-compatibility with future fields without
breaking existing clients.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import ScanStatus

_STRICT = ConfigDict(strict=True, extra="forbid")


class ScanCreateReq(BaseModel):
    """Request body for ``POST /v1/scans``.

    ``content_type`` is optional and defaults to ``application/json``;
    clients targeting non-JSON formats (future) override it.
    """

    model_config = _STRICT

    content_type: str = "application/json"


class ScanCreateResp(BaseModel):
    """Response body for ``POST /v1/scans`` — the upload step of the
    two-step flow."""

    scan_id: UUID
    presigned_put_url: str
    expires_at: datetime


class ScanCommitReq(BaseModel):
    """Request body for ``POST /v1/scans/{id}/commit``.

    ``sha256`` is the hex-encoded SHA-256 of the uploaded ResourceGraph
    JSON bytes. Stored on the scan row for audit / future integrity
    checks; the server validates the hex shape but does not currently
    re-hash the R2 object (that would be a separate Phase 7 audit task).
    """

    model_config = _STRICT

    sha256: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    branch: str | None = Field(default=None, max_length=255)
    commit_sha: str | None = Field(default=None, max_length=40)
    source: str | None = Field(default=None, max_length=32)


class ScanGetResp(BaseModel):
    """Response body for ``GET /v1/scans/{id}`` and ``commit``.

    Phase 7.5 D-13: ``presigned_get_url`` is ``None`` when ``status`` is
    not ``ready`` (the R2 object doesn't exist yet for ``pending`` rows
    and won't exist for ``failed`` rows). The polling page (Plan 11)
    treats a null URL as "still scanning" and a non-null URL as
    "render the viewer".

    The new ``error_message`` + ``source_path`` + ``github_*`` fields are
    populated by either ``POST /v1/scans/from-github`` (sets ``github_*``
    + ``status='pending'``) or the ``scan_repo`` worker (sets
    ``error_message`` on failure or moves to ``status='ready'``).
    """

    id: UUID
    team_id: UUID
    status: ScanStatus
    presigned_get_url: str | None = None
    size_bytes: int | None
    created_at: datetime
    summary_json: dict[str, Any] | None = None
    branch: str | None = None
    commit_sha: str | None = None
    source: str | None = None
    # Phase 7.5 D-13 — populated by the GitHub-trigger flow + worker.
    error_message: str | None = None
    source_path: str | None = None
    github_installation_id: int | None = None
    github_repo: str | None = None
    github_branch: str | None = None
    github_sha: str | None = None


class ScanListItemResp(BaseModel):
    """Single row in ``GET /v1/scans`` (Plan 07-02).

    Mirrors ``ScanGetResp`` minus ``presigned_get_url`` — list rows do
    not include presigned URLs (only detail does), to keep list payloads
    bounded and avoid signing N URLs per page request.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    status: ScanStatus
    size_bytes: int | None
    created_at: datetime
    summary_json: dict[str, Any] | None = None
    branch: str | None = None
    commit_sha: str | None = None
    source: str | None = None


class ScanListResp(BaseModel):
    """Cursor-paginated response for ``GET /v1/scans`` (Plan 07-02)."""

    items: list[ScanListItemResp]
    next_cursor: str | None = None


# ---------------------------------------------------------------------------
# Compare endpoint schemas (Plan 07-03 — D-11)
# ---------------------------------------------------------------------------


class NodeDiff(BaseModel):
    """One row in a ResourceDiffResp.nodes list — the per-node diff result.

    ``kind`` is the discriminator:

    * ``added`` — node present in graph_b but not graph_a; ``before`` is None.
    * ``removed`` — node present in graph_a but not graph_b; ``after`` is None.
    * ``changed`` — present in both, at least one attribute differs;
      ``changed_fields`` lists the attribute keys that differ.
    * ``unchanged`` — present in both, all attributes equal; ``changed_fields``
      is empty.
    """

    id: str
    kind: Literal["added", "removed", "changed", "unchanged"]
    before: dict | None = None
    after: dict | None = None
    changed_fields: list[str] = []


class ResourceDiffResp(BaseModel):
    """Response body for ``GET /v1/scans/{a}/compare/{b}`` (Plan 07-03).

    Designed for reuse by:

    * the dashboard's compare page (Phase 7),
    * the future CLI ``infracanvas diff`` command,
    * v1.2 PR-bot status checks.

    ``nodes`` is capped at 5000 entries upstream by ``compute_diff`` to keep
    response sizes bounded — each scan is ≤25 MB per D-11, so most diffs
    fit comfortably under the cap.
    """

    scan_a_id: UUID
    scan_b_id: UUID
    nodes: list[NodeDiff]
    edges_added: list[dict]
    edges_removed: list[dict]
    summary: dict  # keys: added, removed, changed, unchanged — counts
