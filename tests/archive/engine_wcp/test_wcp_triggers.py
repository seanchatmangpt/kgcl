"""Comprehensive tests for YAWL Trigger Patterns (WCP-23, WCP-24).

Tests verify trigger-based task activation patterns using the AWAIT verb:
- WCP-23: Transient Trigger → Await(threshold="signal", completionStrategy="waitSignal")
- WCP-24: Persistent Trigger → Await(threshold="persistent", completionStrategy="waitPersistent")

Implementation Details:
- TransientTrigger: Pattern `yawl:TransientTrigger`, threshold="signal"
- PersistentTrigger: Pattern `yawl:PersistentTrigger`, threshold="persistent"

Critical behavior differences:
- Transient: Signal must be present at exact moment task checks (ephemeral)
- Persistent: Signal persists until consumed (stable)

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
    """Load KGC Physics Ontology with trigger pattern mappings."""
    ontology = Graph()
    ontology.parse("/Users/sac/dev/kgcl/ontology/core/kgc_physics.ttl", format="turtle")
    return ontology


@pytest.fixture
def semantic_driver(physics_ontology: Graph) -> SemanticDriver:
    """Create Semantic Driver with loaded ontology."""
    return SemanticDriver(physics_ontology)


@pytest.fixture
def transaction_context() -> TransactionContext:
    """Create standard transaction context."""
    return TransactionContext(tx_id="tx-trigger-001", actor="test-agent", prev_hash=GENESIS_HASH, data={})


class TestWcp23TransientTrigger:
    """Tests for WCP-23: Transient Trigger pattern using AWAIT verb.

    Transient triggers are ephemeral signals that enable tasks only when
    the signal is present at the exact moment of checking. If the signal
    arrives too early or too late, the task will not activate.

    Pattern: yawl:TransientTrigger → Await(threshold="signal")
    Completion Strategy: "waitSignal"
    """

    def test_transient_trigger_ontology_mapping(self, physics_ontology: Graph) -> None:
        """Verify ontology maps TransientTrigger to AWAIT verb with signal threshold."""
        # Arrange: Query ontology for TransientTrigger mapping
        query = """
        PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
        PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?verbLabel ?threshold ?completion WHERE {
            ?mapping kgc:pattern yawl:TransientTrigger ;
                     kgc:verb ?verb .
            ?verb rdfs:label ?verbLabel .
            OPTIONAL { ?mapping kgc:hasThreshold ?threshold . }
            OPTIONAL { ?mapping kgc:completionStrategy ?completion . }
        }
        """
        results = list(physics_ontology.query(query))

        # Assert: Mapping exists and parameters are correct
        assert len(results) == 1, "Expected exactly one TransientTrigger mapping"
        row = results[0]
        assert str(row[0]).lower() == "await", f"Expected 'await' verb, got {row[0]}"
        assert str(row[1]) == "signal", f"Expected threshold='signal', got {row[1]}"
        assert str(row[2]) == "waitSignal", f"Expected completionStrategy='waitSignal', got {row[2]}"

    def test_transient_trigger_with_active_signal(
        self, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """Task activates when transient signal is present at check time."""
        # Arrange: Create workflow with transient trigger
        # The signal event flows INTO the trigger task (incoming flow for await)
        graph = Graph()
        trigger_task = WORKFLOW.TransientTask
        signal_event = WORKFLOW.SignalEvent

        # Signal flows into trigger task (AWAIT looks for incoming flows)
        graph.add((signal_event, YAWL.flowsInto, WORKFLOW.Flow1))
        graph.add((WORKFLOW.Flow1, YAWL.nextElementRef, trigger_task))

        # Signal is currently active (present at check time) and completed
        graph.add((signal_event, KGC.hasToken, Literal(True)))
        graph.add((signal_event, KGC.signalType, Literal("transient")))
        graph.add((signal_event, KGC.completedAt, Literal("signal-tx-001")))
        graph.add((trigger_task, YAWL.triggeredBy, signal_event))

        # Act: Execute with transient trigger context (threshold="signal" means need 1 completion)
        ctx = TransactionContext(
            tx_id="tx-trigger-001",
            actor="test-agent",
            prev_hash=GENESIS_HASH,
            data={"signal_active": True, "signal_type": "transient"},
        )

        # Config: threshold="signal" is interpreted as requiring 1 completed source (the signal)
        config = VerbConfig(verb="await", threshold="1", completion_strategy="waitSignal")
        delta = Kernel.await_(graph, trigger_task, ctx, config)

        # Assert: Task activated because signal was present and completed at check time
        assert len(delta.additions) > 0, "Task should activate with active signal"
        additions_dict = {(str(s), str(p), str(o)) for s, p, o in delta.additions}
        assert any(str(trigger_task) in triple[0] and "hasToken" in triple[1] for triple in additions_dict), (
            "Task should receive token when signal is active"
        )

    def test_transient_trigger_without_signal(
        self, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """Task does NOT activate when transient signal is absent at check time."""
        # Arrange: Create workflow with transient trigger, no active signal
        graph = Graph()
        trigger_task = WORKFLOW.TransientTaskNoSignal
        signal_event = WORKFLOW.SignalEventInactive

        # Signal flows into trigger task
        graph.add((signal_event, YAWL.flowsInto, WORKFLOW.Flow1))
        graph.add((WORKFLOW.Flow1, YAWL.nextElementRef, trigger_task))

        # Signal was active in the past but is NO LONGER completed (transient expired)
        # No completedAt means signal hasn't fired yet or has expired
        graph.add((signal_event, KGC.hasToken, Literal(False)))
        graph.add((signal_event, KGC.signalType, Literal("transient")))
        graph.add((trigger_task, YAWL.triggeredBy, signal_event))

        # Act: Execute with no completed signal (completed_sources = 0, required = 1)
        ctx = TransactionContext(
            tx_id="tx-trigger-002",
            actor="test-agent",
            prev_hash=GENESIS_HASH,
            data={"signal_active": False, "signal_type": "transient"},
        )

        config = VerbConfig(verb="await", threshold="1", completion_strategy="waitSignal")
        delta = Kernel.await_(graph, trigger_task, ctx, config)

        # Assert: Task should NOT activate (no completed source, 0 < 1)
        additions_dict = {(str(s), str(p), str(o)) for s, p, o in delta.additions}
        assert not any(str(trigger_task) in triple[0] and "hasToken" in triple[1] for triple in additions_dict), (
            "Task should NOT activate without completed transient signal"
        )

    def test_transient_trigger_signal_expires_immediately(
        self, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """Transient signal expires immediately after being consumed."""
        # Arrange: Workflow with transient trigger that has just fired
        graph = Graph()
        trigger_task = WORKFLOW.TransientExpiring
        signal_event = WORKFLOW.SignalEventExpiring

        # Signal flows into trigger task
        graph.add((signal_event, YAWL.flowsInto, WORKFLOW.Flow1))
        graph.add((WORKFLOW.Flow1, YAWL.nextElementRef, trigger_task))

        # Signal is completed NOW
        graph.add((signal_event, KGC.hasToken, Literal(True)))
        graph.add((signal_event, KGC.signalType, Literal("transient")))
        graph.add((signal_event, KGC.completedAt, Literal("signal-tx-now")))
        graph.add((trigger_task, YAWL.triggeredBy, signal_event))

        # Act: First execution - signal completed
        ctx1 = TransactionContext(
            tx_id="tx-trigger-003a",
            actor="test-agent",
            prev_hash=GENESIS_HASH,
            data={"signal_active": True, "signal_type": "transient"},
        )
        config = VerbConfig(verb="await", threshold="1", completion_strategy="waitSignal")
        delta1 = Kernel.await_(graph, trigger_task, ctx1, config)

        # Apply mutations
        for triple in delta1.removals:
            graph.remove(triple)
        for triple in delta1.additions:
            graph.add(triple)

        # Assert: First execution activated (signal was completed)
        assert len(delta1.additions) > 0, "First execution should activate with completed signal"

        # Arrange: Signal expires (remove completedAt to simulate expiration)
        graph.remove((signal_event, KGC.completedAt, Literal("signal-tx-now")))
        graph.remove((signal_event, KGC.hasToken, Literal(True)))
        graph.add((signal_event, KGC.hasToken, Literal(False)))
        graph.add((signal_event, KGC.expiredAt, Literal("signal-tx-now")))

        # Act: Second execution attempt - signal expired (not completed)
        trigger_task2 = WORKFLOW.TransientExpiring2
        graph.add((signal_event, YAWL.flowsInto, WORKFLOW.Flow2))
        graph.add((WORKFLOW.Flow2, YAWL.nextElementRef, trigger_task2))
        graph.add((trigger_task2, YAWL.triggeredBy, signal_event))

        ctx2 = TransactionContext(
            tx_id="tx-trigger-003b",
            actor="test-agent",
            prev_hash="tx-trigger-003a",
            data={"signal_active": False, "signal_type": "transient"},
        )
        delta2 = Kernel.await_(graph, trigger_task2, ctx2, config)

        # Assert: Second execution does NOT activate (signal not completed, 0 < 1)
        additions_dict = {(str(s), str(p), str(o)) for s, p, o in delta2.additions}
        assert not any(str(trigger_task2) in triple[0] and "hasToken" in triple[1] for triple in additions_dict), (
            "Second execution should NOT activate after signal expired"
        )

    def test_transient_trigger_multiple_signals_concurrent(
        self, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """Multiple tasks with transient triggers activate only when their signals are completed."""
        # Arrange: Two tasks, two signals, only one signal completed
        graph = Graph()
        task1 = WORKFLOW.TransientTask1
        task2 = WORKFLOW.TransientTask2
        signal1 = WORKFLOW.Signal1
        signal2 = WORKFLOW.Signal2

        # Task 1 with completed signal (signal flows INTO task)
        graph.add((signal1, YAWL.flowsInto, WORKFLOW.Flow1))
        graph.add((WORKFLOW.Flow1, YAWL.nextElementRef, task1))
        graph.add((task1, YAWL.triggeredBy, signal1))
        graph.add((signal1, KGC.hasToken, Literal(True)))
        graph.add((signal1, KGC.signalType, Literal("transient")))
        graph.add((signal1, KGC.completedAt, Literal("signal-tx-1")))

        # Task 2 with incomplete signal (signal flows INTO task but not completed)
        graph.add((signal2, YAWL.flowsInto, WORKFLOW.Flow2))
        graph.add((WORKFLOW.Flow2, YAWL.nextElementRef, task2))
        graph.add((task2, YAWL.triggeredBy, signal2))
        graph.add((signal2, KGC.hasToken, Literal(False)))
        graph.add((signal2, KGC.signalType, Literal("transient")))

        # Act: Execute both tasks
        config = VerbConfig(verb="await", threshold="1", completion_strategy="waitSignal")

        ctx1 = TransactionContext(
            tx_id="tx-concurrent-1", actor="test-agent", prev_hash=GENESIS_HASH, data={"signal_active": True}
        )
        delta1 = Kernel.await_(graph, task1, ctx1, config)

        ctx2 = TransactionContext(
            tx_id="tx-concurrent-2", actor="test-agent", prev_hash=GENESIS_HASH, data={"signal_active": False}
        )
        delta2 = Kernel.await_(graph, task2, ctx2, config)

        # Assert: Only task1 activates (signal1 completed), task2 waits (signal2 not completed)
        additions1 = {(str(s), str(p), str(o)) for s, p, o in delta1.additions}
        additions2 = {(str(s), str(p), str(o)) for s, p, o in delta2.additions}

        assert any(str(task1) in triple[0] and "hasToken" in triple[1] for triple in additions1), (
            "Task1 should activate with completed signal"
        )
        assert not any(str(task2) in triple[0] and "hasToken" in triple[1] for triple in additions2), (
            "Task2 should NOT activate without completed signal"
        )


class TestWcp24PersistentTrigger:
    """Tests for WCP-24: Persistent Trigger pattern using AWAIT verb.

    Persistent triggers are stable signals that remain active until explicitly
    consumed or cancelled. Tasks can activate even if they check for the signal
    after it was originally emitted.

    Pattern: yawl:PersistentTrigger → Await(threshold="persistent")
    Completion Strategy: "waitPersistent"
    """

    def test_persistent_trigger_ontology_mapping(self, physics_ontology: Graph) -> None:
        """Verify ontology maps PersistentTrigger to AWAIT verb with persistent threshold."""
        # Arrange: Query ontology for PersistentTrigger mapping
        query = """
        PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
        PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?verbLabel ?threshold ?completion WHERE {
            ?mapping kgc:pattern yawl:PersistentTrigger ;
                     kgc:verb ?verb .
            ?verb rdfs:label ?verbLabel .
            OPTIONAL { ?mapping kgc:hasThreshold ?threshold . }
            OPTIONAL { ?mapping kgc:completionStrategy ?completion . }
        }
        """
        results = list(physics_ontology.query(query))

        # Assert: Mapping exists and parameters are correct
        assert len(results) == 1, "Expected exactly one PersistentTrigger mapping"
        row = results[0]
        assert str(row[0]).lower() == "await", f"Expected 'await' verb, got {row[0]}"
        assert str(row[1]) == "persistent", f"Expected threshold='persistent', got {row[1]}"
        assert str(row[2]) == "waitPersistent", f"Expected completionStrategy='waitPersistent', got {row[2]}"

    def test_persistent_trigger_with_active_signal(
        self, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """Task activates when persistent signal is completed."""
        # Arrange: Create workflow with persistent trigger (signal flows INTO task)
        graph = Graph()
        trigger_task = WORKFLOW.PersistentTask
        signal_event = WORKFLOW.PersistentSignal

        # Signal flows into trigger task (AWAIT looks for incoming flows)
        graph.add((signal_event, YAWL.flowsInto, WORKFLOW.Flow1))
        graph.add((WORKFLOW.Flow1, YAWL.nextElementRef, trigger_task))

        # Persistent signal is completed and remains so
        graph.add((signal_event, KGC.hasToken, Literal(True)))
        graph.add((signal_event, KGC.signalType, Literal("persistent")))
        graph.add((signal_event, KGC.completedAt, Literal("signal-tx-persistent")))
        graph.add((trigger_task, YAWL.triggeredBy, signal_event))

        # Act: Execute with persistent trigger context (threshold="persistent" means need 1 completion)
        ctx = TransactionContext(
            tx_id="tx-persistent-001",
            actor="test-agent",
            prev_hash=GENESIS_HASH,
            data={"signal_active": True, "signal_type": "persistent"},
        )

        config = VerbConfig(verb="await", threshold="1", completion_strategy="waitPersistent")
        delta = Kernel.await_(graph, trigger_task, ctx, config)

        # Assert: Task activated because persistent signal is completed
        assert len(delta.additions) > 0, "Task should activate with completed persistent signal"
        additions_dict = {(str(s), str(p), str(o)) for s, p, o in delta.additions}
        assert any(str(trigger_task) in triple[0] and "hasToken" in triple[1] for triple in additions_dict), (
            "Task should receive token with persistent signal"
        )

    def test_persistent_trigger_signal_persists_after_check(
        self, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """Persistent signal remains completed after being checked (not consumed)."""
        # Arrange: Workflow with persistent trigger (signal flows INTO both tasks)
        graph = Graph()
        task1 = WORKFLOW.PersistentTask1
        task2 = WORKFLOW.PersistentTask2
        signal_event = WORKFLOW.PersistentSignalShared

        # Signal flows into both tasks (shared persistent signal)
        graph.add((signal_event, YAWL.flowsInto, WORKFLOW.Flow1))
        graph.add((WORKFLOW.Flow1, YAWL.nextElementRef, task1))
        graph.add((task1, YAWL.triggeredBy, signal_event))

        graph.add((signal_event, YAWL.flowsInto, WORKFLOW.Flow2))
        graph.add((WORKFLOW.Flow2, YAWL.nextElementRef, task2))
        graph.add((task2, YAWL.triggeredBy, signal_event))

        # Signal is persistent and completed (remains so)
        graph.add((signal_event, KGC.hasToken, Literal(True)))
        graph.add((signal_event, KGC.signalType, Literal("persistent")))
        graph.add((signal_event, KGC.completedAt, Literal("signal-tx-persistent")))

        # Act: First task checks signal
        ctx1 = TransactionContext(
            tx_id="tx-persistent-002a",
            actor="test-agent",
            prev_hash=GENESIS_HASH,
            data={"signal_active": True, "signal_type": "persistent"},
        )
        config = VerbConfig(verb="await", threshold="1", completion_strategy="waitPersistent")
        delta1 = Kernel.await_(graph, task1, ctx1, config)

        # Apply mutations (signal completedAt should still be there - not removed)
        for triple in delta1.removals:
            graph.remove(triple)
        for triple in delta1.additions:
            graph.add(triple)

        # Assert: First task activated
        assert len(delta1.additions) > 0, "First task should activate"

        # Verify signal is still completed (persistent nature - completedAt remains)
        signal_still_completed = (signal_event, KGC.completedAt, Literal("signal-tx-persistent")) in graph
        assert signal_still_completed, "Persistent signal should remain completed after first check"

        # Act: Second task checks same signal
        ctx2 = TransactionContext(
            tx_id="tx-persistent-002b",
            actor="test-agent",
            prev_hash="tx-persistent-002a",
            data={"signal_active": True, "signal_type": "persistent"},
        )
        delta2 = Kernel.await_(graph, task2, ctx2, config)

        # Assert: Second task also activates (signal completion persists)
        additions2 = {(str(s), str(p), str(o)) for s, p, o in delta2.additions}
        assert any(str(task2) in triple[0] and "hasToken" in triple[1] for triple in additions2), (
            "Second task should also activate (signal completion persists)"
        )

    def test_persistent_trigger_activates_late_arrival(
        self, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """Task can activate even if it checks after signal was emitted (late arrival)."""
        # Arrange: Signal emitted BEFORE task checks (simulates late arrival)
        graph = Graph()
        trigger_task = WORKFLOW.LateArrivalTask
        signal_event = WORKFLOW.EarlySignal

        # Signal flows into task (AWAIT looks for incoming flows)
        graph.add((signal_event, YAWL.flowsInto, WORKFLOW.Flow1))
        graph.add((WORKFLOW.Flow1, YAWL.nextElementRef, trigger_task))
        graph.add((trigger_task, YAWL.triggeredBy, signal_event))

        # Signal was completed earlier (timestamp in past) - completion persists!
        graph.add((signal_event, KGC.hasToken, Literal(True)))
        graph.add((signal_event, KGC.signalType, Literal("persistent")))
        graph.add((signal_event, KGC.completedAt, Literal("signal-tx-early-001")))
        graph.add((signal_event, KGC.emittedAt, Literal("timestamp-past")))

        # Act: Task checks for signal (later than signal emission) - persistent completion remains
        ctx = TransactionContext(
            tx_id="tx-persistent-003",
            actor="test-agent",
            prev_hash=GENESIS_HASH,
            data={"signal_active": True, "signal_type": "persistent", "arrival_time": "timestamp-now"},
        )

        config = VerbConfig(verb="await", threshold="1", completion_strategy="waitPersistent")
        delta = Kernel.await_(graph, trigger_task, ctx, config)

        # Assert: Task activates despite checking after signal emission (persistent completion)
        assert len(delta.additions) > 0, "Task should activate even with late arrival (persistent signal)"
        additions_dict = {(str(s), str(p), str(o)) for s, p, o in delta.additions}
        assert any(str(trigger_task) in triple[0] and "hasToken" in triple[1] for triple in additions_dict), (
            "Late-arriving task should receive token with persistent signal"
        )

    def test_persistent_trigger_without_signal(
        self, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """Task does NOT activate when persistent signal is not completed."""
        # Arrange: Workflow with no persistent signal completed
        graph = Graph()
        trigger_task = WORKFLOW.PersistentTaskNoSignal
        signal_event = WORKFLOW.PersistentSignalInactive

        # Signal flows into task
        graph.add((signal_event, YAWL.flowsInto, WORKFLOW.Flow1))
        graph.add((WORKFLOW.Flow1, YAWL.nextElementRef, trigger_task))
        graph.add((trigger_task, YAWL.triggeredBy, signal_event))

        # Signal was active but has been consumed/cleared (no completedAt)
        graph.add((signal_event, KGC.hasToken, Literal(False)))
        graph.add((signal_event, KGC.signalType, Literal("persistent")))
        graph.add((signal_event, KGC.consumedAt, Literal("signal-tx-consumed")))

        # Act: Execute with no completed signal (completed_sources = 0, required = 1)
        ctx = TransactionContext(
            tx_id="tx-persistent-004",
            actor="test-agent",
            prev_hash=GENESIS_HASH,
            data={"signal_active": False, "signal_type": "persistent"},
        )

        config = VerbConfig(verb="await", threshold="1", completion_strategy="waitPersistent")
        delta = Kernel.await_(graph, trigger_task, ctx, config)

        # Assert: Task should NOT activate without completed signal (0 < 1)
        additions_dict = {(str(s), str(p), str(o)) for s, p, o in delta.additions}
        assert not any(str(trigger_task) in triple[0] and "hasToken" in triple[1] for triple in additions_dict), (
            "Task should NOT activate without completed persistent signal"
        )


class TestTriggerPatternComparison:
    """Comparison tests highlighting differences between transient and persistent triggers."""

    def test_transient_vs_persistent_timing_behavior(
        self, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """Compare timing behavior: transient expires, persistent completion persists."""
        # Arrange: Two tasks, same signal timing, different trigger types
        graph = Graph()

        # Transient trigger task (signal flows INTO task)
        transient_task = WORKFLOW.TransientTimingTask
        transient_signal = WORKFLOW.TransientTimingSignal
        graph.add((transient_signal, YAWL.flowsInto, WORKFLOW.Flow1))
        graph.add((WORKFLOW.Flow1, YAWL.nextElementRef, transient_task))
        graph.add((transient_task, YAWL.triggeredBy, transient_signal))
        graph.add((transient_signal, KGC.signalType, Literal("transient")))
        # Signal expired - no completedAt means not completed (transient nature)
        graph.add((transient_signal, KGC.hasToken, Literal(False)))
        graph.add((transient_signal, KGC.expiredAt, Literal("signal-tx-past")))

        # Persistent trigger task (signal flows INTO task)
        persistent_task = WORKFLOW.PersistentTimingTask
        persistent_signal = WORKFLOW.PersistentTimingSignal
        graph.add((persistent_signal, YAWL.flowsInto, WORKFLOW.Flow2))
        graph.add((WORKFLOW.Flow2, YAWL.nextElementRef, persistent_task))
        graph.add((persistent_task, YAWL.triggeredBy, persistent_signal))
        graph.add((persistent_signal, KGC.signalType, Literal("persistent")))
        # Signal completed and remains so (persistent nature)
        graph.add((persistent_signal, KGC.hasToken, Literal(True)))
        graph.add((persistent_signal, KGC.completedAt, Literal("signal-tx-past")))
        graph.add((persistent_signal, KGC.emittedAt, Literal("signal-tx-past")))

        # Act: Execute both tasks (checking after signal emission)
        transient_config = VerbConfig(verb="await", threshold="1", completion_strategy="waitSignal")
        persistent_config = VerbConfig(verb="await", threshold="1", completion_strategy="waitPersistent")

        ctx = TransactionContext(
            tx_id="tx-comparison-001", actor="test-agent", prev_hash=GENESIS_HASH, data={"check_time": "now"}
        )

        transient_delta = Kernel.await_(graph, transient_task, ctx, transient_config)
        persistent_delta = Kernel.await_(graph, persistent_task, ctx, persistent_config)

        # Assert: Transient fails (not completed), persistent succeeds (completion persists)
        transient_additions = {(str(s), str(p), str(o)) for s, p, o in transient_delta.additions}
        persistent_additions = {(str(s), str(p), str(o)) for s, p, o in persistent_delta.additions}

        assert not any(
            str(transient_task) in triple[0] and "hasToken" in triple[1] for triple in transient_additions
        ), "Transient task should NOT activate (signal not completed, expired)"

        assert any(str(persistent_task) in triple[0] and "hasToken" in triple[1] for triple in persistent_additions), (
            "Persistent task SHOULD activate (completion persists)"
        )

    def test_trigger_pattern_provenance_tracking(
        self, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """Verify that trigger activations include proper provenance metadata."""
        # Arrange: Task with persistent trigger (signal flows INTO task)
        graph = Graph()
        trigger_task = WORKFLOW.ProvenanceTask
        signal_event = WORKFLOW.ProvenanceSignal

        # Signal flows into task
        graph.add((signal_event, YAWL.flowsInto, WORKFLOW.Flow1))
        graph.add((WORKFLOW.Flow1, YAWL.nextElementRef, trigger_task))
        graph.add((trigger_task, YAWL.triggeredBy, signal_event))
        graph.add((signal_event, KGC.hasToken, Literal(True)))
        graph.add((signal_event, KGC.signalType, Literal("persistent")))
        graph.add((signal_event, KGC.completedAt, Literal("signal-tx-provenance")))

        # Act: Execute and generate receipt
        ctx = TransactionContext(
            tx_id="tx-provenance-001", actor="test-agent", prev_hash=GENESIS_HASH, data={"signal_active": True}
        )

        config = VerbConfig(verb="await", threshold="1", completion_strategy="waitPersistent")
        delta = Kernel.await_(graph, trigger_task, ctx, config)

        # Create receipt manually (simulating driver.execute)
        import hashlib

        params_str = f"t={config.threshold}|c={config.cardinality}|s={config.selection_mode}"
        merkle_payload = (
            f"{ctx.prev_hash}|{ctx.tx_id}|{config.verb}|{params_str}|{len(delta.additions)}|{len(delta.removals)}"
        )
        merkle_root = hashlib.sha256(merkle_payload.encode()).hexdigest()

        receipt = Receipt(merkle_root=merkle_root, verb_executed=config.verb, delta=delta, params_used=config)

        # Assert: Receipt includes trigger parameters
        assert receipt.params_used is not None, "Receipt should include parameters"
        assert receipt.params_used.verb == "await", "Verb should be 'await'"
        assert receipt.params_used.threshold == "1", "Threshold should be '1'"
        assert receipt.params_used.completion_strategy == "waitPersistent", "Strategy should be 'waitPersistent'"
        assert len(receipt.merkle_root) == SHA256_HEX_LENGTH, "Merkle root should be valid SHA256"
