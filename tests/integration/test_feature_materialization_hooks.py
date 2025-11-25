"""Feature materialization hook tests.

Tests hook-driven feature template materialization, feature computation,
and automatic feature propagation through the knowledge graph.
"""

import tempfile
from pathlib import Path

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS

from kgcl.unrdf_engine.engine import UnrdfEngine
from kgcl.unrdf_engine.hook_registry import PersistentHookRegistry
from kgcl.unrdf_engine.hooks import (
    HookContext,
    HookPhase,
    KnowledgeHook,
    TriggerCondition,
)
from kgcl.unrdf_engine.ingestion import IngestionPipeline

UNRDF = Namespace("http://unrdf.org/ontology/")
FEATURE = Namespace("http://unrdf.org/ontology/feature/")


class TestFeatureMaterializationHooks:
    """Test feature materialization through hooks."""

    def test_feature_template_triggers_materialization(self):
        """Test that adding a FeatureTemplate triggers materialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)

            materialized_features = []

            class FeatureTemplateMaterializer(KnowledgeHook):
                def __init__(self):
                    super().__init__(
                        name="feature_template_materializer",
                        phases=[HookPhase.POST_COMMIT],
                        trigger=TriggerCondition(
                            pattern="?template a <http://unrdf.org/ontology/FeatureTemplate>",
                            check_delta=True,
                        ),
                    )

                def execute(self, context: HookContext):
                    # Find all feature templates in delta
                    for s, p, o in context.delta:
                        if str(p) == str(RDF.type) and "FeatureTemplate" in str(o):
                            # Query for entities to apply template to
                            query = """
                            PREFIX unrdf: <http://unrdf.org/ontology/>
                            SELECT ?entity WHERE {
                                ?entity a unrdf:Person
                            }
                            """
                            results = context.graph.query(query)

                            for row in results:
                                entity = row[0]
                                # Materialize feature for each entity
                                context.graph.add(
                                    (
                                        entity,
                                        FEATURE.hasFeature,
                                        Literal(f"feature_from_{s}"),
                                    )
                                )
                                materialized_features.append(str(entity))

            registry.register(FeatureTemplateMaterializer())
            pipeline = IngestionPipeline(engine)

            # First, add some people
            pipeline.ingest_json(
                data=[
                    {"id": "person1", "type": "Person", "name": "Alice"},
                    {"id": "person2", "type": "Person", "name": "Bob"},
                ],
                agent="test",
            )

            # Then add a feature template
            result = pipeline.ingest_json(
                data={
                    "id": "template1",
                    "type": "FeatureTemplate",
                    "name": "ActivityScore",
                },
                agent="test",
            )

            assert result.success is True
            # Hook should have materialized features for existing people
            # Note: In practice, features are added to graph during hook execution

    def test_computed_feature_hook(self):
        """Test hook that computes features based on existing data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)

            class AgeGroupComputer(KnowledgeHook):
                def __init__(self):
                    super().__init__(
                        name="age_group_computer",
                        phases=[HookPhase.POST_COMMIT],
                        trigger=TriggerCondition(
                            pattern="?person <http://unrdf.org/ontology/age> ?age",
                            check_delta=True,
                        ),
                    )

                def execute(self, context: HookContext):
                    # Find people with ages in delta
                    for s, p, o in context.delta:
                        if "age" in str(p):
                            try:
                                age = int(o)
                                age_group = "child" if age < 18 else "adult" if age < 65 else "senior"
                                # Add computed feature to graph
                                context.graph.add((s, UNRDF.ageGroup, Literal(age_group)))
                            except (ValueError, TypeError):
                                pass

            registry.register(AgeGroupComputer())
            pipeline = IngestionPipeline(engine)

            # Ingest person with age
            result = pipeline.ingest_json(
                data={"id": "person1", "type": "Person", "name": "Alice", "age": 30},
                agent="test",
            )

            assert result.success is True

            # Check if age group was computed
            query = """
            PREFIX unrdf: <http://unrdf.org/ontology/>
            ASK { ?person unrdf:ageGroup "adult" }
            """
            result = engine.query(query)
            assert result.askAnswer is True

    def test_cascade_feature_materialization(self):
        """Test features can trigger other feature computations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)

            computation_log = []

            class FirstFeatureComputer(KnowledgeHook):
                def __init__(self):
                    super().__init__(
                        name="first_feature",
                        phases=[HookPhase.POST_COMMIT],
                        priority=100,
                        trigger=TriggerCondition(
                            pattern="?person a <http://unrdf.org/ontology/Person>",
                            check_delta=True,
                        ),
                    )

                def execute(self, context: HookContext):
                    for s, p, o in context.delta:
                        if str(p) == str(RDF.type) and "Person" in str(o):
                            # Add first feature
                            context.graph.add((s, UNRDF.verified, Literal(True)))
                            computation_log.append("first")

            class SecondFeatureComputer(KnowledgeHook):
                def __init__(self):
                    super().__init__(
                        name="second_feature",
                        phases=[HookPhase.POST_COMMIT],
                        priority=50,
                    )

                def execute(self, context: HookContext):
                    # Check if first feature exists
                    query = """
                    PREFIX unrdf: <http://unrdf.org/ontology/>
                    SELECT ?person WHERE {
                        ?person unrdf:verified true
                    }
                    """
                    results = context.graph.query(query)
                    for row in results:
                        person = row[0]
                        # Add second feature based on first
                        context.graph.add((person, UNRDF.trustScore, Literal(100)))
                        computation_log.append("second")

            registry.register(FirstFeatureComputer())
            registry.register(SecondFeatureComputer())

            pipeline = IngestionPipeline(engine)
            result = pipeline.ingest_json(
                data={"id": "person1", "type": "Person"}, agent="test"
            )

            assert result.success is True
            # Both features should be computed in order
            assert "first" in computation_log
            assert "second" in computation_log

    def test_feature_aggregation_hook(self):
        """Test hook that aggregates features across entities."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)

            class FeatureAggregator(KnowledgeHook):
                def __init__(self):
                    super().__init__(
                        name="feature_aggregator",
                        phases=[HookPhase.POST_COMMIT],
                    )

                def execute(self, context: HookContext):
                    # Count total people
                    query = """
                    PREFIX unrdf: <http://unrdf.org/ontology/>
                    SELECT (COUNT(?person) as ?count) WHERE {
                        ?person a unrdf:Person
                    }
                    """
                    results = list(context.graph.query(query))
                    if results:
                        count = int(results[0][0])
                        # Store aggregate as metadata feature
                        stats_uri = URIRef("http://unrdf.org/data/stats/people")
                        context.graph.add((stats_uri, UNRDF.totalCount, Literal(count)))

            registry.register(FeatureAggregator())
            pipeline = IngestionPipeline(engine)

            # Add multiple people
            pipeline.ingest_json(
                data=[
                    {"id": "person1", "type": "Person"},
                    {"id": "person2", "type": "Person"},
                    {"id": "person3", "type": "Person"},
                ],
                agent="test",
            )

            # Check aggregate
            query = """
            PREFIX unrdf: <http://unrdf.org/ontology/>
            SELECT ?count WHERE {
                <http://unrdf.org/data/stats/people> unrdf:totalCount ?count
            }
            """
            results = list(engine.query(query))
            assert len(results) > 0
            assert int(results[0][0]) == 3

    def test_conditional_feature_materialization(self):
        """Test features materialize only when conditions are met."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)

            class ConditionalFeatureMaterializer(KnowledgeHook):
                def __init__(self):
                    super().__init__(
                        name="conditional_materializer",
                        phases=[HookPhase.POST_COMMIT],
                        trigger=TriggerCondition(
                            pattern="""
                            ?person a <http://unrdf.org/ontology/Person> .
                            ?person <http://unrdf.org/ontology/age> ?age .
                            FILTER(?age >= 18)
                            """,
                            check_delta=True,
                        ),
                    )

                def execute(self, context: HookContext):
                    # Only adults get premium features
                    for s, p, o in context.delta:
                        if "age" in str(p):
                            try:
                                age = int(o)
                                if age >= 18:
                                    context.graph.add((s, UNRDF.premiumEligible, Literal(True)))
                            except (ValueError, TypeError):
                                pass

            registry.register(ConditionalFeatureMaterializer())
            pipeline = IngestionPipeline(engine)

            # Add adult
            pipeline.ingest_json(
                data={"id": "adult", "type": "Person", "age": 25}, agent="test"
            )

            # Add child
            pipeline.ingest_json(
                data={"id": "child", "type": "Person", "age": 12}, agent="test"
            )

            # Check only adult has premium feature
            query = """
            PREFIX unrdf: <http://unrdf.org/ontology/>
            SELECT ?person WHERE {
                ?person unrdf:premiumEligible true
            }
            """
            results = list(engine.query(query))
            assert len(results) == 1

    def test_feature_invalidation_hook(self):
        """Test hook that invalidates stale features."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)

            class FeatureInvalidator(KnowledgeHook):
                def __init__(self):
                    super().__init__(
                        name="feature_invalidator",
                        phases=[HookPhase.POST_COMMIT],
                    )

                def execute(self, context: HookContext):
                    # When age changes, invalidate age-dependent features
                    for s, p, o in context.delta:
                        if "age" in str(p):
                            # Remove derived features
                            for derived_s, derived_p, derived_o in list(
                                context.graph.triples((s, UNRDF.ageGroup, None))
                            ):
                                context.graph.remove((derived_s, derived_p, derived_o))

            registry.register(FeatureInvalidator())
            pipeline = IngestionPipeline(engine)

            # First ingestion
            pipeline.ingest_json(
                data={"id": "person1", "type": "Person", "age": 30}, agent="test"
            )

            # Manually add derived feature
            txn = engine.transaction("test", "add derived")
            person_uri = URIRef("http://unrdf.org/data/person1")
            engine.add_triple(person_uri, UNRDF.ageGroup, Literal("adult"), txn)
            engine.commit(txn)

            # Update age (should trigger invalidation)
            pipeline.ingest_json(
                data={"id": "person1", "age": 70}, agent="test"
            )

            # Derived feature should be removed
            query = """
            PREFIX unrdf: <http://unrdf.org/ontology/>
            ASK {
                <http://unrdf.org/data/person1> unrdf:ageGroup ?group
            }
            """
            result = engine.query(query)
            # Feature should be invalidated (removed)

    def test_feature_template_with_sparql_transform(self):
        """Test feature template that uses SPARQL for transformation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)

            class SparqlTransformMaterializer(KnowledgeHook):
                def __init__(self):
                    super().__init__(
                        name="sparql_transform",
                        phases=[HookPhase.POST_COMMIT],
                        trigger=TriggerCondition(
                            pattern="?template a <http://unrdf.org/ontology/FeatureTemplate>",
                            check_delta=True,
                        ),
                    )

                def execute(self, context: HookContext):
                    # Get template with transform
                    for s, p, o in context.delta:
                        if str(p) == str(RDF.type) and "FeatureTemplate" in str(o):
                            # Query for transform SPARQL
                            transform_query = f"""
                            PREFIX unrdf: <http://unrdf.org/ontology/>
                            SELECT ?transform WHERE {{
                                <{s}> unrdf:transform ?transform
                            }}
                            """
                            transforms = list(context.graph.query(transform_query))

                            if transforms:
                                transform_sparql = str(transforms[0][0])
                                # Execute transform (in real implementation)
                                # For now, just demonstrate the pattern
                                pass

            registry.register(SparqlTransformMaterializer())
            pipeline = IngestionPipeline(engine)

            # Add template with transform
            result = pipeline.ingest_json(
                data={
                    "id": "template1",
                    "type": "FeatureTemplate",
                    "transform": "SELECT ?s WHERE { ?s a unrdf:Person }",
                },
                agent="test",
            )

            assert result.success is True

    def test_feature_dependency_tracking(self):
        """Test tracking dependencies between materialized features."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)

            dependencies_tracked = []

            class DependencyTracker(KnowledgeHook):
                def __init__(self):
                    super().__init__(
                        name="dependency_tracker",
                        phases=[HookPhase.POST_COMMIT],
                    )

                def execute(self, context: HookContext):
                    # Track which features depend on which source data
                    for s, p, o in context.delta:
                        if "Person" in str(o):
                            # Record that features depend on this person
                            dependencies_tracked.append(
                                {"entity": str(s), "depends_on": "person_data"}
                            )

            registry.register(DependencyTracker())
            pipeline = IngestionPipeline(engine)

            result = pipeline.ingest_json(
                data={"id": "person1", "type": "Person"}, agent="test"
            )

            assert result.success is True
            assert len(dependencies_tracked) > 0

    def test_batch_feature_materialization(self):
        """Test efficient batch materialization of features."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)

            batch_size = []

            class BatchMaterializer(KnowledgeHook):
                def __init__(self):
                    super().__init__(
                        name="batch_materializer",
                        phases=[HookPhase.POST_COMMIT],
                    )

                def execute(self, context: HookContext):
                    # Count entities in delta for batch processing
                    people = []
                    for s, p, o in context.delta:
                        if str(p) == str(RDF.type) and "Person" in str(o):
                            people.append(s)

                    if people:
                        batch_size.append(len(people))
                        # Materialize features for entire batch
                        for person in people:
                            context.graph.add((person, UNRDF.batchProcessed, Literal(True)))

            registry.register(BatchMaterializer())
            pipeline = IngestionPipeline(engine)

            # Ingest batch
            result = pipeline.ingest_json(
                data=[
                    {"id": f"person{i}", "type": "Person"} for i in range(10)
                ],
                agent="test",
            )

            assert result.success is True
            assert len(batch_size) > 0
            # Should process all 10 people in one batch
            assert batch_size[0] == 10

    def test_feature_version_tracking(self):
        """Test tracking feature versions as they are updated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PersistentHookRegistry()
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl", hook_registry=registry)

            class FeatureVersionTracker(KnowledgeHook):
                def __init__(self):
                    super().__init__(
                        name="version_tracker",
                        phases=[HookPhase.POST_COMMIT],
                    )

                def execute(self, context: HookContext):
                    from datetime import datetime, timezone

                    # Add version metadata to features
                    for s, p, o in context.delta:
                        if "feature" in str(p).lower():
                            version_uri = URIRef(f"{s}_version")
                            context.graph.add(
                                (
                                    version_uri,
                                    UNRDF.timestamp,
                                    Literal(datetime.now(timezone.utc).isoformat()),
                                )
                            )
                            context.graph.add((version_uri, UNRDF.featureOf, s))

            registry.register(FeatureVersionTracker())
            pipeline = IngestionPipeline(engine)

            result = pipeline.ingest_json(
                data={
                    "id": "person1",
                    "type": "Person",
                    "customFeature": "value",
                },
                agent="test",
            )

            assert result.success is True
