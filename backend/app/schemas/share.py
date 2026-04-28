"""Pydantic schemas for share-link endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Note: strict=True rejects ISO-string → datetime coercion that JSON payloads
# rely on. We use ``extra="forbid"`` to lock the schema shape while letting
# Pydantic coerce ISO strings into datetime for ``expires_at``.
_STRICT = ConfigDict(strict=True, extra="forbid")
_LAX_STRICT = ConfigDict(extra="forbid")


class ShareCreateReq(BaseModel):
    model_config = _LAX_STRICT
    password: str | None = Field(default=None, max_length=128)
    expires_at: datetime | None = None


class ShareCreateResp(BaseModel):
    id: UUID
    token: str          # raw token — returned ONCE, never stored raw
    share_url: str
    expires_at: datetime | None = None


class ShareLandingResp(BaseModel):
    """Response from GET /v1/share-links/{token}.

    When has_password=True, scan_id and presigned_get_url are omitted
    (D-15: scan data never sent to client until password verified).
    """

    has_password: bool
    scan_id: UUID | None = None
    presigned_get_url: str | None = None
    branch: str | None = None
    commit_sha: str | None = None
    created_at: datetime | None = None
    summary_json: dict[str, Any] | None = None


class ShareVerifyReq(BaseModel):
    model_config = _LAX_STRICT
    password: str = Field(max_length=128)


class ShareVerifyResp(BaseModel):
    scan_id: UUID
    presigned_get_url: str
    branch: str | None = None
    commit_sha: str | None = None
    created_at: datetime | None = None
    summary_json: dict[str, Any] | None = None
