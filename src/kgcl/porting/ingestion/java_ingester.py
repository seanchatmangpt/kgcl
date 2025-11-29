"""Java code ingester - converts Java source to RDF representation."""

from pathlib import Path

from kgcl.yawl_ontology.enhanced_java_parser import (
    EnhancedJavaParser,
    EnhancedClassInfo,
)


class JavaIngester:
    """Ingest Java source code and convert to RDF-ready format.

    Uses the enhanced Java parser to extract code structures
    that can be stored in PyOxigraph as RDF triples.
    """

    def __init__(self) -> None:
        """Initialize Java ingester."""
        self.parser = EnhancedJavaParser()

    def parse_file(self, java_file: Path) -> list[EnhancedClassInfo]:
        """Parse Java file and return enhanced class information.

        Parameters
        ----------
        java_file : Path
            Path to Java source file

        Returns
        -------
        list[EnhancedClassInfo]
            List of enhanced class information
        """
        return self.parser.parse_file(java_file)

