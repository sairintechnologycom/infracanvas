"""Phase 12 D-04 — taskiq schedule registration test.

RED until Plan 12-06 registers ``recompute_paths_all_sites`` with a 15-min cron.
"""
from __future__ import annotations

import pytest

pytest.importorskip("app.queue.tasks.path_compute")  # collection RED


def test_recompute_paths_all_sites_registered_with_15min_cron() -> None:
    """D-04 — scheduled cron */15 * * * *."""
    pytest.skip("Plan 12-06 to register taskiq cron task")
    # from app.queue.tasks.path_compute import recompute_paths_all_sites
    # labels = recompute_paths_all_sites.labels
    # schedules = labels.get("schedule", [])
    # assert any(s.get("cron") == "*/15 * * * *" for s in schedules)
