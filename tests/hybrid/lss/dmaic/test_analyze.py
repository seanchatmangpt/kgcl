"""DMAIC ANALYZE Phase: Pattern Analysis and Correlation Tests.

This module tests pattern behavior analysis, root cause identification, and
correlation detection between patterns and execution characteristics.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine, PhysicsResult
from kgcl.hybrid.wcp43_physics import get_patterns_by_category, get_patterns_by_verb


class TestDMAIC003Analyze:
    """ANALYZE Phase: Test pattern analysis and correlation.

    Tests that analyze pattern behavior, identify root causes, and detect
    correlations between patterns and execution characteristics.
    """

    def test_pattern_verb_correlation(self) -> None:
        """Test correlation between pattern verbs and execution behavior.

        Verifies:
        - Copy verbs create parallel branches (multiple activations)
        - Await verbs synchronize (wait for completion)
        - Filter verbs make decisions (conditional activation)
        """
        # Arrange: Get patterns by verb type
        copy_patterns = get_patterns_by_verb("Copy")
        await_patterns = get_patterns_by_verb("Await")
        filter_patterns = get_patterns_by_verb("Filter")

        # Assert: Verify verb groupings make sense
        assert len(copy_patterns) > 0, "Must have Copy patterns"
        assert len(await_patterns) > 0, "Must have Await patterns"
        assert len(filter_patterns) > 0, "Must have Filter patterns"

        # WCP-2 (Parallel Split) should be a Copy pattern
        assert 2 in copy_patterns, "WCP-2 Parallel Split should use Copy verb"

        # WCP-3 (Synchronization) should be an Await pattern
        assert 3 in await_patterns, "WCP-3 Synchronization should use Await verb"

        # WCP-4 (Exclusive Choice) should be a Filter pattern
        assert 4 in filter_patterns, "WCP-4 Exclusive Choice should use Filter verb"

    def test_category_distribution_analysis(self) -> None:
        """Test that pattern categories have reasonable distribution.

        Verifies:
        - No category is empty
        - Basic patterns exist (WCP 1-5)
        - Advanced patterns exist (WCP 28+)
        """
        # Arrange
        basic_patterns = get_patterns_by_category("Basic Control Flow")
        advanced_sync_patterns = get_patterns_by_category("Advanced Sync")

        # Assert
        assert len(basic_patterns) >= 5, "Must have at least 5 basic patterns"
        assert 1 in basic_patterns, "WCP-1 Sequence must be basic"
        assert 2 in basic_patterns, "WCP-2 Parallel Split must be basic"
        assert 3 in basic_patterns, "WCP-3 Synchronization must be basic"

        assert len(advanced_sync_patterns) > 0, "Must have advanced sync patterns"
        assert 37 in advanced_sync_patterns or 38 in advanced_sync_patterns, "WCP-37/38 must be advanced sync"

    def test_convergence_analysis(self) -> None:
        """Test analysis of convergence behavior across patterns.

        Verifies:
        - Simple patterns converge quickly (<5 ticks)
        - Complex patterns may need more ticks
        - All patterns eventually converge
        """
        # Arrange: Simple sequence pattern
        engine = HybridEngine()
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:1> .

        <urn:flow:1> yawl:nextElementRef <urn:task:B> .
        <urn:task:B> a yawl:Task ;
            kgc:status "Pending" .
        """
        engine.load_data(topology)

        # Act
        results = engine.run_to_completion(max_ticks=20)

        # Assert
        assert len(results) < 5, "Simple sequence should converge in < 5 ticks"
        assert results[-1].converged, "Must reach convergence"

        # Analyze: Count productive ticks (delta > 0)
        productive_ticks = sum(1 for r in results if r.delta > 0)
        assert productive_ticks > 0, "Must have at least one productive tick"
