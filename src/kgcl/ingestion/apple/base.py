"""Base class for Apple data ingest engines."""

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from rdflib import RDF, Graph, Literal, Namespace, URIRef


@dataclass
class IngestResult:
    """Result of a single ingest operation."""

    success: bool
    graph: Graph
    receipt_hash: str
    items_processed: int
    errors: list[str]
    metadata: dict


class BaseIngestEngine(ABC):
    """Base class for all Apple ingest engines."""

    def __init__(self):
        """Initialize ingest engine with RDF namespaces."""
        self.graph = Graph()
        self.schema_ns = Namespace("http://schema.org/")
        self.apple_ns = Namespace("urn:kgc:apple:")
        self.bind_namespaces()

    def bind_namespaces(self):
        """Bind RDF namespaces."""
        self.graph.bind("schema", self.schema_ns)
        self.graph.bind("apple", self.apple_ns)
        self.graph.bind("rdf", RDF)

    @abstractmethod
    def ingest(self, source_object: Any) -> IngestResult:
        """Ingest a single object to RDF.

        Args:
            source_object: Object from Apple framework (EKEvent, EKReminder, etc.)

        Returns
        -------
            IngestResult with RDF graph and metadata
        """

    def ingest_batch(self, objects: list[Any]) -> IngestResult:
        """Ingest multiple objects to RDF.

        Args:
            objects: List of objects from Apple framework

        Returns
        -------
            IngestResult with consolidated RDF graph
        """
        self.graph = Graph()
        self.bind_namespaces()
        all_errors = []
        processed = 0

        for obj in objects:
            try:
                result = self.ingest(obj)
                if result.success:
                    # Merge graphs
                    for s, p, o in result.graph:
                        self.graph.add((s, p, o))
                    processed += result.items_processed
                else:
                    all_errors.extend(result.errors)
            except Exception as e:
                all_errors.append(str(e))

        receipt_hash = self._generate_receipt()

        return IngestResult(
            success=len(all_errors) == 0,
            graph=self.graph,
            receipt_hash=receipt_hash,
            items_processed=processed,
            errors=all_errors,
            metadata={"batch_size": len(objects), "processed": processed, "errors": len(all_errors)},
        )

    def _generate_receipt(self) -> str:
        """Generate SHA256 receipt hash for idempotency.

        Returns
        -------
            SHA256 hex digest of serialized RDF
        """
        serialized = self.graph.serialize(format="ttl")
        return hashlib.sha256(serialized.encode()).hexdigest()

    def _create_uri(self, identifier: str, prefix: str = "data") -> URIRef:
        """Create a URI for an entity.

        Args:
            identifier: Unique identifier
            prefix: URI prefix (e.g., 'event', 'task', 'message')

        Returns
        -------
            URIRef for the entity
        """
        return URIRef(f"urn:kgc:{prefix}:{identifier}")

    def _add_literal(self, subject: URIRef, predicate, value: Any, datatype: str | None = None):
        """Add a literal triple to the graph.

        Args:
            subject: Subject URI
            predicate: Predicate URI
            value: Literal value
            datatype: Optional XSD datatype
        """
        if value is not None:
            if isinstance(value, datetime):
                # Convert to ISO 8601 string
                value = value.isoformat()
                datatype = str(Namespace("http://www.w3.org/2001/XMLSchema#")["dateTime"])
            literal = Literal(value, datatype=datatype) if datatype else Literal(value)
            self.graph.add((subject, predicate, literal))

    def _add_uri(self, subject: URIRef, predicate, uri: URIRef):
        """Add a URI triple to the graph.

        Args:
            subject: Subject URI
            predicate: Predicate URI
            uri: Object URI
        """
        if uri is not None:
            self.graph.add((subject, predicate, uri))

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO 8601 format."""
        return datetime.now(tz=UTC).isoformat()
