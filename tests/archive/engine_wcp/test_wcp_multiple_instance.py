"""Comprehensive tests for YAWL Multiple Instance Patterns (WCP 12-15).

Tests verify the Multiple Instance behavior of the COPY verb with different
cardinality and instanceBinding parameters:

WCP-12: MI without Synchronization - Copy(cardinality="dynamic", instanceBinding="data")
WCP-13: MI with Design-Time Knowledge - Copy(cardinality="static", instanceBinding="index")
WCP-14: MI with Runtime Knowledge - Copy(cardinality="dynamic", instanceBinding="data")
WCP-15: MI without Prior Knowledge - Copy(cardinality="incremental", instanceBinding="data")

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
    """Load KGC physics ontology from file."""
    ontology = Graph()
    ontology.parse("ontology/core/kgc_physics.ttl", format="turtle")
    return ontology


@pytest.fixture
def empty_workflow() -> Graph:
    """Create empty workflow graph."""
    return Graph()


@pytest.fixture
def transaction_context() -> TransactionContext:
    """Create standard transaction context."""
    return TransactionContext(tx_id="test-tx-001", actor="test-agent", prev_hash=GENESIS_HASH, data={})


# =============================================================================
# WCP-12: Multiple Instance without Synchronization
# =============================================================================


class TestWcp12MultiInstanceNoSync:
    """Tests for WCP-12: MI without Synchronization.

    Pattern: Copy(cardinality="dynamic", instanceBinding="data")
    Behavior: Create N instances, no synchronization on completion.
    """

    def test_mi_no_sync_creates_dynamic_instances(
        self, empty_workflow: Graph, transaction_context: TransactionContext
    ) -> None:
        """WCP-12: Create N instances from runtime data without sync."""
        # Arrange: MI task with dynamic cardinality
        graph = empty_workflow
        mi_task = WORKFLOW.ProcessOrders
        next_task = WORKFLOW.ShipOrders

        # Set up MI task
        graph.add((mi_task, YAWL.flowsInto, WORKFLOW.Flow1))
        graph.add((WORKFLOW.Flow1, YAWL.nextElementRef, next_task))
        graph.add((mi_task, KGC.hasToken, Literal(True)))

        # Runtime data: list of 3 items to process
        ctx = TransactionContext(
            tx_id="tx-001", actor="system", prev_hash=GENESIS_HASH, data={"mi_items": ["order1", "order2", "order3"]}
        )

        config = VerbConfig(verb="copy", use_dynamic_cardinality=True, instance_binding="data")

        # Act: Copy verb with dynamic cardinality
        delta = Kernel.copy(graph, mi_task, ctx, config)

        # Assert: 3 instances created
        additions_with_tokens = [t for t in delta.additions if t[1] == KGC.hasToken]
        assert len(additions_with_tokens) == 3, "Should create 3 instances"

        # Verify instance URIs created
        instance_ids = [t for t in delta.additions if t[1] == KGC.instanceId]
        assert len(instance_ids) == 3, "Should have 3 instance IDs"

        # Verify data binding
        bound_data = [t for t in delta.additions if t[1] == KGC.boundData]
        assert len(bound_data) == 3, "Should bind data to 3 instances"

        # Verify token removed from parent
        assert (mi_task, KGC.hasToken, Literal(True)) in delta.removals

    def test_mi_no_sync_with_empty_data(self, empty_workflow: Graph, transaction_context: TransactionContext) -> None:
        """WCP-12: Handle empty MI data gracefully (fallback to topology)."""
        # Arrange: MI task with no runtime data
        graph = empty_workflow
        mi_task = WORKFLOW.ProcessBatch
        next_task = WORKFLOW.Finalize

        graph.add((mi_task, YAWL.flowsInto, WORKFLOW.Flow1))
        graph.add((WORKFLOW.Flow1, YAWL.nextElementRef, next_task))
        graph.add((mi_task, KGC.hasToken, Literal(True)))

        ctx = TransactionContext(
            tx_id="tx-002",
            actor="system",
            prev_hash=GENESIS_HASH,
            data={"mi_items": []},  # Empty list
        )

        config = VerbConfig(verb="copy", use_dynamic_cardinality=True, instance_binding="data")

        # Act: Copy with empty data
        delta = Kernel.copy(graph, mi_task, ctx, config)

        # Assert: Falls back to topology (single successor)
        additions_with_tokens = [t for t in delta.additions if t[1] == KGC.hasToken]
        assert len(additions_with_tokens) == 1, "Should fall back to topology"

    def test_mi_no_sync_instance_binding_data(
        self, empty_workflow: Graph, transaction_context: TransactionContext
    ) -> None:
        """WCP-12: Verify instanceBinding=data creates correct bindings."""
        # Arrange: MI task with specific data items
        graph = empty_workflow
        mi_task = WORKFLOW.ValidateItems
        next_task = WORKFLOW.Aggregate

        graph.add((mi_task, YAWL.flowsInto, WORKFLOW.Flow1))
        graph.add((WORKFLOW.Flow1, YAWL.nextElementRef, next_task))
        graph.add((mi_task, KGC.hasToken, Literal(True)))

        ctx = TransactionContext(
            tx_id="tx-003", actor="system", prev_hash=GENESIS_HASH, data={"mi_items": ["item_a", "item_b"]}
        )

        config = VerbConfig(verb="copy", use_dynamic_cardinality=True, instance_binding="data")

        # Act: Copy with data binding
        delta = Kernel.copy(graph, mi_task, ctx, config)

        # Assert: Each instance bound to correct data
        bound_data_triples = [t for t in delta.additions if t[1] == KGC.boundData]
        assert len(bound_data_triples) == 2, "Should bind 2 data items"

        # Verify data values preserved
        data_values = [str(t[2]) for t in bound_data_triples]
        assert "item_a" in data_values
        assert "item_b" in data_values


# =============================================================================
# WCP-13: Multiple Instance with Design-Time Knowledge
# =============================================================================


class TestWcp13MultiInstanceDesignTime:
    """Tests for WCP-13: MI with Design-Time Knowledge.

    Pattern: Copy(cardinality="static", instanceBinding="index")
    Behavior: N is known at design time (static cardinality).
    """

    def test_mi_design_time_static_cardinality(
        self, empty_workflow: Graph, transaction_context: TransactionContext
    ) -> None:
        """WCP-13: Create N instances where N is fixed at design time."""
        # Arrange: MI task with static cardinality
        graph = empty_workflow
        mi_task = WORKFLOW.ProcessTriplicate
        next_task = WORKFLOW.Merge

        graph.add((mi_task, YAWL.flowsInto, WORKFLOW.Flow1))
        graph.add((WORKFLOW.Flow1, YAWL.nextElementRef, next_task))
        graph.add((mi_task, KGC.hasToken, Literal(True)))

        # Static cardinality: min=max=5
        graph.add((mi_task, YAWL.minimum, Literal(5)))
        graph.add((mi_task, YAWL.maximum, Literal(5)))

        ctx = TransactionContext(tx_id="tx-004", actor="system", prev_hash=GENESIS_HASH, data={})

        config = VerbConfig(verb="copy", cardinality_value=-2, instance_binding="index")

        # Act: Copy with static cardinality
        delta = Kernel.copy(graph, mi_task, ctx, config)

        # Assert: Exactly 5 instances created
        additions_with_tokens = [t for t in delta.additions if t[1] == KGC.hasToken]
        assert len(additions_with_tokens) == 5, "Should create exactly 5 instances"

        # Verify instance IDs (0-4)
        instance_ids = [t for t in delta.additions if t[1] == KGC.instanceId]
        assert len(instance_ids) == 5, "Should have 5 instance IDs"

    def test_mi_design_time_index_binding(self, empty_workflow: Graph, transaction_context: TransactionContext) -> None:
        """WCP-13: Verify instanceBinding=index creates sequential IDs."""
        # Arrange: MI task with static N
        graph = empty_workflow
        mi_task = WORKFLOW.ParallelReview
        next_task = WORKFLOW.Decision

        graph.add((mi_task, YAWL.flowsInto, WORKFLOW.Flow1))
        graph.add((WORKFLOW.Flow1, YAWL.nextElementRef, next_task))
        graph.add((mi_task, KGC.hasToken, Literal(True)))

        # Static cardinality: 3 reviewers
        graph.add((mi_task, YAWL.minimum, Literal(3)))
        graph.add((mi_task, YAWL.maximum, Literal(3)))

        ctx = TransactionContext(tx_id="tx-005", actor="system", prev_hash=GENESIS_HASH, data={})

        config = VerbConfig(verb="copy", cardinality_value=-2, instance_binding="index")

        # Act: Copy with index binding
        delta = Kernel.copy(graph, mi_task, ctx, config)

        # Assert: Instance IDs are sequential (0, 1, 2)
        instance_id_triples = [t for t in delta.additions if t[1] == KGC.instanceId]
        instance_ids = [str(t[2]) for t in instance_id_triples]
        assert "0" in instance_ids
        assert "1" in instance_ids
        assert "2" in instance_ids

    def test_mi_design_time_no_runtime_data_required(
        self, empty_workflow: Graph, transaction_context: TransactionContext
    ) -> None:
        """WCP-13: Static cardinality doesn't require runtime data."""
        # Arrange: MI task with no context data
        graph = empty_workflow
        mi_task = WORKFLOW.ThreeWayApproval
        next_task = WORKFLOW.Execute

        graph.add((mi_task, YAWL.flowsInto, WORKFLOW.Flow1))
        graph.add((WORKFLOW.Flow1, YAWL.nextElementRef, next_task))
        graph.add((mi_task, KGC.hasToken, Literal(True)))

        # Static cardinality: always 3
        graph.add((mi_task, YAWL.minimum, Literal(3)))
        graph.add((mi_task, YAWL.maximum, Literal(3)))

        # Empty context data (should not matter)
        ctx = TransactionContext(tx_id="tx-006", actor="system", prev_hash=GENESIS_HASH, data={})

        config = VerbConfig(verb="copy", cardinality_value=-2, instance_binding="index")

        # Act: Copy without runtime data
        delta = Kernel.copy(graph, mi_task, ctx, config)

        # Assert: Creates 3 instances anyway
        additions_with_tokens = [t for t in delta.additions if t[1] == KGC.hasToken]
        assert len(additions_with_tokens) == 3, "Should create 3 instances regardless of data"


# =============================================================================
# WCP-14: Multiple Instance with Runtime Knowledge
# =============================================================================


class TestWcp14MultiInstanceRuntime:
    """Tests for WCP-14: MI with Runtime Knowledge.

    Pattern: Copy(cardinality="dynamic", instanceBinding="data")
    Behavior: N is determined from runtime data at execution.
    """

    def test_mi_runtime_dynamic_cardinality_from_data(
        self, empty_workflow: Graph, transaction_context: TransactionContext
    ) -> None:
        """WCP-14: N determined from runtime data (list length)."""
        # Arrange: MI task with runtime cardinality
        graph = empty_workflow
        mi_task = WORKFLOW.ProcessDocuments
        next_task = WORKFLOW.Archive

        graph.add((mi_task, YAWL.flowsInto, WORKFLOW.Flow1))
        graph.add((WORKFLOW.Flow1, YAWL.nextElementRef, next_task))
        graph.add((mi_task, KGC.hasToken, Literal(True)))

        # Mark as MI with runtime input
        graph.add((mi_task, YAWL.miDataInput, Literal("documents")))

        # Runtime data: 4 documents
        ctx = TransactionContext(
            tx_id="tx-007", actor="system", prev_hash=GENESIS_HASH, data={"mi_items": ["doc1", "doc2", "doc3", "doc4"]}
        )

        config = VerbConfig(verb="copy", use_dynamic_cardinality=True, instance_binding="data")

        # Act: Copy with runtime cardinality
        delta = Kernel.copy(graph, mi_task, ctx, config)

        # Assert: 4 instances created
        additions_with_tokens = [t for t in delta.additions if t[1] == KGC.hasToken]
        assert len(additions_with_tokens) == 4, "Should create 4 instances from runtime data"

    def test_mi_runtime_variable_instance_count(
        self, empty_workflow: Graph, transaction_context: TransactionContext
    ) -> None:
        """WCP-14: Handle variable N across executions."""
        # Arrange: Same task, different data sizes
        graph = empty_workflow
        mi_task = WORKFLOW.SendNotifications
        next_task = WORKFLOW.Done

        graph.add((mi_task, YAWL.flowsInto, WORKFLOW.Flow1))
        graph.add((WORKFLOW.Flow1, YAWL.nextElementRef, next_task))
        graph.add((mi_task, KGC.hasToken, Literal(True)))

        config = VerbConfig(verb="copy", use_dynamic_cardinality=True, instance_binding="data")

        # First execution: 2 items
        ctx1 = TransactionContext(
            tx_id="tx-008a", actor="system", prev_hash=GENESIS_HASH, data={"mi_items": ["user1", "user2"]}
        )
        delta1 = Kernel.copy(graph, mi_task, ctx1, config)
        tokens1 = [t for t in delta1.additions if t[1] == KGC.hasToken]
        assert len(tokens1) == 2, "First execution: 2 instances"

        # Reset graph for second execution
        graph.remove((mi_task, KGC.hasToken, Literal(True)))
        graph.add((mi_task, KGC.hasToken, Literal(True)))

        # Second execution: 7 items
        ctx2 = TransactionContext(
            tx_id="tx-008b",
            actor="system",
            prev_hash=GENESIS_HASH,
            data={"mi_items": ["u1", "u2", "u3", "u4", "u5", "u6", "u7"]},
        )
        delta2 = Kernel.copy(graph, mi_task, ctx2, config)
        tokens2 = [t for t in delta2.additions if t[1] == KGC.hasToken]
        assert len(tokens2) == 7, "Second execution: 7 instances"

    def test_mi_runtime_data_binding_preserves_values(
        self, empty_workflow: Graph, transaction_context: TransactionContext
    ) -> None:
        """WCP-14: Each instance bound to correct data element."""
        # Arrange: MI task with distinct data values
        graph = empty_workflow
        mi_task = WORKFLOW.TransformRecords
        next_task = WORKFLOW.Consolidate

        graph.add((mi_task, YAWL.flowsInto, WORKFLOW.Flow1))
        graph.add((WORKFLOW.Flow1, YAWL.nextElementRef, next_task))
        graph.add((mi_task, KGC.hasToken, Literal(True)))

        ctx = TransactionContext(
            tx_id="tx-009", actor="system", prev_hash=GENESIS_HASH, data={"mi_items": ["alpha", "beta", "gamma"]}
        )

        config = VerbConfig(verb="copy", use_dynamic_cardinality=True, instance_binding="data")

        # Act: Copy with data binding
        delta = Kernel.copy(graph, mi_task, ctx, config)

        # Assert: Each data value bound to instance
        bound_data_triples = [t for t in delta.additions if t[1] == KGC.boundData]
        data_values = [str(t[2]) for t in bound_data_triples]

        assert "alpha" in data_values
        assert "beta" in data_values
        assert "gamma" in data_values
        assert len(data_values) == 3


# =============================================================================
# WCP-15: Multiple Instance without Prior Knowledge
# =============================================================================


class TestWcp15MultiInstanceNoPrior:
    """Tests for WCP-15: MI without Prior Knowledge.

    Pattern: Copy(cardinality="incremental", instanceBinding="data")
    Behavior: Instances created incrementally during execution.
    """

    def test_mi_no_prior_incremental_creation(
        self, empty_workflow: Graph, transaction_context: TransactionContext
    ) -> None:
        """WCP-15: Create one instance at a time incrementally."""
        # Arrange: MI task with incremental creation
        graph = empty_workflow
        mi_task = WORKFLOW.StreamProcessor
        next_task = WORKFLOW.Collector

        graph.add((mi_task, YAWL.flowsInto, WORKFLOW.Flow1))
        graph.add((WORKFLOW.Flow1, YAWL.nextElementRef, next_task))
        graph.add((mi_task, KGC.hasToken, Literal(True)))

        # Mark as dynamic creation mode
        graph.add((mi_task, YAWL.miCreationMode, YAWL.Dynamic))

        ctx = TransactionContext(tx_id="tx-010", actor="system", prev_hash=GENESIS_HASH, data={})

        config = VerbConfig(verb="copy", cardinality_value=-3, instance_binding="data")

        # Act: Copy with incremental cardinality
        delta = Kernel.copy(graph, mi_task, ctx, config)

        # Assert: Only 1 instance created
        additions_with_tokens = [t for t in delta.additions if t[1] == KGC.hasToken]
        assert len(additions_with_tokens) == 1, "Should create exactly 1 instance incrementally"

        # Verify instance ID = 0 (first instance)
        instance_ids = [t for t in delta.additions if t[1] == KGC.instanceId]
        assert len(instance_ids) == 1
        assert str(instance_ids[0][2]) == "0", "First instance should have ID 0"

    def test_mi_no_prior_tracks_instance_count(
        self, empty_workflow: Graph, transaction_context: TransactionContext
    ) -> None:
        """WCP-15: Subsequent calls create next instance (1, 2, 3...)."""
        # Arrange: MI task for incremental creation
        graph = empty_workflow
        mi_task = WORKFLOW.EventHandler
        next_task = WORKFLOW.Aggregator

        graph.add((mi_task, YAWL.flowsInto, WORKFLOW.Flow1))
        graph.add((WORKFLOW.Flow1, YAWL.nextElementRef, next_task))
        graph.add((mi_task, KGC.hasToken, Literal(True)))

        graph.add((mi_task, YAWL.miCreationMode, YAWL.Dynamic))

        config = VerbConfig(verb="copy", cardinality_value=-3, instance_binding="data")

        # First call: creates instance 0
        ctx1 = TransactionContext(tx_id="tx-011a", actor="system", prev_hash=GENESIS_HASH, data={})
        delta1 = Kernel.copy(graph, mi_task, ctx1, config)
        instance_id_1 = [t for t in delta1.additions if t[1] == KGC.instanceId][0]
        assert str(instance_id_1[2]) == "0", "First instance: ID 0"

        # Simulate first instance in graph
        graph.remove((mi_task, KGC.hasToken, Literal(True)))
        graph.add((mi_task, KGC.hasToken, Literal(True)))
        first_instance_uri = instance_id_1[0]
        graph.add((first_instance_uri, KGC.parentTask, mi_task))

        # Second call: creates instance 1
        ctx2 = TransactionContext(tx_id="tx-011b", actor="system", prev_hash=GENESIS_HASH, data={})
        delta2 = Kernel.copy(graph, mi_task, ctx2, config)
        instance_id_2 = [t for t in delta2.additions if t[1] == KGC.instanceId][0]
        assert str(instance_id_2[2]) == "1", "Second instance: ID 1"

    def test_mi_no_prior_parent_task_link(self, empty_workflow: Graph, transaction_context: TransactionContext) -> None:
        """WCP-15: Each instance linked to parent task."""
        # Arrange: MI task with incremental mode
        graph = empty_workflow
        mi_task = WORKFLOW.TaskDispatcher
        next_task = WORKFLOW.Reducer

        graph.add((mi_task, YAWL.flowsInto, WORKFLOW.Flow1))
        graph.add((WORKFLOW.Flow1, YAWL.nextElementRef, next_task))
        graph.add((mi_task, KGC.hasToken, Literal(True)))

        graph.add((mi_task, YAWL.miCreationMode, YAWL.Dynamic))

        ctx = TransactionContext(tx_id="tx-012", actor="system", prev_hash=GENESIS_HASH, data={})

        config = VerbConfig(verb="copy", cardinality_value=-3, instance_binding="data")

        # Act: Create instance
        delta = Kernel.copy(graph, mi_task, ctx, config)

        # Assert: Instance has parentTask link
        parent_links = [t for t in delta.additions if t[1] == KGC.parentTask]
        assert len(parent_links) == 1, "Should have 1 parent link"
        assert parent_links[0][2] == mi_task, "Parent should be MI task"


# =============================================================================
# Integration Tests: MI Patterns with Semantic Driver
# =============================================================================


class TestMultiInstanceIntegration:
    """Integration tests for MI patterns using Kernel directly."""

    def test_kernel_copy_with_dynamic_cardinality(
        self, empty_workflow: Graph, transaction_context: TransactionContext
    ) -> None:
        """Integration: Kernel.copy with dynamic cardinality from config."""
        # Arrange: Workflow with MI task
        graph = empty_workflow
        mi_task = WORKFLOW.MITask
        next_task = WORKFLOW.Continue

        graph.add((mi_task, YAWL.flowsInto, WORKFLOW.Flow1))
        graph.add((WORKFLOW.Flow1, YAWL.nextElementRef, next_task))
        graph.add((mi_task, KGC.hasToken, Literal(True)))

        ctx = TransactionContext(
            tx_id="tx-int-001", actor="system", prev_hash=GENESIS_HASH, data={"mi_items": ["a", "b", "c"]}
        )

        config = VerbConfig(verb="copy", use_dynamic_cardinality=True, instance_binding="data")

        # Act: Execute copy through kernel
        delta = Kernel.copy(graph, mi_task, ctx, config)

        # Assert: 3 instances created
        tokens = [t for t in delta.additions if t[1] == KGC.hasToken]
        assert len(tokens) == 3, "Should create 3 instances"

        # Verify provenance in receipt-like structure
        assert len(delta.additions) > 0
        assert len(delta.removals) == 1

    def test_kernel_copy_with_static_cardinality(
        self, empty_workflow: Graph, transaction_context: TransactionContext
    ) -> None:
        """Integration: Kernel.copy with static cardinality."""
        # Arrange: MI task with static N
        graph = empty_workflow
        mi_task = WORKFLOW.StaticMI
        next_task = WORKFLOW.Sync

        graph.add((mi_task, YAWL.flowsInto, WORKFLOW.Flow1))
        graph.add((WORKFLOW.Flow1, YAWL.nextElementRef, next_task))
        graph.add((mi_task, KGC.hasToken, Literal(True)))

        # Static cardinality metadata
        graph.add((mi_task, YAWL.minimum, Literal(4)))
        graph.add((mi_task, YAWL.maximum, Literal(4)))

        ctx = TransactionContext(tx_id="tx-int-002", actor="system", prev_hash=GENESIS_HASH, data={})

        config = VerbConfig(verb="copy", cardinality_value=-2, instance_binding="index")

        # Act: Execute through kernel
        delta = Kernel.copy(graph, mi_task, ctx, config)

        # Assert: 4 instances created
        tokens = [t for t in delta.additions if t[1] == KGC.hasToken]
        assert len(tokens) == 4, "Should create exactly 4 instances"

    def test_kernel_copy_with_incremental_cardinality(
        self, empty_workflow: Graph, transaction_context: TransactionContext
    ) -> None:
        """Integration: Kernel.copy with incremental cardinality."""
        # Arrange: MI task for incremental creation
        graph = empty_workflow
        mi_task = WORKFLOW.IncrementalMI
        next_task = WORKFLOW.Join

        graph.add((mi_task, YAWL.flowsInto, WORKFLOW.Flow1))
        graph.add((WORKFLOW.Flow1, YAWL.nextElementRef, next_task))
        graph.add((mi_task, KGC.hasToken, Literal(True)))

        ctx = TransactionContext(tx_id="tx-int-003", actor="system", prev_hash=GENESIS_HASH, data={})

        config = VerbConfig(verb="copy", cardinality_value=-3, instance_binding="data")

        # Act: Execute
        delta = Kernel.copy(graph, mi_task, ctx, config)

        # Assert: Only 1 instance created
        tokens = [t for t in delta.additions if t[1] == KGC.hasToken]
        assert len(tokens) == 1, "Should create 1 instance incrementally"

        # Verify parent link exists
        parent_links = [t for t in delta.additions if t[1] == KGC.parentTask]
        assert len(parent_links) == 1, "Should have parent link"
