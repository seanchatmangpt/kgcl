"""Unit tests for semantic porting engine."""

from pathlib import Path

import pytest

from kgcl.porting.engine.pattern_matcher import PatternMatcher
from kgcl.porting.engine.porting_engine import PortingEngine
from kgcl.porting.ingestion.rdf_codebase import RDFCodebase


@pytest.fixture
def sample_java_code(tmp_path: Path) -> Path:
    """Create sample Java code."""
    java_dir = tmp_path / "java"
    java_dir.mkdir()
    java_file = java_dir / "TestClass.java"
    java_file.write_text(
        """
package org.example;

public class TestClass {
    public String getName() {
        return "test";
    }
}
"""
    )
    return java_dir


@pytest.fixture
def sample_python_code(tmp_path: Path) -> Path:
    """Create sample Python code."""
    python_dir = tmp_path / "python"
    python_dir.mkdir()
    python_file = python_dir / "test_class.py"
    python_file.write_text(
        '''
"""Test class."""


class TestClass:
    """Test class."""

    def get_name(self) -> str:
        """Get name."""
        return "test"
'''
    )
    return python_dir


def test_porting_engine_ingestion(sample_java_code: Path, sample_python_code: Path, tmp_path: Path) -> None:
    """Test codebase ingestion."""
    engine = PortingEngine(store_path=tmp_path / "test_store")

    java_count = engine.ingest_java(sample_java_code)
    assert java_count > 0

    python_count = engine.ingest_python(sample_python_code)
    assert python_count > 0


def test_pattern_matcher(sample_java_code: Path, sample_python_code: Path, tmp_path: Path) -> None:
    """Test pattern matcher."""
    engine = PortingEngine(store_path=tmp_path / "test_store")
    engine.ingest_java(sample_java_code)
    engine.ingest_python(sample_python_code)

    matcher = PatternMatcher(engine.codebase)

    missing_classes = matcher.find_missing_classes()
    missing_methods = matcher.find_missing_methods()

    # Should find some deltas (naming differences)
    assert isinstance(missing_classes, list)
    assert isinstance(missing_methods, list)


def test_rdf_codebase_queries(sample_java_code: Path, sample_python_code: Path, tmp_path: Path) -> None:
    """Test RDF codebase queries."""
    codebase = RDFCodebase(store_path=tmp_path / "test_store")
    codebase.ingest_java_codebase(sample_java_code)
    codebase.ingest_python_codebase(sample_python_code)

    java_classes = codebase.query_classes(language="java")
    python_classes = codebase.query_classes(language="python")

    assert len(java_classes) > 0
    assert len(python_classes) > 0

    methods = codebase.query_methods()
    assert len(methods) > 0

