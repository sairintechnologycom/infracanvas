"""Pydantic schemas for /v1/github/* and /v1/scans/from-github endpoints (D-10a..e).

Request schemas use ``ConfigDict(strict=True, extra="forbid")`` per CC-9 so
that unexpected types and unknown keys are rejected at the boundary. Response
schemas relax this — the server is the source of truth and we want forward
compatibility with future fields without breaking existing clients.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

_STRICT = ConfigDict(strict=True, extra="forbid")


class InstallationResp(BaseModel):
    """Response item for ``GET /v1/github/installations`` (D-10a).

    Sourced from the local ``github_installations`` table. No GitHub API call
    happens for this endpoint — denormalised account fields are populated by
    the install-callback handler at install time.
    """

    installation_id: int
    github_account_login: str
    github_account_type: str
    installed_at: datetime
    installed_by_user_id: str


class RepoResp(BaseModel):
    """Response item for ``GET /v1/github/repos`` (D-10b)."""

    full_name: str
    default_branch: str
    private: bool


class BranchResp(BaseModel):
    """Response item for ``GET /v1/github/branches`` (D-10c)."""

    name: str
    commit_sha: str


class ScanFromGitHubReq(BaseModel):
    """Request body for ``POST /v1/scans/from-github`` (D-10e).

    Validation:
      - ``installation_id``: positive integer (GitHub install ids are >0).
      - ``repo``: GitHub ``owner/name`` shape.
      - ``branch``: non-empty, ≤255 chars (GitHub max).
      - ``path``: defaults to ``"."`` (scan repo root).
    """

    model_config = _STRICT

    installation_id: int = Field(gt=0)
    repo: str = Field(pattern=r"^[\w.\-]+/[\w.\-]+$", max_length=255)
    branch: str = Field(min_length=1, max_length=255)
    path: str = Field(default=".", max_length=1024)


class ScanFromGitHubResp(BaseModel):
    """Response body for ``POST /v1/scans/from-github``."""

    scan_id: UUID
