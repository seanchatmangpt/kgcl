"""DSPy signature generator integrating RDF/SHACL transpiler.

This generator creates DSPy signature classes from RDF ontologies with
SHACL constraints, integrating the ultra-optimized transpiler with the
standard generator framework.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rdflib import Graph

from kgcl.codegen.base.generator import BaseGenerator, GenerationResult, Parser
from kgcl.codegen.transpiler import UltraOptimizedTTL2DSPyTranspiler


@dataclass(frozen=True)
class RDFMetadata:
    """Metadata from parsed RDF ontology.

    Parameters
    ----------
    graph : Graph
        Parsed RDF graph
    ontology_uri : str
        URI of the ontology
    file_path : Path
        Source file path
    """

    graph: Graph
    ontology_uri: str
    file_path: Path


class RDFParser(Parser[RDFMetadata]):
    """Parser for RDF/SHACL ontology files.

    Parses TTL/RDF/OWL files into RDF graphs with metadata extraction.
    """

    def parse(self, input_path: Path) -> RDFMetadata:
        """Parse RDF ontology file.

        Parameters
        ----------
        input_path : Path
            Path to RDF file

        Returns
        -------
        RDFMetadata
            Parsed graph with metadata

        Raises
        ------
        FileNotFoundError
            If input file doesn't exist
        """
        if not input_path.exists():
            msg = f"RDF file not found: {input_path}"
            raise FileNotFoundError(msg)

        graph = Graph()
        graph.parse(str(input_path), format="turtle")

        # Extract ontology URI
        from rdflib.namespace import OWL, RDF

        ontology_uri = "http://example.org/ontology"  # Default
        for s in graph.subjects(RDF.type, OWL.Ontology):
            ontology_uri = str(s)
            break

        return RDFMetadata(graph=graph, ontology_uri=ontology_uri, file_path=input_path)


class DSPySignatureGenerator(BaseGenerator[RDFMetadata]):
    """Generator for DSPy signature classes from RDF/SHACL ontologies.

    Integrates the ultra-optimized TTL to DSPy transpiler with the
    standard generator framework, providing caching, metrics, and
    validation capabilities.

    Parameters
    ----------
    template_dir : Path
        Directory containing templates (not used for DSPy)
    output_dir : Path
        Root directory for generated output
    dry_run : bool
        If True, don't write output files (default: False)
    cache_size : int
        Graph cache size (default: 100)
    max_workers : int
        Maximum parallel workers (default: 4)
    allow_multi_output : bool
        Allow signatures with multiple outputs (default: False)

    Examples
    --------
    >>> generator = DSPySignatureGenerator(template_dir=Path("templates"), output_dir=Path("generated"), cache_size=200)
    >>> result = generator.generate(Path("ontology.ttl"))
    >>> assert result.output_path.exists()
    """

    def __init__(
        self,
        template_dir: Path,
        output_dir: Path,
        dry_run: bool = False,
        cache_size: int = 100,
        max_workers: int = 4,
        allow_multi_output: bool = False,
    ) -> None:
        """Initialize DSPy generator with transpiler."""
        super().__init__(template_dir, output_dir, dry_run)

        # Initialize DSPy transpiler
        self.transpiler = UltraOptimizedTTL2DSPyTranspiler(cache_size=cache_size, max_workers=max_workers)
        self.allow_multi_output = allow_multi_output
        self._parser = RDFParser()

    @property
    def parser(self) -> Parser[RDFMetadata]:
        """Return RDF parser instance.

        Returns
        -------
        Parser[RDFMetadata]
            RDF ontology parser
        """
        return self._parser

    def _transform(self, metadata: RDFMetadata, **kwargs: Any) -> dict[str, Any]:
        """Transform RDF metadata to template context.

        For DSPy generation, we use the transpiler directly rather than
        templates, so this returns metadata for tracking only.

        Parameters
        ----------
        metadata : RDFMetadata
            Parsed RDF metadata
        **kwargs : Any
            Additional options

        Returns
        -------
        dict[str, Any]
            Context with metadata
        """
        return {
            "ontology_uri": metadata.ontology_uri,
            "file_path": str(metadata.file_path),
            "graph_size": len(metadata.graph),
        }

    def _get_template_name(self, metadata: RDFMetadata, **kwargs: Any) -> str:
        """Get template name (not used for DSPy generation).

        Parameters
        ----------
        metadata : RDFMetadata
            Parsed metadata
        **kwargs : Any
            Additional options

        Returns
        -------
        str
            Template name (unused)
        """
        return "dspy_signatures.py.j2"

    def _get_output_path(self, metadata: RDFMetadata, **kwargs: Any) -> Path:
        """Determine output file path.

        Parameters
        ----------
        metadata : RDFMetadata
            Parsed metadata
        **kwargs : Any
            May include 'output_path' override

        Returns
        -------
        Path
            Output file path
        """
        if "output_path" in kwargs:
            return Path(kwargs["output_path"])

        # Default: use input filename with .py extension
        stem = metadata.file_path.stem
        return self.output_dir / f"{stem}_signatures.py"

    def generate(self, input_path: Path, **kwargs: Any) -> GenerationResult:
        """Generate DSPy signatures from RDF ontology.

        Overrides base generate() to use transpiler directly instead of templates.

        Parameters
        ----------
        input_path : Path
            Path to RDF file
        **kwargs : Any
            Additional generation options

        Returns
        -------
        GenerationResult
            Generation result with output path, source, and metrics

        Raises
        ------
        FileNotFoundError
            If input file doesn't exist
        """
        # 1. Parse RDF file
        metadata = self.parser.parse(input_path)

        # 2. Generate signatures using transpiler
        signatures = self.transpiler.ultra_build_signatures([input_path], allow_multi_output=self.allow_multi_output)

        # 3. Generate module code
        source = self.transpiler.generate_ultra_module(signatures, ontology_uris=[metadata.ontology_uri])

        # 4. Get output path
        output_path = self._get_output_path(metadata, **kwargs)

        # 5. Write output (unless dry run)
        if not self.dry_run:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(source, encoding="utf-8")

        # 6. Build result metadata with transpiler metrics
        transpiler_metrics = self.transpiler.get_metrics()
        result_metadata = {
            "ontology_uri": metadata.ontology_uri,
            "signatures_generated": transpiler_metrics.signatures_generated,
            "processing_time_ms": transpiler_metrics.processing_time * 1000,
            "cache_efficiency": transpiler_metrics.cache_efficiency,
            "graph_size": len(metadata.graph),
        }

        return GenerationResult(output_path=output_path, source=source, metadata=result_metadata)


__all__ = ["DSPySignatureGenerator", "RDFMetadata", "RDFParser"]
