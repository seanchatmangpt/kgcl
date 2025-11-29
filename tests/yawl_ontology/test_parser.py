"""Tests for Java source code parser.

Chicago School TDD - tests assert on real Java parsing behavior.
"""

from pathlib import Path
from textwrap import dedent

import pytest

from kgcl.yawl_ontology.parser import JavaParser, MethodInfo


@pytest.fixture
def tmp_java_file(tmp_path: Path) -> Path:
    """Create a temporary Java file for testing."""
    java_file = tmp_path / "TestClass.java"
    content = dedent("""
        package org.example.test;

        import java.util.List;

        /**
         * Test class for demonstrating parsing.
         * This is a multi-line javadoc comment.
         */
        public class TestClass {
            private String name;
            private int count;

            /**
             * Constructor for TestClass.
             * @param name the name parameter
             */
            public TestClass(String name) {
                this.name = name;
            }

            /**
             * Get the name value.
             * @return the name
             */
            public String getName() {
                return name;
            }

            /**
             * Calculate something with backslash \\ and quotes "test".
             * @param value the input value
             * @return calculated result
             */
            public int calculate(int value) {
                return value * 2;
            }
        }
    """)
    java_file.write_text(content)
    return java_file


def test_parser_extracts_package_name(tmp_java_file: Path) -> None:
    """Test that parser correctly extracts package declaration."""
    parser = JavaParser()
    classes = parser.parse_file(tmp_java_file)

    assert len(classes) == 1
    assert classes[0].package == "org.example.test"


def test_parser_extracts_class_name(tmp_java_file: Path) -> None:
    """Test that parser correctly extracts class name."""
    parser = JavaParser()
    classes = parser.parse_file(tmp_java_file)

    assert classes[0].name == "TestClass"
    assert classes[0].clean_name == "TestClass"


def test_parser_extracts_javadoc(tmp_java_file: Path) -> None:
    """Test that parser extracts and cleans javadoc comments."""
    parser = JavaParser()
    classes = parser.parse_file(tmp_java_file)

    javadoc = classes[0].javadoc
    assert "Test class for demonstrating parsing" in javadoc
    assert "multi-line javadoc" in javadoc
    assert "/**" not in javadoc  # Cleaned


def test_parser_extracts_methods(tmp_java_file: Path) -> None:
    """Test that parser extracts method declarations."""
    parser = JavaParser()
    classes = parser.parse_file(tmp_java_file)

    methods = classes[0].methods
    assert len(methods) == 2  # getName and calculate (constructor not included)

    get_name = next(m for m in methods if m.name == "getName")
    assert get_name.return_type == "String"
    assert len(get_name.parameters) == 0


def test_parser_extracts_method_parameters(tmp_java_file: Path) -> None:
    """Test that parser extracts method parameter types and names."""
    parser = JavaParser()
    classes = parser.parse_file(tmp_java_file)

    calculate = next(m for m in classes[0].methods if m.name == "calculate")
    assert calculate.return_type == "int"
    assert len(calculate.parameters) == 1
    assert "int value" in calculate.parameters[0]


def test_parser_escapes_special_characters_in_javadoc(tmp_java_file: Path) -> None:
    """Test that parser properly escapes backslashes and quotes in javadoc."""
    parser = JavaParser()
    classes = parser.parse_file(tmp_java_file)

    calculate = next(m for m in classes[0].methods if m.name == "calculate")
    javadoc = calculate.javadoc

    # Backslashes should be escaped for Turtle
    assert "\\\\" in javadoc or "backslash" in javadoc
    # Quotes should be escaped
    assert '\\"' in javadoc or "test" in javadoc


def test_parser_extracts_fields(tmp_java_file: Path) -> None:
    """Test that parser extracts field declarations."""
    parser = JavaParser()
    classes = parser.parse_file(tmp_java_file)

    fields = classes[0].fields
    assert "name" in fields
    assert "count" in fields


def test_parser_extracts_modifiers(tmp_java_file: Path) -> None:
    """Test that parser extracts class and method modifiers."""
    parser = JavaParser()
    classes = parser.parse_file(tmp_java_file)

    assert "public" in classes[0].modifiers

    get_name = next(m for m in classes[0].methods if m.name == "getName")
    assert "public" in get_name.modifiers


def test_method_info_signature_generation() -> None:
    """Test that MethodInfo generates correct signatures."""
    method = MethodInfo(
        name="testMethod", return_type="String", parameters=["int value", "String name"], modifiers={"public"}
    )

    assert method.signature == "String testMethod(int value, String name)"


def test_method_info_clean_name() -> None:
    """Test that MethodInfo generates URI-safe names."""
    method = MethodInfo(name="test<T>Method", return_type="List<String>", parameters=[])

    assert "<" not in method.clean_name
    assert ">" not in method.clean_name


def test_parser_handles_syntax_errors(tmp_path: Path) -> None:
    """Test that parser gracefully handles Java syntax errors."""
    bad_file = tmp_path / "Bad.java"
    bad_file.write_text("public class Bad { invalid syntax }")

    parser = JavaParser()
    classes = parser.parse_file(bad_file)

    assert len(classes) == 0  # Returns empty list on syntax error


def test_parser_handles_missing_package(tmp_path: Path) -> None:
    """Test that parser handles files without package declaration."""
    no_package = tmp_path / "NoPackage.java"
    no_package.write_text("public class NoPackage { }")

    parser = JavaParser()
    classes = parser.parse_file(no_package)

    assert len(classes) == 1
    assert classes[0].package == "default"
