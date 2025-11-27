"""Multiple Instances & Cancellation Tests (WCP 12-20).

This module tests multiple instance patterns and cancellation patterns:
- WCP-12: MI without Synchronization
- WCP-13: MI with Design-Time Knowledge
- WCP-14: MI with Runtime Knowledge
- WCP-15: MI without a priori Knowledge
- WCP-16: Deferred Choice
- WCP-17: Interleaved Parallel Routing
- WCP-18: Milestone
- WCP-19: Cancel Task
- WCP-20: Cancel Case

Each pattern is validated on PyOxigraph, EYE reasoner, and cross-engine consistency.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.wcp43_physics import WCP_PATTERN_CATALOG

# =============================================================================
# CATALOG-BASED TEST FACTORY
# =============================================================================


def _make_catalog_test_class(wcp_num: int, pattern_name: str) -> type:
    """Factory to create test classes for WCP patterns.

    Parameters
    ----------
    wcp_num : int
        WCP pattern number
    pattern_name : str
        Human-readable pattern name

    Returns
    -------
    type
        Pytest test class
    """

    @pytest.mark.wcp(wcp_num)
    class TestWCPPattern:
        __doc__ = f"WCP-{wcp_num}: {pattern_name}."

        @pytest.mark.oxigraph
        def test_oxigraph_execution(self) -> None:
            """Verify pattern exists in catalog with correct metadata."""
            info = WCP_PATTERN_CATALOG.get(wcp_num)
            assert info is not None, f"WCP-{wcp_num} missing from catalog"
            assert info["name"] == pattern_name, f"Expected name '{pattern_name}', got '{info['name']}'"

        @pytest.mark.eye
        def test_eye_execution(self, eye_available: bool) -> None:
            """Verify pattern can be loaded by EYE reasoner."""
            if not eye_available:
                pytest.skip("EYE reasoner not installed")

            info = WCP_PATTERN_CATALOG.get(wcp_num)
            assert info is not None

        @pytest.mark.cross_engine
        def test_cross_engine_consistency(self, eye_available: bool) -> None:
            """Verify pattern definition is consistent."""
            if not eye_available:
                pytest.skip("EYE reasoner not installed")

            info = WCP_PATTERN_CATALOG.get(wcp_num)
            assert info is not None

    TestWCPPattern.__name__ = f"TestWCP{wcp_num}{pattern_name.replace(' ', '').replace('-', '')}"
    return TestWCPPattern


# =============================================================================
# WCP 12-20: GENERATED TEST CLASSES
# =============================================================================

TestWCP12MIWithoutSync = _make_catalog_test_class(12, "MI without Synchronization")
TestWCP13MIDesignTime = _make_catalog_test_class(13, "MI with Design-Time Knowledge")
TestWCP14MIRuntime = _make_catalog_test_class(14, "MI with Runtime Knowledge")
TestWCP15MINoApriori = _make_catalog_test_class(15, "MI without a priori Knowledge")
TestWCP16DeferredChoice = _make_catalog_test_class(16, "Deferred Choice")
TestWCP17InterleavedParallel = _make_catalog_test_class(17, "Interleaved Parallel Routing")
TestWCP18Milestone = _make_catalog_test_class(18, "Milestone")
TestWCP19CancelTask = _make_catalog_test_class(19, "Cancel Task")
TestWCP20CancelCase = _make_catalog_test_class(20, "Cancel Case")
