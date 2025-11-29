"""Exception analyzer for delta detection.

Maps exception throwing/catching patterns between Java and Python and detects
missing exception handling, changed exception types, and propagation differences.
"""

from typing import Any

from kgcl.yawl_ontology.enhanced_java_parser import EnhancedJavaParser
from kgcl.yawl_ontology.enhanced_python_analyzer import EnhancedPythonCodeAnalyzer
from kgcl.yawl_ontology.models import (
    DeltaSeverity,
    ExceptionDelta,
    ExceptionDeltas,
    ExceptionPattern,
)

# Java to Python exception type mapping
JAVA_TO_PYTHON_EXCEPTIONS = {
    "NullPointerException": "AttributeError",
    "IllegalArgumentException": "ValueError",
    "IllegalStateException": "RuntimeError",
    "IndexOutOfBoundsException": "IndexError",
    "UnsupportedOperationException": "NotImplementedError",
    "IOException": "IOError",
    "FileNotFoundException": "FileNotFoundError",
    "ClassNotFoundException": "ImportError",
    "RuntimeException": "RuntimeError",
    "Exception": "Exception",
    "Error": "Exception",
}


class ExceptionAnalyzer:
    """Analyze exception patterns and detect exception-related deltas."""

    def __init__(
        self,
        java_parser: EnhancedJavaParser,
        python_analyzer: EnhancedPythonCodeAnalyzer,
    ) -> None:
        """Initialize exception analyzer.

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
    ) -> ExceptionDeltas:
        """Detect exception handling differences between Java and Python.

        Parameters
        ----------
        java_classes : list[Any]
            List of enhanced Java class info
        python_classes : dict[str, Any]
            Dictionary of Python class name -> enhanced class info

        Returns
        -------
        ExceptionDeltas
            Detected exception differences
        """
        missing_exceptions: list[ExceptionDelta] = []
        changed_exceptions: list[ExceptionDelta] = []
        missing_handling: list[ExceptionDelta] = []

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

                # Extract exception patterns
                java_exceptions = self._extract_exception_patterns(
                    java_class_name, java_method_name, java_method, is_java=True
                )
                python_exceptions = self._extract_exception_patterns(
                    java_class_name, java_method_name, python_method, is_java=False
                )

                # Compare exceptions
                for java_exc in java_exceptions:
                    python_exc = self._find_matching_exception(java_exc, python_exceptions)

                    if not python_exc:
                        # Missing exception handling
                        missing_handling.append(
                            ExceptionDelta(
                                java_class=java_class_name,
                                java_method=java_method_name,
                                java_pattern=java_exc,
                                python_pattern=None,
                                missing_handling=True,
                                changed_type=False,
                                severity=DeltaSeverity.HIGH if java_exc.is_thrown else DeltaSeverity.MEDIUM,
                            )
                        )
                    else:
                        # Check if exception type changed
                        expected_python_type = JAVA_TO_PYTHON_EXCEPTIONS.get(
                            java_exc.exception_type, java_exc.exception_type
                        )
                        if python_exc.exception_type != expected_python_type:
                            changed_exceptions.append(
                                ExceptionDelta(
                                    java_class=java_class_name,
                                    java_method=java_method_name,
                                    java_pattern=java_exc,
                                    python_pattern=python_exc,
                                    missing_handling=False,
                                    changed_type=True,
                                    severity=DeltaSeverity.MEDIUM,
                                )
                            )

                # Check for exceptions in Python that don't exist in Java
                for python_exc in python_exceptions:
                    java_exc = self._find_matching_exception(python_exc, java_exceptions, reverse=True)
                    if not java_exc:
                        # New exception in Python
                        missing_exceptions.append(
                            ExceptionDelta(
                                java_class=java_class_name,
                                java_method=java_method_name,
                                java_pattern=None,
                                python_pattern=python_exc,
                                missing_handling=False,
                                changed_type=False,
                                severity=DeltaSeverity.LOW,
                            )
                        )

        return ExceptionDeltas(
            missing_exceptions=missing_exceptions,
            changed_exceptions=changed_exceptions,
            missing_handling=missing_handling,
        )

    def _extract_exception_patterns(
        self, class_name: str, method_name: str, method: Any, is_java: bool
    ) -> list[ExceptionPattern]:
        """Extract exception patterns from method.

        Parameters
        ----------
        class_name : str
            Class name
        method_name : str
            Method name
        method : Any
            Method body object
        is_java : bool
            Whether this is a Java method

        Returns
        -------
        list[ExceptionPattern]
            List of exception patterns
        """
        patterns: list[ExceptionPattern] = []

        if hasattr(method, "exceptions"):
            for exc_info in method.exceptions:
                if is_java:
                    patterns.append(
                        ExceptionPattern(
                            class_name=class_name,
                            method_name=method_name,
                            exception_type=exc_info.exception_type,
                            is_thrown=exc_info.is_thrown,
                            is_caught=exc_info.is_caught,
                            context=exc_info.context,
                        )
                    )
                else:
                    patterns.append(
                        ExceptionPattern(
                            class_name=class_name,
                            method_name=method_name,
                            exception_type=exc_info.exception_type,
                            is_thrown=exc_info.is_raised,
                            is_caught=exc_info.is_caught,
                            context=exc_info.context,
                        )
                    )

        return patterns

    def _find_matching_exception(
        self,
        target: ExceptionPattern,
        candidates: list[ExceptionPattern],
        reverse: bool = False,
    ) -> ExceptionPattern | None:
        """Find matching exception pattern.

        Parameters
        ----------
        target : ExceptionPattern
            Target exception pattern
        candidates : list[ExceptionPattern]
            List of candidate patterns
        reverse : bool
            If True, map Python to Java instead of Java to Python

        Returns
        -------
        ExceptionPattern | None
            Matching pattern or None
        """
        for candidate in candidates:
            # Match by context and exception type
            if target.context == candidate.context:
                if reverse:
                    # Python to Java mapping
                    python_to_java = {v: k for k, v in JAVA_TO_PYTHON_EXCEPTIONS.items()}
                    expected_java = python_to_java.get(
                        target.exception_type, target.exception_type
                    )
                    if candidate.exception_type == expected_java:
                        return candidate
                else:
                    # Java to Python mapping
                    expected_python = JAVA_TO_PYTHON_EXCEPTIONS.get(
                        target.exception_type, target.exception_type
                    )
                    if candidate.exception_type == expected_python:
                        return candidate

        return None

