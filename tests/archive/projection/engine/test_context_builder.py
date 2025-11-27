"""Tests for context builder.

Chicago School TDD: Test behavior, not implementation.
Tests verify correct query execution and context construction.
"""

from __future__ import annotations

from typing import Any

import pytest

import time

from kgcl.projection.domain.descriptors import QueryDescriptor, QuerySource
from kgcl.projection.domain.exceptions import QueryExecutionError, QueryTimeoutError, ResourceLimitExceeded
from kgcl.projection.engine.context_builder import ContextBuilder, QueryContext
from kgcl.projection.ports.graph_client import GraphClient


class MockGraphClient:
    """Test double for GraphClient."""

    def __init__(self, graph_id: str, results: dict[str, list[dict[str, Any]]]) -> None:
        """Initialize mock with predefined results."""
        self._graph_id = graph_id
        self._results = results

    @property
    def graph_id(self) -> str:
        """Return graph identifier."""
        return self._graph_id

    def query(self, sparql: str) -> list[dict[str, Any]]:
        """Return mock results based on query content."""
        # Match queries by content
        for key, value in self._results.items():
            if key in sparql:
                return value
        return []

    def ask(self, sparql: str) -> bool:
        """Return mock boolean result."""
        return True

    def construct(self, sparql: str) -> str:
        """Return mock RDF graph."""
        return ""


class FailingGraphClient:
    """Test double that fails on query execution."""

    @property
    def graph_id(self) -> str:
        """Return graph identifier."""
        return "failing"

    def query(self, sparql: str) -> list[dict[str, Any]]:
        """Raise exception on query."""
        raise RuntimeError("Query execution failed")

    def ask(self, sparql: str) -> bool:
        """Raise exception on ask."""
        raise RuntimeError("ASK execution failed")

    def construct(self, sparql: str) -> str:
        """Raise exception on construct."""
        raise RuntimeError("CONSTRUCT execution failed")


class TestContextBuilder:
    """Test context builder behavior."""

    def test_initialization(self) -> None:
        """Initialize builder with graph client."""
        client = MockGraphClient("test", {})

        builder = ContextBuilder(client)

        assert builder.graph_client.graph_id == "test"

    def test_execute_single_query(self) -> None:
        """Execute single query and return results."""
        client = MockGraphClient("main", {"Entity": [{"s": "ex:Entity1"}, {"s": "ex:Entity2"}]})
        builder = ContextBuilder(client)

        query = QueryDescriptor(
            name="entities",
            purpose="Fetch all entities",
            source=QuerySource.INLINE,
            content="SELECT ?s WHERE { ?s a ex:Entity }",
        )

        results = builder.execute_queries((query,))

        assert "entities" in results
        assert len(results["entities"]) == 2
        assert results["entities"][0]["s"] == "ex:Entity1"
        assert results["entities"][1]["s"] == "ex:Entity2"

    def test_execute_multiple_queries(self) -> None:
        """Execute multiple queries in sequence."""
        client = MockGraphClient(
            "main", {"Entity": [{"s": "ex:Entity1"}], "FILTER": [{"p": "ex:prop1"}, {"p": "ex:prop2"}]}
        )
        builder = ContextBuilder(client)

        q1 = QueryDescriptor(
            name="entities",
            purpose="Fetch entities",
            source=QuerySource.INLINE,
            content="SELECT ?s WHERE { ?s a ex:Entity }",
        )
        q2 = QueryDescriptor(
            name="properties",
            purpose="Fetch properties",
            source=QuerySource.INLINE,
            content="SELECT ?p WHERE { ?s ?p ?o . FILTER(?p != rdf:type) }",
        )

        results = builder.execute_queries((q1, q2))

        assert len(results) == 2
        assert "entities" in results
        assert "properties" in results
        assert len(results["entities"]) == 1
        assert len(results["properties"]) == 2

    def test_execute_no_queries(self) -> None:
        """Execute empty query tuple returns empty results."""
        client = MockGraphClient("main", {})
        builder = ContextBuilder(client)

        results = builder.execute_queries(())

        assert results == {}

    def test_execute_query_no_results(self) -> None:
        """Execute query that returns no results."""
        client = MockGraphClient("main", {})
        builder = ContextBuilder(client)

        query = QueryDescriptor(
            name="empty",
            purpose="Query with no matches",
            source=QuerySource.INLINE,
            content="SELECT ?s WHERE { ?s a ex:NonExistent }",
        )

        results = builder.execute_queries((query,))

        assert "empty" in results
        assert results["empty"] == []

    def test_execute_query_failure(self) -> None:
        """Fail when query execution raises exception."""
        client = FailingGraphClient()
        builder = ContextBuilder(client)

        query = QueryDescriptor(
            name="failing", purpose="Failing query", source=QuerySource.INLINE, content="SELECT ?s WHERE { ?s ?p ?o }"
        )

        with pytest.raises(QueryExecutionError) as exc:
            builder.execute_queries((query,))

        assert exc.value.query_name == "failing"
        assert "Query execution failed" in exc.value.reason

    def test_build_context_with_queries(self) -> None:
        """Build context from queries."""
        client = MockGraphClient("main", {"Entity": [{"s": "ex:Entity1"}]})
        builder = ContextBuilder(client)

        query = QueryDescriptor(
            name="entities",
            purpose="Fetch entities",
            source=QuerySource.INLINE,
            content="SELECT ?s WHERE { ?s a ex:Entity }",
        )

        context = builder.build_context((query,))

        assert isinstance(context, QueryContext)
        assert "entities" in context.sparql
        assert len(context.sparql["entities"]) == 1
        assert context.params == {}

    def test_build_context_with_params(self) -> None:
        """Build context with user parameters."""
        client = MockGraphClient("main", {})
        builder = ContextBuilder(client)

        params = {"app_name": "MyApp", "version": "1.0.0", "debug": True}

        context = builder.build_context((), params)

        assert context.params["app_name"] == "MyApp"
        assert context.params["version"] == "1.0.0"
        assert context.params["debug"] is True

    def test_build_context_with_queries_and_params(self) -> None:
        """Build context from both queries and params."""
        client = MockGraphClient("main", {"label ?name": [{"name": "Alice"}, {"name": "Bob"}]})
        builder = ContextBuilder(client)

        query = QueryDescriptor(
            name="users",
            purpose="Fetch users",
            source=QuerySource.INLINE,
            content="SELECT ?name WHERE { ?s rdfs:label ?name }",
        )

        params = {"title": "User List"}

        context = builder.build_context((query,), params)

        assert "users" in context.sparql
        assert len(context.sparql["users"]) == 2
        assert context.params["title"] == "User List"

    def test_build_context_empty_params(self) -> None:
        """Build context with None params creates empty dict."""
        client = MockGraphClient("main", {})
        builder = ContextBuilder(client)

        context = builder.build_context((), None)

        assert context.params == {}

    def test_query_context_frozen(self) -> None:
        """Verify QueryContext is immutable."""
        context = QueryContext(sparql={"q1": [{"s": "value"}]}, params={"p1": "value"})

        with pytest.raises(AttributeError):
            context.sparql = {}  # type: ignore[misc]

    def test_results_conversion_to_dict(self) -> None:
        """Verify results are converted to dicts with Any values."""

        class CustomBinding:
            """Custom binding type."""

            def __init__(self, data: dict[str, str]) -> None:
                self._data = data

            def __iter__(self) -> Any:
                return iter(self._data.items())

        class ClientWithCustomBindings:
            """Client that returns custom binding objects."""

            @property
            def graph_id(self) -> str:
                return "custom"

            def query(self, sparql: str) -> list[dict[str, Any]]:
                return [CustomBinding({"s": "ex:Entity1"})]  # type: ignore[list-item]

            def ask(self, sparql: str) -> bool:
                return True

            def construct(self, sparql: str) -> str:
                return ""

        client = ClientWithCustomBindings()
        builder = ContextBuilder(client)

        query = QueryDescriptor(name="test", purpose="Test", source=QuerySource.INLINE, content="SELECT ?s")

        results = builder.execute_queries((query,))

        # Results should be converted to plain dicts
        assert isinstance(results["test"][0], dict)


# =============================================================================
# Resource Limit Tests
# =============================================================================


class TestContextBuilderLimits:
    """Tests for query result limits."""

    def test_max_query_results_enforced(self) -> None:
        """Raises ResourceLimitExceeded when query exceeds max_results."""
        # Return 100 results
        results = [{"s": f"ex:Entity{i}"} for i in range(100)]
        client = MockGraphClient("main", {"Entity": results})
        builder = ContextBuilder(client, max_query_results=50)

        query = QueryDescriptor(
            name="entities",
            purpose="Fetch all entities",
            source=QuerySource.INLINE,
            content="SELECT ?s WHERE { ?s a ex:Entity }",
        )

        with pytest.raises(ResourceLimitExceeded) as exc:
            builder.execute_queries((query,))

        assert exc.value.limit == 50
        assert exc.value.actual == 100
        assert "query_results:entities" in exc.value.resource

    def test_max_query_results_allows_under_limit(self) -> None:
        """Allows queries under the result limit."""
        results = [{"s": f"ex:Entity{i}"} for i in range(10)]
        client = MockGraphClient("main", {"Entity": results})
        builder = ContextBuilder(client, max_query_results=50)

        query = QueryDescriptor(
            name="entities",
            purpose="Fetch entities",
            source=QuerySource.INLINE,
            content="SELECT ?s WHERE { ?s a ex:Entity }",
        )

        query_results = builder.execute_queries((query,))

        assert len(query_results["entities"]) == 10

    def test_max_query_results_allows_exact_limit(self) -> None:
        """Allows exactly max_results without raising."""
        results = [{"s": f"ex:Entity{i}"} for i in range(50)]
        client = MockGraphClient("main", {"Entity": results})
        builder = ContextBuilder(client, max_query_results=50)

        query = QueryDescriptor(
            name="entities",
            purpose="Fetch entities",
            source=QuerySource.INLINE,
            content="SELECT ?s WHERE { ?s a ex:Entity }",
        )

        query_results = builder.execute_queries((query,))

        assert len(query_results["entities"]) == 50

    def test_no_limit_when_none(self) -> None:
        """No limit enforced when max_query_results is None."""
        results = [{"s": f"ex:Entity{i}"} for i in range(10000)]
        client = MockGraphClient("main", {"Entity": results})
        builder = ContextBuilder(client, max_query_results=None)

        query = QueryDescriptor(
            name="entities",
            purpose="Fetch all",
            source=QuerySource.INLINE,
            content="SELECT ?s WHERE { ?s a ex:Entity }",
        )

        query_results = builder.execute_queries((query,))

        assert len(query_results["entities"]) == 10000


# =============================================================================
# Query Timeout Tests
# =============================================================================


class SlowGraphClient:
    """Test double that sleeps during query execution."""

    def __init__(self, sleep_seconds: float) -> None:
        """Initialize with sleep duration."""
        self._sleep_seconds = sleep_seconds

    @property
    def graph_id(self) -> str:
        """Return graph identifier."""
        return "slow"

    def query(self, sparql: str) -> list[dict[str, Any]]:
        """Sleep then return results."""
        time.sleep(self._sleep_seconds)
        return [{"s": "ex:Entity1"}]

    def ask(self, sparql: str) -> bool:
        """Execute ASK."""
        time.sleep(self._sleep_seconds)
        return True

    def construct(self, sparql: str) -> str:
        """Execute CONSTRUCT."""
        time.sleep(self._sleep_seconds)
        return ""


@pytest.mark.slow
class TestContextBuilderTimeout:
    """Tests for query timeout functionality."""

    def test_query_timeout_raises_error(self) -> None:
        """Slow query raises QueryTimeoutError."""
        client = SlowGraphClient(sleep_seconds=1.0)
        builder = ContextBuilder(client, query_timeout_seconds=0.05)

        query = QueryDescriptor(
            name="slow_query",
            purpose="Test timeout",
            source=QuerySource.INLINE,
            content="SELECT ?s WHERE { ?s ?p ?o }",
        )

        with pytest.raises(QueryTimeoutError) as exc:
            builder.execute_queries((query,))

        assert exc.value.query_name == "slow_query"
        assert exc.value.timeout_seconds == 0.05

    def test_fast_query_succeeds_with_timeout(self) -> None:
        """Fast query succeeds when timeout is configured."""
        client = MockGraphClient("main", {"Entity": [{"s": "ex:Entity1"}]})
        builder = ContextBuilder(client, query_timeout_seconds=1.0)

        query = QueryDescriptor(
            name="fast_query",
            purpose="Test fast",
            source=QuerySource.INLINE,
            content="SELECT ?s WHERE { ?s a ex:Entity }",
        )

        results = builder.execute_queries((query,))

        assert len(results["fast_query"]) == 1

    def test_no_timeout_when_none(self) -> None:
        """No timeout enforced when query_timeout_seconds is None."""
        # Use a fast client to test that None timeout doesn't break things
        client = MockGraphClient("main", {"Entity": [{"s": "ex:Entity1"}]})
        builder = ContextBuilder(client, query_timeout_seconds=None)

        query = QueryDescriptor(
            name="query",
            purpose="Test no timeout",
            source=QuerySource.INLINE,
            content="SELECT ?s WHERE { ?s a ex:Entity }",
        )

        results = builder.execute_queries((query,))

        assert len(results["query"]) == 1
