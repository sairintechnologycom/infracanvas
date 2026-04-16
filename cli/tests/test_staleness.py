"""Tests for runtime staleness checks (RST-01, RST-02). Wave 0 stubs."""
import pytest


@pytest.mark.skip("Wave 0 stub — implementation in Plan 03")
class TestLambdaStaleness:
    def test_eol_runtime_flagged(self): ...
    def test_current_runtime_not_flagged(self): ...
    def test_finding_has_framework_ids(self): ...


@pytest.mark.skip("Wave 0 stub — implementation in Plan 03")
class TestEksStaleness:
    def test_old_eks_flagged(self): ...


@pytest.mark.skip("Wave 0 stub — implementation in Plan 03")
class TestAksStaleness:
    def test_old_aks_flagged(self): ...


@pytest.mark.skip("Wave 0 stub — implementation in Plan 03")
class TestResourceLocks:
    def test_unlocked_critical_resource_flagged(self): ...
    def test_locked_resource_not_flagged(self): ...
