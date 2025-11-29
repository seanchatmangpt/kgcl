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

    # Token storage (maps identifier ID -> count)
    # Java YAWL stores tokens directly in conditions
    _tokens: dict[str, int] = field(default_factory=dict, repr=False)

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

    # =========================================================================
    # Token Management (Java YAWL YCondition methods)
    # =========================================================================

    def add(self, identifier_id: str, amount: int = 1) -> None:
        """Add token(s) to this condition.

        Java signature: void add(YIdentifier identifier)

        Parameters
        ----------
        identifier_id : str
            Case identifier ID
        amount : int
            Number of tokens to add (default 1)

        Examples
        --------
        >>> cond = YCondition(id="c1")
        >>> cond.add("case-001")
        >>> cond.contains("case-001")
        True
        """
        current = self._tokens.get(identifier_id, 0)
        self._tokens[identifier_id] = current + amount

    def remove(self, identifier_id: str, amount: int = 1) -> None:
        """Remove token(s) from this condition.

        Java signature: void remove(YIdentifier identifier, int amount)

        Parameters
        ----------
        identifier_id : str
            Case identifier ID
        amount : int
            Number of tokens to remove (default 1)

        Raises
        ------
        ValueError
            If trying to remove more tokens than exist

        Examples
        --------
        >>> cond = YCondition(id="c1")
        >>> cond.add("case-001")
        >>> cond.remove("case-001")
        >>> cond.contains("case-001")
        False
        """
        current = self._tokens.get(identifier_id, 0)
        if current < amount:
            raise ValueError(f"Cannot remove {amount} tokens, only {current} exist for {identifier_id}")

        new_count = current - amount
        if new_count == 0:
            del self._tokens[identifier_id]
        else:
            self._tokens[identifier_id] = new_count

    def contains(self, identifier_id: str) -> bool:
        """Check if condition contains token for identifier.

        Java signature: boolean contains(YIdentifier identifier)

        Parameters
        ----------
        identifier_id : str
            Case identifier ID

        Returns
        -------
        bool
            True if token exists

        Examples
        --------
        >>> cond = YCondition(id="c1")
        >>> cond.add("case-001")
        >>> cond.contains("case-001")
        True
        >>> cond.contains("case-002")
        False
        """
        return identifier_id in self._tokens

    def get_identifiers(self) -> list[str]:
        """Get all case identifiers with tokens in this condition.

        Java signature: List getIdentifiers()

        Returns
        -------
        list[str]
            List of case identifier IDs

        Examples
        --------
        >>> cond = YCondition(id="c1")
        >>> cond.add("case-001")
        >>> cond.add("case-002")
        >>> sorted(cond.get_identifiers())
        ['case-001', 'case-002']
        """
        return list(self._tokens.keys())

    def get_amount(self, identifier_id: str) -> int:
        """Get number of tokens for identifier.

        Java signature: int getAmount(YIdentifier identifier)

        Parameters
        ----------
        identifier_id : str
            Case identifier ID

        Returns
        -------
        int
            Number of tokens (0 if none)

        Examples
        --------
        >>> cond = YCondition(id="c1")
        >>> cond.add("case-001", 3)
        >>> cond.get_amount("case-001")
        3
        >>> cond.get_amount("case-002")
        0
        """
        return self._tokens.get(identifier_id, 0)

    def contains_identifier(self) -> bool:
        """Check if condition contains any tokens.

        Java signature: boolean containsIdentifier()

        Returns
        -------
        bool
            True if any tokens exist

        Examples
        --------
        >>> cond = YCondition(id="c1")
        >>> cond.contains_identifier()
        False
        >>> cond.add("case-001")
        >>> cond.contains_identifier()
        True
        """
        return len(self._tokens) > 0

    def remove_all(self) -> None:
        """Remove all tokens from this condition.

        Java signature: void removeAll()

        Examples
        --------
        >>> cond = YCondition(id="c1")
        >>> cond.add("case-001")
        >>> cond.add("case-002")
        >>> cond.remove_all()
        >>> cond.contains_identifier()
        False
        """
        self._tokens.clear()
