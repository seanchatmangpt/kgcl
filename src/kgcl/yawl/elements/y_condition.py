"""Place in YAWL net (mirrors Java YCondition).

Conditions are places in the underlying Petri net that hold tokens
and connect to tasks via flows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class ConditionType(Enum):
    """Type of condition in a YAWL net.

    Attributes
    ----------
    INPUT : auto
        Start condition (unique input place)
    OUTPUT : auto
        End condition (unique output place)
    IMPLICIT : auto
        Implicit condition between directly connected tasks
    EXPLICIT : auto
        Explicitly defined intermediate condition
    """

    INPUT = auto()
    OUTPUT = auto()
    IMPLICIT = auto()
    EXPLICIT = auto()


@dataclass
class YCondition:
    """Place in YAWL net (mirrors Java YCondition).

    Conditions are places in the underlying Petri net. They hold tokens
    and connect to tasks via flows. Each workflow net has exactly one
    input condition and one output condition.

    Parameters
    ----------
    id : str
        Unique identifier for this condition
    name : str
        Human-readable name
    condition_type : ConditionType
        Type of condition (INPUT, OUTPUT, IMPLICIT, EXPLICIT)
    net_id : str | None
        ID of containing net (set when added to net)
    preset_flows : list[str]
        IDs of incoming flows
    postset_flows : list[str]
        IDs of outgoing flows

    Examples
    --------
    >>> start = YCondition(id="start", condition_type=ConditionType.INPUT)
    >>> start.is_input_condition()
    True
    """

    id: str
    name: str = ""
    condition_type: ConditionType = ConditionType.EXPLICIT
    net_id: str | None = None

    # Connected elements (populated during net construction)
    preset_flows: list[str] = field(default_factory=list)
    postset_flows: list[str] = field(default_factory=list)

    def is_input_condition(self) -> bool:
        """Check if this is the input (start) condition.

        Returns
        -------
        bool
            True if this is the input condition

        Examples
        --------
        >>> cond = YCondition(id="c1", condition_type=ConditionType.INPUT)
        >>> cond.is_input_condition()
        True
        """
        return self.condition_type == ConditionType.INPUT

    def is_output_condition(self) -> bool:
        """Check if this is the output (end) condition.

        Returns
        -------
        bool
            True if this is the output condition

        Examples
        --------
        >>> cond = YCondition(id="c1", condition_type=ConditionType.OUTPUT)
        >>> cond.is_output_condition()
        True
        """
        return self.condition_type == ConditionType.OUTPUT

    def is_implicit(self) -> bool:
        """Check if this is an implicit condition.

        Returns
        -------
        bool
            True if this is an implicit condition

        Examples
        --------
        >>> cond = YCondition(id="c1", condition_type=ConditionType.IMPLICIT)
        >>> cond.is_implicit()
        True
        """
        return self.condition_type == ConditionType.IMPLICIT

    def get_display_name(self) -> str:
        """Get display name (name if set, else ID).

        Returns
        -------
        str
            Name or ID for display

        Examples
        --------
        >>> YCondition(id="c1", name="Start").get_display_name()
        'Start'
        >>> YCondition(id="c1").get_display_name()
        'c1'
        """
        return self.name if self.name else self.id

    def __hash__(self) -> int:
        """Hash by ID for use in sets/dicts."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Equality by ID."""
        if not isinstance(other, YCondition):
            return NotImplemented
        return self.id == other.id
