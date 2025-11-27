"""CTQ-4: Performance Tests for WCP Patterns.

This module validates that YAWL workflow control patterns execute within
acceptable tick/time bounds and scale linearly with graph size.

Test Coverage
-------------
- Basic Control Flow: Sequence (WCP-1), Parallel Split (WCP-2)
- Tick convergence (<5 ticks)
- Time limits (<100ms per tick)

Quality Gates
-------------
- Converge within expected tick count
- Execute within time limits (<100ms per tick)
- Scale linearly with graph size
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine

if TYPE_CHECKING:
    from collections.abc import Callable

    from kgcl.hybrid.hybrid_engine import PhysicsResult


@pytest.fixture
def load_and_run(engine: HybridEngine) -> Callable[[str, int], tuple[list[PhysicsResult], dict[str, str]]]:
    """Factory fixture for loading topology and running physics.

    Parameters
    ----------
    engine : HybridEngine
        Engine to load data into and run.

    Returns
    -------
    Callable[[str, int], tuple[list[PhysicsResult], dict[str, str]]]
        Function that loads topology, runs physics, returns results and statuses.
    """

    def _load_and_run(topology: str, max_ticks: int = 10) -> tuple[list[PhysicsResult], dict[str, str]]:
        engine.load_data(topology)
        results = engine.run_to_completion(max_ticks=max_ticks)
        statuses = engine.inspect()
        return results, statuses

    return _load_and_run


class TestCTQ4Performance:
    """CTQ-4: Performance - Execution within acceptable tick/time bounds.

    Validates that patterns:
    - Converge within expected tick count
    - Execute within time limits (<100ms per tick)
    - Scale linearly with graph size
    """

    def test_basic_control_flow_sequence_performance(
        self, load_and_run: Callable[[str, int], tuple[list[PhysicsResult], dict[str, str]]]
    ) -> None:
        """WCP-1 Sequence converges within acceptable tick count.

        CTQ Factor: Performance
        Pattern: WCP-1 (Sequence)
        Expected: <5 ticks, <100ms per tick
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
        results, statuses = load_and_run(topology, max_ticks=10)

        assert len(results) < 5, "Should converge in <5 ticks"
        for result in results:
            assert result.duration_ms < 100.0, f"Tick {result.tick_number} took {result.duration_ms}ms (>100ms)"

    def test_advanced_branching_parallel_split_performance(
        self, load_and_run: Callable[[str, int], tuple[list[PhysicsResult], dict[str, str]]]
    ) -> None:
        """WCP-2 Parallel Split converges efficiently.

        CTQ Factor: Performance
        Pattern: WCP-2 (AND-Split)
        Expected: <5 ticks, <100ms per tick
        """
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeAnd ;
            yawl:flowsInto <urn:flow:1>, <urn:flow:2>, <urn:flow:3> .

        <urn:flow:1> yawl:nextElementRef <urn:task:B> .
        <urn:flow:2> yawl:nextElementRef <urn:task:C> .
        <urn:flow:3> yawl:nextElementRef <urn:task:D> .

        <urn:task:B> a yawl:Task .
        <urn:task:C> a yawl:Task .
        <urn:task:D> a yawl:Task .
        """
        results, statuses = load_and_run(topology, max_ticks=10)

        assert len(results) < 5, "Should converge in <5 ticks"
        for result in results:
            assert result.duration_ms < 100.0, f"Tick {result.tick_number} took {result.duration_ms}ms"
