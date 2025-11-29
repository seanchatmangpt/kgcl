"""Delta inference using HybridEngine and N3 rules.

Infers deltas between codebases by applying N3 porting rules
via HybridEngine.apply_physics() pattern.
"""

from pathlib import Path
from typing import Any

from kgcl.porting.engine.porting_engine import PortingEngine


class DeltaInference:
    """Infer deltas using HybridEngine and N3 rules.

    Uses HybridEngine.apply_physics() to apply N3 porting rules
    and infer structural and semantic deltas between codebases.

    Follows existing HybridEngine patterns from kgcl.hybrid.

    Parameters
    ----------
    porting_engine : PortingEngine
        Porting engine with ingested codebases
    """

    def __init__(self, porting_engine: PortingEngine) -> None:
        """Initialize delta inference.

        Parameters
        ----------
        porting_engine : PortingEngine
            Porting engine with ingested codebases
        """
        self.engine = porting_engine

    def infer_deltas(self, rules_path: Path) -> dict[str, Any]:
        """Infer deltas by applying N3 rules via HybridEngine.

        Uses HybridEngine.apply_physics() pattern to apply N3 rules.
        The rules are loaded and applied to the existing codebase state
        in the shared PyOxigraph store.

        Parameters
        ----------
        rules_path : Path
            Path to N3 rules file

        Returns
        -------
        dict[str, Any]
            Dictionary of inferred deltas
        """
        # Load rules
        rules = rules_path.read_text(encoding="utf-8")

        # Load rules into HybridEngine (HybridEngine pattern)
        # The codebase data is already in the store
        self.engine.engine.load_data(rules, trigger_hooks=False)

        # Apply physics (rules) using HybridEngine pattern
        result = self.engine.engine.apply_physics()

        if not result.success:
            return {"error": result.error or "Reasoning failed"}

        # Query the store for inferred deltas
        deltas = self._query_deltas()

        return deltas

    def _query_deltas(self) -> dict[str, Any]:
        """Query store for inferred delta triples.

        Queries the shared PyOxigraph store for porting relationships
        inferred by N3 rules.

        Returns
        -------
        dict[str, Any]
            Parsed deltas from store
        """
        deltas: dict[str, Any] = {
            "missing_classes": [],
            "missing_methods": [],
            "signature_mismatches": [],
            "semantic_deltas": [],
        }

        # Query for missing classes
        missing_class_query = """
        PREFIX port: <http://kgcl.dev/ontology/porting#>
        PREFIX code: <http://kgcl.dev/ontology/codebase#>

        SELECT ?class ?name
        WHERE {
            ?class port:status "missing" .
            ?class code:name ?name .
        }
        """

        for solution in self.engine.codebase.store.query(missing_class_query):
            deltas["missing_classes"].append(
                {
                    "uri": str(solution["class"]),
                    "name": str(solution["name"]),
                }
            )

        # Query for missing methods
        missing_method_query = """
        PREFIX port: <http://kgcl.dev/ontology/porting#>
        PREFIX code: <http://kgcl.dev/ontology/codebase#>

        SELECT ?method ?name
        WHERE {
            ?method port:status "missing" .
            ?method code:name ?name .
        }
        """

        for solution in self.engine.codebase.store.query(missing_method_query):
            deltas["missing_methods"].append(
                {
                    "uri": str(solution["method"]),
                    "name": str(solution["name"]),
                }
            )

        return deltas

