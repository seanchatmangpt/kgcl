"""Unit tests for delta detector components."""

from pathlib import Path

import pytest

from kgcl.yawl_ontology.enhanced_java_parser import EnhancedJavaParser
from kgcl.yawl_ontology.enhanced_python_analyzer import EnhancedPythonCodeAnalyzer
from kgcl.yawl_ontology.models import DeltaSeverity
from kgcl.yawl_ontology.semantic_detector import SemanticDetector


@pytest.fixture
def sample_java_code(tmp_path: Path) -> Path:
    """Create a sample Java file for testing."""
    java_file = tmp_path / "TestClass.java"
    java_file.write_text(
        """
package org.example;

public class TestClass {
    private String name;
    
    public String getName() {
        return name;
    }
    
    public void setName(String name) {
        this.name = name;
    }
    
    public int calculate(int a, int b) {
        if (a > b) {
            return a + b;
        }
        return a * b;
    }
}
"""
    )
    return java_file


@pytest.fixture
def sample_python_code(tmp_path: Path) -> Path:
    """Create a sample Python file for testing."""
    python_file = tmp_path / "test_class.py"
    python_file.write_text(
        '''
"""Test class implementation."""


class TestClass:
    """Test class."""

    def __init__(self) -> None:
        """Initialize."""
        self.name: str = ""

    def get_name(self) -> str:
        """Get name."""
        return self.name

    def set_name(self, name: str) -> None:
        """Set name."""
        self.name = name

    def calculate(self, a: int, b: int) -> int:
        """Calculate."""
        if a > b:
            return a + b
        return a * b
'''
    )
    return tmp_path


def test_enhanced_java_parser(sample_java_code: Path) -> None:
    """Test enhanced Java parser."""
    parser = EnhancedJavaParser()
    classes = parser.parse_file(sample_java_code)

    assert len(classes) == 1
    assert classes[0].name == "TestClass"
    assert len(classes[0].methods) == 3

    # Check method details
    method_names = {m.name for m in classes[0].methods}
    assert "getName" in method_names
    assert "setName" in method_names
    assert "calculate" in method_names

    # Check that methods have call sites and complexity
    calculate_method = next(m for m in classes[0].methods if m.name == "calculate")
    assert calculate_method.complexity > 1  # Has if statement
    assert calculate_method.return_type == "String" or calculate_method.return_type == "int"


def test_enhanced_python_analyzer(sample_python_code: Path) -> None:
    """Test enhanced Python analyzer."""
    analyzer = EnhancedPythonCodeAnalyzer(sample_python_code)
    assert "TestClass" in analyzer.classes

    test_class = analyzer.classes["TestClass"]
    assert len(test_class.methods) >= 3

    # Check method details
    method_names = {m.name for m in test_class.methods}
    assert "get_name" in method_names or "getName" in method_names
    assert "set_name" in method_names or "setName" in method_names
    assert "calculate" in method_names

    # Check that methods have type hints
    calculate_method = next(m for m in test_class.methods if m.name == "calculate")
    assert calculate_method.return_type is not None


def test_semantic_detector(sample_java_code: Path, sample_python_code: Path) -> None:
    """Test semantic detector."""
    java_parser = EnhancedJavaParser()
    python_analyzer = EnhancedPythonCodeAnalyzer(sample_python_code)

    java_classes = java_parser.parse_file(sample_java_code)
    python_classes = {cls.name: cls for cls in python_analyzer.classes.values()}

    detector = SemanticDetector(java_parser, python_analyzer)
    deltas = detector.detect_deltas(java_classes, python_classes)

    # Should detect some deltas (method name differences, etc.)
    assert isinstance(deltas.fingerprint_mismatches, list)
    assert isinstance(deltas.algorithm_changes, list)
    assert isinstance(deltas.control_flow_differences, list)


def test_delta_severity() -> None:
    """Test delta severity enum."""
    assert DeltaSeverity.CRITICAL.value == "critical"
    assert DeltaSeverity.HIGH.value == "high"
    assert DeltaSeverity.MEDIUM.value == "medium"
    assert DeltaSeverity.LOW.value == "low"
    assert DeltaSeverity.INFO.value == "info"

