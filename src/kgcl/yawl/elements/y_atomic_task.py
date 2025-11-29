"""Atomic and composite task types (mirrors Java YAtomicTask, YCompositeTask).

Tasks in YAWL are either atomic (leaf tasks that do actual work) or
composite (contain a sub-net). This mirrors the Java task hierarchy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

from kgcl.yawl.elements.y_task import JoinType, SplitType, YTask
from kgcl.yawl.resources.y_distribution import DistributionStrategy
from kgcl.yawl.resources.y_filters import FilterExpression

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_multi_instance import YMultiInstanceAttributes


class TaskType(Enum):
    """Type of task for categorization.

    Attributes
    ----------
    ATOMIC : auto
        Atomic task (leaf, does actual work)
    COMPOSITE : auto
        Composite task (contains sub-net)
    MULTIPLE_ATOMIC : auto
        Multiple instance atomic task
    MULTIPLE_COMPOSITE : auto
        Multiple instance composite task
    """

    ATOMIC = auto()
    COMPOSITE = auto()
    MULTIPLE_ATOMIC = auto()
    MULTIPLE_COMPOSITE = auto()


class ResourcingType(Enum):
    """How a task obtains resources.

    Attributes
    ----------
    OFFER : auto
        Offer to multiple participants (they choose)
    ALLOCATE : auto
        Allocate to specific participant
    START : auto
        Auto-start when allocated
    SYSTEM : auto
        System task (no human resources)
    """

    OFFER = auto()
    ALLOCATE = auto()
    START = auto()
    SYSTEM = auto()


@dataclass
class YResourcingSpec:
    """Resourcing specification for a task (mirrors Java resourcing).

    Defines how a task obtains human resources and what happens
    at various lifecycle stages.

    Parameters
    ----------
    offer_type : ResourcingType
        How task is offered to participants
    allocate_type : ResourcingType
        How task is allocated
    start_type : ResourcingType
        How task is started
    privilege_type : str
        Privileges for the resource
    role_ids : set[str]
        IDs of roles that can perform task
    participant_ids : set[str]
        IDs of specific participants
    filter_expressions : list[str]
        Filter expressions for resource selection (legacy string format)
    distribution_set : str | None
        Distribution set expression
    familiar_participant : str | None
        Reference to familiar participant (e.g., same as previous task)
    filters : list[FilterExpression]
        RBAC filter expressions for participant selection
    distribution_strategy : DistributionStrategy
        Strategy for distributing work among qualified participants
    four_eyes_tasks : set[str]
        Task IDs for four-eyes separation (different participant required)
    """

    offer_type: ResourcingType = ResourcingType.OFFER
    allocate_type: ResourcingType = ResourcingType.ALLOCATE
    start_type: ResourcingType = ResourcingType.SYSTEM
    privilege_type: str = ""

    # Who can do this task
    role_ids: set[str] = field(default_factory=set)
    participant_ids: set[str] = field(default_factory=set)

    # Dynamic selection (legacy string format)
    filter_expressions: list[str] = field(default_factory=list)
    distribution_set: str | None = None
    familiar_participant: str | None = None

    # RBAC filters (Gap 7)
    filters: list[FilterExpression] = field(default_factory=list)
    distribution_strategy: DistributionStrategy = DistributionStrategy.OFFER_TO_ALL
    four_eyes_tasks: set[str] = field(default_factory=set)

    # Timer configuration for work item timeouts
    # Dict with "duration" (timedelta) and "action" (str: NOTIFY, COMPLETE, FAIL, ESCALATE)
    timer: dict[str, Any] | None = None

    def add_role(self, role_id: str) -> None:
        """Add role to resourcing.

        Parameters
        ----------
        role_id : str
            ID of role to add
        """
        self.role_ids.add(role_id)

    def add_participant(self, participant_id: str) -> None:
        """Add specific participant to resourcing.

        Parameters
        ----------
        participant_id : str
            ID of participant to add
        """
        self.participant_ids.add(participant_id)

    def add_filter(self, filter_expr: FilterExpression) -> None:
        """Add RBAC filter expression.

        Parameters
        ----------
        filter_expr : FilterExpression
            Filter to add
        """
        self.filters.append(filter_expr)

    def add_four_eyes_task(self, task_id: str) -> None:
        """Add task requiring four-eyes separation.

        Parameters
        ----------
        task_id : str
            Task ID requiring different participant
        """
        self.four_eyes_tasks.add(task_id)

    def has_filters(self) -> bool:
        """Check if RBAC filters are configured.

        Returns
        -------
        bool
            True if filters exist
        """
        return len(self.filters) > 0

    def has_four_eyes(self) -> bool:
        """Check if four-eyes separation is required.

        Returns
        -------
        bool
            True if four-eyes tasks exist
        """
        return len(self.four_eyes_tasks) > 0

    def is_system_task(self) -> bool:
        """Check if this is a system (automated) task.

        Returns
        -------
        bool
            True if no human resources required
        """
        return len(self.role_ids) == 0 and len(self.participant_ids) == 0 and self.start_type == ResourcingType.SYSTEM


@dataclass
class YDataBinding:
    """Data binding for task input/output (mirrors Java data mappings).

    Maps data between net variables and task parameters using
    expressions (XQuery in Java, Python expressions here).

    Parameters
    ----------
    name : str
        Binding name
    expression : str
        Mapping expression
    target : str
        Target parameter/variable name
    is_input : bool
        True if input binding, False if output

    Examples
    --------
    >>> binding = YDataBinding(
    ...     name="customerInput", expression="customer_data['name']", target="customerName", is_input=True
    ... )
    """

    name: str
    expression: str
    target: str
    is_input: bool = True


@dataclass
class YAtomicTask(YTask):
    """Atomic task - leaf task that does actual work (mirrors Java YAtomicTask).

    Atomic tasks are the leaves in the task hierarchy. They perform
    actual work, either through human resources or automated services.

    Parameters
    ----------
    task_type : TaskType
        Type categorization
    resourcing : YResourcingSpec
        Resource allocation specification
    input_bindings : dict[str, YDataBinding]
        Input data bindings (param name → binding)
    output_bindings : dict[str, YDataBinding]
        Output data bindings (param name → binding)
    timer_expression : str | None
        Timer expression for task timeout
    timer_trigger : str
        Timer trigger type: "OnEnabled", "OnAllocated", "OnStarted"
    custom_form_url : str | None
        URL of custom form for task
    codelet : str | None
        Class name for automated service
    enable_skipper : bool
        Allow task to be skipped
    skip_expression : str | None
        Expression to evaluate for auto-skip

    Examples
    --------
    >>> task = YAtomicTask(id="ReviewOrder")
    >>> task.resourcing.add_role("OrderReviewer")
    >>> task.enable_skipper = True
    """

    task_type: TaskType = TaskType.ATOMIC
    resourcing: YResourcingSpec = field(default_factory=YResourcingSpec)

    # Data bindings
    input_bindings: dict[str, YDataBinding] = field(default_factory=dict)
    output_bindings: dict[str, YDataBinding] = field(default_factory=dict)

    # Timer support
    timer_expression: str | None = None
    timer_trigger: str = "OnEnabled"

    # Custom form
    custom_form_url: str | None = None

    # Automated service
    codelet: str | None = None

    # Skip capability
    enable_skipper: bool = False
    skip_expression: str | None = None

    def add_input_binding(self, binding: YDataBinding) -> None:
        """Add input data binding.

        Parameters
        ----------
        binding : YDataBinding
            Binding to add
        """
        self.input_bindings[binding.name] = binding

    def add_output_binding(self, binding: YDataBinding) -> None:
        """Add output data binding.

        Parameters
        ----------
        binding : YDataBinding
            Binding to add
        """
        self.output_bindings[binding.name] = binding

    def is_manual_task(self) -> bool:
        """Check if task requires human work.

        Returns
        -------
        bool
            True if manual task
        """
        return not self.resourcing.is_system_task() and self.codelet is None

    def is_automated_task(self) -> bool:
        """Check if task is automated.

        Returns
        -------
        bool
            True if automated (has codelet)
        """
        return self.codelet is not None

    def has_timer(self) -> bool:
        """Check if task has timer.

        Returns
        -------
        bool
            True if timer configured
        """
        return self.timer_expression is not None

    def can_skip(self) -> bool:
        """Check if task can be skipped.

        Returns
        -------
        bool
            True if skipping enabled
        """
        return self.enable_skipper


@dataclass
class YCompositeTask(YTask):
    """Composite task - contains a sub-net (mirrors Java YCompositeTask).

    Composite tasks delegate to a sub-net for their implementation.
    This enables hierarchical decomposition of workflows.

    Parameters
    ----------
    task_type : TaskType
        Type categorization
    subnet_id : str | None
        ID of the sub-net decomposition
    input_bindings : dict[str, YDataBinding]
        Input data bindings
    output_bindings : dict[str, YDataBinding]
        Output data bindings

    Examples
    --------
    >>> task = YCompositeTask(id="ProcessOrder", subnet_id="OrderProcessNet")
    """

    task_type: TaskType = TaskType.COMPOSITE
    subnet_id: str | None = None

    # Data bindings
    input_bindings: dict[str, YDataBinding] = field(default_factory=dict)
    output_bindings: dict[str, YDataBinding] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Set decomposition ID to subnet ID."""
        if self.subnet_id and not self.decomposition_id:
            self.decomposition_id = self.subnet_id

    def add_input_binding(self, binding: YDataBinding) -> None:
        """Add input data binding.

        Parameters
        ----------
        binding : YDataBinding
            Binding to add
        """
        self.input_bindings[binding.name] = binding

    def add_output_binding(self, binding: YDataBinding) -> None:
        """Add output data binding.

        Parameters
        ----------
        binding : YDataBinding
            Binding to add
        """
        self.output_bindings[binding.name] = binding

    def has_subnet(self) -> bool:
        """Check if subnet is configured.

        Returns
        -------
        bool
            True if subnet ID set
        """
        return self.subnet_id is not None


@dataclass
class YMultipleInstanceTask(YAtomicTask):
    """Multiple instance task (mirrors Java multi-instance handling).

    A task that spawns multiple instances based on data. This implements
    WCP 12-15 (multiple instance patterns).

    Parameters
    ----------
    mi_minimum : int
        Minimum number of instances
    mi_maximum : int
        Maximum number of instances
    mi_threshold : int
        Threshold for completion (how many must complete)
    mi_creation_mode : str
        Creation mode: "static" or "dynamic"
    mi_query : str
        Query expression to generate instances
    mi_input_joiner : str
        Expression to join input data
    mi_output_query : str
        Query expression for output aggregation
    mi_unique_input_expression : str
        Expression to extract unique input per instance

    Examples
    --------
    >>> task = YMultipleInstanceTask(id="ReviewItems", mi_minimum=1, mi_maximum=10, mi_threshold=5)
    """

    mi_minimum: int = 1
    mi_maximum: int = 1
    mi_threshold: int = 1
    mi_creation_mode: str = "static"
    mi_query: str = ""
    mi_input_joiner: str = ""
    mi_output_query: str = ""
    mi_unique_input_expression: str = ""

    def __post_init__(self) -> None:
        """Set task type."""
        self.task_type = TaskType.MULTIPLE_ATOMIC

    def is_static_creation(self) -> bool:
        """Check if instances are created statically.

        Returns
        -------
        bool
            True if static creation
        """
        return self.mi_creation_mode == "static"

    def is_dynamic_creation(self) -> bool:
        """Check if instances can be created dynamically.

        Returns
        -------
        bool
            True if dynamic creation
        """
        return self.mi_creation_mode == "dynamic"

    def get_completion_threshold(self) -> int:
        """Get completion threshold.

        Returns
        -------
        int
            Number of instances that must complete
        """
        return self.mi_threshold
