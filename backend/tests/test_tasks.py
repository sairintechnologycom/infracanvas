"""Integration tests for ``enqueue_scan_indexing`` + queue middlewares.

Test IDs (per Plan 06-06 must_haves.truths):

* JOB-001 — In-memory broker fires the task; ``scans.summary_json`` is
  populated within a few seconds.
* JOB-002 — Task raises twice then succeeds; ``SmartRetryMiddleware``
  replays it the appropriate number of times.
* JOB-003 — Task always fails; ``DLQLogMiddleware.on_error`` emits a
  structured log line with ``dlq=true`` after retries are exhausted.
* JOB-004 — kicker label ``request_id=...`` reaches the worker side via
  ``RequestIdMiddleware`` and shows up in the task body's structlog
  contextvar.

The DB-touching tests carry the ``rls`` marker because they need the
Postgres testcontainer with migration 004 applied. The pure-broker
retry/DLQ/request_id tests do not — they exercise middleware behaviour
without any DB session.
"""

from __future__ import annotations

import json
import secrets
from io import StringIO
from typing import Any

import pytest
import structlog
from sqlalchemy import select
from taskiq import InMemoryBroker
from taskiq.middlewares import SmartRetryMiddleware

from app.db.models import Scan, ScanStatus, Team
from app.queue.middleware import DLQLogMiddleware, RequestIdMiddleware
from app.queue.tasks.indexing import enqueue_scan_indexing
from app.util.ids import new_uuid7


# A minimally-valid ResourceGraph blob with a single critical finding so the
# computed summary is deterministic and asserts cleanly: 1 resource, 1 critical
# finding → score = 100 - 20 = 80.
# Minimal valid ResourceGraph blob: ResourceNode requires id/type/name/provider;
# every other field has a default. One critical finding so compute_summary()
# yields a deterministic shape we can assert: total_resources=1, score=80.
_VALID_GRAPH = json.dumps(
    {
        "nodes": [
            {
                "id": "aws_s3_bucket.a",
                "type": "aws_s3_bucket",
                "name": "a",
                "provider": "aws",
                "findings": [
                    {
                        "rule_id": "SEC-001",
                        "severity": "critical",
                        "title": "T",
                        "description": "D",
                        "remediation": "R",
                    }
                ],
            }
        ],
    }
).encode()


# ---------------------------------------------------------------------------
# Shared fixtures for the DB-touching JOB-001 / JOB-004 tests.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _wire_r2_to_moto(monkeypatch: pytest.MonkeyPatch, mock_r2: Any) -> None:
    """Replace ``app.storage.r2.get_r2_client`` with a moto-backed client.

    Same pattern as ``tests/test_scans.py::_wire_r2_to_moto`` — moto
    intercepts at the botocore layer so a stock ``boto3.client('s3', ...)``
    works without endpoint_url tricks. Auto-applied for every test in
    this module so even pure-broker tests don't accidentally hit the
    real R2 endpoint when fixtures touch it.
    """
    import os

    import boto3
    from botocore.config import Config

    from app.settings import settings
    from app.storage import r2 as r2_mod

    r2_mod.get_r2_client.cache_clear()
    monkeypatch.setattr(settings, "r2_bucket", mock_r2.bucket)

    moto_client = boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4"),
    )
    monkeypatch.setattr(r2_mod, "get_r2_client", lambda: moto_client)


@pytest.fixture
async def _wire_db_to_pg(
    pg_container: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Repoint the app's async engine at the testcontainer using NullPool.

    NullPool is required because pytest-asyncio's per-test event loop is
    different from the long-lived production pool's loop; a pooled
    connection would carry futures from a closed loop into the next test.
    Same rationale as ``test_scans.py::app_client``.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from app.db import session as sess_mod
    from app.settings import settings

    host = pg_container.get_container_host_ip()
    port = pg_container.get_exposed_port(5432)
    dbname = pg_container.dbname if hasattr(pg_container, "dbname") else "test"
    db_url = f"postgresql+asyncpg://infracanvas_app:app@{host}:{port}/{dbname}"
    monkeypatch.setattr(settings, "database_url", db_url)

    test_engine = create_async_engine(db_url, poolclass=NullPool)
    test_sm = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=sess_mod.AsyncSession
    )
    monkeypatch.setattr(sess_mod, "_engine", test_engine)
    monkeypatch.setattr(sess_mod, "_Session", test_sm)


@pytest.fixture
async def team_with_scan(
    seed_session: Any, mock_r2: Any
) -> tuple[Team, Scan]:
    """Seed a Team + a 'ready' Scan row pointing at a moto-resident blob.

    The blob lives at ``teams/<team_id>/scans/<scan_id>.json`` (the final
    location used by Plan 06-05's commit handler). The scan_team_id()
    SECURITY DEFINER helper installed by migration 004 is what the worker
    uses to discover ``team_id`` from ``scan_id``.
    """
    team = Team(
        id=new_uuid7(),
        clerk_org_id=f"org_idx_{secrets.token_hex(6)}",
        name="Idx",
        stripe_customer_id="cus",
    )
    scan = Scan(
        id=new_uuid7(),
        team_id=team.id,
        r2_key=f"teams/{team.id}/scans/idx.json",
        size_bytes=len(_VALID_GRAPH),
        status=ScanStatus.ready,
    )
    async with seed_session.begin():
        seed_session.add(team)
        await seed_session.flush()  # FK target must exist before scan INSERT
        seed_session.add(scan)

    # Write the blob into moto so the task can fetch it.
    from app.storage.r2 import get_r2_client

    get_r2_client().put_object(
        Bucket=mock_r2.bucket,
        Key=scan.r2_key,
        Body=_VALID_GRAPH,
        ContentType="application/json",
    )
    return team, scan


# ---------------------------------------------------------------------------
# JOB-001: full-flow test — task body populates summary_json under RLS.
# ---------------------------------------------------------------------------


@pytest.mark.rls
async def test_enqueue_scan_indexing_populates_summary(
    team_with_scan: tuple[Team, Scan],
    seed_session: Any,
    _wire_db_to_pg: None,
) -> None:
    """JOB-001: invoking the task body writes summary_json with the
    correct counts/score.

    Calls ``enqueue_scan_indexing.original_func`` (the unwrapped async body)
    directly rather than going through ``InMemoryBroker.kiq()`` — the
    contract under test is the body's behaviour, not taskiq's wiring.
    Going through the broker would require registering against an
    InMemoryBroker instance and wiring the production module's broker
    reference; that adds noise without exercising any extra contract.
    """
    _team, scan = team_with_scan

    await enqueue_scan_indexing.original_func(str(scan.id))

    # Re-read via BYPASSRLS seed_session so we don't have to set the GUC.
    refreshed = (
        await seed_session.execute(select(Scan).where(Scan.id == scan.id))
    ).scalar_one()
    assert refreshed.summary_json is not None
    summary = refreshed.summary_json
    assert summary["total_resources"] == 1
    assert summary["findings"] == {
        "critical": 1,
        "high": 0,
        "medium": 0,
        "info": 0,
    }
    # Score: 100 - (1 critical × 20) = 80.
    assert summary["score"] == 80
    assert summary["estimated_monthly_cost"] == 0.0


# ---------------------------------------------------------------------------
# JOB-002: SmartRetryMiddleware retries a transient-failing task.
# ---------------------------------------------------------------------------


async def test_task_retries_on_error_via_smart_retry() -> None:
    """JOB-002: a task raising ``RuntimeError`` twice succeeds on the
    third attempt; ``SmartRetryMiddleware`` replays the failed schedule.

    Pure broker test — does not touch DB or R2, so it does not need the
    ``rls`` marker. Uses ``InMemoryBroker`` with the same retry middleware
    we ship in production (with ``default_delay=0`` so the test runs fast).
    """
    in_mem = InMemoryBroker().with_middlewares(
        SmartRetryMiddleware(default_retry_count=3, default_delay=0)
    )
    calls = {"n": 0}

    @in_mem.task(retry_on_error=True, max_retries=3, delay=0)
    async def flaky(scan_id: str) -> None:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")

    await in_mem.startup()
    try:
        sent = await flaky.kiq(scan_id="s_test")
        result = await sent.wait_result(timeout=10)
        assert not result.is_err, f"expected success after 3 attempts; {result.error!r}"
    finally:
        await in_mem.shutdown()
    assert calls["n"] == 3, f"expected 3 attempts, saw {calls['n']}"


# ---------------------------------------------------------------------------
# JOB-003: DLQLogMiddleware emits dlq=true after retries are exhausted.
# ---------------------------------------------------------------------------


async def test_task_dlq_log_emitted_on_exhausted_retries() -> None:
    """JOB-003: when SmartRetryMiddleware exhausts retries and the task
    fails permanently, ``DLQLogMiddleware.on_error`` fires a structured
    log line with ``dlq=true``.

    We don't go through the full broker harness (capsys interactions
    with InMemoryBroker's worker loop are version-sensitive). Instead we
    invoke ``DLQLogMiddleware.on_error`` directly with a synthetic
    message labelled ``_retry_count=3, max_retries=3``. This tests the
    same observable contract the production retry path triggers.
    """
    from taskiq.message import TaskiqMessage
    from taskiq.result import TaskiqResult

    # Capture structlog output by configuring a StringIO logger factory
    # for the duration of the test.
    buf = StringIO()
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(file=buf),
        cache_logger_on_first_use=False,
    )
    try:
        msg = TaskiqMessage(
            task_id="t1",
            task_name="t.fail",
            labels={
                "_retry_count": "3",
                "max_retries": "3",
                "request_id": "trace-dlq",
            },
            labels_types=None,
            args=["s_test"],
            kwargs={},
        )
        result: TaskiqResult[Any] = TaskiqResult(
            is_err=True, return_value=None, execution_time=0.0, error=RuntimeError("permanent")
        )
        await DLQLogMiddleware().on_error(msg, result, RuntimeError("permanent"))
    finally:
        # Reset structlog so other tests inherit the standard config.
        from app.obs.logging import configure_logging

        configure_logging()

    out = buf.getvalue()
    dlq_lines = [
        ln for ln in out.splitlines() if '"dlq": true' in ln or '"dlq":true' in ln
    ]
    assert len(dlq_lines) >= 1, f"expected dlq=true log line; out={out[:600]!r}"
    # And the request_id is preserved in the log line for cross-trace correlation.
    assert "trace-dlq" in dlq_lines[0]


# ---------------------------------------------------------------------------
# JOB-004: kicker labels propagate request_id into worker contextvar.
# ---------------------------------------------------------------------------


async def test_request_id_propagates_into_worker_contextvar() -> None:
    """JOB-004: when the kicker attaches ``request_id``, the worker-side
    ``RequestIdMiddleware.pre_execute`` rebinds it into the structlog
    contextvar so log lines emitted inside the task body share the trace.

    This is the D-21 single-trace-id observability contract proved
    end-to-end in-process. We use ``InMemoryBroker`` + the production
    middleware (same instance type), kick a probe task with labels, and
    have the probe read back the contextvar.
    """
    in_mem = InMemoryBroker().with_middlewares(RequestIdMiddleware())
    captured: dict[str, Any] = {"rid": None, "scan_id": None}

    @in_mem.task
    async def probe(scan_id: str) -> None:
        ctx = structlog.contextvars.get_contextvars()
        captured["rid"] = ctx.get("request_id")
        captured["scan_id"] = ctx.get("scan_id")

    await in_mem.startup()
    try:
        sent = await probe.kicker().with_labels(request_id="trace-xyz-789").kiq(
            "s_arg_payload"
        )
        await sent.wait_result(timeout=5)
    finally:
        await in_mem.shutdown()

    assert captured["rid"] == "trace-xyz-789"
    # Convenience binding: scan_id from positional args[0] also bound.
    assert captured["scan_id"] == "s_arg_payload"
