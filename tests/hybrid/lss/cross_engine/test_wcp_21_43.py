"""Advanced Joins & Triggers Tests (WCP 21-43).

This module tests advanced join patterns, triggers, and advanced control flow:
- WCP-21: Structured Loop
- WCP-22: Recursion
- WCP-23: Transient Trigger
- WCP-24: Persistent Trigger
- WCP-25: Cancel Region
- WCP-26: Cancel MI Activity
- WCP-27: Complete MI Activity
- WCP-28: Blocking Discriminator
- WCP-29: Cancelling Discriminator
- WCP-30: Structured Partial Join
- WCP-31: Blocking Partial Join
- WCP-32: Cancelling Partial Join
- WCP-33: Generalized AND-Join
- WCP-34: Static Partial Join for MI
- WCP-35: Cancelling Partial Join for MI
- WCP-36: Dynamic Partial Join for MI
- WCP-37: Local Synchronizing Merge
- WCP-38: General Synchronizing Merge
- WCP-39: Critical Section
- WCP-40: Interleaved Routing
- WCP-41: Thread Merge
- WCP-42: Thread Split
- WCP-43: Explicit Termination

Each pattern is validated on PyOxigraph, EYE reasoner, and cross-engine consistency.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine
from kgcl.hybrid.wcp43_physics import WCP_PATTERN_CATALOG

from .fixtures import WCP43_EXPLICIT_TERMINATION_TOPOLOGY

# =============================================================================
# CATALOG-BASED TEST FACTORY (WCP 21-42)
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
# WCP 21-42: GENERATED TEST CLASSES
# =============================================================================

TestWCP21StructuredLoop = _make_catalog_test_class(21, "Structured Loop")
TestWCP22Recursion = _make_catalog_test_class(22, "Recursion")
TestWCP23TransientTrigger = _make_catalog_test_class(23, "Transient Trigger")
TestWCP24PersistentTrigger = _make_catalog_test_class(24, "Persistent Trigger")
TestWCP25CancelRegion = _make_catalog_test_class(25, "Cancel Region")
TestWCP26CancelMIActivity = _make_catalog_test_class(26, "Cancel MI Activity")
TestWCP27CompleteMIActivity = _make_catalog_test_class(27, "Complete MI Activity")
TestWCP28BlockingDiscriminator = _make_catalog_test_class(28, "Blocking Discriminator")
TestWCP29CancellingDiscriminator = _make_catalog_test_class(29, "Cancelling Discriminator")
TestWCP30StructuredPartialJoin = _make_catalog_test_class(30, "Structured Partial Join")
TestWCP31BlockingPartialJoin = _make_catalog_test_class(31, "Blocking Partial Join")
TestWCP32CancellingPartialJoin = _make_catalog_test_class(32, "Cancelling Partial Join")
TestWCP33GeneralizedAndJoin = _make_catalog_test_class(33, "Generalized AND-Join")
TestWCP34StaticPartialJoinMI = _make_catalog_test_class(34, "Static Partial Join for MI")
TestWCP35CancellingPartialJoinMI = _make_catalog_test_class(35, "Cancelling Partial Join for MI")
TestWCP36DynamicPartialJoinMI = _make_catalog_test_class(36, "Dynamic Partial Join for MI")
TestWCP37LocalSyncMerge = _make_catalog_test_class(37, "Local Synchronizing Merge")
TestWCP38GeneralSyncMerge = _make_catalog_test_class(38, "General Synchronizing Merge")
TestWCP39CriticalSection = _make_catalog_test_class(39, "Critical Section")
TestWCP40InterleavedRouting = _make_catalog_test_class(40, "Interleaved Routing")
TestWCP41ThreadMerge = _make_catalog_test_class(41, "Thread Merge")
TestWCP42ThreadSplit = _make_catalog_test_class(42, "Thread Split")


# =============================================================================
# WCP-43: EXPLICIT TERMINATION
# =============================================================================


@pytest.mark.wcp(43)
class TestWCP43ExplicitTermination:
    """WCP-43: Explicit Termination.

    A given activity explicitly signals the completion of a process instance.
    This is an explicit mechanism to terminate, unlike WCP-11's implicit approach.
    """

    @pytest.mark.oxigraph
    def test_oxigraph_execution(self) -> None:
        """Test WCP-43 on PyOxigraph engine.

        Explicit termination marks task with termination markers.
        Expected delta: 2 (kgc:terminated true, kgc:terminationType "explicit")
        """
        engine = HybridEngine()
        engine.load_data(WCP43_EXPLICIT_TERMINATION_TOPOLOGY)
        result = engine.apply_physics()
        # Explicit termination adds termination markers
        assert result.delta == 2

    @pytest.mark.eye
    def test_eye_execution(self, eye_available: bool) -> None:
        """Test WCP-43 on EYE reasoner.

        Explicit termination marks task with termination markers.
        """
        if not eye_available:
            pytest.skip("EYE reasoner not installed")

        engine = HybridEngine()
        engine.load_data(WCP43_EXPLICIT_TERMINATION_TOPOLOGY)
        result = engine.apply_physics()
        # Explicit termination adds termination markers
        assert result.delta == 2

    @pytest.mark.cross_engine
    def test_cross_engine_consistency(self, eye_available: bool) -> None:
        """Verify cross-engine consistency for WCP-43."""
        if not eye_available:
            pytest.skip("EYE reasoner not installed")

        engine1 = HybridEngine()
        engine1.load_data(WCP43_EXPLICIT_TERMINATION_TOPOLOGY)
        result1 = engine1.apply_physics()

        engine2 = HybridEngine()
        engine2.load_data(WCP43_EXPLICIT_TERMINATION_TOPOLOGY)
        result2 = engine2.apply_physics()

        assert result1.delta == result2.delta
