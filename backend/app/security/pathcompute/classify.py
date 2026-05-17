"""Root-cause classifier (ASY-02 D-08/D-09).

Each cause computes its own 0–1 confidence. Highest >= threshold wins.
On tie, fixed precedence NAT_ASYMMETRY > ROUTE_LEAK > BGP_LOCAL_PREF
(most specific first). On no cause >= threshold, emit UNKNOWN.
All non-winning scores live in ``evidence['scores']`` for the
diagnostic detail panel.

Threshold is operator-tunable via the ``CAUSE_THRESHOLD`` env var
(default 0.4 per D-09).

Public functions:
    score_nat(forward, ret, nat_rules) -> float
    score_leak(forward_routes, ret_routes) -> float
    score_local_pref(forward_routes, ret_routes) -> float
    classify(forward, ret, forward_routes, ret_routes, nat_rules) -> tuple[str, float, dict]
"""
from __future__ import annotations

import os
import sys
from typing import Any

import structlog
from infracanvas.graph.models import NetworkPath

_log = structlog.get_logger("app.security.pathcompute.classify")
_CAUSE_THRESHOLD = float(os.environ.get("CAUSE_THRESHOLD", "0.4"))

# Precedence dict: lower number = higher precedence on tied scores
# (D-08 NAT_ASYMMETRY > ROUTE_LEAK > BGP_LOCAL_PREF)
_PRECEDENCE = {"NAT_ASYMMETRY": 0, "ROUTE_LEAK": 1, "BGP_LOCAL_PREF": 2}


def score_nat(
    forward: NetworkPath,
    ret: NetworkPath,
    nat_rules: list[Any],
) -> float:
    """NAT_ASYMMETRY: forward transits NAT whose return-side pinhole is absent.

    Signals (each adds 0.5, capped at 1.0):
        - For each forward egress interface that matches a NAT rule's
          interface_in, no reverse NAT rule exists routing
          (NAT.interface_out → return-path interface_in).
    """
    score = 0.0
    fwd_egress = {h.interface_out for h in forward.hops if h.interface_out}
    ret_ingress = {h.interface_in for h in ret.hops if h.interface_in}
    for egress in fwd_egress:
        forward_nat = [
            n for n in nat_rules if _attr(n, "interface_in") == egress
        ]
        if not forward_nat:
            continue
        for fn in forward_nat:
            reverse_exists = any(
                _attr(n, "interface_in") == _attr(fn, "interface_out")
                and _attr(n, "interface_out") in ret_ingress
                for n in nat_rules
            )
            if not reverse_exists:
                score += 0.5
    return min(score, 1.0)


def score_leak(forward_routes: list[Any], ret_routes: list[Any]) -> float:
    """ROUTE_LEAK: more-specific prefix on one leg only, or unexpected AS
    in return.

    Signals:
        - More-specific prefix appears on exactly one of the two route lists
          (+ 0.3 scaled by count).
        - Return leg has an as_path containing an AS not in forward leg
          (+ 0.4).
    """
    score = 0.0
    fwd_prefixes = {_attr(r, "prefix") for r in forward_routes}
    ret_prefixes = {_attr(r, "prefix") for r in ret_routes}
    only_one_side = fwd_prefixes ^ ret_prefixes
    if only_one_side:
        score += 0.3 * min(len(only_one_side) / 5.0, 1.0)
    fwd_ases = {
        a for r in forward_routes for a in (_attr(r, "as_path") or "").split()
    }
    ret_ases = {a for r in ret_routes for a in (_attr(r, "as_path") or "").split()}
    if ret_ases - fwd_ases:
        score += 0.4
    return min(score, 1.0)


def score_local_pref(forward_routes: list[Any], ret_routes: list[Any]) -> float:
    """BGP_LOCAL_PREF: as_path or metric divergence between legs.

    Phase 10 RouteRecord does NOT carry LOCAL_PREF; classifier falls back
    to as_path-divergence + metric-divergence signals (Q4 — LOCAL_PREF
    field deferred to v1.2).

    Signals:
        - as_path sets differ between legs (+ 0.3).
        - metric sets differ between legs (+ 0.2).
    """
    score = 0.0
    fwd_paths = {_attr(r, "as_path") for r in forward_routes}
    ret_paths = {_attr(r, "as_path") for r in ret_routes}
    if fwd_paths != ret_paths:
        score += 0.3
    fwd_metrics = {_attr(r, "metric") for r in forward_routes}
    ret_metrics = {_attr(r, "metric") for r in ret_routes}
    if fwd_metrics != ret_metrics:
        score += 0.2
    return min(score, 1.0)


def classify(
    forward: NetworkPath | None,
    ret: NetworkPath | None,
    forward_routes: list[Any],
    ret_routes: list[Any],
    nat_rules: list[Any],
) -> tuple[str, float, dict[str, Any]]:
    """D-08/D-09 evidence-scored classifier with deterministic tiebreaker.

    Returns:
        ``(cause, confidence, evidence)`` where ``evidence['scores']`` dumps
        all 3 raw scores for the diagnostic panel. When no score clears
        ``CAUSE_THRESHOLD`` (env-tunable, default 0.4), returns
        ``("UNKNOWN", 0.0, evidence)``. On tied highest scores, the
        precedence dict (NAT > LEAK > LOCAL_PREF) breaks the tie.
    """
    # Resolve score functions via the module so monkeypatch.setattr works
    # in tests (rebinding the module attribute, not just the local import).
    mod = sys.modules[__name__]
    scores = {
        "NAT_ASYMMETRY": float(mod.score_nat(forward, ret, nat_rules)),
        "ROUTE_LEAK": float(mod.score_leak(forward_routes, ret_routes)),
        "BGP_LOCAL_PREF": float(mod.score_local_pref(forward_routes, ret_routes)),
    }
    evidence: dict[str, Any] = {"scores": scores}
    candidates = {k: v for k, v in scores.items() if v >= _CAUSE_THRESHOLD}
    if not candidates:
        return ("UNKNOWN", 0.0, evidence)
    # Sort: highest score first; ties broken by precedence (lowest enum value wins)
    winner = sorted(
        candidates.items(),
        key=lambda kv: (-kv[1], _PRECEDENCE[kv[0]]),
    )[0]
    return (winner[0], float(winner[1]), evidence)


def _attr(obj: Any, name: str) -> Any:
    """Read ``name`` from ``obj`` whether attribute (object) or key (dict)."""
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)
