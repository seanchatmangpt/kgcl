"""Semantic delta detector using AST fingerprinting.

Compares method bodies semantically by:
- Normalizing ASTs (ignoring variable names, preserving logic)
- Generating semantic hashes
- Computing similarity scores
- Detecting algorithm changes and control flow differences
"""

import hashlib
from pathlib import Path
from typing import Any

from kgcl.yawl_ontology.enhanced_java_parser import EnhancedJavaParser, MethodBody as JavaMethodBody
from kgcl.yawl_ontology.enhanced_python_analyzer import (
    EnhancedPythonCodeAnalyzer,
    PythonMethodBody,
)
from kgcl.yawl_ontology.models import (
    AlgorithmDelta,
    CFGDelta,
    DataFlowDelta,
    DeltaSeverity,
    FingerprintDelta,
    SemanticDeltas,
)


class SemanticDetector:
    """Detect semantic differences between Java and Python methods."""

    def __init__(
        self,
        java_parser: EnhancedJavaParser,
        python_analyzer: EnhancedPythonCodeAnalyzer,
    ) -> None:
        """Initialize semantic detector.

        Parameters
        ----------
        java_parser : EnhancedJavaParser
            Enhanced Java parser with method bodies
        python_analyzer : EnhancedPythonCodeAnalyzer
            Enhanced Python analyzer with method bodies
        """
        self.java_parser = java_parser
        self.python_analyzer = python_analyzer

    def detect_deltas(
        self, java_classes: list[Any], python_classes: dict[str, Any]
    ) -> SemanticDeltas:
        """Detect semantic deltas between Java and Python implementations.

        Parameters
        ----------
        java_classes : list[Any]
            List of enhanced Java class info
        python_classes : dict[str, Any]
            Dictionary of Python class name -> enhanced class info

        Returns
        -------
        SemanticDeltas
            Detected semantic differences
        """
        fingerprint_mismatches: list[FingerprintDelta] = []
        algorithm_changes: list[AlgorithmDelta] = []
        control_flow_differences: list[CFGDelta] = []
        data_flow_differences: list[DataFlowDelta] = []

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

                # Generate fingerprints
                java_fp = self._generate_fingerprint(java_method, is_java=True)
                python_fp = self._generate_fingerprint(python_method, is_java=False)

                # Compare fingerprints
                similarity = self._compare_fingerprints(java_fp, python_fp)

                if similarity < 0.8:  # Threshold for significant difference
                    severity = (
                        DeltaSeverity.CRITICAL
                        if similarity < 0.5
                        else DeltaSeverity.HIGH
                        if similarity < 0.7
                        else DeltaSeverity.MEDIUM
                    )

                    fingerprint_mismatches.append(
                        FingerprintDelta(
                            java_class=java_class_name,
                            java_method=java_method_name,
                            java_fingerprint=java_fp,
                            python_fingerprint=python_fp,
                            similarity_score=similarity,
                            severity=severity,
                        )
                    )

                # Compare control flow complexity
                if java_method.complexity != python_method.complexity:
                    missing_branches = self._detect_missing_branches(
                        java_method, python_method
                    )
                    severity = (
                        DeltaSeverity.HIGH
                        if abs(java_method.complexity - python_method.complexity) > 3
                        else DeltaSeverity.MEDIUM
                    )

                    control_flow_differences.append(
                        CFGDelta(
                            java_class=java_class_name,
                            java_method=java_method_name,
                            java_complexity=java_method.complexity,
                            python_complexity=python_method.complexity,
                            missing_branches=missing_branches,
                            severity=severity,
                        )
                    )

                # Compare algorithms (loops, recursion patterns)
                if java_method.has_loops != python_method.has_loops:
                    java_approach = "has loops" if java_method.has_loops else "no loops"
                    python_approach = "has loops" if python_method.has_loops else "no loops"
                    algorithm_changes.append(
                        AlgorithmDelta(
                            java_class=java_class_name,
                            java_method=java_method_name,
                            java_approach=java_approach,
                            python_approach=python_approach,
                            complexity_difference=None,
                            severity=DeltaSeverity.MEDIUM,
                        )
                    )

                if java_method.has_recursion != python_method.has_recursion:
                    java_approach = "recursive" if java_method.has_recursion else "iterative"
                    python_approach = "recursive" if python_method.has_recursion else "iterative"
                    algorithm_changes.append(
                        AlgorithmDelta(
                            java_class=java_class_name,
                            java_method=java_method_name,
                            java_approach=java_approach,
                            python_approach=python_approach,
                            complexity_difference=None,
                            severity=DeltaSeverity.MEDIUM,
                        )
                    )

                # Compare data flow (mutations)
                java_mutations = self._extract_mutations(java_method, is_java=True)
                python_mutations = self._extract_mutations(python_method, is_java=False)
                missing_mutations = set(java_mutations) - set(python_mutations)
                extra_mutations = set(python_mutations) - set(java_mutations)

                if missing_mutations or extra_mutations:
                    data_flow_differences.append(
                        DataFlowDelta(
                            java_class=java_class_name,
                            java_method=java_method_name,
                            java_mutations=list(java_mutations),
                            python_mutations=list(python_mutations),
                            missing_mutations=list(missing_mutations),
                            extra_mutations=list(extra_mutations),
                            severity=DeltaSeverity.MEDIUM,
                        )
                    )

        return SemanticDeltas(
            fingerprint_mismatches=fingerprint_mismatches,
            algorithm_changes=algorithm_changes,
            control_flow_differences=control_flow_differences,
            data_flow_differences=data_flow_differences,
        )

    def _generate_fingerprint(
        self, method: JavaMethodBody | PythonMethodBody, is_java: bool
    ) -> str:
        """Generate semantic fingerprint from method body.

        Parameters
        ----------
        method : JavaMethodBody | PythonMethodBody
            Method to fingerprint
        is_java : bool
            Whether this is a Java method

        Returns
        -------
        str
            Semantic fingerprint hash
        """
        # Normalize the method body
        normalized = self._normalize_method_body(method, is_java)

        # Generate hash
        hash_obj = hashlib.sha256(normalized.encode("utf-8"))
        return hash_obj.hexdigest()[:16]  # Use first 16 chars for readability

    def _normalize_method_body(
        self, method: JavaMethodBody | PythonMethodBody, is_java: bool
    ) -> str:
        """Normalize method body for semantic comparison.

        Removes variable names, preserves control flow structure.

        Parameters
        ----------
        method : JavaMethodBody | PythonMethodBody
            Method to normalize
        is_java : bool
            Whether this is a Java method

        Returns
        -------
        str
            Normalized method body representation
        """
        # Use body text if available, otherwise use structural info
        body_text = method.body_text if hasattr(method, "body_text") else ""

        if not body_text:
            # Fall back to structural fingerprint
            parts = [
                f"complexity:{method.complexity}",
                f"loops:{method.has_loops}",
                f"recursion:{method.has_recursion}",
                f"calls:{len(method.call_sites)}",
            ]
            return "|".join(parts)

        # Normalize: remove variable names, preserve structure
        normalized = body_text

        # Remove comments
        if is_java:
            import re

            normalized = re.sub(r"//.*?\n", "\n", normalized)
            normalized = re.sub(r"/\*.*?\*/", "", normalized, flags=re.DOTALL)
        else:
            import re

            normalized = re.sub(r"#.*?\n", "\n", normalized)
            normalized = re.sub(r'""".*?"""', "", normalized, flags=re.DOTALL)
            normalized = re.sub(r"'''.*?'''", "", normalized, flags=re.DOTALL)

        # Normalize whitespace
        normalized = " ".join(normalized.split())

        # Remove variable names (simple heuristic: lowercase words that aren't keywords)
        # This is a simplified approach - full normalization would require AST parsing
        keywords = {
            "if",
            "else",
            "for",
            "while",
            "return",
            "class",
            "def",
            "import",
            "from",
            "try",
            "except",
            "finally",
            "raise",
            "pass",
            "continue",
            "break",
        }
        words = normalized.split()
        normalized_words = []
        for word in words:
            if word.lower() in keywords or not word.isalpha():
                normalized_words.append(word)
            else:
                normalized_words.append("VAR")

        return " ".join(normalized_words)

    def _compare_fingerprints(self, fp1: str, fp2: str) -> float:
        """Compare two fingerprints and return similarity score.

        Parameters
        ----------
        fp1 : str
            First fingerprint
        fp2 : str
            Second fingerprint

        Returns
        -------
        float
            Similarity score between 0.0 and 1.0
        """
        if fp1 == fp2:
            return 1.0

        # Simple character-level similarity
        # More sophisticated: use edit distance or structural comparison
        if len(fp1) == 0 or len(fp2) == 0:
            return 0.0

        # Jaccard similarity on character n-grams
        n = 3
        set1 = {fp1[i : i + n] for i in range(len(fp1) - n + 1)}
        set2 = {fp2[i : i + n] for i in range(len(fp2) - n + 1)}

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    def _detect_missing_branches(
        self, java_method: JavaMethodBody, python_method: PythonMethodBody
    ) -> list[str]:
        """Detect missing control flow branches.

        Parameters
        ----------
        java_method : JavaMethodBody
            Java method
        python_method : PythonMethodBody
            Python method

        Returns
        -------
        list[str]
            List of missing branch descriptions
        """
        missing: list[str] = []

        # If Java has higher complexity, Python might be missing branches
        if java_method.complexity > python_method.complexity:
            diff = java_method.complexity - python_method.complexity
            missing.append(f"Missing {diff} branch(es) compared to Java")

        # Check for specific patterns
        if java_method.has_loops and not python_method.has_loops:
            missing.append("Missing loop structure")

        return missing

    def _extract_mutations(
        self, method: JavaMethodBody | PythonMethodBody, is_java: bool
    ) -> list[str]:
        """Extract variable mutations from method body.

        Parameters
        ----------
        method : JavaMethodBody | PythonMethodBody
            Method to analyze
        is_java : bool
            Whether this is a Java method

        Returns
        -------
        list[str]
            List of mutation patterns
        """
        mutations: list[str] = []

        # Extract from call sites (methods that might mutate state)
        for call_site in method.call_sites:
            callee = call_site.callee_name if hasattr(call_site, "callee_name") else ""
            # Common mutation patterns
            if any(
                pattern in callee.lower()
                for pattern in ["set", "add", "remove", "update", "modify", "change"]
            ):
                mutations.append(f"mutates:{callee}")

        return mutations

