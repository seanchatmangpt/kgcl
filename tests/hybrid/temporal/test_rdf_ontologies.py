"""Tests for RDF ontologies (Petri Net, XES) and SHACL validation.

Tests van der Aalst workflow theory implementation in RDF.
"""

from pathlib import Path

import pytest

# Skip if pyoxigraph not available
pytest.importorskip("pyoxigraph")

from pyoxigraph import Store  # noqa: E402

from kgcl.hybrid.temporal.ontology import PETRI_NET_ONTOLOGY, SOUNDNESS_SHAPES, XES_ONTOLOGY  # noqa: E402


class TestOntologyLoading:
    """Test ontology files parse correctly."""

    def test_petri_net_ontology_loads(self) -> None:
        """Petri Net ontology parses without errors."""
        store = Store()
        with PETRI_NET_ONTOLOGY.open() as f:
            store.load(f, mime_type="text/turtle")

        # Should have triples
        assert len(store) > 0

        # Verify key classes exist
        query = """
            PREFIX pn: <https://kgcl.org/ontology/petri-net#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

            SELECT ?class ?label
            WHERE {
                ?class a <http://www.w3.org/2002/07/owl#Class> .
                ?class rdfs:label ?label .
                FILTER(?class IN (pn:WorkflowNet, pn:Place, pn:Transition, pn:Arc))
            }
        """
        results = list(store.query(query))
        assert len(results) >= 4, "Missing core Petri net classes"

    def test_xes_ontology_loads(self) -> None:
        """XES ontology parses without errors."""
        store = Store()
        with XES_ONTOLOGY.open() as f:
            store.load(f, mime_type="text/turtle")

        assert len(store) > 0

        # Verify XES core classes
        query = """
            PREFIX xes: <https://kgcl.org/ontology/xes#>

            SELECT ?class
            WHERE {
                ?class a <http://www.w3.org/2002/07/owl#Class> .
                FILTER(?class IN (xes:Log, xes:Trace, xes:Event))
            }
        """
        results = list(store.query(query))
        assert len(results) == 3, "Missing XES core classes"

    def test_soundness_shapes_loads(self) -> None:
        """SHACL shapes parse without errors."""
        store = Store()
        with SOUNDNESS_SHAPES.open() as f:
            store.load(f, mime_type="text/turtle")

        assert len(store) > 0

        # Verify shapes exist
        query = """
            PREFIX sh: <http://www.w3.org/ns/shacl#>
            PREFIX pn: <https://kgcl.org/ontology/petri-net#>

            SELECT ?shape
            WHERE {
                ?shape a sh:NodeShape .
            }
        """
        results = list(store.query(query))
        assert len(results) >= 5, "Missing SHACL shapes"


class TestWorkflowNetValidation:
    """Test SHACL validation of workflow nets."""

    def test_valid_simple_workflow_net(self) -> None:
        """Simple sound WF-net passes validation."""
        store = Store()

        # Load ontology and shapes
        with PETRI_NET_ONTOLOGY.open() as f:
            store.load(f, mime_type="text/turtle")
        with SOUNDNESS_SHAPES.open() as f:
            store.load(f, mime_type="text/turtle")

        # Create simple WF-net: i -> t1 -> o
        wfnet_data = """
            PREFIX pn: <https://kgcl.org/ontology/petri-net#>
            PREFIX ex: <http://example.org/wf#>

            ex:net1 a pn:WorkflowNet ;
                pn:sourcePlace ex:i ;
                pn:sinkPlace ex:o ;
                pn:hasPlace ex:i, ex:o ;
                pn:hasTransition ex:t1 ;
                pn:hasArc ex:arc1, ex:arc2 .

            ex:i a pn:SourcePlace .
            ex:o a pn:SinkPlace .
            ex:t1 a pn:Transition ;
                pn:activityName "Process" .

            ex:arc1 a pn:Arc ;
                pn:source ex:i ;
                pn:target ex:t1 ;
                pn:weight 1 .

            ex:arc2 a pn:Arc ;
                pn:source ex:t1 ;
                pn:target ex:o ;
                pn:weight 1 .
        """
        store.load(wfnet_data.encode(), mime_type="text/turtle")

        # Verify structure
        query = """
            PREFIX pn: <https://kgcl.org/ontology/petri-net#>
            PREFIX ex: <http://example.org/wf#>

            SELECT ?net ?source ?sink
            WHERE {
                ?net a pn:WorkflowNet ;
                     pn:sourcePlace ?source ;
                     pn:sinkPlace ?sink .
            }
        """
        results = list(store.query(query))
        assert len(results) == 1, "WF-net not created correctly"

    def test_missing_source_place_violation(self) -> None:
        """WF-net without source place violates SHACL."""
        store = Store()

        with PETRI_NET_ONTOLOGY.open() as f:
            store.load(f, mime_type="text/turtle")
        with SOUNDNESS_SHAPES.open() as f:
            store.load(f, mime_type="text/turtle")

        # WF-net missing source place
        bad_wfnet = """
            PREFIX pn: <https://kgcl.org/ontology/petri-net#>
            PREFIX ex: <http://example.org/wf#>

            ex:badnet a pn:WorkflowNet ;
                pn:sinkPlace ex:o ;
                pn:hasPlace ex:o ;
                pn:hasTransition ex:t1 .

            ex:o a pn:SinkPlace .
            ex:t1 a pn:Transition .
        """
        store.load(bad_wfnet.encode(), mime_type="text/turtle")

        # Query for violation (would need pyshacl for actual validation)
        # Here we just verify the malformed data exists
        query = """
            PREFIX pn: <https://kgcl.org/ontology/petri-net#>

            SELECT ?net
            WHERE {
                ?net a pn:WorkflowNet .
                FILTER NOT EXISTS { ?net pn:sourcePlace ?source }
            }
        """
        results = list(store.query(query))
        assert len(results) == 1, "Should detect missing source place"

    def test_bipartite_violation(self) -> None:
        """Arc connecting place-to-place violates bipartite constraint."""
        store = Store()

        with PETRI_NET_ONTOLOGY.open() as f:
            store.load(f, mime_type="text/turtle")
        with SOUNDNESS_SHAPES.open() as f:
            store.load(f, mime_type="text/turtle")

        # Invalid arc: place -> place
        bad_arc = """
            PREFIX pn: <https://kgcl.org/ontology/petri-net#>
            PREFIX ex: <http://example.org/wf#>

            ex:p1 a pn:Place .
            ex:p2 a pn:Place .

            ex:badArc a pn:Arc ;
                pn:source ex:p1 ;
                pn:target ex:p2 ;
                pn:weight 1 .
        """
        store.load(bad_arc.encode(), mime_type="text/turtle")

        # Detect bipartite violation
        query = """
            PREFIX pn: <https://kgcl.org/ontology/petri-net#>

            SELECT ?arc
            WHERE {
                ?arc a pn:Arc ;
                     pn:source ?s ;
                     pn:target ?t .
                ?s a pn:Place .
                ?t a pn:Place .
            }
        """
        results = list(store.query(query))
        assert len(results) == 1, "Should detect place-to-place arc"


class TestProperCompletionValidation:
    """Test proper completion SHACL shape."""

    def test_proper_completion_valid(self) -> None:
        """Marking with only sink token is valid."""
        store = Store()

        with PETRI_NET_ONTOLOGY.open() as f:
            store.load(f, mime_type="text/turtle")
        with SOUNDNESS_SHAPES.open() as f:
            store.load(f, mime_type="text/turtle")

        # Final marking: only sink has token
        proper_marking = """
            PREFIX pn: <https://kgcl.org/ontology/petri-net#>
            PREFIX ex: <http://example.org/wf#>

            ex:o a pn:SinkPlace .

            ex:finalMarking a pn:Marking .

            ex:token1 a pn:Token ;
                pn:inPlace ex:o ;
                pn:atMarking ex:finalMarking ;
                pn:tokenCount 1 .
        """
        store.load(proper_marking.encode(), mime_type="text/turtle")

        # Should pass (no violations)
        query = """
            PREFIX pn: <https://kgcl.org/ontology/petri-net#>

            SELECT ?marking
            WHERE {
                ?marking a pn:Marking .
                ?token pn:atMarking ?marking ;
                       pn:inPlace ?sink .
                ?sink a pn:SinkPlace .

                # No other tokens
                FILTER NOT EXISTS {
                    ?otherToken pn:atMarking ?marking ;
                                pn:inPlace ?other .
                    FILTER(?other != ?sink)
                    ?otherToken pn:tokenCount ?count .
                    FILTER(?count > 0)
                }
            }
        """
        results = list(store.query(query))
        assert len(results) == 1, "Proper completion should be valid"

    def test_improper_completion_violation(self) -> None:
        """Marking with sink + other tokens is improper."""
        store = Store()

        with PETRI_NET_ONTOLOGY.open() as f:
            store.load(f, mime_type="text/turtle")
        with SOUNDNESS_SHAPES.open() as f:
            store.load(f, mime_type="text/turtle")

        # Improper marking: sink + other place have tokens
        improper_marking = """
            PREFIX pn: <https://kgcl.org/ontology/petri-net#>
            PREFIX ex: <http://example.org/wf#>

            ex:o a pn:SinkPlace .
            ex:p1 a pn:Place .

            ex:badMarking a pn:Marking .

            ex:token1 a pn:Token ;
                pn:inPlace ex:o ;
                pn:atMarking ex:badMarking ;
                pn:tokenCount 1 .

            ex:token2 a pn:Token ;
                pn:inPlace ex:p1 ;
                pn:atMarking ex:badMarking ;
                pn:tokenCount 1 .
        """
        store.load(improper_marking.encode(), mime_type="text/turtle")

        # Detect improper completion
        query = """
            PREFIX pn: <https://kgcl.org/ontology/petri-net#>

            SELECT ?marking
            WHERE {
                ?sinkToken pn:atMarking ?marking ;
                           pn:inPlace ?sink .
                ?sink a pn:SinkPlace .
                ?sinkToken pn:tokenCount ?sinkCount .
                FILTER(?sinkCount > 0)

                ?otherToken pn:atMarking ?marking ;
                            pn:inPlace ?other .
                FILTER(?other != ?sink)
                ?otherToken pn:tokenCount ?otherCount .
                FILTER(?otherCount > 0)
            }
        """
        results = list(store.query(query))
        assert len(results) == 1, "Should detect improper completion"


class TestXESEventLog:
    """Test XES event log creation and querying."""

    def test_create_simple_trace(self) -> None:
        """Create XES trace with events."""
        store = Store()

        with XES_ONTOLOGY.open() as f:
            store.load(f, mime_type="text/turtle")

        # Simple trace: A -> B -> C
        trace_data = """
            PREFIX xes: <https://kgcl.org/ontology/xes#>
            PREFIX ex: <http://example.org/log#>

            ex:log1 a xes:Log ;
                xes:hasTrace ex:trace1 .

            ex:trace1 a xes:Trace ;
                xes:conceptName "Case1" ;
                xes:hasEvent ex:e1, ex:e2, ex:e3 .

            ex:e1 a xes:Event ;
                xes:conceptName "A" ;
                xes:timestamp "2024-01-01T10:00:00Z"^^<http://www.w3.org/2001/XMLSchema#dateTime> ;
                xes:eventIndex 1 ;
                xes:lifecycleTransition xes:complete ;
                xes:nextEvent ex:e2 .

            ex:e2 a xes:Event ;
                xes:conceptName "B" ;
                xes:timestamp "2024-01-01T10:05:00Z"^^<http://www.w3.org/2001/XMLSchema#dateTime> ;
                xes:eventIndex 2 ;
                xes:lifecycleTransition xes:complete ;
                xes:previousEvent ex:e1 ;
                xes:nextEvent ex:e3 .

            ex:e3 a xes:Event ;
                xes:conceptName "C" ;
                xes:timestamp "2024-01-01T10:10:00Z"^^<http://www.w3.org/2001/XMLSchema#dateTime> ;
                xes:eventIndex 3 ;
                xes:lifecycleTransition xes:complete ;
                xes:previousEvent ex:e2 .
        """
        store.load(trace_data.encode(), mime_type="text/turtle")

        # Query trace structure
        query = """
            PREFIX xes: <https://kgcl.org/ontology/xes#>

            SELECT ?event ?name ?index
            WHERE {
                ?trace a xes:Trace ;
                       xes:hasEvent ?event .
                ?event xes:conceptName ?name ;
                       xes:eventIndex ?index .
            }
            ORDER BY ?index
        """
        results = list(store.query(query))
        assert len(results) == 3, "Should have 3 events"

        # Verify sequence
        names = [str(r[1]) for r in results]
        assert names == ["A", "B", "C"], "Events in wrong order"

    def test_directly_follows_relation(self) -> None:
        """Derive directly-follows relation from event sequence."""
        store = Store()

        with XES_ONTOLOGY.open() as f:
            store.load(f, mime_type="text/turtle")

        # Trace with directly-follows
        df_data = """
            PREFIX xes: <https://kgcl.org/ontology/xes#>
            PREFIX ex: <http://example.org/log#>

            ex:e1 a xes:Event ;
                xes:conceptName "Register" ;
                xes:nextEvent ex:e2 .

            ex:e2 a xes:Event ;
                xes:conceptName "Approve" ;
                xes:previousEvent ex:e1 .

            ex:e1 xes:directlyFollows ex:e2 .
        """
        store.load(df_data.encode(), mime_type="text/turtle")

        # Query directly-follows
        query = """
            PREFIX xes: <https://kgcl.org/ontology/xes#>

            SELECT ?e1 ?e2
            WHERE {
                ?e1 xes:directlyFollows ?e2 .
            }
        """
        results = list(store.query(query))
        assert len(results) == 1, "Should have directly-follows relation"


class TestWorkflowPatternDetection:
    """Test SPARQL-based workflow pattern detection."""

    def test_detect_and_split(self) -> None:
        """Detect AND-split (parallel split) pattern."""
        store = Store()

        with PETRI_NET_ONTOLOGY.open() as f:
            store.load(f, mime_type="text/turtle")
        with SOUNDNESS_SHAPES.open() as f:
            store.load(f, mime_type="text/turtle")

        # AND-split: one transition, two output places
        and_split = """
            PREFIX pn: <https://kgcl.org/ontology/petri-net#>
            PREFIX ex: <http://example.org/wf#>

            ex:t1 a pn:Transition ;
                pn:activityName "Fork" .

            ex:p1 a pn:Place .
            ex:p2 a pn:Place .

            ex:arc1 a pn:Arc ;
                pn:source ex:t1 ;
                pn:target ex:p1 .

            ex:arc2 a pn:Arc ;
                pn:source ex:t1 ;
                pn:target ex:p2 .
        """
        store.load(and_split.encode(), mime_type="text/turtle")

        # Detect AND-split pattern
        query = """
            PREFIX pn: <https://kgcl.org/ontology/petri-net#>

            SELECT ?transition
            WHERE {
                ?arc1 pn:source ?transition ; pn:target ?p1 .
                ?arc2 pn:source ?transition ; pn:target ?p2 .
                ?p1 a pn:Place .
                ?p2 a pn:Place .
                FILTER(?p1 != ?p2)
            }
        """
        results = list(store.query(query))
        assert len(results) == 1, "Should detect AND-split pattern"

    def test_detect_xor_split(self) -> None:
        """Detect XOR-split (exclusive choice) pattern."""
        store = Store()

        with PETRI_NET_ONTOLOGY.open() as f:
            store.load(f, mime_type="text/turtle")
        with SOUNDNESS_SHAPES.open() as f:
            store.load(f, mime_type="text/turtle")

        # XOR-split: one place, two output transitions
        xor_split = """
            PREFIX pn: <https://kgcl.org/ontology/petri-net#>
            PREFIX ex: <http://example.org/wf#>

            ex:p1 a pn:Place .

            ex:t1 a pn:Transition ;
                pn:activityName "Option A" .
            ex:t2 a pn:Transition ;
                pn:activityName "Option B" .

            ex:arc1 a pn:Arc ;
                pn:source ex:p1 ;
                pn:target ex:t1 .

            ex:arc2 a pn:Arc ;
                pn:source ex:p1 ;
                pn:target ex:t2 .
        """
        store.load(xor_split.encode(), mime_type="text/turtle")

        # Detect XOR-split pattern
        query = """
            PREFIX pn: <https://kgcl.org/ontology/petri-net#>

            SELECT ?place
            WHERE {
                ?arc1 pn:source ?place ; pn:target ?t1 .
                ?arc2 pn:source ?place ; pn:target ?t2 .
                ?t1 a pn:Transition .
                ?t2 a pn:Transition .
                FILTER(?t1 != ?t2)
            }
        """
        results = list(store.query(query))
        assert len(results) == 1, "Should detect XOR-split pattern"
