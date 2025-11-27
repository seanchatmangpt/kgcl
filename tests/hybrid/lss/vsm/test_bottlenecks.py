"""Bottleneck Identification and Analysis Tests.

Tests for identifying workflow bottlenecks, analyzing WIP,
and measuring parallel vs sequential throughput.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine
from tests.hybrid.lss.vsm.calculations import calculate_vsm_metrics, identify_bottlenecks


@pytest.fixture
def engine() -> HybridEngine:
    """Create fresh HybridEngine for VSM testing."""
    return HybridEngine()


class TestVSM002ParallelSplitValueStream:
    """VSM-002: Analyze value stream for parallel execution.

    Value Stream: Split -> (A || B || C) -> Join
    Focus: WIP, throughput, parallel efficiency
    """

    def test_parallel_wip_measurement(self, engine: HybridEngine) -> None:
        """Measure WIP (Work In Progress) in parallel branches."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Split> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeAnd ;
            yawl:flowsInto <urn:flow:to_a>, <urn:flow:to_b>, <urn:flow:to_c> .

        <urn:flow:to_a> yawl:nextElementRef <urn:task:A> .
        <urn:flow:to_b> yawl:nextElementRef <urn:task:B> .
        <urn:flow:to_c> yawl:nextElementRef <urn:task:C> .

        <urn:task:A> a yawl:Task .
        <urn:task:B> a yawl:Task .
        <urn:task:C> a yawl:Task .
        """
        engine.load_data(topology)
        results = engine.run_to_completion(max_ticks=10)

        vsm = calculate_vsm_metrics(results)

        # WIP should be >= 3 for parallel activation of 3 branches
        assert vsm.max_wip >= 3, "Parallel split should have WIP >= 3"

    def test_parallel_throughput_vs_sequence(self, engine: HybridEngine) -> None:
        """Compare parallel vs sequential throughput using REAL engine."""
        # Sequential version
        topology_seq = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:a_to_b> .

        <urn:flow:a_to_b> yawl:nextElementRef <urn:task:B> .

        <urn:task:B> a yawl:Task ;
            yawl:flowsInto <urn:flow:b_to_c> .

        <urn:flow:b_to_c> yawl:nextElementRef <urn:task:C> .

        <urn:task:C> a yawl:Task .
        """
        engine_seq = HybridEngine()
        engine_seq.load_data(topology_seq)
        results_seq = engine_seq.run_to_completion(max_ticks=10)

        # Parallel version
        topology_par = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Split> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeAnd ;
            yawl:flowsInto <urn:flow:to_a>, <urn:flow:to_b>, <urn:flow:to_c> .

        <urn:flow:to_a> yawl:nextElementRef <urn:task:A> .
        <urn:flow:to_b> yawl:nextElementRef <urn:task:B> .
        <urn:flow:to_c> yawl:nextElementRef <urn:task:C> .

        <urn:task:A> a yawl:Task .
        <urn:task:B> a yawl:Task .
        <urn:task:C> a yawl:Task .
        """
        engine_par = HybridEngine()
        engine_par.load_data(topology_par)
        results_par = engine_par.run_to_completion(max_ticks=10)

        vsm_seq = calculate_vsm_metrics(results_seq)
        vsm_par = calculate_vsm_metrics(results_par)

        # Parallel should complete in fewer or equal ticks
        assert vsm_par.total_ticks <= vsm_seq.total_ticks


class TestVSM004BottleneckIdentification:
    """VSM-004: Identify workflow bottlenecks.

    Value Stream: Complex workflow with varied task durations
    Focus: Bottleneck detection, constraint analysis
    """

    def test_identify_slowest_tick(self, engine: HybridEngine) -> None:
        """Identify the slowest tick (bottleneck) in workflow."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:a_to_b> .

        <urn:flow:a_to_b> yawl:nextElementRef <urn:task:B> .

        <urn:task:B> a yawl:Task ;
            yawl:flowsInto <urn:flow:b_to_c> .

        <urn:flow:b_to_c> yawl:nextElementRef <urn:task:C> .

        <urn:task:C> a yawl:Task .
        """
        engine.load_data(topology)
        results = engine.run_to_completion(max_ticks=10)

        bottlenecks = identify_bottlenecks(results)

        # Should have at least one bottleneck
        assert len(bottlenecks) > 0
        # First bottleneck should be slowest
        if len(bottlenecks) >= 2:
            assert bottlenecks[0][1] >= bottlenecks[1][1]

    def test_bottleneck_impact_on_lead_time(self, engine: HybridEngine) -> None:
        """Analyze bottleneck contribution to total lead time."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeAnd ;
            yawl:flowsInto <urn:flow:to_b>, <urn:flow:to_c> .

        <urn:flow:to_b> yawl:nextElementRef <urn:task:B> .
        <urn:flow:to_c> yawl:nextElementRef <urn:task:C> .

        <urn:task:B> a yawl:Task .
        <urn:task:C> a yawl:Task .
        """
        engine.load_data(topology)
        results = engine.run_to_completion(max_ticks=10)

        vsm = calculate_vsm_metrics(results)
        bottlenecks = identify_bottlenecks(results)

        # Bottleneck should be significant portion of lead time
        if bottlenecks:
            bottleneck_duration = bottlenecks[0][1]
            bottleneck_pct = (bottleneck_duration / vsm.lead_time_ms) * 100
            assert bottleneck_pct > 0, "Bottleneck should contribute to lead time"


class TestVSM007XorSplitWasteAnalysis:
    """VSM-007: Analyze waste in exclusive choice patterns.

    Value Stream: XOR-Split -> (Path A XOR Path B)
    Focus: Unused path waste, decision overhead
    """

    def test_xor_split_path_utilization(self, engine: HybridEngine) -> None:
        """Measure utilization of XOR-split paths."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Decision> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeXor ;
            yawl:flowsInto <urn:flow:to_a>, <urn:flow:to_b> .

        <urn:flow:to_a> yawl:nextElementRef <urn:task:PathA> ;
            yawl:hasPredicate <urn:pred:a> .
        <urn:pred:a> kgc:evaluatesTo true .

        <urn:flow:to_b> yawl:nextElementRef <urn:task:PathB> ;
            yawl:isDefaultFlow true .

        <urn:task:PathA> a yawl:Task .
        <urn:task:PathB> a yawl:Task .
        """
        engine.load_data(topology)
        results = engine.run_to_completion(max_ticks=10)
        statuses = engine.inspect()

        # Only one path should be utilized
        path_a_used = statuses.get("urn:task:PathA") in ["Active", "Completed", "Archived"]
        path_b_used = statuses.get("urn:task:PathB") in ["Active", "Completed", "Archived"]

        # Exclusive choice means only one path
        utilized_paths = sum([path_a_used, path_b_used])
        assert utilized_paths == 1, "XOR should utilize exactly one path"

    def test_xor_decision_overhead(self, engine: HybridEngine) -> None:
        """Measure decision overhead in XOR-split."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Decision> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeXor ;
            yawl:flowsInto <urn:flow:to_a>, <urn:flow:to_b> .

        <urn:flow:to_a> yawl:nextElementRef <urn:task:PathA> ;
            yawl:hasPredicate <urn:pred:a> .
        <urn:pred:a> kgc:evaluatesTo true .

        <urn:flow:to_b> yawl:nextElementRef <urn:task:PathB> ;
            yawl:isDefaultFlow true .

        <urn:task:PathA> a yawl:Task .
        <urn:task:PathB> a yawl:Task .
        """
        engine.load_data(topology)
        results = engine.run_to_completion(max_ticks=10)

        # Decision overhead is captured in tick durations
        vsm = calculate_vsm_metrics(results)
        assert vsm.lead_time_ms > 0


class TestVSM008OrSplitMultiPathEfficiency:
    """VSM-008: Analyze multi-path activation efficiency.

    Value Stream: OR-Split -> (multiple paths based on predicates)
    Focus: WIP, parallel efficiency, predicate overhead
    """

    def test_or_split_wip_analysis(self, engine: HybridEngine) -> None:
        """Analyze WIP when multiple OR-split paths activate."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:OrSplit> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeOr ;
            yawl:flowsInto <urn:flow:to_a>, <urn:flow:to_b>, <urn:flow:to_c> .

        <urn:flow:to_a> yawl:nextElementRef <urn:task:PathA> ;
            yawl:hasPredicate <urn:pred:a> .
        <urn:pred:a> kgc:evaluatesTo true .

        <urn:flow:to_b> yawl:nextElementRef <urn:task:PathB> ;
            yawl:hasPredicate <urn:pred:b> .
        <urn:pred:b> kgc:evaluatesTo true .

        <urn:flow:to_c> yawl:nextElementRef <urn:task:PathC> ;
            yawl:hasPredicate <urn:pred:c> .
        <urn:pred:c> kgc:evaluatesTo false .

        <urn:task:PathA> a yawl:Task .
        <urn:task:PathB> a yawl:Task .
        <urn:task:PathC> a yawl:Task .
        """
        engine.load_data(topology)
        results = engine.run_to_completion(max_ticks=10)

        vsm = calculate_vsm_metrics(results)

        # OR-split with 2 true predicates should have WIP >= 2
        assert vsm.max_wip >= 2, "OR-split should activate multiple paths"


class TestVSM010DiscriminatorPatternWaste:
    """VSM-010: Analyze waste in discriminator patterns.

    Value Stream: Multiple paths -> Discriminator -> Continue
    Focus: Non-winner path waste, cancellation overhead
    """

    def test_cancelling_discriminator_waste(self, engine: HybridEngine) -> None:
        """Measure waste from cancelled discriminator paths."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:TaskA> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:to_discrim> .

        <urn:task:TaskB> a yawl:Task ;
            kgc:status "Active" ;
            yawl:flowsInto <urn:flow:to_discrim2> .

        <urn:flow:to_discrim> yawl:nextElementRef <urn:task:Discrim> .
        <urn:flow:to_discrim2> yawl:nextElementRef <urn:task:Discrim> .

        <urn:task:Discrim> a yawl:Task ;
            yawl:hasJoin kgc:CancellingDiscriminator .
        """
        engine.load_data(topology)
        results = engine.run_to_completion(max_ticks=10)
        statuses = engine.inspect()

        # Discriminator should activate
        assert statuses.get("urn:task:Discrim") in ["Active", "Completed", "Archived"]


class TestVSM011ComplexWorkflowEndToEnd:
    """VSM-011: Complete VSM analysis of complex workflow.

    Value Stream: Multi-pattern workflow with splits, joins, choices
    Focus: Full VSM metrics, waste identification, efficiency
    """

    def test_complex_workflow_full_vsm(self, engine: HybridEngine) -> None:
        """Complete VSM analysis of complex multi-pattern workflow."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        # Start with AND-split
        <urn:task:Start> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeAnd ;
            yawl:flowsInto <urn:flow:to_a>, <urn:flow:to_b> .

        # Parallel branch A
        <urn:flow:to_a> yawl:nextElementRef <urn:task:BranchA> .
        <urn:task:BranchA> a yawl:Task ;
            yawl:flowsInto <urn:flow:a_to_join> .

        # Parallel branch B with XOR-split
        <urn:flow:to_b> yawl:nextElementRef <urn:task:BranchB> .
        <urn:task:BranchB> a yawl:Task ;
            yawl:hasSplit yawl:ControlTypeXor ;
            yawl:flowsInto <urn:flow:to_b1>, <urn:flow:to_b2> .

        <urn:flow:to_b1> yawl:nextElementRef <urn:task:B1> ;
            yawl:hasPredicate <urn:pred:b1> .
        <urn:pred:b1> kgc:evaluatesTo true .

        <urn:flow:to_b2> yawl:nextElementRef <urn:task:B2> ;
            yawl:isDefaultFlow true .

        <urn:task:B1> a yawl:Task ;
            yawl:flowsInto <urn:flow:b1_to_join> .

        <urn:task:B2> a yawl:Task ;
            yawl:flowsInto <urn:flow:b2_to_join> .

        # AND-join
        <urn:flow:a_to_join> yawl:nextElementRef <urn:task:Join> .
        <urn:flow:b1_to_join> yawl:nextElementRef <urn:task:Join> .

        <urn:task:Join> a yawl:Task ;
            yawl:hasJoin yawl:ControlTypeAnd ;
            yawl:flowsInto <urn:flow:to_end> .

        # End
        <urn:flow:to_end> yawl:nextElementRef <urn:task:End> .
        <urn:task:End> a yawl:Task .
        """
        engine.load_data(topology)
        results = engine.run_to_completion(max_ticks=20)

        # Full VSM analysis
        vsm = calculate_vsm_metrics(results)

        # Verify all metrics are calculated
        assert vsm.lead_time_ms > 0
        assert vsm.total_ticks > 0
        assert 0.0 <= vsm.process_efficiency <= 1.0
        assert vsm.max_wip >= 0
        assert 0.0 <= vsm.waste_percentage <= 100.0

        # Complex workflow should have reasonable tick count
        assert vsm.total_ticks <= 20, "Should complete within max_ticks"
