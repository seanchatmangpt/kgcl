"""State Mutator Port - Interface for atomic state mutations.

This port defines the contract for SPARQL UPDATE-based state mutation,
solving the monotonicity barrier identified in the thesis.

The key insight: N3/EYE can only ADD facts (monotonic), but workflows
require state TRANSITIONS (non-monotonic). SPARQL UPDATE provides
atomic DELETE/INSERT operations that enable true state mutation.
"""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True)
class Triple:
    """Immutable RDF triple representation.

    Parameters
    ----------
    subject : str
        Subject IRI or blank node.
    predicate : str
        Predicate IRI.
    obj : str
        Object (IRI, literal, or blank node).
    """

    subject: str
    predicate: str
    obj: str

    def to_sparql(self) -> str:
        """Serialize triple for SPARQL.

        Returns
        -------
        str
            SPARQL-formatted triple.
        """
        # Handle literals vs IRIs
        if self.obj.startswith('"') or self.obj.startswith("'"):
            obj_str = self.obj
        elif self.obj.startswith("<") or ":" in self.obj:
            # Already an IRI (bracketed or prefixed)
            obj_str = self.obj
        else:
            # Assume literal string
            obj_str = f'"{self.obj}"'

        subj = self.subject if self.subject.startswith("<") else f"<{self.subject}>"
        pred = self.predicate if self.predicate.startswith("<") else f"<{self.predicate}>"

        return f"{subj} {pred} {obj_str}"


@dataclass(frozen=True)
class StateMutation:
    """Represents an atomic state mutation operation.

    A mutation consists of triples to DELETE and triples to INSERT,
    executed atomically within a single SPARQL UPDATE transaction.

    This solves the three fundamental barriers:
    1. Monotonicity: DELETE removes old facts
    2. Counter updates: DELETE old value, INSERT new value
    3. Marker cleanup: DELETE guard markers after use

    Parameters
    ----------
    delete_patterns : tuple[Triple, ...]
        Triples to remove from the graph.
    insert_patterns : tuple[Triple, ...]
        Triples to add to the graph.
    where_patterns : tuple[Triple, ...]
        WHERE clause patterns for binding variables.
    bindings : dict[str, str]
        Variable bindings (e.g., {"?new": "BIND(?old + 1 AS ?new)"}).
    description : str
        Human-readable description of the mutation.
    """

    delete_patterns: tuple[Triple, ...] = field(default_factory=tuple)
    insert_patterns: tuple[Triple, ...] = field(default_factory=tuple)
    where_patterns: tuple[Triple, ...] = field(default_factory=tuple)
    bindings: dict[str, str] = field(default_factory=dict)
    description: str = ""

    def to_sparql(self, prefixes: str = "") -> str:
        """Generate SPARQL UPDATE query.

        Parameters
        ----------
        prefixes : str, optional
            SPARQL PREFIX declarations.

        Returns
        -------
        str
            Complete SPARQL UPDATE query.
        """
        parts = [prefixes] if prefixes else []

        # DELETE clause
        if self.delete_patterns:
            delete_triples = " .\n    ".join(t.to_sparql() for t in self.delete_patterns)
            parts.append(f"DELETE {{\n    {delete_triples} .\n}}")

        # INSERT clause
        if self.insert_patterns:
            insert_triples = " .\n    ".join(t.to_sparql() for t in self.insert_patterns)
            parts.append(f"INSERT {{\n    {insert_triples} .\n}}")

        # WHERE clause
        if self.where_patterns or self.bindings:
            where_parts = []
            if self.where_patterns:
                where_triples = " .\n    ".join(t.to_sparql() for t in self.where_patterns)
                where_parts.append(where_triples)
            for bind_expr in self.bindings.values():
                where_parts.append(bind_expr)
            parts.append(f"WHERE {{\n    {' .\n    '.join(where_parts)} .\n}}")

        return "\n".join(parts)


@dataclass(frozen=True)
class MutationResult:
    """Result of a state mutation operation.

    Parameters
    ----------
    success : bool
        Whether mutation completed successfully.
    mutations_applied : int
        Number of mutations that modified state.
    triples_deleted : int
        Number of triples removed.
    triples_inserted : int
        Number of triples added.
    error : str | None
        Error message if mutation failed.
    """

    success: bool
    mutations_applied: int = 0
    triples_deleted: int = 0
    triples_inserted: int = 0
    error: str | None = None


class StateMutator(Protocol):
    """Protocol for atomic state mutation operations.

    Implementations provide SPARQL UPDATE execution with
    transaction support for atomic multi-statement mutations.

    This is the key component that overcomes the monotonicity
    barrier identified in the thesis. While N3/EYE can only
    add facts, StateMutator enables true state transitions
    via DELETE/INSERT.
    """

    @abstractmethod
    def apply_mutation(self, mutation: StateMutation) -> MutationResult:
        """Apply a single atomic mutation.

        Parameters
        ----------
        mutation : StateMutation
            The mutation to apply.

        Returns
        -------
        MutationResult
            Result of the mutation.

        Raises
        ------
        MutationError
            If mutation fails and cannot be rolled back.
        """
        ...

    @abstractmethod
    def apply_mutations(self, mutations: Sequence[StateMutation]) -> MutationResult:
        """Apply multiple mutations atomically.

        All mutations succeed or all fail (transactional).

        Parameters
        ----------
        mutations : Sequence[StateMutation]
            Mutations to apply in order.

        Returns
        -------
        MutationResult
            Combined result of all mutations.

        Raises
        ------
        MutationError
            If any mutation fails.
        """
        ...

    @abstractmethod
    def execute_sparql_update(self, sparql: str) -> MutationResult:
        """Execute raw SPARQL UPDATE.

        Parameters
        ----------
        sparql : str
            SPARQL UPDATE query.

        Returns
        -------
        MutationResult
            Result of the update.
        """
        ...
