"""Worklet models (mirrors Java worklet service).

Defines worklet structures, RDR tree nodes, and rule representations
for the YAWL worklet exception handling service.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any


class WorkletType(Enum):
    """Type of worklet.

    Attributes
    ----------
    CASE_EXCEPTION : auto
        Handles case-level exceptions
    ITEM_EXCEPTION : auto
        Handles work item exceptions
    SELECTION : auto
        Dynamic worklet selection
    EXTERNAL_EXCEPTION : auto
        Handles external service exceptions
    TIMEOUT : auto
        Handles timeout exceptions
    CONSTRAINT_VIOLATION : auto
        Handles constraint violations
    """

    CASE_EXCEPTION = auto()
    ITEM_EXCEPTION = auto()
    SELECTION = auto()
    EXTERNAL_EXCEPTION = auto()
    TIMEOUT = auto()
    CONSTRAINT_VIOLATION = auto()


class WorkletStatus(Enum):
    """Status of a worklet execution.

    Attributes
    ----------
    PENDING : auto
        Worklet is pending
    RUNNING : auto
        Worklet is executing
    COMPLETED : auto
        Worklet completed successfully
    FAILED : auto
        Worklet failed
    CANCELLED : auto
        Worklet was cancelled
    """

    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class Worklet:
    """A worklet definition (mirrors Java Worklet).

    A worklet is a small, self-contained workflow that handles
    exceptions or provides dynamic behavior.

    Parameters
    ----------
    id : str
        Unique identifier
    name : str
        Worklet name
    worklet_type : WorkletType
        Type of worklet
    specification_uri : str | None
        URI of the specification to execute
    description : str
        Worklet description
    enabled : bool
        Whether worklet is enabled
    created : datetime
        Creation timestamp
    modified : datetime | None
        Last modification timestamp
    version : int
        Version number
    parameters : dict[str, Any]
        Worklet parameters
    """

    id: str
    name: str
    worklet_type: WorkletType = WorkletType.CASE_EXCEPTION
    specification_uri: str | None = None
    description: str = ""
    enabled: bool = True
    created: datetime = field(default_factory=datetime.now)
    modified: datetime | None = None
    version: int = 1
    parameters: dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        """Hash by ID."""
        return hash(self.id)


@dataclass
class WorkletCase:
    """A running worklet case.

    Tracks the execution of a worklet instance.

    Parameters
    ----------
    id : str
        Unique case ID
    worklet_id : str
        ID of the worklet definition
    parent_case_id : str
        ID of the parent case
    parent_work_item_id : str | None
        ID of the parent work item (for item exceptions)
    status : WorkletStatus
        Current status
    started : datetime
        Start timestamp
    completed : datetime | None
        Completion timestamp
    exception_type : str
        Type of exception being handled
    exception_data : dict[str, Any]
        Exception context data
    result_data : dict[str, Any]
        Result data from worklet
    """

    id: str
    worklet_id: str
    parent_case_id: str
    parent_work_item_id: str | None = None
    status: WorkletStatus = WorkletStatus.PENDING
    started: datetime = field(default_factory=datetime.now)
    completed: datetime | None = None
    exception_type: str = ""
    exception_data: dict[str, Any] = field(default_factory=dict)
    result_data: dict[str, Any] = field(default_factory=dict)

    def start(self) -> None:
        """Start the worklet case."""
        self.status = WorkletStatus.RUNNING

    def complete(self, result_data: dict[str, Any] | None = None) -> None:
        """Complete the worklet case.

        Parameters
        ----------
        result_data : dict[str, Any] | None
            Result data
        """
        self.status = WorkletStatus.COMPLETED
        self.completed = datetime.now()
        if result_data:
            self.result_data = result_data

    def fail(self, error: str) -> None:
        """Mark worklet case as failed.

        Parameters
        ----------
        error : str
            Error message
        """
        self.status = WorkletStatus.FAILED
        self.completed = datetime.now()
        self.result_data["error"] = error

    def cancel(self) -> None:
        """Cancel the worklet case."""
        self.status = WorkletStatus.CANCELLED
        self.completed = datetime.now()

    def __hash__(self) -> int:
        """Hash by ID."""
        return hash(self.id)


@dataclass
class RDRNode:
    """A node in the Ripple Down Rules tree.

    RDR trees provide incremental knowledge acquisition for
    exception handling decisions.

    Parameters
    ----------
    id : str
        Unique node ID
    condition : str
        Condition expression to evaluate
    conclusion : str | None
        Conclusion (worklet ID to execute) if condition is true
    true_child : RDRNode | None
        Child node for true condition
    false_child : RDRNode | None
        Child node for false condition
    parent : RDRNode | None
        Parent node
    cornerstone_case : dict[str, Any] | None
        The case that created this rule
    description : str
        Rule description
    created : datetime
        Creation timestamp
    """

    id: str
    condition: str = "true"
    conclusion: str | None = None
    true_child: RDRNode | None = None
    false_child: RDRNode | None = None
    parent: RDRNode | None = None
    cornerstone_case: dict[str, Any] | None = None
    description: str = ""
    created: datetime = field(default_factory=datetime.now)

    def is_leaf(self) -> bool:
        """Check if this is a leaf node.

        Returns
        -------
        bool
            True if no children
        """
        return self.true_child is None and self.false_child is None

    def has_conclusion(self) -> bool:
        """Check if node has a conclusion.

        Returns
        -------
        bool
            True if conclusion set
        """
        return self.conclusion is not None

    def add_true_child(self, node: RDRNode) -> None:
        """Add child for true condition.

        Parameters
        ----------
        node : RDRNode
            Child node
        """
        self.true_child = node
        node.parent = self

    def add_false_child(self, node: RDRNode) -> None:
        """Add child for false condition.

        Parameters
        ----------
        node : RDRNode
            Child node
        """
        self.false_child = node
        node.parent = self

    def __hash__(self) -> int:
        """Hash by ID."""
        return hash(self.id)


@dataclass
class RDRTree:
    """A Ripple Down Rules tree.

    The tree is traversed to find the appropriate worklet for
    a given exception context.

    Parameters
    ----------
    id : str
        Unique tree ID
    name : str
        Tree name
    root : RDRNode
        Root node
    task_id : str | None
        Task ID this tree applies to (None for case-level)
    exception_type : str
        Type of exception handled
    nodes : dict[str, RDRNode]
        All nodes by ID for quick lookup
    """

    id: str
    name: str
    root: RDRNode = field(default_factory=lambda: RDRNode(id="root"))
    task_id: str | None = None
    exception_type: str = "default"
    nodes: dict[str, RDRNode] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Register root node."""
        if self.root.id not in self.nodes:
            self.nodes[self.root.id] = self.root

    def add_node(self, node: RDRNode) -> None:
        """Add a node to the tree.

        Parameters
        ----------
        node : RDRNode
            Node to add
        """
        self.nodes[node.id] = node

    def get_node(self, node_id: str) -> RDRNode | None:
        """Get node by ID.

        Parameters
        ----------
        node_id : str
            Node ID

        Returns
        -------
        RDRNode | None
            Node or None
        """
        return self.nodes.get(node_id)

    def count_nodes(self) -> int:
        """Count total nodes.

        Returns
        -------
        int
            Node count
        """
        return len(self.nodes)

    def __hash__(self) -> int:
        """Hash by ID."""
        return hash(self.id)
