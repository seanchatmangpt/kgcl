"""Performance characteristics analyzer for delta detection.

Analyzes algorithmic complexity, loop structures, and recursion patterns
to detect performance regressions and optimization opportunities.
"""

from typing import Any

from kgcl.yawl_ontology.enhanced_java_parser import EnhancedJavaParser
from kgcl.yawl_ontology.enhanced_python_analyzer import EnhancedPythonCodeAnalyzer
from kgcl.yawl_ontology.models import (
    DeltaSeverity,
    PerformanceDelta,
    PerformanceDeltas,
    PerformanceMetric,
)


class PerformanceAnalyzer:
    """Analyze performance characteristics and detect performance-related deltas."""

    def __init__(
        self,
        java_parser: EnhancedJavaParser,
        python_analyzer: EnhancedPythonCodeAnalyzer,
    ) -> None:
        """Initialize performance analyzer.

        Parameters
        ----------
        java_parser : EnhancedJavaParser
            Enhanced Java parser
        python_analyzer : EnhancedPythonCodeAnalyzer
            Enhanced Python analyzer
        """
        self.java_parser = java_parser
        self.python_analyzer = python_analyzer

    def detect_deltas(
        self, java_classes: list[Any], python_classes: dict[str, Any]
    ) -> PerformanceDeltas:
        """Detect performance characteristic differences between Java and Python.

        Parameters
        ----------
        java_classes : list[Any]
            List of enhanced Java class info
        python_classes : dict[str, Any]
            Dictionary of Python class name -> enhanced class info

        Returns
        -------
        PerformanceDeltas
            Detected performance differences
        """
        complexity_regressions: list[PerformanceDelta] = []
        optimization_opportunities: list[PerformanceDelta] = []

        for java_class in java_classes:
            java_class_name = java_class.name
            python_class = python_classes.get(java_class_name)

            if not python_class:
                continue

            # Compare methods
            java_methods = {m.name: m for m in java_class.methods}
            python_methods = {m.name: m for m in python_class.methods}

            for java_method_name, java_method in java_methods.items():
                python_method = python_methods.get(java_method_name)

                if not python_method:
                    continue

                # Extract performance metrics
                java_metrics = self._extract_performance_metrics(
                    java_class_name, java_method, is_java=True
                )
                python_metrics = self._extract_performance_metrics(
                    java_class_name, python_method, is_java=False
                )

                # Compare complexity
                java_complexity = self._complexity_to_big_o(java_metrics)
                python_complexity = self._complexity_to_big_o(python_metrics)

                if self._is_complexity_regression(java_complexity, python_complexity):
                    complexity_regressions.append(
                        PerformanceDelta(
                            java_class=java_class_name,
                            java_method=java_method_name,
                            java_metrics=java_metrics,
                            python_metrics=python_metrics,
                            complexity_regression=True,
                            optimization_opportunity=False,
                            severity=DeltaSeverity.HIGH,
                        )
                    )
                elif self._is_optimization_opportunity(java_complexity, python_complexity):
                    optimization_opportunities.append(
                        PerformanceDelta(
                            java_class=java_class_name,
                            java_method=java_method_name,
                            java_metrics=java_metrics,
                            python_metrics=python_metrics,
                            complexity_regression=False,
                            optimization_opportunity=True,
                            severity=DeltaSeverity.LOW,
                        )
                    )

        return PerformanceDeltas(
            complexity_regressions=complexity_regressions,
            optimization_opportunities=optimization_opportunities,
        )

    def _extract_performance_metrics(
        self, class_name: str, method: Any, is_java: bool
    ) -> PerformanceMetric:
        """Extract performance metrics from method.

        Parameters
        ----------
        class_name : str
            Class name
        method : Any
            Method body object
        is_java : bool
            Whether this is a Java method

        Returns
        -------
        PerformanceMetric
            Performance metrics
        """
        complexity = self._estimate_complexity(method)
        loop_count = self._count_loops(method)
        recursion_depth = 1 if hasattr(method, "has_recursion") and method.has_recursion else 0
        has_nested_loops = loop_count > 1

        return PerformanceMetric(
            class_name=class_name,
            method_name=method.name,
            complexity=complexity,
            loop_count=loop_count,
            recursion_depth=recursion_depth,
            has_nested_loops=has_nested_loops,
        )

    def _estimate_complexity(self, method: Any) -> str:
        """Estimate algorithmic complexity from method characteristics.

        Parameters
        ----------
        method : Any
            Method body object

        Returns
        -------
        str
            Complexity notation (O(1), O(n), O(n^2), etc.)
        """
        complexity = method.complexity if hasattr(method, "complexity") else 1
        has_loops = method.has_loops if hasattr(method, "has_loops") else False
        has_nested = (
            hasattr(method, "has_loops")
            and hasattr(method, "complexity")
            and method.complexity > 3
        )

        if complexity == 1:
            return "O(1)"
        elif complexity <= 3 and not has_loops:
            return "O(1)"
        elif has_nested:
            return "O(n^2)"
        elif has_loops:
            return "O(n)"
        else:
            return "O(log n)"

    def _count_loops(self, method: Any) -> int:
        """Count number of loops in method.

        Parameters
        ----------
        method : Any
            Method body object

        Returns
        -------
        int
            Number of loops
        """
        if not hasattr(method, "has_loops") or not method.has_loops:
            return 0

        # Estimate based on complexity
        complexity = method.complexity if hasattr(method, "complexity") else 1
        if complexity > 5:
            return 2  # Likely nested loops
        elif complexity > 2:
            return 1
        else:
            return 0

    def _complexity_to_big_o(self, metric: PerformanceMetric) -> str:
        """Convert performance metric to Big-O notation.

        Parameters
        ----------
        metric : PerformanceMetric
            Performance metric

        Returns
        -------
        str
            Big-O notation
        """
        return metric.complexity

    def _is_complexity_regression(self, java_complexity: str, python_complexity: str) -> bool:
        """Check if Python has worse complexity than Java.

        Parameters
        ----------
        java_complexity : str
            Java complexity
        python_complexity : str
            Python complexity

        Returns
        -------
        bool
            True if Python has worse complexity
        """
        complexity_order = {"O(1)": 1, "O(log n)": 2, "O(n)": 3, "O(n^2)": 4, "O(n^3)": 5}
        java_order = complexity_order.get(java_complexity, 3)
        python_order = complexity_order.get(python_complexity, 3)
        return python_order > java_order

    def _is_optimization_opportunity(self, java_complexity: str, python_complexity: str) -> bool:
        """Check if Python has better complexity than Java (optimization opportunity).

        Parameters
        ----------
        java_complexity : str
            Java complexity
        python_complexity : str
            Python complexity

        Returns
        -------
        bool
            True if Python has better complexity
        """
        complexity_order = {"O(1)": 1, "O(log n)": 2, "O(n)": 3, "O(n^2)": 4, "O(n^3)": 5}
        java_order = complexity_order.get(java_complexity, 3)
        python_order = complexity_order.get(python_complexity, 3)
        return python_order < java_order

