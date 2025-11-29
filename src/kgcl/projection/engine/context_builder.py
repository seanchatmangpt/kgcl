"""Context builder - SPARQL results to Jinja context mapping.

This module implements the ContextBuilder which executes SPARQL queries
against GraphClient instances and builds the Jinja context dictionary
for template rendering.

Examples
--------
>>> from kgcl.projection.domain.descriptors import QueryDescriptor, QuerySource
>>> class MockClient:
...     @property
...     def graph_id(self) -> str:
...         return "main"
...
...     def query(self, sparql: str) -> list[dict[str, object]]:
...         return [{"name": "Alice"}]
...
...     def ask(self, sparql: str) -> bool:
...         return True
...
...     def construct(self, sparql: str) -> str:
...         return ""
>>> builder = ContextBuilder(MockClient())
>>> q = QueryDescriptor("users", "Get users", QuerySource.INLINE, "SELECT ?name")
>>> ctx = builder.build_context((q,), {"version": "1.0"})
>>> ctx.sparql["users"]
[{'name': 'Alice'}]
>>> ctx.params["version"]
'1.0'
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kgcl.projection.domain.descriptors import QueryDescriptor
from kgcl.projection.domain.exceptions import QueryExecutionError, QueryTimeoutError, ResourceLimitExceeded
from kgcl.projection.engine.timeout_executor import execute_with_timeout
from kgcl.projection.ports.graph_client import GraphClient

__all__ = ["QueryContext", "ContextBuilder"]


@dataclass(frozen=True)
class QueryContext:
    """Context built from executed queries.

    Parameters
    ----------
    sparql : dict[str, list[dict[str, Any]]]
        Mapping of query name to result bindings.
    params : dict[str, Any]
        User-provided parameters merged into context.

    Examples
    --------
    >>> ctx = QueryContext(sparql={"users": [{"name": "Alice"}]}, params={"version": "1.0"})
    >>> ctx.sparql["users"][0]["name"]
    'Alice'
    """

    sparql: dict[str, list[dict[str, Any]]]
    params: dict[str, Any]


class ContextBuilder:
    """Builds Jinja context from SPARQL query execution.

    The ContextBuilder executes QueryDescriptor instances against a
    GraphClient and constructs the context dictionary used for
    template rendering.

    Parameters
    ----------
    graph_client : GraphClient
        Client for executing SPARQL queries.

    Examples
    --------
    >>> class MockClient:
    ...     @property
    ...     def graph_id(self) -> str:
    ...         return "test"
    ...
    ...     def query(self, s: str) -> list[dict[str, Any]]:
    ...         return []
    ...
    ...     def ask(self, s: str) -> bool:
    ...         return False
    ...
    ...     def construct(self, s: str) -> str:
    ...         return ""
    >>> builder = ContextBuilder(MockClient())
    >>> builder.graph_client.graph_id
    'test'
    """

    def __init__(
        self,
        graph_client: GraphClient,
        max_query_results: int | None = None,
        query_timeout_seconds: float | None = None,
    ) -> None:
        """Initialize context builder with graph client.

        Parameters
        ----------
        graph_client : GraphClient
            Client for executing SPARQL queries.
        max_query_results : int | None
            Maximum number of results per query. If None, no limit.
        query_timeout_seconds : float | None
            Maximum query execution time in seconds. If None, no timeout.
        """
        self.graph_client = graph_client
        self._max_query_results = max_query_results
        self._query_timeout_seconds = query_timeout_seconds

    def execute_queries(self, queries: tuple[QueryDescriptor, ...]) -> dict[str, list[dict[str, Any]]]:
        """Execute all queries and return results mapping.

        Parameters
        ----------
        queries : tuple[QueryDescriptor, ...]
            Queries to execute.

        Returns
        -------
        dict[str, list[dict[str, Any]]]
            Mapping of query name to result bindings.

        Raises
        ------
        QueryExecutionError
            If any query execution fails.

        Examples
        --------
        >>> from kgcl.projection.domain.descriptors import QueryDescriptor, QuerySource
        >>> class MockClient:
        ...     @property
        ...     def graph_id(self) -> str:
        ...         return "test"
        ...
        ...     def query(self, s: str) -> list[dict[str, Any]]:
        ...         if "Entity" in s:
        ...             return [{"s": "ex:Entity1"}, {"s": "ex:Entity2"}]
        ...         return []
        ...
        ...     def ask(self, s: str) -> bool:
        ...         return False
        ...
        ...     def construct(self, s: str) -> str:
        ...         return ""
        >>> builder = ContextBuilder(MockClient())
        >>> q = QueryDescriptor(
        ...     name="entities",
        ...     purpose="Get all",
        ...     source=QuerySource.INLINE,
        ...     content="SELECT ?s WHERE { ?s a ex:Entity }",
        ... )
        >>> results = builder.execute_queries((q,))
        >>> len(results["entities"])
        2
        """
        results: dict[str, list[dict[str, Any]]] = {}

        for query in queries:
            try:
                # Execute query with optional timeout
                if self._query_timeout_seconds is not None:
                    bindings = execute_with_timeout(
                        lambda q=query.content: self.graph_client.query(q), self._query_timeout_seconds, query.name
                    )
                else:
                    bindings = self.graph_client.query(query.content)

                # Convert to list of dicts with Any values
                result_list = [dict(binding) for binding in bindings]

                # Check result limit
                if self._max_query_results is not None and len(result_list) > self._max_query_results:
                    raise ResourceLimitExceeded(
                        f"query_results:{query.name}", self._max_query_results, len(result_list)
                    )

                results[query.name] = result_list
            except (ResourceLimitExceeded, QueryTimeoutError):
                raise
            except Exception as e:
                msg = str(e)
                raise QueryExecutionError(query.name, query.content, msg) from e

        return results

    def build_context(self, queries: tuple[QueryDescriptor, ...], params: dict[str, Any] | None = None) -> QueryContext:
        """Build complete Jinja context from queries and params.

        Parameters
        ----------
        queries : tuple[QueryDescriptor, ...]
            Queries to execute.
        params : dict[str, Any] | None
            User-provided parameters to merge into context.

        Returns
        -------
        QueryContext
            Complete context for template rendering.

        Examples
        --------
        >>> from kgcl.projection.domain.descriptors import QueryDescriptor, QuerySource
        >>> class MockClient:
        ...     @property
        ...     def graph_id(self) -> str:
        ...         return "test"
        ...
        ...     def query(self, s: str) -> list[dict[str, Any]]:
        ...         return [{"name": "Alice"}]
        ...
        ...     def ask(self, s: str) -> bool:
        ...         return False
        ...
        ...     def construct(self, s: str) -> str:
        ...         return ""
        >>> builder = ContextBuilder(MockClient())
        >>> q = QueryDescriptor("users", "Get users", QuerySource.INLINE, "SELECT ?name")
        >>> ctx = builder.build_context((q,), {"app_name": "MyApp"})
        >>> ctx.sparql["users"][0]["name"]
        'Alice'
        >>> ctx.params["app_name"]
        'MyApp'
        """
        # Execute queries
        query_results = self.execute_queries(queries)

        # Build params dict
        merged_params = dict(params) if params else {}

        return QueryContext(sparql=query_results, params=merged_params)
