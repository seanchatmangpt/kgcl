"""Place in YAWL net (mirrors Java YCondition).

Conditions are places in the underlying Petri net that hold tokens
and connect to tasks via flows.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

from kgcl.yawl.elements.y_identifier import YIdentifier

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_net import YNet
    from kgcl.yawl.engine.y_engine import YPersistenceManager, YVerificationHandler


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
    documentation: str = ""
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

    def add(self, identifier: YIdentifier | str, amount: int = 1, pmgr: YPersistenceManager | None = None) -> None:
        """Add token(s) to this condition.

        Java signature: void add(YIdentifier identifier)
        Java signature: void add(YPersistenceManager pmgr, YIdentifier identifier)

        Parameters
        ----------
        identifier : YIdentifier | str
            Case identifier or identifier ID string
        amount : int
            Number of tokens to add (default 1)
        pmgr : YPersistenceManager | None
            Optional persistence manager for persistence operations

        Examples
        --------
        >>> cond = YCondition(id="c1")
        >>> cond.add("case-001")
        >>> cond.contains("case-001")
        True
        >>> identifier = YIdentifier(id="case-002")
        >>> cond.add(identifier)
        >>> cond.contains(identifier)
        True
        """
        identifier_id = identifier.id if isinstance(identifier, YIdentifier) else identifier
        current = self._tokens.get(identifier_id, 0)
        self._tokens[identifier_id] = current + amount

        if pmgr:
            pmgr.update_object(self)

    def remove(self, identifier: YIdentifier | str, amount: int = 1, pmgr: YPersistenceManager | None = None) -> None:
        """Remove token(s) from this condition.

        Java signature: void remove(YIdentifier identifier, int amount)
        Java signature: void remove(YPersistenceManager pmgr, YIdentifier identifier, int amount)

        Parameters
        ----------
        identifier : YIdentifier | str
            Case identifier or identifier ID string
        amount : int
            Number of tokens to remove (default 1)
        pmgr : YPersistenceManager | None
            Optional persistence manager for persistence operations

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
        identifier_id = identifier.id if isinstance(identifier, YIdentifier) else identifier
        current = self._tokens.get(identifier_id, 0)
        if current < amount:
            raise ValueError(f"Cannot remove {amount} tokens, only {current} exist for {identifier_id}")

        new_count = current - amount
        if new_count == 0:
            del self._tokens[identifier_id]
        else:
            self._tokens[identifier_id] = new_count

        if pmgr:
            pmgr.update_object(self)

    def contains(self, identifier: YIdentifier | str) -> bool:
        """Check if condition contains token for identifier.

        Java signature: boolean contains(YIdentifier identifier)

        Parameters
        ----------
        identifier : YIdentifier | str
            Case identifier or identifier ID string

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
        identifier_id = identifier.id if isinstance(identifier, YIdentifier) else identifier
        return identifier_id in self._tokens

    def get_identifiers(self) -> list[YIdentifier]:
        """Get all identifiers in this condition.

        Java signature: List getIdentifiers()

        Returns
        -------
        list[YIdentifier]
            List of identifiers (created from stored IDs)

        Examples
        --------
        >>> cond = YCondition(id="c1")
        >>> cond.add("case-001")
        >>> cond.add("case-002")
        >>> identifiers = cond.get_identifiers()
        >>> len(identifiers)
        2
        """
        return [YIdentifier(id=identifier_id) for identifier_id in self._tokens.keys()]

    def get_amount(self, identifier: YIdentifier | str) -> int:
        """Get number of tokens for identifier.

        Java signature: int getAmount(YIdentifier identifier)

        Parameters
        ----------
        identifier : YIdentifier | str
            Case identifier or identifier ID string

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
        identifier_id = identifier.id if isinstance(identifier, YIdentifier) else identifier
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

    def remove_all(self, identifier: YIdentifier | str | None = None, pmgr: YPersistenceManager | None = None) -> None:
        """Remove all tokens (optionally matching identifier).

        Java signature: void removeAll()
        Java signature: void removeAll(YPersistenceManager pmgr)
        Java signature: void removeAll(YIdentifier identifier)
        Java signature: void removeAll(YPersistenceManager pmgr, YIdentifier identifier)

        Parameters
        ----------
        identifier : YIdentifier | str | None
            If provided, remove all matching this identifier.
            If None, remove all tokens.
        pmgr : YPersistenceManager | None
            Optional persistence manager for persistence operations

        Examples
        --------
        >>> cond = YCondition(id="c1")
        >>> cond.add("case-001", 3)
        >>> cond.add("case-002", 2)
        >>> cond.remove_all("case-001")
        >>> cond.contains("case-001")
        False
        >>> cond.contains("case-002")
        True
        """
        if identifier is not None:
            identifier_id = identifier.id if isinstance(identifier, YIdentifier) else identifier
            if identifier_id in self._tokens:
                del self._tokens[identifier_id]
        else:
            self._tokens.clear()

        if pmgr:
            pmgr.update_object(self)

    def remove_one(
        self, identifier: YIdentifier | str | None = None, pmgr: YPersistenceManager | None = None
    ) -> YIdentifier | None:
        """Remove one token (optionally matching identifier).

        Java signature: YIdentifier removeOne()
        Java signature: YIdentifier removeOne(YPersistenceManager pmgr)
        Java signature: void removeOne(YIdentifier identifier)
        Java signature: void removeOne(YPersistenceManager pmgr, YIdentifier identifier)

        Parameters
        ----------
        identifier : YIdentifier | str | None
            If provided, remove one matching this identifier.
            If None, remove any one token.
        pmgr : YPersistenceManager | None
            Optional persistence manager for persistence operations

        Returns
        -------
        YIdentifier | None
            The removed identifier, or None if none removed

        Examples
        --------
        >>> cond = YCondition(id="c1")
        >>> cond.add("case-001", 3)
        >>> removed = cond.remove_one()
        >>> removed is not None
        True
        >>> cond.get_amount("case-001")
        2
        """
        if identifier is not None:
            identifier_id = identifier.id if isinstance(identifier, YIdentifier) else identifier
            if identifier_id in self._tokens:
                self.remove(identifier_id, 1, pmgr)
                return YIdentifier(id=identifier_id) if isinstance(identifier, str) else identifier
            return None

        # Remove any one token
        if not self._tokens:
            return None

        identifier_id = next(iter(self._tokens.keys()))
        self.remove(identifier_id, 1, pmgr)
        return YIdentifier(id=identifier_id)

    # =========================================================================
    # Additional Java YCondition methods
    # =========================================================================

    def set_implicit(self, is_implicit: bool) -> None:
        """Set whether this condition is implicit.

        Java signature: void setImplicit(boolean isImplicit)

        Parameters
        ----------
        is_implicit : bool
            True if condition is implicit

        Examples
        --------
        >>> cond = YCondition(id="c1")
        >>> cond.set_implicit(True)
        >>> cond.is_implicit()
        True
        """
        if is_implicit:
            self.condition_type = ConditionType.IMPLICIT
        elif self.condition_type == ConditionType.IMPLICIT:
            self.condition_type = ConditionType.EXPLICIT

    def is_anonymous(self) -> bool:
        """Check if condition has no name (is anonymous).

        Java signature: boolean isAnonymous()

        Returns
        -------
        bool
            True if condition has no name

        Examples
        --------
        >>> cond = YCondition(id="c1")
        >>> cond.is_anonymous()
        True
        >>> cond.name = "MyCondition"
        >>> cond.is_anonymous()
        False
        """
        return not self.name or self.name.strip() == ""

    def clone(self) -> YCondition:
        """Create a deep copy of this condition.

        Java signature: Object clone()

        Returns
        -------
        YCondition
            Cloned condition with independent token storage

        Examples
        --------
        >>> cond = YCondition(id="c1")
        >>> cond.add("case-001")
        >>> cloned = cond.clone()
        >>> cloned.id == cond.id
        True
        >>> cloned._tokens is not cond._tokens
        True
        """
        cloned = deepcopy(self)
        # Ensure tokens are independent
        cloned._tokens = deepcopy(self._tokens)
        return cloned

    def verify(self, handler: YVerificationHandler) -> None:
        """Verify condition against YAWL semantics.

        Java signature: void verify(YVerificationHandler handler)

        Parameters
        ----------
        handler : YVerificationHandler
            Verification handler to report issues

        Examples
        --------
        >>> from kgcl.yawl.engine.y_engine import YVerificationHandler
        >>> cond = YCondition(id="")
        >>> handler = YVerificationHandler()
        >>> cond.verify(handler)
        >>> len(handler.errors) > 0
        True
        """
        if not self.id or self.id.strip() == "":
            handler.error(self, "Condition must have a non-empty ID")

    def to_xml(self) -> str:
        """Serialize condition to XML.

        Java signature: String toXML()

        Returns
        -------
        str
            XML representation of condition

        Examples
        --------
        >>> cond = YCondition(id="c1", name="Start")
        >>> xml = cond.to_xml()
        >>> "condition" in xml
        True
        >>> "c1" in xml
        True
        """
        # Determine tag based on condition type
        if self.is_input_condition():
            tag = "inputCondition"
        elif self.is_output_condition():
            tag = "outputCondition"
        else:
            tag = "condition"

        root = ET.Element(tag)
        root.set("id", self.id)

        if self.name:
            name_elem = ET.SubElement(root, "name")
            name_elem.text = self.name

        if self.documentation:
            doc_elem = ET.SubElement(root, "documentation")
            doc_elem.text = self.documentation

        return ET.tostring(root, encoding="unicode")
