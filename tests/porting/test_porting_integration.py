"""Integration tests for semantic porting tool."""

from pathlib import Path

import pytest

from kgcl.porting.engine.porting_engine import PortingEngine
from kgcl.porting.mcp.server import PortingMCPServer


@pytest.mark.integration
def test_porting_engine_end_to_end(tmp_path: Path) -> None:
    """Test end-to-end porting engine workflow."""
    # Create sample code
    java_dir = tmp_path / "java"
    java_dir.mkdir()
    (java_dir / "TestClass.java").write_text(
        "package org.example; public class TestClass { public String getName() { return \"test\"; } }"
    )

    python_dir = tmp_path / "python"
    python_dir.mkdir()
    (python_dir / "test_class.py").write_text('class TestClass: def get_name(self) -> str: return "test"')

    # Test ingestion
    engine = PortingEngine(store_path=tmp_path / "store")
    java_count = engine.ingest_java(java_dir)
    python_count = engine.ingest_python(python_dir)

    assert java_count > 0
    assert python_count > 0

    # Test pattern matching
    from kgcl.porting.engine.pattern_matcher import PatternMatcher

    matcher = PatternMatcher(engine.codebase)
    deltas = {
        "missing_classes": matcher.find_missing_classes(),
        "missing_methods": matcher.find_missing_methods(),
    }

    assert isinstance(deltas, dict)
    assert "missing_classes" in deltas
    assert "missing_methods" in deltas


@pytest.mark.integration
def test_mcp_server(tmp_path: Path) -> None:
    """Test MCP server functionality."""
    java_dir = tmp_path / "java"
    java_dir.mkdir()
    (java_dir / "TestClass.java").write_text(
        "package org.example; public class TestClass { }"
    )

    python_dir = tmp_path / "python"
    python_dir.mkdir()
    (python_dir / "test_class.py").write_text("class TestClass: pass")

    server = PortingMCPServer(
        java_root=java_dir,
        python_root=python_dir,
        store_path=tmp_path / "store",
    )

    # Test delta detection
    deltas = server.detect_deltas()
    assert isinstance(deltas, dict)

    # Test port suggestion
    suggestion = server.suggest_port("TestClass")
    assert isinstance(suggestion, dict)
    assert "class_name" in suggestion

    # Test validation
    validation = server.validate_port("TestClass")
    assert isinstance(validation, dict)
    assert "is_complete" in validation

