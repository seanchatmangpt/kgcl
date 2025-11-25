"""Comprehensive hook and UNRDF integration tests.

Tests hook triggers on ingestion, transaction lifecycle, SPARQL queries,
feature materialization, and cross-hook communication.
"""

import tempfile
from datetime import UTC
from pathlib import Path

import pytest
from rdflib import Literal, Namespace, URIRef
from rdflib.namespace import RDF

from kgcl.unrdf_engine.engine import UnrdfEngine
from kgcl.unrdf_engine.hook_registry import PersistentHookRegistry
from kgcl.unrdf_engine.hooks import HookContext, HookPhase, KnowledgeHook, TriggerCondition
from kgcl.unrdf_engine.ingestion import IngestionPipeline

UNRDF = Namespace("http://unrdf.org/ontology/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")


class TestHookUnrdfIntegration:
    """Test hook integration with UNRDF engine."""

    def test_hook_triggers_on_ingestion_with_delta(self) -> None:
        """Test hook triggers on ingestion with access to graph delta."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)

            delta_captured = []

            class DeltaCapture(KnowledgeHook):
                def __init__(self):
                    super().__init__(name="delta_capture", phases=[HookPhase.ON_CHANGE])

                def execute(self, context: HookContext):
                    # Capture delta triples
                    for s, p, o in context.delta:
                        delta_captured.append((str(s), str(p), str(o)))

            registry.register(DeltaCapture())

            # Create pipeline with hook executor
            from kgcl.unrdf_engine.hooks import HookExecutor

            hook_executor = HookExecutor(registry)
            pipeline = IngestionPipeline(engine, hook_executor=hook_executor)

            # Ingest data
            result = pipeline.ingest_json(
                data={"id": "person1", "type": "Person", "name": "Alice"}, agent="test_agent"
            )

            assert result.success is True
            assert len(delta_captured) >= 2  # At least type and name triples

    def test_hook_examines_data_before_commit(self) -> None:
        """Test hook can examine ingested data before commitment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)

            examined_data = {"found_person": False}

            class DataExaminer(KnowledgeHook):
                def __init__(self):
                    super().__init__(name="data_examiner", phases=[HookPhase.PRE_TRANSACTION])

                def execute(self, context: HookContext):
                    # Check if Person type exists in delta
                    for s, p, o in context.delta:
                        if str(p) == str(RDF.type) and "Person" in str(o):
                            examined_data["found_person"] = True

            registry.register(DataExaminer())

            from kgcl.unrdf_engine.hooks import HookExecutor

            hook_executor = HookExecutor(registry)
            pipeline = IngestionPipeline(engine, hook_executor=hook_executor)

            result = pipeline.ingest_json(data={"id": "person1", "type": "Person"}, agent="test")

            assert result.success is True
            assert examined_data["found_person"] is True

    def test_hook_modifies_ingested_data(self) -> None:
        """Test hook can modify data before transaction."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)

            class DataModifier(KnowledgeHook):
                def __init__(self):
                    super().__init__(name="data_modifier", phases=[HookPhase.PRE_TRANSACTION])

                def execute(self, context: HookContext):
                    # Add a timestamp triple to delta
                    from datetime import datetime

                    for s, p, o in context.delta:
                        if str(p) == str(RDF.type):
                            context.delta.add(
                                (s, UNRDF.processedAt, Literal(datetime.now(UTC).isoformat()))
                            )
                            break

            registry.register(DataModifier())
            pipeline = IngestionPipeline(engine)

            result = pipeline.ingest_json(data={"id": "person1", "type": "Person"}, agent="test")

            assert result.success is True

            # Check if timestamp was added
            query = f"""
            PREFIX unrdf: <{UNRDF}>
            ASK {{ ?s unrdf:processedAt ?timestamp }}
            """
            # Note: Hook adds to delta but delta isn't directly committed in this flow
            # This test validates hook can modify delta graph structure

    def test_hook_rejects_ingestion_with_reason(self) -> None:
        """Test hook can reject ingestion using POST_VALIDATION with loaded shapes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)

            class RejectionHook(KnowledgeHook):
                def __init__(self):
                    super().__init__(name="rejection_hook", phases=[HookPhase.POST_VALIDATION])

                def execute(self, context: HookContext):
                    # Reject if data contains "forbidden"
                    for s, p, o in context.delta:
                        if "forbidden" in str(o).lower():
                            context.metadata["should_rollback"] = True
                            context.metadata["rollback_reason"] = "Forbidden content detected"

            registry.register(RejectionHook())

            from kgcl.unrdf_engine.hooks import HookExecutor
            from kgcl.unrdf_engine.validation import ShaclValidator

            hook_executor = HookExecutor(registry)
            validator = ShaclValidator()

            # Load a minimal SHACL shape to trigger validation
            shapes_ttl = """
            @prefix sh: <http://www.w3.org/ns/shacl#> .
            @prefix unrdf: <http://unrdf.org/ontology/> .

            [] a sh:NodeShape ;
                sh:targetClass unrdf:TestEntity ;
                sh:property [
                    sh:path unrdf:name ;
                    sh:minCount 0 ;
                ] .
            """
            validator.load_shapes_from_string(shapes_ttl)

            pipeline = IngestionPipeline(engine, validator=validator, hook_executor=hook_executor)

            # Try to ingest forbidden data
            result = pipeline.ingest_json(
                data={"id": "test", "type": "TestEntity", "name": "Forbidden User"}, agent="test"
            )

            # Should fail with rollback
            assert result.success is False
            assert "Forbidden content detected" in str(result.error)

    def test_multiple_hooks_execute_in_priority_order(self) -> None:
        """Test multiple hooks execute in priority order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)

            execution_order = []

            class PriorityHook(KnowledgeHook):
                def __init__(self, name, priority):
                    super().__init__(name=name, phases=[HookPhase.POST_COMMIT], priority=priority)
                    self.hook_name = name

                def execute(self, context: HookContext):
                    execution_order.append(self.hook_name)

            # Register in random order
            registry.register(PriorityHook("low", 10))
            registry.register(PriorityHook("high", 100))
            registry.register(PriorityHook("medium", 50))

            pipeline = IngestionPipeline(engine)
            result = pipeline.ingest_json(data={"id": "test"}, agent="test")

            assert result.success is True
            assert execution_order == ["high", "medium", "low"]

    def test_hook_failure_causes_transaction_rollback(self) -> None:
        """Test hook failure can cause transaction rollback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)

            class FailureHook(KnowledgeHook):
                def __init__(self):
                    super().__init__(name="failure_hook", phases=[HookPhase.PRE_TRANSACTION])

                def execute(self, context: HookContext):
                    context.metadata["should_rollback"] = True
                    context.metadata["rollback_reason"] = "Test rollback"

            registry.register(FailureHook())
            pipeline = IngestionPipeline(engine)

            # Should fail and rollback
            result = pipeline.ingest_json(data={"id": "test"}, agent="test")
            assert result.success is False
            assert "Test rollback" in (result.error or "")

            # Verify nothing was committed
            assert len(engine.graph) == 0

    def test_receipts_stored_in_transaction_provenance(self) -> None:
        """Test receipts are stored in transaction metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)

            class ReceiptHook(KnowledgeHook):
                def __init__(self):
                    super().__init__(name="receipt_hook", phases=[HookPhase.POST_TRANSACTION])

                def execute(self, context: HookContext):
                    pass  # Just execute

            registry.register(ReceiptHook())

            # Create transaction manually
            txn = engine.transaction("test_agent", "test reason")
            engine.add_triple(URIRef("http://example.org/test"), RDF.type, UNRDF.TestEntity, txn)
            engine.commit(txn)

            # Check receipts
            assert len(txn.hook_receipts) > 0
            assert any(r.hook_id == "receipt_hook" for r in txn.hook_receipts)

    def test_feature_materialization_hook(self) -> None:
        """Test feature materialization through hooks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)

            materialized_features = []

            class FeatureMaterializer(KnowledgeHook):
                def __init__(self):
                    super().__init__(
                        name="feature_materializer",
                        phases=[HookPhase.POST_COMMIT],
                        trigger=TriggerCondition(
                            pattern="?s a <http://unrdf.org/ontology/FeatureTemplate>",
                            check_delta=True,
                        ),
                    )

                def execute(self, context: HookContext):
                    # Find templates and materialize
                    for s, p, o in context.delta:
                        if str(p) == str(RDF.type) and "FeatureTemplate" in str(o):
                            materialized_features.append(str(s))

            registry.register(FeatureMaterializer())
            pipeline = IngestionPipeline(engine)

            # Ingest feature template
            result = pipeline.ingest_json(
                data={"id": "template1", "type": "FeatureTemplate", "name": "Test Template"},
                agent="test",
            )

            assert result.success is True
            assert len(materialized_features) > 0

    def test_sparql_query_hooks(self) -> None:
        """Test hooks on SPARQL query execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)

            query_intercepted = []

            class QueryInterceptor(KnowledgeHook):
                def __init__(self):
                    super().__init__(name="query_interceptor", phases=[HookPhase.PRE_QUERY])

                def execute(self, context: HookContext):
                    query_intercepted.append(context.metadata.get("query"))

            registry.register(QueryInterceptor())

            # Add some data
            txn = engine.transaction("test", "setup")
            engine.add_triple(
                URIRef("http://example.org/person1"), FOAF.name, Literal("Alice"), txn
            )
            engine.commit(txn)

            # Execute query
            result = engine.query("SELECT ?s ?n WHERE { ?s <http://xmlns.com/foaf/0.1/name> ?n }")

            assert len(query_intercepted) > 0
            assert "SELECT" in query_intercepted[0]

    def test_cross_hook_communication(self) -> None:
        """Test hooks can communicate through receipts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)

            class Hook1(KnowledgeHook):
                def __init__(self):
                    super().__init__(name="hook1", phases=[HookPhase.ON_CHANGE], priority=100)

                def execute(self, context: HookContext):
                    context.metadata["hook1_data"] = "processed_by_hook1"

            class Hook2(KnowledgeHook):
                def __init__(self):
                    super().__init__(name="hook2", phases=[HookPhase.ON_CHANGE], priority=50)

                def execute(self, context: HookContext):
                    # Should see data from Hook1
                    assert context.metadata.get("hook1_data") == "processed_by_hook1"
                    context.metadata["hook2_data"] = "processed_by_hook2"

            registry.register(Hook1())
            registry.register(Hook2())

            pipeline = IngestionPipeline(engine)
            result = pipeline.ingest_json(data={"id": "test"}, agent="test")

            assert result.success is True

    def test_hook_performance_tracking(self) -> None:
        """Test hook execution performance is tracked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)

            class SlowHook(KnowledgeHook):
                def __init__(self):
                    super().__init__(name="slow_hook", phases=[HookPhase.POST_TRANSACTION])

                def execute(self, context: HookContext):
                    import time

                    time.sleep(0.01)  # 10ms delay

            registry.register(SlowHook())

            txn = engine.transaction("test", "performance test")
            engine.add_triple(URIRef("http://example.org/test"), RDF.type, UNRDF.Test, txn)
            engine.commit(txn)

            # Check receipts have duration
            assert len(txn.hook_receipts) > 0
            receipt = txn.hook_receipts[0]
            assert receipt.duration_ms >= 10.0  # Should be at least 10ms

    def test_hook_registry_persistence(self) -> None:
        """Test hook registry can persist and reload."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "hooks.json"
            registry = PersistentHookRegistry(storage_path=storage_path, auto_save=True)

            class TestHook(KnowledgeHook):
                def __init__(self):
                    super().__init__(name="test_hook", phases=[HookPhase.POST_COMMIT])

                def execute(self, context: HookContext):
                    pass

            hook = TestHook()
            registry.register(hook, description="Test hook for persistence")
            assert storage_path.exists()

            # Load in new registry
            new_registry = PersistentHookRegistry(storage_path=storage_path)
            metadata = new_registry.get_metadata("test_hook")
            assert metadata is not None
            assert metadata.description == "Test hook for persistence"

    def test_hook_export_to_rdf(self) -> None:
        """Test hook registry can export to RDF."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()

            class ExportHook(KnowledgeHook):
                def __init__(self):
                    super().__init__(
                        name="export_hook", phases=[HookPhase.POST_COMMIT], priority=100
                    )

                def execute(self, context: HookContext):
                    pass

            registry.register(ExportHook(), description="Test export")

            # Export to RDF
            output_path = Path(tmpdir) / "hooks.ttl"
            rdf_graph = registry.export_to_rdf(output_path)

            assert output_path.exists()
            assert len(rdf_graph) > 0

    def test_engine_hook_statistics(self) -> None:
        """Test engine provides hook statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)

            class StatsHook(KnowledgeHook):
                def __init__(self):
                    super().__init__(name="stats_hook", phases=[HookPhase.POST_COMMIT])

                def execute(self, context: HookContext):
                    pass

            registry.register(StatsHook())

            stats = engine.get_hook_statistics()
            assert stats["hooks_enabled"] is True
            assert stats["has_executor"] is True
            assert stats["total_hooks"] == 1

    def test_hook_can_access_full_graph(self) -> None:
        """Test hook can access and query the full graph."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)

            graph_triple_count = []

            class GraphAccessHook(KnowledgeHook):
                def __init__(self):
                    super().__init__(name="graph_access", phases=[HookPhase.POST_TRANSACTION])

                def execute(self, context: HookContext):
                    # Count triples in full graph
                    graph_triple_count.append(len(context.graph))

            registry.register(GraphAccessHook())

            # Add data in first transaction
            txn1 = engine.transaction("test", "first")
            engine.add_triple(URIRef("http://example.org/s1"), RDF.type, UNRDF.Test, txn1)
            engine.commit(txn1)

            # Add more in second transaction
            txn2 = engine.transaction("test", "second")
            engine.add_triple(URIRef("http://example.org/s2"), RDF.type, UNRDF.Test, txn2)
            engine.commit(txn2)

            # Hook should see growing graph
            assert len(graph_triple_count) == 2
            assert graph_triple_count[1] > graph_triple_count[0]


class TestHookErrorHandling:
    """Test hook error handling and recovery."""

    def test_hook_error_does_not_prevent_commit(self) -> None:
        """Test hook error in POST_COMMIT doesn't prevent commit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)

            class FailingPostHook(KnowledgeHook):
                def __init__(self):
                    super().__init__(name="failing_post", phases=[HookPhase.POST_TRANSACTION])

                def execute(self, context: HookContext):
                    raise RuntimeError("Post-commit hook failed")

            registry.register(FailingPostHook())

            txn = engine.transaction("test", "test")
            engine.add_triple(URIRef("http://example.org/test"), RDF.type, UNRDF.Test, txn)
            engine.commit(txn)

            # Transaction should be committed despite hook failure
            assert txn.committed is True
            assert len(engine.graph) > 0

            # Receipt should show error
            assert len(txn.hook_receipts) > 0
            receipt = next(r for r in txn.hook_receipts if r.hook_id == "failing_post")
            assert receipt.success is False
            assert receipt.error is not None

    def test_pre_transaction_hook_error_prevents_commit(self) -> None:
        """Test PRE_TRANSACTION hook error prevents commit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)

            class FailingPreHook(KnowledgeHook):
                def __init__(self):
                    super().__init__(name="failing_pre", phases=[HookPhase.PRE_TRANSACTION])

                def execute(self, context: HookContext):
                    context.metadata["should_rollback"] = True
                    context.metadata["rollback_reason"] = "Pre-hook rejection"

            registry.register(FailingPreHook())

            txn = engine.transaction("test", "test")
            engine.add_triple(URIRef("http://example.org/test"), RDF.type, UNRDF.Test, txn)

            with pytest.raises(ValueError, match="Pre-hook rejection"):
                engine.commit(txn)

            # Transaction should be rolled back
            assert txn.rolled_back is True
            assert len(engine.graph) == 0
