"""Top-level workflow specification (mirrors Java YSpecification).

A YSpecification is the complete container for a YAWL workflow definition,
containing nets, decompositions, and metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_decomposition import YDecomposition
    from kgcl.yawl.elements.y_net import YNet


class SpecificationStatus(Enum):
    """Status of a specification in its lifecycle.

    Attributes
    ----------
    EDITING : auto
        Specification is being edited
    LOADED : auto
        Specification is loaded and ready
    ACTIVE : auto
        Specification is active and can execute
    SUSPENDED : auto
        Specification is temporarily suspended
    RETIRED : auto
        Specification is retired (no new cases)
    ARCHIVED : auto
        Specification is archived
    """

    EDITING = auto()
    LOADED = auto()
    ACTIVE = auto()
    SUSPENDED = auto()
    RETIRED = auto()
    ARCHIVED = auto()


@dataclass(frozen=True)
class YSpecificationID:
    """Unique identifier for a specification (mirrors Java YSpecificationID).

    Parameters
    ----------
    uri : str
        URI of the specification
    version : str
        Version string
    identifier : str
        Unique identifier

    Examples
    --------
    >>> spec_id = YSpecificationID(uri="http://example.com/spec", version="1.0", identifier="my_spec")
    """

    uri: str
    version: str
    identifier: str


@dataclass
class YSpecificationVersion:
    """Version information for a specification.

    Parameters
    ----------
    major : int
        Major version number
    minor : int
        Minor version number
    build : str
        Build identifier

    Examples
    --------
    >>> version = YSpecificationVersion(major=1, minor=0)
    >>> str(version)
    '1.0'
    """

    major: int = 0
    minor: int = 1
    build: str = ""

    def __str__(self) -> str:
        """Format as version string."""
        version = f"{self.major}.{self.minor}"
        if self.build:
            version += f".{self.build}"
        return version

    def __lt__(self, other: YSpecificationVersion) -> bool:
        """Compare versions."""
        if self.major != other.major:
            return self.major < other.major
        return self.minor < other.minor


@dataclass
class YMetaData:
    """Metadata about a specification (mirrors Java YMetaData).

    Contains Dublin Core-style metadata elements plus YAWL-specific fields.

    Parameters
    ----------
    title : str
        Title of the specification
    creator : str
        Creator/author name
    description : str
        Description of the workflow
    subject : str
        Subject/keywords
    coverage : str
        Coverage (scope)
    valid_from : datetime | None
        Start of validity period
    valid_until : datetime | None
        End of validity period
    created : datetime | None
        Creation timestamp
    version : YSpecificationVersion
        Version information
    status : str
        Status string
    persistent : bool
        Whether to persist specification
    unique_id : str
        Unique identifier (often URI)

    Examples
    --------
    >>> meta = YMetaData(title="Order Processing", creator="John Doe")
    """

    title: str = ""
    creator: str = ""
    description: str = ""
    subject: str = ""
    coverage: str = ""
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    created: datetime | None = None
    version: YSpecificationVersion = field(default_factory=YSpecificationVersion)
    status: str = ""
    persistent: bool = True
    unique_id: str = ""

    def __post_init__(self) -> None:
        """Initialize created timestamp if not set."""
        if self.created is None:
            self.created = datetime.now()


@dataclass
class YSpecification:
    """Top-level workflow specification (mirrors Java YSpecification).

    A YSpecification is the complete definition of a YAWL workflow. It contains:
    - One or more nets (with exactly one root net)
    - Decompositions (what tasks do)
    - Metadata (title, creator, version, etc.)
    - Data type definitions

    Parameters
    ----------
    id : str
        Unique identifier (typically a URI)
    name : str
        Human-readable name
    documentation : str
        Optional documentation
    metadata : YMetaData
        Specification metadata
    status : SpecificationStatus
        Current status
    root_net_id : str | None
        ID of the root net
    nets : dict[str, YNet]
        All nets by ID
    decompositions : dict[str, YDecomposition]
        All decompositions by ID
    data_type_definitions : dict[str, str]
        Custom data type definitions (name → schema)
    schema : str
        Schema version/URI
    attributes : dict[str, Any]
        Extended attributes

    Examples
    --------
    >>> spec = YSpecification(id="urn:example:order-process")
    >>> spec.set_root_net(order_net)
    >>> spec.add_decomposition(payment_service)
    """

    id: str
    name: str = ""
    documentation: str = ""
    metadata: YMetaData = field(default_factory=YMetaData)
    status: SpecificationStatus = SpecificationStatus.EDITING

    # Root net (entry point)
    root_net_id: str | None = None

    # All nets (root + subnets)
    nets: dict[str, Any] = field(default_factory=dict)  # YNet

    # All decompositions
    decompositions: dict[str, Any] = field(default_factory=dict)  # YDecomposition

    # Custom data types
    data_type_definitions: dict[str, str] = field(default_factory=dict)

    # Schema info
    schema: str = "http://www.yawlfoundation.org/yawlschema"

    # Extended attributes
    attributes: dict[str, Any] = field(default_factory=dict)

    def set_root_net(self, net: Any) -> None:
        """Set the root net (entry point).

        Parameters
        ----------
        net : YNet
            Net to set as root

        Examples
        --------
        >>> spec = YSpecification(id="test")
        >>> net = YNet(id="main")
        >>> spec.set_root_net(net)
        >>> spec.root_net_id
        'main'
        """
        self.root_net_id = net.id
        self.add_net(net)

    def get_root_net(self) -> Any | None:
        """Get the root net.

        Returns
        -------
        YNet | None
            Root net or None if not set
        """
        if self.root_net_id:
            return self.nets.get(self.root_net_id)
        return None

    def add_net(self, net: Any) -> None:
        """Add net to specification.

        Parameters
        ----------
        net : YNet
            Net to add
        """
        net.specification_id = self.id
        self.nets[net.id] = net
        # Also add as decomposition (nets are decompositions)
        self.decompositions[net.id] = net

    def get_net(self, net_id: str) -> Any | None:
        """Get net by ID.

        Parameters
        ----------
        net_id : str
            Net ID

        Returns
        -------
        YNet | None
            Net or None if not found
        """
        return self.nets.get(net_id)

    def add_decomposition(self, decomposition: Any) -> None:
        """Add decomposition to specification.

        Parameters
        ----------
        decomposition : YDecomposition
            Decomposition to add
        """
        decomposition.specification_id = self.id
        self.decompositions[decomposition.id] = decomposition

    def get_decomposition(self, decomposition_id: str) -> Any | None:
        """Get decomposition by ID.

        Parameters
        ----------
        decomposition_id : str
            Decomposition ID

        Returns
        -------
        YDecomposition | None
            Decomposition or None if not found
        """
        return self.decompositions.get(decomposition_id)

    def add_data_type_definition(self, name: str, schema: str) -> None:
        """Add custom data type definition.

        Parameters
        ----------
        name : str
            Type name
        schema : str
            XML Schema definition
        """
        self.data_type_definitions[name] = schema

    def get_data_type_definition(self, name: str) -> str | None:
        """Get data type definition.

        Parameters
        ----------
        name : str
            Type name

        Returns
        -------
        str | None
            Schema definition or None
        """
        return self.data_type_definitions.get(name)

    def get_all_task_ids(self) -> list[str]:
        """Get IDs of all tasks across all nets.

        Returns
        -------
        list[str]
            All task IDs
        """
        task_ids = []
        for net in self.nets.values():
            task_ids.extend(net.tasks.keys())
        return task_ids

    def get_task(self, task_id: str) -> Any | None:
        """Get task by ID from any net.

        Parameters
        ----------
        task_id : str
            Task ID

        Returns
        -------
        YTask | None
            Task or None if not found
        """
        for net in self.nets.values():
            if task_id in net.tasks:
                return net.tasks[task_id]
        return None

    def is_valid(self) -> tuple[bool, list[str]]:
        """Validate specification structure.

        Returns
        -------
        tuple[bool, list[str]]
            (is_valid, list of error messages)
        """
        errors = []

        # Must have root net
        if self.root_net_id is None:
            errors.append("No root net specified")
        elif self.root_net_id not in self.nets:
            errors.append(f"Root net '{self.root_net_id}' not found")

        # Root net must be valid
        root_net = self.get_root_net()
        if root_net and not root_net.is_valid():
            errors.append("Root net is invalid")

        # All task decompositions must exist
        for net in self.nets.values():
            for task in net.tasks.values():
                if task.decomposition_id:
                    if task.decomposition_id not in self.decompositions:
                        errors.append(f"Task '{task.id}' references unknown decomposition '{task.decomposition_id}'")

        return len(errors) == 0, errors

    def activate(self) -> None:
        """Activate specification for execution."""
        self.status = SpecificationStatus.ACTIVE

    def suspend(self) -> None:
        """Suspend specification (pause new cases)."""
        self.status = SpecificationStatus.SUSPENDED

    def retire(self) -> None:
        """Retire specification (no new cases, existing continue)."""
        self.status = SpecificationStatus.RETIRED

    def can_create_case(self) -> bool:
        """Check if new cases can be created.

        Returns
        -------
        bool
            True if specification is active
        """
        return self.status == SpecificationStatus.ACTIVE

    def set_attribute(self, key: str, value: Any) -> None:
        """Set extended attribute.

        Parameters
        ----------
        key : str
            Attribute key
        value : Any
            Attribute value
        """
        self.attributes[key] = value

    def get_attribute(self, key: str) -> Any | None:
        """Get extended attribute.

        Parameters
        ----------
        key : str
            Attribute key

        Returns
        -------
        Any | None
            Attribute value or None
        """
        return self.attributes.get(key)

    def __hash__(self) -> int:
        """Hash by ID."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Equality by ID."""
        if not isinstance(other, YSpecification):
            return NotImplemented
        return self.id == other.id
