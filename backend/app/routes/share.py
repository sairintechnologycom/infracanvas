"""Share-link endpoints.

POST   /v1/scans/{scan_id}/share-links   — auth required, creates share link
GET    /v1/share-links/{token}           — public, returns landing metadata
POST   /v1/share-links/{token}/unlock    — public, verifies password → presigned URL
DELETE /v1/scans/{scan_id}/share-links/{share_id}  — auth required, revokes

Security design:
- raw_token = secrets.token_urlsafe(32)  — 32 bytes of entropy
- token_hash = bcrypt(raw_token, cost=12)  — stored in DB
- token_lookup_hash = sha256(raw_token) — indexed lookup, constant-time fetch
- share_link_by_token() SECURITY DEFINER — public path bypasses RLS safely
- Rate limit: 5 unlock attempts per IP per 15 min (T-07-04-02)
- Timing safety: dummy bcrypt op when token not found (T-07-04-03)
"""
from __future__ import annotations

import hashlib
import os
import secrets
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select, text

from app.auth.clerk import ClerkPrincipal, require_role
from app.auth.deps import resolve_team_from_clerk_org
from app.db.models import Scan, ShareLink, Team
from app.db.session import get_sessionmaker
from app.schemas.share import (
    ShareCreateReq,
    ShareCreateResp,
    ShareLandingResp,
    ShareVerifyReq,
    ShareVerifyResp,
)
from app.services.bcrypt_hash import hash_value, verify_value
from app.storage import r2

log = structlog.get_logger(__name__)

router = APIRouter(tags=["share"])

_GET_TTL_SECONDS = 300

# --- In-process rate limiter for /unlock (T-07-04-02) ---
# Maps (client_ip, token_prefix) -> (attempt_count, window_start_epoch)
# Not distributed — acceptable for solo-founder scale; replace with Redis/slowapi when needed.
_RATE_LIMIT_WINDOW = 900  # 15 minutes
_RATE_LIMIT_MAX = 5
_rate_store: dict[tuple[str, str], tuple[int, float]] = defaultdict(lambda: (0, 0.0))


def _check_rate_limit(client_ip: str, token_prefix: str) -> None:
    """Raise 429 if this IP has exceeded 5 unlock attempts in the last 15 minutes."""
    key = (client_ip, token_prefix)
    count, window_start = _rate_store[key]
    now = time.monotonic()
    if now - window_start > _RATE_LIMIT_WINDOW:
        _rate_store[key] = (1, now)
        return
    count += 1
    _rate_store[key] = (count, window_start)
    if count > _RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too_many_attempts",
            headers={"Retry-After": str(_RATE_LIMIT_WINDOW)},
        )


def _token_lookup_hash(raw_token: str) -> str:
    """SHA-256 hex digest of raw token — deterministic, used for indexed DB lookup."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _share_url(raw_token: str) -> str:
    """Build the public share URL for a given raw token."""
    base = os.environ.get("DASHBOARD_URL", "http://localhost:3001")
    return f"{base}/share/{raw_token}"


# ---------------------------------------------------------------------------
# POST /v1/scans/{scan_id}/share-links — auth required
# ---------------------------------------------------------------------------

@router.post(
    "/scans/{scan_id}/share-links",
    response_model=ShareCreateResp,
    status_code=status.HTTP_201_CREATED,
)
async def create_share_link(
    scan_id: UUID,
    body: ShareCreateReq,
    principal: ClerkPrincipal = Depends(  # noqa: B008
        require_role("owner", "admin", "member", "basic_member")
    ),
    team: Team = Depends(resolve_team_from_clerk_org),  # noqa: B008
) -> ShareCreateResp:
    """Create a share link for a scan. Raw token returned once — never stored raw."""
    raw_token = secrets.token_urlsafe(32)
    lookup_hash = _token_lookup_hash(raw_token)

    # Hash token and (optionally) password in threadpool — CPU-bound bcrypt
    token_hash = await run_in_threadpool(hash_value, raw_token)
    password_hash: str | None = None
    if body.password:
        password_hash = await run_in_threadpool(hash_value, body.password)

    sm = get_sessionmaker()
    async with sm() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('app.current_team_id', :t, true)"),
                {"t": str(team.id)},
            )
            # Verify scan belongs to caller's team (RLS will also enforce this)
            scan_row = (
                await session.execute(select(Scan).where(Scan.id == scan_id))
            ).scalar_one_or_none()
            if scan_row is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "scan_not_found")

            link = ShareLink(
                id=uuid.uuid4(),
                team_id=team.id,
                scan_id=scan_id,
                token_hash=token_hash,
                token_lookup_hash=lookup_hash,
                password_hash=password_hash,
                expires_at=body.expires_at,
                created_by=principal.user_id,
            )
            session.add(link)
            await session.flush()
            link_id = link.id

    return ShareCreateResp(
        id=link_id,
        token=raw_token,  # shown once — client must copy immediately
        share_url=_share_url(raw_token),
        expires_at=body.expires_at,
    )


# ---------------------------------------------------------------------------
# GET /v1/share-links/{token} — public, no auth
# ---------------------------------------------------------------------------

@router.get("/share-links/{token}", response_model=ShareLandingResp)
async def get_share_landing(token: str) -> ShareLandingResp:
    """Public landing info for a share link.

    Returns {has_password: true} with NO scan metadata when password-protected (D-15).
    Uses share_link_by_token() SECURITY DEFINER to bypass RLS safely.
    """
    lookup_hash = _token_lookup_hash(token)

    sm = get_sessionmaker()
    async with sm() as session:
        async with session.begin():
            result = await session.execute(
                text("SELECT * FROM share_link_by_token(:h)"),
                {"h": lookup_hash},
            )
            row = result.mappings().first()

    if row is None:
        # Timing safety: perform dummy bcrypt op to prevent timing oracle on existence
        await run_in_threadpool(verify_value, "dummy", hash_value("sentinel"))
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")

    # Check expiry and revocation
    if row["revoked_at"] is not None:
        raise HTTPException(status.HTTP_410_GONE, "revoked")
    if row["expires_at"] and row["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_410_GONE, "expired")

    # Verify bcrypt token (constant-time; confirms token is valid, not just lookup_hash)
    token_valid = await run_in_threadpool(verify_value, token, row["token_hash"])
    if not token_valid:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")

    if row["password_hash"] is not None:
        # Password-protected: return NO scan metadata (D-15)
        return ShareLandingResp(has_password=True)

    # No password — fetch scan metadata and return presigned URL.
    # share_link_by_token() already validated the row; we set the
    # app.current_team_id GUC from the row's team_id so the team-scoped
    # RLS policy on scans permits the read.
    scan_id = row["scan_id"]
    team_id = row["team_id"]
    sm2 = get_sessionmaker()
    async with sm2() as session2:
        async with session2.begin():
            await session2.execute(
                text("SELECT set_config('app.current_team_id', :t, true)"),
                {"t": str(team_id)},
            )
            scan_row = await session2.get(Scan, scan_id)

    if scan_row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "scan_not_found")

    get_url = await run_in_threadpool(r2.presigned_get, scan_row.r2_key, _GET_TTL_SECONDS)
    return ShareLandingResp(
        has_password=False,
        scan_id=scan_row.id,
        presigned_get_url=get_url,
        branch=scan_row.branch,
        commit_sha=scan_row.commit_sha,
        created_at=scan_row.created_at,
        summary_json=scan_row.summary_json,
    )


# ---------------------------------------------------------------------------
# POST /v1/share-links/{token}/unlock — public, no auth, rate-limited
# ---------------------------------------------------------------------------

@router.post("/share-links/{token}/unlock", response_model=ShareVerifyResp)
async def unlock_share_link(
    token: str,
    body: ShareVerifyReq,
    request: Request,
) -> ShareVerifyResp:
    """Verify password for a password-protected share link.

    Rate-limited: 5 attempts per IP per 15 minutes (T-07-04-02).
    Wrong password → 401 (no existence leakage via timing: always runs bcrypt).
    """
    client_ip = request.client.host if request.client else "unknown"
    token_prefix = token[:8]  # use first 8 chars as rate-limit key suffix
    _check_rate_limit(client_ip, token_prefix)

    lookup_hash = _token_lookup_hash(token)

    sm = get_sessionmaker()
    async with sm() as session:
        async with session.begin():
            result = await session.execute(
                text("SELECT * FROM share_link_by_token(:h)"),
                {"h": lookup_hash},
            )
            row = result.mappings().first()

    if row is None:
        # Dummy bcrypt op to prevent timing oracle (T-07-04-03)
        await run_in_threadpool(verify_value, body.password, hash_value("sentinel"))
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")

    # Check revocation + expiry
    if row["revoked_at"] is not None:
        raise HTTPException(status.HTTP_410_GONE, "revoked")
    if row["expires_at"] and row["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_410_GONE, "expired")

    if row["password_hash"] is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "no_password_set",
        )

    # Verify password (bcrypt constant-time)
    password_valid = await run_in_threadpool(verify_value, body.password, row["password_hash"])
    if not password_valid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_password")

    # Verify token itself
    token_valid = await run_in_threadpool(verify_value, token, row["token_hash"])
    if not token_valid:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")

    # Fetch scan and return presigned URL.
    # Set GUC from row.team_id so the scans RLS policy permits the read on
    # this unauthenticated path; share_link_by_token() already validated the row.
    scan_id = row["scan_id"]
    team_id = row["team_id"]
    sm2 = get_sessionmaker()
    async with sm2() as session2:
        async with session2.begin():
            await session2.execute(
                text("SELECT set_config('app.current_team_id', :t, true)"),
                {"t": str(team_id)},
            )
            scan_row = await session2.get(Scan, scan_id)

    if scan_row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "scan_not_found")

    get_url = await run_in_threadpool(r2.presigned_get, scan_row.r2_key, _GET_TTL_SECONDS)
    return ShareVerifyResp(
        scan_id=scan_row.id,
        presigned_get_url=get_url,
        branch=scan_row.branch,
        commit_sha=scan_row.commit_sha,
        created_at=scan_row.created_at,
        summary_json=scan_row.summary_json,
    )


# ---------------------------------------------------------------------------
# DELETE /v1/scans/{scan_id}/share-links/{share_id} — auth required
# ---------------------------------------------------------------------------

@router.delete(
    "/scans/{scan_id}/share-links/{share_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def revoke_share_link(
    scan_id: UUID,
    share_id: UUID,
    principal: ClerkPrincipal = Depends(  # noqa: B008
        require_role("owner", "admin", "member", "basic_member")
    ),
    team: Team = Depends(resolve_team_from_clerk_org),  # noqa: B008
) -> Response:
    """Revoke a share link by setting revoked_at. Returns 204."""
    sm = get_sessionmaker()
    async with sm() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('app.current_team_id', :t, true)"),
                {"t": str(team.id)},
            )
            link_row = (
                await session.execute(
                    select(ShareLink).where(
                        ShareLink.id == share_id,
                        ShareLink.scan_id == scan_id,
                    )
                )
            ).scalar_one_or_none()
            if link_row is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "share_link_not_found")
            link_row.revoked_at = datetime.now(timezone.utc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
