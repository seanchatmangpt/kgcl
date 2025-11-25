"""Tests for UNRDF core engine."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
from rdflib import Literal, URIRef

from kgcl.unrdf_engine.engine import ProvenanceRecord, Transaction, UnrdfEngine


class TestProvenanceRecord:
    """Test ProvenanceRecord class."""

    def test_creation(self) -> None:
        """Test creating provenance record."""
        record = ProvenanceRecord(
            agent="test_agent", timestamp=datetime.now(UTC), reason="testing", source="test_source"
        )

        assert record.agent == "test_agent"
        assert record.reason == "testing"
        assert record.source == "test_source"

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        timestamp = datetime.now(UTC)
        record = ProvenanceRecord(agent="test", timestamp=timestamp, reason="test reason")

        result = record.to_dict()

        assert result["agent"] == "test"
        assert result["reason"] == "test reason"
        assert result["timestamp"] == timestamp.isoformat()


class TestTransaction:
    """Test Transaction class."""

    def test_creation(self) -> None:
        """Test creating transaction."""
        txn = Transaction(transaction_id="txn-1")

        assert txn.transaction_id == "txn-1"
        assert len(txn.added_triples) == 0
        assert len(txn.removed_triples) == 0
        assert not txn.committed
        assert not txn.rolled_back

    def test_can_modify(self) -> None:
        """Test can_modify logic."""
        txn = Transaction(transaction_id="txn-1")

        assert txn.can_modify()

        txn.committed = True
        assert not txn.can_modify()

        txn.committed = False
        txn.rolled_back = True
        assert not txn.can_modify()


class TestUnrdfEngine:
    """Test UnrdfEngine class."""

    def test_initialization(self) -> None:
        """Test engine initialization."""
        engine = UnrdfEngine()

        assert len(engine.graph) == 0
        assert engine.file_path is None

    def test_initialization_with_file(self) -> None:
        """Test engine initialization with file path."""
        with tempfile.NamedTemporaryFile(suffix=".ttl", delete=False) as f:
            file_path = Path(f.name)

        try:
            engine = UnrdfEngine(file_path=file_path)
            assert engine.file_path == file_path
        finally:
            file_path.unlink(missing_ok=True)

    def test_transaction_creation(self) -> None:
        """Test creating transactions."""
        engine = UnrdfEngine()

        txn = engine.transaction(agent="test_user", reason="testing")

        assert txn.transaction_id.startswith("txn-")
        assert txn.provenance is not None
        assert txn.provenance.agent == "test_user"
        assert txn.provenance.reason == "testing"

    def test_add_triple(self) -> None:
        """Test adding triples."""
        engine = UnrdfEngine()
        txn = engine.transaction("test_agent")

        subject = URIRef("http://example.org/subject")
        predicate = URIRef("http://example.org/predicate")
        obj = Literal("value")

        engine.add_triple(subject, predicate, obj, txn)

        assert len(txn.added_triples) == 1
        assert txn.added_triples[0] == (subject, predicate, obj)

    def test_commit_transaction(self) -> None:
        """Test committing transaction."""
        engine = UnrdfEngine()
        txn = engine.transaction("test_agent")

        subject = URIRef("http://example.org/subject")
        predicate = URIRef("http://example.org/predicate")
        obj = Literal("value")

        engine.add_triple(subject, predicate, obj, txn)
        engine.commit(txn)

        assert len(engine.graph) == 1
        assert txn.committed
        assert (subject, predicate, obj) in engine.graph

    def test_rollback_transaction(self) -> None:
        """Test rolling back transaction."""
        engine = UnrdfEngine()
        txn = engine.transaction("test_agent")

        subject = URIRef("http://example.org/subject")
        predicate = URIRef("http://example.org/predicate")
        obj = Literal("value")

        engine.add_triple(subject, predicate, obj, txn)
        engine.rollback(txn)

        assert len(engine.graph) == 0
        assert txn.rolled_back
        assert (subject, predicate, obj) not in engine.graph

    def test_remove_triple(self) -> None:
        """Test removing triples."""
        engine = UnrdfEngine()

        # Add a triple first
        txn1 = engine.transaction("test_agent")
        subject = URIRef("http://example.org/subject")
        predicate = URIRef("http://example.org/predicate")
        obj = Literal("value")
        engine.add_triple(subject, predicate, obj, txn1)
        engine.commit(txn1)

        assert len(engine.graph) == 1

        # Remove it
        txn2 = engine.transaction("test_agent")
        engine.remove_triple(subject, predicate, obj, txn2)
        engine.commit(txn2)

        assert len(engine.graph) == 0

    def test_provenance_tracking(self) -> None:
        """Test provenance tracking."""
        engine = UnrdfEngine()
        txn = engine.transaction("test_agent", "testing provenance")

        subject = URIRef("http://example.org/subject")
        predicate = URIRef("http://example.org/predicate")
        obj = Literal("value")

        engine.add_triple(subject, predicate, obj, txn)
        engine.commit(txn)

        prov = engine.get_provenance(subject, predicate, obj)

        assert prov is not None
        assert prov.agent == "test_agent"
        assert prov.reason == "testing provenance"

    def test_sparql_query(self) -> None:
        """Test SPARQL querying."""
        engine = UnrdfEngine()
        txn = engine.transaction("test_agent")

        # Add some data
        subject = URIRef("http://example.org/person1")
        predicate = URIRef("http://xmlns.com/foaf/0.1/name")
        obj = Literal("Alice")

        engine.add_triple(subject, predicate, obj, txn)
        engine.commit(txn)

        # Query it
        results = engine.query(
            """
            SELECT ?name WHERE {
                ?s <http://xmlns.com/foaf/0.1/name> ?name
            }
        """
        )

        results_list = list(results)
        assert len(results_list) == 1
        assert str(results_list[0][0]) == "Alice"

    def test_triples_iteration(self) -> None:
        """Test iterating over triples."""
        engine = UnrdfEngine()
        txn = engine.transaction("test_agent")

        subject = URIRef("http://example.org/subject")
        predicate = URIRef("http://example.org/predicate")
        obj = Literal("value")

        engine.add_triple(subject, predicate, obj, txn)
        engine.commit(txn)

        triples = list(engine.triples())
        assert len(triples) == 1
        assert triples[0] == (subject, predicate, obj)

    def test_triples_pattern_matching(self) -> None:
        """Test pattern matching in triples."""
        engine = UnrdfEngine()
        txn = engine.transaction("test_agent")

        subject1 = URIRef("http://example.org/subject1")
        subject2 = URIRef("http://example.org/subject2")
        predicate = URIRef("http://example.org/predicate")
        obj = Literal("value")

        engine.add_triple(subject1, predicate, obj, txn)
        engine.add_triple(subject2, predicate, obj, txn)
        engine.commit(txn)

        # Match by predicate
        triples = list(engine.triples(predicate=predicate))
        assert len(triples) == 2

        # Match by subject
        triples = list(engine.triples(subject=subject1))
        assert len(triples) == 1
        assert triples[0][0] == subject1

    def test_export_stats(self) -> None:
        """Test exporting statistics."""
        engine = UnrdfEngine()
        txn = engine.transaction("test_agent")

        subject = URIRef("http://example.org/subject")
        predicate = URIRef("http://example.org/predicate")
        obj = Literal("value")

        engine.add_triple(subject, predicate, obj, txn)
        engine.commit(txn)

        stats = engine.export_stats()

        assert stats["triple_count"] == 1
        assert stats["provenance_count"] == 1
        assert stats["transaction_count"] == 1
        assert not stats["file_backed"]

    def test_save_and_load(self) -> None:
        """Test saving and loading from file."""
        with tempfile.NamedTemporaryFile(suffix=".ttl", delete=False) as f:
            file_path = Path(f.name)

        try:
            # Create and save
            engine1 = UnrdfEngine(file_path=file_path)
            txn = engine1.transaction("test_agent")

            subject = URIRef("http://example.org/subject")
            predicate = URIRef("http://example.org/predicate")
            obj = Literal("value")

            engine1.add_triple(subject, predicate, obj, txn)
            engine1.commit(txn)
            engine1.save_to_file()

            # Load in new engine
            engine2 = UnrdfEngine(file_path=file_path)

            assert len(engine2.graph) == 1
            assert (subject, predicate, obj) in engine2.graph

        finally:
            file_path.unlink(missing_ok=True)

    def test_context_manager(self) -> None:
        """Test using engine as context manager."""
        with tempfile.NamedTemporaryFile(suffix=".ttl", delete=False) as f:
            file_path = Path(f.name)

        try:
            with UnrdfEngine(file_path=file_path) as engine:
                txn = engine.transaction("test_agent")
                subject = URIRef("http://example.org/subject")
                predicate = URIRef("http://example.org/predicate")
                obj = Literal("value")
                engine.add_triple(subject, predicate, obj, txn)
                engine.commit(txn)

            # File should be saved automatically
            engine2 = UnrdfEngine(file_path=file_path)
            assert len(engine2.graph) == 1

        finally:
            file_path.unlink(missing_ok=True)

    def test_transaction_cannot_modify_after_commit(self) -> None:
        """Test that transactions cannot be modified after commit."""
        engine = UnrdfEngine()
        txn = engine.transaction("test_agent")

        subject = URIRef("http://example.org/subject")
        predicate = URIRef("http://example.org/predicate")
        obj = Literal("value")

        engine.add_triple(subject, predicate, obj, txn)
        engine.commit(txn)

        with pytest.raises(ValueError, match="cannot be modified"):
            engine.add_triple(subject, predicate, obj, txn)

    def test_transaction_cannot_modify_after_rollback(self) -> None:
        """Test that transactions cannot be modified after rollback."""
        engine = UnrdfEngine()
        txn = engine.transaction("test_agent")

        subject = URIRef("http://example.org/subject")
        predicate = URIRef("http://example.org/predicate")
        obj = Literal("value")

        engine.rollback(txn)

        with pytest.raises(ValueError, match="cannot be modified"):
            engine.add_triple(subject, predicate, obj, txn)

    def test_get_all_provenance(self) -> None:
        """Test getting all provenance records."""
        engine = UnrdfEngine()
        txn = engine.transaction("test_agent")

        subject1 = URIRef("http://example.org/subject1")
        subject2 = URIRef("http://example.org/subject2")
        predicate = URIRef("http://example.org/predicate")
        obj = Literal("value")

        engine.add_triple(subject1, predicate, obj, txn)
        engine.add_triple(subject2, predicate, obj, txn)
        engine.commit(txn)

        all_prov = engine.get_all_provenance()

        assert len(all_prov) == 2
        assert all(isinstance(p, ProvenanceRecord) for p in all_prov.values())
