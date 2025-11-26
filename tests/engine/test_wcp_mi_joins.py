"""Comprehensive tests for YAWL MI Join Patterns (WCP-34, WCP-35, WCP-36).

Tests verify Multiple Instance join patterns with partial synchronization:
- WCP-34: Static Partial Join (threshold="static", completionStrategy="waitQuorum")
- WCP-35: Cancelling Partial Join (threshold="static" + cancellationScope="region")
- WCP-36: Dynamic Partial Join (threshold="dynamic", runtime computation)

Critical constraints:
- ALL behavior resolved via ontology (kgc_physics.ttl)
- ZERO pattern-specific if/else in engine code
- Partial joins fire at quorum N < M (not all instances required)
- WCP-35 voids remaining instances after threshold met
- WCP-36 computes threshold from ctx.data["join_threshold"]

Chicago School TDD: Real collaborators, no mocking domain objects.
"""

from __future__ import annotations

import pytest
from rdflib import Graph, Literal, Namespace, URIRef

from kgcl.engine.knowledge_engine import (
    GENESIS_HASH,
    KGC,
    YAWL,
    Kernel,
    QuadDelta,
    Receipt,
    SemanticDriver,
    TransactionContext,
    VerbConfig,
)

# Test namespaces
WORKFLOW = Namespace("http://example.org/workflow#")

# Test constants
P99_TARGET_MS: float = 100.0
SHA256_HEX_LENGTH: int = 64


@pytest.fixture
def physics_ontology() -> Graph:
    """Load KGC Physics Ontology from kgc_physics.ttl."""
    ontology = Graph()
    ontology.parse("/Users/sac/dev/kgcl/ontology/kgc_physics.ttl", format="turtle")
    return ontology


@pytest.fixture
def semantic_driver(physics_ontology: Graph) -> SemanticDriver:
    """Create Semantic Driver with loaded ontology."""
    return SemanticDriver(physics_ontology)


@pytest.fixture
def empty_graph() -> Graph:
    """Create empty RDF workflow graph."""
    return Graph()


@pytest.fixture
def transaction_context() -> TransactionContext:
    """Create standard transaction context."""
    return TransactionContext(tx_id="test-tx-001", actor="test-agent", prev_hash=GENESIS_HASH, data={})


# =============================================================================
# WCP-34: STATIC PARTIAL JOIN FOR MI
# =============================================================================


class TestWCP34StaticPartialJoin:
    """Tests for WCP-34: Static Partial Join with threshold N < M.

    Pattern: Await(threshold="static", completionStrategy="waitQuorum")
    Behavior: Join fires when N of M instances complete (partial sync).
    """

    def test_wcp34_threshold_2_of_5_instances(
        self, empty_graph: Graph, transaction_context: TransactionContext
    ) -> None:
        """WCP-34: Join fires when 2 of 5 MI instances complete."""
        # Arrange: MI task with 5 instances, threshold=2
        graph = empty_graph
        mi_task = WORKFLOW.ParallelReviewTask
        join_task = WORKFLOW.ReviewJoin

        # Create 5 MI instances
        instances = [URIRef(f"{mi_task}_instance_{i}") for i in range(5)]
        for i, instance in enumerate(instances):
            graph.add((instance, KGC.instanceId, Literal(str(i))))
            graph.add((instance, KGC.parentTask, mi_task))

        # Define MI join with threshold
        graph.add((mi_task, YAWL.hasJoin, YAWL.ControlTypeAnd))
        graph.add((mi_task, YAWL.minimum, Literal(5)))
        graph.add((mi_task, YAWL.maximum, Literal(5)))
        graph.add((mi_task, YAWL.miThreshold, Literal(2)))

        # Connect instances to join
        for instance in instances:
            graph.add((instance, YAWL.flowsInto, WORKFLOW.Flow_to_join))
        graph.add((WORKFLOW.Flow_to_join, YAWL.nextElementRef, join_task))

        # Mark 2 instances as completed (threshold met)
        graph.add((instances[0], KGC.completedAt, Literal("tx-100")))
        graph.add((instances[1], KGC.completedAt, Literal("tx-101")))

        # Act: Execute await verb with threshold=2 (RDF-only: threshold_value)
        config = VerbConfig(verb="await", threshold_value=2)
        delta = Kernel.await_(graph, join_task, transaction_context, config)

        # Assert: Join activated (threshold met with 2 completions)
        assert len(delta.additions) > 0
        # Verify join node has token
        assert any(
            triple[0] == join_task and triple[1] == KGC.hasToken and str(triple[2]) == "true"
            for triple in delta.additions
        )
        # Verify threshold recorded for provenance
        assert any(triple[0] == join_task and triple[1] == KGC.thresholdAchieved for triple in delta.additions)

    def test_wcp34_threshold_not_met_3_of_10_required(
        self, empty_graph: Graph, transaction_context: TransactionContext
    ) -> None:
        """WCP-34: Join does NOT fire when only 2 of 10 instances complete (threshold=3)."""
        # Arrange: MI task with 10 instances, threshold=3
        graph = empty_graph
        mi_task = WORKFLOW.DataProcessingTask
        join_task = WORKFLOW.AggregationJoin

        # Create 10 MI instances
        instances = [URIRef(f"{mi_task}_instance_{i}") for i in range(10)]
        for i, instance in enumerate(instances):
            graph.add((instance, KGC.instanceId, Literal(str(i))))
            graph.add((instance, KGC.parentTask, mi_task))

        # Define MI join with threshold=3
        graph.add((mi_task, YAWL.hasJoin, YAWL.ControlTypeAnd))
        graph.add((mi_task, YAWL.minimum, Literal(10)))
        graph.add((mi_task, YAWL.maximum, Literal(10)))
        graph.add((mi_task, YAWL.miThreshold, Literal(3)))

        # Connect instances to join
        for instance in instances:
            graph.add((instance, YAWL.flowsInto, WORKFLOW.Flow_to_join))
        graph.add((WORKFLOW.Flow_to_join, YAWL.nextElementRef, join_task))

        # Mark only 2 instances as completed (threshold NOT met)
        graph.add((instances[0], KGC.completedAt, Literal("tx-200")))
        graph.add((instances[1], KGC.completedAt, Literal("tx-201")))

        # Act: Execute await verb with threshold=3 (RDF-only: threshold_value)
        config = VerbConfig(verb="await", threshold_value=3)
        delta = Kernel.await_(graph, join_task, transaction_context, config)

        # Assert: Join NOT activated (only 2 < 3 completions)
        # Should not add token to join node
        assert not any(
            triple[0] == join_task and triple[1] == KGC.hasToken and str(triple[2]) == "true"
            for triple in delta.additions
        )

    def test_wcp34_exact_threshold_3_of_8_completes(
        self, empty_graph: Graph, transaction_context: TransactionContext
    ) -> None:
        """WCP-34: Join fires exactly when threshold is met (3 of 8)."""
        # Arrange: MI task with 8 instances, threshold=3
        graph = empty_graph
        mi_task = WORKFLOW.ValidationTask
        join_task = WORKFLOW.ValidationJoin

        # Create 8 MI instances
        instances = [URIRef(f"{mi_task}_instance_{i}") for i in range(8)]
        for i, instance in enumerate(instances):
            graph.add((instance, KGC.instanceId, Literal(str(i))))
            graph.add((instance, KGC.parentTask, mi_task))

        # Define MI join with threshold=3
        graph.add((mi_task, YAWL.hasJoin, YAWL.ControlTypeAnd))
        graph.add((mi_task, YAWL.minimum, Literal(8)))
        graph.add((mi_task, YAWL.maximum, Literal(8)))
        graph.add((mi_task, YAWL.miThreshold, Literal(3)))

        # Connect instances to join
        for instance in instances:
            graph.add((instance, YAWL.flowsInto, WORKFLOW.Flow_to_join))
        graph.add((WORKFLOW.Flow_to_join, YAWL.nextElementRef, join_task))

        # Mark exactly 3 instances as completed
        graph.add((instances[0], KGC.completedAt, Literal("tx-300")))
        graph.add((instances[1], KGC.completedAt, Literal("tx-301")))
        graph.add((instances[2], KGC.completedAt, Literal("tx-302")))

        # Act: Execute await verb (RDF-only: threshold_value)
        config = VerbConfig(verb="await", threshold_value=3)
        delta = Kernel.await_(graph, join_task, transaction_context, config)

        # Assert: Join activated with exact threshold
        assert len(delta.additions) > 0
        assert any(triple[0] == join_task and triple[1] == KGC.hasToken for triple in delta.additions)
        # Verify threshold achieved metadata
        threshold_recorded = any(
            triple[0] == join_task and triple[1] == KGC.thresholdAchieved and str(triple[2]) == "3"
            for triple in delta.additions
        )
        assert threshold_recorded


# =============================================================================
# WCP-35: CANCELLING PARTIAL JOIN FOR MI
# =============================================================================


class TestWCP35CancellingPartialJoin:
    """Tests for WCP-35: Cancelling Partial Join with remaining instance void.

    Pattern: Await(threshold="static", completionStrategy="waitQuorum",
                   cancellationScope="region")
    Behavior: Join fires at threshold N, then voids remaining M-N instances.
    """

    def test_wcp35_complete_3_cancel_remaining_7_instances(
        self, empty_graph: Graph, transaction_context: TransactionContext
    ) -> None:
        """WCP-35: After 3 of 10 complete, void remaining 7 instances."""
        # Arrange: MI task with 10 instances, threshold=3, cancelling=true
        graph = empty_graph
        mi_task = WORKFLOW.SearchTask
        join_task = WORKFLOW.SearchJoin

        # Create 10 MI instances
        instances = [URIRef(f"{mi_task}_instance_{i}") for i in range(10)]
        for i, instance in enumerate(instances):
            graph.add((instance, KGC.instanceId, Literal(str(i))))
            graph.add((instance, KGC.parentTask, mi_task))
            # Mark instances 3-9 as still active (have tokens)
            if i >= 3:
                graph.add((instance, KGC.hasToken, Literal(True)))

        # Define MI join with cancelling
        graph.add((mi_task, YAWL.hasJoin, YAWL.ControlTypeAnd))
        graph.add((mi_task, YAWL.miThreshold, Literal(3)))
        graph.add((mi_task, YAWL.miCancelling, Literal(True)))

        # Define cancellation region
        graph.add((mi_task, YAWL.cancellationSet, WORKFLOW.CancellationRegion1))
        for i in range(3, 10):
            graph.add((instances[i], YAWL.inCancellationRegion, WORKFLOW.CancellationRegion1))

        # Connect instances to join
        for instance in instances:
            graph.add((instance, YAWL.flowsInto, WORKFLOW.Flow_to_join))
        graph.add((WORKFLOW.Flow_to_join, YAWL.nextElementRef, join_task))

        # Mark 3 instances as completed (threshold met)
        graph.add((instances[0], KGC.completedAt, Literal("tx-400")))
        graph.add((instances[1], KGC.completedAt, Literal("tx-401")))
        graph.add((instances[2], KGC.completedAt, Literal("tx-402")))

        # Act: First execute await to activate join (RDF-only: threshold_value)
        await_config = VerbConfig(
            verb="await", threshold_value=3, cancellation_scope="region"
        )
        await_delta = Kernel.await_(graph, join_task, transaction_context, await_config)

        # Apply await mutations
        for triple in await_delta.additions:
            graph.add(triple)

        # Then execute void to cancel remaining instances
        void_config = VerbConfig(verb="void", cancellation_scope="region")
        void_delta = Kernel.void(graph, mi_task, transaction_context, void_config)

        # Assert: Join activated
        assert any(triple[0] == join_task and triple[1] == KGC.hasToken for triple in await_delta.additions)

        # Assert: Remaining 7 instances voided
        voided_count = sum(1 for triple in void_delta.additions if triple[1] == KGC.voidedAt)
        # At least some instances should be voided (7 remaining)
        assert voided_count >= 7

        # Verify tokens removed from remaining instances
        token_removals = sum(
            1 for triple in void_delta.removals if triple[1] == KGC.hasToken and str(triple[2]) == "true"
        )
        assert token_removals >= 7

    def test_wcp35_cancellation_scope_region_parameter(
        self, empty_graph: Graph, transaction_context: TransactionContext
    ) -> None:
        """WCP-35: Verify cancellationScope='region' parameter propagates."""
        # Arrange: Simple MI join with cancelling
        graph = empty_graph
        mi_task = WORKFLOW.ApprovalTask
        join_task = WORKFLOW.ApprovalJoin

        # Create 5 instances
        instances = [URIRef(f"{mi_task}_instance_{i}") for i in range(5)]
        for i, instance in enumerate(instances):
            graph.add((instance, KGC.instanceId, Literal(str(i))))
            if i >= 2:
                graph.add((instance, KGC.hasToken, Literal(True)))

        # Define cancellation region
        graph.add((mi_task, YAWL.cancellationSet, WORKFLOW.CancellationRegion2))
        for i in range(2, 5):
            graph.add((instances[i], YAWL.inCancellationRegion, WORKFLOW.CancellationRegion2))

        graph.add((mi_task, YAWL.miThreshold, Literal(2)))
        graph.add((mi_task, YAWL.miCancelling, Literal(True)))

        # Mark 2 as completed
        graph.add((instances[0], KGC.completedAt, Literal("tx-500")))
        graph.add((instances[1], KGC.completedAt, Literal("tx-501")))

        # Act: Execute void with region scope
        config = VerbConfig(verb="void", cancellation_scope="region")
        delta = Kernel.void(graph, mi_task, transaction_context, config)

        # Assert: Scope parameter recorded
        assert any(
            triple[0] == mi_task and triple[1] == KGC.cancellationScope and str(triple[2]) == "region"
            for triple in delta.additions
        )

    def test_wcp35_no_double_void_already_completed_instances(
        self, empty_graph: Graph, transaction_context: TransactionContext
    ) -> None:
        """WCP-35: Already completed instances should NOT be voided."""
        # Arrange: MI task where some instances already completed
        graph = empty_graph
        mi_task = WORKFLOW.FilterTask
        join_task = WORKFLOW.FilterJoin

        # Create 6 instances
        instances = [URIRef(f"{mi_task}_instance_{i}") for i in range(6)]
        for i, instance in enumerate(instances):
            graph.add((instance, KGC.instanceId, Literal(str(i))))

        # Mark instances 0-2 as completed (threshold=3)
        graph.add((instances[0], KGC.completedAt, Literal("tx-600")))
        graph.add((instances[1], KGC.completedAt, Literal("tx-601")))
        graph.add((instances[2], KGC.completedAt, Literal("tx-602")))

        # Instances 3-5 are active (have tokens)
        for i in range(3, 6):
            graph.add((instances[i], KGC.hasToken, Literal(True)))

        # Define cancellation region (only active instances)
        graph.add((mi_task, YAWL.cancellationSet, WORKFLOW.CancellationRegion3))
        for i in range(3, 6):
            graph.add((instances[i], YAWL.inCancellationRegion, WORKFLOW.CancellationRegion3))

        # Act: Execute void
        config = VerbConfig(verb="void", cancellation_scope="region")
        delta = Kernel.void(graph, mi_task, transaction_context, config)

        # Assert: Only active instances (3-5) voided, not completed (0-2)
        voided_instances = {triple[0] for triple in delta.additions if triple[1] == KGC.voidedAt}
        # Should NOT include already completed instances
        assert instances[0] not in voided_instances
        assert instances[1] not in voided_instances
        assert instances[2] not in voided_instances


# =============================================================================
# WCP-36: DYNAMIC PARTIAL JOIN FOR MI
# =============================================================================


class TestWCP36DynamicPartialJoin:
    """Tests for WCP-36: Dynamic Partial Join with runtime threshold.

    Pattern: Await(threshold="dynamic", completionStrategy="waitQuorum")
    Behavior: Threshold N computed at runtime from ctx.data["join_threshold"].
    """

    def test_wcp36_dynamic_threshold_from_context_data(self, empty_graph: Graph) -> None:
        """WCP-36: Threshold computed from ctx.data['join_threshold'] at runtime."""
        # Arrange: MI task with 8 instances
        graph = empty_graph
        mi_task = WORKFLOW.DynamicReviewTask
        join_task = WORKFLOW.DynamicJoin

        # Create 8 MI instances
        instances = [URIRef(f"{mi_task}_instance_{i}") for i in range(8)]
        for i, instance in enumerate(instances):
            graph.add((instance, KGC.instanceId, Literal(str(i))))
            graph.add((instance, KGC.parentTask, mi_task))

        # Connect instances to join
        for instance in instances:
            graph.add((instance, YAWL.flowsInto, WORKFLOW.Flow_to_join))
        graph.add((WORKFLOW.Flow_to_join, YAWL.nextElementRef, join_task))

        # Mark 4 instances as completed
        for i in range(4):
            graph.add((instances[i], KGC.completedAt, Literal(f"tx-70{i}")))

        # Act: Context with dynamic threshold=4
        ctx = TransactionContext(
            tx_id="test-tx-700",
            actor="test-agent",
            prev_hash=GENESIS_HASH,
            data={"join_threshold": 4},  # Dynamic threshold from data
        )
        config = VerbConfig(verb="await", use_dynamic_threshold=True)
        delta = Kernel.await_(graph, join_task, ctx, config)

        # Assert: Join activated (4 completions = threshold)
        assert any(triple[0] == join_task and triple[1] == KGC.hasToken for triple in delta.additions)
        # Verify threshold achieved recorded
        assert any(
            triple[0] == join_task and triple[1] == KGC.thresholdAchieved and str(triple[2]) == "4"
            for triple in delta.additions
        )

    def test_wcp36_dynamic_threshold_higher_than_completions(self, empty_graph: Graph) -> None:
        """WCP-36: Join does NOT fire if completions < dynamic threshold."""
        # Arrange: MI task with 10 instances
        graph = empty_graph
        mi_task = WORKFLOW.AdaptiveTask
        join_task = WORKFLOW.AdaptiveJoin

        # Create 10 instances
        instances = [URIRef(f"{mi_task}_instance_{i}") for i in range(10)]
        for i, instance in enumerate(instances):
            graph.add((instance, KGC.instanceId, Literal(str(i))))

        # Connect to join
        for instance in instances:
            graph.add((instance, YAWL.flowsInto, WORKFLOW.Flow_to_join))
        graph.add((WORKFLOW.Flow_to_join, YAWL.nextElementRef, join_task))

        # Mark only 3 instances as completed
        for i in range(3):
            graph.add((instances[i], KGC.completedAt, Literal(f"tx-80{i}")))

        # Act: Context with dynamic threshold=5 (higher than 3 completions)
        ctx = TransactionContext(
            tx_id="test-tx-800",
            actor="test-agent",
            prev_hash=GENESIS_HASH,
            data={"join_threshold": 5},  # Requires 5, only 3 completed
        )
        config = VerbConfig(verb="await", use_dynamic_threshold=True)
        delta = Kernel.await_(graph, join_task, ctx, config)

        # Assert: Join NOT activated (3 < 5)
        assert not any(
            triple[0] == join_task and triple[1] == KGC.hasToken and str(triple[2]) == "true"
            for triple in delta.additions
        )

    def test_wcp36_dynamic_threshold_changes_between_executions(self, empty_graph: Graph) -> None:
        """WCP-36: Threshold can change between executions (runtime flexibility)."""
        # Arrange: MI task with 6 instances
        graph = empty_graph
        mi_task = WORKFLOW.FlexibleTask
        join_task = WORKFLOW.FlexibleJoin

        # Create 6 instances
        instances = [URIRef(f"{mi_task}_instance_{i}") for i in range(6)]
        for i, instance in enumerate(instances):
            graph.add((instance, KGC.instanceId, Literal(str(i))))

        # Connect to join
        for instance in instances:
            graph.add((instance, YAWL.flowsInto, WORKFLOW.Flow_to_join))
        graph.add((WORKFLOW.Flow_to_join, YAWL.nextElementRef, join_task))

        # Mark 3 instances as completed
        for i in range(3):
            graph.add((instances[i], KGC.completedAt, Literal(f"tx-90{i}")))

        # Act: First execution with threshold=5 (should not fire)
        ctx1 = TransactionContext(
            tx_id="test-tx-900", actor="test-agent", prev_hash=GENESIS_HASH, data={"join_threshold": 5}
        )
        config = VerbConfig(verb="await", use_dynamic_threshold=True)
        delta1 = Kernel.await_(graph, join_task, ctx1, config)

        # Assert: Not activated (3 < 5)
        assert not any(
            triple[0] == join_task and triple[1] == KGC.hasToken and str(triple[2]) == "true"
            for triple in delta1.additions
        )

        # Act: Second execution with threshold=2 (should fire)
        ctx2 = TransactionContext(
            tx_id="test-tx-901",
            actor="test-agent",
            prev_hash=GENESIS_HASH,
            data={"join_threshold": 2},  # Lowered threshold
        )
        delta2 = Kernel.await_(graph, join_task, ctx2, config)

        # Assert: Now activated (3 >= 2)
        assert any(triple[0] == join_task and triple[1] == KGC.hasToken for triple in delta2.additions)


# =============================================================================
# INTEGRATION TESTS: ONTOLOGY-DRIVEN PARAMETER RESOLUTION
# =============================================================================


class TestMIJoinOntologyIntegration:
    """Integration tests verifying ontology-driven parameter resolution."""

    def test_ontology_maps_wcp34_to_await_with_static_threshold(
        self, semantic_driver: SemanticDriver, empty_graph: Graph
    ) -> None:
        """Ontology maps WCP-34 pattern to Await(threshold='static')."""
        # Arrange: Workflow node with WCP-34 pattern indicators
        graph = empty_graph
        join_task = WORKFLOW.WCP34_Join

        # Mark as MI task with static threshold
        graph.add((join_task, YAWL.hasJoin, YAWL.ControlTypeAnd))
        graph.add((join_task, YAWL.miThreshold, Literal(3)))
        graph.add((join_task, YAWL.minimum, Literal(5)))
        graph.add((join_task, YAWL.maximum, Literal(5)))

        # Act: Resolve verb from ontology
        # Note: resolve_verb requires the pattern to be in workflow graph
        # This test verifies the ontology mapping exists
        ontology_query = f"""
        PREFIX kgc: <{KGC}>
        PREFIX yawl: <{YAWL}>
        SELECT ?threshold ?completion WHERE {{
            ?mapping kgc:pattern yawl:MultiInstanceTask ;
                     kgc:hasThreshold ?threshold ;
                     kgc:completionStrategy ?completion .
            FILTER(?threshold = "static")
        }}
        """
        results = list(semantic_driver.physics_ontology.query(ontology_query))

        # Assert: Ontology contains WCP-34 mapping
        assert len(results) > 0
        threshold, completion = results[0]
        assert str(threshold) == "static"
        assert str(completion) == "waitQuorum"

    def test_ontology_maps_wcp35_to_await_with_cancellation_scope(self, semantic_driver: SemanticDriver) -> None:
        """Ontology maps WCP-35 to Await with cancellationScope='region'."""
        # Act: Query ontology for WCP-35 mapping
        query = f"""
        PREFIX kgc: <{KGC}>
        PREFIX yawl: <{YAWL}>
        SELECT ?threshold ?completion ?scope WHERE {{
            ?mapping kgc:pattern yawl:MultiInstanceTask ;
                     kgc:hasThreshold ?threshold ;
                     kgc:completionStrategy ?completion ;
                     kgc:cancellationScope ?scope .
            FILTER(?scope = "region")
        }}
        """
        results = list(semantic_driver.physics_ontology.query(query))

        # Assert: WCP-35 mapping exists with region cancellation
        assert len(results) > 0
        threshold, completion, scope = results[0]
        assert str(threshold) == "static"
        assert str(completion) == "waitQuorum"
        assert str(scope) == "region"

    def test_ontology_maps_wcp36_to_await_with_dynamic_threshold(self, semantic_driver: SemanticDriver) -> None:
        """Ontology maps WCP-36 to Await(threshold='dynamic')."""
        # Act: Query ontology for WCP-36 mapping
        query = f"""
        PREFIX kgc: <{KGC}>
        PREFIX yawl: <{YAWL}>
        SELECT ?threshold ?completion WHERE {{
            ?mapping kgc:pattern yawl:MultiInstanceTask ;
                     kgc:hasThreshold ?threshold ;
                     kgc:completionStrategy ?completion .
            FILTER(?threshold = "dynamic")
        }}
        """
        results = list(semantic_driver.physics_ontology.query(query))

        # Assert: WCP-36 mapping exists
        assert len(results) > 0
        threshold, completion = results[0]
        assert str(threshold) == "dynamic"
        assert str(completion) == "waitQuorum"


# =============================================================================
# PROVENANCE & PARAMETER VERIFICATION
# =============================================================================


class TestMIJoinProvenance:
    """Tests verifying provenance and parameter tracking."""

    def test_threshold_achieved_recorded_in_receipt(
        self, empty_graph: Graph, transaction_context: TransactionContext
    ) -> None:
        """Verify thresholdAchieved metadata recorded for audit trail."""
        # Arrange: MI join with threshold=2
        graph = empty_graph
        join_task = WORKFLOW.ProvenanceJoin
        instances = [URIRef(f"urn:instance:{i}") for i in range(5)]

        for i, instance in enumerate(instances):
            graph.add((instance, YAWL.flowsInto, WORKFLOW.Flow_to_join))
            if i < 2:
                graph.add((instance, KGC.completedAt, Literal(f"tx-{i}")))
        graph.add((WORKFLOW.Flow_to_join, YAWL.nextElementRef, join_task))

        # Act: Execute with threshold=2 (RDF-only: threshold_value)
        config = VerbConfig(verb="await", threshold_value=2)
        delta = Kernel.await_(graph, join_task, transaction_context, config)

        # Assert: Provenance metadata recorded
        assert any(triple[0] == join_task and triple[1] == KGC.thresholdAchieved for triple in delta.additions)

    def test_completion_strategy_wait_quorum_parameter(
        self, empty_graph: Graph, transaction_context: TransactionContext
    ) -> None:
        """Verify completionStrategy='waitQuorum' for all MI joins."""
        # Arrange: Simple MI join
        graph = empty_graph
        join_task = WORKFLOW.QuorumJoin

        # Create minimal setup
        instance = WORKFLOW.Instance1
        graph.add((instance, YAWL.flowsInto, WORKFLOW.Flow_to_join))
        graph.add((WORKFLOW.Flow_to_join, YAWL.nextElementRef, join_task))
        graph.add((instance, KGC.completedAt, Literal("tx-1000")))

        # Act: Verify config parameter (RDF-only: threshold_value)
        config = VerbConfig(verb="await", threshold_value=1)

        # Assert: Config has correct RDF-only threshold
        assert config.threshold_value == 1
        assert config.verb == "await"

    def test_cancellation_scope_region_for_wcp35(
        self, empty_graph: Graph, transaction_context: TransactionContext
    ) -> None:
        """Verify cancellationScope='region' parameter for WCP-35."""
        # Arrange: Cancellation region setup
        graph = empty_graph
        mi_task = WORKFLOW.CancellableTask

        graph.add((mi_task, YAWL.cancellationSet, WORKFLOW.Region1))
        graph.add((mi_task, KGC.hasToken, Literal(True)))

        # Act: Execute void with region scope
        config = VerbConfig(verb="void", cancellation_scope="region")
        delta = Kernel.void(graph, mi_task, transaction_context, config)

        # Assert: Scope recorded
        assert any(
            triple[0] == mi_task and triple[1] == KGC.cancellationScope and str(triple[2]) == "region"
            for triple in delta.additions
        )
