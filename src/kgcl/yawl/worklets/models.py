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


@dataclass(frozen=True)
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

    Examples
    --------
    >>> worklet = Worklet(id="wl-001", name="Retry Handler", worklet_type=WorkletType.ITEM_EXCEPTION)
    >>> worklet.id
    'wl-001'
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

    def __post_init__(self) -> None:
        """Validate worklet data."""
        if not self.id:
            raise ValueError("Worklet id cannot be empty")
        if not self.name:
            raise ValueError("Worklet name cannot be empty")
        if self.version < 1:
            raise ValueError("Worklet version must be >= 1")

    def __repr__(self) -> str:
        """Developer representation."""
        return (
            f"Worklet("
            f"id={self.id!r}, "
            f"name={self.name!r}, "
            f"worklet_type={self.worklet_type.name}, "
            f"enabled={self.enabled})"
        )

    def __str__(self) -> str:
        """Human-readable representation."""
        return f"Worklet(id={self.id}, name={self.name})"

    def __eq__(self, other: object) -> bool:
        """Equality comparison by ID."""
        if not isinstance(other, Worklet):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash by ID."""
        return hash(self.id)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns
        -------
        dict[str, Any]
            Dictionary representation
        """
        return {
            "id": self.id,
            "name": self.name,
            "worklet_type": self.worklet_type.name,
            "specification_uri": self.specification_uri,
            "description": self.description,
            "enabled": self.enabled,
            "created": self.created.isoformat(),
            "modified": self.modified.isoformat() if self.modified else None,
            "version": self.version,
            "parameters": self.parameters,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Worklet:
        """Create from dictionary.

        Parameters
        ----------
        data : dict[str, Any]
            Dictionary data

        Returns
        -------
        Worklet
            Worklet instance
        """
        created = (
            datetime.fromisoformat(data["created"])
            if isinstance(data.get("created"), str)
            else data.get("created", datetime.now())
        )
        modified = (
            datetime.fromisoformat(data["modified"])
            if isinstance(data.get("modified"), str) and data["modified"]
            else data.get("modified")
        )
        return cls(
            id=data["id"],
            name=data["name"],
            worklet_type=WorkletType[data.get("worklet_type", "CASE_EXCEPTION")],
            specification_uri=data.get("specification_uri"),
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            created=created,
            modified=modified,
            version=data.get("version", 1),
            parameters=data.get("parameters", {}),
        )


@dataclass
class WorkletCase:
    """A running worklet case.

    Tracks the execution of a worklet instance.
    Note: Not frozen due to mutating methods (start, complete, etc.).

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

    Examples
    --------
    >>> case = WorkletCase(id="case-001", worklet_id="wl-001", parent_case_id="parent-001")
    >>> case.start()
    >>> case.status
    <WorkletStatus.RUNNING: 2>
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

    def __post_init__(self) -> None:
        """Validate worklet case data."""
        if not self.id:
            raise ValueError("WorkletCase id cannot be empty")
        if not self.worklet_id:
            raise ValueError("WorkletCase worklet_id cannot be empty")
        if not self.parent_case_id:
            raise ValueError("WorkletCase parent_case_id cannot be empty")

    def __repr__(self) -> str:
        """Developer representation."""
        return f"WorkletCase(id={self.id!r}, worklet_id={self.worklet_id!r}, status={self.status.name})"

    def __str__(self) -> str:
        """Human-readable representation."""
        return f"WorkletCase(id={self.id}, status={self.status.name})"

    def __eq__(self, other: object) -> bool:
        """Equality comparison by ID."""
        if not isinstance(other, WorkletCase):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash by ID."""
        return hash(self.id)

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

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns
        -------
        dict[str, Any]
            Dictionary representation
        """
        return {
            "id": self.id,
            "worklet_id": self.worklet_id,
            "parent_case_id": self.parent_case_id,
            "parent_work_item_id": self.parent_work_item_id,
            "status": self.status.name,
            "started": self.started.isoformat(),
            "completed": self.completed.isoformat() if self.completed else None,
            "exception_type": self.exception_type,
            "exception_data": self.exception_data,
            "result_data": self.result_data,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkletCase:
        """Create from dictionary.

        Parameters
        ----------
        data : dict[str, Any]
            Dictionary data

        Returns
        -------
        WorkletCase
            WorkletCase instance
        """
        started = (
            datetime.fromisoformat(data["started"])
            if isinstance(data.get("started"), str)
            else data.get("started", datetime.now())
        )
        completed = (
            datetime.fromisoformat(data["completed"])
            if isinstance(data.get("completed"), str) and data["completed"]
            else data.get("completed")
        )
        return cls(
            id=data["id"],
            worklet_id=data["worklet_id"],
            parent_case_id=data["parent_case_id"],
            parent_work_item_id=data.get("parent_work_item_id"),
            status=WorkletStatus[data.get("status", "PENDING")],
            started=started,
            completed=completed,
            exception_type=data.get("exception_type", ""),
            exception_data=data.get("exception_data", {}),
            result_data=data.get("result_data", {}),
        )


@dataclass
class RDRNode:
    """A node in the Ripple Down Rules tree.

    RDR trees provide incremental knowledge acquisition for
    exception handling decisions.
    Note: Not frozen due to mutating methods (add_true_child, etc.).

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

    Examples
    --------
    >>> node = RDRNode(id="node-001", condition="x > 5")
    >>> node.is_leaf()
    True
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

    def __post_init__(self) -> None:
        """Validate RDR node data."""
        if not self.id:
            raise ValueError("RDRNode id cannot be empty")
        if not self.condition:
            raise ValueError("RDRNode condition cannot be empty")

    def __repr__(self) -> str:
        """Developer representation."""
        return f"RDRNode(id={self.id!r}, condition={self.condition!r}, conclusion={self.conclusion!r})"

    def __str__(self) -> str:
        """Human-readable representation."""
        return f"RDRNode(id={self.id}, condition={self.condition[:30]})"

    def __eq__(self, other: object) -> bool:
        """Equality comparison by ID."""
        if not isinstance(other, RDRNode):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash by ID."""
        return hash(self.id)

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


@dataclass
class RDRTree:
    """A Ripple Down Rules tree.

    The tree is traversed to find the appropriate worklet for
    a given exception context.
    Note: Not frozen due to mutating methods (add_node, etc.).

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

    Examples
    --------
    >>> tree = RDRTree(id="tree-001", name="Exception Handler")
    >>> tree.count_nodes()
    1
    """

    id: str
    name: str
    root: RDRNode = field(default_factory=lambda: RDRNode(id="root"))
    task_id: str | None = None
    exception_type: str = "default"
    nodes: dict[str, RDRNode] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Register root node and validate."""
        if not self.id:
            raise ValueError("RDRTree id cannot be empty")
        if not self.name:
            raise ValueError("RDRTree name cannot be empty")
        if self.root.id not in self.nodes:
            self.nodes[self.root.id] = self.root

    def __repr__(self) -> str:
        """Developer representation."""
        return f"RDRTree(id={self.id!r}, name={self.name!r}, node_count={len(self.nodes)})"

    def __str__(self) -> str:
        """Human-readable representation."""
        return f"RDRTree(id={self.id}, name={self.name}, nodes={len(self.nodes)})"

    def __eq__(self, other: object) -> bool:
        """Equality comparison by ID."""
        if not isinstance(other, RDRTree):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash by ID."""
        return hash(self.id)

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
