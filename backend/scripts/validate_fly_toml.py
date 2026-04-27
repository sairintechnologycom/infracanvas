"""Validate invariants across backend/fly.*.toml files.

Run:
    python -m scripts.validate_fly_toml fly.dev.toml fly.prod.toml

Exit 0 if all invariants hold, exit 1 otherwise.

Invariants asserted (sourced from 06-08-PLAN.md acceptance_criteria and
RESEARCH § F11 / § P4 / § P5):

  1. [processes] must include 'api'
  2. [processes] must include 'worker'
  3. [deploy].release_command must run `alembic ... upgrade head`
  4. [deploy].release_command_timeout >= 10 minutes
  5. [http_service].processes must be exactly ['api']  (worker NOT publicly exposed)
  6. [http_service].force_https must be true
  7. [http_service].min_machines_running must be >= 1
  8. A /healthz http_check must exist (under [[services.http_checks]] OR [[http_checks]])

This is the structural CI gate. It doesn't talk to Fly's API; flyctl config
validate (in the GHA workflow) does that — they're complementary.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Callable
from pathlib import Path

try:
    import tomllib
except ImportError:  # pragma: no cover  # py<3.11 fallback
    import tomli as tomllib  # type: ignore[no-redef]


def _has_process(doc: dict[str, object], name: str) -> bool:
    procs = doc.get("processes")
    return isinstance(procs, dict) and name in procs


def _release_command_runs_alembic(doc: dict[str, object]) -> bool:
    deploy = doc.get("deploy")
    if not isinstance(deploy, dict):
        return False
    cmd = deploy.get("release_command", "")
    if not isinstance(cmd, str):
        return False
    return "alembic" in cmd and "upgrade head" in cmd


def _release_command_timeout_ok(doc: dict[str, object]) -> bool:
    deploy = doc.get("deploy")
    if not isinstance(deploy, dict):
        return False
    raw = deploy.get("release_command_timeout", "")
    if not isinstance(raw, str):
        return False
    # Accept formats like "15m", "900s", "1h"
    m = re.fullmatch(r"\s*(\d+)\s*([smh])\s*", raw)
    if not m:
        return False
    value, unit = int(m.group(1)), m.group(2)
    seconds = {"s": value, "m": value * 60, "h": value * 3600}[unit]
    return seconds >= 10 * 60


def _http_service_processes_api_only(doc: dict[str, object]) -> bool:
    svc = doc.get("http_service")
    if not isinstance(svc, dict):
        return False
    return svc.get("processes") == ["api"]


def _http_service_force_https(doc: dict[str, object]) -> bool:
    svc = doc.get("http_service")
    return isinstance(svc, dict) and svc.get("force_https") is True


def _http_service_min_machines(doc: dict[str, object]) -> bool:
    svc = doc.get("http_service")
    if not isinstance(svc, dict):
        return False
    val = svc.get("min_machines_running")
    return isinstance(val, int) and val >= 1


def _has_healthz_check(doc: dict[str, object]) -> bool:
    """Tolerant check: TOML parses [[services.http_checks]] under a 'services'
    dict OR via the literal key 'services.http_checks' depending on context.
    Also accept a top-level [[http_checks]] / [[services.tcp_checks]] absent.
    """
    candidates: list[object] = []
    services = doc.get("services")
    if isinstance(services, dict):
        candidates.extend(services.get("http_checks", []) or [])
    candidates.extend(doc.get("services.http_checks", []) or [])  # type: ignore[arg-type]
    candidates.extend(doc.get("http_checks", []) or [])  # type: ignore[arg-type]
    return any(isinstance(c, dict) and c.get("path") == "/healthz" for c in candidates)


INVARIANTS: list[tuple[str, Callable[[dict[str, object]], bool]]] = [
    ("[processes] must include 'api'", lambda d: _has_process(d, "api")),
    ("[processes] must include 'worker'", lambda d: _has_process(d, "worker")),
    ("[deploy].release_command must run alembic upgrade head", _release_command_runs_alembic),
    ("[deploy].release_command_timeout must be >= 10m", _release_command_timeout_ok),
    (
        "[http_service].processes must be exactly ['api'] (worker not exposed)",
        _http_service_processes_api_only,
    ),
    ("[http_service].force_https must be true", _http_service_force_https),
    ("[http_service].min_machines_running must be >= 1", _http_service_min_machines),
    ("a /healthz http_check must exist", _has_healthz_check),
]


def validate(path: Path) -> list[str]:
    doc = tomllib.loads(path.read_text())
    failures: list[str] = []
    for desc, check in INVARIANTS:
        try:
            if not check(doc):
                failures.append(f"{path.name}: {desc}")
        except Exception as exc:
            failures.append(f"{path.name}: {desc} (raised {exc!r})")
    return failures


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: python -m scripts.validate_fly_toml <fly.toml> [<fly.toml> ...]")
        return 2
    failures: list[str] = []
    for arg in argv[1:]:
        path = Path(arg)
        if not path.exists():
            failures.append(f"{arg}: file does not exist")
            continue
        failures.extend(validate(path))
    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(f"OK: {len(argv) - 1} Fly config(s) validated")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
