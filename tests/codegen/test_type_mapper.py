"""Tests for type mapper."""

from __future__ import annotations

import pytest
from scripts.codegen.type_mapper import TypeMapper


class TestTypeMapper:
    """Test Java to Python type mapping."""

    @pytest.fixture
    def mapper(self) -> TypeMapper:
        """Create mapper instance.

        Returns
        -------
        TypeMapper
            Type mapper instance
        """
        return TypeMapper()

    def test_primitive_types(self, mapper: TypeMapper) -> None:
        """Test primitive type mapping.

        Parameters
        ----------
        mapper : TypeMapper
            Type mapper instance
        """
        # Arrange & Act & Assert
        assert mapper.map_type("int") == "int"
        assert mapper.map_type("long") == "int"
        assert mapper.map_type("float") == "float"
        assert mapper.map_type("double") == "float"
        assert mapper.map_type("boolean") == "bool"
        assert mapper.map_type("char") == "str"
        assert mapper.map_type("void") == "None"

    def test_boxed_types(self, mapper: TypeMapper) -> None:
        """Test boxed primitive type mapping.

        Parameters
        ----------
        mapper : TypeMapper
            Type mapper instance
        """
        # Arrange & Act & Assert
        assert mapper.map_type("Integer") == "int"
        assert mapper.map_type("Long") == "int"
        assert mapper.map_type("Float") == "float"
        assert mapper.map_type("Double") == "float"
        assert mapper.map_type("Boolean") == "bool"
        assert mapper.map_type("Character") == "str"

    def test_common_types(self, mapper: TypeMapper) -> None:
        """Test common type mapping.

        Parameters
        ----------
        mapper : TypeMapper
            Type mapper instance
        """
        # Arrange & Act & Assert
        assert mapper.map_type("String") == "str"
        assert mapper.map_type("Object") == "Any"
        assert mapper.map_type("Date") == "datetime"
        assert mapper.map_type("UUID") == "str"

    def test_simple_generics(self, mapper: TypeMapper) -> None:
        """Test simple generic type mapping.

        Parameters
        ----------
        mapper : TypeMapper
            Type mapper instance
        """
        # Arrange & Act & Assert
        assert mapper.map_type("List<String>") == "list[str]"
        assert mapper.map_type("Set<Integer>") == "set[int]"
        assert mapper.map_type("Map<String, Object>") == "dict[str, Any]"

    def test_nested_generics(self, mapper: TypeMapper) -> None:
        """Test nested generic type mapping.

        Parameters
        ----------
        mapper : TypeMapper
            Type mapper instance
        """
        # Arrange & Act & Assert
        assert mapper.map_type("List<List<String>>") == "list[list[str]]"
        assert mapper.map_type("Map<String, List<Integer>>") == "dict[str, list[int]]"
        assert mapper.map_type("Map<String, Map<String, Object>>") == "dict[str, dict[str, Any]]"

    def test_array_types(self, mapper: TypeMapper) -> None:
        """Test array type mapping.

        Parameters
        ----------
        mapper : TypeMapper
            Type mapper instance
        """
        # Arrange & Act & Assert
        assert mapper.map_type("String[]") == "list[str]"
        assert mapper.map_type("int[]") == "list[int]"
        assert mapper.map_type("Object[]") == "list[Any]"

    def test_collection_types(self, mapper: TypeMapper) -> None:
        """Test collection type mapping.

        Parameters
        ----------
        mapper : TypeMapper
            Type mapper instance
        """
        # Arrange & Act & Assert
        assert mapper.map_type("ArrayList<String>") == "list[str]"
        assert mapper.map_type("HashSet<Integer>") == "set[int]"
        assert mapper.map_type("HashMap<String, Object>") == "dict[str, Any]"
        assert mapper.map_type("LinkedList<String>") == "list[str]"

    def test_unknown_types(self, mapper: TypeMapper) -> None:
        """Test unknown type mapping defaults to Any.

        Parameters
        ----------
        mapper : TypeMapper
            Type mapper instance
        """
        # Arrange & Act & Assert
        assert mapper.map_type("UnknownType") == "Any"
        assert mapper.map_type("com.custom.CustomClass") == "Any"

    def test_custom_mapping(self, mapper: TypeMapper) -> None:
        """Test adding custom type mappings.

        Parameters
        ----------
        mapper : TypeMapper
            Type mapper instance
        """
        # Arrange
        mapper.add_custom_mapping("CustomType", "MyPythonType")

        # Act
        result = mapper.map_type("CustomType")

        # Assert
        assert result == "MyPythonType"

    def test_yawl_specific_types(self, mapper: TypeMapper) -> None:
        """Test YAWL-specific type mapping.

        Parameters
        ----------
        mapper : TypeMapper
            Type mapper instance
        """
        # Arrange & Act & Assert
        assert mapper.map_type("YSpecificationID") == "str"
        assert mapper.map_type("YTask") == "dict[str, Any]"
        assert mapper.map_type("YNet") == "dict[str, Any]"
        assert mapper.map_type("Element") == "Any"  # XML Element

    def test_complex_generic_parsing(self, mapper: TypeMapper) -> None:
        """Test complex generic type parsing with multiple arguments.

        Parameters
        ----------
        mapper : TypeMapper
            Type mapper instance
        """
        # Arrange & Act
        result = mapper.map_type("Map<String, List<Map<String, Integer>>>")

        # Assert
        assert result == "dict[str, list[dict[str, int]]]"
