"""Shared pytest fixtures for the backend test suite.

Exposes the session-scoped Postgres Testcontainer, dual-role async sessions
(``infracanvas_app`` RLS-active, ``infracanvas_test`` BYPASSRLS seed),
plus fixture-local mocks for Clerk (RSA keypair + JWKS), R2 (moto S3),
Stripe (respx meter-event capture), and the in-memory taskiq broker.

Also ports the per-module coverage gate (Phase 4 D-15) from
``cli/tests/conftest.py`` so every ``app/<module>`` prefix must independently
clear 80% line + branch coverage — bytewise copy of the hook, only
``PER_MODULE_GATES`` and ``source=["app"]`` changed.

Downstream plans consume these fixtures by name — do not rename.

Skip control:
    Set ``GSD_SKIP_TESTCONTAINERS=1`` to skip Postgres-dependent fixtures
    (Wave 0 smoke can pass before Alembic migrations exist).
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Per-module coverage gate (Phase 4 D-15, ported from cli/tests/conftest.py).
# Paths are relative to the installed ``app`` package (matches
# [tool.coverage.run] source).
# ---------------------------------------------------------------------------

PER_MODULE_GATES: dict[str, float] = {
    "app/auth":    80.0,
    "app/routes":  80.0,
    "app/db":      80.0,
    "app/queue":   80.0,
    "app/billing": 80.0,
    "app/storage": 80.0,
    "app/obs":     80.0,
}


def _module_percents(cov: Any) -> dict[str, tuple[float, float, int, int, int, int]]:
    """Return {module_prefix: (line_pct, branch_pct, lines_hit, lines_total,
    branches_hit, branches_total)} aggregated across every measured file
    whose path contains the prefix.

    Takes a coverage.Coverage instance (not a CoverageData) because
    analysis2() is defined on Coverage, which knows about the config
    (branch-enabled, file_reporter, etc.)."""
    cov_data = cov.get_data()
    agg: dict[str, list[int]] = {
        prefix: [0, 0, 0, 0]  # lines_hit, lines_total, branches_hit, branches_total
        for prefix in PER_MODULE_GATES
    }

    for filename in cov_data.measured_files():
        # Normalise to forward-slash for cross-platform matching.
        normalised = filename.replace("\\", "/")
        for prefix in PER_MODULE_GATES:
            if prefix not in normalised:
                continue
            try:
                analysis = cov.analysis2(filename)
            except Exception:  # noqa: BLE001 — skip files coverage cannot read
                continue
            # analysis2 returns (filename, executable, excluded, missing, missing_formatted)
            executable = set(analysis[1])
            missing = set(analysis[3])
            hit = len(executable - missing)
            total = len(executable)
            agg[prefix][0] += hit
            agg[prefix][1] += total

            # Branch data (optional — only present if branch=true).
            try:
                from coverage.results import analysis_from_file_reporter
                fr = cov._get_file_reporter(filename)
                an = analysis_from_file_reporter(cov_data, 2, fr, filename)
                n_branches = an.numbers.n_branches
                n_missing_branches = an.numbers.n_missing_branches
                hit_branches = max(n_branches - n_missing_branches, 0)
                agg[prefix][2] += hit_branches
                agg[prefix][3] += n_branches
            except Exception:  # noqa: BLE001 — coverage API variance is tolerated
                pass

    result: dict[str, tuple[float, float, int, int, int, int]] = {}
    for prefix, (lh, lt, bh, bt) in agg.items():
        line_pct = (lh / lt * 100.0) if lt else 100.0
        branch_pct = (bh / bt * 100.0) if bt else 100.0
        result[prefix] = (line_pct, branch_pct, lh, lt, bh, bt)
    return result


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """After the test session, enforce per-module >=80% line+branch gate."""
    # Only run when coverage was collected (pytest-cov active).
    try:
        import coverage
    except ImportError:
        return

    cov_file = Path(session.config.rootpath) / ".coverage"
    if not cov_file.exists():
        return

    cov = coverage.Coverage(data_file=str(cov_file))
    cov.load()

    failures: list[str] = []
    per_module = _module_percents(cov)
    for prefix, threshold in PER_MODULE_GATES.items():
        line_pct, branch_pct, lh, lt, bh, bt = per_module[prefix]
        if lt == 0:
            # No files measured for this prefix in the current run scope —
            # skip the gate (a scoped run like `pytest tests/test_scans.py`
            # should not fail for `app/obs` having 0 measured files).
            continue
        if line_pct < threshold:
            failures.append(
                f"PER-MODULE COVERAGE FAIL: {prefix} line={line_pct:.1f}% "
                f"({lh}/{lt}) < {threshold:.0f}%"
            )
        if bt > 0 and branch_pct < threshold:
            failures.append(
                f"PER-MODULE COVERAGE FAIL: {prefix} branch={branch_pct:.1f}% "
                f"({bh}/{bt}) < {threshold:.0f}%"
            )

    if failures:
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if reporter is not None:
            reporter.write_sep("!", "PER-MODULE COVERAGE GATE (D-15)", red=True)
            for msg in failures:
                reporter.write_line(msg, red=True)
        # Mark the session as failed (only if tests themselves didn't already fail)
        if exitstatus == 0:
            session.exitstatus = 1


# ---------------------------------------------------------------------------
# Postgres Testcontainer — session-scoped; provisions both
# infracanvas_app (NOBYPASSRLS) and infracanvas_test (BYPASSRLS) roles.
# Alembic is run ONLY if backend/alembic.ini exists (Plan 03+).
# ---------------------------------------------------------------------------

_SKIP_PG = os.environ.get("GSD_SKIP_TESTCONTAINERS") == "1"

BYPASS_ROLE_SQL = Path(__file__).parent / "fixtures" / "bypass_role.sql"

# Raw SQL to provision the RLS-active app role. Mirrors RESEARCH § F3
# lines 243-253 but omits the GRANT on specific tables (those are granted by
# subsequent migrations — this conftest only creates the ROLE + CONNECT/USAGE).
APP_ROLE_SQL = """
CREATE ROLE infracanvas_app WITH LOGIN PASSWORD 'app';
ALTER ROLE infracanvas_app NOBYPASSRLS;
GRANT CONNECT ON DATABASE test TO infracanvas_app;
GRANT USAGE ON SCHEMA public TO infracanvas_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO infracanvas_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO infracanvas_app;
"""


@pytest.fixture(scope="session")
def pg_container() -> Iterator[Any]:
    """Postgres 16 Testcontainer with both RLS roles provisioned.

    Runs ``alembic upgrade head`` via subprocess IF ``backend/alembic.ini``
    exists (guarded so this conftest works in Wave 0 before Plan 03 lands).
    """
    if _SKIP_PG:
        pytest.skip("Postgres Testcontainer disabled via GSD_SKIP_TESTCONTAINERS=1")

    from sqlalchemy import create_engine, text
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine") as pg:
        # Superuser URL (sync psycopg/psycopg2 for synchronous setup DDL).
        super_url = pg.get_connection_url()  # postgresql+psycopg2://test:test@host:port/test
        # Normalize to the SYNC driver url for one-shot DDL.
        sync_url = super_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
        engine = create_engine(sync_url, isolation_level="AUTOCOMMIT")

        with engine.connect() as conn:
            # Provision infracanvas_app (NOBYPASSRLS).
            conn.execute(text(APP_ROLE_SQL))
            # Provision infracanvas_test (BYPASSRLS) from the dedicated SQL file.
            bypass_sql = BYPASS_ROLE_SQL.read_text()
            conn.execute(text(bypass_sql))
        engine.dispose()

        # Optional: run Alembic head if migrations exist (Plan 03+).
        alembic_ini = Path(__file__).parents[1] / "alembic.ini"
        if alembic_ini.exists():
            env = os.environ.copy()
            env["DATABASE_URL_MIGRATOR"] = sync_url.replace(
                "postgresql+psycopg2", "postgresql+asyncpg"
            )
            subprocess.run(
                ["alembic", "-c", str(alembic_ini), "upgrade", "head"],
                check=True,
                env=env,
                cwd=str(alembic_ini.parent),
            )

        yield pg


def _async_url_for(pg: Any, user: str, password: str) -> str:
    """Build an ``postgresql+asyncpg://`` URL for the given role."""
    host = pg.get_container_host_ip()
    port = pg.get_exposed_port(5432)
    dbname = pg.dbname if hasattr(pg, "dbname") else "test"
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{dbname}"


async def with_team_ctx(session: Any, team_id: Any) -> None:
    """Helper: apply ``SET LOCAL app.current_team_id = :t`` inside the
    caller's open transaction (D-02 pattern). Callers must be inside a
    ``session.begin()`` block."""
    from sqlalchemy import text

    await session.execute(
        text("SET LOCAL app.current_team_id = :t"),
        {"t": str(team_id)},
    )


@pytest.fixture
async def seed_session(pg_container: Any) -> AsyncIterator[Any]:
    """Per-test AsyncSession connected as ``infracanvas_test`` (BYPASSRLS).

    Use for seeding cross-team rows without tripping RLS. Does NOT set the
    ``app.current_team_id`` GUC; BYPASSRLS ignores it.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(_async_url_for(pg_container, "infracanvas_test", "test"))
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def app_session(pg_container: Any) -> AsyncIterator[Any]:
    """Per-test AsyncSession connected as ``infracanvas_app`` (RLS active).

    Caller is responsible for opening a transaction (``async with
    session.begin():``) and calling :func:`with_team_ctx` to set the team
    GUC before issuing RLS-scoped queries.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(_async_url_for(pg_container, "infracanvas_app", "app"))
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        yield session
    await engine.dispose()


# ---------------------------------------------------------------------------
# Clerk mock — fixture-local RSA keypair + JWKS served by pytest-httpserver.
# Downstream tests use ``mock_clerk.sign_jwt(...)`` to mint valid tokens.
# ---------------------------------------------------------------------------

@dataclass
class ClerkFixture:
    """In-process Clerk mock: RSA keypair + JWKS URL + sign_jwt helper."""

    private_key_pem: bytes
    public_key_pem: bytes
    jwks_url: str
    jwks_json: dict[str, Any]
    kid: str = "test-key-1"

    def sign_jwt(
        self,
        sub: str,
        org_id: str,
        role: str = "admin",
        azp: str = "https://infracanvas.app",
        exp_delta: int = 3600,
    ) -> str:
        """Mint a Clerk v2 session token (see RESEARCH § F1 lines 111-126).

        Claims: azp, exp, iat, iss, sub, sid, v=2, o={id, rol}.
        """
        import jwt  # PyJWT

        now = int(time.time())
        claims: dict[str, Any] = {
            "azp": azp,
            "exp": now + exp_delta,
            "iat": now,
            "iss": "https://clerk.infracanvas.app",
            "sub": sub,
            "sid": f"sess_{sub}",
            "v": 2,
            "o": {"id": org_id, "rol": role},
        }
        token = jwt.encode(
            claims,
            self.private_key_pem,
            algorithm="RS256",
            headers={"kid": self.kid},
        )
        return token


@pytest.fixture
def mock_clerk(httpserver: Any) -> ClerkFixture:
    """Fixture-local Clerk mock with RSA keypair + fake JWKS endpoint.

    Uses ``pytest-httpserver`` to serve the JWKS at a real localhost URL
    so ``PyJWKClient`` can fetch it over HTTP.
    """
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    # Generate a fresh RSA keypair per test.
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # Build a minimal JWKS document referencing the public key.
    # PyJWT's PyJWKClient uses the 'n' + 'e' components for RS256 verification.
    public_numbers = public_key.public_numbers()
    import base64

    def _b64url_uint(v: int) -> str:
        byte_len = (v.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(v.to_bytes(byte_len, "big")).rstrip(b"=").decode("ascii")

    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "alg": "RS256",
                "use": "sig",
                "kid": "test-key-1",
                "n": _b64url_uint(public_numbers.n),
                "e": _b64url_uint(public_numbers.e),
            }
        ]
    }

    httpserver.expect_request("/.well-known/jwks.json").respond_with_json(jwks)
    jwks_url = httpserver.url_for("/.well-known/jwks.json")

    return ClerkFixture(
        private_key_pem=private_pem,
        public_key_pem=public_pem,
        jwks_url=jwks_url,
        jwks_json=jwks,
    )


# ---------------------------------------------------------------------------
# R2 / S3 mock via moto.
# ---------------------------------------------------------------------------

@dataclass
class S3MockFixture:
    """moto-backed S3 mock standing in for Cloudflare R2 in tests."""

    bucket: str
    endpoint_url: str | None
    access_key: str
    secret_key: str


@pytest.fixture
def mock_r2() -> Iterator[S3MockFixture]:
    """Provide a moto-backed S3 bucket ``infracanvas-scans-test``.

    R2 is S3-compatible; moto's ``mock_aws`` covers put_object, head_object,
    generate_presigned_url (RESEARCH § F14).
    """
    import boto3
    from moto import mock_aws

    prior_akid = os.environ.get("AWS_ACCESS_KEY_ID")
    prior_sak = os.environ.get("AWS_SECRET_ACCESS_KEY")
    prior_region = os.environ.get("AWS_DEFAULT_REGION")
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="infracanvas-scans-test")
        yield S3MockFixture(
            bucket="infracanvas-scans-test",
            endpoint_url=None,  # moto intercepts at botocore layer; no endpoint override needed
            access_key="testing",
            secret_key="testing",
        )

    # Restore prior env (respect unset case).
    for key, prior in (
        ("AWS_ACCESS_KEY_ID", prior_akid),
        ("AWS_SECRET_ACCESS_KEY", prior_sak),
        ("AWS_DEFAULT_REGION", prior_region),
    ):
        if prior is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = prior


# ---------------------------------------------------------------------------
# Stripe mock via respx — intercepts POSTs to the v2 meter-events endpoint.
# ---------------------------------------------------------------------------

@dataclass
class StripeMockFixture:
    """respx-backed Stripe meter-event capture."""

    captured_requests: list[dict[str, Any]] = field(default_factory=list)

    def assert_meter_event(self, event_name: str, identifier: str, value: str) -> None:
        """Assert a meter event with the given shape was POSTed."""
        for req in self.captured_requests:
            payload = req.get("payload") or {}
            if (
                payload.get("event_name") == event_name
                and payload.get("payload", {}).get("stripe_customer_id") == identifier
                and str(payload.get("payload", {}).get("value")) == str(value)
            ):
                return
        raise AssertionError(
            f"No Stripe meter event captured with event_name={event_name!r}, "
            f"identifier={identifier!r}, value={value!r}. "
            f"Captured: {self.captured_requests}"
        )


@pytest.fixture
def mock_stripe() -> Iterator[StripeMockFixture]:
    """Capture POSTs to Stripe's v2 meter-events endpoint (RESEARCH § F8).

    Returns a fixture whose ``captured_requests`` list is appended to on
    every intercepted POST. Default response: ``200`` with a synthetic id.
    """
    import respx

    fx = StripeMockFixture()
    ts = int(time.time())

    def _capture(request: Any) -> Any:
        # Parse form-encoded or JSON body.
        raw = request.content
        parsed: dict[str, Any]
        try:
            parsed = json.loads(raw.decode("utf-8")) if raw else {}
        except (ValueError, UnicodeDecodeError):
            # Stripe typically uses form-encoded; decode leniently.
            from urllib.parse import parse_qs

            parsed = {
                k: (v[0] if isinstance(v, list) and len(v) == 1 else v)
                for k, v in parse_qs(raw.decode("utf-8")).items()
            }
        fx.captured_requests.append(
            {
                "url": str(request.url),
                "headers": dict(request.headers),
                "payload": parsed,
            }
        )
        import httpx

        return httpx.Response(
            200,
            json={
                "id": f"me_test_{len(fx.captured_requests)}",
                "event_name": parsed.get("event_name", ""),
                "timestamp": ts,
            },
        )

    with respx.mock(base_url="https://api.stripe.com", assert_all_called=False) as router:
        router.post("/v2/billing/meter_events").mock(side_effect=_capture)
        yield fx


# ---------------------------------------------------------------------------
# taskiq in-memory broker — fires tasks synchronously in-process.
# ---------------------------------------------------------------------------

@pytest.fixture
async def in_memory_broker() -> AsyncIterator[Any]:
    """Return a ``taskiq.InMemoryBroker`` with ``is_worker_process=True``.

    Downstream task modules will override the production broker with this
    fixture so task bodies execute synchronously in tests.
    """
    from taskiq import InMemoryBroker

    broker = InMemoryBroker()
    broker.is_worker_process = True
    await broker.startup()
    try:
        yield broker
    finally:
        await broker.shutdown()
