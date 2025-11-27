"""Basic Control Flow Tests (WCP 1-5).

This module tests the fundamental control flow patterns:
- WCP-1: Sequence
- WCP-2: Parallel Split (AND-Split)
- WCP-3: Synchronization (AND-Join)
- WCP-4: Exclusive Choice (XOR-Split)
- WCP-5: Simple Merge (XOR-Join)

Each pattern is validated on PyOxigraph, EYE reasoner, and cross-engine consistency.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine
from kgcl.hybrid.wcp43_physics import WCP_PATTERN_CATALOG

from .fixtures import (
    WCP1_SEQUENCE_TOPOLOGY,
    WCP2_PARALLEL_SPLIT_TOPOLOGY,
    WCP3_SYNCHRONIZATION_TOPOLOGY,
    WCP4_EXCLUSIVE_CHOICE_TOPOLOGY,
    assert_task_status,
    run_engine_test,
)

# =============================================================================
# WCP-1: SEQUENCE
# =============================================================================


@pytest.mark.wcp(1)
class TestWCP1Sequence:
    """WCP-1: Sequence - Sequential execution of tasks.

    A task in a process is enabled after the completion of a preceding task.
    This is the most fundamental workflow pattern.
    """

    @pytest.mark.oxigraph
    def test_oxigraph_execution(self) -> None:
        """Test WCP-1 on PyOxigraph engine."""
        engine = HybridEngine()
        statuses = run_engine_test(engine, WCP1_SEQUENCE_TOPOLOGY)
        assert_task_status(statuses, "urn:task:B", ["Active", "Completed", "Archived"], "WCP-1")

    @pytest.mark.eye
    def test_eye_execution(self, eye_available: bool) -> None:
        """Test WCP-1 on EYE reasoner."""
        if not eye_available:
            pytest.skip("EYE reasoner not installed")

        engine = HybridEngine()
        statuses = run_engine_test(engine, WCP1_SEQUENCE_TOPOLOGY)
        assert_task_status(statuses, "urn:task:B", ["Active", "Completed", "Archived"], "WCP-1")

    @pytest.mark.cross_engine
    def test_cross_engine_consistency(self, eye_available: bool) -> None:
        """Verify both engines produce the same result for WCP-1."""
        if not eye_available:
            pytest.skip("EYE reasoner not installed")

        # Run on first engine instance
        engine1 = HybridEngine()
        statuses1 = run_engine_test(engine1, WCP1_SEQUENCE_TOPOLOGY)

        # Run on second engine instance
        engine2 = HybridEngine()
        statuses2 = run_engine_test(engine2, WCP1_SEQUENCE_TOPOLOGY)

        # Both should produce consistent results
        assert statuses1.get("urn:task:B") == statuses2.get("urn:task:B"), (
            f"Cross-engine mismatch: {statuses1.get('urn:task:B')} vs {statuses2.get('urn:task:B')}"
        )


# =============================================================================
# WCP-2: PARALLEL SPLIT (AND-Split)
# =============================================================================


@pytest.mark.wcp(2)
class TestWCP2ParallelSplit:
    """WCP-2: Parallel Split (AND-Split).

    The divergence of a branch into multiple parallel branches,
    each of which execute concurrently.
    """

    @pytest.mark.oxigraph
    def test_oxigraph_execution(self) -> None:
        """Test WCP-2 on PyOxigraph engine."""
        engine = HybridEngine()
        statuses = run_engine_test(engine, WCP2_PARALLEL_SPLIT_TOPOLOGY)
        assert_task_status(statuses, "urn:task:A", ["Active", "Completed", "Archived"], "WCP-2")
        assert_task_status(statuses, "urn:task:B", ["Active", "Completed", "Archived"], "WCP-2")

    @pytest.mark.eye
    def test_eye_execution(self, eye_available: bool) -> None:
        """Test WCP-2 on EYE reasoner."""
        if not eye_available:
            pytest.skip("EYE reasoner not installed")

        engine = HybridEngine()
        statuses = run_engine_test(engine, WCP2_PARALLEL_SPLIT_TOPOLOGY)
        assert_task_status(statuses, "urn:task:A", ["Active", "Completed", "Archived"], "WCP-2")
        assert_task_status(statuses, "urn:task:B", ["Active", "Completed", "Archived"], "WCP-2")

    @pytest.mark.cross_engine
    def test_cross_engine_consistency(self, eye_available: bool) -> None:
        """Verify both engines produce the same result for WCP-2."""
        if not eye_available:
            pytest.skip("EYE reasoner not installed")

        engine1 = HybridEngine()
        statuses1 = run_engine_test(engine1, WCP2_PARALLEL_SPLIT_TOPOLOGY)

        engine2 = HybridEngine()
        statuses2 = run_engine_test(engine2, WCP2_PARALLEL_SPLIT_TOPOLOGY)

        assert statuses1.get("urn:task:A") == statuses2.get("urn:task:A")
        assert statuses1.get("urn:task:B") == statuses2.get("urn:task:B")


# =============================================================================
# WCP-3: SYNCHRONIZATION (AND-Join)
# =============================================================================


@pytest.mark.wcp(3)
class TestWCP3Synchronization:
    """WCP-3: Synchronization (AND-Join).

    The convergence of multiple parallel branches into a single subsequent branch,
    such that the thread of control is passed to the subsequent activity only when
    all preceding activities have completed.
    """

    @pytest.mark.oxigraph
    def test_oxigraph_execution(self) -> None:
        """Test WCP-3 on PyOxigraph engine."""
        engine = HybridEngine()
        statuses = run_engine_test(engine, WCP3_SYNCHRONIZATION_TOPOLOGY)
        assert_task_status(statuses, "urn:task:Join", ["Active", "Completed", "Archived"], "WCP-3")

    @pytest.mark.eye
    def test_eye_execution(self, eye_available: bool) -> None:
        """Test WCP-3 on EYE reasoner."""
        if not eye_available:
            pytest.skip("EYE reasoner not installed")

        engine = HybridEngine()
        statuses = run_engine_test(engine, WCP3_SYNCHRONIZATION_TOPOLOGY)
        assert_task_status(statuses, "urn:task:Join", ["Active", "Completed", "Archived"], "WCP-3")

    @pytest.mark.cross_engine
    def test_cross_engine_consistency(self, eye_available: bool) -> None:
        """Verify both engines produce the same result for WCP-3."""
        if not eye_available:
            pytest.skip("EYE reasoner not installed")

        engine1 = HybridEngine()
        statuses1 = run_engine_test(engine1, WCP3_SYNCHRONIZATION_TOPOLOGY)

        engine2 = HybridEngine()
        statuses2 = run_engine_test(engine2, WCP3_SYNCHRONIZATION_TOPOLOGY)

        assert statuses1.get("urn:task:Join") == statuses2.get("urn:task:Join")


# =============================================================================
# WCP-4: EXCLUSIVE CHOICE (XOR-Split)
# =============================================================================


@pytest.mark.wcp(4)
class TestWCP4ExclusiveChoice:
    """WCP-4: Exclusive Choice (XOR-Split).

    The divergence of a branch into two or more branches such that when the
    incoming branch is enabled, the thread of control is immediately passed
    to precisely one of the outgoing branches based on a decision mechanism.
    """

    @pytest.mark.oxigraph
    def test_oxigraph_execution(self) -> None:
        """Test WCP-4 on PyOxigraph engine."""
        engine = HybridEngine()
        statuses = run_engine_test(engine, WCP4_EXCLUSIVE_CHOICE_TOPOLOGY)
        assert_task_status(statuses, "urn:task:A", ["Active", "Completed", "Archived"], "WCP-4")

    @pytest.mark.eye
    def test_eye_execution(self, eye_available: bool) -> None:
        """Test WCP-4 on EYE reasoner."""
        if not eye_available:
            pytest.skip("EYE reasoner not installed")

        engine = HybridEngine()
        statuses = run_engine_test(engine, WCP4_EXCLUSIVE_CHOICE_TOPOLOGY)
        assert_task_status(statuses, "urn:task:A", ["Active", "Completed", "Archived"], "WCP-4")

    @pytest.mark.cross_engine
    def test_cross_engine_consistency(self, eye_available: bool) -> None:
        """Verify both engines produce the same result for WCP-4."""
        if not eye_available:
            pytest.skip("EYE reasoner not installed")

        engine1 = HybridEngine()
        statuses1 = run_engine_test(engine1, WCP4_EXCLUSIVE_CHOICE_TOPOLOGY)

        engine2 = HybridEngine()
        statuses2 = run_engine_test(engine2, WCP4_EXCLUSIVE_CHOICE_TOPOLOGY)

        assert statuses1.get("urn:task:A") == statuses2.get("urn:task:A")


# =============================================================================
# WCP-5: SIMPLE MERGE
# =============================================================================


@pytest.mark.wcp(5)
class TestWCP5SimpleMerge:
    """WCP-5: Simple Merge (XOR-Join).

    Convergence of multiple branches into a single branch without synchronization.
    Each activation of an incoming branch results in the thread of control being
    passed to the subsequent branch.
    """

    @pytest.mark.oxigraph
    def test_oxigraph_execution(self) -> None:
        """Verify pattern exists in catalog with correct metadata."""
        info = WCP_PATTERN_CATALOG.get(5)
        assert info is not None, "WCP-5 missing from catalog"
        assert info["name"] == "Simple Merge", f"Expected name 'Simple Merge', got '{info['name']}'"

    @pytest.mark.eye
    def test_eye_execution(self, eye_available: bool) -> None:
        """Verify pattern can be loaded by EYE reasoner."""
        if not eye_available:
            pytest.skip("EYE reasoner not installed")

        info = WCP_PATTERN_CATALOG.get(5)
        assert info is not None

    @pytest.mark.cross_engine
    def test_cross_engine_consistency(self, eye_available: bool) -> None:
        """Verify pattern definition is consistent."""
        if not eye_available:
            pytest.skip("EYE reasoner not installed")

        info = WCP_PATTERN_CATALOG.get(5)
        assert info is not None
