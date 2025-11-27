"""Tests for projection engine.

Chicago School TDD: Test behavior, not implementation.
Tests verify correct template rendering orchestration.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest

from kgcl.projection.domain.descriptors import (
    OntologyConfig,
    QueryDescriptor,
    QuerySource,
    TemplateDescriptor,
    TemplateMetadata,
)
from kgcl.projection.domain.exceptions import GraphNotFoundError, TemplateNotFoundError, TemplateRenderError
from kgcl.projection.domain.result import ProjectionResult
from kgcl.projection.engine.projection_engine import ProjectionConfig, ProjectionEngine
from kgcl.projection.ports.graph_client import GraphClient


class MockTemplateRegistry:
    """Test double for template registry."""

    def __init__(self, templates: dict[str, TemplateDescriptor]) -> None:
        """Initialize registry with templates."""
        self._templates = templates

    def get(self, template_name: str) -> TemplateDescriptor | None:
        """Get template by name."""
        return self._templates.get(template_name)


class MockGraphClient:
    """Test double for graph client."""

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


class TestProjectionEngine:
    """Test projection engine behavior."""

    def test_initialization(self) -> None:
        """Initialize engine with registry and clients."""
        registry = MockTemplateRegistry({})
        clients: dict[str, GraphClient] = {"main": MockGraphClient("main", {})}

        engine = ProjectionEngine(registry, clients)

        assert engine.template_registry == registry
        assert "main" in engine.graph_clients

    def test_initialization_with_config(self) -> None:
        """Initialize engine with custom config."""
        registry = MockTemplateRegistry({})
        clients: dict[str, GraphClient] = {}
        config = ProjectionConfig(cache_ttl=600, strict_mode=False)

        engine = ProjectionEngine(registry, clients, config=config)

        assert engine.config.cache_ttl == 600
        assert engine.config.strict_mode is False

    def test_render_simple_template(self) -> None:
        """Render template without queries."""
        template = TemplateDescriptor(
            id="http://example.org/greeting",
            engine="jinja2",
            language="text",
            framework="",
            version="1.0.0",
            ontology=OntologyConfig(graph_id="main"),
            queries=(),
            n3_rules=(),
            metadata=TemplateMetadata(),
            template_path="greeting.j2",
            raw_content="Hello {{ params.name }}!",
        )

        registry = MockTemplateRegistry({"greeting": template})
        clients: dict[str, GraphClient] = {"main": MockGraphClient("main", {})}
        engine = ProjectionEngine(registry, clients)

        result = engine.render("greeting", {"name": "Alice"})

        assert result.content == "Hello Alice!"
        assert result.template_id == "http://example.org/greeting"
        assert result.version == "1.0.0"

    def test_render_template_with_queries(self) -> None:
        """Render template with SPARQL query results."""
        query = QueryDescriptor(
            name="users",
            purpose="Fetch users",
            source=QuerySource.INLINE,
            content="SELECT ?name WHERE { ?s rdfs:label ?name }",
        )

        template = TemplateDescriptor(
            id="http://example.org/userlist",
            engine="jinja2",
            language="markdown",
            framework="",
            version="1.0.0",
            ontology=OntologyConfig(graph_id="main"),
            queries=(query,),
            n3_rules=(),
            metadata=TemplateMetadata(),
            template_path="users.j2",
            raw_content="{% for u in sparql.users %}* {{ u.name }}\n{% endfor %}",
        )

        registry = MockTemplateRegistry({"userlist": template})
        clients: dict[str, GraphClient] = {
            "main": MockGraphClient("main", {"label ?name": [{"name": "Alice"}, {"name": "Bob"}]})
        }
        engine = ProjectionEngine(registry, clients)

        result = engine.render("userlist")

        assert "* Alice" in result.content
        assert "* Bob" in result.content

    def test_render_template_with_params(self) -> None:
        """Render template using user-provided parameters."""
        template = TemplateDescriptor(
            id="http://example.org/config",
            engine="jinja2",
            language="yaml",
            framework="",
            version="1.0.0",
            ontology=OntologyConfig(graph_id="main"),
            queries=(),
            n3_rules=(),
            metadata=TemplateMetadata(),
            template_path="config.j2",
            raw_content="app_name: {{ params.app_name }}\nversion: {{ params.version }}",
        )

        registry = MockTemplateRegistry({"config": template})
        clients: dict[str, GraphClient] = {"main": MockGraphClient("main", {})}
        engine = ProjectionEngine(registry, clients)

        result = engine.render("config", {"app_name": "MyApp", "version": "2.0.0"})

        assert "app_name: MyApp" in result.content
        assert "version: 2.0.0" in result.content

    def test_render_template_not_found(self) -> None:
        """Fail when template not found in registry."""
        registry = MockTemplateRegistry({})
        clients: dict[str, GraphClient] = {"main": MockGraphClient("main", {})}
        engine = ProjectionEngine(registry, clients)

        with pytest.raises(TemplateNotFoundError) as exc:
            engine.render("missing")

        assert exc.value.template_name == "missing"

    def test_render_graph_not_found(self) -> None:
        """Fail when required graph client not available."""
        template = TemplateDescriptor(
            id="http://example.org/test",
            engine="jinja2",
            language="text",
            framework="",
            version="1.0.0",
            ontology=OntologyConfig(graph_id="secondary"),
            queries=(),
            n3_rules=(),
            metadata=TemplateMetadata(),
            template_path="test.j2",
            raw_content="test",
        )

        registry = MockTemplateRegistry({"test": template})
        clients: dict[str, GraphClient] = {"main": MockGraphClient("main", {})}
        engine = ProjectionEngine(registry, clients)

        with pytest.raises(GraphNotFoundError) as exc:
            engine.render("test")

        assert exc.value.graph_id == "secondary"

    def test_render_template_parse_error(self) -> None:
        """Fail when template has invalid Jinja syntax."""
        template = TemplateDescriptor(
            id="http://example.org/invalid",
            engine="jinja2",
            language="text",
            framework="",
            version="1.0.0",
            ontology=OntologyConfig(graph_id="main"),
            queries=(),
            n3_rules=(),
            metadata=TemplateMetadata(),
            template_path="invalid.j2",
            raw_content="{% for item in items %}{{ item.name }",  # Missing {% endfor %}
        )

        registry = MockTemplateRegistry({"invalid": template})
        clients: dict[str, GraphClient] = {"main": MockGraphClient("main", {})}
        engine = ProjectionEngine(registry, clients)

        with pytest.raises(TemplateRenderError) as exc:
            engine.render("invalid")

        assert "Failed to parse template" in str(exc.value)

    def test_render_template_render_error(self) -> None:
        """Fail when template rendering raises exception."""
        template = TemplateDescriptor(
            id="http://example.org/error",
            engine="jinja2",
            language="text",
            framework="",
            version="1.0.0",
            ontology=OntologyConfig(graph_id="main"),
            queries=(),
            n3_rules=(),
            metadata=TemplateMetadata(),
            template_path="error.j2",
            raw_content="{{ undefined_var }}",
        )

        registry = MockTemplateRegistry({"error": template})
        clients: dict[str, GraphClient] = {"main": MockGraphClient("main", {})}
        # Use strict mode (default)
        engine = ProjectionEngine(registry, clients)

        with pytest.raises(TemplateRenderError) as exc:
            engine.render("error")

        assert "Rendering failed" in str(exc.value)

    def test_render_result_metadata(self) -> None:
        """Verify result contains rendering metadata."""
        template = TemplateDescriptor(
            id="http://example.org/test",
            engine="jinja2",
            language="python",
            framework="",
            version="1.0.0",
            ontology=OntologyConfig(graph_id="main"),
            queries=(
                QueryDescriptor("q1", "Query 1", QuerySource.INLINE, "SELECT ?s"),
                QueryDescriptor("q2", "Query 2", QuerySource.INLINE, "SELECT ?p"),
            ),
            n3_rules=(),
            metadata=TemplateMetadata(),
            template_path="test.j2",
            raw_content="# test",
        )

        registry = MockTemplateRegistry({"test": template})
        clients: dict[str, GraphClient] = {"main": MockGraphClient("main", {})}
        engine = ProjectionEngine(registry, clients)

        result = engine.render("test")

        assert result.query_count == 2
        assert result.render_time_ms > 0
        assert result.context_info["graph_id"] == "main"

    def test_render_to_file(self) -> None:
        """Render template and write to file."""
        template = TemplateDescriptor(
            id="http://example.org/code",
            engine="jinja2",
            language="python",
            framework="",
            version="1.0.0",
            ontology=OntologyConfig(graph_id="main"),
            queries=(),
            n3_rules=(),
            metadata=TemplateMetadata(),
            template_path="code.j2",
            raw_content="# {{ params.title }}\nprint('Hello')",
        )

        registry = MockTemplateRegistry({"code": template})
        clients: dict[str, GraphClient] = {"main": MockGraphClient("main", {})}
        engine = ProjectionEngine(registry, clients)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.py"

            result = engine.render_to_file("code", output_path, {"title": "Test Script"})

            assert output_path.exists()
            content = output_path.read_text()
            assert "# Test Script" in content
            assert "print('Hello')" in content
            assert result.content == content

    def test_render_to_file_creates_parent_dirs(self) -> None:
        """Render to file creates parent directories if needed."""
        template = TemplateDescriptor(
            id="http://example.org/test",
            engine="jinja2",
            language="text",
            framework="",
            version="1.0.0",
            ontology=OntologyConfig(graph_id="main"),
            queries=(),
            n3_rules=(),
            metadata=TemplateMetadata(),
            template_path="test.j2",
            raw_content="test content",
        )

        registry = MockTemplateRegistry({"test": template})
        clients: dict[str, GraphClient] = {"main": MockGraphClient("main", {})}
        engine = ProjectionEngine(registry, clients)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "deep" / "output.txt"

            engine.render_to_file("test", output_path)

            assert output_path.exists()
            assert output_path.read_text() == "test content"

    def test_infer_media_type_python(self) -> None:
        """Infer media type for Python language."""
        registry = MockTemplateRegistry({})
        clients: dict[str, GraphClient] = {}
        engine = ProjectionEngine(registry, clients)

        media_type = engine._infer_media_type("python")

        assert media_type == "text/x-python"

    def test_infer_media_type_typescript(self) -> None:
        """Infer media type for TypeScript language."""
        registry = MockTemplateRegistry({})
        clients: dict[str, GraphClient] = {}
        engine = ProjectionEngine(registry, clients)

        media_type = engine._infer_media_type("typescript")

        assert media_type == "text/typescript"

    def test_infer_media_type_unknown(self) -> None:
        """Return None for unknown language."""
        registry = MockTemplateRegistry({})
        clients: dict[str, GraphClient] = {}
        engine = ProjectionEngine(registry, clients)

        media_type = engine._infer_media_type("unknown")

        assert media_type is None

    def test_infer_media_type_case_insensitive(self) -> None:
        """Infer media type is case insensitive."""
        registry = MockTemplateRegistry({})
        clients: dict[str, GraphClient] = {}
        engine = ProjectionEngine(registry, clients)

        assert engine._infer_media_type("PYTHON") == "text/x-python"
        assert engine._infer_media_type("JavaScript") == "text/javascript"

    def test_config_default_values(self) -> None:
        """Verify ProjectionConfig default values."""
        config = ProjectionConfig()

        assert config.cache_ttl == 300
        assert config.strict_mode is True

    def test_multiple_graph_clients(self) -> None:
        """Support multiple graph clients for different ontologies."""
        template = TemplateDescriptor(
            id="http://example.org/test",
            engine="jinja2",
            language="text",
            framework="",
            version="1.0.0",
            ontology=OntologyConfig(graph_id="secondary"),
            queries=(),
            n3_rules=(),
            metadata=TemplateMetadata(),
            template_path="test.j2",
            raw_content="test",
        )

        registry = MockTemplateRegistry({"test": template})
        clients: dict[str, GraphClient] = {
            "main": MockGraphClient("main", {}),
            "secondary": MockGraphClient("secondary", {}),
        }
        engine = ProjectionEngine(registry, clients)

        result = engine.render("test")

        assert result.context_info["graph_id"] == "secondary"
