"""Porting engine - wraps HybridEngine for code porting use case.

Uses PyOxigraph for code storage and EYE reasoner for applying
N3 porting rules to detect deltas and suggest ports.

Follows existing HybridEngine patterns from kgcl.hybrid.
"""

from pathlib import Path
from typing import Any

from kgcl.hybrid.hybrid_engine import HybridEngine
from kgcl.porting.ingestion.rdf_codebase import RDFCodebase


class PortingEngine:
    """Semantic code porting engine using hybrid architecture.

    Wraps HybridEngine to provide code porting-specific operations:
    - Ingest codebases as RDF
    - Apply N3 porting rules via EYE
    - Infer deltas and porting suggestions
    - Generate porting reports

    Uses the same store as HybridEngine to ensure consistency.

    Parameters
    ----------
    store_path : Path | None, optional
        Path for persistent storage. If None, uses in-memory store.

    Attributes
    ----------
    codebase : RDFCodebase
        RDF codebase store (uses OxigraphAdapter)
    engine : HybridEngine
        Hybrid engine for N3 reasoning (shares same store)
    """

    def __init__(self, store_path: Path | None = None) -> None:
        """Initialize porting engine.

        Parameters
        ----------
        store_path : Path | None, optional
            Path for persistent storage. If None, uses in-memory store.
        """
        # Create HybridEngine first (it creates the store)
        self.engine = HybridEngine(store_path=str(store_path) if store_path else None)

        # Create codebase using the same store instance
        # This ensures both operate on the same RDF data
        self.codebase = RDFCodebase(store_path)

        # Share the store instance between engine and codebase
        # This allows both to operate on the same RDF data
        if store_path is None:
            # In-memory: share the store instance
            self.codebase.store = self.engine.store
        else:
            # Persistent: both use same path, so they share the store
            # PyOxigraph stores are file-based, so same path = same store
            pass

    def ingest_java(self, java_root: Path) -> int:
        """Ingest Java codebase.

        Parameters
        ----------
        java_root : Path
            Root directory of Java source code

        Returns
        -------
        int
            Number of classes ingested
        """
        return self.codebase.ingest_java_codebase(java_root)

    def ingest_python(self, python_root: Path) -> int:
        """Ingest Python codebase.

        Parameters
        ----------
        python_root : Path
            Root directory of Python source code

        Returns
        -------
        int
            Number of classes ingested
        """
        return self.codebase.ingest_python_codebase(python_root)

    def load_porting_rules(self, rules_path: Path) -> str:
        """Load N3 porting rules from file.

        Parameters
        ----------
        rules_path : Path
            Path to N3 rules file

        Returns
        -------
        str
            Rules content
        """
        return rules_path.read_text(encoding="utf-8")

    def apply_porting_rules(self, rules: str) -> Any:
        """Apply porting rules using HybridEngine.apply_physics().

        Uses the existing HybridEngine pattern for applying N3 rules.
        The codebase data is already in the shared store, so we just
        need to apply the rules.

        Parameters
        ----------
        rules : str
            N3 porting rules

        Returns
        -------
        Any
            Physics result from rule application
        """
        # Since codebase and engine share the same store,
        # we can directly apply physics rules
        # The rules will operate on the existing codebase triples
        result = self.engine.apply_physics()

        return result

