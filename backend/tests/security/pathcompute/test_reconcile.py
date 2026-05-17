"""Phase 12 D-16 — finding reconciliation tests (first_seen / last_seen / resolved_at).

RED until Plan 12-05 lands the recompute reconciliation logic.
"""
from __future__ import annotations

import pytest

pytest.importorskip("app.security.pathcompute.reconcile")  # collection RED

from app.security.pathcompute.reconcile import reconcile_findings  # noqa: E402


def test_still_present_updates_last_seen_at() -> None:
    """D-16: finding present in two consecutive recomputes →
    row at t2 has first_seen_at==t1, last_seen_at==t2, resolved_at is NULL."""
    pytest.skip("Plan 12-05 to implement reconcile_findings")
    # row_t1 = reconcile_findings([finding], at=t1)[0]
    # row_t2 = reconcile_findings([finding], at=t2)[0]
    # assert row_t2.first_seen_at == row_t1.first_seen_at
    # assert row_t2.last_seen_at == t2
    # assert row_t2.resolved_at is None


def test_missing_sets_resolved_at() -> None:
    """D-16: finding present at t1, absent at t2 → row gets resolved_at=t2."""
    pytest.skip("Plan 12-05 to implement resolved_at transition")
    # _row_t1 = reconcile_findings([finding], at=t1)[0]
    # rows_t2 = reconcile_findings([], at=t2)  # finding absent at t2
    # # the previously-open row is closed with resolved_at == t2
    # closed = [r for r in rows_t2 if r.resolved_at is not None]
    # assert len(closed) == 1
    # assert closed[0].resolved_at == t2
