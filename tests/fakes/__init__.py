"""Verified Fakes for Chicago-Style TDD.

This module provides in-memory test fakes that implement the same interfaces
as real KGCL components. These fakes are used instead of mocks in Chicago School
TDD to test real object interactions and observable state.

Key Principles
--------------
1. **Real Interfaces**: Each fake implements the same Protocol/ABC as production code
2. **In-Memory Storage**: All data stored in simple dict/list structures
3. **Observable State**: Fakes expose helper methods to inspect internal state
4. **Simple & Predictable**: No complex logic, just storage/retrieval
5. **Full Type Safety**: Complete type hints matching production types

Examples
--------
Chicago-Style test using fakes::

    from tests.fakes import FakeReceiptStore, FakeRdfStore, FakeHookRegistry


    def test_hook_execution_stores_receipt():
        '''Hook execution creates receipt with success status.'''
        # Arrange - real collaborators with fake storage
        registry = FakeHookRegistry()
        receipt_store = FakeReceiptStore()
        rdf_store = FakeRdfStore()

        hook = ValidationHook(name="validator")
        registry.register(hook)

        executor = HookExecutor(registry=registry, receipt_store=receipt_store)

        # Act - real execution
        context = HookContext(
            phase=HookPhase.PRE_TRANSACTION, graph=rdf_store.graph, delta=Graph(), transaction_id="txn-001"
        )
        executor.execute_phase(HookPhase.PRE_TRANSACTION, context)

        # Assert - verify observable state
        receipts = receipt_store.all()
        assert len(receipts) == 1
        assert receipts[0].hook_id == "validator"
        assert receipts[0].success is True
        assert receipts[0].phase == HookPhase.PRE_TRANSACTION

"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.query import Result

from kgcl.unrdf_engine.engine import ProvenanceRecord, Transaction
from kgcl.unrdf_engine.hooks import HookContext, HookPhase, KnowledgeHook, Receipt

# Constants
UNRDF = Namespace("http://unrdf.org/ontology/")


@dataclass
class FakeReceiptStore:
    """In-memory receipt storage for testing.

    Stores hook execution receipts in memory and provides inspection methods.

    Examples
    --------
    >>> store = FakeReceiptStore()
    >>> receipt = Receipt(
    ...     hook_id="test_hook",
    ...     phase=HookPhase.PRE_TRANSACTION,
    ...     timestamp=datetime.now(UTC),
    ...     success=True,
    ...     duration_ms=5.0,
    ... )
    >>> store.save(receipt)
    >>> assert store.get("test_hook") == receipt
    >>> assert len(store.all()) == 1

    """

    _receipts: dict[str, Receipt] = field(default_factory=dict)
    _receipts_by_phase: dict[HookPhase, list[Receipt]] = field(default_factory=lambda: defaultdict(list))

    def save(self, receipt: Receipt) -> None:
        """Store a receipt.

        Parameters
        ----------
        receipt : Receipt
            Receipt to store

        """
        self._receipts[receipt.hook_id] = receipt
        self._receipts_by_phase[receipt.phase].append(receipt)

    def get(self, hook_id: str) -> Receipt | None:
        """Get receipt by hook ID.

        Parameters
        ----------
        hook_id : str
            Hook identifier

        Returns
        -------
        Receipt | None
            Receipt if found, None otherwise

        """
        return self._receipts.get(hook_id)

    def all(self) -> list[Receipt]:
        """Get all receipts.

        Returns
        -------
        list[Receipt]
            All stored receipts

        """
        return list(self._receipts.values())

    def for_phase(self, phase: HookPhase) -> list[Receipt]:
        """Get receipts for specific phase.

        Parameters
        ----------
        phase : HookPhase
            Lifecycle phase

        Returns
        -------
        list[Receipt]
            Receipts for the phase

        """
        return list(self._receipts_by_phase[phase])

    def count(self) -> int:
        """Count total receipts.

        Returns
        -------
        int
            Total receipt count

        """
        return len(self._receipts)

    def successful_count(self) -> int:
        """Count successful receipts.

        Returns
        -------
        int
            Number of successful receipts

        """
        return sum(1 for r in self._receipts.values() if r.success)

    def failed_count(self) -> int:
        """Count failed receipts.

        Returns
        -------
        int
            Number of failed receipts

        """
        return sum(1 for r in self._receipts.values() if not r.success)

    def clear(self) -> None:
        """Clear all receipts."""
        self._receipts.clear()
        self._receipts_by_phase.clear()


@dataclass
class FakeRdfStore:
    """In-memory RDF triple store for testing.

    Uses rdflib.Graph internally but provides simplified access for tests.

    Examples
    --------
    >>> store = FakeRdfStore()
    >>> subject = URIRef("http://example.org/person1")
    >>> predicate = URIRef("http://xmlns.com/foaf/0.1/name")
    >>> obj = Literal("Alice")
    >>> store.add_triple(subject, predicate, obj)
    >>> assert store.count_triples() == 1
    >>> assert list(store.all_triples())[0] == (subject, predicate, obj)

    """

    graph: Graph = field(default_factory=Graph)
    _provenance: dict[tuple[URIRef, URIRef, URIRef | Literal], ProvenanceRecord] = field(default_factory=dict)

    def add_triple(
        self, subject: URIRef, predicate: URIRef, obj: URIRef | Literal, provenance: ProvenanceRecord | None = None
    ) -> None:
        """Add a triple to the graph.

        Parameters
        ----------
        subject : URIRef
            Subject URI
        predicate : URIRef
            Predicate URI
        obj : URIRef | Literal
            Object URI or literal
        provenance : ProvenanceRecord, optional
            Provenance metadata

        """
        triple = (subject, predicate, obj)
        self.graph.add(triple)
        if provenance:
            self._provenance[triple] = provenance

    def remove_triple(self, subject: URIRef, predicate: URIRef, obj: URIRef | Literal) -> None:
        """Remove a triple from the graph.

        Parameters
        ----------
        subject : URIRef
            Subject URI
        predicate : URIRef
            Predicate URI
        obj : URIRef | Literal
            Object URI or literal

        """
        triple = (subject, predicate, obj)
        self.graph.remove(triple)
        self._provenance.pop(triple, None)

    def count_triples(self) -> int:
        """Count total triples.

        Returns
        -------
        int
            Triple count

        """
        return len(self.graph)

    def all_triples(self) -> Iterator[tuple[URIRef, URIRef, URIRef | Literal]]:
        """Get all triples.

        Yields
        ------
        tuple[URIRef, URIRef, URIRef | Literal]
            Subject, predicate, object tuples

        """
        # Note: Cannot use yield from due to rdflib type incompatibility
        # rdflib.Graph yields Node but we need URIRef/Literal for type safety
        for s, p, o in self.graph:
            yield (s, p, o)  # type: ignore[misc]

    def query(self, sparql: str) -> Result:
        """Execute SPARQL query.

        Parameters
        ----------
        sparql : str
            SPARQL query string

        Returns
        -------
        Result
            Query results

        """
        return self.graph.query(sparql)

    def get_provenance(self, subject: URIRef, predicate: URIRef, obj: URIRef | Literal) -> ProvenanceRecord | None:
        """Get provenance for a triple.

        Parameters
        ----------
        subject : URIRef
            Subject URI
        predicate : URIRef
            Predicate URI
        obj : URIRef | Literal
            Object URI or literal

        Returns
        -------
        ProvenanceRecord | None
            Provenance if available

        """
        return self._provenance.get((subject, predicate, obj))

    def clear(self) -> None:
        """Clear all triples and provenance."""
        # Create new graph to fully reset state
        self.graph = Graph()
        self._provenance.clear()


@dataclass
class FakeHookRegistry:
    """In-memory hook registry for testing.

    Stores hooks and provides lookup by ID or phase.

    Examples
    --------
    >>> registry = FakeHookRegistry()
    >>> hook = ValidationHook(name="validator", phases=[HookPhase.PRE_TRANSACTION])
    >>> registry.register(hook)
    >>> assert registry.get("validator") == hook
    >>> assert hook in registry.get_for_phase(HookPhase.PRE_TRANSACTION)

    """

    _hooks: dict[str, KnowledgeHook] = field(default_factory=dict)
    _hooks_by_phase: dict[HookPhase, list[KnowledgeHook]] = field(
        default_factory=lambda: {phase: [] for phase in HookPhase}
    )

    def register(self, hook: KnowledgeHook) -> None:
        """Register a hook.

        Parameters
        ----------
        hook : KnowledgeHook
            Hook to register

        Raises
        ------
        ValueError
            If hook already registered

        """
        if hook.name in self._hooks:
            msg = f"Hook {hook.name} already registered"
            raise ValueError(msg)

        self._hooks[hook.name] = hook

        # Index by phase
        for phase in hook.phases:
            self._hooks_by_phase[phase].append(hook)
            # Sort by priority (descending)
            self._hooks_by_phase[phase].sort(key=lambda h: h.priority, reverse=True)

    def unregister(self, name: str) -> None:
        """Unregister a hook.

        Parameters
        ----------
        name : str
            Hook name

        Raises
        ------
        ValueError
            If hook not found

        """
        if name not in self._hooks:
            msg = f"Hook {name} not found"
            raise ValueError(msg)

        hook = self._hooks[name]

        # Remove from phase indices
        for phase in hook.phases:
            if hook in self._hooks_by_phase[phase]:
                self._hooks_by_phase[phase].remove(hook)

        del self._hooks[name]

    def get(self, name: str) -> KnowledgeHook | None:
        """Get hook by name.

        Parameters
        ----------
        name : str
            Hook name

        Returns
        -------
        KnowledgeHook | None
            Hook if found, None otherwise

        """
        return self._hooks.get(name)

    def get_for_phase(self, phase: HookPhase) -> list[KnowledgeHook]:
        """Get hooks for a specific phase.

        Parameters
        ----------
        phase : HookPhase
            Lifecycle phase

        Returns
        -------
        list[KnowledgeHook]
            Hooks for the phase (sorted by priority)

        """
        return self._hooks_by_phase[phase].copy()

    def list_all(self) -> list[KnowledgeHook]:
        """List all registered hooks.

        Returns
        -------
        list[KnowledgeHook]
            All hooks

        """
        return list(self._hooks.values())

    def count(self) -> int:
        """Count total hooks.

        Returns
        -------
        int
            Hook count

        """
        return len(self._hooks)

    def clear(self) -> None:
        """Clear all hooks."""
        self._hooks.clear()
        for phase in self._hooks_by_phase:
            self._hooks_by_phase[phase].clear()


@dataclass
class FakeHookExecutor:
    """In-memory hook executor for testing.

    Executes hooks and records execution history.

    Examples
    --------
    >>> registry = FakeHookRegistry()
    >>> executor = FakeHookExecutor(registry=registry)
    >>> hook = ValidationHook(name="validator", phases=[HookPhase.PRE_TRANSACTION])
    >>> registry.register(hook)
    >>> context = HookContext(phase=HookPhase.PRE_TRANSACTION, graph=Graph(), delta=Graph(), transaction_id="txn-001")
    >>> results = executor.execute_phase(HookPhase.PRE_TRANSACTION, context)
    >>> assert len(results) == 1
    >>> assert results[0]["success"] is True

    """

    registry: FakeHookRegistry
    _execution_history: list[dict[str, Any]] = field(default_factory=list)

    def execute_phase(self, phase: HookPhase, context: HookContext, fail_fast: bool = False) -> list[dict[str, Any]]:
        """Execute all hooks for a phase.

        Parameters
        ----------
        phase : HookPhase
            Lifecycle phase
        context : HookContext
            Execution context
        fail_fast : bool, default=False
            Stop on first failure

        Returns
        -------
        list[dict[str, Any]]
            Execution results

        """
        hooks = self.registry.get_for_phase(phase)
        results = []

        for hook in hooks:
            result = self._execute_hook(hook, context)
            results.append(result)

            if fail_fast and not result["success"]:
                break

        self._execution_history.extend(results)
        return results

    def _execute_hook(self, hook: KnowledgeHook, context: HookContext) -> dict[str, Any]:
        """Execute a single hook.

        Parameters
        ----------
        hook : KnowledgeHook
            Hook to execute
        context : HookContext
            Execution context

        Returns
        -------
        dict[str, Any]
            Execution result

        """
        start_time = time.perf_counter()
        timestamp = datetime.now(UTC)

        result = {
            "hook": hook.name,
            "phase": context.phase.value,
            "transaction_id": context.transaction_id,
            "success": False,
            "executed": False,
            "error": None,
            "duration_ms": 0.0,
        }

        try:
            if not hook.should_execute(context):
                duration_ms = (time.perf_counter() - start_time) * 1000
                result["duration_ms"] = duration_ms
                result["executed"] = False

                # Create receipt for skipped hook
                receipt = Receipt(
                    hook_id=hook.name,
                    phase=context.phase,
                    timestamp=timestamp,
                    success=True,
                    duration_ms=duration_ms,
                    metadata={"skipped": True},
                )
                context.receipts.append(receipt)

                return result

            hook.execute(context)

            duration_ms = (time.perf_counter() - start_time) * 1000
            result["success"] = True
            result["executed"] = True
            result["duration_ms"] = duration_ms

            # Create receipt for successful execution
            receipt = Receipt(
                hook_id=hook.name, phase=context.phase, timestamp=timestamp, success=True, duration_ms=duration_ms
            )
            context.receipts.append(receipt)

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            result["error"] = str(e)
            result["duration_ms"] = duration_ms

            # Create receipt for failed execution
            receipt = Receipt(
                hook_id=hook.name,
                phase=context.phase,
                timestamp=timestamp,
                success=False,
                duration_ms=duration_ms,
                error=str(e),
            )
            context.receipts.append(receipt)

        return result

    def get_execution_history(self) -> list[dict[str, Any]]:
        """Get execution history.

        Returns
        -------
        list[dict[str, Any]]
            All execution results

        """
        return self._execution_history.copy()

    def clear_history(self) -> None:
        """Clear execution history."""
        self._execution_history.clear()


@dataclass
class FakeTransactionStore:
    """In-memory transaction storage for testing.

    Stores transactions and provides lookup capabilities.

    Examples
    --------
    >>> store = FakeTransactionStore()
    >>> txn = Transaction(
    ...     transaction_id="txn-001",
    ...     provenance=ProvenanceRecord(agent="test_user", timestamp=datetime.now(UTC), reason="test transaction"),
    ... )
    >>> store.save(txn)
    >>> assert store.get("txn-001") == txn
    >>> assert len(store.all()) == 1

    """

    _transactions: dict[str, Transaction] = field(default_factory=dict)

    def save(self, transaction: Transaction) -> None:
        """Store a transaction.

        Parameters
        ----------
        transaction : Transaction
            Transaction to store

        """
        self._transactions[transaction.transaction_id] = transaction

    def get(self, txn_id: str) -> Transaction | None:
        """Get transaction by ID.

        Parameters
        ----------
        txn_id : str
            Transaction ID

        Returns
        -------
        Transaction | None
            Transaction if found, None otherwise

        """
        return self._transactions.get(txn_id)

    def all(self) -> list[Transaction]:
        """Get all transactions.

        Returns
        -------
        list[Transaction]
            All stored transactions

        """
        return list(self._transactions.values())

    def committed(self) -> list[Transaction]:
        """Get committed transactions.

        Returns
        -------
        list[Transaction]
            Committed transactions

        """
        return [t for t in self._transactions.values() if t.committed]

    def rolled_back(self) -> list[Transaction]:
        """Get rolled back transactions.

        Returns
        -------
        list[Transaction]
            Rolled back transactions

        """
        return [t for t in self._transactions.values() if t.rolled_back]

    def count(self) -> int:
        """Count total transactions.

        Returns
        -------
        int
            Transaction count

        """
        return len(self._transactions)

    def clear(self) -> None:
        """Clear all transactions."""
        self._transactions.clear()


@dataclass
class FakeIngestionPipeline:
    """In-memory ingestion pipeline for testing.

    Simplified ingestion that converts JSON to RDF without full validation.

    Examples
    --------
    >>> pipeline = FakeIngestionPipeline()
    >>> result = pipeline.ingest_json(data={"type": "Person", "name": "Alice"}, agent="test_service")
    >>> assert result.success is True
    >>> assert result.triples_added > 0

    """

    rdf_store: FakeRdfStore = field(default_factory=FakeRdfStore)
    _ingestion_history: list[dict[str, Any]] = field(default_factory=list)

    def ingest_json(
        self, data: dict[str, Any] | list[dict[str, Any]], agent: str, reason: str | None = None
    ) -> dict[str, Any]:
        """Ingest JSON data.

        Parameters
        ----------
        data : dict[str, Any] | list[dict[str, Any]]
            JSON data to ingest
        agent : str
            Agent performing ingestion
        reason : str, optional
            Reason for ingestion

        Returns
        -------
        dict[str, Any]
            Ingestion result

        """
        items = data if isinstance(data, list) else [data]
        txn_id = f"txn-{uuid4()}"

        try:
            triples_added = 0
            for item in items:
                triples_added += self._json_to_rdf(item)

            result = {
                "success": True,
                "triples_added": triples_added,
                "transaction_id": txn_id,
                "agent": agent,
                "reason": reason,
            }

            self._ingestion_history.append(result)
            return result

        except Exception as e:
            result = {"success": False, "triples_added": 0, "transaction_id": txn_id, "error": str(e)}
            self._ingestion_history.append(result)
            return result

    def _json_to_rdf(self, data: dict[str, Any]) -> int:
        """Convert JSON to RDF triples.

        Parameters
        ----------
        data : dict[str, Any]
            JSON object

        Returns
        -------
        int
            Number of triples added

        """
        entity_id = data.get("id", str(uuid4()))
        subject = URIRef(f"http://unrdf.org/data/{entity_id}")

        count = 0
        for key, value in data.items():
            if key == "id":
                continue

            predicate = UNRDF[key]
            obj = Literal(str(value))
            self.rdf_store.add_triple(subject, predicate, obj)
            count += 1

        return count

    def get_history(self) -> list[dict[str, Any]]:
        """Get ingestion history.

        Returns
        -------
        list[dict[str, Any]]
            All ingestion results

        """
        return self._ingestion_history.copy()

    def clear_history(self) -> None:
        """Clear ingestion history."""
        self._ingestion_history.clear()


__all__ = [
    "FakeHookExecutor",
    "FakeHookRegistry",
    "FakeIngestionPipeline",
    "FakeRdfStore",
    "FakeReceiptStore",
    "FakeTransactionStore",
]
