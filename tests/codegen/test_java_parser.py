"""Tests for Java parser."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from scripts.codegen.java_parser import JavaParseError, JavaParser


class TestJavaParser:
    """Test Java source file parsing."""

    @pytest.fixture
    def parser(self) -> JavaParser:
        """Create parser instance."""
        return JavaParser()

    @pytest.fixture
    def sample_java_file(self, tmp_path: Path) -> Path:
        """Create sample Java file for testing."""
        java_code = dedent(
            """
            package org.yawlfoundation.yawl.ui.service;

            import java.util.List;
            import java.util.Map;

            public class SampleService {
                private String name;

                public List<String> getItems(String filter) {
                    return null;
                }
            }
            """
        ).strip()

        java_file = tmp_path / "SampleService.java"
        java_file.write_text(java_code)
        return java_file

    def test_parse_file_success(self, parser: JavaParser, sample_java_file: Path) -> None:
        """Test successful Java file parsing."""
        java_class = parser.parse_file(sample_java_file)

        assert java_class.name == "SampleService"
        assert java_class.package == "org.yawlfoundation.yawl.ui.service"
        assert len(java_class.fields) == 1
        assert len(java_class.methods) == 1

    def test_parse_file_not_found(self, parser: JavaParser) -> None:
        """Test parsing non-existent file."""
        non_existent = Path("/tmp/does_not_exist.java")

        with pytest.raises(FileNotFoundError):
            parser.parse_file(non_existent)

    def test_parse_file_invalid_syntax(self, parser: JavaParser, tmp_path: Path) -> None:
        """Test parsing file with invalid Java syntax."""
        bad_java = tmp_path / "bad.java"
        bad_java.write_text("public class {{{{{ invalid syntax")

        with pytest.raises(JavaParseError):
            parser.parse_file(bad_java)
