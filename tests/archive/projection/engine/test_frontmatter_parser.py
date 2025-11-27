"""Tests for frontmatter parser.

Chicago School TDD: Test behavior, not implementation.
Tests verify correct parsing, validation, and descriptor building.
"""

from __future__ import annotations

import pytest

from kgcl.projection.domain.descriptors import (
    N3Role,
    OntologyConfig,
    QueryDescriptor,
    QuerySource,
    TemplateDescriptor,
    TemplateMetadata,
)
from kgcl.projection.domain.exceptions import FrontmatterParseError, FrontmatterValidationError
from kgcl.projection.engine.frontmatter_parser import (
    FRONTMATTER_DELIMITER,
    ParsedTemplate,
    build_template_descriptor,
    parse_template_file,
    validate_frontmatter,
)


class TestParseTemplateFile:
    """Test template file parsing behavior."""

    def test_parse_simple_frontmatter(self) -> None:
        """Parse template with minimal frontmatter."""
        content = """---
id: http://example.org/api
engine: jinja2
---
body content here"""

        result = parse_template_file(content)

        assert result.frontmatter["id"] == "http://example.org/api"
        assert result.frontmatter["engine"] == "jinja2"
        assert result.body == "body content here"

    def test_parse_complex_frontmatter(self) -> None:
        """Parse template with nested structures."""
        content = """---
id: http://example.org/api
engine: jinja2
language: python
framework: fastapi
version: 1.0.0
ontology:
  graph_id: main
  base_iri: http://example.org/
queries:
  - name: entities
    purpose: Fetch all entities
    inline: SELECT ?s WHERE { ?s a ex:Entity }
metadata:
  author: team
  tags:
    - api
    - rest
---
{% for e in sparql.entities %}
{{ e.s }}
{% endfor %}"""

        result = parse_template_file(content)

        assert result.frontmatter["id"] == "http://example.org/api"
        assert result.frontmatter["ontology"]["graph_id"] == "main"
        assert len(result.frontmatter["queries"]) == 1
        assert result.frontmatter["queries"][0]["name"] == "entities"
        assert "for e in sparql.entities" in result.body

    def test_parse_empty_frontmatter(self) -> None:
        """Parse template with empty frontmatter section."""
        content = """---
---
just body"""

        result = parse_template_file(content)

        assert result.frontmatter == {}
        assert result.body == "just body"

    def test_missing_opening_delimiter(self) -> None:
        """Fail when frontmatter opening delimiter missing."""
        content = "no frontmatter\nbody"

        with pytest.raises(FrontmatterParseError) as exc:
            parse_template_file(content)

        assert "must start with YAML frontmatter delimiter" in str(exc.value)

    def test_missing_closing_delimiter(self) -> None:
        """Fail when frontmatter closing delimiter missing."""
        content = """---
id: test
no closing delimiter"""

        with pytest.raises(FrontmatterParseError) as exc:
            parse_template_file(content)

        assert "closing delimiter" in str(exc.value)

    def test_invalid_yaml_syntax(self) -> None:
        """Fail when frontmatter has invalid YAML."""
        content = """---
id: test
invalid: [unclosed list
---
body"""

        with pytest.raises(FrontmatterParseError) as exc:
            parse_template_file(content)

        assert "Invalid YAML" in str(exc.value)

    def test_non_dict_frontmatter(self) -> None:
        """Fail when frontmatter is not a YAML mapping."""
        content = """---
- item1
- item2
---
body"""

        with pytest.raises(FrontmatterParseError) as exc:
            parse_template_file(content)

        assert "must be a YAML mapping" in str(exc.value)

    def test_multiline_body(self) -> None:
        """Parse template with multiline body content."""
        content = """---
id: test
---
line 1
line 2
line 3"""

        result = parse_template_file(content)

        assert result.body == "line 1\nline 2\nline 3"

    def test_delimiter_constant(self) -> None:
        """Verify delimiter constant value."""
        assert FRONTMATTER_DELIMITER == "---"


class TestValidateFrontmatter:
    """Test frontmatter validation behavior."""

    def test_valid_minimal_frontmatter(self) -> None:
        """Accept valid minimal frontmatter."""
        data = {
            "id": "http://example.org/api",
            "engine": "jinja2",
            "language": "python",
            "version": "1.0.0",
            "ontology": {"graph_id": "main"},
        }

        # Should not raise
        validate_frontmatter(data, "test.j2")

    def test_missing_required_field_id(self) -> None:
        """Fail when id field missing."""
        data = {"engine": "jinja2", "language": "python", "version": "1.0.0", "ontology": {"graph_id": "main"}}

        with pytest.raises(FrontmatterValidationError) as exc:
            validate_frontmatter(data, "test.j2")

        assert exc.value.field == "id"
        assert "required field missing" in str(exc.value)

    def test_missing_required_field_engine(self) -> None:
        """Fail when engine field missing."""
        data = {
            "id": "http://example.org/api",
            "language": "python",
            "version": "1.0.0",
            "ontology": {"graph_id": "main"},
        }

        with pytest.raises(FrontmatterValidationError) as exc:
            validate_frontmatter(data, "test.j2")

        assert exc.value.field == "engine"

    def test_empty_required_field(self) -> None:
        """Fail when required field is empty."""
        data = {
            "id": "",
            "engine": "jinja2",
            "language": "python",
            "version": "1.0.0",
            "ontology": {"graph_id": "main"},
        }

        with pytest.raises(FrontmatterValidationError) as exc:
            validate_frontmatter(data, "test.j2")

        assert exc.value.field == "id"
        assert "cannot be empty" in str(exc.value)

    def test_ontology_not_dict(self) -> None:
        """Fail when ontology is not a mapping."""
        data = {
            "id": "http://example.org/api",
            "engine": "jinja2",
            "language": "python",
            "version": "1.0.0",
            "ontology": "invalid",
        }

        with pytest.raises(FrontmatterValidationError) as exc:
            validate_frontmatter(data, "test.j2")

        assert exc.value.field == "ontology"
        assert "must be a mapping" in str(exc.value)

    def test_ontology_missing_graph_id(self) -> None:
        """Fail when ontology.graph_id missing."""
        data = {
            "id": "http://example.org/api",
            "engine": "jinja2",
            "language": "python",
            "version": "1.0.0",
            "ontology": {"base_iri": "http://example.org/"},
        }

        with pytest.raises(FrontmatterValidationError) as exc:
            validate_frontmatter(data, "test.j2")

        assert exc.value.field == "ontology"
        assert "graph_id is required" in str(exc.value)

    def test_queries_not_list(self) -> None:
        """Fail when queries is not a list."""
        data = {
            "id": "http://example.org/api",
            "engine": "jinja2",
            "language": "python",
            "version": "1.0.0",
            "ontology": {"graph_id": "main"},
            "queries": "invalid",
        }

        with pytest.raises(FrontmatterValidationError) as exc:
            validate_frontmatter(data, "test.j2")

        assert exc.value.field == "queries"
        assert "must be a list" in str(exc.value)

    def test_n3_rules_not_list(self) -> None:
        """Fail when n3_rules is not a list."""
        data = {
            "id": "http://example.org/api",
            "engine": "jinja2",
            "language": "python",
            "version": "1.0.0",
            "ontology": {"graph_id": "main"},
            "n3_rules": "invalid",
        }

        with pytest.raises(FrontmatterValidationError) as exc:
            validate_frontmatter(data, "test.j2")

        assert exc.value.field == "n3_rules"
        assert "must be a list" in str(exc.value)

    def test_valid_with_optional_fields(self) -> None:
        """Accept frontmatter with all optional fields."""
        data = {
            "id": "http://example.org/api",
            "engine": "jinja2",
            "language": "python",
            "framework": "fastapi",
            "version": "1.0.0",
            "ontology": {"graph_id": "main", "base_iri": "http://example.org/"},
            "queries": [],
            "n3_rules": [],
            "metadata": {"author": "team"},
        }

        # Should not raise
        validate_frontmatter(data, "test.j2")


class TestBuildTemplateDescriptor:
    """Test template descriptor building behavior."""

    def test_build_minimal_descriptor(self) -> None:
        """Build descriptor from minimal frontmatter."""
        frontmatter = {
            "id": "http://example.org/api",
            "engine": "jinja2",
            "language": "python",
            "version": "1.0.0",
            "ontology": {"graph_id": "main"},
        }
        body = "template body"

        descriptor = build_template_descriptor(frontmatter, body, "test.j2")

        assert descriptor.id == "http://example.org/api"
        assert descriptor.engine == "jinja2"
        assert descriptor.language == "python"
        assert descriptor.framework == ""
        assert descriptor.version == "1.0.0"
        assert descriptor.ontology.graph_id == "main"
        assert descriptor.ontology.base_iri == ""
        assert descriptor.queries == ()
        assert descriptor.n3_rules == ()
        assert descriptor.template_path == "test.j2"
        assert descriptor.raw_content == "template body"

    def test_build_with_framework(self) -> None:
        """Build descriptor with framework specified."""
        frontmatter = {
            "id": "http://example.org/api",
            "engine": "jinja2",
            "language": "python",
            "framework": "fastapi",
            "version": "1.0.0",
            "ontology": {"graph_id": "main"},
        }

        descriptor = build_template_descriptor(frontmatter, "", "test.j2")

        assert descriptor.framework == "fastapi"

    def test_build_with_ontology_base_iri(self) -> None:
        """Build descriptor with ontology base IRI."""
        frontmatter = {
            "id": "http://example.org/api",
            "engine": "jinja2",
            "language": "python",
            "version": "1.0.0",
            "ontology": {"graph_id": "main", "base_iri": "http://example.org/ontology/"},
        }

        descriptor = build_template_descriptor(frontmatter, "", "test.j2")

        assert descriptor.ontology.base_iri == "http://example.org/ontology/"

    def test_build_with_inline_queries(self) -> None:
        """Build descriptor with inline SPARQL queries."""
        frontmatter = {
            "id": "http://example.org/api",
            "engine": "jinja2",
            "language": "python",
            "version": "1.0.0",
            "ontology": {"graph_id": "main"},
            "queries": [
                {"name": "entities", "purpose": "Fetch all entities", "inline": "SELECT ?s WHERE { ?s a ex:Entity }"},
                {
                    "name": "count",
                    "purpose": "Count entities",
                    "inline": "SELECT (COUNT(?s) AS ?count) WHERE { ?s a ex:Entity }",
                },
            ],
        }

        descriptor = build_template_descriptor(frontmatter, "", "test.j2")

        assert len(descriptor.queries) == 2
        assert descriptor.queries[0].name == "entities"
        assert descriptor.queries[0].source == QuerySource.INLINE
        assert "SELECT ?s" in descriptor.queries[0].content
        assert descriptor.queries[1].name == "count"

    def test_build_with_file_queries_and_loader(self) -> None:
        """Build descriptor with external query files."""

        def mock_loader(path: str) -> str:
            if path == "queries/entities.rq":
                return "SELECT ?s WHERE { ?s a ex:Entity }"
            return ""

        frontmatter = {
            "id": "http://example.org/api",
            "engine": "jinja2",
            "language": "python",
            "version": "1.0.0",
            "ontology": {"graph_id": "main"},
            "queries": [{"name": "entities", "purpose": "Fetch all entities", "file": "queries/entities.rq"}],
        }

        descriptor = build_template_descriptor(frontmatter, "", "test.j2", mock_loader)

        assert len(descriptor.queries) == 1
        assert descriptor.queries[0].name == "entities"
        assert descriptor.queries[0].source == QuerySource.FILE
        assert descriptor.queries[0].file_path == "queries/entities.rq"
        assert "SELECT ?s" in descriptor.queries[0].content

    def test_build_file_query_without_loader(self) -> None:
        """Fail when file query declared but no loader provided."""
        frontmatter = {
            "id": "http://example.org/api",
            "engine": "jinja2",
            "language": "python",
            "version": "1.0.0",
            "ontology": {"graph_id": "main"},
            "queries": [{"name": "entities", "purpose": "Fetch all entities", "file": "queries/entities.rq"}],
        }

        with pytest.raises(FrontmatterValidationError) as exc:
            build_template_descriptor(frontmatter, "", "test.j2", None)

        assert exc.value.field == "queries"
        assert "no query_loader provided" in str(exc.value)

    def test_build_file_query_loader_fails(self) -> None:
        """Fail when query file loader raises exception."""

        def failing_loader(path: str) -> str:
            raise FileNotFoundError(f"File not found: {path}")

        frontmatter = {
            "id": "http://example.org/api",
            "engine": "jinja2",
            "language": "python",
            "version": "1.0.0",
            "ontology": {"graph_id": "main"},
            "queries": [{"name": "entities", "purpose": "Fetch all entities", "file": "queries/entities.rq"}],
        }

        with pytest.raises(FrontmatterValidationError) as exc:
            build_template_descriptor(frontmatter, "", "test.j2", failing_loader)

        assert exc.value.field == "queries"
        assert "Failed to load query file" in str(exc.value)

    def test_build_with_n3_rules(self) -> None:
        """Build descriptor with N3 rule declarations."""
        frontmatter = {
            "id": "http://example.org/api",
            "engine": "jinja2",
            "language": "python",
            "version": "1.0.0",
            "ontology": {"graph_id": "main"},
            "n3_rules": [
                {"name": "validation", "file": "rules/validate.n3", "role": "precondition"},
                {"name": "inference", "file": "rules/infer.n3", "role": "inference"},
            ],
        }

        descriptor = build_template_descriptor(frontmatter, "", "test.j2")

        assert len(descriptor.n3_rules) == 2
        assert descriptor.n3_rules[0].name == "validation"
        assert descriptor.n3_rules[0].role == N3Role.PRECONDITION
        assert descriptor.n3_rules[1].name == "inference"
        assert descriptor.n3_rules[1].role == N3Role.INFERENCE

    def test_build_with_metadata(self) -> None:
        """Build descriptor with metadata section."""
        frontmatter = {
            "id": "http://example.org/api",
            "engine": "jinja2",
            "language": "python",
            "version": "1.0.0",
            "ontology": {"graph_id": "main"},
            "metadata": {"author": "team", "description": "REST API template", "tags": ["api", "rest", "fastapi"]},
        }

        descriptor = build_template_descriptor(frontmatter, "", "test.j2")

        assert descriptor.metadata.author == "team"
        assert descriptor.metadata.description == "REST API template"
        assert descriptor.metadata.tags == ("api", "rest", "fastapi")

    def test_build_with_empty_metadata(self) -> None:
        """Build descriptor with empty metadata section."""
        frontmatter = {
            "id": "http://example.org/api",
            "engine": "jinja2",
            "language": "python",
            "version": "1.0.0",
            "ontology": {"graph_id": "main"},
            "metadata": {},
        }

        descriptor = build_template_descriptor(frontmatter, "", "test.j2")

        assert descriptor.metadata.author == ""
        assert descriptor.metadata.description == ""
        assert descriptor.metadata.tags == ()

    def test_parsed_template_frozen(self) -> None:
        """Verify ParsedTemplate is immutable."""
        pt = ParsedTemplate(frontmatter={"id": "test"}, body="content")

        with pytest.raises(AttributeError):
            pt.body = "changed"  # type: ignore[misc]
