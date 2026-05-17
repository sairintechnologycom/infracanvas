"""Phase 12 ASY-02 D-08 — evidence-scored classifier tests.

RED until Plan 12-05 lands ``app.security.pathcompute.classify``.

Asserts the deterministic NAT > LEAK > LOCAL_PREF tiebreaker (D-08) and
the UNKNOWN fallback when no score clears the 0.4 evidence threshold (D-09).
"""
from __future__ import annotations

import pytest

pytest.importorskip("app.security.pathcompute.classify")  # collection RED

from app.security.pathcompute.classify import (  # noqa: E402
    classify,
    score_leak,
    score_local_pref,
    score_nat,
)


def test_nat_wins() -> None:
    """ASY-02 D-08: NAT_ASYMMETRY score 0.7 > LEAK 0.5 > LOCAL_PREF 0.0 → NAT wins."""
    pytest.skip("Plan 12-05 to implement classify()")
    # cause, conf, evidence = classify(fwd, ret, snapshot)
    # # given fixtures: score_nat=0.7, score_leak=0.5, score_local_pref=0.0
    # assert cause == "NAT_ASYMMETRY"
    # assert conf == pytest.approx(0.7)
    # assert evidence["scores"]["ROUTE_LEAK"] == pytest.approx(0.5)
    # assert evidence["scores"]["BGP_LOCAL_PREF"] == pytest.approx(0.0)


def test_unknown_fallback() -> None:
    """ASY-02 D-09: all scores < 0.4 threshold → UNKNOWN + full scores dump."""
    pytest.skip("Plan 12-05 to implement UNKNOWN fallback (D-09)")
    # cause, conf, evidence = classify(fwd, ret, snapshot)
    # # given fixtures: all scores 0.3 < 0.4 threshold
    # assert cause == "UNKNOWN"
    # assert conf == pytest.approx(0.0)
    # assert "scores" in evidence
    # # all 3 non-winning causes still recorded for diagnostic detail
    # assert set(evidence["scores"]) >= {"NAT_ASYMMETRY", "ROUTE_LEAK", "BGP_LOCAL_PREF"}


def test_tiebreaker() -> None:
    """ASY-02 D-08: tied scores → NAT > LEAK > LOCAL_PREF precedence."""
    pytest.skip("Plan 12-05 to implement deterministic tiebreaker")
    # cause, conf, _evidence = classify(fwd, ret, snapshot)
    # # given fixtures: score_nat=score_leak=score_local_pref=0.6
    # assert cause == "NAT_ASYMMETRY"  # NAT precedence wins on tie
    # assert conf == pytest.approx(0.6)
