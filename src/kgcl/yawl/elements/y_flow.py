"""Arc between elements in YAWL net (mirrors Java YFlow).

Flows connect conditions to tasks and tasks to conditions,
forming the structure of the workflow net.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class YFlow:
    """Arc between elements in YAWL net (mirrors Java YFlow).

    Flows are directed arcs that connect conditions to tasks
    (input arcs) or tasks to conditions (output arcs). They
    form the structure of the underlying Petri net.

    Parameters
    ----------
    id : str
        Unique identifier for this flow
    source_id : str
        ID of source element (condition or task)
    target_id : str
        ID of target element (condition or task)
    predicate : str | None
        XPath predicate for XOR/OR splits (evaluates to boolean)
    is_default : bool
        True if this is the default flow for XOR splits
    ordering : int
        Evaluation order for predicates (lower = earlier)

    Examples
    --------
    >>> flow = YFlow(id="f1", source_id="start", target_id="A")
    >>> flow.source_id
    'start'
    """

    id: str
    source_id: str
    target_id: str
    predicate: str | None = None
    is_default: bool = False
    ordering: int = 0

    def has_predicate(self) -> bool:
        """Check if flow has a routing predicate.

        Returns
        -------
        bool
            True if predicate is set

        Examples
        --------
        >>> YFlow(id="f1", source_id="A", target_id="B", predicate="amount > 100").has_predicate()
        True
        >>> YFlow(id="f2", source_id="A", target_id="C").has_predicate()
        False
        """
        return self.predicate is not None and self.predicate != ""

    def __hash__(self) -> int:
        """Hash by ID for use in sets/dicts."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Equality by ID."""
        if not isinstance(other, YFlow):
            return NotImplemented
        return self.id == other.id
