"""Log predicate parser for decompositions (mirrors Java YLogPredicateDecompositionParser).

Parses log predicates against decomposition context.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kgcl.yawl.util.parser import YPredicateParser

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_decomposition import YDecomposition


class YLogPredicateDecompositionParser(YPredicateParser):
    """Parser for log predicates against decompositions (mirrors Java YLogPredicateDecompositionParser).

    Extends YPredicateParser to resolve decomposition-specific predicates.

    Parameters
    ----------
    decomp : YDecomposition
        Decomposition to parse predicates against

    Examples
    --------
    >>> from kgcl.yawl.elements.y_decomposition import YDecomposition
    >>> decomp = YDecomposition(id="OrderProcess")
    >>> parser = YLogPredicateDecompositionParser(decomp)
    >>> result = parser.parse("${decomp:name}")
    >>> result == "OrderProcess"
    True
    """

    def __init__(self, decomp: YDecomposition) -> None:
        """Initialize parser with decomposition.

        Java signature: YLogPredicateDecompositionParser(YDecomposition decomp)

        Parameters
        ----------
        decomp : YDecomposition
            Decomposition to parse against
        """
        super().__init__()
        self._decomp = decomp

    def value_of(self, predicate: str) -> str:
        """Resolve predicate value.

        Java signature: protected String valueOf(String predicate)

        Parameters
        ----------
        predicate : str
            Predicate string to resolve

        Returns
        -------
        str
            Resolved value or "n/a" if not found
        """
        resolved = "n/a"

        if predicate == "${decomp:name}":
            resolved = self._decomp.get_id() if hasattr(self._decomp, "get_id") else self._decomp.id
        elif predicate == "${decomp:spec:name}":
            spec = self._decomp.get_specification() if hasattr(self._decomp, "get_specification") else None
            resolved = (
                spec.get_name()
                if spec and hasattr(spec, "get_name")
                else (spec.name if spec and hasattr(spec, "name") else "n/a")
            )
        elif predicate == "${decomp:inputs}":
            param_names = (
                self._decomp.get_input_parameter_names() if hasattr(self._decomp, "get_input_parameter_names") else []
            )
            resolved = self.names_to_csv(param_names)
        elif predicate == "${decomp:outputs}":
            param_names = (
                self._decomp.get_output_parameter_names() if hasattr(self._decomp, "get_output_parameter_names") else []
            )
            resolved = self.names_to_csv(param_names)
        elif predicate.startswith("${decomp:attribute:"):
            attrs = self._decomp.get_attributes() if hasattr(self._decomp, "get_attributes") else None
            resolved = self.get_attribute_value(attrs, predicate) if attrs else "n/a"
        else:
            resolved = super().value_of(predicate)

        if resolved is None or resolved == "null" or resolved == predicate:
            resolved = "n/a"

        return resolved
