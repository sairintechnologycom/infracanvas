"""``scan_repo`` taskiq job — Phase 7.5 Plan 06 (GH-03).

Single highest-risk job in Phase 7.5: shells out to ``git clone`` with a
short-lived installation token, runs ``infracanvas scan`` as a
subprocess, writes the JSON output to ``/tmp``, uploads to R2, and fires
the Stripe meter via :func:`app.services.scans.finalize_scan`.

Five threat classes converge here (see Plan 06 ``<threat_model>``):

* T-07.5-06-01 token leakage in argv (accept — Fly per-app VM tenancy)
* T-07.5-06-02 token leakage in stderr / structlog (mitigate via
  :func:`_redact_token` + structured-bind hygiene)
* T-07.5-06-03 path traversal via user-supplied subpath (mitigate via
  ``(tmp_root / path).resolve().relative_to(tmp_root.resolve())``)
* T-07.5-06-04 hung subprocess (mitigate via ``asyncio.wait_for`` +
  ``proc.kill()`` on ``TimeoutError``)
* T-07.5-06-07 race on ``status='ready'`` clobber (mitigate via
  ``UPDATE ... WHERE id=:id AND status='pending'`` guard)

Dispatch contract (locked by Plan 05's ``POST /v1/scans/from-github``):
the route enqueues with EXACTLY 7 keyword args — ``scan_id``,
``installation_id``, ``repo``, ``branch``, ``sha``, ``path``,
``team_id``. The ``@broker.task`` signature MUST accept these by name.

Failure-handling shape (Plan 06 must_haves.truths):

* Stripe meter failure inside :func:`finalize_scan`: the StripeError is
  re-raised so taskiq's :class:`SmartRetryMiddleware` can replay the
  job. We do NOT translate to HTTP 502 here (that's the route-side
  wrapper :func:`fire_scan_meter_or_502`).
* Any other failure (clone error, scan error, R2 PUT error, traversal
  reject): caught by the outer ``except Exception``, surfaced via an
  ``UPDATE scans SET status='failed', error_message=...`` (with the
  ``WHERE status='pending'`` guard), then re-raised.
* tmp_root removal runs in ``finally`` regardless of outcome.

References:

* RESEARCH.md lines 411-508 — taskiq-job code skeleton
* PATTERNS.md CC-5 (taskiq task definition), CC-6 (subprocess), CC-7
  (R2 commit / Stripe), CC-8 (observability propagation)
* CONTEXT.md D-02 (taskiq-Redis), D-06 (mint-per-scan), D-07 (URL
  embedding), D-09 (cd subpath + scan), D-13 (status enum), D-16
  (``/tmp/scan-{uuid4}`` + try/finally rmtree), D-17 (Sentry tags)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any

import sentry_sdk
import structlog
from sqlalchemy import text

from app.db.session import get_sessionmaker
from app.integrations.github.auth import mint_installation_token
from app.queue.broker import broker
from app.services.scans import finalize_scan
from app.storage.r2 import put_bytes

_log = structlog.get_logger("app.worker.scan_repo")

# Subprocess wall-clock caps (RESEARCH § Taskiq Job; CC-6).
# Wall-clock limits, NOT CPU; on Fly's per-app VM these align to the
# job's total budget = CLONE_TIMEOUT_S + SCAN_TIMEOUT_S ~ 9 min.
CLONE_TIMEOUT_S: float = 60.0
SCAN_TIMEOUT_S: float = 8 * 60.0


def _redact_token(text_blob: str, token: str) -> str:
    """Return ``text_blob`` with every occurrence of ``token`` replaced by
    ``***``. No-op if ``token`` is empty (worker hasn't minted yet).

    Centralised so every stderr decode and every exception message that
    might carry the bearer goes through one chokepoint. Tests assert the
    ``***`` marker AND the absence of the bare token (T-07.5-06-02).
    """
    if not token:
        return text_blob
    return text_blob.replace(token, "***")


def _make_tmp_root() -> Path:
    """Generate a per-job ``/tmp/scan-{uuid4}`` path.

    Factored to a helper so tests can monkeypatch and inspect cleanup
    without racing against the real ``/tmp``.
    """
    return Path("/tmp") / f"scan-{uuid.uuid4()}"


@broker.task(retry_on_error=True, max_retries=3, delay=5, task_name="scan_repo")
async def scan_repo(
    scan_id: str,
    installation_id: int,
    repo: str,
    branch: str,
    sha: str,
    path: str,
    team_id: str,
) -> None:
    """Clone the repo at HEAD, run infracanvas scan, upload to R2, finalize.

    Dispatch shape locked by Plan 05's ``POST /v1/scans/from-github``
    handler — the route enqueues with these exact 7 kwargs (CC-4).

    Two-phase team handling (CC-5 divergence): the route already passes
    ``team_id`` as a kwarg, so unlike :func:`enqueue_scan_indexing` we do
    NOT need a SECURITY DEFINER ``scan_team_id()`` lookup — we go
    straight to the team-scoped session.

    On any non-Stripe failure: UPDATE the scans row to ``status='failed'``
    + ``error_message`` (guarded by ``WHERE status='pending'`` so a row
    that already raced to ``ready`` is not clobbered — T-07.5-06-07).
    On a StripeError from :func:`finalize_scan`: re-raise so taskiq's
    SmartRetryMiddleware reschedules the job.
    """
    log_ctx = _log.bind(
        scan_id=scan_id,
        team_id=team_id,
        installation_id=installation_id,
        repo=repo,
        branch=branch,
        sha=sha[:8] if sha else None,
    )
    sentry_sdk.set_tag("scan_id", scan_id)
    sentry_sdk.set_tag("team_id", team_id)
    sentry_sdk.set_tag("installation_id", str(installation_id))
    sentry_sdk.set_tag("repo", repo)
    sentry_sdk.set_tag("branch", branch)
    if sha:
        sentry_sdk.set_tag("github_sha", sha[:8])

    log_ctx.info("scan_repo.start")

    tmp_root = _make_tmp_root()
    token: str = ""

    try:
        # ---- 1. Mint a fresh installation token (D-06). ------------------
        token = await mint_installation_token(installation_id)

        # ---- 2. Prepare the clone target. --------------------------------
        # exist_ok=False because uuid4 collision is astronomical — if it
        # somehow happens, fail loudly so we don't write into a dir we
        # don't own.
        tmp_root.mkdir(parents=True, exist_ok=False)
        clone_url = (
            f"https://x-access-token:{token}@github.com/{repo}.git"
        )

        # ---- 3. Shallow clone, timeboxed (CLONE_TIMEOUT_S). --------------
        # GIT_TERMINAL_PROMPT=0 prevents an interactive prompt if the
        # token were ever rejected (landmine #6 / RESEARCH § F1).
        clone_proc = await asyncio.create_subprocess_exec(
            "git",
            "clone",
            "--depth=1",
            "--single-branch",
            "--branch",
            branch,
            clone_url,
            str(tmp_root),
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, clone_stderr = await asyncio.wait_for(
                clone_proc.communicate(), timeout=CLONE_TIMEOUT_S
            )
        except TimeoutError as toexc:
            clone_proc.kill()
            await clone_proc.wait()
            raise RuntimeError(
                f"git clone timed out after {CLONE_TIMEOUT_S:g}s"
            ) from toexc

        if clone_proc.returncode != 0:
            sanitized = _redact_token(
                clone_stderr.decode(errors="replace"), token
            )
            raise RuntimeError(
                f"git clone failed (rc={clone_proc.returncode}): "
                f"{sanitized[:500]}"
            )

        # ---- 4. Path-traversal guard (T-07.5-06-03). ---------------------
        candidate = (tmp_root / path).resolve()
        tmp_resolved = tmp_root.resolve()
        try:
            candidate.relative_to(tmp_resolved)
        except ValueError as vexc:
            raise ValueError(
                f"path traversal detected: {path!r}"
            ) from vexc
        if not candidate.is_dir():
            raise ValueError(
                f"subpath {path!r} not found in {repo}@{branch}"
            )

        # ---- 5. Run infracanvas scan, timeboxed (SCAN_TIMEOUT_S). --------
        scan_json_path = candidate / "scan.json"
        scan_proc = await asyncio.create_subprocess_exec(
            "infracanvas",
            "scan",
            ".",
            "--ci",
            "--output",
            str(scan_json_path),
            cwd=str(candidate),
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, scan_stderr = await asyncio.wait_for(
                scan_proc.communicate(), timeout=SCAN_TIMEOUT_S
            )
        except TimeoutError as toexc:
            scan_proc.kill()
            await scan_proc.wait()
            raise RuntimeError(
                f"infracanvas scan timed out after {SCAN_TIMEOUT_S:g}s"
            ) from toexc

        # rc 0 = no findings, 1 = findings present (still success),
        # 2 = error (landmine #13).
        if scan_proc.returncode not in (0, 1):
            sanitized = _redact_token(
                scan_stderr.decode(errors="replace"), token
            )
            raise RuntimeError(
                f"scan failed (rc={scan_proc.returncode}): "
                f"{sanitized[:500]}"
            )

        # ---- 6. Read + hash the scan output. -----------------------------
        payload_bytes = scan_json_path.read_bytes()
        sha256 = hashlib.sha256(payload_bytes).hexdigest()
        size_bytes = len(payload_bytes)
        summary_json = _extract_summary(payload_bytes)

        # ---- 7. Upload to R2 (D-07 key shape). ---------------------------
        r2_key = f"teams/{team_id}/scans/{scan_id}.json"
        await put_bytes(r2_key, payload_bytes, "application/json")

        # ---- 8. Finalize: UPDATE pending->ready + Stripe meter. ----------
        # Two-phase tx: open a fresh team-scoped session for the helper.
        # The Team row tells us the Stripe customer id; finalize_scan
        # owns the UPDATE + meter atomicity (with rollback on Stripe
        # failure; SmartRetryMiddleware retries by virtue of the raised
        # StripeError bubbling out of this whole task body).
        sm = get_sessionmaker()
        async with sm() as session:
            async with session.begin():
                await session.execute(
                    text("SELECT set_config('app.current_team_id', :t, true)"),
                    {"t": team_id},
                )
                team_row = (
                    await session.execute(
                        text(
                            "SELECT id, stripe_customer_id "
                            "FROM teams WHERE id = :id"
                        ),
                        {"id": team_id},
                    )
                ).one_or_none()
                stripe_customer_id = (
                    team_row.stripe_customer_id if team_row is not None else ""
                )

                await finalize_scan(
                    session,
                    scan_id=scan_id,
                    team_id=team_id,
                    stripe_customer_id=stripe_customer_id or "",
                    r2_key=r2_key,
                    sha256=sha256,
                    size_bytes=size_bytes,
                    summary_json=summary_json,
                )

        log_ctx.info(
            "scan_repo.success",
            r2_key=r2_key,
            size_bytes=size_bytes,
            sha256=sha256,
        )

    except Exception as exc:
        # Log with the message redacted (defence: even if we forgot to
        # redact at the throw site, this catches it at the log site too).
        msg_for_log = (
            _redact_token(str(exc), token) if token else str(exc)
        )
        log_ctx.error("scan_repo.failed", error=msg_for_log)

        # Best-effort failure-path UPDATE. If even this DB call fails we
        # still re-raise the original exception below so taskiq can
        # retry. The pending guard (WHERE status='pending') prevents
        # clobbering a row that already raced to 'ready' (T-07.5-06-07).
        try:
            sm = get_sessionmaker()
            async with sm() as session:
                async with session.begin():
                    await session.execute(
                        text(
                            "SELECT set_config('app.current_team_id', "
                            ":t, true)"
                        ),
                        {"t": team_id},
                    )
                    await session.execute(
                        text(
                            "UPDATE scans SET status='failed', "
                            "error_message=:msg "
                            "WHERE id=:id AND status='pending'"
                        ),
                        {"id": scan_id, "msg": msg_for_log[:500]},
                    )
        except Exception as db_exc:  # noqa: BLE001 — DB failure is itself non-fatal here
            log_ctx.warning(
                "scan_repo.failure_update_failed", error=repr(db_exc)
            )

        raise

    finally:
        # Belt-and-suspenders cleanup. shutil.rmtree(ignore_errors=True)
        # so a partial cleanup doesn't mask the original exception.
        if tmp_root.exists():
            shutil.rmtree(tmp_root, ignore_errors=True)


def _extract_summary(payload_bytes: bytes) -> dict[str, Any] | None:
    """Pull the ``summary`` block out of the scan JSON without re-parsing
    the full graph here. Returns ``None`` if the JSON is malformed or
    has no summary key (finalize_scan accepts ``None``).

    The actual ResourceGraph validation is the indexing job's
    responsibility (Phase 6 Plan 06-06) — we just persist what the CLI
    emitted so the list page can render counts pre-indexing.
    """
    try:
        decoded = json.loads(payload_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(decoded, dict):
        return None
    summary = decoded.get("summary")
    if isinstance(summary, dict):
        return summary
    return None
