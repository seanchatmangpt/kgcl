"""Test suite for temporal ontology RDF files and SHACL validation.

Validates:
- Ontology files parse correctly (Turtle/N3 syntax)
- SHACL shapes validate valid events
- SHACL shapes reject invalid events
- Causal consistency detection
"""

import warnings
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pyshacl import validate

try:
    from pyoxigraph import RdfFormat, Store
except ImportError:
    pytest.skip("pyoxigraph not installed", allow_module_level=True)

from kgcl.hybrid.temporal.ontology import EVENT_TYPES, FULL_ONTOLOGY, TEMPORAL_LOGIC, TEMPORAL_ONTOLOGY, TEMPORAL_SHAPES

# Suppress deprecation warnings from rdflib (used by pyshacl)
# These are external library warnings we can't fix
warnings.filterwarnings("ignore", category=DeprecationWarning, module="rdflib")
warnings.filterwarnings("ignore", "Dataset.default_context is deprecated")


class TestOntologyParsing:
    """Test that all ontology files parse without errors."""

    def test_temporal_ontology_parses(self) -> None:
        """Temporal ontology must parse as valid Turtle."""
        store = Store()
        store.load(TEMPORAL_ONTOLOGY.encode(), RdfFormat.TURTLE)
        assert len(store) > 0, "Temporal ontology should contain triples"

    def test_event_types_ontology_parses(self) -> None:
        """Event types ontology must parse as valid Turtle."""
        store = Store()
        store.load(EVENT_TYPES.encode(), RdfFormat.TURTLE)
        assert len(store) > 0, "Event types ontology should contain triples"

    def test_temporal_shapes_parses(self) -> None:
        """SHACL shapes must parse as valid Turtle."""
        store = Store()
        store.load(TEMPORAL_SHAPES.encode(), RdfFormat.TURTLE)
        assert len(store) > 0, "SHACL shapes should contain triples"

    @pytest.mark.skip(reason="N3 syntax not supported by pyoxigraph (requires EYE reasoner)")
    def test_temporal_logic_parses(self) -> None:
        """N3 logic rules must parse as valid N3 (requires EYE reasoner)."""
        # N3 has advanced syntax ({...} for rules) not supported by Turtle parsers
        # This file is meant for EYE reasoner which supports full N3
        # Verifies N3 content is present (parsing requires EYE reasoner)
        assert len(TEMPORAL_LOGIC) > 0, "N3 logic file should not be empty"
        assert "@prefix ltl:" in TEMPORAL_LOGIC, "N3 file should have LTL prefix"

    def test_full_ontology_parses(self) -> None:
        """Combined ontology graph must parse correctly."""
        store = Store()
        store.load(FULL_ONTOLOGY.encode(), RdfFormat.TURTLE)
        assert len(store) > 0, "Full ontology should contain triples"


@pytest.mark.filterwarnings("ignore:Dataset.*is deprecated:DeprecationWarning")
class TestSHACLValidation:
    """Test SHACL shapes validate event data correctly."""

    def _create_valid_event_graph(
        self,
        event_id: str | None = None,
        event_hash: str | None = None,
        previous_hash: str = "",
        tick_number: int = 0,
        workflow_id: str | None = None,
        timestamp: str | None = None,
    ) -> str:
        """Create minimal valid event RDF graph for testing."""
        event_id = event_id or self._uuid7()
        event_hash = event_hash or "a" * 64  # Valid SHA-256
        workflow_id = workflow_id or str(uuid4())
        timestamp = timestamp or datetime.now(UTC).isoformat()

        return f"""
        @prefix evt: <http://kgcl.dev/ontology/event/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        <urn:event:{event_id}> a evt:WorkflowEvent ;
            evt:eventId "{event_id}" ;
            evt:eventHash "{event_hash}" ;
            evt:previousHash "{previous_hash}" ;
            evt:timestamp "{timestamp}"^^xsd:dateTime ;
            evt:tickNumber "{tick_number}"^^xsd:nonNegativeInteger ;
            evt:workflowId "{workflow_id}" .
        """

    def _uuid7(self) -> str:
        """Generate UUID v7 (time-ordered) for testing."""
        # UUID v7 has version bits set to 0111 in the time_hi_and_version field
        uid = uuid4()
        # Set version to 7 (0111 in binary = 0x7)
        uid_hex = uid.hex
        uuid7_hex = uid_hex[:12] + "7" + uid_hex[13:16] + uid_hex[16:]  # Set version nibble
        return str(UUID(uuid7_hex))

    def test_valid_event_passes_validation(self) -> None:
        """Valid event should pass all SHACL constraints."""
        event_graph = self._create_valid_event_graph()
        shapes_graph = TEMPORAL_SHAPES

        conforms, _, _ = validate(
            event_graph,
            shacl_graph=shapes_graph,
            data_graph_format="turtle",
            shacl_graph_format="turtle",
            inference="rdfs",
        )

        assert conforms, "Valid event should pass SHACL validation"

    def test_invalid_uuid_fails_validation(self) -> None:
        """Event with non-UUID v7 identifier should fail."""
        event_graph = self._create_valid_event_graph(event_id="not-a-valid-uuid-at-all")
        shapes_graph = TEMPORAL_SHAPES

        conforms, results_graph, _ = validate(
            event_graph,
            shacl_graph=shapes_graph,
            data_graph_format="turtle",
            shacl_graph_format="turtle",
            inference="rdfs",
        )

        assert not conforms, "Invalid UUID should fail validation"
        results_text = results_graph.serialize(format="turtle")
        assert "UUID v7" in results_text or "must be" in results_text, "Should mention UUID v7 requirement"

    def test_invalid_hash_length_fails_validation(self) -> None:
        """Event with wrong hash length should fail."""
        event_graph = self._create_valid_event_graph(event_hash="abc123")  # Too short
        shapes_graph = TEMPORAL_SHAPES

        conforms, results_graph, _ = validate(
            event_graph,
            shacl_graph=shapes_graph,
            data_graph_format="turtle",
            shacl_graph_format="turtle",
            inference="rdfs",
        )

        assert not conforms, "Invalid hash length should fail validation"
        results_text = results_graph.serialize(format="turtle")
        assert "64" in results_text or "SHA-256" in results_text, "Should mention 64-char SHA-256"

    def test_invalid_hash_characters_fails_validation(self) -> None:
        """Event hash with non-hex characters should fail."""
        event_graph = self._create_valid_event_graph(
            event_hash="x" * 64  # Invalid hex
        )
        shapes_graph = TEMPORAL_SHAPES

        conforms, _, _ = validate(
            event_graph,
            shacl_graph=shapes_graph,
            data_graph_format="turtle",
            shacl_graph_format="turtle",
            inference="rdfs",
        )

        assert not conforms, "Non-hex hash should fail validation"

    def test_negative_tick_number_fails_validation(self) -> None:
        """Tick number must be non-negative."""
        event_graph = self._create_valid_event_graph(tick_number=-5)
        shapes_graph = TEMPORAL_SHAPES

        conforms, _, _ = validate(
            event_graph,
            shacl_graph=shapes_graph,
            data_graph_format="turtle",
            shacl_graph_format="turtle",
            inference="rdfs",
        )

        assert not conforms, "Negative tick number should fail validation"

    def test_missing_required_field_fails_validation(self) -> None:
        """Event missing required fields should fail."""
        event_graph = """
        @prefix evt: <http://kgcl.dev/ontology/event/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        <urn:event:123> a evt:WorkflowEvent ;
            evt:eventId "00000000-0000-7000-8000-000000000001" .
        """
        shapes_graph = TEMPORAL_SHAPES

        conforms, _, _ = validate(
            event_graph,
            shacl_graph=shapes_graph,
            data_graph_format="turtle",
            shacl_graph_format="turtle",
            inference="rdfs",
        )

        assert not conforms, "Missing required fields should fail validation"


class TestCausalConsistency:
    """Test causal consistency SHACL shape detects violations."""

    def test_causal_predecessor_with_earlier_tick_is_valid(self) -> None:
        """Causal predecessor with earlier tick should be valid."""
        wf_id = str(uuid4())
        event_graph = f"""
        @prefix evt: <http://kgcl.dev/ontology/event/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        <urn:event:1> a evt:WorkflowEvent ;
            evt:eventId "00000000-0000-7000-8000-000000000001" ;
            evt:eventHash "{"a" * 64}" ;
            evt:previousHash "" ;
            evt:timestamp "2024-01-01T00:00:00Z"^^xsd:dateTime ;
            evt:tickNumber "0"^^xsd:nonNegativeInteger ;
            evt:workflowId "{wf_id}" .

        <urn:event:2> a evt:WorkflowEvent ;
            evt:eventId "00000000-0000-7000-8000-000000000002" ;
            evt:eventHash "{"b" * 64}" ;
            evt:previousHash "{"a" * 64}" ;
            evt:timestamp "2024-01-01T00:00:01Z"^^xsd:dateTime ;
            evt:tickNumber "1"^^xsd:nonNegativeInteger ;
            evt:workflowId "{wf_id}" ;
            evt:causedBy <urn:event:1> .
        """
        shapes_graph = TEMPORAL_SHAPES

        conforms, _, _ = validate(
            event_graph,
            shacl_graph=shapes_graph,
            data_graph_format="turtle",
            shacl_graph_format="turtle",
            inference="rdfs",
        )

        assert conforms, "Valid causal ordering should pass validation"

    def test_causal_predecessor_with_same_tick_fails(self) -> None:
        """Causal predecessor with same tick violates happens-before."""
        wf_id = str(uuid4())
        event_graph = f"""
        @prefix evt: <http://kgcl.dev/ontology/event/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        <urn:event:1> a evt:WorkflowEvent ;
            evt:eventId "00000000-0000-7000-8000-000000000001" ;
            evt:eventHash "{"a" * 64}" ;
            evt:previousHash "" ;
            evt:timestamp "2024-01-01T00:00:00Z"^^xsd:dateTime ;
            evt:tickNumber "5"^^xsd:nonNegativeInteger ;
            evt:workflowId "{wf_id}" .

        <urn:event:2> a evt:WorkflowEvent ;
            evt:eventId "00000000-0000-7000-8000-000000000002" ;
            evt:eventHash "{"b" * 64}" ;
            evt:previousHash "{"a" * 64}" ;
            evt:timestamp "2024-01-01T00:00:01Z"^^xsd:dateTime ;
            evt:tickNumber "5"^^xsd:nonNegativeInteger ;
            evt:workflowId "{wf_id}" ;
            evt:causedBy <urn:event:1> .
        """
        shapes_graph = TEMPORAL_SHAPES

        conforms, results_graph, _ = validate(
            event_graph,
            shacl_graph=shapes_graph,
            data_graph_format="turtle",
            shacl_graph_format="turtle",
            inference="rdfs",
        )

        assert not conforms, "Same tick number should violate causal consistency"
        results_text = results_graph.serialize(format="turtle")
        assert "happens-before" in results_text or "causal" in results_text.lower(), (
            "Should mention causal/happens-before violation"
        )

    def test_causal_predecessor_with_later_tick_fails(self) -> None:
        """Causal predecessor with later tick violates causality."""
        wf_id = str(uuid4())
        event_graph = f"""
        @prefix evt: <http://kgcl.dev/ontology/event/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        <urn:event:1> a evt:WorkflowEvent ;
            evt:eventId "00000000-0000-7000-8000-000000000001" ;
            evt:eventHash "{"a" * 64}" ;
            evt:previousHash "" ;
            evt:timestamp "2024-01-01T00:00:00Z"^^xsd:dateTime ;
            evt:tickNumber "10"^^xsd:nonNegativeInteger ;
            evt:workflowId "{wf_id}" .

        <urn:event:2> a evt:WorkflowEvent ;
            evt:eventId "00000000-0000-7000-8000-000000000002" ;
            evt:eventHash "{"b" * 64}" ;
            evt:previousHash "{"a" * 64}" ;
            evt:timestamp "2024-01-01T00:00:01Z"^^xsd:dateTime ;
            evt:tickNumber "5"^^xsd:nonNegativeInteger ;
            evt:workflowId "{wf_id}" ;
            evt:causedBy <urn:event:1> .
        """
        shapes_graph = TEMPORAL_SHAPES

        conforms, _, _ = validate(
            event_graph,
            shacl_graph=shapes_graph,
            data_graph_format="turtle",
            shacl_graph_format="turtle",
            inference="rdfs",
        )

        assert not conforms, "Later tick number should violate causal consistency"


class TestHashChainIntegrity:
    """Test hash chain validation (blockchain-style linking)."""

    def test_valid_hash_chain_passes(self) -> None:
        """Valid hash chain with matching previousHash/eventHash should pass."""
        wf_id = str(uuid4())
        event_graph = f"""
        @prefix evt: <http://kgcl.dev/ontology/event/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        <urn:event:1> a evt:WorkflowEvent ;
            evt:eventId "00000000-0000-7000-8000-000000000001" ;
            evt:eventHash "{"a" * 64}" ;
            evt:previousHash "" ;
            evt:timestamp "2024-01-01T00:00:00Z"^^xsd:dateTime ;
            evt:tickNumber "0"^^xsd:nonNegativeInteger ;
            evt:workflowId "{wf_id}" .

        <urn:event:2> a evt:WorkflowEvent ;
            evt:eventId "00000000-0000-7000-8000-000000000002" ;
            evt:eventHash "{"b" * 64}" ;
            evt:previousHash "{"a" * 64}" ;
            evt:timestamp "2024-01-01T00:00:01Z"^^xsd:dateTime ;
            evt:tickNumber "1"^^xsd:nonNegativeInteger ;
            evt:workflowId "{wf_id}" .
        """
        shapes_graph = TEMPORAL_SHAPES

        conforms, _, _ = validate(
            event_graph,
            shacl_graph=shapes_graph,
            data_graph_format="turtle",
            shacl_graph_format="turtle",
            inference="rdfs",
        )

        assert conforms, "Valid hash chain should pass validation"

    def test_broken_hash_chain_fails(self) -> None:
        """Hash chain with mismatched previousHash should fail."""
        wf_id = str(uuid4())
        event_graph = f"""
        @prefix evt: <http://kgcl.dev/ontology/event/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        <urn:event:1> a evt:WorkflowEvent ;
            evt:eventId "00000000-0000-7000-8000-000000000001" ;
            evt:eventHash "{"a" * 64}" ;
            evt:previousHash "" ;
            evt:timestamp "2024-01-01T00:00:00Z"^^xsd:dateTime ;
            evt:tickNumber "0"^^xsd:nonNegativeInteger ;
            evt:workflowId "{wf_id}" .

        <urn:event:2> a evt:WorkflowEvent ;
            evt:eventId "00000000-0000-7000-8000-000000000002" ;
            evt:eventHash "{"b" * 64}" ;
            evt:previousHash "{"x" * 64}" ;
            evt:timestamp "2024-01-01T00:00:01Z"^^xsd:dateTime ;
            evt:tickNumber "1"^^xsd:nonNegativeInteger ;
            evt:workflowId "{wf_id}" .
        """
        shapes_graph = TEMPORAL_SHAPES

        conforms, results_graph, _ = validate(
            event_graph,
            shacl_graph=shapes_graph,
            data_graph_format="turtle",
            shacl_graph_format="turtle",
            inference="rdfs",
        )

        assert not conforms, "Broken hash chain should fail validation"
        results_text = results_graph.serialize(format="turtle")
        assert "chain" in results_text.lower() or "hash" in results_text.lower(), "Should mention chain/hash violation"


@pytest.mark.filterwarnings("ignore:Dataset.*is deprecated:DeprecationWarning")
class TestEventTypeValidation:
    """Test event type-specific SHACL shapes."""

    def test_status_change_event_with_valid_status_passes(self) -> None:
        """StatusChangeEvent with valid status values should pass."""
        wf_id = str(uuid4())
        event_graph = f"""
        @prefix evt: <http://kgcl.dev/ontology/event/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        <urn:event:1> a evt:StatusChangeEvent ;
            evt:eventId "00000000-0000-7000-8000-000000000001" ;
            evt:eventHash "{"a" * 64}" ;
            evt:previousHash "" ;
            evt:timestamp "2024-01-01T00:00:00Z"^^xsd:dateTime ;
            evt:tickNumber "0"^^xsd:nonNegativeInteger ;
            evt:workflowId "{wf_id}" ;
            evt:taskId "task-123" ;
            evt:fromStatus "idle" ;
            evt:toStatus "enabled" .
        """
        shapes_graph = TEMPORAL_SHAPES

        conforms, _, _ = validate(
            event_graph,
            shacl_graph=shapes_graph,
            data_graph_format="turtle",
            shacl_graph_format="turtle",
            inference="rdfs",
        )

        assert conforms, "Valid status change event should pass"

    def test_status_change_event_with_invalid_status_fails(self) -> None:
        """StatusChangeEvent with invalid status value should fail."""
        wf_id = str(uuid4())
        event_graph = f"""
        @prefix evt: <http://kgcl.dev/ontology/event/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        <urn:event:1> a evt:StatusChangeEvent ;
            evt:eventId "00000000-0000-7000-8000-000000000001" ;
            evt:eventHash "{"a" * 64}" ;
            evt:previousHash "" ;
            evt:timestamp "2024-01-01T00:00:00Z"^^xsd:dateTime ;
            evt:tickNumber "0"^^xsd:nonNegativeInteger ;
            evt:workflowId "{wf_id}" ;
            evt:taskId "task-123" ;
            evt:fromStatus "idle" ;
            evt:toStatus "invalid-status" .
        """
        shapes_graph = TEMPORAL_SHAPES

        conforms, _, _ = validate(
            event_graph,
            shacl_graph=shapes_graph,
            data_graph_format="turtle",
            shacl_graph_format="turtle",
            inference="rdfs",
        )

        assert not conforms, "Invalid status value should fail validation"

    def test_token_move_event_with_valid_operation_passes(self) -> None:
        """TokenMoveEvent with 'add' or 'remove' operation should pass."""
        wf_id = str(uuid4())
        event_graph = f"""
        @prefix evt: <http://kgcl.dev/ontology/event/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        <urn:event:1> a evt:TokenMoveEvent ;
            evt:eventId "00000000-0000-7000-8000-000000000001" ;
            evt:eventHash "{"a" * 64}" ;
            evt:previousHash "" ;
            evt:timestamp "2024-01-01T00:00:00Z"^^xsd:dateTime ;
            evt:tickNumber "0"^^xsd:nonNegativeInteger ;
            evt:workflowId "{wf_id}" ;
            evt:placeId "place-1" ;
            evt:tokenId "token-xyz" ;
            evt:operation "add" .
        """
        shapes_graph = TEMPORAL_SHAPES

        conforms, _, _ = validate(
            event_graph,
            shacl_graph=shapes_graph,
            data_graph_format="turtle",
            shacl_graph_format="turtle",
            inference="rdfs",
        )

        assert conforms, "Valid token move event should pass"

    def test_hook_execution_event_with_valid_phase_passes(self) -> None:
        """HookExecutionEvent with valid phase and result should pass."""
        wf_id = str(uuid4())
        event_graph = f"""
        @prefix evt: <http://kgcl.dev/ontology/event/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        <urn:event:1> a evt:HookExecutionEvent ;
            evt:eventId "00000000-0000-7000-8000-000000000001" ;
            evt:eventHash "{"a" * 64}" ;
            evt:previousHash "" ;
            evt:timestamp "2024-01-01T00:00:00Z"^^xsd:dateTime ;
            evt:tickNumber "0"^^xsd:nonNegativeInteger ;
            evt:workflowId "{wf_id}" ;
            evt:hookId "hook-abc" ;
            evt:hookPhase "pre" ;
            evt:hookResult "success" .
        """
        shapes_graph = TEMPORAL_SHAPES

        conforms, _, _ = validate(
            event_graph,
            shacl_graph=shapes_graph,
            data_graph_format="turtle",
            shacl_graph_format="turtle",
            inference="rdfs",
        )

        assert conforms, "Valid hook execution event should pass"

    def test_validation_event_with_violation_count_passes(self) -> None:
        """ValidationEvent with violation count should pass."""
        wf_id = str(uuid4())
        event_graph = f"""
        @prefix evt: <http://kgcl.dev/ontology/event/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        <urn:event:1> a evt:ValidationEvent ;
            evt:eventId "00000000-0000-7000-8000-000000000001" ;
            evt:eventHash "{"a" * 64}" ;
            evt:previousHash "" ;
            evt:timestamp "2024-01-01T00:00:00Z"^^xsd:dateTime ;
            evt:tickNumber "0"^^xsd:nonNegativeInteger ;
            evt:workflowId "{wf_id}" ;
            evt:validationResult "valid" ;
            evt:violationCount "0"^^xsd:nonNegativeInteger .
        """
        shapes_graph = TEMPORAL_SHAPES

        conforms, _, _ = validate(
            event_graph,
            shacl_graph=shapes_graph,
            data_graph_format="turtle",
            shacl_graph_format="turtle",
            inference="rdfs",
        )

        assert conforms, "Valid validation event should pass"


@pytest.mark.filterwarnings("ignore:Dataset.*is deprecated:DeprecationWarning")
class TestVectorClockValidation:
    """Test vector clock format and monotonicity validation."""

    def test_valid_vector_clock_format_passes(self) -> None:
        """Vector clock in format 'node1:5,node2:3' should pass."""
        wf_id = str(uuid4())
        event_graph = f"""
        @prefix evt: <http://kgcl.dev/ontology/event/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        <urn:vc:1> a evt:VectorClock ;
            evt:clockValue "node1:5,node2:3,node3:7" .

        <urn:event:1> a evt:WorkflowEvent ;
            evt:eventId "00000000-0000-7000-8000-000000000001" ;
            evt:eventHash "{"a" * 64}" ;
            evt:previousHash "" ;
            evt:timestamp "2024-01-01T00:00:00Z"^^xsd:dateTime ;
            evt:tickNumber "0"^^xsd:nonNegativeInteger ;
            evt:workflowId "{wf_id}" ;
            evt:vectorClock <urn:vc:1> .
        """
        shapes_graph = TEMPORAL_SHAPES

        conforms, _, _ = validate(
            event_graph,
            shacl_graph=shapes_graph,
            data_graph_format="turtle",
            shacl_graph_format="turtle",
            inference="rdfs",
        )

        assert conforms, "Valid vector clock format should pass"

    def test_invalid_vector_clock_format_fails(self) -> None:
        """Vector clock with invalid format should fail."""
        wf_id = str(uuid4())
        event_graph = f"""
        @prefix evt: <http://kgcl.dev/ontology/event/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        <urn:vc:1> a evt:VectorClock ;
            evt:clockValue "not-a-valid-format" .

        <urn:event:1> a evt:WorkflowEvent ;
            evt:eventId "00000000-0000-7000-8000-000000000001" ;
            evt:eventHash "{"a" * 64}" ;
            evt:previousHash "" ;
            evt:timestamp "2024-01-01T00:00:00Z"^^xsd:dateTime ;
            evt:tickNumber "0"^^xsd:nonNegativeInteger ;
            evt:workflowId "{wf_id}" ;
            evt:vectorClock <urn:vc:1> .
        """
        shapes_graph = TEMPORAL_SHAPES

        conforms, _, _ = validate(
            event_graph,
            shacl_graph=shapes_graph,
            data_graph_format="turtle",
            shacl_graph_format="turtle",
            inference="rdfs",
        )

        assert not conforms, "Invalid vector clock format should fail validation"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
