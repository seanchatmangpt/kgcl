"""Oxigraph RDF store wrapper for KGC Hybrid Engine.

Provides a clean interface to pyoxigraph with transaction support,
multiple format loading, and comprehensive query capabilities.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from pyoxigraph import QuerySolution, QuerySolutions, RdfFormat, Store, parse


# Custom Exceptions
class StoreError(Exception):
    """Base exception for store operations."""


class QueryError(StoreError):
    """Exception for query execution failures."""


class UpdateError(StoreError):
    """Exception for update operation failures."""


@dataclass(frozen=True)
class QueryResult:
    """Result from a SPARQL query.

    Attributes
    ----------
    bindings : list[dict[str, Any]]
        Variable bindings from query results
    variables : list[str]
        Query result variables
    """

    bindings: list[dict[str, Any]]
    variables: list[str]


class OxigraphStore:
    """Wrapper around pyoxigraph Store with enhanced API.

    Provides methods for loading RDF data, executing SPARQL queries,
    and managing the triple store with transaction support.

    Parameters
    ----------
    path : str | None, optional
        Path to persistent store directory. If None, creates in-memory store.

    Attributes
    ----------
    store : Store
        Underlying pyoxigraph Store instance
    is_persistent : bool
        Whether store is persistent or in-memory
    """

    def __init__(self, path: str | None = None) -> None:
        """Initialize Oxigraph store.

        Parameters
        ----------
        path : str | None, optional
            Path to persistent store directory. If None, creates in-memory store.

        Raises
        ------
        StoreError
            If store initialization fails
        """
        try:
            self.store = Store(path)
            self.is_persistent = path is not None
        except Exception as e:
            raise StoreError(f"Failed to initialize store: {e}") from e

    def load_turtle(self, data: str) -> int:
        """Load Turtle (TTL) format RDF data.

        Parameters
        ----------
        data : str
            Turtle format RDF data

        Returns
        -------
        int
            Number of triples loaded

        Raises
        ------
        StoreError
            If loading fails
        """
        try:
            count_before = self.triple_count()
            for triple in parse(data, format=RdfFormat.TURTLE):
                self.store.add(triple)
            return self.triple_count() - count_before
        except Exception as e:
            raise StoreError(f"Failed to load Turtle data: {e}") from e

    def load_n3(self, data: str) -> int:
        """Load N3 format RDF data.

        Parameters
        ----------
        data : str
            N3 format RDF data

        Returns
        -------
        int
            Number of triples loaded

        Raises
        ------
        StoreError
            If loading fails
        """
        try:
            count_before = self.triple_count()
            for triple in parse(data, format=RdfFormat.N3):
                self.store.add(triple)
            return self.triple_count() - count_before
        except Exception as e:
            raise StoreError(f"Failed to load N3 data: {e}") from e

    def query(self, sparql: str) -> list[dict[str, Any]]:
        """Execute SPARQL SELECT query.

        Parameters
        ----------
        sparql : str
            SPARQL SELECT query

        Returns
        -------
        list[dict[str, Any]]
            List of variable bindings

        Raises
        ------
        QueryError
            If query execution fails
        """
        try:
            results = self.store.query(sparql)
            if not isinstance(results, QuerySolutions):
                raise QueryError("Expected SELECT query results")

            # Get variables from the QuerySolutions object
            variables = results.variables

            bindings: list[dict[str, Any]] = []
            for solution in results:
                if isinstance(solution, QuerySolution):
                    binding: dict[str, Any] = {}
                    for var in variables:
                        value = solution[var]
                        if value is not None:
                            # Convert RDF terms to Python types
                            # Use var.value to get 's' instead of '?s'
                            binding[var.value] = self._convert_term(value)
                    bindings.append(binding)

            return bindings
        except Exception as e:
            raise QueryError(f"Query execution failed: {e}") from e

    def ask(self, sparql: str) -> bool:
        """Execute SPARQL ASK query.

        Parameters
        ----------
        sparql : str
            SPARQL ASK query

        Returns
        -------
        bool
            Query result

        Raises
        ------
        QueryError
            If query execution fails
        """
        try:
            result = self.store.query(sparql)
            if isinstance(result, bool):
                return result
            raise QueryError("Expected ASK query result")
        except Exception as e:
            raise QueryError(f"ASK query execution failed: {e}") from e

    def update(self, sparql: str) -> None:
        """Execute SPARQL UPDATE query.

        Parameters
        ----------
        sparql : str
            SPARQL UPDATE query

        Raises
        ------
        UpdateError
            If update execution fails
        """
        try:
            self.store.update(sparql)
        except Exception as e:
            raise UpdateError(f"Update execution failed: {e}") from e

    def construct(self, sparql: str) -> str:
        """Execute SPARQL CONSTRUCT query.

        Parameters
        ----------
        sparql : str
            SPARQL CONSTRUCT query

        Returns
        -------
        str
            Constructed triples in Turtle format

        Raises
        ------
        QueryError
            If query execution fails
        """
        try:
            results = self.store.query(sparql)
            # CONSTRUCT queries return an iterator of triples, not QuerySolutions
            # Check that it's NOT QuerySolutions (SELECT queries return QuerySolutions)
            if isinstance(results, QuerySolutions):
                raise QueryError("Expected CONSTRUCT query, got SELECT query results")

            # Collect triples
            triples: list[str] = []
            for triple in results:
                triples.append(str(triple))

            # Return as Turtle-like format
            return "\n".join(triples) + "\n" if triples else ""
        except Exception as e:
            raise QueryError(f"CONSTRUCT query execution failed: {e}") from e

    def dump(self) -> str:
        """Dump entire store as Turtle.

        Returns
        -------
        str
            All triples in Turtle format

        Raises
        ------
        StoreError
            If dump fails
        """
        try:
            output: list[str] = []
            for quad in self.store:
                # Extract triple (ignore graph)
                triple_str = f"{quad.subject} {quad.predicate} {quad.object} ."
                output.append(triple_str)
            return "\n".join(output) + "\n" if output else ""
        except Exception as e:
            raise StoreError(f"Store dump failed: {e}") from e

    def triple_count(self) -> int:
        """Count total triples in store.

        Returns
        -------
        int
            Number of triples

        Raises
        ------
        StoreError
            If count fails
        """
        try:
            return len(self.store)
        except Exception as e:
            raise StoreError(f"Triple count failed: {e}") from e

    def clear(self) -> None:
        """Clear all triples from store.

        Raises
        ------
        StoreError
            If clear operation fails
        """
        try:
            self.store.clear()
        except Exception as e:
            raise StoreError(f"Store clear failed: {e}") from e

    @contextmanager
    def transaction(self) -> Iterator[OxigraphStore]:
        """Create transaction context for atomic operations.

        Yields
        ------
        OxigraphStore
            Store instance for transaction operations

        Raises
        ------
        StoreError
            If transaction fails

        Examples
        --------
        >>> with store.transaction() as txn:
        ...     txn.load_turtle(data)
        ...     txn.update(sparql_update)
        """
        # Pyoxigraph doesn't expose transactions directly,
        # so we simulate with backup/restore on error
        backup_count = self.triple_count()
        backup_data = self.dump()

        try:
            yield self
        except Exception as e:
            # Restore on error
            try:
                self.clear()
                if backup_data:
                    self.load_turtle(backup_data)
            except Exception as restore_error:
                raise StoreError(f"Transaction rollback failed: {restore_error}") from e
            raise StoreError(f"Transaction failed: {e}") from e

    def _convert_term(self, term: Any) -> Any:
        """Convert RDF term to Python type.

        Parameters
        ----------
        term : Any
            RDF term from pyoxigraph

        Returns
        -------
        Any
            Python representation
        """
        # Convert based on term type
        term_str = str(term)

        # Check for literal with datatype
        if hasattr(term, "value"):
            return term.value

        # Check for URI
        if term_str.startswith("<") and term_str.endswith(">"):
            return term_str[1:-1]

        # Return as string
        return term_str


class TransactionContext:
    """Context manager for atomic store operations.

    Parameters
    ----------
    store : OxigraphStore
        Store to create transaction for

    Examples
    --------
    >>> with TransactionContext(store) as txn:
    ...     txn.load_turtle(data)
    ...     txn.update(sparql)
    """

    def __init__(self, store: OxigraphStore) -> None:
        """Initialize transaction context.

        Parameters
        ----------
        store : OxigraphStore
            Store to create transaction for
        """
        self.store = store
        self._backup: str = ""

    def __enter__(self) -> OxigraphStore:
        """Enter transaction context.

        Returns
        -------
        OxigraphStore
            Store instance for operations
        """
        self._backup = self.store.dump()
        return self.store

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        """Exit transaction context.

        Parameters
        ----------
        exc_type : type[BaseException] | None
            Exception type if raised
        exc_val : BaseException | None
            Exception value if raised
        exc_tb : Any
            Exception traceback
        """
        if exc_type is not None:
            # Rollback on error
            try:
                self.store.clear()
                if self._backup:
                    self.store.load_turtle(self._backup)
            except Exception as e:
                raise StoreError(f"Transaction rollback failed: {e}") from exc_val
