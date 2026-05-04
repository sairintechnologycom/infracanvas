"""Smoke tests for app.schemas.github — request rejection + response happy path.

Covers the eight behaviors from Plan 07.5-03 Task 3:

  1. InstallationResp instantiates with all five fields
  2. RepoResp instantiates
  3. BranchResp instantiates
  4. ScanFromGitHubReq instantiates with default path='.'
  5. ScanFromGitHubReq rejects extra fields (extra=forbid)
  6. ScanFromGitHubReq rejects installation_id <= 0
  7. ScanFromGitHubReq rejects repo without slash (regex)
  8. ScanFromGitHubResp instantiates from a UUID
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.github import (
    BranchResp,
    InstallationResp,
    RepoResp,
    ScanFromGitHubReq,
    ScanFromGitHubResp,
)


def test_installation_resp_happy():
    obj = InstallationResp(
        installation_id=99,
        github_account_login="foo",
        github_account_type="Organization",
        installed_at=datetime.now(tz=UTC),
        installed_by_user_id="user_abc",
    )
    assert obj.installation_id == 99


def test_repo_resp_happy():
    obj = RepoResp(full_name="org/repo", default_branch="main", private=False)
    assert obj.full_name == "org/repo"
    assert obj.private is False


def test_branch_resp_happy():
    obj = BranchResp(name="main", commit_sha="abc")
    assert obj.commit_sha == "abc"


def test_scan_from_github_req_happy_default_path():
    req = ScanFromGitHubReq(installation_id=99, repo="org/repo", branch="main")
    assert req.path == "."


def test_scan_from_github_req_rejects_extra_fields():
    with pytest.raises(ValidationError):
        ScanFromGitHubReq(
            installation_id=99,
            repo="org/repo",
            branch="main",
            unexpected_field="boom",  # type: ignore[call-arg]
        )


def test_scan_from_github_req_rejects_zero_installation_id():
    with pytest.raises(ValidationError):
        ScanFromGitHubReq(installation_id=0, repo="org/repo", branch="main")


def test_scan_from_github_req_rejects_repo_without_slash():
    with pytest.raises(ValidationError):
        ScanFromGitHubReq(installation_id=1, repo="bad", branch="main")


def test_scan_from_github_resp_happy():
    obj = ScanFromGitHubResp(scan_id=uuid.uuid4())
    assert isinstance(obj.scan_id, uuid.UUID)
