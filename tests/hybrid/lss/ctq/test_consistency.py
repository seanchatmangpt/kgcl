"""CTQ-3: Consistency Tests for WCP Patterns.

This module validates that YAWL workflow control patterns produce deterministic
behavior across multiple runs (same inputs → same outputs).

Test Coverage
-------------
- Basic Control Flow: Sequence (WCP-1), Parallel Split (WCP-2)
- Deterministic tick counts
- Identical final states

Quality Gates
-------------
- Identical results on repeated runs
- Same tick counts for convergence
- Same final states across runs
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine


class TestCTQ3Consistency:
    """CTQ-3: Consistency - Deterministic behavior across multiple runs.

    Validates that patterns produce:
    - Identical results on repeated runs
    - Same tick counts for convergence
    - Same final states
    """

    def test_basic_control_flow_sequence_deterministic(self, engine: HybridEngine) -> None:
        """WCP-1 Sequence produces identical results across runs.

        CTQ Factor: Consistency
        Pattern: WCP-1 (Sequence)
        Expected: Same tick count, same final state
        """
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:1> .

        <urn:flow:1> yawl:nextElementRef <urn:task:B> .
        <urn:task:B> a yawl:Task .
        """

        # Run 1
        engine1 = HybridEngine()
        engine1.load_data(topology)
        results1 = engine1.run_to_completion(max_ticks=5)
        statuses1 = engine1.inspect()

        # Run 2
        engine2 = HybridEngine()
        engine2.load_data(topology)
        results2 = engine2.run_to_completion(max_ticks=5)
        statuses2 = engine2.inspect()

        assert len(results1) == len(results2), "Tick counts should be identical"
        assert statuses1 == statuses2, "Final states should be identical"

    def test_advanced_branching_and_split_deterministic(self, engine: HybridEngine) -> None:
        """WCP-2 Parallel Split produces identical results across runs.

        CTQ Factor: Consistency
        Pattern: WCP-2 (AND-Split)
        Expected: Same activation order, same final state
        """
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeAnd ;
            yawl:flowsInto <urn:flow:1>, <urn:flow:2> .

        <urn:flow:1> yawl:nextElementRef <urn:task:B> .
        <urn:flow:2> yawl:nextElementRef <urn:task:C> .

        <urn:task:B> a yawl:Task .
        <urn:task:C> a yawl:Task .
        """

        # Run 1
        engine1 = HybridEngine()
        engine1.load_data(topology)
        results1 = engine1.run_to_completion(max_ticks=5)
        statuses1 = engine1.inspect()

        # Run 2
        engine2 = HybridEngine()
        engine2.load_data(topology)
        results2 = engine2.run_to_completion(max_ticks=5)
        statuses2 = engine2.inspect()

        assert len(results1) == len(results2), "Tick counts should match"
        assert statuses1 == statuses2, "Final states should match"
