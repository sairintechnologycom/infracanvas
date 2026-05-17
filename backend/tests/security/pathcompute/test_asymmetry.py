"""Phase 12 ASY-01 — asymmetry detector tests.

RED until Plan 12-05 lands ``app.security.pathcompute.asymmetry``.
"""
from __future__ import annotations

import pytest

pytest.importorskip("app.security.pathcompute.asymmetry")  # collection RED

from app.security.pathcompute.asymmetry import asymmetric_nodes, is_asymmetric  # noqa: E402


def test_symmetric_pair_no_finding() -> None:
    """ASY-01: forward and return traverse identical hop set → not asymmetric."""
    pytest.skip("Plan 12-05 to implement is_asymmetric")
    # fwd = mk_path("forward", [PathHop(node_id="r1"), PathHop(node_id="fw-a"),
    #                            PathHop(node_id="r2")])
    # ret = mk_path("return", [PathHop(node_id="r2"), PathHop(node_id="fw-a"),
    #                          PathHop(node_id="r1")])
    # assert is_asymmetric(fwd, ret) is False


def test_asymmetric_pair_flagged() -> None:
    """ASY-01: forward through fw-A, return through fw-B → asymmetric;
    asymmetric_nodes returns {fw-A, fw-B}."""
    pytest.skip("Plan 12-05 to implement asymmetric_nodes")
    # fwd = mk_path("forward", [PathHop(node_id="r1"), PathHop(node_id="fw-A"),
    #                            PathHop(node_id="r2")])
    # ret = mk_path("return", [PathHop(node_id="r2"), PathHop(node_id="fw-B"),
    #                          PathHop(node_id="r1")])
    # assert is_asymmetric(fwd, ret) is True
    # assert asymmetric_nodes(fwd, ret) == {"fw-A", "fw-B"}
