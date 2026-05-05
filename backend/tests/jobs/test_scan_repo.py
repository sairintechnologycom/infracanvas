"""Integration tests for ``scan_repo`` taskiq job — Phase 7.5 Plan 06.

Tests the full pipeline: token mint, shallow clone, infracanvas scan
subprocess, R2 upload, ``finalize_scan`` (DB UPDATE pending then ready
plus Stripe meter). Plus the failure paths: clone timeout, scan timeout,
subpath traversal, scan rc=2, R2 ClientError, finalize-time race.

Test inventory (matches Plan 06 behavior list):

* JOB-SR-01 ``test_happy_path`` — clone+scan+upload+finalize success
* JOB-SR-02 ``test_clone_timeout`` — flips status='failed'
* JOB-SR-03 ``test_scan_timeout`` — flips status='failed'
* JOB-SR-04 ``test_subpath_traversal_rejected``
* JOB-SR-05 ``test_subpath_absolute_rejected``
* JOB-SR-06 ``test_subpath_not_found``
* JOB-SR-07 ``test_tmpdir_cleanup_on_exception``
* JOB-SR-08 ``test_token_redacted_in_stderr_log``
* JOB-SR-09 ``test_token_never_in_log_bind``
* JOB-SR-10 ``test_scan_rc1_treated_as_success`` — findings present
* JOB-SR-11 ``test_scan_rc2_failure``
* JOB-SR-12 ``test_failed_update_uses_pending_guard``
* JOB-SR-13 ``test_team_id_passed_via_kwarg`` — CC-5 divergence smoke

The DB-touching tests carry the ``rls`` marker so they require the
Postgres testcontainer (skipped locally with ``GSD_SKIP_TESTCONTAINERS=1``;
CI runs them). Pure-subprocess / pure-tmpdir tests do not need the
marker — they exercise the worker logic without DB.
"""

from __future__ import annotations

import asyncio
import json
import secrets
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Shared helpers — mock subprocess factory and tmpdir snapshot inspector.
# ---------------------------------------------------------------------------


class _FakeProc:
    """Minimal stand-in for ``asyncio.subprocess.Process`` that the worker
    awaits via ``proc.communicate()`` / ``proc.kill()`` / ``proc.wait()``.
    """

    def __init__(
        self,
        *,
        returncode: int = 0,
        stdout: bytes = b"",
        stderr: bytes = b"",
        hang: bool = False,
        on_communicate: Any = None,
    ) -> None:
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr
        self._hang = hang
        self._killed = False
        self._on_communicate = on_communicate

    async def communicate(self) -> tuple[bytes, bytes]:
        if self._on_communicate is not None:
            self._on_communicate()
        if self._hang:
            await asyncio.sleep(3600)
        return self._stdout, self._stderr

    def kill(self) -> None:
        self._killed = True

    async def wait(self) -> int:
        return self.returncode


def _exec_factory(
    *,
    clone_proc: _FakeProc | None = None,
    scan_proc: _FakeProc | None = None,
    write_scan_json_at: Path | None = None,
    scan_payload: dict[str, Any] | None = None,
):
    """Build a stand-in for ``asyncio.create_subprocess_exec``.

    The factory dispatches on the first argv element:

    * ``"git"`` returns ``clone_proc``; ALSO mkdir's the clone target so
      the worker's path-traversal/is_dir check sees a real directory.
    * ``"infracanvas"`` returns ``scan_proc``; ALSO writes the requested
      ``scan.json`` if ``write_scan_json_at`` + ``scan_payload`` are set.
    """

    async def _create_subprocess(*argv, **kwargs):  # type: ignore[no-untyped-def]
        program = argv[0]
        if program == "git":
            target = Path(argv[-1])
            if (clone_proc is None) or clone_proc.returncode == 0:
                target.mkdir(parents=True, exist_ok=True)
            return clone_proc or _FakeProc(returncode=0)
        if program == "infracanvas":
            if (
                write_scan_json_at is not None
                and scan_payload is not None
                and (scan_proc is None or scan_proc.returncode in (0, 1))
            ):
                write_scan_json_at.parent.mkdir(parents=True, exist_ok=True)
                write_scan_json_at.write_bytes(json.dumps(scan_payload).encode())
            return scan_proc or _FakeProc(returncode=0)
        raise AssertionError(f"unexpected subprocess: {argv!r}")

    return _create_subprocess


# ---------------------------------------------------------------------------
# Wire R2 to moto for any test that uploads (mirrors test_tasks.py pattern).
# ---------------------------------------------------------------------------


@pytest.fixture
def _wire_r2_to_moto(monkeypatch: pytest.MonkeyPatch, mock_r2: Any) -> None:
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

    Mirrors ``tests/test_tasks.py::_wire_db_to_pg``. Required because the
    worker calls ``get_sessionmaker()`` from its module body, and that
    sessionmaker would otherwise point at the .env DATABASE_URL (likely
    localhost:5432, not the testcontainer host:port).
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
def stub_stripe_meter(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Replace ``stripe_meter._client`` with a SDK-shape capturing stub.

    Returns a dict with ``calls`` (list of (params, options)) and
    ``next_failure`` (set to True to make the next call raise StripeError).
    Mirrors the same-name fixture in ``tests/test_scans.py``.
    """
    import stripe

    from app.billing import stripe_meter

    state: dict[str, Any] = {"calls": [], "next_failure": False}

    class _MeterEvents:
        def create(self, *, params: Any, options: Any = None) -> Any:
            if state["next_failure"]:
                state["next_failure"] = False
                raise stripe.error.APIError("simulated_meter_failure")
            state["calls"].append({"params": dict(params), "options": options})
            return None

    class _Billing:
        meter_events = _MeterEvents()

    class _V2:
        billing = _Billing()

    class _Client:
        v2 = _V2()

    monkeypatch.setattr(stripe_meter, "_client", lambda: _Client())
    return state


@pytest.fixture
def _stub_mint_token(monkeypatch: pytest.MonkeyPatch) -> str:
    """Stub mint_installation_token to a known value the redaction tests
    can assert against. Returned string is the test token."""
    token = "ghs_redact_me_abc123"

    async def _fake_mint(installation_id: int) -> str:
        return token

    import app.queue.tasks.scan_repo as sr_mod

    monkeypatch.setattr(sr_mod, "mint_installation_token", _fake_mint)
    return token


# ---------------------------------------------------------------------------
# Helper: stub the DB failure-path UPDATE call so non-DB tests do not need
# the testcontainer.
# ---------------------------------------------------------------------------


def _stub_db_update_to_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace ``get_sessionmaker`` inside scan_repo with a no-op factory
    so the failure-path DB UPDATE does not try to connect to Postgres.
    """
    import app.queue.tasks.scan_repo as sr_mod

    class _NoopSession:
        async def __aenter__(self):  # type: ignore[no-untyped-def]
            return self

        async def __aexit__(self, *exc):  # type: ignore[no-untyped-def]
            return False

        def begin(self):  # type: ignore[no-untyped-def]
            class _Tx:
                async def __aenter__(self_inner):  # type: ignore[no-untyped-def]  # noqa: N805
                    return self_inner

                async def __aexit__(self_inner, *exc):  # type: ignore[no-untyped-def]  # noqa: N805
                    return False

            return _Tx()

        async def execute(self, *_args, **_kwargs):  # type: ignore[no-untyped-def]
            class _R:
                def scalar_one_or_none(self_inner):  # type: ignore[no-untyped-def]  # noqa: N805
                    return None

            return _R()

    class _NoopMaker:
        def __call__(self):  # type: ignore[no-untyped-def]
            return _NoopSession()

    monkeypatch.setattr(sr_mod, "get_sessionmaker", lambda: _NoopMaker())


# ---------------------------------------------------------------------------
# JOB-SR-13 (smoke): module imports, decorator + signature shape.
# Runs independently of DB / R2 — verifies Plan 06 lands the contracted
# 7-kwarg async def + @broker.task decorator.
# ---------------------------------------------------------------------------


def test_team_id_passed_via_kwarg() -> None:
    """JOB-SR-13: scan_repo signature accepts the 7 CC-4 kwargs and
    carries the @broker.task decorator (taskiq exposes ``.original_func``
    + ``.task_name`` on a decorated task).
    """
    import inspect

    from app.queue.tasks.scan_repo import scan_repo

    assert hasattr(scan_repo, "original_func"), (
        "scan_repo must be a @broker.task — missing .original_func attr"
    )
    sig = inspect.signature(scan_repo.original_func)
    expected = {
        "scan_id",
        "installation_id",
        "repo",
        "branch",
        "sha",
        "path",
        "team_id",
    }
    assert set(sig.parameters) == expected, (
        f"scan_repo signature must accept exactly the 7 CC-4 kwargs; "
        f"saw {set(sig.parameters)!r}"
    )


# ---------------------------------------------------------------------------
# JOB-SR-04, JOB-SR-05, JOB-SR-07, JOB-SR-08, JOB-SR-09 — pure-subprocess
# tests that DO NOT touch DB/R2/Stripe. They short-circuit early enough
# that no upload / finalize call is reached.
# ---------------------------------------------------------------------------


async def test_subpath_traversal_rejected(
    monkeypatch: pytest.MonkeyPatch,
    _stub_mint_token: str,
    tmp_path: Path,
) -> None:
    """JOB-SR-04: ``path='../etc'`` resolves outside tmp_root → ValueError
    is caught; failure-path UPDATE is attempted (we stub the DB session)
    and tmp_root is cleaned up.
    """
    import app.queue.tasks.scan_repo as sr_mod

    monkeypatch.setattr(
        asyncio,
        "create_subprocess_exec",
        _exec_factory(),
    )
    _stub_db_update_to_noop(monkeypatch)

    forced_tmp = tmp_path / "scan-traversal"
    monkeypatch.setattr(
        sr_mod, "_make_tmp_root", lambda: forced_tmp, raising=False
    )

    with pytest.raises(ValueError, match="path traversal"):
        await sr_mod.scan_repo.original_func(
            scan_id="sc_trav",
            installation_id=1,
            repo="acme/infra",
            branch="main",
            sha="f" * 40,
            path="../etc",
            team_id="00000000-0000-0000-0000-000000000001",
        )

    assert not forced_tmp.exists(), "tmp_root must be removed after failure"


async def test_subpath_absolute_rejected(
    monkeypatch: pytest.MonkeyPatch,
    _stub_mint_token: str,
    tmp_path: Path,
) -> None:
    """JOB-SR-05: path='/etc' resolves outside tmp_root → ValueError."""
    import app.queue.tasks.scan_repo as sr_mod

    monkeypatch.setattr(
        asyncio, "create_subprocess_exec", _exec_factory()
    )
    _stub_db_update_to_noop(monkeypatch)

    forced_tmp = tmp_path / "scan-abs"
    monkeypatch.setattr(
        sr_mod, "_make_tmp_root", lambda: forced_tmp, raising=False
    )

    with pytest.raises(ValueError, match="path traversal"):
        await sr_mod.scan_repo.original_func(
            scan_id="sc_abs",
            installation_id=1,
            repo="acme/infra",
            branch="main",
            sha="f" * 40,
            path="/etc",
            team_id="00000000-0000-0000-0000-000000000001",
        )
    assert not forced_tmp.exists()


async def test_subpath_not_found(
    monkeypatch: pytest.MonkeyPatch,
    _stub_mint_token: str,
    tmp_path: Path,
) -> None:
    """JOB-SR-06: path='nonexistent' is inside tmp_root but not a dir →
    ValueError "subpath ... not found"."""
    import app.queue.tasks.scan_repo as sr_mod

    monkeypatch.setattr(
        asyncio, "create_subprocess_exec", _exec_factory()
    )
    _stub_db_update_to_noop(monkeypatch)

    forced_tmp = tmp_path / "scan-missing"
    monkeypatch.setattr(
        sr_mod, "_make_tmp_root", lambda: forced_tmp, raising=False
    )

    with pytest.raises(ValueError, match="not found"):
        await sr_mod.scan_repo.original_func(
            scan_id="sc_missing",
            installation_id=1,
            repo="acme/infra",
            branch="main",
            sha="f" * 40,
            path="nonexistent",
            team_id="00000000-0000-0000-0000-000000000001",
        )
    assert not forced_tmp.exists()


async def test_clone_timeout(
    monkeypatch: pytest.MonkeyPatch,
    _stub_mint_token: str,
    tmp_path: Path,
) -> None:
    """JOB-SR-02: clone subprocess hangs → asyncio.TimeoutError surfaces
    as RuntimeError "git clone timed out"; tmp_root is removed.
    """
    import app.queue.tasks.scan_repo as sr_mod

    monkeypatch.setattr(sr_mod, "CLONE_TIMEOUT_S", 0.05)

    monkeypatch.setattr(
        asyncio,
        "create_subprocess_exec",
        _exec_factory(clone_proc=_FakeProc(hang=True)),
    )
    _stub_db_update_to_noop(monkeypatch)

    forced_tmp = tmp_path / "scan-clone-to"
    monkeypatch.setattr(
        sr_mod, "_make_tmp_root", lambda: forced_tmp, raising=False
    )

    with pytest.raises(RuntimeError, match="git clone timed out"):
        await sr_mod.scan_repo.original_func(
            scan_id="sc_clone_to",
            installation_id=1,
            repo="acme/infra",
            branch="main",
            sha="f" * 40,
            path=".",
            team_id="00000000-0000-0000-0000-000000000001",
        )
    assert not forced_tmp.exists()


async def test_scan_timeout(
    monkeypatch: pytest.MonkeyPatch,
    _stub_mint_token: str,
    tmp_path: Path,
) -> None:
    """JOB-SR-03: scan subprocess hangs → RuntimeError "infracanvas scan
    timed out"; tmp_root removed.
    """
    import app.queue.tasks.scan_repo as sr_mod

    monkeypatch.setattr(sr_mod, "SCAN_TIMEOUT_S", 0.05)

    monkeypatch.setattr(
        asyncio,
        "create_subprocess_exec",
        _exec_factory(scan_proc=_FakeProc(hang=True)),
    )
    _stub_db_update_to_noop(monkeypatch)

    forced_tmp = tmp_path / "scan-scan-to"
    monkeypatch.setattr(
        sr_mod, "_make_tmp_root", lambda: forced_tmp, raising=False
    )

    with pytest.raises(RuntimeError, match="infracanvas scan timed out"):
        await sr_mod.scan_repo.original_func(
            scan_id="sc_scan_to",
            installation_id=1,
            repo="acme/infra",
            branch="main",
            sha="f" * 40,
            path=".",
            team_id="00000000-0000-0000-0000-000000000001",
        )
    assert not forced_tmp.exists()


async def test_token_redacted_in_stderr_log(
    monkeypatch: pytest.MonkeyPatch,
    _stub_mint_token: str,
    tmp_path: Path,
) -> None:
    """JOB-SR-08: clone fails with stderr containing the token → the
    captured RuntimeError message has '***' instead of the bare token.
    """
    import app.queue.tasks.scan_repo as sr_mod

    token = _stub_mint_token  # "ghs_redact_me_abc123"
    stderr_with_token = (
        f"fatal: unable to access "
        f"'https://x-access-token:{token}@github.com/acme/infra.git/': "
        f"403"
    ).encode()

    monkeypatch.setattr(
        asyncio,
        "create_subprocess_exec",
        _exec_factory(
            clone_proc=_FakeProc(returncode=128, stderr=stderr_with_token)
        ),
    )
    _stub_db_update_to_noop(monkeypatch)

    forced_tmp = tmp_path / "scan-redact"
    monkeypatch.setattr(
        sr_mod, "_make_tmp_root", lambda: forced_tmp, raising=False
    )

    with pytest.raises(RuntimeError) as exc_info:
        await sr_mod.scan_repo.original_func(
            scan_id="sc_redact",
            installation_id=1,
            repo="acme/infra",
            branch="main",
            sha="f" * 40,
            path=".",
            team_id="00000000-0000-0000-0000-000000000001",
        )
    msg = str(exc_info.value)
    assert token not in msg, f"token leaked into RuntimeError: {msg!r}"
    assert "***" in msg, f"token redaction marker missing: {msg!r}"


async def test_token_never_in_log_bind(
    monkeypatch: pytest.MonkeyPatch,
    _stub_mint_token: str,
    tmp_path: Path,
) -> None:
    """JOB-SR-09: under the happy log path the structlog bind() call does
    NOT receive any kwarg whose value contains the bare token.
    """
    import app.queue.tasks.scan_repo as sr_mod

    token = _stub_mint_token

    bound_values: list[Any] = []

    class _RecordingLogger:
        def bind(self, **kwargs: Any) -> _RecordingLogger:
            bound_values.extend(kwargs.values())
            return self

        def info(self, *_args: Any, **kwargs: Any) -> None:
            bound_values.extend(kwargs.values())

        def error(self, *_args: Any, **kwargs: Any) -> None:
            bound_values.extend(kwargs.values())

        def warning(self, *_args: Any, **kwargs: Any) -> None:
            bound_values.extend(kwargs.values())

    monkeypatch.setattr(sr_mod, "_log", _RecordingLogger())

    monkeypatch.setattr(
        asyncio, "create_subprocess_exec", _exec_factory()
    )
    _stub_db_update_to_noop(monkeypatch)

    forced_tmp = tmp_path / "scan-never-token"
    monkeypatch.setattr(
        sr_mod, "_make_tmp_root", lambda: forced_tmp, raising=False
    )

    with pytest.raises(ValueError):
        await sr_mod.scan_repo.original_func(
            scan_id="sc_never_token",
            installation_id=1,
            repo="acme/infra",
            branch="main",
            sha="f" * 40,
            path="../escape",
            team_id="00000000-0000-0000-0000-000000000001",
        )

    for v in bound_values:
        assert token not in str(v), (
            f"token leaked into log binding value: {v!r}"
        )


async def test_tmpdir_cleanup_on_exception(
    monkeypatch: pytest.MonkeyPatch,
    _stub_mint_token: str,
    tmp_path: Path,
) -> None:
    """JOB-SR-07: any internal exception leaves tmp_root removed (the
    finally block runs ``shutil.rmtree(ignore_errors=True)``).
    """
    import app.queue.tasks.scan_repo as sr_mod

    async def _explode(*_argv, **_kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("synthetic clone explosion")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _explode)
    _stub_db_update_to_noop(monkeypatch)

    forced_tmp = tmp_path / "scan-cleanup"
    monkeypatch.setattr(
        sr_mod, "_make_tmp_root", lambda: forced_tmp, raising=False
    )

    with pytest.raises(RuntimeError, match="synthetic clone"):
        await sr_mod.scan_repo.original_func(
            scan_id="sc_cleanup",
            installation_id=1,
            repo="acme/infra",
            branch="main",
            sha="f" * 40,
            path=".",
            team_id="00000000-0000-0000-0000-000000000001",
        )

    assert not forced_tmp.exists(), "finally must rmtree the tmp_root"


async def test_scan_rc2_failure(
    monkeypatch: pytest.MonkeyPatch,
    _stub_mint_token: str,
    tmp_path: Path,
) -> None:
    """JOB-SR-11: ``infracanvas scan`` exits rc=2 → RuntimeError "scan
    failed (rc=2)"; failure-path UPDATE attempted; tmp_root removed.
    """
    import app.queue.tasks.scan_repo as sr_mod

    monkeypatch.setattr(
        asyncio,
        "create_subprocess_exec",
        _exec_factory(
            scan_proc=_FakeProc(returncode=2, stderr=b"hcl parse error: x")
        ),
    )
    _stub_db_update_to_noop(monkeypatch)

    forced_tmp = tmp_path / "scan-rc2"
    monkeypatch.setattr(
        sr_mod, "_make_tmp_root", lambda: forced_tmp, raising=False
    )

    with pytest.raises(RuntimeError, match=r"scan failed \(rc=2\)"):
        await sr_mod.scan_repo.original_func(
            scan_id="sc_rc2",
            installation_id=1,
            repo="acme/infra",
            branch="main",
            sha="f" * 40,
            path=".",
            team_id="00000000-0000-0000-0000-000000000001",
        )
    assert not forced_tmp.exists()


# ---------------------------------------------------------------------------
# JOB-SR-01, JOB-SR-10, JOB-SR-12 — DB-touching happy / rc1 / race tests.
# Carry the rls marker; the testcontainer is required.
# ---------------------------------------------------------------------------


@pytest.mark.rls
async def test_happy_path(
    monkeypatch: pytest.MonkeyPatch,
    seed_session: Any,
    _wire_db_to_pg: None,
    _wire_r2_to_moto: None,
    _stub_mint_token: str,
    stub_stripe_meter: dict[str, Any],
    tmp_path: Path,
    mock_r2: Any,
) -> None:
    """JOB-SR-01: full pipeline — clone, scan, put_bytes, finalize_scan
    (DB UPDATE pending then ready + Stripe meter event).
    """
    from sqlalchemy import text

    import app.queue.tasks.scan_repo as sr_mod
    from app.db.models import Scan, ScanStatus, Team
    from app.util.ids import new_uuid7

    team = Team(
        id=new_uuid7(),
        clerk_org_id=f"org_sr_{secrets.token_hex(6)}",
        name="ScanRepoHappy",
        stripe_customer_id="cus_sr_happy",
    )
    scan = Scan(
        id=new_uuid7(),
        team_id=team.id,
        r2_key="",
        size_bytes=0,
        status=ScanStatus.pending,
        source="github",
        source_path=".",
        github_installation_id=99887766,
        github_repo="acme/infra",
        github_branch="main",
        github_sha="f" * 40,
    )
    async with seed_session.begin():
        seed_session.add(team)
        await seed_session.flush()
        seed_session.add(scan)

    forced_tmp = tmp_path / "scan-happy"
    monkeypatch.setattr(
        sr_mod, "_make_tmp_root", lambda: forced_tmp, raising=False
    )
    scan_payload = {
        "summary": {"total_resources": 1, "score": 80},
        "nodes": [],
    }
    monkeypatch.setattr(
        asyncio,
        "create_subprocess_exec",
        _exec_factory(
            scan_proc=_FakeProc(returncode=0),
            write_scan_json_at=forced_tmp / "scan.json",
            scan_payload=scan_payload,
        ),
    )

    await sr_mod.scan_repo.original_func(
        scan_id=str(scan.id),
        installation_id=99887766,
        repo="acme/infra",
        branch="main",
        sha="f" * 40,
        path=".",
        team_id=str(team.id),
    )

    refreshed = (
        await seed_session.execute(
            text("SELECT status, r2_key, sha256 FROM scans WHERE id = :id"),
            {"id": str(scan.id)},
        )
    ).one()
    assert refreshed.status == "ready"
    assert refreshed.r2_key == f"teams/{team.id}/scans/{scan.id}.json"
    assert len(stub_stripe_meter["calls"]) == 1
    assert not forced_tmp.exists()


@pytest.mark.rls
async def test_scan_rc1_treated_as_success(
    monkeypatch: pytest.MonkeyPatch,
    seed_session: Any,
    _wire_db_to_pg: None,
    _wire_r2_to_moto: None,
    _stub_mint_token: str,
    stub_stripe_meter: dict[str, Any],
    tmp_path: Path,
    mock_r2: Any,
) -> None:
    """JOB-SR-10: scan rc=1 (findings present) is success — finalize_scan
    is still called, row flips to ready, meter fires.
    """
    from sqlalchemy import text

    import app.queue.tasks.scan_repo as sr_mod
    from app.db.models import Scan, ScanStatus, Team
    from app.util.ids import new_uuid7

    team = Team(
        id=new_uuid7(),
        clerk_org_id=f"org_sr_{secrets.token_hex(6)}",
        name="ScanRepoRc1",
        stripe_customer_id="cus_rc1",
    )
    scan = Scan(
        id=new_uuid7(), team_id=team.id, r2_key="", size_bytes=0,
        status=ScanStatus.pending, source="github", source_path=".",
        github_installation_id=1, github_repo="acme/infra",
        github_branch="main", github_sha="f" * 40,
    )
    async with seed_session.begin():
        seed_session.add(team)
        await seed_session.flush()
        seed_session.add(scan)

    forced_tmp = tmp_path / "scan-rc1"
    monkeypatch.setattr(
        sr_mod, "_make_tmp_root", lambda: forced_tmp, raising=False
    )
    monkeypatch.setattr(
        asyncio,
        "create_subprocess_exec",
        _exec_factory(
            scan_proc=_FakeProc(returncode=1),
            write_scan_json_at=forced_tmp / "scan.json",
            scan_payload={"summary": {"findings": "present"}, "nodes": []},
        ),
    )

    await sr_mod.scan_repo.original_func(
        scan_id=str(scan.id),
        installation_id=1,
        repo="acme/infra",
        branch="main",
        sha="f" * 40,
        path=".",
        team_id=str(team.id),
    )

    refreshed = (
        await seed_session.execute(
            text("SELECT status FROM scans WHERE id = :id"),
            {"id": str(scan.id)},
        )
    ).one()
    assert refreshed.status == "ready"
    assert len(stub_stripe_meter["calls"]) == 1


@pytest.mark.rls
async def test_failed_update_uses_pending_guard(
    monkeypatch: pytest.MonkeyPatch,
    seed_session: Any,
    _wire_db_to_pg: None,
    _stub_mint_token: str,
    tmp_path: Path,
) -> None:
    """JOB-SR-12: pre-seed a row in 'ready' state; force scan_repo to fail.
    The failure-path UPDATE has WHERE status='pending', so a no-op — the
    'ready' row is NOT clobbered to 'failed'.
    """
    from sqlalchemy import text

    import app.queue.tasks.scan_repo as sr_mod
    from app.db.models import Scan, ScanStatus, Team
    from app.util.ids import new_uuid7

    team = Team(
        id=new_uuid7(),
        clerk_org_id=f"org_sr_{secrets.token_hex(6)}",
        name="ScanRepoGuard",
        stripe_customer_id="cus_guard",
    )
    scan = Scan(
        id=new_uuid7(), team_id=team.id,
        r2_key=f"teams/{team.id}/scans/already_ready.json", size_bytes=10,
        status=ScanStatus.ready, source="github", source_path=".",
        github_installation_id=1, github_repo="acme/infra",
        github_branch="main", github_sha="f" * 40,
    )
    async with seed_session.begin():
        seed_session.add(team)
        await seed_session.flush()
        seed_session.add(scan)

    forced_tmp = tmp_path / "scan-guard"
    monkeypatch.setattr(
        sr_mod, "_make_tmp_root", lambda: forced_tmp, raising=False
    )
    monkeypatch.setattr(
        asyncio, "create_subprocess_exec", _exec_factory()
    )

    with pytest.raises(ValueError, match="path traversal"):
        await sr_mod.scan_repo.original_func(
            scan_id=str(scan.id),
            installation_id=1,
            repo="acme/infra",
            branch="main",
            sha="f" * 40,
            path="../etc",
            team_id=str(team.id),
        )

    refreshed = (
        await seed_session.execute(
            text("SELECT status FROM scans WHERE id = :id"),
            {"id": str(scan.id)},
        )
    ).one()
    assert refreshed.status == "ready", (
        "WHERE status='pending' guard must not flip a ready row to failed"
    )


# ---------------------------------------------------------------------------
# JOB-SR-14..18 — Slack alert fire conditions (Plan 08-03).
#
# These tests mock the full pipeline up to finalize_scan so the Slack block
# executes.  They do NOT need the Postgres testcontainer — all DB access is
# intercepted via _stub_full_pipeline_for_slack() below.
# ---------------------------------------------------------------------------


def _stub_full_pipeline_for_slack(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    source: str,
    slack_webhook_url: str | None,
    critical: int,
    scan_json: dict[str, Any] | None = None,
) -> None:
    """Wire all the mocks needed so scan_repo completes the happy path and
    reaches the Slack fire block.

    Stubs applied:
    - mint_installation_token → deterministic fake token
    - asyncio.create_subprocess_exec → fake clone + fake scan + writes scan.json
    - put_bytes → no-op
    - finalize_scan → no-op
    - get_sessionmaker → controlled so the first call (team SELECT in section 8)
      returns stripe_customer_id and the second call (Slack SELECT in section 9)
      returns source + slack_webhook_url.
    """
    import app.queue.tasks.scan_repo as sr_mod

    # Stub token mint.
    async def _fake_mint(installation_id: int) -> str:
        return "ghs_fake_test_token"

    monkeypatch.setattr(sr_mod, "mint_installation_token", _fake_mint)

    # Force a deterministic tmp_root so we control the scan.json path.
    forced_tmp = tmp_path / "scan-slack"
    monkeypatch.setattr(sr_mod, "_make_tmp_root", lambda: forced_tmp, raising=False)

    # Build scan payload with the requested critical count.
    payload = scan_json or {
        "summary": {
            "total_resources": 2,
            "score": 50,
            "findings": {"critical": critical, "high": 0, "medium": 0, "info": 0},
        },
        "nodes": [],
    }

    monkeypatch.setattr(
        asyncio,
        "create_subprocess_exec",
        _exec_factory(
            scan_proc=_FakeProc(returncode=0),
            write_scan_json_at=forced_tmp / "scan.json",
            scan_payload=payload,
        ),
    )

    # Stub R2 put_bytes to a no-op.
    async def _fake_put_bytes(key: str, body: bytes, content_type: str = "") -> None:
        pass

    monkeypatch.setattr(sr_mod, "put_bytes", _fake_put_bytes)

    # Stub finalize_scan to a no-op coroutine.
    async def _fake_finalize(session: Any, **kwargs: Any) -> None:  # type: ignore[no-untyped-def]
        pass

    monkeypatch.setattr(sr_mod, "finalize_scan", _fake_finalize)

    # Build session mock that dispatches by SQL text content.
    # Section 8 executes: set_config, then SELECT stripe_customer_id FROM teams
    # Section 9 (Slack) executes: SELECT s.source, t.slack_webhook_url FROM scans
    #
    # We detect which query is being made by inspecting the SQL string fragment
    # rather than relying on call ordering — more robust to future reordering.

    class _FakeRow0:
        """Team row returned for the stripe_customer_id SELECT (section 8)."""
        stripe_customer_id = "cus_test"

    # Use a dynamic type so closure vars are captured without the class-body
    # scoping restriction (class body can't reference outer locals by name).
    _slack_source = source
    _slack_url = slack_webhook_url
    _FakeRow1 = type(
        "_FakeRow1",
        (),
        {"source": _slack_source, "slack_webhook_url": _slack_url},
    )

    class _NoopResult:
        """For set_config and other side-effect-only calls."""
        def one_or_none(self) -> None:
            return None

    class _FakeTeamResult:
        def one_or_none(self) -> _FakeRow0:
            return _FakeRow0()

    class _FakeSlackResult:
        def one_or_none(self) -> Any:  # type: ignore[no-untyped-def]
            return _FakeRow1()

    class _FakeSession:
        async def __aenter__(self):  # type: ignore[no-untyped-def]
            return self

        async def __aexit__(self, *exc):  # type: ignore[no-untyped-def]
            return False

        def begin(self):  # type: ignore[no-untyped-def]
            class _Tx:
                async def __aenter__(self_inner):  # type: ignore[no-untyped-def]  # noqa: N805
                    return self_inner

                async def __aexit__(self_inner, *exc):  # type: ignore[no-untyped-def]  # noqa: N805
                    return False

            return _Tx()

        async def execute(self, stmt: Any, *_args: Any, **_kwargs: Any) -> Any:
            stmt_str = str(stmt)
            if "set_config" in stmt_str:
                return _NoopResult()
            if "stripe_customer_id" in stmt_str:
                return _FakeTeamResult()
            if "slack_webhook_url" in stmt_str:
                return _FakeSlackResult()
            return _NoopResult()

    class _FakeMaker:
        def __call__(self) -> _FakeSession:
            return _FakeSession()

    monkeypatch.setattr(sr_mod, "get_sessionmaker", lambda: _FakeMaker())


async def test_slack_fires_on_webhook_source_with_critical(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """JOB-SR-14: source='webhook', slack_webhook_url set, critical=2 →
    httpx.AsyncClient.post called once with the Slack URL and a JSON body
    containing 'Critical' and the repo name.
    """
    import unittest.mock as mock

    import httpx

    import app.queue.tasks.scan_repo as sr_mod

    slack_url = "https://hooks.slack.com/services/T/B/x"
    _stub_full_pipeline_for_slack(
        monkeypatch,
        tmp_path,
        source="webhook",
        slack_webhook_url=slack_url,
        critical=2,
    )

    post_calls: list[dict[str, Any]] = []

    async def _fake_http_post(url: str, *, json: Any = None, timeout: float = 5.0) -> Any:
        post_calls.append({"url": url, "json": json})

        class _Resp:
            status_code = 200

        return _Resp()

    mock_client = mock.AsyncMock()
    mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = mock.AsyncMock(return_value=False)
    mock_client.post = _fake_http_post

    with mock.patch("httpx.AsyncClient", return_value=mock_client):
        await sr_mod.scan_repo.original_func(
            scan_id="sc_slack_fire",
            installation_id=42,
            repo="acme/infra",
            branch="main",
            sha="a" * 40,
            path=".",
            team_id="00000000-0000-0000-0000-000000000001",
        )

    assert len(post_calls) == 1, f"Expected 1 Slack POST, got {len(post_calls)}"
    assert post_calls[0]["url"] == slack_url
    body = post_calls[0]["json"]
    assert body is not None
    body_str = str(body)
    assert "Critical" in body_str, f"'Critical' not in Slack body: {body_str!r}"
    assert "acme/infra" in body_str, f"repo name not in Slack body: {body_str!r}"


async def test_slack_no_fire_on_github_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """JOB-SR-15: source='github' (not 'webhook'), slack_webhook_url set,
    critical=3 → httpx.AsyncClient.post NOT called.
    """
    import unittest.mock as mock

    import app.queue.tasks.scan_repo as sr_mod

    _stub_full_pipeline_for_slack(
        monkeypatch,
        tmp_path,
        source="github",
        slack_webhook_url="https://hooks.slack.com/services/T/B/x",
        critical=3,
    )

    post_calls: list[Any] = []

    async def _fake_http_post(url: str, **kwargs: Any) -> Any:
        post_calls.append(url)

        class _Resp:
            status_code = 200

        return _Resp()

    mock_client = mock.AsyncMock()
    mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = mock.AsyncMock(return_value=False)
    mock_client.post = _fake_http_post

    with mock.patch("httpx.AsyncClient", return_value=mock_client):
        await sr_mod.scan_repo.original_func(
            scan_id="sc_no_slack_github",
            installation_id=42,
            repo="acme/infra",
            branch="main",
            sha="b" * 40,
            path=".",
            team_id="00000000-0000-0000-0000-000000000001",
        )

    # Gate: scan_repo module must import httpx for the Slack block to work.
    assert hasattr(sr_mod, "httpx"), (
        "scan_repo must import httpx at module level for the Slack block"
    )
    assert len(post_calls) == 0, f"Expected 0 Slack POSTs for source='github', got {len(post_calls)}"


async def test_slack_no_fire_on_zero_critical(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """JOB-SR-16: source='webhook', slack_webhook_url set, critical=0 →
    httpx.AsyncClient.post NOT called (no critical findings, no alert).
    """
    import unittest.mock as mock

    import app.queue.tasks.scan_repo as sr_mod

    _stub_full_pipeline_for_slack(
        monkeypatch,
        tmp_path,
        source="webhook",
        slack_webhook_url="https://hooks.slack.com/services/T/B/x",
        critical=0,
    )

    post_calls: list[Any] = []

    async def _fake_http_post(url: str, **kwargs: Any) -> Any:
        post_calls.append(url)

        class _Resp:
            status_code = 200

        return _Resp()

    mock_client = mock.AsyncMock()
    mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = mock.AsyncMock(return_value=False)
    mock_client.post = _fake_http_post

    with mock.patch("httpx.AsyncClient", return_value=mock_client):
        await sr_mod.scan_repo.original_func(
            scan_id="sc_no_slack_zero_crit",
            installation_id=42,
            repo="acme/infra",
            branch="main",
            sha="c" * 40,
            path=".",
            team_id="00000000-0000-0000-0000-000000000001",
        )

    # Gate: scan_repo module must import httpx for the Slack block to work.
    assert hasattr(sr_mod, "httpx"), (
        "scan_repo must import httpx at module level for the Slack block"
    )
    assert len(post_calls) == 0, f"Expected 0 Slack POSTs for critical=0, got {len(post_calls)}"


async def test_slack_no_fire_when_url_none(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """JOB-SR-17: source='webhook', slack_webhook_url=None, critical=5 →
    httpx.AsyncClient.post NOT called (no Slack URL configured).
    """
    import unittest.mock as mock

    import app.queue.tasks.scan_repo as sr_mod

    _stub_full_pipeline_for_slack(
        monkeypatch,
        tmp_path,
        source="webhook",
        slack_webhook_url=None,
        critical=5,
    )

    post_calls: list[Any] = []

    async def _fake_http_post(url: str, **kwargs: Any) -> Any:
        post_calls.append(url)

        class _Resp:
            status_code = 200

        return _Resp()

    mock_client = mock.AsyncMock()
    mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = mock.AsyncMock(return_value=False)
    mock_client.post = _fake_http_post

    with mock.patch("httpx.AsyncClient", return_value=mock_client):
        await sr_mod.scan_repo.original_func(
            scan_id="sc_no_slack_url_none",
            installation_id=42,
            repo="acme/infra",
            branch="main",
            sha="d" * 40,
            path=".",
            team_id="00000000-0000-0000-0000-000000000001",
        )

    # Gate: scan_repo module must import httpx for the Slack block to work.
    assert hasattr(sr_mod, "httpx"), (
        "scan_repo must import httpx at module level for the Slack block"
    )
    assert len(post_calls) == 0, f"Expected 0 Slack POSTs when URL is None, got {len(post_calls)}"


async def test_slack_httpx_failure_logged_not_raised(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """JOB-SR-18: source='webhook', slack_webhook_url set, critical=1 →
    httpx.AsyncClient.post raises httpx.ConnectError → no exception propagates
    from scan_repo, and sentry_sdk.capture_exception is called.
    """
    import unittest.mock as mock

    import httpx

    import app.queue.tasks.scan_repo as sr_mod

    _stub_full_pipeline_for_slack(
        monkeypatch,
        tmp_path,
        source="webhook",
        slack_webhook_url="https://hooks.slack.com/services/T/B/x",
        critical=1,
    )

    captured: list[Any] = []

    def _fake_capture(exc: Any) -> None:
        captured.append(exc)

    monkeypatch.setattr(sr_mod.sentry_sdk, "capture_exception", _fake_capture)

    async def _exploding_post(url: str, **kwargs: Any) -> Any:
        raise httpx.ConnectError("timeout")

    mock_client = mock.AsyncMock()
    mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = mock.AsyncMock(return_value=False)
    mock_client.post = _exploding_post

    with mock.patch("httpx.AsyncClient", return_value=mock_client):
        # Must NOT raise — the Slack block swallows the error.
        await sr_mod.scan_repo.original_func(
            scan_id="sc_slack_httpx_fail",
            installation_id=42,
            repo="acme/infra",
            branch="main",
            sha="e" * 40,
            path=".",
            team_id="00000000-0000-0000-0000-000000000001",
        )

    assert len(captured) == 1, (
        f"Expected sentry_sdk.capture_exception called once, got {len(captured)}"
    )
    assert isinstance(captured[0], httpx.ConnectError), (
        f"Expected httpx.ConnectError to be captured, got {type(captured[0])}"
    )
