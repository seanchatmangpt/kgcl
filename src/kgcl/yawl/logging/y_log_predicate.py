"""Log predicate for conditional logging (mirrors Java YLogPredicate).

Defines predicates for when to log data items (start/completion).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from xml.etree import ElementTree as ET

from kgcl.yawl.util import string_util

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_decomposition import YDecomposition, YParameter
    from kgcl.yawl.engine.y_work_item import YWorkItem


@dataclass
class YLogPredicate:
    """Log predicate (mirrors Java YLogPredicate).

    Defines predicates for conditional logging of data items.
    Contains start and completion predicates that can be evaluated
    against work items, decompositions, or parameters.

    Parameters
    ----------
    start_predicate : str | None
        Predicate for start logging
    completion_predicate : str | None
        Predicate for completion logging

    Examples
    --------
    >>> predicate = YLogPredicate(start_predicate="status='active'")
    >>> predicate.get_start_predicate()
    "status='active'"
    """

    start_predicate: str | None = None
    completion_predicate: str | None = None

    def __init__(
        self,
        start_predicate: str | None = None,
        completion_predicate: str | None = None,
        xml: ET.Element | None = None,
        namespace: str | None = None,
    ) -> None:
        """Initialize log predicate.

        Parameters
        ----------
        start_predicate : str | None
            Start predicate
        completion_predicate : str | None
            Completion predicate
        xml : ET.Element | None
            XML element to parse from
        namespace : str | None
            XML namespace (optional)
        """
        if xml is not None:
            if namespace:
                self.from_xml(xml, namespace)
            else:
                self.from_xml(xml)
        else:
            self.start_predicate = start_predicate
            self.completion_predicate = completion_predicate

    def get_start_predicate(self) -> str | None:
        """Get start predicate.

        Java signature: String getStartPredicate()

        Returns
        -------
        str | None
            Start predicate
        """
        return self.start_predicate

    def set_start_predicate(self, predicate: str) -> None:
        """Set start predicate.

        Java signature: void setStartPredicate(String predicate)

        Parameters
        ----------
        predicate : str
            Start predicate
        """
        self.start_predicate = predicate

    def get_completion_predicate(self) -> str | None:
        """Get completion predicate.

        Java signature: String getCompletionPredicate()

        Returns
        -------
        str | None
            Completion predicate
        """
        return self.completion_predicate

    def set_completion_predicate(self, predicate: str) -> None:
        """Set completion predicate.

        Java signature: void setCompletionPredicate(String predicate)

        Parameters
        ----------
        predicate : str
            Completion predicate
        """
        self.completion_predicate = predicate

    def get_parsed_start_predicate(
        self, work_item: Any | None = None, decomp: Any | None = None, param: Any | None = None
    ) -> str | None:
        """Get parsed start predicate.

        Java signature: String getParsedStartPredicate(YWorkItem workItem)
        Java signature: String getParsedStartPredicate(YDecomposition decomp)
        Java signature: String getParsedStartPredicate(YParameter param)

        Parameters
        ----------
        work_item : Any | None
            Work item to parse against
        decomp : Any | None
            Decomposition to parse against
        param : Any | None
            Parameter to parse against

        Returns
        -------
        str | None
            Parsed start predicate or None
        """
        if self.start_predicate is None:
            return None

        if work_item is not None:
            from kgcl.yawl.logging.y_log_predicate_work_item_parser import YLogPredicateWorkItemParser

            return YLogPredicateWorkItemParser(work_item).parse(self.start_predicate)
        elif decomp is not None:
            from kgcl.yawl.logging.y_log_predicate_decomposition_parser import YLogPredicateDecompositionParser

            return YLogPredicateDecompositionParser(decomp).parse(self.start_predicate)
        elif param is not None:
            from kgcl.yawl.logging.y_log_predicate_parameter_parser import YLogPredicateParameterParser

            return YLogPredicateParameterParser(param).parse(self.start_predicate)

        return self.start_predicate

    def get_parsed_completion_predicate(
        self, work_item: Any | None = None, decomp: Any | None = None, param: Any | None = None
    ) -> str | None:
        """Get parsed completion predicate.

        Java signature: String getParsedCompletionPredicate(YWorkItem workItem)
        Java signature: String getParsedCompletionPredicate(YDecomposition decomp)
        Java signature: String getParsedCompletionPredicate(YParameter param)

        Parameters
        ----------
        work_item : Any | None
            Work item to parse against
        decomp : Any | None
            Decomposition to parse against
        param : Any | None
            Parameter to parse against

        Returns
        -------
        str | None
            Parsed completion predicate or None
        """
        if self.completion_predicate is None:
            return None

        if work_item is not None:
            from kgcl.yawl.logging.y_log_predicate_work_item_parser import YLogPredicateWorkItemParser

            return YLogPredicateWorkItemParser(work_item).parse(self.completion_predicate)
        elif decomp is not None:
            from kgcl.yawl.logging.y_log_predicate_decomposition_parser import YLogPredicateDecompositionParser

            return YLogPredicateDecompositionParser(decomp).parse(self.completion_predicate)
        elif param is not None:
            from kgcl.yawl.logging.y_log_predicate_parameter_parser import YLogPredicateParameterParser

            return YLogPredicateParameterParser(param).parse(self.completion_predicate)

        return self.completion_predicate

    def from_xml(self, xml: ET.Element, namespace: str | None = None) -> None:
        """Parse from XML element.

        Java signature: void fromXML(Element xml)
        Java signature: void fromXML(Element xml, Namespace ns)

        Parameters
        ----------
        xml : ET.Element
            XML element
        namespace : str | None
            XML namespace (optional)
        """
        if namespace:
            self.start_predicate = xml.findtext(f"{{{namespace}}}start") or xml.findtext("start")
            self.completion_predicate = xml.findtext(f"{{{namespace}}}completion") or xml.findtext("completion")
        else:
            self.start_predicate = xml.findtext("start")
            self.completion_predicate = xml.findtext("completion")

    def to_xml(self) -> str:
        """Convert to XML.

        Java signature: String toXML()

        Returns
        -------
        str
            XML representation or empty string if both predicates are None
        """
        if self.start_predicate is None and self.completion_predicate is None:
            return ""

        xml_parts: list[str] = []
        xml_parts.append("<logPredicate>")
        if self.start_predicate is not None:
            xml_parts.append(string_util.wrap_escaped(self.start_predicate, "start"))
        if self.completion_predicate is not None:
            xml_parts.append(string_util.wrap_escaped(self.completion_predicate, "completion"))
        xml_parts.append("</logPredicate>")
        return "".join(xml_parts)

    def __eq__(self, other: object) -> bool:
        """Equality comparison.

        Java signature: boolean equals(Object o)

        Parameters
        ----------
        other : object
            Other object to compare

        Returns
        -------
        bool
            True if equal
        """
        if not isinstance(other, YLogPredicate):
            return False

        start_eq = (self.start_predicate is None and other.start_predicate is None) or (
            self.start_predicate is not None
            and other.start_predicate is not None
            and self.start_predicate == other.start_predicate
        )

        completion_eq = (self.completion_predicate is None and other.completion_predicate is None) or (
            self.completion_predicate is not None
            and other.completion_predicate is not None
            and self.completion_predicate == other.completion_predicate
        )

        return start_eq and completion_eq

    def __hash__(self) -> int:
        """Hash code.

        Java signature: int hashCode()

        Returns
        -------
        int
            Hash code
        """
        start_hash = hash(self.start_predicate) if self.start_predicate is not None else 17
        completion_hash = hash(self.completion_predicate) if self.completion_predicate is not None else 33
        return 17 * start_hash * completion_hash
