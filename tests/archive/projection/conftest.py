"""Shared fixtures for projection tests."""

from __future__ import annotations

from typing import Any

import pytest

from kgcl.projection.domain.descriptors import (
    OntologyConfig,
    QueryDescriptor,
    QuerySource,
    TemplateDescriptor,
    TemplateMetadata,
)
from kgcl.projection.domain.result import ProjectionResult
from kgcl.projection.ports.graph_client import GraphClient


class MockGraphClient:
    """Mock graph client for testing.

    Provides a simple in-memory mock that satisfies the GraphClient protocol.
    """

    def __init__(self, graph_id: str = "main", query_results: list[dict[str, Any]] | None = None) -> None:
        """Initialize mock client.

        Parameters
        ----------
        graph_id : str
            Identifier for this client.
        query_results : list[dict[str, Any]] | None
            Results to return from query() calls.
        """
        self._graph_id = graph_id
        self._query_results = query_results or []
        self._query_log: list[str] = []

    @property
    def graph_id(self) -> str:
        """Return graph identifier."""
        return self._graph_id

    def query(self, sparql: str) -> list[dict[str, Any]]:
        """Execute mock query."""
        self._query_log.append(sparql)
        return self._query_results

    def ask(self, sparql: str) -> bool:
        """Execute mock ASK query."""
        self._query_log.append(sparql)
        return len(self._query_results) > 0

    def construct(self, sparql: str) -> str:
        """Execute mock CONSTRUCT query."""
        self._query_log.append(sparql)
        return ""

    @property
    def query_log(self) -> list[str]:
        """Return log of executed queries."""
        return self._query_log


@pytest.fixture
def mock_graph_client() -> MockGraphClient:
    """Create mock graph client fixture."""
    return MockGraphClient(
        graph_id="main",
        query_results=[
            {"entity": "http://example.org/Entity1", "name": "Entity One"},
            {"entity": "http://example.org/Entity2", "name": "Entity Two"},
        ],
    )


@pytest.fixture
def sample_query() -> QueryDescriptor:
    """Create sample query descriptor fixture."""
    return QueryDescriptor(
        name="all_entities",
        purpose="Fetch all entities",
        source=QuerySource.INLINE,
        content="SELECT ?entity ?name WHERE { ?entity rdfs:label ?name }",
    )


@pytest.fixture
def sample_template_descriptor(sample_query: QueryDescriptor) -> TemplateDescriptor:
    """Create sample template descriptor fixture."""
    return TemplateDescriptor(
        id="http://example.org/templates/api",
        engine="jinja2",
        language="python",
        framework="fastapi",
        version="1.0.0",
        ontology=OntologyConfig(graph_id="main", base_iri="http://example.org/"),
        queries=(sample_query,),
        n3_rules=(),
        metadata=TemplateMetadata(author="test", description="Test template", tags=("test", "api")),
        template_path="templates/api.j2",
        raw_content="{% for e in sparql.all_entities %}{{ e.name }}{% endfor %}",
    )


@pytest.fixture
def sample_projection_result() -> ProjectionResult:
    """Create sample projection result fixture."""
    return ProjectionResult(
        template_id="http://example.org/templates/api",
        version="1.0.0",
        content="Entity One\nEntity Two",
        media_type="text/x-python",
        context_info={"query_count": 1, "render_time_ms": 5.5},
    )
