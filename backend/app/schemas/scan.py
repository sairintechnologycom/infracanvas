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
from typing import Any
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


class ScanGetResp(BaseModel):
    """Response body for ``GET /v1/scans/{id}`` and ``commit``."""

    id: UUID
    team_id: UUID
    status: ScanStatus
    presigned_get_url: str
    size_bytes: int | None
    created_at: datetime
    summary_json: dict[str, Any] | None = None
