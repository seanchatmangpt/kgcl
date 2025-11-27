"""Tests for type mapping filters."""

import pytest

from kgcl.projection.filters.type_mapping import (
    cardinality_to_python,
    cardinality_to_typescript,
    to_python_class,
    to_typescript_interface,
    xsd_to_openapi,
    xsd_to_python,
    xsd_to_typescript,
)


class TestXSDToPython:
    """Test XSD to Python type conversion."""

    def test_string_types(self) -> None:
        """Convert string types."""
        assert xsd_to_python("xsd:string") == "str"
        assert xsd_to_python("xsd:anyURI") == "str"

    def test_numeric_types(self) -> None:
        """Convert numeric types."""
        assert xsd_to_python("xsd:integer") == "int"
        assert xsd_to_python("xsd:int") == "int"
        assert xsd_to_python("xsd:long") == "int"
        assert xsd_to_python("xsd:decimal") == "float"
        assert xsd_to_python("xsd:float") == "float"
        assert xsd_to_python("xsd:double") == "float"

    def test_boolean_type(self) -> None:
        """Convert boolean type."""
        assert xsd_to_python("xsd:boolean") == "bool"

    def test_temporal_types(self) -> None:
        """Convert temporal types."""
        assert xsd_to_python("xsd:dateTime") == "datetime"
        assert xsd_to_python("xsd:date") == "date"
        assert xsd_to_python("xsd:time") == "time"
        assert xsd_to_python("xsd:duration") == "timedelta"

    def test_binary_types(self) -> None:
        """Convert binary types."""
        assert xsd_to_python("xsd:base64Binary") == "bytes"
        assert xsd_to_python("xsd:hexBinary") == "bytes"

    def test_unknown_type(self) -> None:
        """Handle unknown types."""
        assert xsd_to_python("xsd:unknown") == "Any"
        assert xsd_to_python("custom:type") == "Any"


class TestXSDToTypeScript:
    """Test XSD to TypeScript type conversion."""

    def test_string_types(self) -> None:
        """Convert string types."""
        assert xsd_to_typescript("xsd:string") == "string"
        assert xsd_to_typescript("xsd:anyURI") == "string"

    def test_numeric_types(self) -> None:
        """Convert numeric types."""
        assert xsd_to_typescript("xsd:integer") == "number"
        assert xsd_to_typescript("xsd:int") == "number"
        assert xsd_to_typescript("xsd:decimal") == "number"
        assert xsd_to_typescript("xsd:float") == "number"

    def test_boolean_type(self) -> None:
        """Convert boolean type."""
        assert xsd_to_typescript("xsd:boolean") == "boolean"

    def test_temporal_types(self) -> None:
        """Convert temporal types."""
        assert xsd_to_typescript("xsd:dateTime") == "Date"
        assert xsd_to_typescript("xsd:date") == "Date"
        assert xsd_to_typescript("xsd:time") == "string"

    def test_unknown_type(self) -> None:
        """Handle unknown types."""
        assert xsd_to_typescript("xsd:unknown") == "any"
        assert xsd_to_typescript("custom:type") == "any"


class TestXSDToOpenAPI:
    """Test XSD to OpenAPI schema conversion."""

    def test_string_type(self) -> None:
        """Convert string type."""
        assert xsd_to_openapi("xsd:string") == {"type": "string"}

    def test_integer_types(self) -> None:
        """Convert integer types with formats."""
        assert xsd_to_openapi("xsd:integer") == {"type": "integer"}
        assert xsd_to_openapi("xsd:int") == {"type": "integer", "format": "int32"}
        assert xsd_to_openapi("xsd:long") == {"type": "integer", "format": "int64"}

    def test_number_types(self) -> None:
        """Convert number types with formats."""
        assert xsd_to_openapi("xsd:decimal") == {"type": "number"}
        assert xsd_to_openapi("xsd:float") == {"type": "number", "format": "float"}
        assert xsd_to_openapi("xsd:double") == {"type": "number", "format": "double"}

    def test_boolean_type(self) -> None:
        """Convert boolean type."""
        assert xsd_to_openapi("xsd:boolean") == {"type": "boolean"}

    def test_temporal_types(self) -> None:
        """Convert temporal types with formats."""
        assert xsd_to_openapi("xsd:dateTime") == {"type": "string", "format": "date-time"}
        assert xsd_to_openapi("xsd:date") == {"type": "string", "format": "date"}
        assert xsd_to_openapi("xsd:time") == {"type": "string", "format": "time"}

    def test_uri_type(self) -> None:
        """Convert URI type."""
        assert xsd_to_openapi("xsd:anyURI") == {"type": "string", "format": "uri"}

    def test_binary_types(self) -> None:
        """Convert binary types."""
        assert xsd_to_openapi("xsd:base64Binary") == {"type": "string", "format": "byte"}
        assert xsd_to_openapi("xsd:hexBinary") == {"type": "string"}

    def test_unknown_type(self) -> None:
        """Handle unknown types."""
        assert xsd_to_openapi("xsd:unknown") == {"type": "string"}


class TestNamingConventions:
    """Test naming convention conversions."""

    def test_to_python_class_simple(self) -> None:
        """Convert simple names to Python class names."""
        assert to_python_class("entity") == "Entity"
        assert to_python_class("person") == "Person"

    def test_to_python_class_snake_case(self) -> None:
        """Convert snake_case to PascalCase."""
        assert to_python_class("user_profile") == "UserProfile"
        assert to_python_class("http_client") == "HttpClient"

    def test_to_python_class_kebab_case(self) -> None:
        """Convert kebab-case to PascalCase."""
        assert to_python_class("http-client") == "HttpClient"
        assert to_python_class("user-profile") == "UserProfile"

    def test_to_python_class_spaces(self) -> None:
        """Convert spaced words to PascalCase."""
        assert to_python_class("User Profile") == "UserProfile"
        assert to_python_class("HTTP Client") == "HttpClient"

    def test_to_typescript_interface_simple(self) -> None:
        """Convert simple names to TypeScript interface names."""
        assert to_typescript_interface("entity") == "IEntity"
        assert to_typescript_interface("person") == "IPerson"

    def test_to_typescript_interface_compound(self) -> None:
        """Convert compound names to TypeScript interface names."""
        assert to_typescript_interface("user_profile") == "IUserProfile"
        assert to_typescript_interface("http-client") == "IHttpClient"


class TestCardinality:
    """Test cardinality to type annotation conversion."""

    def test_cardinality_to_python_optional(self) -> None:
        """Convert 0..1 cardinality to Optional."""
        assert cardinality_to_python(0, 1) == "Optional[X]"

    def test_cardinality_to_python_required(self) -> None:
        """Convert 1..1 cardinality to required type."""
        assert cardinality_to_python(1, 1) == "X"

    def test_cardinality_to_python_list_unbounded(self) -> None:
        """Convert 0..* cardinality to list."""
        assert cardinality_to_python(0, None) == "list[X]"
        assert cardinality_to_python(1, None) == "list[X]"

    def test_cardinality_to_python_list_bounded(self) -> None:
        """Convert 0..N cardinality to list."""
        assert cardinality_to_python(0, 5) == "list[X]"
        assert cardinality_to_python(1, 10) == "list[X]"

    def test_cardinality_to_typescript_nullable(self) -> None:
        """Convert 0..1 cardinality to nullable."""
        assert cardinality_to_typescript(0, 1) == "X | null"

    def test_cardinality_to_typescript_required(self) -> None:
        """Convert 1..1 cardinality to required type."""
        assert cardinality_to_typescript(1, 1) == "X"

    def test_cardinality_to_typescript_array_unbounded(self) -> None:
        """Convert 0..* cardinality to array."""
        assert cardinality_to_typescript(0, None) == "X[]"
        assert cardinality_to_typescript(1, None) == "X[]"

    def test_cardinality_to_typescript_array_bounded(self) -> None:
        """Convert 0..N cardinality to array."""
        assert cardinality_to_typescript(0, 5) == "X[]"
        assert cardinality_to_typescript(1, 10) == "X[]"


class TestCompleteTypeMapping:
    """Test complete type mapping scenarios."""

    def test_property_definition_python(self) -> None:
        """Map complete property definition to Python."""
        # Property: name, type: xsd:string, cardinality: 1..1
        py_type = xsd_to_python("xsd:string")
        cardinality = cardinality_to_python(1, 1)

        assert py_type == "str"
        assert cardinality == "X"
        # Complete: name: str

    def test_optional_property_python(self) -> None:
        """Map optional property to Python."""
        # Property: age, type: xsd:integer, cardinality: 0..1
        py_type = xsd_to_python("xsd:integer")
        cardinality = cardinality_to_python(0, 1)

        assert py_type == "int"
        assert cardinality == "Optional[X]"
        # Complete: age: Optional[int]

    def test_collection_property_python(self) -> None:
        """Map collection property to Python."""
        # Property: tags, type: xsd:string, cardinality: 0..*
        py_type = xsd_to_python("xsd:string")
        cardinality = cardinality_to_python(0, None)

        assert py_type == "str"
        assert cardinality == "list[X]"
        # Complete: tags: list[str]

    def test_class_name_conversion(self) -> None:
        """Map class names across languages."""
        class_name = "user_profile"

        py_class = to_python_class(class_name)
        ts_interface = to_typescript_interface(class_name)

        assert py_class == "UserProfile"
        assert ts_interface == "IUserProfile"


class TestFilterExports:
    """Test TYPE_MAPPING_FILTERS export."""

    def test_all_filters_exported(self) -> None:
        """Verify all filters are in TYPE_MAPPING_FILTERS dict."""
        from kgcl.projection.filters.type_mapping import TYPE_MAPPING_FILTERS

        expected_filters = {
            "xsd_to_python",
            "xsd_to_typescript",
            "xsd_to_openapi",
            "to_python_class",
            "to_typescript_interface",
            "cardinality_to_python",
            "cardinality_to_typescript",
        }
        assert set(TYPE_MAPPING_FILTERS.keys()) == expected_filters

    def test_filters_are_callable(self) -> None:
        """Verify all exported filters are callable."""
        from kgcl.projection.filters.type_mapping import TYPE_MAPPING_FILTERS

        for name, func in TYPE_MAPPING_FILTERS.items():
            assert callable(func), f"Filter {name} is not callable"
