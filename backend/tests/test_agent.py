"""Phase 10 DC Agent backend test stubs (Wave 0 Nyquist scaffold).

Each test is skipped with a RED marker pointing to the plan that will
flip it to GREEN. This file MUST be collectable by pytest from the
moment Plan 10-01 closes so subsequent plans land in RED -> GREEN cadence.
"""
from __future__ import annotations

import pytest


# --- POST /v1/sites (DCA-05 backend, Plan 10-02) ----------------------------
@pytest.mark.skip(reason="RED — implementation lands in plan 10-02 (POST /v1/sites)")
def test_create_site_returns_one_time_token() -> None:
    """DCA-05: POST /v1/sites returns plaintext token once, stores SHA-256 hash in DB."""


@pytest.mark.skip(reason="RED — implementation lands in plan 10-02 (POST /v1/sites RBAC)")
def test_create_site_requires_owner_role() -> None:
    """DCA-05: POST /v1/sites returns 403 for non-owner Clerk roles."""


# --- POST /v1/agent/routes (DCA-05, Plan 10-02) -----------------------------
@pytest.mark.skip(reason="RED — implementation lands in plan 10-02 (require_site_token)")
def test_push_routes_rejects_missing_bearer() -> None:
    """DCA-05: POST /v1/agent/routes returns 401 missing_bearer with no auth header."""


@pytest.mark.skip(reason="RED — implementation lands in plan 10-02 (require_site_token)")
def test_push_routes_rejects_invalid_site_token() -> None:
    """DCA-05: POST /v1/agent/routes returns 401 invalid_site_token with bogus token."""


@pytest.mark.skip(reason="RED — implementation lands in plan 10-02 (happy path)")
def test_push_routes_accepts_valid_site_token() -> None:
    """DCA-05: POST /v1/agent/routes returns 202 with valid bearer + body."""


# --- POST /v1/agent/flows (DCA-05, Plan 10-02) ------------------------------
@pytest.mark.skip(reason="RED — implementation lands in plan 10-02 (require_site_token)")
def test_push_flows_rejects_missing_bearer() -> None:
    """DCA-05: POST /v1/agent/flows returns 401 missing_bearer with no auth header."""


@pytest.mark.skip(reason="RED — implementation lands in plan 10-02 (happy path)")
def test_push_flows_accepts_valid_site_token() -> None:
    """DCA-05: POST /v1/agent/flows returns 202 with valid bearer + JSON body."""


# --- RLS isolation (DCA-05 + TMM-01, Plan 10-02) ----------------------------
@pytest.mark.skip(reason="RED — implementation lands in plan 10-02 (RLS dc_sites)")
def test_dc_sites_rls_isolates_teams() -> None:
    """TMM-01: dc_sites query under team A's RLS context returns 0 rows for team B."""
