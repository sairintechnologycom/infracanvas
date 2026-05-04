"""Scan ingest + retrieval HTTP routes.

Three endpoints:

* ``POST /v1/scans`` — issues a presigned PUT URL targeting
  ``pending/{scan_id}.json`` (the two-step layout — D-11).
* ``POST /v1/scans/{id}/commit`` — atomic commit:
  HEAD pending → validate ResourceGraph → INSERT scan row →
  Stripe meter event → DB COMMIT → server-side R2 copy
  ``pending/`` → ``teams/{team_id}/scans/`` → DELETE pending.
* ``GET /v1/scans/{id}`` — return scan metadata + presigned GET URL
  (≤300s TTL). Cross-team access returns 404 (D-10) — never 403, so the
  existence of a scan in another team's namespace is not leaked.

Ordering inside commit (RESEARCH § F8 + D-09):

1. ``HEAD pending/`` — 404 if missing, 413 if oversized.
2. Fetch + ``ResourceGraph.model_validate_json`` — 422 on malformed JSON.
3. INSERT ``scans`` row with ``r2_key = teams/{team_id}/scans/{id}.json``
   (the FINAL key — even though the bytes still live at ``pending/``;
   the post-commit copy moves them).
4. Stripe meter event — LAST inside the tx so any Stripe failure
   triggers a DB rollback (no scan row without a meter event).
5. Tx commits.
6. Best-effort R2 copy ``pending/`` → ``teams/.../`` then delete
   pending. Failure logged at WARNING; lifecycle rule (Plan 08) GCs
   abandoned ``pending/`` after 7 days.
7. Best-effort taskiq enqueue for indexing (Plan 06-06 will provide).

Why post-commit copy is safe: if the copy fails, the DB row's r2_key
points at the final key but the bytes still live at ``pending/``. A GET
issued before the copy succeeds would 404 against R2 — we accept this
as an eventual-consistency window. A Phase 7 reconciler can retry.
"""
from __future__ import annotations

import asyncio
import base64
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError
from sqlalchemy import and_, or_, select, text

from infracanvas.graph.models import ResourceGraph  # cross-package via file:../cli

from app.auth.clerk import ClerkPrincipal, require_role
from app.auth.deps import resolve_team_from_clerk_org
from app.db.models import Scan, ScanStatus, Team
from app.db.session import get_sessionmaker
from app.schemas.scan import (
    NodeDiff,
    ResourceDiffResp,
    ScanCommitReq,
    ScanCreateReq,
    ScanCreateResp,
    ScanGetResp,
    ScanListItemResp,
    ScanListResp,
)
from app.services.diff import compute_diff
from app.services.scans import fire_scan_meter_or_502
from app.storage import r2
from app.util.ids import new_uuid7

# Hard cap on uploaded ResourceGraph size. Enforced at commit-time HEAD
# because R2 doesn't honour Content-Length-Range on presigned PUT
# (research callout #2). 25 MB matches CONTEXT.md D-11.
_MAX_BYTES = 25 * 1024 * 1024
# 10 minutes — long enough for even a slow client upload to complete; short
# enough that an leaked URL is useless quickly.
_PUT_TTL_SECONDS = 600
# 5 minutes — bounds the leak window for a GET URL while still being
# usable for a single user navigation.
_GET_TTL_SECONDS = 300

router = APIRouter(prefix="/v1/scans", tags=["scans"])
_log = structlog.get_logger("app.scans")


def _pending_key(scan_id: UUID) -> str:
    """Two-step layout: presigned PUT targets pending/.

    Plan 08's R2 lifecycle rule will GC any pending/{id}.json older than
    7 days — safe because committed scans are copied to teams/.../ and
    the pending source is deleted on the success path.
    """
    return f"pending/{scan_id}.json"


def _final_key(team_id: UUID, scan_id: UUID) -> str:
    """The committed-scan layout: teams/{team_id}/scans/{scan_id}.json.

    Per-team prefix bounds blast radius — each presigned GET is scoped to
    a key under the authenticated team's prefix (T-06-04 mitigation).
    """
    return f"teams/{team_id}/scans/{scan_id}.json"


@router.post("", response_model=ScanCreateResp, status_code=200)
async def create_scan(
    body: ScanCreateReq,
    principal: ClerkPrincipal = Depends(  # noqa: B008
        require_role("owner", "admin", "member")
    ),
    team: Team = Depends(resolve_team_from_clerk_org),
) -> ScanCreateResp:
    """Step 1 of two-step upload — return a presigned PUT URL.

    No R2 bytes flow through the API. Client PUTs directly to the
    pending/ key; the commit endpoint atomically promotes that to a
    durable scan row + Stripe meter event + final R2 location.
    """
    scan_id = new_uuid7()
    put_key = _pending_key(scan_id)
    url = await run_in_threadpool(
        r2.presigned_put, put_key, body.content_type, _PUT_TTL_SECONDS
    )
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=_PUT_TTL_SECONDS)
    _log.info(
        "scan_create",
        scan_id=str(scan_id),
        team_id=str(team.id),
        put_key=put_key,
    )
    return ScanCreateResp(
        scan_id=scan_id, presigned_put_url=url, expires_at=expires_at
    )


@router.post("/{scan_id}/commit", response_model=ScanGetResp, status_code=200)
async def commit_scan(
    scan_id: UUID,
    body: ScanCommitReq,
    principal: ClerkPrincipal = Depends(  # noqa: B008
        require_role("owner", "admin", "member")
    ),
    team: Team = Depends(resolve_team_from_clerk_org),
) -> ScanGetResp:
    """Atomic commit per D-09 + D-11.

    Order: HEAD → fetch+validate → INSERT (final key) → Stripe → COMMIT
    → CopyObject pending→final → DeleteObject pending → enqueue indexing.
    """
    pending = _pending_key(scan_id)
    final = _final_key(team.id, scan_id)

    # 1. HEAD pending — 404 if missing, 413 if oversized.
    try:
        head_meta = await run_in_threadpool(r2.head, pending)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey", "NotFound"):
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "object_not_found"
            ) from e
        raise

    size = int(head_meta["ContentLength"])
    if size > _MAX_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            {"error": "too_large", "size_bytes": size, "max": _MAX_BYTES},
        )

    # 2. Fetch + Pydantic-validate ResourceGraph. We do not retain the
    # parsed graph past this point — the worker (Plan 06-06) will reparse
    # from R2 with full type info; this gate just ensures we don't commit
    # a row pointing at structurally invalid JSON.
    blob = await run_in_threadpool(r2.get_bytes, pending)
    try:
        ResourceGraph.model_validate_json(blob)
    except ValidationError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {"errors": e.errors()[:10]},
        ) from e

    # 3-5. tx: SET team GUC → INSERT scan row → Stripe meter event → COMMIT.
    sm = get_sessionmaker()
    async with sm() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('app.current_team_id', :t, true)"),
                {"t": str(team.id)},
            )
            scan = Scan(
                id=scan_id,
                team_id=team.id,
                r2_key=final,  # final key, even though bytes are still pending/
                sha256=body.sha256,
                size_bytes=size,
                status=ScanStatus.ready,
                branch=body.branch,
                commit_sha=body.commit_sha,
                source=body.source,
            )
            session.add(scan)
            # Surface UNIQUE-violation / RLS-WITH-CHECK failures BEFORE
            # the Stripe call — flushing here forces an INSERT roundtrip.
            await session.flush()

            # Stripe meter event — LAST statement in the tx. If this
            # raises, the enclosing session.begin() context manager
            # rolls back. Per D-09: every committed scan row carries a
            # meter event; partial states are impossible.
            #
            # Phase 7.5 Plan 05: extracted to app.services.scans so the
            # worker (scan_repo, Plan 06) shares the SAME meter call site
            # — keeps the D-08/D-09 invariant testable in isolation.
            await fire_scan_meter_or_502(
                scan_id=scan_id,
                stripe_customer_id=team.stripe_customer_id or "",
            )
        # Tx committed here on success; rolled back on any exception above.

    # 5b. Post-commit R2 move: pending/ → teams/.../, then delete pending/.
    # Failure here doesn't undo the DB commit — the scan row's r2_key
    # already points at `final`. We log a WARNING for on-call; Plan 08's
    # 7-day lifecycle rule on pending/ guarantees eventual GC. A Phase 7
    # reconciler task can retry the copy.
    try:
        await run_in_threadpool(r2.copy, src_key=pending, dst_key=final)
        await run_in_threadpool(r2.delete, pending)
    except ClientError as e:
        _log.warning(
            "r2_post_commit_copy_failed",
            scan_id=str(scan_id),
            pending=pending,
            final=final,
            error=repr(e),
        )

    # 6. Best-effort enqueue for the indexing worker (Plan 06-06 will
    # provide app.queue.tasks.indexing.enqueue_scan_indexing). Lazy import
    # so we don't fail at module-load while Plan 06-06 isn't shipped yet.
    try:  # pragma: no cover — depends on Plan 06-06 module
        from app.queue.tasks.indexing import enqueue_scan_indexing  # type: ignore[import-not-found]

        rid = structlog.contextvars.get_contextvars().get("request_id", "")
        await (
            enqueue_scan_indexing.kicker()
            .with_labels(request_id=rid)
            .kiq(scan_id=str(scan_id))
        )
    except Exception as e:  # noqa: BLE001 — enqueue failures must NOT undo the commit
        _log.warning(
            "indexing_enqueue_failed", scan_id=str(scan_id), error=repr(e)
        )

    # Build response (fresh team-scoped read so the row reflects committed state).
    async with sm() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('app.current_team_id', :t, true)"),
                {"t": str(team.id)},
            )
            row = (
                await session.execute(select(Scan).where(Scan.id == scan_id))
            ).scalar_one()
            get_url = await run_in_threadpool(
                r2.presigned_get, row.r2_key, _GET_TTL_SECONDS
            )
            return ScanGetResp(
                id=row.id,
                team_id=row.team_id,
                status=row.status,
                presigned_get_url=get_url,
                size_bytes=row.size_bytes,
                created_at=row.created_at,
                summary_json=row.summary_json,
                branch=row.branch,
                commit_sha=row.commit_sha,
                source=row.source,
                error_message=row.error_message,
                source_path=row.source_path,
                github_installation_id=row.github_installation_id,
                github_repo=row.github_repo,
                github_branch=row.github_branch,
                github_sha=row.github_sha,
            )


@router.get("/{scan_id}", response_model=ScanGetResp)
async def get_scan(
    scan_id: UUID,
    principal: ClerkPrincipal = Depends(  # noqa: B008
        require_role("owner", "admin", "member", "basic_member")
    ),
    team: Team = Depends(resolve_team_from_clerk_org),
) -> ScanGetResp:
    """Return scan metadata + presigned GET URL.

    Opens a team-scoped DB session inline (rather than via Depends) to
    avoid the FastAPI dep-graph dance for passing ``team`` into
    ``team_scoped_session`` — the inline form is clearer at the call site
    and equivalent in semantics. RLS enforces tenant isolation: a team_B
    principal asking for a team_A scan sees zero rows → 404
    ``scan_not_found`` (D-10: don't leak the existence of cross-team
    scan ids).
    """
    sm = get_sessionmaker()
    async with sm() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('app.current_team_id', :t, true)"),
                {"t": str(team.id)},
            )
            row = (
                await session.execute(select(Scan).where(Scan.id == scan_id))
            ).scalar_one_or_none()
            if row is None:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND, "scan_not_found"
                )
            # Phase 7.5 D-13: only sign a GET URL when the row is ready
            # (pending/failed rows have no R2 object — signing would
            # produce a URL that 404s against R2). The polling page
            # treats null as "still scanning / failed" and a non-null
            # URL as "render the viewer".
            get_url: str | None = None
            if row.status == ScanStatus.ready and row.r2_key:
                get_url = await run_in_threadpool(
                    r2.presigned_get, row.r2_key, _GET_TTL_SECONDS
                )
            return ScanGetResp(
                id=row.id,
                team_id=row.team_id,
                status=row.status,
                presigned_get_url=get_url,
                size_bytes=row.size_bytes,
                created_at=row.created_at,
                summary_json=row.summary_json,
                branch=row.branch,
                commit_sha=row.commit_sha,
                source=row.source,
                error_message=row.error_message,
                source_path=row.source_path,
                github_installation_id=row.github_installation_id,
                github_repo=row.github_repo,
                github_branch=row.github_branch,
                github_sha=row.github_sha,
            )


# ---------------------------------------------------------------------------
# GET /v1/scans — paginated scan-list endpoint (Plan 07-02).
# ---------------------------------------------------------------------------

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 100


def _encode_cursor(created_at: datetime, scan_id: UUID) -> str:
    """Encode a (created_at, id) tuple as a base64url-JSON cursor string.

    Cursor decoding is intentionally tolerant — a tampered or malformed
    cursor decodes to ``None`` and is silently ignored, returning the
    first page. Cross-team scans remain invisible because RLS still
    applies regardless of cursor contents (T-07-02-04 disposition).
    """
    payload = {"t": created_at.isoformat(), "i": str(scan_id)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, UUID] | None:
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return datetime.fromisoformat(payload["t"]), UUID(payload["i"])
    except Exception:  # noqa: BLE001 — tampered cursors fall back to page 1
        return None


@router.get("", response_model=ScanListResp)
async def list_scans(
    search: str | None = Query(default=None, max_length=255),
    environment: str | None = Query(default=None, max_length=32),
    scan_status: str | None = Query(default=None, alias="status"),
    created_after: str | None = Query(default=None),
    created_before: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    principal: ClerkPrincipal = Depends(  # noqa: B008
        require_role("owner", "admin", "member", "basic_member")
    ),
    team: Team = Depends(resolve_team_from_clerk_org),
) -> ScanListResp:
    """Paginated team-scoped scan list with optional filters.

    Cursor is (created_at DESC, id DESC) — stable, no offset drift.
    RLS enforces team isolation: cross-team rows are invisible at the DB
    layer. List rows do NOT include presigned URLs (only detail does); a
    list of N scans returns only metadata to keep payloads bounded.

    Per D-19, this endpoint does NOT fire Stripe Billing Meter events —
    metering occurs only on scan upload (Phase 6 D-08).
    """
    _ = principal  # auth dependency only

    sm = get_sessionmaker()
    async with sm() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('app.current_team_id', :t, true)"),
                {"t": str(team.id)},
            )

            q = select(Scan).order_by(Scan.created_at.desc(), Scan.id.desc())

            # --- cursor pagination ---
            if cursor:
                decoded = _decode_cursor(cursor)
                if decoded:
                    cur_ts, cur_id = decoded
                    q = q.where(
                        or_(
                            Scan.created_at < cur_ts,
                            and_(Scan.created_at == cur_ts, Scan.id < cur_id),
                        )
                    )

            # --- filters ---
            if search:
                pattern = f"%{search}%"
                q = q.where(
                    or_(
                        Scan.branch.ilike(pattern),
                        Scan.commit_sha.ilike(pattern),
                        Scan.source.ilike(pattern),
                    )
                )

            # environment maps to source for v1 (per D-06 — placeholder field).
            if environment:
                q = q.where(Scan.source == environment)

            if scan_status:
                q = q.where(Scan.status == scan_status)

            if created_after:
                try:
                    dt_after = datetime.fromisoformat(created_after).replace(
                        tzinfo=timezone.utc
                    )
                    q = q.where(Scan.created_at >= dt_after)
                except ValueError as e:
                    raise HTTPException(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        "invalid_created_after",
                    ) from e

            if created_before:
                try:
                    dt_before = datetime.fromisoformat(created_before).replace(
                        tzinfo=timezone.utc
                    )
                    q = q.where(Scan.created_at <= dt_before)
                except ValueError as e:
                    raise HTTPException(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        "invalid_created_before",
                    ) from e

            rows = (await session.execute(q.limit(limit + 1))).scalars().all()

    # Build next_cursor from the (limit+1)th row if present.
    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor: str | None = None
    if has_more and items:
        last = items[-1]
        next_cursor = _encode_cursor(last.created_at, last.id)

    return ScanListResp(
        items=[ScanListItemResp.model_validate(row) for row in items],
        next_cursor=next_cursor,
    )


# ---------------------------------------------------------------------------
# GET /v1/scans/{a}/compare/{b} — server-side scan diff (Plan 07-03, D-11).
# ---------------------------------------------------------------------------


@router.get("/{scan_a_id}/compare/{scan_b_id}", response_model=ResourceDiffResp)
async def compare_scans(
    scan_a_id: UUID,
    scan_b_id: UUID,
    principal: ClerkPrincipal = Depends(  # noqa: B008
        require_role("owner", "admin", "member", "basic_member")
    ),
    team: Team = Depends(resolve_team_from_clerk_org),
) -> ResourceDiffResp:
    """Diff two scans from the same team and return a ResourceDiffResp.

    Both scans must belong to the caller's team — RLS makes cross-team
    rows invisible inside the team-scoped session, so a missing row
    surfaces as 404 ``scan_not_found`` (D-18: don't leak cross-team
    scan-id existence).

    R2 blobs for both scans are fetched concurrently via
    :func:`asyncio.gather` so the wall-clock for the GET is bounded by
    the slower of the two object reads, not their sum (each scan ≤25 MB
    per D-11; two concurrent reads peak at ~50 MB which is acceptable).

    Diff is computed by :func:`app.services.diff.compute_diff` — a pure
    function reused by the future CLI ``infracanvas diff`` and the v1.2
    PR-bot.
    """
    _ = principal  # auth dependency only

    sm = get_sessionmaker()
    async with sm() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('app.current_team_id', :t, true)"),
                {"t": str(team.id)},
            )
            row_a = (
                await session.execute(select(Scan).where(Scan.id == scan_a_id))
            ).scalar_one_or_none()
            # Avoid two SELECTs when scan_a == scan_b — same row, fewer
            # round-trips, and still correct (compare-with-self is a
            # documented use case returning all-unchanged).
            if scan_b_id == scan_a_id:
                row_b = row_a
            else:
                row_b = (
                    await session.execute(select(Scan).where(Scan.id == scan_b_id))
                ).scalar_one_or_none()
            if row_a is None or row_b is None:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND, "scan_not_found"
                )
            # Capture R2 keys before the session closes so the post-session
            # block doesn't lazy-load anything off detached ORM rows.
            key_a = row_a.r2_key
            key_b = row_b.r2_key

    # Concurrent R2 fetch — never sequential for two large blobs.
    try:
        if key_a == key_b:
            # Same object — fetch once, reuse. compute_diff handles
            # identical-graphs-as-input correctly (all-unchanged).
            blob_a = await run_in_threadpool(r2.get_bytes, key_a)
            blob_b = blob_a
        else:
            blob_a, blob_b = await asyncio.gather(
                run_in_threadpool(r2.get_bytes, key_a),
                run_in_threadpool(r2.get_bytes, key_b),
            )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey", "NotFound"):
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "object_not_found"
            ) from exc
        raise

    try:
        graph_a = ResourceGraph.model_validate_json(blob_a)
        graph_b = (
            graph_a if blob_b is blob_a else ResourceGraph.model_validate_json(blob_b)
        )
    except ValidationError as exc:
        # The scan upload pipeline (Phase 6) Pydantic-validates before
        # committing the row, so reaching here means the R2 object was
        # tampered with after commit — a 500 is appropriate.
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "scan_blob_invalid"
        ) from exc

    return compute_diff(
        graph_a, graph_b, scan_a_id=scan_a_id, scan_b_id=scan_b_id
    )


# Re-export NodeDiff so OpenAPI schema generation picks it up via
# ResourceDiffResp.nodes; the `_ = NodeDiff` keeps Ruff F401 silent
# when the symbol is imported solely for the schema graph.
_ = NodeDiff
