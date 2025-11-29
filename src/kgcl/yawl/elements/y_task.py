"""Task in YAWL net with split/join semantics (mirrors Java YTask).

Tasks are transitions in the Petri net. Unlike pure Petri nets,
YAWL tasks have split/join behavior as PROPERTIES, not separate elements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_multi_instance import YMultiInstanceAttributes


class SplitType(Enum):
    """Type of split behavior on outgoing flows.

    Attributes
    ----------
    AND : auto
        Fire ALL outgoing flows (parallel split)
    XOR : auto
        Fire exactly ONE flow (exclusive choice)
    OR : auto
        Fire ONE OR MORE flows (multi-choice)
    """

    AND = auto()
    XOR = auto()
    OR = auto()


class JoinType(Enum):
    """Type of join behavior on incoming flows.

    Attributes
    ----------
    AND : auto
        Wait for ALL incoming tokens (synchronization)
    XOR : auto
        Fire on ANY ONE incoming token (simple merge)
    OR : auto
        Fire when no more tokens expected (structured discriminator)
    """

    AND = auto()
    XOR = auto()
    OR = auto()


class TaskStatus(Enum):
    """Status of a task instance during execution.

    Attributes
    ----------
    ENABLED : auto
        Task can fire (all join conditions met)
    FIRED : auto
        Task has started execution
    EXECUTING : auto
        Task is currently executing
    COMPLETED : auto
        Task execution completed successfully
    CANCELLED : auto
        Task was cancelled (via cancellation region)
    """

    ENABLED = auto()
    FIRED = auto()
    EXECUTING = auto()
    COMPLETED = auto()
    CANCELLED = auto()


@dataclass
class YTask:
    """Task in YAWL net with split/join semantics (mirrors Java YTask).

    Tasks are transitions in the underlying Petri net. Unlike pure Petri
    nets, YAWL tasks have split/join behavior as PROPERTIES rather than
    separate gateway elements. This is a key differentiator from BPMN.

    Parameters
    ----------
    id : str
        Unique identifier for this task
    name : str
        Human-readable name
    split_type : SplitType
        Split behavior on outgoing flows
    join_type : JoinType
        Join behavior on incoming flows
    net_id : str | None
        ID of containing net (set when added to net)
    preset_flows : list[str]
        IDs of incoming flows (from conditions)
    postset_flows : list[str]
        IDs of outgoing flows (to conditions)
    flow_predicates : dict[str, str]
        Predicates for XOR/OR splits (flow_id → predicate string)
    cancellation_set : set[str]
        IDs of elements to cancel when this task fires
    multi_instance : YMultiInstanceAttributes | None
        Multi-instance configuration (if applicable)
    decomposition_id : str | None
        ID of decomposition (what the task actually does)

    Examples
    --------
    >>> task = YTask(id="A", split_type=SplitType.AND, join_type=JoinType.XOR)
    >>> task.is_and_split()
    True
    >>> task.is_xor_join()
    True
    """

    id: str
    name: str = ""
    split_type: SplitType = SplitType.AND
    join_type: JoinType = JoinType.XOR
    net_id: str | None = None

    # Flow connections
    preset_flows: list[str] = field(default_factory=list)
    postset_flows: list[str] = field(default_factory=list)

    # Flow predicates (XOR/OR splits evaluate these)
    flow_predicates: dict[str, str] = field(default_factory=dict)

    # Cancellation region (reset net semantics)
    cancellation_set: set[str] = field(default_factory=set)

    # Multi-instance configuration
    multi_instance: YMultiInstanceAttributes | None = None

    # Decomposition (what the task actually does)
    decomposition_id: str | None = None

    def is_and_split(self) -> bool:
        """Check if task has AND-split behavior.

        Returns
        -------
        bool
            True if split_type is AND
        """
        return self.split_type == SplitType.AND

    def is_xor_split(self) -> bool:
        """Check if task has XOR-split behavior.

        Returns
        -------
        bool
            True if split_type is XOR
        """
        return self.split_type == SplitType.XOR

    def is_or_split(self) -> bool:
        """Check if task has OR-split behavior.

        Returns
        -------
        bool
            True if split_type is OR
        """
        return self.split_type == SplitType.OR

    def is_and_join(self) -> bool:
        """Check if task has AND-join behavior.

        Returns
        -------
        bool
            True if join_type is AND
        """
        return self.join_type == JoinType.AND

    def is_xor_join(self) -> bool:
        """Check if task has XOR-join behavior.

        Returns
        -------
        bool
            True if join_type is XOR
        """
        return self.join_type == JoinType.XOR

    def is_or_join(self) -> bool:
        """Check if task has OR-join behavior.

        Returns
        -------
        bool
            True if join_type is OR
        """
        return self.join_type == JoinType.OR

    def has_cancellation_set(self) -> bool:
        """Check if task has a cancellation set.

        Returns
        -------
        bool
            True if cancellation_set is not empty
        """
        return len(self.cancellation_set) > 0

    def is_multi_instance(self) -> bool:
        """Check if task is a multi-instance task.

        Returns
        -------
        bool
            True if multi_instance is configured
        """
        return self.multi_instance is not None

    def get_display_name(self) -> str:
        """Get display name (name if set, else ID).

        Returns
        -------
        str
            Name or ID for display
        """
        return self.name if self.name else self.id

    def set_predicate(self, flow_id: str, predicate: str) -> None:
        """Set predicate for an outgoing flow.

        Parameters
        ----------
        flow_id : str
            ID of the flow
        predicate : str
            Predicate expression (evaluated for XOR/OR splits)
        """
        self.flow_predicates[flow_id] = predicate

    def get_predicate(self, flow_id: str) -> str | None:
        """Get predicate for an outgoing flow.

        Parameters
        ----------
        flow_id : str
            ID of the flow

        Returns
        -------
        str | None
            Predicate expression or None if not set
        """
        return self.flow_predicates.get(flow_id)

    def add_to_cancellation_set(self, element_id: str) -> None:
        """Add element to cancellation set.

        Parameters
        ----------
        element_id : str
            ID of element (condition or task) to add
        """
        self.cancellation_set.add(element_id)

    def __hash__(self) -> int:
        """Hash by ID for use in sets/dicts."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Equality by ID."""
        if not isinstance(other, YTask):
            return NotImplemented
        return self.id == other.id
