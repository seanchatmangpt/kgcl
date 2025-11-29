"""Call graph analyzer for delta detection.

Extracts method call graphs from Java and Python codebases and compares them
to detect missing call paths, new paths, and orphaned methods.
"""

from collections import defaultdict
from typing import Any

from kgcl.yawl_ontology.enhanced_java_parser import EnhancedJavaParser, MethodBody as JavaMethodBody
from kgcl.yawl_ontology.enhanced_python_analyzer import (
    EnhancedPythonCodeAnalyzer,
    PythonMethodBody,
)
from kgcl.yawl_ontology.models import CallGraphDeltas, CallPath


class CallGraphAnalyzer:
    """Analyze and compare call graphs between Java and Python."""

    def __init__(
        self,
        java_parser: EnhancedJavaParser,
        python_analyzer: EnhancedPythonCodeAnalyzer,
    ) -> None:
        """Initialize call graph analyzer.

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
    ) -> CallGraphDeltas:
        """Detect call graph differences between Java and Python.

        Parameters
        ----------
        java_classes : list[Any]
            List of enhanced Java class info
        python_classes : dict[str, Any]
            Dictionary of Python class name -> enhanced class info

        Returns
        -------
        CallGraphDeltas
            Detected call graph differences
        """
        # Build call graphs
        java_graph = self._build_call_graph(java_classes, is_java=True)
        python_graph = self._build_call_graph(
            list(python_classes.values()), is_java=False
        )

        # Compare graphs
        missing_paths = self._find_missing_paths(java_graph, python_graph)
        new_paths = self._find_new_paths(java_graph, python_graph)
        orphaned_methods = self._find_orphaned_methods(java_graph, python_graph)

        return CallGraphDeltas(
            missing_paths=missing_paths,
            new_paths=new_paths,
            orphaned_methods=orphaned_methods,
        )

    def _build_call_graph(
        self, classes: list[Any], is_java: bool
    ) -> dict[tuple[str, str], set[tuple[str, str]]]:
        """Build call graph from classes.

        Parameters
        ----------
        classes : list[Any]
            List of class info objects
        is_java : bool
            Whether these are Java classes

        Returns
        -------
        dict[tuple[str, str], set[tuple[str, str]]]
            Call graph: (class, method) -> set of (callee_class, callee_method)
        """
        graph: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)

        for class_info in classes:
            class_name = class_info.name

            for method in class_info.methods:
                method_name = method.name
                caller_key = (class_name, method_name)

                # Extract call sites
                call_sites = method.call_sites

                for call_site in call_sites:
                    if is_java:
                        callee_name = call_site.callee_name
                        callee_class = call_site.callee_class or class_name  # Default to same class
                    else:
                        callee_name = call_site.callee_name
                        callee_attr = call_site.callee_attr
                        # Try to resolve callee class
                        callee_class = self._resolve_callee_class(
                            callee_attr, callee_name, classes, class_name
                        )

                    callee_key = (callee_class, callee_name)
                    graph[caller_key].add(callee_key)

        return dict(graph)

    def _resolve_callee_class(
        self,
        callee_attr: str | None,
        callee_name: str,
        classes: list[Any],
        current_class: str,
    ) -> str:
        """Resolve callee class from call site.

        Parameters
        ----------
        callee_attr : str | None
            Attribute/method name (for method calls)
        callee_name : str
            Function/method name
        classes : list[Any]
            List of class info objects
        current_class : str
            Current class name

        Returns
        -------
        str
            Resolved callee class name
        """
        # If it's a method call (has callee_attr), try to find the class
        if callee_attr:
            # Check if it's a method on an object of a known class
            for class_info in classes:
                if class_info.name == callee_attr:
                    return callee_attr
                # Check if any method matches
                for method in class_info.methods:
                    if method.name == callee_name:
                        return class_info.name

        # Check if it's a method in the current class
        for class_info in classes:
            if class_info.name == current_class:
                for method in class_info.methods:
                    if method.name == callee_name:
                        return current_class

        # Default: assume it's in the same class or a builtin
        return current_class

    def _find_missing_paths(
        self,
        java_graph: dict[tuple[str, str], set[tuple[str, str]]],
        python_graph: dict[tuple[str, str], set[tuple[str, str]]],
    ) -> list[CallPath]:
        """Find call paths that exist in Java but not in Python.

        Parameters
        ----------
        java_graph : dict[tuple[str, str], set[tuple[str, str]]]
            Java call graph
        python_graph : dict[tuple[str, str], set[tuple[str, str]]]
            Python call graph

        Returns
        -------
        list[CallPath]
            List of missing call paths
        """
        missing: list[CallPath] = []

        for (caller_class, caller_method), callees in java_graph.items():
            python_callees = python_graph.get((caller_class, caller_method), set())

            for callee_class, callee_method in callees:
                if (callee_class, callee_method) not in python_callees:
                    missing.append(
                        CallPath(
                            caller_class=caller_class,
                            caller_method=caller_method,
                            callee_class=callee_class,
                            callee_method=callee_method,
                        )
                    )

        return missing

    def _find_new_paths(
        self,
        java_graph: dict[tuple[str, str], set[tuple[str, str]]],
        python_graph: dict[tuple[str, str], set[tuple[str, str]]],
    ) -> list[CallPath]:
        """Find call paths that exist in Python but not in Java.

        Parameters
        ----------
        java_graph : dict[tuple[str, str], set[tuple[str, str]]]
            Java call graph
        python_graph : dict[tuple[str, str], set[tuple[str, str]]]
            Python call graph

        Returns
        -------
        list[CallPath]
            List of new call paths
        """
        new: list[CallPath] = []

        for (caller_class, caller_method), callees in python_graph.items():
            java_callees = java_graph.get((caller_class, caller_method), set())

            for callee_class, callee_method in callees:
                if (callee_class, callee_method) not in java_callees:
                    new.append(
                        CallPath(
                            caller_class=caller_class,
                            caller_method=caller_method,
                            callee_class=callee_class,
                            callee_method=callee_method,
                        )
                    )

        return new

    def _find_orphaned_methods(
        self,
        java_graph: dict[tuple[str, str], set[tuple[str, str]]],
        python_graph: dict[tuple[str, str], set[tuple[str, str]]],
    ) -> list[tuple[str, str]]:
        """Find methods that are called in Java but not called in Python.

        Parameters
        ----------
        java_graph : dict[tuple[str, str], set[tuple[str, str]]]
            Java call graph
        python_graph : dict[tuple[str, str], set[tuple[str, str]]]
            Python call graph

        Returns
        -------
        list[tuple[str, str]]
            List of (class, method) tuples for orphaned methods
        """
        orphaned: list[tuple[str, str]] = []

        # Find all methods that are called in Java
        java_callees: set[tuple[str, str]] = set()
        for callees in java_graph.values():
            java_callees.update(callees)

        # Find all methods that are called in Python
        python_callees: set[tuple[str, str]] = set()
        for callees in python_graph.values():
            python_callees.update(callees)

        # Methods called in Java but not in Python
        orphaned = list(java_callees - python_callees)

        return orphaned

