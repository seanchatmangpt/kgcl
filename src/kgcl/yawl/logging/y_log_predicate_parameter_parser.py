"""Log predicate parser for parameters (mirrors Java YLogPredicateParameterParser).

Parses log predicates against parameter context.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kgcl.yawl.util.parser import YPredicateParser

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_decomposition import YParameter


class YLogPredicateParameterParser(YPredicateParser):
    """Parser for log predicates against parameters (mirrors Java YLogPredicateParameterParser).

    Extends YPredicateParser to resolve parameter-specific predicates.

    Parameters
    ----------
    param : YParameter
        Parameter to parse predicates against

    Examples
    --------
    >>> from kgcl.yawl.elements.y_decomposition import YParameter
    >>> param = YParameter(name="customerId", data_type="string")
    >>> parser = YLogPredicateParameterParser(param)
    >>> result = parser.parse("${parameter:name}")
    >>> result == "customerId"
    True
    """

    def __init__(self, param: YParameter) -> None:
        """Initialize parser with parameter.

        Java signature: YLogPredicateParameterParser(YParameter param)

        Parameters
        ----------
        param : YParameter
            Parameter to parse against
        """
        super().__init__()
        self._param = param

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

        if predicate == "${parameter:name}":
            resolved = (
                self._param.get_preferred_name() if hasattr(self._param, "get_preferred_name") else self._param.name
            )
        elif predicate == "${parameter:datatype}":
            resolved = (
                self._param.get_data_type_name()
                if hasattr(self._param, "get_data_type_name")
                else self._param.data_type
            )
        elif predicate == "${parameter:namespace}":
            resolved = (
                self._param.get_data_type_name_space()
                if hasattr(self._param, "get_data_type_name_space")
                else (self._param.namespace if hasattr(self._param, "namespace") else "")
            )
        elif predicate == "${parameter:doco}":
            resolved = (
                self._param.get_documentation()
                if hasattr(self._param, "get_documentation")
                else (self._param.documentation if hasattr(self._param, "documentation") else "")
            )
        elif predicate == "${parameter:usage}":
            resolved = self._param.get_direction() if hasattr(self._param, "get_direction") else "input"
        elif predicate == "${parameter:ordering}":
            resolved = str(
                self._param.get_ordering()
                if hasattr(self._param, "get_ordering")
                else (self._param.ordering if hasattr(self._param, "ordering") else 0)
            )
        elif predicate == "${parameter:decomposition}":
            decomp = (
                self._param.get_parent_decomposition() if hasattr(self._param, "get_parent_decomposition") else None
            )
            if decomp:
                resolved = decomp.get_id() if hasattr(decomp, "get_id") else decomp.id
        elif predicate == "${parameter:initialvalue}":
            resolved = (
                self._param.get_initial_value()
                if hasattr(self._param, "get_initial_value")
                else (
                    str(self._param.initial_value)
                    if hasattr(self._param, "initial_value") and self._param.initial_value
                    else ""
                )
            )
        elif predicate == "${parameter:defaultvalue}":
            resolved = (
                self._param.get_default_value()
                if hasattr(self._param, "get_default_value")
                else (
                    str(self._param.initial_value)
                    if hasattr(self._param, "initial_value") and self._param.initial_value
                    else ""
                )
            )
        elif predicate.startswith("${parameter:attribute:"):
            attrs = self._param.get_attributes() if hasattr(self._param, "get_attributes") else None
            resolved = self.get_attribute_value(attrs, predicate) if attrs else "n/a"
        else:
            resolved = super().value_of(predicate)

        if resolved is None or resolved == "null" or resolved == predicate:
            resolved = "n/a"

        return resolved
