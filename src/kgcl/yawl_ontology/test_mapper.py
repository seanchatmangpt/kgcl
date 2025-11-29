"""Test coverage mapper for delta detection.

Maps Java test files to Python implementations and calculates coverage deltas
to identify untested Python code and missing test scenarios.
"""

import ast
import re
from pathlib import Path
from typing import Any

from kgcl.yawl_ontology.models import DeltaSeverity, TestCoverage, TestCoverageDelta, TestCoverageDeltas


class TestMapper:
    """Map test coverage between Java and Python."""

    def __init__(self, java_test_root: Path, python_test_root: Path) -> None:
        """Initialize test mapper.

        Parameters
        ----------
        java_test_root : Path
            Root directory of Java test files
        python_test_root : Path
            Root directory of Python test files
        """
        self.java_test_root = java_test_root
        self.python_test_root = python_test_root

    def detect_deltas(
        self, java_classes: list[Any], python_classes: dict[str, Any]
    ) -> TestCoverageDeltas:
        """Detect test coverage differences between Java and Python.

        Parameters
        ----------
        java_classes : list[Any]
            List of enhanced Java class info
        python_classes : dict[str, Any]
            Dictionary of Python class name -> enhanced class info

        Returns
        -------
        TestCoverageDeltas
            Detected test coverage differences
        """
        uncovered_methods: list[TestCoverageDelta] = []
        coverage_gaps: list[TestCoverageDelta] = []

        # Map Java tests
        java_test_map = self._map_java_tests()

        # Map Python tests
        python_test_map = self._map_python_tests()

        # Compare coverage
        for java_class in java_classes:
            java_class_name = java_class.name
            python_class = python_classes.get(java_class_name)

            if not python_class:
                continue

            # Get test coverage for this class
            java_tests = java_test_map.get(java_class_name, [])
            python_tests = python_test_map.get(java_class_name, [])

            # Compare method coverage
            for java_method in java_class.methods:
                java_method_name = java_method.name

                # Find Java tests for this method
                java_method_tests = [
                    test for test in java_tests if self._test_covers_method(test, java_method_name)
                ]

                # Find Python tests for this method
                python_method_tests = [
                    test for test in python_tests if self._test_covers_method(test, java_method_name)
                ]

                # Calculate coverage
                java_coverage = 1.0 if java_method_tests else 0.0
                python_coverage = 1.0 if python_method_tests else 0.0

                if java_coverage > python_coverage:
                    missing_tests = [
                        test for test in java_method_tests if test not in python_method_tests
                    ]

                    severity = (
                        DeltaSeverity.HIGH
                        if java_coverage > 0 and python_coverage == 0
                        else DeltaSeverity.MEDIUM
                    )

                    if python_coverage == 0:
                        uncovered_methods.append(
                            TestCoverageDelta(
                                class_name=java_class_name,
                                method_name=java_method_name,
                                java_coverage=java_coverage,
                                python_coverage=python_coverage,
                                missing_tests=missing_tests,
                                severity=severity,
                            )
                        )
                    else:
                        coverage_gaps.append(
                            TestCoverageDelta(
                                class_name=java_class_name,
                                method_name=java_method_name,
                                java_coverage=java_coverage,
                                python_coverage=python_coverage,
                                missing_tests=missing_tests,
                                severity=severity,
                            )
                        )

        return TestCoverageDeltas(
            uncovered_methods=uncovered_methods,
            coverage_gaps=coverage_gaps,
        )

    def _map_java_tests(self) -> dict[str, list[str]]:
        """Map Java test files to classes.

        Returns
        -------
        dict[str, list[str]]
            Dictionary mapping class name -> list of test file paths
        """
        test_map: dict[str, list[str]] = {}

        if not self.java_test_root.exists():
            return test_map

        for test_file in self.java_test_root.rglob("*.java"):
            if "Test" not in test_file.name:
                continue

            try:
                content = test_file.read_text(encoding="utf-8")
                # Extract class names being tested
                class_names = self._extract_tested_classes(content, is_java=True)
                for class_name in class_names:
                    if class_name not in test_map:
                        test_map[class_name] = []
                    test_map[class_name].append(str(test_file))
            except Exception as e:
                print(f"Warning: Could not parse Java test {test_file}: {e}")

        return test_map

    def _map_python_tests(self) -> dict[str, list[str]]:
        """Map Python test files to classes.

        Returns
        -------
        dict[str, list[str]]
            Dictionary mapping class name -> list of test file paths
        """
        test_map: dict[str, list[str]] = {}

        if not self.python_test_root.exists():
            return test_map

        for test_file in self.python_test_root.rglob("test_*.py"):
            try:
                content = test_file.read_text(encoding="utf-8")
                # Extract class names being tested
                class_names = self._extract_tested_classes(content, is_java=False)
                for class_name in class_names:
                    if class_name not in test_map:
                        test_map[class_name] = []
                    test_map[class_name].append(str(test_file))
            except Exception as e:
                print(f"Warning: Could not parse Python test {test_file}: {e}")

        return test_map

    def _extract_tested_classes(self, content: str, is_java: bool) -> list[str]:
        """Extract class names being tested from test file content.

        Parameters
        ----------
        content : str
            Test file content
        is_java : bool
            Whether this is a Java test file

        Returns
        -------
        list[str]
            List of class names being tested
        """
        class_names: list[str] = []

        if is_java:
            # Java: Look for patterns like "new ClassName(" or "ClassName.class"
            patterns = [
                r"new\s+(\w+)\s*\(",
                r"(\w+)\.class",
                r"(\w+)\s+\w+\s*=\s*new",
            ]
            for pattern in patterns:
                matches = re.findall(pattern, content)
                class_names.extend(matches)
        else:
            # Python: Look for imports and instantiations
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if node.module:
                            # Extract class names from imports
                            for alias in node.names:
                                class_names.append(alias.name)
                    elif isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            class_names.append(node.func.id)
            except Exception:
                # Fallback to regex
                patterns = [
                    r"from\s+\S+\s+import\s+(\w+)",
                    r"import\s+(\w+)",
                    r"(\w+)\s*\(",
                ]
                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    class_names.extend(matches)

        # Remove duplicates and common test framework classes
        filtered = []
        test_framework_classes = {"Test", "TestCase", "Assert", "Mock", "Fixture"}
        for name in class_names:
            if name not in test_framework_classes and name not in filtered:
                filtered.append(name)

        return filtered

    def _test_covers_method(self, test_file: str, method_name: str) -> bool:
        """Check if a test file covers a specific method.

        Parameters
        ----------
        test_file : str
            Path to test file
        method_name : str
            Method name to check

        Returns
        -------
        bool
            True if test covers the method
        """
        try:
            content = Path(test_file).read_text(encoding="utf-8")
            # Look for method name in test file
            # Common patterns: testMethodName, test_method_name, methodName()
            patterns = [
                f"test{method_name}",
                f"test_{method_name.lower()}",
                f"{method_name}()",
                f".{method_name}(",
            ]
            for pattern in patterns:
                if pattern in content:
                    return True
            return False
        except Exception:
            return False

