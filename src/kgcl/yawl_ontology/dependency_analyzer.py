"""Dependency analyzer for delta detection.

Extracts class dependencies from imports, fields, and method parameters,
builds dependency graphs, and compares them to detect missing dependencies,
new dependencies, and circular dependency differences.
"""

from typing import Any

from kgcl.yawl_ontology.enhanced_java_parser import EnhancedJavaParser
from kgcl.yawl_ontology.enhanced_python_analyzer import EnhancedPythonCodeAnalyzer
from kgcl.yawl_ontology.models import (
    DeltaSeverity,
    Dependency,
    DependencyDelta,
    DependencyDeltas,
)


class DependencyAnalyzer:
    """Analyze dependencies and detect dependency-related deltas."""

    def __init__(
        self,
        java_parser: EnhancedJavaParser,
        python_analyzer: EnhancedPythonCodeAnalyzer,
    ) -> None:
        """Initialize dependency analyzer.

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
    ) -> DependencyDeltas:
        """Detect dependency differences between Java and Python.

        Parameters
        ----------
        java_classes : list[Any]
            List of enhanced Java class info
        python_classes : dict[str, Any]
            Dictionary of Python class name -> enhanced class info

        Returns
        -------
        DependencyDeltas
            Detected dependency differences
        """
        missing_dependencies: list[DependencyDelta] = []
        new_dependencies: list[DependencyDelta] = []
        circular_differences: list[DependencyDelta] = []

        for java_class in java_classes:
            java_class_name = java_class.name
            python_class = python_classes.get(java_class_name)

            if not python_class:
                continue

            # Extract dependencies
            java_deps = self._extract_dependencies(java_class, is_java=True)
            python_deps = self._extract_dependencies(python_class, is_java=False)

            # Compare dependencies
            java_dep_names = {dep.dependency_class for dep in java_deps}
            python_dep_names = {dep.dependency_class for dep in python_deps}

            missing = java_dep_names - python_dep_names
            new = python_dep_names - java_dep_names

            if missing:
                missing_dep_objs = [d for d in java_deps if d.dependency_class in missing]
                missing_dependencies.append(
                    DependencyDelta(
                        java_class=java_class_name,
                        missing_dependencies=missing_dep_objs,
                        new_dependencies=[],
                        circular_differences=[],
                        severity=DeltaSeverity.HIGH if len(missing) > 3 else DeltaSeverity.MEDIUM,
                    )
                )

            if new:
                new_dep_objs = [d for d in python_deps if d.dependency_class in new]
                new_dependencies.append(
                    DependencyDelta(
                        java_class=java_class_name,
                        missing_dependencies=[],
                        new_dependencies=new_dep_objs,
                        circular_differences=[],
                        severity=DeltaSeverity.LOW,
                    )
                )

            # Check for circular dependencies
            java_circular = [d for d in java_deps if d.is_circular]
            python_circular = [d for d in python_deps if d.is_circular]

            if len(java_circular) != len(python_circular):
                circular_differences.append(
                    DependencyDelta(
                        java_class=java_class_name,
                        missing_dependencies=[],
                        new_dependencies=[],
                        circular_differences=java_circular + python_circular,
                        severity=DeltaSeverity.MEDIUM,
                    )
                )

        return DependencyDeltas(
            missing_dependencies=missing_dependencies,
            new_dependencies=new_dependencies,
            circular_differences=circular_differences,
        )

    def _extract_dependencies(self, class_info: Any, is_java: bool) -> list[Dependency]:
        """Extract dependencies from class.

        Parameters
        ----------
        class_info : Any
            Class info object
        is_java : bool
            Whether this is a Java class

        Returns
        -------
        list[Dependency]
            List of dependencies
        """
        dependencies: list[Dependency] = []

        # Extract from imports
        if hasattr(class_info, "imports"):
            for imp in class_info.imports:
                dep_class = imp.split(".")[-1]  # Get class name from import
                dependencies.append(
                    Dependency(
                        dependent_class=class_info.name,
                        dependency_class=dep_class,
                        dependency_type="import",
                        is_circular=False,
                    )
                )

        # Extract from field types
        if hasattr(class_info, "field_types"):
            for field_type in class_info.field_types.values():
                # Remove generics
                clean_type = field_type.split("<")[0].split("[")[0]
                dependencies.append(
                    Dependency(
                        dependent_class=class_info.name,
                        dependency_class=clean_type,
                        dependency_type="field",
                        is_circular=clean_type == class_info.name,
                    )
                )

        # Extract from method parameters and return types
        if hasattr(class_info, "methods"):
            for method in class_info.methods:
                # Parameter types
                if is_java:
                    for param in method.parameters:
                        parts = param.split()
                        if parts:
                            param_type = parts[0].split("<")[0].split("[")[0]
                            dependencies.append(
                                Dependency(
                                    dependent_class=class_info.name,
                                    dependency_class=param_type,
                                    dependency_type="parameter",
                                    is_circular=param_type == class_info.name,
                                )
                            )
                else:
                    if hasattr(method, "parameter_types"):
                        for param_type in method.parameter_types.values():
                            clean_type = param_type.split("[")[0]
                            dependencies.append(
                                Dependency(
                                    dependent_class=class_info.name,
                                    dependency_class=clean_type,
                                    dependency_type="parameter",
                                    is_circular=clean_type == class_info.name,
                                )
                            )

                # Return type
                if hasattr(method, "return_type") and method.return_type:
                    return_type = method.return_type.split("<")[0].split("[")[0]
                    if return_type not in {"void", "None", "str", "int", "bool", "float"}:
                        dependencies.append(
                            Dependency(
                                dependent_class=class_info.name,
                                dependency_class=return_type,
                                dependency_type="return",
                                is_circular=return_type == class_info.name,
                            )
                        )

        # Remove duplicates
        seen = set()
        unique_deps = []
        for dep in dependencies:
            key = (dep.dependent_class, dep.dependency_class, dep.dependency_type)
            if key not in seen:
                seen.add(key)
                unique_deps.append(dep)

        return unique_deps

