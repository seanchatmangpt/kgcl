"""Integration tests for delta detector.

Tests end-to-end delta detection with known Java/Python pairs.
"""

from pathlib import Path

import pytest

from kgcl.yawl_ontology.delta_detector import DeltaDetector


@pytest.mark.integration
def test_delta_detector_basic(tmp_path: Path) -> None:
    """Test basic delta detector functionality."""
    # Create sample Java and Python code
    java_root = tmp_path / "java"
    java_root.mkdir()
    java_file = java_root / "TestClass.java"
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

    python_root = tmp_path / "python"
    python_root.mkdir()
    python_file = python_root / "test_class.py"
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

    detector = DeltaDetector(
        java_root=java_root,
        python_root=python_root,
        ontology_path=None,
    )

    report = detector.detect_all_deltas()

    # Verify report structure
    assert report.summary.total_classes_analyzed > 0
    assert report.summary.total_methods_analyzed > 0
    assert 0 <= report.summary.coverage_percent <= 100

    # Verify delta categories exist
    assert report.structural_deltas is not None
    assert report.semantic_deltas is not None
    assert report.call_graph_deltas is not None
    assert report.type_flow_deltas is not None
    assert report.exception_deltas is not None
    assert report.dependency_deltas is not None
    assert report.performance_deltas is not None
    assert report.test_coverage_deltas is not None


@pytest.mark.integration
def test_delta_detector_export(tmp_path: Path) -> None:
    """Test delta detector report export."""
    java_root = tmp_path / "java"
    java_root.mkdir()
    (java_root / "TestClass.java").write_text(
        "package org.example; public class TestClass { }"
    )

    python_root = tmp_path / "python"
    python_root.mkdir()
    (python_root / "test_class.py").write_text("class TestClass: pass")

    detector = DeltaDetector(
        java_root=java_root,
        python_root=python_root,
    )

    report = detector.detect_all_deltas()

    # Test JSON export
    json_output = tmp_path / "deltas.json"
    detector.export_report(report, json_output, format="json")
    assert json_output.exists()
    assert json_output.read_text().startswith("{")

    # Test YAML export
    yaml_output = tmp_path / "deltas.yaml"
    detector.export_report(report, yaml_output, format="yaml")
    assert yaml_output.exists()
    assert "summary" in yaml_output.read_text().lower()

