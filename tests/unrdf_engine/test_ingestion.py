"""Tests for ingestion pipeline."""

from __future__ import annotations

from rdflib import Literal, URIRef
from rdflib.namespace import RDF

from kgcl.unrdf_engine.engine import UNRDF, UnrdfEngine
from kgcl.unrdf_engine.hooks import (
    HookContext,
    HookExecutor,
    HookPhase,
    HookRegistry,
    KnowledgeHook,
)
from kgcl.unrdf_engine.ingestion import IngestionPipeline, IngestionResult
from kgcl.unrdf_engine.validation import ShaclValidator

EXPECTED_TRIPLES_ADDED = 10
BATCH_RESULT_COUNT = 3
ARRAY_TRIPLE_THRESHOLD = 3


class TestIngestionResult:
    """Test IngestionResult class."""

    def test_creation(self) -> None:
        """Test creating ingestion result."""
        result = IngestionResult(
            success=True, triples_added=EXPECTED_TRIPLES_ADDED, transaction_id="txn-1"
        )

        assert result.success
        assert result.triples_added == EXPECTED_TRIPLES_ADDED
        assert result.transaction_id == "txn-1"

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        result = IngestionResult(
            success=False,
            triples_added=0,
            transaction_id="txn-1",
            error="Validation failed",
        )

        result_dict = result.to_dict()

        assert not result_dict["success"]
        assert result_dict["triples_added"] == 0
        assert result_dict["error"] == "Validation failed"


class TestIngestionPipeline:
    """Test IngestionPipeline class."""

    def test_initialization(self) -> None:
        """Test pipeline initialization."""
        engine = UnrdfEngine()
        pipeline = IngestionPipeline(engine=engine)

        assert pipeline.engine == engine
        assert pipeline.validator is None
        assert pipeline.hook_executor is None

    def test_ingest_simple_json(self) -> None:
        """Test ingesting simple JSON object."""
        engine = UnrdfEngine()
        pipeline = IngestionPipeline(engine=engine, validate_on_ingest=False)

        data = {"type": "Person", "name": "Alice", "age": 30}

        result = pipeline.ingest_json(data=data, agent="test_agent")

        assert result.success
        assert result.triples_added > 0
        assert len(engine.graph) > 0

    def test_ingest_json_array(self) -> None:
        """Test ingesting JSON array."""
        engine = UnrdfEngine()
        pipeline = IngestionPipeline(engine=engine, validate_on_ingest=False)

        data = [{"type": "Person", "name": "Alice"}, {"type": "Person", "name": "Bob"}]

        result = pipeline.ingest_json(data=data, agent="test_agent")

        assert result.success
        assert result.triples_added > 0

    def test_ingest_nested_json(self) -> None:
        """Test ingesting nested JSON."""
        engine = UnrdfEngine()
        pipeline = IngestionPipeline(engine=engine, validate_on_ingest=False)

        data = {
            "type": "Person",
            "name": "Alice",
            "address": {"street": "123 Main St", "city": "Springfield"},
        }

        result = pipeline.ingest_json(data=data, agent="test_agent")

        assert result.success
        assert result.triples_added > 0

    def test_ingest_with_id(self) -> None:
        """Test ingesting with explicit ID."""
        engine = UnrdfEngine()
        pipeline = IngestionPipeline(engine=engine, validate_on_ingest=False)

        data = {"id": "person123", "type": "Person", "name": "Alice"}

        result = pipeline.ingest_json(data=data, agent="test_agent")

        assert result.success

        # Check that ID was used
        subject_uri = URIRef("http://unrdf.org/data/person123")
        assert (subject_uri, None, None) in engine.graph

    def test_ingest_with_custom_base_uri(self) -> None:
        """Test ingesting with custom base URI."""
        engine = UnrdfEngine()
        pipeline = IngestionPipeline(engine=engine, validate_on_ingest=False)

        data = {"id": "item1", "type": "Item"}

        result = pipeline.ingest_json(
            data=data, agent="test_agent", base_uri="http://example.org/"
        )

        assert result.success

        subject_uri = URIRef("http://example.org/item1")
        assert (subject_uri, None, None) in engine.graph

    def test_ingest_with_validation_success(self) -> None:
        """Test ingesting with successful validation."""
        engine = UnrdfEngine()
        validator = ShaclValidator()

        # Simple shape that allows anything
        shapes_ttl = """
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix ex: <http://example.org/> .

        ex:AnyShape a sh:NodeShape ;
            sh:targetClass ex:Person .
        """
        validator.load_shapes_from_string(shapes_ttl)

        pipeline = IngestionPipeline(
            engine=engine, validator=validator, validate_on_ingest=True
        )

        data = {"type": "Person", "name": "Alice"}

        result = pipeline.ingest_json(data=data, agent="test_agent")

        assert result.success
        assert result.validation_result is not None

    def test_ingest_with_validation_failure(self) -> None:
        """Test ingesting with validation failure - simplified."""
        engine = UnrdfEngine()
        validator = ShaclValidator()

        # Simple shape requiring name property (no datatype constraint to avoid SHACL issues)
        shapes_ttl = """
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix unrdf: <http://unrdf.org/ontology/> .

        unrdf:PersonShape a sh:NodeShape ;
            sh:targetClass unrdf:Person ;
            sh:property [
                sh:path unrdf:name ;
                sh:minCount 1 ;
            ] .
        """
        validator.load_shapes_from_string(shapes_ttl)

        pipeline = IngestionPipeline(
            engine=engine, validator=validator, validate_on_ingest=True
        )

        # Data missing required name
        data = {"type": "Person"}

        result = pipeline.ingest_json(data=data, agent="test_agent")

        assert not result.success
        assert result.error is not None
        assert "validation failed" in result.error.lower()

    def test_ingest_with_hooks(self) -> None:
        """Test ingesting with hooks enabled."""
        engine = UnrdfEngine()
        registry = HookRegistry()

        class TestHook(KnowledgeHook):
            def __init__(self) -> None:
                super().__init__(name="test_hook", phases=[HookPhase.POST_COMMIT])
                self.executed = False

            def execute(self, _context: HookContext) -> None:
                self.executed = True

        hook = TestHook()
        registry.register(hook)

        hook_executor = HookExecutor(registry)
        pipeline = IngestionPipeline(
            engine=engine, hook_executor=hook_executor, validate_on_ingest=False
        )

        data = {"type": "Person", "name": "Alice"}

        result = pipeline.ingest_json(data=data, agent="test_agent")

        assert result.success
        assert hook.executed
        assert result.hook_results is not None

    def test_ingest_batch(self) -> None:
        """Test batch ingestion."""
        engine = UnrdfEngine()
        pipeline = IngestionPipeline(engine=engine, validate_on_ingest=False)

        items = [{"type": "Item", "value": i} for i in range(250)]

        results = pipeline.ingest_batch(items=items, agent="test_agent", batch_size=100)

        # Should have 3 batches (100, 100, 50)
        assert len(results) == BATCH_RESULT_COUNT
        assert all(r.success for r in results)

    def test_ingest_array_values(self) -> None:
        """Test ingesting array values."""
        engine = UnrdfEngine()
        pipeline = IngestionPipeline(engine=engine, validate_on_ingest=False)

        data = {"type": "Person", "tags": ["developer", "engineer", "coder"]}

        result = pipeline.ingest_json(data=data, agent="test_agent")

        assert result.success
        # Should create multiple triples for array
        assert result.triples_added > ARRAY_TRIPLE_THRESHOLD

    def test_ingest_with_reason(self) -> None:
        """Test ingesting with reason for provenance."""
        engine = UnrdfEngine()
        pipeline = IngestionPipeline(engine=engine, validate_on_ingest=False)

        data = {"type": "Person", "name": "Alice"}

        result = pipeline.ingest_json(
            data=data, agent="test_agent", reason="Initial data load"
        )

        assert result.success

        # Check provenance
        all_prov = engine.get_all_provenance()
        assert len(all_prov) > 0
        assert any(p.reason == "Initial data load" for p in all_prov.values())

    def test_json_to_rdf_types(self) -> None:
        """Test JSON to RDF type conversion."""
        engine = UnrdfEngine()
        pipeline = IngestionPipeline(engine=engine, validate_on_ingest=False)

        data = {
            "type": "TestObject",
            "string_val": "text",
            "int_val": 42,
            "float_val": 3.14,
            "bool_val": True,
        }

        result = pipeline.ingest_json(data=data, agent="test_agent")

        assert result.success

        # Verify different literal types were created
        graph = engine.graph
        literals = [o for s, p, o in graph if isinstance(o, Literal)]

        assert len(literals) > 0
        # Should have different datatypes
        datatypes = {lit.datatype for lit in literals if lit.datatype}
        assert len(datatypes) > 1

    def test_materialize_features(self) -> None:
        """Test feature materialization."""
        engine = UnrdfEngine()
        pipeline = IngestionPipeline(engine=engine, validate_on_ingest=False)

        # Add a feature template
        template_uri = URIRef("http://unrdf.org/templates/test-template")
        txn = engine.transaction("test_agent")

        engine.add_triple(template_uri, RDF.type, UNRDF.FeatureTemplate, txn)
        engine.add_triple(template_uri, UNRDF.property, UNRDF.testProperty, txn)
        engine.commit(txn)

        # Add target entity
        target_uri = URIRef("http://unrdf.org/data/target1")
        txn2 = engine.transaction("test_agent")
        engine.add_triple(target_uri, RDF.type, UNRDF.Target, txn2)
        engine.commit(txn2)

        # Materialize
        result = pipeline.materialize_features(
            template_uri=template_uri,
            target_pattern="?target <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://unrdf.org/ontology/Target>",
            agent="test_agent",
        )

        assert result.success
        assert result.triples_added > 0

    def test_ingest_error_rollback(self) -> None:
        """Test that errors cause rollback."""
        engine = UnrdfEngine()

        # Create validator with constraint that will fail
        validator = ShaclValidator()
        shapes_ttl = """
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix unrdf: <http://unrdf.org/ontology/> .

        unrdf:StrictShape a sh:NodeShape ;
            sh:targetClass unrdf:Person ;
            sh:property [
                sh:path unrdf:name ;
                sh:minCount 2 ;
            ] .
        """
        validator.load_shapes_from_string(shapes_ttl)

        pipeline = IngestionPipeline(
            engine=engine, validator=validator, validate_on_ingest=True
        )

        # Data with only 1 name (needs 2)
        data = {"type": "Person", "name": "Alice"}

        initial_count = len(engine.graph)

        result = pipeline.ingest_json(data=data, agent="test_agent")

        assert not result.success
        # Graph should be unchanged
        assert len(engine.graph) == initial_count
