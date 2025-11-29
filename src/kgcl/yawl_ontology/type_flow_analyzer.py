"""Type flow analyzer for delta detection.

Tracks type transformations through method chains and compares Java vs Python
type systems to detect type safety regressions and incompatible return types.
"""

from typing import Any

from kgcl.yawl_ontology.enhanced_java_parser import EnhancedJavaParser
from kgcl.yawl_ontology.enhanced_python_analyzer import EnhancedPythonCodeAnalyzer
from kgcl.yawl_ontology.models import DeltaSeverity, TypeFlow, TypeFlowDelta, TypeFlowDeltas


class TypeFlowAnalyzer:
    """Analyze type flows and detect type-related deltas."""

    def __init__(
        self,
        java_parser: EnhancedJavaParser,
        python_analyzer: EnhancedPythonCodeAnalyzer,
    ) -> None:
        """Initialize type flow analyzer.

        Parameters
        ----------
        java_parser : EnhancedJavaParser
            Enhanced Java parser
        python_analyzer : EnhancedPythonCodeAnalyzer
            Enhanced Python analyzer
        """
        self.java_parser = java_parser
        self.python_analyzer = python_analyzer

        # Java to Python type mapping
        self.type_mapping = {
            "String": "str",
            "int": "int",
            "long": "int",
            "float": "float",
            "double": "float",
            "boolean": "bool",
            "List": "list",
            "Map": "dict",
            "Set": "set",
            "void": "None",
        }

    def detect_deltas(
        self, java_classes: list[Any], python_classes: dict[str, Any]
    ) -> TypeFlowDeltas:
        """Detect type flow differences between Java and Python.

        Parameters
        ----------
        java_classes : list[Any]
            List of enhanced Java class info
        python_classes : dict[str, Any]
            Dictionary of Python class name -> enhanced class info

        Returns
        -------
        TypeFlowDeltas
            Detected type flow differences
        """
        type_mismatches: list[TypeFlowDelta] = []
        missing_validations: list[TypeFlowDelta] = []
        incompatible_returns: list[TypeFlowDelta] = []

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

                # Extract type flows
                java_flow = self._extract_type_flow(java_class_name, java_method, is_java=True)
                python_flow = self._extract_type_flow(
                    java_class_name, python_method, is_java=False
                )

                # Compare return types
                java_return = self._normalize_type(java_method.return_type, is_java=True)
                python_return = (
                    self._normalize_type(python_method.return_type or "None", is_java=False)
                    if python_method.return_type
                    else "None"
                )

                if java_return != python_return and not self._are_compatible_types(
                    java_return, python_return
                ):
                    incompatible_returns.append(
                        TypeFlowDelta(
                            java_flow=java_flow,
                            python_flow=python_flow,
                            missing_validations=[],
                            incompatible_types=[f"return: {java_return} vs {python_return}"],
                            severity=DeltaSeverity.HIGH,
                        )
                    )

                # Compare parameter types
                java_param_types = self._extract_parameter_types(java_method, is_java=True)
                python_param_types = self._extract_parameter_types(python_method, is_java=False)

                if len(java_param_types) != len(python_param_types):
                    type_mismatches.append(
                        TypeFlowDelta(
                            java_flow=java_flow,
                            python_flow=python_flow,
                            missing_validations=[],
                            incompatible_types=[
                                f"parameter count: {len(java_param_types)} vs {len(python_param_types)}"
                            ],
                            severity=DeltaSeverity.MEDIUM,
                        )
                    )
                else:
                    incompatible = []
                    for java_type, python_type in zip(java_param_types, python_param_types):
                        if not self._are_compatible_types(java_type, python_type):
                            incompatible.append(f"{java_type} vs {python_type}")

                    if incompatible:
                        type_mismatches.append(
                            TypeFlowDelta(
                                java_flow=java_flow,
                                python_flow=python_flow,
                                missing_validations=[],
                                incompatible_types=incompatible,
                                severity=DeltaSeverity.MEDIUM,
                            )
                        )

        return TypeFlowDeltas(
            type_mismatches=type_mismatches,
            missing_validations=missing_validations,
            incompatible_returns=incompatible_returns,
        )

    def _extract_type_flow(
        self, class_name: str, method: Any, is_java: bool
    ) -> TypeFlow:
        """Extract type flow information from method.

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
        TypeFlow
            Type flow information
        """
        input_types = self._extract_parameter_types(method, is_java)
        output_type = (
            self._normalize_type(method.return_type, is_java)
            if hasattr(method, "return_type")
            else "None"
        )

        # Extract transformations from call sites
        transformations: list[str] = []
        if hasattr(method, "call_sites"):
            for call_site in method.call_sites:
                if is_java:
                    callee = call_site.callee_name
                else:
                    callee = call_site.callee_name
                transformations.append(f"calls:{callee}")

        return TypeFlow(
            class_name=class_name,
            method_name=method.name,
            input_types=input_types,
            output_type=output_type,
            transformations=transformations,
        )

    def _extract_parameter_types(self, method: Any, is_java: bool) -> list[str]:
        """Extract parameter types from method.

        Parameters
        ----------
        method : Any
            Method body object
        is_java : bool
            Whether this is a Java method

        Returns
        -------
        list[str]
            List of normalized parameter types
        """
        if is_java:
            # Extract from parameters string like "String name, int age"
            params = method.parameters
            types: list[str] = []
            for param in params:
                # Format: "Type name"
                parts = param.split()
                if parts:
                    param_type = parts[0]
                    types.append(self._normalize_type(param_type, is_java=True))
            return types
        else:
            # Extract from parameter_types dict
            if hasattr(method, "parameter_types"):
                return [
                    self._normalize_type(t, is_java=False) for t in method.parameter_types.values()
                ]
            return []

    def _normalize_type(self, type_str: str, is_java: bool) -> str:
        """Normalize type string for comparison.

        Parameters
        ----------
        type_str : str
            Type string
        is_java : bool
            Whether this is a Java type

        Returns
        -------
        str
            Normalized type string
        """
        if not type_str:
            return "None"

        # Remove generics
        clean_type = type_str.split("<")[0].split("[")[0].strip()

        if is_java:
            # Map Java types to Python equivalents
            return self.type_mapping.get(clean_type, clean_type)
        else:
            # Python types are already normalized
            return clean_type

    def _are_compatible_types(self, java_type: str, python_type: str) -> bool:
        """Check if Java and Python types are compatible.

        Parameters
        ----------
        java_type : str
            Normalized Java type
        python_type : str
            Normalized Python type

        Returns
        -------
        bool
            True if types are compatible
        """
        # Direct match
        if java_type == python_type:
            return True

        # Check type mapping
        mapped_java = self.type_mapping.get(java_type, java_type)
        if mapped_java == python_type:
            return True

        # Numeric types are compatible
        numeric_java = {"int", "long", "float", "double"}
        numeric_python = {"int", "float"}
        if java_type in numeric_java and python_type in numeric_python:
            return True

        # Collection types are compatible if both are collections
        collection_java = {"List", "Set", "Map"}
        collection_python = {"list", "set", "dict"}
        if java_type in collection_java and python_type in collection_python:
            return True

        return False

