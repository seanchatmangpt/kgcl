"""Test YVariable methods implementation.

Validates all 50 newly implemented YVariable methods match Java YAWL signatures.
"""

from __future__ import annotations

import pytest

from kgcl.yawl.elements.y_decomposition import YDecomposition, YVariable


class TestYVariableGettersSetters:
    """Test basic getter/setter methods."""

    def test_get_set_default_value(self) -> None:
        """Test get_default_value and set_default_value."""
        var = YVariable(name="test", initial_value="original")
        assert var.get_default_value() == "original"
        assert var.get_initial_value() == "original"

        var.set_default_value("new_value")
        assert var.get_default_value() == "new_value"

        var2 = YVariable(name="test2")
        assert var2.get_default_value() == ""

    def test_get_set_initial_value(self) -> None:
        """Test get_initial_value and set_initial_value."""
        var = YVariable(name="test")
        assert var.get_initial_value() == ""

        var.set_initial_value("value123")
        assert var.get_initial_value() == "value123"

    def test_data_type_methods(self) -> None:
        """Test data type getter methods."""
        var = YVariable(name="test", data_type="xs:string", namespace="http://www.w3.org/2001/XMLSchema")

        assert var.get_data_type_name() == "xs:string"
        assert var.get_data_type_name_unprefixed() == "string"
        assert var.get_data_type_prefix() == "xs"
        assert var.get_data_type_name_space() == "http://www.w3.org/2001/XMLSchema"

    def test_data_type_no_prefix(self) -> None:
        """Test data type methods with no prefix."""
        var = YVariable(name="test", data_type="string")

        assert var.get_data_type_name() == "string"
        assert var.get_data_type_name_unprefixed() == "string"
        assert var.get_data_type_prefix() == ""

    def test_set_data_type_and_name(self) -> None:
        """Test set_data_type_and_name."""
        var = YVariable(name="old_name")

        var.set_data_type_and_name("xs:int", "new_name", "http://example.com")

        assert var.name == "new_name"
        assert var.data_type == "xs:int"
        assert var.namespace == "http://example.com"


class TestYVariableTypeChecks:
    """Test type-related boolean methods."""

    def test_is_empty_typed(self) -> None:
        """Test is_empty_typed."""
        var1 = YVariable(name="test", data_type="string")
        assert var1.is_empty_typed()  # Has type but no value

        var2 = YVariable(name="test", data_type="string", initial_value="value")
        assert not var2.is_empty_typed()  # Has both type and value

    def test_set_empty_typed(self) -> None:
        """Test set_empty_typed."""
        var = YVariable(name="test")
        var.set_empty_typed(True)
        assert var.is_empty_typed()

    def test_is_untyped(self) -> None:
        """Test is_untyped."""
        var1 = YVariable(name="test")
        assert not var1.is_untyped()  # Default is "string", which is typed

        var2 = YVariable(name="test", data_type="")
        assert var2.is_untyped()

        var3 = YVariable(name="test", data_type="anyType")
        assert var3.is_untyped()

    def test_set_untyped(self) -> None:
        """Test set_untyped."""
        var = YVariable(name="test", data_type="xs:string")
        var.set_untyped(True)
        assert var.is_untyped()

    def test_is_user_defined_type(self) -> None:
        """Test is_user_defined_type."""
        # Standard types
        for std_type in ["string", "int", "integer", "boolean", "decimal"]:
            var = YVariable(name="test", data_type=std_type)
            assert not var.is_user_defined_type(), f"{std_type} should be standard"

        # User-defined type
        var_custom = YVariable(name="test", data_type="MyCustomType")
        assert var_custom.is_user_defined_type()

        # Prefixed standard type
        var_prefixed = YVariable(name="test", data_type="xs:string")
        assert not var_prefixed.is_user_defined_type()


class TestYVariableNaming:
    """Test name-related methods."""

    def test_get_set_name(self) -> None:
        """Test get_name and set_name."""
        var = YVariable(name="original")
        assert var.get_name() == "original"

        var.set_name("new_name")
        assert var.get_name() == "new_name"

    def test_get_set_element_name(self) -> None:
        """Test get_element_name and set_element_name."""
        var = YVariable(name="var_name")
        assert var.get_element_name() == "var_name"  # Defaults to variable name

        var.set_element_name("element_name")
        assert var.get_element_name() == "element_name"

    def test_get_preferred_name(self) -> None:
        """Test get_preferred_name."""
        var = YVariable(name="var_name")
        assert var.get_preferred_name() == "var_name"

        var.set_element_name("element_name")
        assert var.get_preferred_name() == "element_name"


class TestYVariableDocumentation:
    """Test documentation methods."""

    def test_get_set_documentation(self) -> None:
        """Test get_documentation and set_documentation."""
        var = YVariable(name="test", documentation="Original docs")
        assert var.get_documentation() == "Original docs"

        var.set_documentation("Updated documentation")
        assert var.get_documentation() == "Updated documentation"


class TestYVariableOrdering:
    """Test ordering methods."""

    def test_get_set_ordering(self) -> None:
        """Test get_ordering and set_ordering."""
        var = YVariable(name="test")
        assert var.get_ordering() == 0

        var.set_ordering(5)
        assert var.get_ordering() == 5


class TestYVariableRequirements:
    """Test mandatory/optional/required methods."""

    def test_is_mandatory_set_mandatory(self) -> None:
        """Test is_mandatory and set_mandatory."""
        var = YVariable(name="test")
        assert var.is_mandatory()  # Default is True

        var.set_mandatory(False)
        assert not var.is_mandatory()

    def test_is_optional_set_optional(self) -> None:
        """Test is_optional and set_optional."""
        var = YVariable(name="test")
        assert not var.is_optional()  # Default is False

        var.set_optional(True)
        assert var.is_optional()

    def test_is_required(self) -> None:
        """Test is_required."""
        var = YVariable(name="test")
        var.set_mandatory(True)
        var.set_optional(False)
        assert var.is_required()

        var.set_optional(True)
        assert not var.is_required()  # Optional overrides mandatory

    def test_requires_input_value(self) -> None:
        """Test requires_input_value."""
        # Local variable - never requires input
        var_local = YVariable(name="test", scope="local")
        var_local.set_mandatory(True)
        assert not var_local.requires_input_value()

        # Input variable that is required
        var_input = YVariable(name="test", scope="input")
        var_input.set_mandatory(True)
        var_input.set_optional(False)
        assert var_input.requires_input_value()

        # Input variable that is optional
        var_input.set_optional(True)
        assert not var_input.requires_input_value()


class TestYVariableAttributes:
    """Test attribute management methods."""

    def test_get_set_attributes(self) -> None:
        """Test get_attributes and set_attributes."""
        var = YVariable(name="test")
        assert var.get_attributes() == {}

        attrs = {"key1": "value1", "key2": "value2"}
        var.set_attributes(attrs)
        assert var.get_attributes() == attrs

    def test_add_attribute(self) -> None:
        """Test add_attribute."""
        var = YVariable(name="test")

        var.add_attribute("key1", "value1")
        assert var.get_attributes() == {"key1": "value1"}

        var.add_attribute("key2", 123)
        assert var.get_attributes() == {"key1": "value1", "key2": 123}

    def test_has_attributes(self) -> None:
        """Test has_attributes."""
        var = YVariable(name="test")
        assert not var.has_attributes()

        var.add_attribute("key", "value")
        assert var.has_attributes()


class TestYVariableComparison:
    """Test comparison methods."""

    def test_compare_to(self) -> None:
        """Test compare_to."""
        var_a = YVariable(name="aaa")
        var_b = YVariable(name="bbb")
        var_c = YVariable(name="aaa")

        assert var_a.compare_to(var_b) < 0  # aaa < bbb
        assert var_b.compare_to(var_a) > 0  # bbb > aaa
        assert var_a.compare_to(var_c) == 0  # aaa == aaa


class TestYVariableStringRepresentation:
    """Test string representation methods."""

    def test_to_string(self) -> None:
        """Test to_string."""
        var = YVariable(name="myVar", data_type="xs:string", scope="input")
        result = var.to_string()

        assert "myVar" in result
        assert "xs:string" in result
        assert "input" in result

    def test_to_xml(self) -> None:
        """Test to_xml."""
        var1 = YVariable(name="myVar", data_type="string", initial_value="hello")
        xml1 = var1.to_xml()
        assert "<myVar" in xml1
        assert 'type="string"' in xml1
        assert "hello" in xml1

        var2 = YVariable(name="myVar", data_type="string")
        xml2 = var2.to_xml()
        assert "<myVar" in xml2
        assert "/>" in xml2  # Self-closing tag

    def test_to_xml_guts(self) -> None:
        """Test to_xml_guts."""
        var1 = YVariable(name="test", initial_value="content")
        assert var1.to_xml_guts() == "content"

        var2 = YVariable(name="test")
        assert var2.to_xml_guts() == ""


class TestYVariableDeclarations:
    """Test declaration type methods."""

    def test_uses_element_declaration(self) -> None:
        """Test uses_element_declaration."""
        var = YVariable(name="test")
        assert not var.uses_element_declaration()

        var.set_element_name("element")
        assert var.uses_element_declaration()

    def test_uses_type_declaration(self) -> None:
        """Test uses_type_declaration."""
        var = YVariable(name="test", data_type="string")
        assert var.uses_type_declaration()  # Has type, no element name

        var.set_element_name("element")
        assert not var.uses_type_declaration()  # Element declaration takes precedence


class TestYVariableValidation:
    """Test validation methods."""

    def test_is_valid_type_name_for_schema(self) -> None:
        """Test is_valid_type_name_for_schema."""
        var = YVariable(name="test")

        # Valid type names
        assert var.is_valid_type_name_for_schema("string")
        assert var.is_valid_type_name_for_schema("xs:string")
        assert var.is_valid_type_name_for_schema("MyCustomType")
        assert var.is_valid_type_name_for_schema("my-type.name")

        # Invalid type names
        assert not var.is_valid_type_name_for_schema("")
        assert not var.is_valid_type_name_for_schema("123type")  # Starts with digit

    def test_is_schema_version_at_least_2_1(self) -> None:
        """Test is_schema_version_at_least_2_1."""
        var = YVariable(name="test")
        assert var.is_schema_version_at_least_2_1()  # Always True in Python implementation


class TestYVariableClone:
    """Test clone method."""

    def test_clone(self) -> None:
        """Test clone creates deep copy."""
        original = YVariable(
            name="original",
            data_type="xs:string",
            scope="input",
            initial_value="value",
            documentation="docs",
            namespace="http://example.com",
        )
        original.set_element_name("element")
        original.set_ordering(5)
        original.set_mandatory(False)
        original.add_attribute("key", "value")

        cloned = original.clone()

        # Verify all fields copied
        assert cloned.name == original.name
        assert cloned.data_type == original.data_type
        assert cloned.scope == original.scope
        assert cloned.initial_value == original.initial_value
        assert cloned.documentation == original.documentation
        assert cloned.namespace == original.namespace
        assert cloned.get_element_name() == original.get_element_name()
        assert cloned.get_ordering() == original.get_ordering()
        assert cloned.is_mandatory() == original.is_mandatory()
        assert cloned.get_attributes() == original.get_attributes()

        # Verify it's a different object
        assert cloned is not original

        # Verify modifying clone doesn't affect original
        cloned.set_name("modified")
        assert original.name == "original"


class TestYVariableVerification:
    """Test verification methods."""

    def test_verify_with_handler(self) -> None:
        """Test verify method."""

        class MockHandler:
            def __init__(self) -> None:
                self.errors: list[str] = []
                self.warnings: list[str] = []

            def add_error(self, msg: str) -> None:
                self.errors.append(msg)

            def add_warning(self, msg: str) -> None:
                self.warnings.append(msg)

        # Test variable without name
        var_no_name = YVariable(name="")
        handler = MockHandler()
        var_no_name.verify(handler)
        assert len(handler.errors) == 1
        assert "must have a name" in handler.errors[0]

        # Test required variable without initial value
        var_required = YVariable(name="test")
        var_required.set_mandatory(True)
        var_required.set_optional(False)
        handler2 = MockHandler()
        var_required.verify(handler2)
        assert len(handler2.warnings) == 1
        assert "no initial value" in handler2.warnings[0]

    def test_check_value(self) -> None:
        """Test check_value method."""

        class MockHandler:
            def __init__(self) -> None:
                self.errors: list[str] = []

            def add_error(self, msg: str) -> None:
                self.errors.append(msg)

        var = YVariable(name="test")
        var.set_mandatory(True)
        var.set_optional(False)

        handler = MockHandler()
        var.check_value("", "TestLabel", handler)
        assert len(handler.errors) == 1
        assert "TestLabel" in handler.errors[0]
        assert "empty value" in handler.errors[0]

    def test_check_data_type_value(self) -> None:
        """Test check_data_type_value (no-op placeholder)."""
        var = YVariable(name="test")
        # Should not raise exception
        var.check_data_type_value("any_value")
        var.check_data_type_value(123)
        var.check_data_type_value(None)
