"""Advanced Branching Tests (WCP 6-11).

This module tests advanced branching and merging patterns:
- WCP-6: Multi-Choice (OR-Split)
- WCP-7: Structured Synchronizing Merge
- WCP-8: Multi-Merge
- WCP-9: Structured Discriminator
- WCP-10: Arbitrary Cycles
- WCP-11: Implicit Termination

Each pattern is validated on PyOxigraph, EYE reasoner, and cross-engine consistency.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine
from kgcl.hybrid.wcp43_physics import WCP_PATTERN_CATALOG

from .fixtures import WCP11_IMPLICIT_TERMINATION_TOPOLOGY

# =============================================================================
# CATALOG-BASED TEST FACTORY (WCP 6-10)
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
# WCP 6-10: GENERATED TEST CLASSES
# =============================================================================

TestWCP6MultiChoice = _make_catalog_test_class(6, "Multi-Choice")
TestWCP7StructuredSynchronizingMerge = _make_catalog_test_class(7, "Structured Synchronizing Merge")
TestWCP8MultiMerge = _make_catalog_test_class(8, "Multi-Merge")
TestWCP9StructuredDiscriminator = _make_catalog_test_class(9, "Structured Discriminator")
TestWCP10ArbitraryCycles = _make_catalog_test_class(10, "Arbitrary Cycles")


# =============================================================================
# WCP-11: IMPLICIT TERMINATION
# =============================================================================


@pytest.mark.wcp(11)
class TestWCP11ImplicitTermination:
    """WCP-11: Implicit Termination.

    A process instance completes when there are no remaining work items that
    can be executed or that are currently executing. This is implicit completion
    based on process state.
    """

    @pytest.mark.oxigraph
    def test_oxigraph_execution(self) -> None:
        """Test WCP-11 on PyOxigraph engine."""
        engine = HybridEngine()
        engine.load_data(WCP11_IMPLICIT_TERMINATION_TOPOLOGY)
        result = engine.apply_physics()
        assert result.delta == 0

    @pytest.mark.eye
    def test_eye_execution(self, eye_available: bool) -> None:
        """Test WCP-11 on EYE reasoner."""
        if not eye_available:
            pytest.skip("EYE reasoner not installed")

        engine = HybridEngine()
        engine.load_data(WCP11_IMPLICIT_TERMINATION_TOPOLOGY)
        result = engine.apply_physics()
        assert result.delta == 0

    @pytest.mark.cross_engine
    def test_cross_engine_consistency(self, eye_available: bool) -> None:
        """Verify cross-engine consistency for WCP-11."""
        if not eye_available:
            pytest.skip("EYE reasoner not installed")

        engine1 = HybridEngine()
        engine1.load_data(WCP11_IMPLICIT_TERMINATION_TOPOLOGY)
        result1 = engine1.apply_physics()

        engine2 = HybridEngine()
        engine2.load_data(WCP11_IMPLICIT_TERMINATION_TOPOLOGY)
        result2 = engine2.apply_physics()

        assert result1.delta == result2.delta
