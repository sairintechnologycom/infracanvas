"""Phase 12 ASY-02 D-08 — evidence-scored classifier tests.

GREEN after Plan 12-05 lands ``app.security.pathcompute.classify``.

Asserts the deterministic NAT > LEAK > LOCAL_PREF tiebreaker (D-08) and
the UNKNOWN fallback when no score clears the 0.4 evidence threshold (D-09).
"""
from __future__ import annotations

import pytest

from app.security.pathcompute.classify import classify


def test_nat_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    """ASY-02 D-08: NAT_ASYMMETRY score 0.7 > LEAK 0.5 > LOCAL_PREF 0.0 → NAT wins."""
    monkeypatch.setattr("app.security.pathcompute.classify.score_nat", lambda *a, **k: 0.7)
    monkeypatch.setattr("app.security.pathcompute.classify.score_leak", lambda *a, **k: 0.5)
    monkeypatch.setattr("app.security.pathcompute.classify.score_local_pref", lambda *a, **k: 0.0)
    cause, conf, evidence = classify(None, None, [], [], [])
    assert cause == "NAT_ASYMMETRY"
    assert conf == pytest.approx(0.7)
    assert evidence["scores"]["ROUTE_LEAK"] == pytest.approx(0.5)
    assert evidence["scores"]["BGP_LOCAL_PREF"] == pytest.approx(0.0)


def test_unknown_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """ASY-02 D-09: all scores < 0.4 threshold → UNKNOWN + full scores dump."""
    monkeypatch.setattr("app.security.pathcompute.classify.score_nat", lambda *a, **k: 0.3)
    monkeypatch.setattr("app.security.pathcompute.classify.score_leak", lambda *a, **k: 0.3)
    monkeypatch.setattr("app.security.pathcompute.classify.score_local_pref", lambda *a, **k: 0.3)
    cause, conf, evidence = classify(None, None, [], [], [])
    assert cause == "UNKNOWN"
    assert conf == pytest.approx(0.0)
    assert "scores" in evidence
    assert set(evidence["scores"]) >= {"NAT_ASYMMETRY", "ROUTE_LEAK", "BGP_LOCAL_PREF"}


def test_tiebreaker(monkeypatch: pytest.MonkeyPatch) -> None:
    """ASY-02 D-08: tied scores → NAT > LEAK > LOCAL_PREF precedence."""
    monkeypatch.setattr("app.security.pathcompute.classify.score_nat", lambda *a, **k: 0.6)
    monkeypatch.setattr("app.security.pathcompute.classify.score_leak", lambda *a, **k: 0.6)
    monkeypatch.setattr("app.security.pathcompute.classify.score_local_pref", lambda *a, **k: 0.6)
    cause, conf, _evidence = classify(None, None, [], [], [])
    assert cause == "NAT_ASYMMETRY"  # NAT precedence wins on tie
    assert conf == pytest.approx(0.6)


def test_leak_beats_local_pref(monkeypatch: pytest.MonkeyPatch) -> None:
    """ASY-02 D-08: LEAK > LOCAL_PREF when NAT is below threshold."""
    monkeypatch.setattr("app.security.pathcompute.classify.score_nat", lambda *a, **k: 0.0)
    monkeypatch.setattr("app.security.pathcompute.classify.score_leak", lambda *a, **k: 0.5)
    monkeypatch.setattr("app.security.pathcompute.classify.score_local_pref", lambda *a, **k: 0.5)
    cause, _conf, _evidence = classify(None, None, [], [], [])
    assert cause == "ROUTE_LEAK"
