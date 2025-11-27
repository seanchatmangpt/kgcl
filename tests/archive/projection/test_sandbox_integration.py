"""Integration tests for sandbox with realistic RDF projection scenarios."""

from __future__ import annotations

import pytest
from jinja2.exceptions import SecurityError

from kgcl.projection.sandbox import create_projection_environment


class TestRDFProjectionIntegration:
    """Test sandboxed environment with realistic RDF projection scenarios."""

    def test_ontology_class_projection(self) -> None:
        """Test projecting an ontology class to Python code."""
        env = create_projection_environment()

        template_str = """
class {{ class_uri | uri_local_name }}:
    \"\"\"{{ description }}.\"\"\"

    def __init__(self, uri: str) -> None:
        self.uri = uri
        self.type = "{{ class_uri }}"
"""

        template = env.from_string(template_str)
        result = template.render(
            class_uri="http://example.org/ontology#Person", description="Represents a person entity"
        )

        assert "class Person:" in result
        assert 'self.type = "http://example.org/ontology#Person"' in result

    def test_property_projection_with_type_mapping(self) -> None:
        """Test projecting RDF properties to typed Python attributes."""
        env = create_projection_environment()

        template_str = """
@dataclass
class {{ class_name }}:
    {% for prop in properties %}
    {{ prop.name }}: {{ prop.type | xsd_to_python }}  # {{ prop.uri | uri_local_name }}
    {% endfor %}
"""

        template = env.from_string(template_str)
        result = template.render(
            class_name="Person",
            properties=[
                {"name": "name", "type": "xsd:string", "uri": "http://example.org/ontology#hasName"},
                {"name": "age", "type": "xsd:integer", "uri": "http://example.org/ontology#hasAge"},
            ],
        )

        assert "name: str" in result
        assert "age: int" in result

    def test_typescript_interface_projection(self) -> None:
        """Test projecting RDF class to TypeScript interface."""
        env = create_projection_environment()

        template_str = """
interface {{ class_uri | uri_local_name }} {
  {% for prop in properties %}
  {{ prop.name }}: {{ prop.type | xsd_to_typescript }};
  {% endfor %}
}
"""

        template = env.from_string(template_str)
        result = template.render(
            class_uri="http://example.org/ontology#Person",
            properties=[
                {"name": "name", "type": "xsd:string"},
                {"name": "age", "type": "xsd:integer"},
                {"name": "active", "type": "xsd:boolean"},
            ],
        )

        assert "interface Person {" in result
        assert "name: string;" in result
        assert "age: number;" in result
        assert "active: boolean;" in result

    def test_openapi_schema_projection(self) -> None:
        """Test projecting RDF schema to OpenAPI."""
        env = create_projection_environment()

        template_str = """
components:
  schemas:
    {% for schema in schemas %}
    {{ schema.name | pascal_case }}:
      type: object
      properties:
        {% for prop in schema.properties %}
        {{ prop.name }}:
          {% set openapi = prop.type | xsd_to_openapi %}
          type: {{ openapi.type }}
        {% endfor %}
    {% endfor %}
"""

        template = env.from_string(template_str)
        result = template.render(
            schemas=[
                {
                    "name": "person",
                    "properties": [{"name": "name", "type": "xsd:string"}, {"name": "age", "type": "xsd:integer"}],
                }
            ]
        )

        assert "Person:" in result
        assert "type: string" in result
        assert "type: integer" in result

    def test_namespace_prefix_handling(self) -> None:
        """Test handling multiple namespaces with prefixes."""
        env = create_projection_environment()

        template_str = """
Namespaces:
{% for ns in namespaces %}
- {{ ns.prefix }}: {{ ns.uri | uri_namespace }}
{% endfor %}

Classes:
{% for cls in classes %}
- {{ cls | uri_local_name }} ({{ cls | uri_namespace }})
{% endfor %}
"""

        template = env.from_string(template_str)
        result = template.render(
            namespaces=[
                {"prefix": "ex", "uri": "http://example.org/ontology#Thing"},
                {"prefix": "schema", "uri": "http://schema.org/Thing"},
            ],
            classes=["http://example.org/ontology#Person", "http://schema.org/Organization"],
        )

        assert "ex: http://example.org/ontology#" in result
        assert "schema: http://schema.org/" in result
        assert "Person (http://example.org/ontology#)" in result

    def test_sorting_and_grouping_results(self) -> None:
        """Test sorting and grouping SPARQL-like results."""
        env = create_projection_environment()

        template_str = """
{% set sorted_items = items | sort_by('name') %}
Results ({{ sorted_items | length }}):
{% for item in sorted_items %}
- {{ item.name }}: {{ item.uri | uri_local_name }}
{% endfor %}
"""

        template = env.from_string(template_str)
        result = template.render(
            items=[
                {"name": "zebra", "uri": "http://example.org/Z"},
                {"name": "apple", "uri": "http://example.org/A"},
                {"name": "cherry", "uri": "http://example.org/C"},
            ]
        )

        # Should be sorted
        assert "Results (3)" in result
        assert result.index("apple") < result.index("cherry")
        assert result.index("cherry") < result.index("zebra")

    def test_security_prevents_code_injection(self) -> None:
        """Test that sandbox prevents code injection attempts."""
        env = create_projection_environment()

        # Attempt to access __class__
        template = env.from_string("{{ class_uri.__class__ }}")
        with pytest.raises(SecurityError):
            template.render(class_uri="http://example.org/Thing")

        # Attempt to access __globals__
        def dummy() -> str:
            return "test"

        template = env.from_string("{{ func.__globals__ }}")
        with pytest.raises(SecurityError):
            template.render(func=dummy)

    def test_security_prevents_file_access(self) -> None:
        """Test that sandbox prevents file system access."""
        env = create_projection_environment()

        # open() should not be available
        template = env.from_string("{{ open('/etc/passwd') }}")
        with pytest.raises(Exception):  # UndefinedError
            template.render()

    def test_complex_nested_projection(self) -> None:
        """Test complex nested structure projection."""
        env = create_projection_environment()

        template_str = """
class {{ ontology.name | pascal_case }}:
    \"\"\"{{ ontology.description }}.\"\"\"

    CLASSES = {
        {% for cls in ontology.classes %}
        "{{ cls.uri | uri_local_name }}": {
            "uri": "{{ cls.uri }}",
            "properties": [
                {% for prop in cls.properties %}
                {
                    "name": "{{ prop.name }}",
                    "type": "{{ prop.range | xsd_to_python }}",
                },
                {% endfor %}
            ],
        },
        {% endfor %}
    }
"""

        template = env.from_string(template_str)
        result = template.render(
            ontology={
                "name": "person",
                "description": "Person ontology",
                "classes": [
                    {
                        "uri": "http://example.org/Person",
                        "properties": [
                            {"name": "name", "range": "xsd:string"},
                            {"name": "age", "range": "xsd:integer"},
                        ],
                    }
                ],
            }
        )

        assert "class Person:" in result
        assert '"Person": {' in result
        assert '"name": "name"' in result
        assert '"type": "str"' in result
        assert '"type": "int"' in result
