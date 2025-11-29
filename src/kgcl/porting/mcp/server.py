"""MCP server for semantic code porting.

Exposes porting tools as MCP server following FastMCP pattern.
"""

from pathlib import Path
from typing import Any

from kgcl.porting.engine.delta_inference import DeltaInference
from kgcl.porting.engine.pattern_matcher import PatternMatcher
from kgcl.porting.engine.porting_engine import PortingEngine


class PortingMCPServer:
    """MCP server for semantic code porting tool.

    Exposes porting capabilities as MCP tools and resources
    for IDE and agent integration.

    Parameters
    ----------
    java_root : Path | None, optional
        Root directory of Java codebase
    python_root : Path | None, optional
        Root directory of Python codebase
    store_path : Path | None, optional
        Path for persistent storage

    Note
    ----
    This is a placeholder for FastMCP integration. Full implementation
    would use FastMCP framework for MCP protocol compliance.
    """

    def __init__(
        self,
        java_root: Path | None = None,
        python_root: Path | None = None,
        store_path: Path | None = None,
    ) -> None:
        """Initialize MCP server.

        Parameters
        ----------
        java_root : Path | None, optional
            Root directory of Java codebase
        python_root : Path | None, optional
            Root directory of Python codebase
        store_path : Path | None, optional
            Path for persistent storage
        """
        self.engine = PortingEngine(store_path=store_path)
        self.pattern_matcher = PatternMatcher(self.engine.codebase)
        self.delta_inference = DeltaInference(self.engine)

        if java_root:
            self.engine.ingest_java(java_root)
        if python_root:
            self.engine.ingest_python(python_root)

    def detect_deltas(
        self, rules_path: Path | None = None
    ) -> dict[str, Any]:
        """Detect deltas between Java and Python codebases.

        Parameters
        ----------
        rules_path : Path | None, optional
            Path to N3 rules file. If None, uses SPARQL-based matching.

        Returns
        -------
        dict[str, Any]
            Dictionary of detected deltas
        """
        if rules_path and rules_path.exists():
            return self.delta_inference.infer_deltas(rules_path)

        # Fallback to SPARQL-based pattern matching
        return {
            "missing_classes": self.pattern_matcher.find_missing_classes(),
            "missing_methods": self.pattern_matcher.find_missing_methods(),
            "signature_mismatches": self.pattern_matcher.find_signature_mismatches(),
            "semantic_deltas": self.pattern_matcher.find_semantic_deltas(),
        }

    def suggest_port(self, class_name: str) -> dict[str, Any]:
        """Suggest porting strategy for a class.

        Parameters
        ----------
        class_name : str
            Name of class to port

        Returns
        -------
        dict[str, Any]
            Porting suggestions
        """
        missing_methods = self.pattern_matcher.find_missing_methods(class_name=class_name)
        signature_mismatches = [
            m for m in self.pattern_matcher.find_signature_mismatches() if class_name in m.get("javaMethod", "")
        ]

        return {
            "class_name": class_name,
            "missing_methods": missing_methods,
            "signature_mismatches": signature_mismatches,
            "suggestions": self._generate_suggestions(missing_methods, signature_mismatches),
        }

    def _generate_suggestions(
        self, missing_methods: list[dict[str, str]], signature_mismatches: list[dict[str, str]]
    ) -> list[str]:
        """Generate porting suggestions.

        Parameters
        ----------
        missing_methods : list[dict[str, str]]
            List of missing methods
        signature_mismatches : list[dict[str, str]]
            List of signature mismatches

        Returns
        -------
        list[str]
            List of suggestion strings
        """
        suggestions: list[str] = []

        if missing_methods:
            suggestions.append(f"Implement {len(missing_methods)} missing methods")

        if signature_mismatches:
            suggestions.append(f"Fix {len(signature_mismatches)} signature mismatches")

        return suggestions

    def validate_port(self, class_name: str) -> dict[str, Any]:
        """Validate porting completeness for a class.

        Parameters
        ----------
        class_name : str
            Name of class to validate

        Returns
        -------
        dict[str, Any]
            Validation results
        """
        missing_methods = self.pattern_matcher.find_missing_methods(class_name=class_name)
        signature_mismatches = [
            m for m in self.pattern_matcher.find_signature_mismatches() if class_name in m.get("javaMethod", "")
        ]

        total_issues = len(missing_methods) + len(signature_mismatches)
        is_complete = total_issues == 0

        return {
            "class_name": class_name,
            "is_complete": is_complete,
            "missing_methods": len(missing_methods),
            "signature_mismatches": len(signature_mismatches),
            "total_issues": total_issues,
        }

