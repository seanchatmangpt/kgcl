"""Verification tests for the Fakes module.

These tests verify that the fakes work correctly in Chicago-Style TDD scenarios.
"""

from __future__ import annotations

from datetime import UTC, datetime

from rdflib import Graph, Literal, URIRef

from kgcl.unrdf_engine.engine import ProvenanceRecord, Transaction
from kgcl.unrdf_engine.hooks import HookContext, HookPhase, KnowledgeHook, Receipt
from tests.fakes import (
    FakeHookExecutor,
    FakeHookRegistry,
    FakeIngestionPipeline,
    FakeRdfStore,
    FakeReceiptStore,
    FakeTransactionStore,
)


class SimpleValidationHook(KnowledgeHook):
    """Simple validation hook for testing."""

    def __init__(self) -> None:
        """Initialize validation hook."""
        super().__init__(name="simple_validator", phases=[HookPhase.PRE_TRANSACTION], priority=10)
        self.executed_count = 0

    def execute(self, context: HookContext) -> None:
        """Execute validation - just count executions."""
        self.executed_count += 1


class TestFakeReceiptStore:
    """Test FakeReceiptStore behavior."""

    def test_save_and_retrieve_receipt(self) -> None:
        """Saved receipt can be retrieved by hook ID."""
        # Arrange
        store = FakeReceiptStore()
        receipt = Receipt(
            hook_id="test_hook",
            phase=HookPhase.PRE_TRANSACTION,
            timestamp=datetime.now(UTC),
            success=True,
            duration_ms=5.0,
        )

        # Act
        store.save(receipt)

        # Assert
        retrieved = store.get("test_hook")
        assert retrieved is not None
        assert retrieved.hook_id == "test_hook"
        assert retrieved.success is True
        assert retrieved.duration_ms == 5.0

    def test_all_returns_all_receipts(self) -> None:
        """All receipts are returned by all() method."""
        # Arrange
        store = FakeReceiptStore()
        receipts = [
            Receipt(
                hook_id=f"hook_{i}",
                phase=HookPhase.PRE_TRANSACTION,
                timestamp=datetime.now(UTC),
                success=True,
                duration_ms=float(i),
            )
            for i in range(3)
        ]

        # Act
        for receipt in receipts:
            store.save(receipt)

        # Assert
        all_receipts = store.all()
        assert len(all_receipts) == 3
        assert set(r.hook_id for r in all_receipts) == {"hook_0", "hook_1", "hook_2"}

    def test_for_phase_filters_by_phase(self) -> None:
        """Receipts are filtered by phase correctly."""
        # Arrange
        store = FakeReceiptStore()
        pre_receipt = Receipt(
            hook_id="pre_hook",
            phase=HookPhase.PRE_TRANSACTION,
            timestamp=datetime.now(UTC),
            success=True,
            duration_ms=1.0,
        )
        post_receipt = Receipt(
            hook_id="post_hook",
            phase=HookPhase.POST_TRANSACTION,
            timestamp=datetime.now(UTC),
            success=True,
            duration_ms=2.0,
        )

        # Act
        store.save(pre_receipt)
        store.save(post_receipt)

        # Assert
        pre_receipts = store.for_phase(HookPhase.PRE_TRANSACTION)
        assert len(pre_receipts) == 1
        assert pre_receipts[0].hook_id == "pre_hook"

        post_receipts = store.for_phase(HookPhase.POST_TRANSACTION)
        assert len(post_receipts) == 1
        assert post_receipts[0].hook_id == "post_hook"

    def test_successful_count_counts_only_successful(self) -> None:
        """Successful count only counts receipts with success=True."""
        # Arrange
        store = FakeReceiptStore()
        store.save(
            Receipt(
                hook_id="success1",
                phase=HookPhase.PRE_TRANSACTION,
                timestamp=datetime.now(UTC),
                success=True,
                duration_ms=1.0,
            )
        )
        store.save(
            Receipt(
                hook_id="failure1",
                phase=HookPhase.PRE_TRANSACTION,
                timestamp=datetime.now(UTC),
                success=False,
                duration_ms=2.0,
                error="Test error",
            )
        )
        store.save(
            Receipt(
                hook_id="success2",
                phase=HookPhase.PRE_TRANSACTION,
                timestamp=datetime.now(UTC),
                success=True,
                duration_ms=3.0,
            )
        )

        # Act & Assert
        assert store.successful_count() == 2
        assert store.failed_count() == 1
        assert store.count() == 3


class TestFakeRdfStore:
    """Test FakeRdfStore behavior."""

    def test_add_and_retrieve_triple(self) -> None:
        """Added triple can be retrieved from graph."""
        # Arrange
        store = FakeRdfStore()
        subject = URIRef("http://example.org/person1")
        predicate = URIRef("http://xmlns.com/foaf/0.1/name")
        obj = Literal("Alice")

        # Act
        store.add_triple(subject, predicate, obj)

        # Assert
        assert store.count_triples() == 1
        triples = list(store.all_triples())
        assert len(triples) == 1
        assert triples[0] == (subject, predicate, obj)

    def test_remove_triple_removes_from_graph(self) -> None:
        """Removed triple is no longer in graph."""
        # Arrange
        store = FakeRdfStore()
        subject = URIRef("http://example.org/person1")
        predicate = URIRef("http://xmlns.com/foaf/0.1/name")
        obj = Literal("Alice")
        store.add_triple(subject, predicate, obj)

        # Act
        store.remove_triple(subject, predicate, obj)

        # Assert
        assert store.count_triples() == 0

    def test_provenance_stored_with_triple(self) -> None:
        """Provenance is stored and retrievable for triple."""
        # Arrange
        store = FakeRdfStore()
        subject = URIRef("http://example.org/person1")
        predicate = URIRef("http://xmlns.com/foaf/0.1/name")
        obj = Literal("Alice")
        provenance = ProvenanceRecord(agent="test_user", timestamp=datetime.now(UTC), reason="test data")

        # Act
        store.add_triple(subject, predicate, obj, provenance=provenance)

        # Assert
        retrieved_prov = store.get_provenance(subject, predicate, obj)
        assert retrieved_prov is not None
        assert retrieved_prov.agent == "test_user"
        assert retrieved_prov.reason == "test data"


class TestFakeHookRegistry:
    """Test FakeHookRegistry behavior."""

    def test_register_and_retrieve_hook(self) -> None:
        """Registered hook can be retrieved by name."""
        # Arrange
        registry = FakeHookRegistry()
        hook = SimpleValidationHook()

        # Act
        registry.register(hook)

        # Assert
        retrieved = registry.get("simple_validator")
        assert retrieved is not None
        assert retrieved.name == "simple_validator"
        assert retrieved is hook

    def test_get_for_phase_returns_hooks_sorted_by_priority(self) -> None:
        """Hooks for phase are sorted by priority descending."""
        # Arrange
        registry = FakeHookRegistry()

        class LowPriorityHook(KnowledgeHook):
            def __init__(self) -> None:
                super().__init__(name="low_priority", phases=[HookPhase.PRE_TRANSACTION], priority=1)

            def execute(self, context: HookContext) -> None:
                """Execute low priority hook - no-op for testing."""
                context.metadata["low_priority_executed"] = True

        class HighPriorityHook(KnowledgeHook):
            def __init__(self) -> None:
                super().__init__(name="high_priority", phases=[HookPhase.PRE_TRANSACTION], priority=100)

            def execute(self, context: HookContext) -> None:
                """Execute high priority hook - no-op for testing."""
                context.metadata["high_priority_executed"] = True

        low_hook = LowPriorityHook()
        high_hook = HighPriorityHook()

        # Act - register in reverse priority order
        registry.register(low_hook)
        registry.register(high_hook)

        # Assert - should be sorted with high priority first
        hooks = registry.get_for_phase(HookPhase.PRE_TRANSACTION)
        assert len(hooks) == 2
        assert hooks[0].name == "high_priority"
        assert hooks[1].name == "low_priority"

    def test_unregister_removes_hook(self) -> None:
        """Unregistered hook is no longer retrievable."""
        # Arrange
        registry = FakeHookRegistry()
        hook = SimpleValidationHook()
        registry.register(hook)

        # Act
        registry.unregister("simple_validator")

        # Assert
        assert registry.get("simple_validator") is None
        assert len(registry.list_all()) == 0


class TestFakeHookExecutor:
    """Test FakeHookExecutor behavior."""

    def test_execute_phase_runs_registered_hooks(self) -> None:
        """Hooks registered for phase are executed."""
        # Arrange
        registry = FakeHookRegistry()
        executor = FakeHookExecutor(registry=registry)
        hook = SimpleValidationHook()
        registry.register(hook)

        context = HookContext(phase=HookPhase.PRE_TRANSACTION, graph=Graph(), delta=Graph(), transaction_id="txn-001")

        # Act
        results = executor.execute_phase(HookPhase.PRE_TRANSACTION, context)

        # Assert
        assert len(results) == 1
        assert results[0]["hook"] == "simple_validator"
        assert results[0]["success"] is True
        assert results[0]["executed"] is True
        assert hook.executed_count == 1

    def test_execute_phase_creates_receipts(self) -> None:
        """Hook execution creates receipts in context."""
        # Arrange
        registry = FakeHookRegistry()
        executor = FakeHookExecutor(registry=registry)
        hook = SimpleValidationHook()
        registry.register(hook)

        context = HookContext(phase=HookPhase.PRE_TRANSACTION, graph=Graph(), delta=Graph(), transaction_id="txn-001")

        # Act
        executor.execute_phase(HookPhase.PRE_TRANSACTION, context)

        # Assert
        assert len(context.receipts) == 1
        receipt = context.receipts[0]
        assert receipt.hook_id == "simple_validator"
        assert receipt.success is True
        assert receipt.phase == HookPhase.PRE_TRANSACTION

    def test_execution_history_records_all_executions(self) -> None:
        """Execution history contains all hook executions."""
        # Arrange
        registry = FakeHookRegistry()
        executor = FakeHookExecutor(registry=registry)
        hook = SimpleValidationHook()
        registry.register(hook)

        context1 = HookContext(phase=HookPhase.PRE_TRANSACTION, graph=Graph(), delta=Graph(), transaction_id="txn-001")
        context2 = HookContext(phase=HookPhase.PRE_TRANSACTION, graph=Graph(), delta=Graph(), transaction_id="txn-002")

        # Act
        executor.execute_phase(HookPhase.PRE_TRANSACTION, context1)
        executor.execute_phase(HookPhase.PRE_TRANSACTION, context2)

        # Assert
        history = executor.get_execution_history()
        assert len(history) == 2
        assert history[0]["transaction_id"] == "txn-001"
        assert history[1]["transaction_id"] == "txn-002"


class TestFakeTransactionStore:
    """Test FakeTransactionStore behavior."""

    def test_save_and_retrieve_transaction(self) -> None:
        """Saved transaction can be retrieved by ID."""
        # Arrange
        store = FakeTransactionStore()
        txn = Transaction(
            transaction_id="txn-001",
            provenance=ProvenanceRecord(agent="test_user", timestamp=datetime.now(UTC), reason="test transaction"),
        )

        # Act
        store.save(txn)

        # Assert
        retrieved = store.get("txn-001")
        assert retrieved is not None
        assert retrieved.transaction_id == "txn-001"
        assert retrieved is txn

    def test_committed_filters_committed_transactions(self) -> None:
        """Committed transactions are filtered correctly."""
        # Arrange
        store = FakeTransactionStore()
        txn1 = Transaction(transaction_id="txn-001")
        txn1.committed = True
        txn2 = Transaction(transaction_id="txn-002")
        txn2.rolled_back = True

        # Act
        store.save(txn1)
        store.save(txn2)

        # Assert
        committed = store.committed()
        assert len(committed) == 1
        assert committed[0].transaction_id == "txn-001"

        rolled_back = store.rolled_back()
        assert len(rolled_back) == 1
        assert rolled_back[0].transaction_id == "txn-002"


class TestFakeIngestionPipeline:
    """Test FakeIngestionPipeline behavior."""

    def test_ingest_json_creates_triples(self) -> None:
        """JSON ingestion creates RDF triples."""
        # Arrange
        pipeline = FakeIngestionPipeline()
        data = {"type": "Person", "name": "Alice", "age": "30"}

        # Act
        result = pipeline.ingest_json(data=data, agent="test_service")

        # Assert
        assert result["success"] is True
        assert result["triples_added"] == 3  # type, name, age
        assert pipeline.rdf_store.count_triples() == 3

    def test_ingest_json_list_processes_all_items(self) -> None:
        """Ingesting list of JSON objects processes all items."""
        # Arrange
        pipeline = FakeIngestionPipeline()
        data = [{"type": "Person", "name": "Alice"}, {"type": "Person", "name": "Bob"}]

        # Act
        result = pipeline.ingest_json(data=data, agent="test_service")

        # Assert
        assert result["success"] is True
        assert result["triples_added"] == 4  # 2 type + 2 name
        assert pipeline.rdf_store.count_triples() == 4

    def test_ingestion_history_records_all_ingestions(self) -> None:
        """Ingestion history contains all ingestion operations."""
        # Arrange
        pipeline = FakeIngestionPipeline()

        # Act
        pipeline.ingest_json(data={"name": "Alice"}, agent="service1")
        pipeline.ingest_json(data={"name": "Bob"}, agent="service2")

        # Assert
        history = pipeline.get_history()
        assert len(history) == 2
        assert history[0]["agent"] == "service1"
        assert history[1]["agent"] == "service2"


class TestChicagoStyleIntegration:
    """Integration tests demonstrating Chicago-Style TDD with fakes."""

    def test_hook_execution_with_real_collaborators(self) -> None:
        """Hook execution with real objects and fake storage.

        This demonstrates Chicago School TDD:
        - Real KnowledgeHook instances
        - Real HookExecutor logic
        - Real Graph from rdflib
        - Fake storage for verification
        - Assertions on observable state (not mocks)
        """
        # Arrange - real collaborators with fake storage
        registry = FakeHookRegistry()
        rdf_store = FakeRdfStore()

        hook = SimpleValidationHook()
        registry.register(hook)

        executor = FakeHookExecutor(registry=registry)

        # Act - real execution
        context = HookContext(
            phase=HookPhase.PRE_TRANSACTION, graph=rdf_store.graph, delta=Graph(), transaction_id="txn-001"
        )
        results = executor.execute_phase(HookPhase.PRE_TRANSACTION, context)

        # Assert - verify observable state
        assert len(results) == 1
        assert results[0]["success"] is True
        assert hook.executed_count == 1

        # Verify receipt was created
        assert len(context.receipts) == 1
        receipt = context.receipts[0]
        assert receipt.hook_id == "simple_validator"
        assert receipt.success is True
        assert receipt.duration_ms > 0

    def test_ingestion_pipeline_with_real_graph(self) -> None:
        """Ingestion pipeline with real RDF graph.

        Demonstrates:
        - Real JSON to RDF conversion
        - Real rdflib Graph
        - Fake storage for inspection
        - Observable state verification
        """
        # Arrange
        pipeline = FakeIngestionPipeline()
        data = {"type": "Event", "name": "user_login", "userId": "123", "timestamp": "2024-01-01T00:00:00Z"}

        # Act
        result = pipeline.ingest_json(data=data, agent="ingestion_service", reason="test data")

        # Assert - verify observable state
        assert result["success"] is True
        assert result["triples_added"] == 4  # type, name, userId, timestamp
        assert result["agent"] == "ingestion_service"
        assert result["reason"] == "test data"

        # Verify RDF graph state
        assert pipeline.rdf_store.count_triples() == 4

        # Verify we can query the graph
        query_result = pipeline.rdf_store.query(
            """
            PREFIX unrdf: <http://unrdf.org/ontology/>
            SELECT ?name WHERE { ?s unrdf:name ?name }
            """
        )
        names = [str(row[0]) for row in query_result]  # type: ignore[index]
        assert "user_login" in names
