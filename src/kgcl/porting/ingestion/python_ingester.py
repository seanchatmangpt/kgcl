"""Python code ingester - converts Python source to RDF representation."""

from pathlib import Path

from kgcl.yawl_ontology.enhanced_python_analyzer import (
    EnhancedPythonCodeAnalyzer,
    EnhancedPythonClassInfo,
)


class PythonIngester:
    """Ingest Python source code and convert to RDF-ready format.

    Uses the enhanced Python analyzer to extract code structures
    that can be stored in PyOxigraph as RDF triples.
    """

    def __init__(self) -> None:
        """Initialize Python ingester."""
        self.analyzer: EnhancedPythonCodeAnalyzer | None = None
        self.classes: dict[str, EnhancedPythonClassInfo] = {}

    def analyze_codebase(self, python_root: Path) -> None:
        """Analyze Python codebase and extract class information.

        Parameters
        ----------
        python_root : Path
            Root directory of Python source code
        """
        self.analyzer = EnhancedPythonCodeAnalyzer(python_root)
        self.classes = self.analyzer.classes

