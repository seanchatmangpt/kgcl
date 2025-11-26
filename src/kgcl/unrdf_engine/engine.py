"""Core UNRDF Engine with RDF triple store, SPARQL, transactions, and provenance."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from opentelemetry import trace
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.plugins.sparql import prepareQuery
from rdflib.query import Result

tracer = trace.get_tracer(__name__)

# Lazy import to avoid circular dependencies
HookRegistry = None
HookExecutor = None
HookContext = None
HookPhase = None
Receipt = None

if TYPE_CHECKING:  # pragma: no cover - import for type checking only
    from kgcl.unrdf_engine.hook_registry import PersistentHookRegistry
    from kgcl.unrdf_engine.hooks import HookExecutor as HookExecutorType

# UNRDF namespaces
UNRDF = Namespace("http://unrdf.org/ontology/")
PROV = Namespace("http://www.w3.org/ns/prov#")


@dataclass
class ProvenanceRecord:
    """Provenance metadata for RDF triples."""

    agent: str  # Who added the triple
    timestamp: datetime  # When it was added
    reason: str | None = None  # Why it was added
    source: str | None = None  # Source system/file
    activity: str | None = None  # Activity that generated it

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "agent": self.agent,
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason,
            "source": self.source,
            "activity": self.activity,
        }


@dataclass
class Transaction:
    """Transaction context for atomic RDF operations."""

    transaction_id: str
    added_triples: list[tuple[URIRef, URIRef, URIRef | Literal]] = field(
        default_factory=list
    )
    removed_triples: list[tuple[URIRef, URIRef, URIRef | Literal]] = field(
        default_factory=list
    )
    provenance: ProvenanceRecord | None = None
    committed: bool = False
    rolled_back: bool = False
    hook_receipts: list[Any] = field(default_factory=list)  # List of Receipt objects

    def can_modify(self) -> bool:
        """Check if transaction can still be modified."""
        return not self.committed and not self.rolled_back


class UnrdfEngine:
    """RDF triple store with SPARQL, transactions, and provenance tracking.

    Features:
    - In-memory RDF graph with optional file-backed persistence
    - SPARQL 1.1 query support
    - Transaction support with rollback capability
    - Full provenance tracking (who/when/why for each triple)
    - Batch operations for performance
    - OpenTelemetry instrumentation

    Examples
    --------
    >>> engine = UnrdfEngine()
    >>> with engine.transaction("user1", "Initial data load") as txn:
    ...     engine.add_triple(
    ...         URIRef("http://example.org/person1"),
    ...         URIRef("http://xmlns.com/foaf/0.1/name"),
    ...         Literal("Alice"),
    ...         txn,
    ...     )
    >>> results = engine.query("SELECT ?name WHERE { ?s foaf:name ?name }")

    """

    def __init__(
        self, file_path: Path | None = None, hook_registry: Any = None
    ) -> None:
        """Initialize the UNRDF engine.

        Parameters
        ----------
        file_path : Path, optional
            Path to file for persistence (Turtle format)
        hook_registry : HookRegistry, optional
            Hook registry for lifecycle hooks

        """
        self.graph = Graph()
        self.file_path = file_path
        self._provenance: dict[tuple, ProvenanceRecord] = {}
        self._transactions: dict[str, Transaction] = {}
        self._transaction_counter = 0
        self._hook_registry = hook_registry
        self._hook_executor = None

        # Initialize hook executor if registry provided
        if hook_registry:
            global HookExecutor
            if HookExecutor is None:
                from kgcl.unrdf_engine.hooks import HookExecutor as HE

                HookExecutor = HE
            self._hook_executor = HookExecutor(hook_registry)

        # Bind common namespaces
        self.graph.bind("unrdf", UNRDF)
        self.graph.bind("prov", PROV)
        self.graph.bind("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#")
        self.graph.bind("rdfs", "http://www.w3.org/2000/01/rdf-schema#")
        self.graph.bind("owl", "http://www.w3.org/2002/07/owl#")
        self.graph.bind("xsd", "http://www.w3.org/2001/XMLSchema#")

        # Load from file if exists
        if file_path and file_path.exists():
            self._load_from_file()

    @tracer.start_as_current_span("unrdf.load_from_file")
    def _load_from_file(self) -> None:
        """Load RDF graph from file."""
        if not self.file_path:
            return

        span = trace.get_current_span()
        span.set_attribute("file.path", str(self.file_path))

        self.graph.parse(self.file_path, format="turtle")
        span.set_attribute("triples.count", len(self.graph))

    @tracer.start_as_current_span("unrdf.save_to_file")
    def save_to_file(self) -> None:
        """Persist RDF graph to file in Turtle format."""
        if not self.file_path:
            msg = "No file path configured for persistence"
            raise ValueError(msg)

        span = trace.get_current_span()
        span.set_attribute("file.path", str(self.file_path))
        span.set_attribute("triples.count", len(self.graph))

        # Ensure parent directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize to Turtle format
        self.graph.serialize(destination=self.file_path, format="turtle")

    @tracer.start_as_current_span("unrdf.transaction")
    def transaction(self, agent: str, reason: str | None = None) -> Transaction:
        """Create a new transaction context.

        Parameters
        ----------
        agent : str
            Agent performing the transaction
        reason : str, optional
            Reason for the transaction

        Returns
        -------
        Transaction
            Transaction context manager

        """
        self._transaction_counter += 1
        transaction_id = f"txn-{self._transaction_counter}"

        span = trace.get_current_span()
        span.set_attribute("transaction.id", transaction_id)
        span.set_attribute("transaction.agent", agent)
        if reason:
            span.set_attribute("transaction.reason", reason)

        provenance = ProvenanceRecord(
            agent=agent, timestamp=datetime.now(UTC), reason=reason
        )

        txn = Transaction(transaction_id=transaction_id, provenance=provenance)
        self._transactions[transaction_id] = txn
        return txn

    @tracer.start_as_current_span("unrdf.add_triple")
    def add_triple(
        self,
        subject: URIRef,
        predicate: URIRef,
        obj: URIRef | Literal,
        transaction: Transaction,
    ) -> None:
        """Add a triple to the graph within a transaction.

        Parameters
        ----------
        subject : URIRef
            Subject of the triple
        predicate : URIRef
            Predicate of the triple
        obj : URIRef | Literal
            Object of the triple
        transaction : Transaction
            Transaction context

        """
        if not transaction.can_modify():
            msg = f"Transaction {transaction.transaction_id} cannot be modified"
            raise ValueError(msg)

        span = trace.get_current_span()
        span.set_attribute("triple.subject", str(subject))
        span.set_attribute("triple.predicate", str(predicate))
        span.set_attribute("triple.object", str(obj))

        triple = (subject, predicate, obj)
        transaction.added_triples.append(triple)

    @tracer.start_as_current_span("unrdf.remove_triple")
    def remove_triple(
        self,
        subject: URIRef,
        predicate: URIRef,
        obj: URIRef | Literal,
        transaction: Transaction,
    ) -> None:
        """Remove a triple from the graph within a transaction.

        Parameters
        ----------
        subject : URIRef
            Subject of the triple
        predicate : URIRef
            Predicate of the triple
        obj : URIRef | Literal
            Object of the triple
        transaction : Transaction
            Transaction context

        """
        if not transaction.can_modify():
            msg = f"Transaction {transaction.transaction_id} cannot be modified"
            raise ValueError(msg)

        triple = (subject, predicate, obj)
        transaction.removed_triples.append(triple)

    @tracer.start_as_current_span("unrdf.commit")
    def commit(self, transaction: Transaction) -> None:
        """Commit a transaction, applying all changes to the graph.

        Parameters
        ----------
        transaction : Transaction
            Transaction to commit

        """
        if not transaction.can_modify():
            msg = f"Transaction {transaction.transaction_id} cannot be modified"
            raise ValueError(msg)

        span = trace.get_current_span()
        span.set_attribute("transaction.id", transaction.transaction_id)
        span.set_attribute("transaction.added", len(transaction.added_triples))
        span.set_attribute("transaction.removed", len(transaction.removed_triples))

        # Execute PRE_TRANSACTION hooks
        if self._hook_executor:
            global HookContext, HookPhase
            if HookContext is None:
                from kgcl.unrdf_engine.hooks import HookContext as HC
                from kgcl.unrdf_engine.hooks import HookPhase as HP

                HookContext = HC
                HookPhase = HP

            delta = Graph()
            for s, p, o in transaction.added_triples:
                delta.add((s, p, o))

            context = HookContext(
                phase=HookPhase.PRE_TRANSACTION,
                graph=self.graph,
                delta=delta,
                transaction_id=transaction.transaction_id,
            )
            self._hook_executor.execute_phase(HookPhase.PRE_TRANSACTION, context)

            # Check if hooks signaled rollback
            if context.metadata.get("should_rollback"):
                self.rollback(transaction)
                msg = context.metadata.get(
                    "rollback_reason", "Hook rejected transaction"
                )
                raise ValueError(msg)

        # Apply removals
        for triple in transaction.removed_triples:
            self.graph.remove(triple)
            if triple in self._provenance:
                del self._provenance[triple]

        # Apply additions
        for triple in transaction.added_triples:
            self.graph.add(triple)
            if transaction.provenance:
                self._provenance[triple] = transaction.provenance

        transaction.committed = True

        # Execute POST_TRANSACTION hooks
        if self._hook_executor:
            context.phase = HookPhase.POST_TRANSACTION
            pre_receipt_count = len(context.receipts)
            self._hook_executor.execute_phase(HookPhase.POST_TRANSACTION, context)
            transaction.hook_receipts.extend(context.receipts[pre_receipt_count:])

            # Execute POST_COMMIT hooks for long-running observability/pipeline triggers
            context.phase = HookPhase.POST_COMMIT
            context.metadata.setdefault("transaction", transaction)
            post_commit_start = len(context.receipts)
            self._hook_executor.execute_phase(HookPhase.POST_COMMIT, context)
            transaction.hook_receipts.extend(context.receipts[post_commit_start:])

    @tracer.start_as_current_span("unrdf.rollback")
    def rollback(self, transaction: Transaction) -> None:
        """Rollback a transaction, discarding all changes.

        Parameters
        ----------
        transaction : Transaction
            Transaction to rollback

        """
        if not transaction.can_modify():
            msg = f"Transaction {transaction.transaction_id} already finalized"
            raise ValueError(msg)

        span = trace.get_current_span()
        span.set_attribute("transaction.id", transaction.transaction_id)
        span.set_attribute("transaction.discarded", len(transaction.added_triples))

        transaction.rolled_back = True

    @tracer.start_as_current_span("unrdf.query")
    def get_hook_registry(self) -> PersistentHookRegistry | None:
        """Return the configured hook registry if available."""
        return self._hook_registry

    def get_hook_executor(self) -> HookExecutorType | None:
        """Return the active hook executor if hooks are enabled."""
        return self._hook_executor

    @property
    def hook_registry(self) -> PersistentHookRegistry | None:
        """Expose the configured hook registry for callers that need direct access."""
        return self._hook_registry

    @property
    def hook_executor(self) -> HookExecutorType | None:
        """Expose the active hook executor."""
        return self._hook_executor

    def query(self, sparql: str, **kwargs: Any) -> Result:
        """Execute a SPARQL query against the graph.

        Parameters
        ----------
        sparql : str
            SPARQL query string
        **kwargs : Any
            Additional arguments for query execution

        Returns
        -------
        Result
            SPARQL query results

        """
        span = trace.get_current_span()
        span.set_attribute("sparql.query", sparql)

        # Execute PRE_QUERY hooks if available
        if self._hook_executor:
            global HookContext, HookPhase
            if HookContext is None:
                from kgcl.unrdf_engine.hooks import HookContext as HC
                from kgcl.unrdf_engine.hooks import HookPhase as HP

                HookContext = HC
                HookPhase = HP

            context = HookContext(
                phase=HookPhase.PRE_QUERY,
                graph=self.graph,
                delta=Graph(),
                transaction_id="query",
                metadata={"query": sparql, "kwargs": kwargs},
            )
            self._hook_executor.execute_phase(HookPhase.PRE_QUERY, context)

            # Check if hooks modified the query
            sparql = context.metadata.get("query", sparql)

        prepared = prepareQuery(sparql)
        results = self.graph.query(prepared, **kwargs)

        # Execute POST_QUERY hooks if available
        if self._hook_executor:
            context.phase = HookPhase.POST_QUERY
            context.metadata["results"] = results
            self._hook_executor.execute_phase(HookPhase.POST_QUERY, context)

        span.set_attribute("results.count", len(list(results)))
        return results

    @tracer.start_as_current_span("unrdf.get_provenance")
    def get_provenance(
        self, subject: URIRef, predicate: URIRef, obj: URIRef | Literal
    ) -> ProvenanceRecord | None:
        """Get provenance information for a specific triple.

        Parameters
        ----------
        subject : URIRef
            Subject of the triple
        predicate : URIRef
            Predicate of the triple
        obj : URIRef | Literal
            Object of the triple

        Returns
        -------
        ProvenanceRecord | None
            Provenance record if available

        """
        return self._provenance.get((subject, predicate, obj))

    @tracer.start_as_current_span("unrdf.get_all_provenance")
    def get_all_provenance(self) -> dict[tuple, ProvenanceRecord]:
        """Get all provenance records.

        Returns
        -------
        dict[tuple, ProvenanceRecord]
            All provenance records indexed by triple

        """
        return self._provenance.copy()

    def triples(
        self,
        subject: URIRef | None = None,
        predicate: URIRef | None = None,
        obj: URIRef | Literal | None = None,
    ) -> Iterator[tuple[URIRef, URIRef, URIRef | Literal]]:
        """Iterate over triples matching a pattern.

        Parameters
        ----------
        subject : URIRef, optional
            Subject pattern (None matches any)
        predicate : URIRef, optional
            Predicate pattern (None matches any)
        obj : URIRef | Literal, optional
            Object pattern (None matches any)

        Yields
        ------
        tuple[URIRef, URIRef, URIRef | Literal]
            Matching triples

        """
        yield from self.graph.triples((subject, predicate, obj))

    @tracer.start_as_current_span("unrdf.export_stats")
    def export_stats(self) -> dict[str, Any]:
        """Export statistics about the graph.

        Returns
        -------
        dict[str, Any]
            Statistics including triple count, provenance count, etc.

        """
        return {
            "triple_count": len(self.graph),
            "provenance_count": len(self._provenance),
            "namespace_count": len(list(self.graph.namespaces())),
            "transaction_count": len(self._transactions),
            "file_backed": self.file_path is not None,
        }

    def __enter__(self) -> UnrdfEngine:
        """Context manager entry."""
        return self

    def register_hook(self, hook: Any, description: str = "", version: int = 1) -> str:
        """Register a hook with the engine.

        Parameters
        ----------
        hook : KnowledgeHook
            Hook to register
        description : str, default=""
            Hook description
        version : int, default=1
            Hook version

        Returns
        -------
        str
            Hook identifier

        """
        if not self._hook_registry:
            msg = "No hook registry configured. Initialize engine with hook_registry parameter."
            raise ValueError(msg)

        return self._hook_registry.register(hook, description, version)

    def trigger_hooks(self, delta: Graph, phase: str) -> list[Any]:
        """Trigger hooks for a specific phase with graph changes.

        Parameters
        ----------
        delta : Graph
            Graph changes to process
        phase : str
            Hook phase name (e.g., "pre_ingestion", "post_commit")

        Returns
        -------
        list[Receipt]
            Hook execution receipts

        """
        if not self._hook_executor:
            return []

        global HookContext, HookPhase
        if HookContext is None:
            from kgcl.unrdf_engine.hooks import HookContext as HC
            from kgcl.unrdf_engine.hooks import HookPhase as HP

            HookContext = HC
            HookPhase = HP

        # Convert phase string to enum
        try:
            phase_enum = HookPhase(phase)
        except ValueError as e:
            msg = f"Invalid hook phase: {phase}"
            raise ValueError(msg) from e

        context = HookContext(
            phase=phase_enum, graph=self.graph, delta=delta, transaction_id="manual"
        )

        self._hook_executor.execute_phase(phase_enum, context)
        return context.receipts

    def query_with_hooks(self, sparql_query: str) -> Result:
        """Execute SPARQL query with hook support.

        This is an alias for the standard query() method, which already
        supports hooks if configured.

        Parameters
        ----------
        sparql_query : str
            SPARQL query string

        Returns
        -------
        Result
            Query results

        """
        return self.query(sparql_query)

    def get_hook_statistics(self) -> dict[str, Any]:
        """Get statistics about registered hooks.

        Returns
        -------
        dict[str, Any]
            Hook statistics

        """
        if not self._hook_registry:
            return {"hooks_enabled": False}

        stats = (
            self._hook_registry.get_statistics()
            if hasattr(self._hook_registry, "get_statistics")
            else {}
        )
        stats["hooks_enabled"] = True
        stats["has_executor"] = self._hook_executor is not None

        return stats

    def __exit__(self, exc_type: type, exc_val: Exception, exc_tb: Any) -> None:
        """Context manager exit with auto-save if file-backed."""
        if exc_type is None and self.file_path:
            self.save_to_file()
