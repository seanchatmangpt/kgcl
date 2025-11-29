"""Multi-Instance task execution context (WCP 12-15).

Manages parallel and sequential execution of multi-instance tasks,
tracking child instances and implementing completion thresholds.

Patterns supported:
- WCP-12: Multiple Instances without Synchronization
- WCP-13: Multiple Instances with a Priori Design-Time Knowledge
- WCP-14: Multiple Instances with a Priori Run-Time Knowledge
- WCP-15: Multiple Instances without a Priori Run-Time Knowledge

Java Reference: YMultiInstanceAttributes, MIDataInput, MIDataOutput
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class MICreationMode(Enum):
    """How instances are created."""

    STATIC = auto()  # Fixed count at design time
    DYNAMIC = auto()  # Count determined at runtime


class MIOrderingMode(Enum):
    """Execution ordering of instances."""

    PARALLEL = auto()  # All instances concurrent
    SEQUENTIAL = auto()  # One at a time


class MICompletionMode(Enum):
    """When parent task completes."""

    ALL = auto()  # Wait for all instances
    THRESHOLD = auto()  # Complete when threshold reached


class MIChildStatus(Enum):
    """Status of a child instance."""

    PENDING = auto()
    EXECUTING = auto()
    COMPLETED = auto()
    CANCELLED = auto()
    FAILED = auto()


@dataclass
class MIChildInstance:
    """A single child instance of a multi-instance task.

    Parameters
    ----------
    id : str
        Unique instance ID
    index : int
        Index in the instance set (0-based)
    work_item_id : str | None
        Associated work item ID
    status : MIChildStatus
        Current instance status
    input_data : dict[str, Any]
        Input data for this instance
    output_data : dict[str, Any]
        Output data from this instance
    """

    id: str
    index: int
    work_item_id: str | None = None
    status: MIChildStatus = MIChildStatus.PENDING
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] = field(default_factory=dict)

    def is_terminal(self) -> bool:
        """Check if instance is in terminal state.

        Returns
        -------
        bool
            True if completed, cancelled, or failed
        """
        return self.status in (MIChildStatus.COMPLETED, MIChildStatus.CANCELLED, MIChildStatus.FAILED)


@dataclass
class MITaskConfig:
    """Configuration for a multi-instance task.

    Parameters
    ----------
    minimum : int
        Minimum number of instances
    maximum : int | None
        Maximum instances (None = unlimited)
    threshold : int
        Completion threshold
    creation_mode : MICreationMode
        How instances are created
    ordering_mode : MIOrderingMode
        Sequential or parallel execution
    completion_mode : MICompletionMode
        When to complete parent
    input_query : str | None
        Expression to extract input items
    input_variable : str | None
        Variable name for each instance input
    output_query : str | None
        Expression to aggregate outputs
    output_variable : str | None
        Variable name for aggregated output
    """

    minimum: int = 1
    maximum: int | None = None
    threshold: int = 1
    creation_mode: MICreationMode = MICreationMode.STATIC
    ordering_mode: MIOrderingMode = MIOrderingMode.PARALLEL
    completion_mode: MICompletionMode = MICompletionMode.ALL
    input_query: str | None = None
    input_variable: str | None = None
    output_query: str | None = None
    output_variable: str | None = None

    def validate(self) -> list[str]:
        """Validate configuration.

        Returns
        -------
        list[str]
            Validation errors
        """
        errors: list[str] = []

        if self.minimum < 1:
            errors.append("minimum must be >= 1")

        if self.maximum is not None and self.maximum < self.minimum:
            errors.append("maximum must be >= minimum")

        if self.threshold < 1:
            errors.append("threshold must be >= 1")

        if self.threshold > self.minimum:
            errors.append("threshold must be <= minimum")

        return errors


@dataclass
class MIExecutionContext:
    """Execution context for a multi-instance task.

    Tracks all child instances and completion state.

    Parameters
    ----------
    context_id : str
        Unique context ID
    task_id : str
        Parent task ID
    parent_work_item_id : str
        Parent work item ID
    config : MITaskConfig
        Task configuration
    children : dict[str, MIChildInstance]
        Child instances by ID
    aggregated_output : list[Any]
        Collected outputs from children
    """

    context_id: str
    task_id: str
    parent_work_item_id: str
    config: MITaskConfig
    children: dict[str, MIChildInstance] = field(default_factory=dict)
    aggregated_output: list[Any] = field(default_factory=list)
    _next_index: int = field(default=0, repr=False)

    @property
    def total_count(self) -> int:
        """Total number of children created."""
        return len(self.children)

    @property
    def completed_count(self) -> int:
        """Number of completed children."""
        return sum(1 for c in self.children.values() if c.status == MIChildStatus.COMPLETED)

    @property
    def active_count(self) -> int:
        """Number of executing children."""
        return sum(1 for c in self.children.values() if c.status == MIChildStatus.EXECUTING)

    @property
    def pending_count(self) -> int:
        """Number of pending children."""
        return sum(1 for c in self.children.values() if c.status == MIChildStatus.PENDING)

    def create_child(self, input_data: dict[str, Any] | None = None) -> MIChildInstance:
        """Create a new child instance.

        Parameters
        ----------
        input_data : dict[str, Any] | None
            Input data for the child

        Returns
        -------
        MIChildInstance
            New child instance

        Raises
        ------
        ValueError
            If maximum instances reached
        """
        if self.config.maximum is not None:
            if self.total_count >= self.config.maximum:
                raise ValueError(f"Maximum instances ({self.config.maximum}) reached")

        child = MIChildInstance(
            id=f"{self.context_id}-child-{self._next_index}", index=self._next_index, input_data=input_data or {}
        )
        self._next_index += 1
        self.children[child.id] = child
        return child

    def get_child(self, child_id: str) -> MIChildInstance | None:
        """Get child by ID.

        Parameters
        ----------
        child_id : str
            Child instance ID

        Returns
        -------
        MIChildInstance | None
            Child or None
        """
        return self.children.get(child_id)

    def get_child_by_work_item(self, work_item_id: str) -> MIChildInstance | None:
        """Get child by associated work item ID.

        Parameters
        ----------
        work_item_id : str
            Work item ID

        Returns
        -------
        MIChildInstance | None
            Child or None
        """
        for child in self.children.values():
            if child.work_item_id == work_item_id:
                return child
        return None

    def start_child(self, child_id: str, work_item_id: str) -> bool:
        """Mark child as executing.

        Parameters
        ----------
        child_id : str
            Child instance ID
        work_item_id : str
            Associated work item ID

        Returns
        -------
        bool
            True if started
        """
        child = self.children.get(child_id)
        if child and child.status == MIChildStatus.PENDING:
            child.status = MIChildStatus.EXECUTING
            child.work_item_id = work_item_id
            return True
        return False

    def complete_child(self, child_id: str, output_data: dict[str, Any] | None = None) -> bool:
        """Mark child as completed.

        Parameters
        ----------
        child_id : str
            Child instance ID
        output_data : dict[str, Any] | None
            Output data from the child

        Returns
        -------
        bool
            True if completed
        """
        child = self.children.get(child_id)
        if child and not child.is_terminal():
            child.status = MIChildStatus.COMPLETED
            child.output_data = output_data or {}
            self.aggregated_output.append(child.output_data)
            return True
        return False

    def fail_child(self, child_id: str, error: str | None = None) -> bool:
        """Mark child as failed.

        Parameters
        ----------
        child_id : str
            Child instance ID
        error : str | None
            Error message

        Returns
        -------
        bool
            True if failed
        """
        child = self.children.get(child_id)
        if child and not child.is_terminal():
            child.status = MIChildStatus.FAILED
            if error:
                child.output_data["_error"] = error
            return True
        return False

    def cancel_child(self, child_id: str) -> bool:
        """Cancel a child instance.

        Parameters
        ----------
        child_id : str
            Child instance ID

        Returns
        -------
        bool
            True if cancelled
        """
        child = self.children.get(child_id)
        if child and not child.is_terminal():
            child.status = MIChildStatus.CANCELLED
            return True
        return False

    def is_completion_satisfied(self) -> bool:
        """Check if completion criteria met.

        Returns
        -------
        bool
            True if parent can complete
        """
        if self.config.completion_mode == MICompletionMode.ALL:
            # All children must be terminal (completed/cancelled/failed)
            return all(c.is_terminal() for c in self.children.values())

        # Threshold mode
        return self.completed_count >= self.config.threshold

    def should_cancel_remaining(self) -> bool:
        """Check if remaining instances should be cancelled.

        Called when completion threshold is reached.

        Returns
        -------
        bool
            True if remaining should be cancelled
        """
        if self.config.completion_mode == MICompletionMode.THRESHOLD:
            return self.completed_count >= self.config.threshold
        return False

    def cancel_remaining(self) -> list[str]:
        """Cancel all non-terminal children.

        Returns
        -------
        list[str]
            IDs of cancelled children
        """
        cancelled: list[str] = []
        for child in self.children.values():
            if not child.is_terminal():
                child.status = MIChildStatus.CANCELLED
                cancelled.append(child.id)
        return cancelled

    def get_next_to_execute(self) -> MIChildInstance | None:
        """Get next child to execute (for sequential mode).

        Returns
        -------
        MIChildInstance | None
            Next pending child in order
        """
        if self.config.ordering_mode != MIOrderingMode.SEQUENTIAL:
            return None

        # Find first pending by index
        pending = [c for c in self.children.values() if c.status == MIChildStatus.PENDING]
        if pending:
            return min(pending, key=lambda c: c.index)
        return None

    def can_start_more(self) -> bool:
        """Check if more instances can be started.

        Returns
        -------
        bool
            True if more can start
        """
        if self.config.ordering_mode == MIOrderingMode.SEQUENTIAL:
            # Sequential: only one active at a time
            return self.active_count == 0 and self.pending_count > 0

        # Parallel: all pending can start
        return self.pending_count > 0


@dataclass
class YMIRunner:
    """Runner for multi-instance task execution.

    Manages creation and tracking of MI execution contexts.

    Parameters
    ----------
    contexts : dict[str, MIExecutionContext]
        Active contexts by parent work item ID
    """

    contexts: dict[str, MIExecutionContext] = field(default_factory=dict)

    def create_context(
        self,
        task_id: str,
        parent_work_item_id: str,
        config: MITaskConfig,
        input_items: list[dict[str, Any]] | None = None,
    ) -> MIExecutionContext:
        """Create a new MI execution context.

        Parameters
        ----------
        task_id : str
            Parent task ID
        parent_work_item_id : str
            Parent work item ID
        config : MITaskConfig
            Task configuration
        input_items : list[dict[str, Any]] | None
            Optional input items (one per instance)

        Returns
        -------
        MIExecutionContext
            New execution context
        """
        context = MIExecutionContext(
            context_id=str(uuid.uuid4()), task_id=task_id, parent_work_item_id=parent_work_item_id, config=config
        )

        # Create children based on input items or minimum count
        if input_items:
            for item in input_items:
                context.create_child(item)
        else:
            for _ in range(config.minimum):
                context.create_child()

        self.contexts[parent_work_item_id] = context
        return context

    def get_context(self, parent_work_item_id: str) -> MIExecutionContext | None:
        """Get context by parent work item ID.

        Parameters
        ----------
        parent_work_item_id : str
            Parent work item ID

        Returns
        -------
        MIExecutionContext | None
            Context or None
        """
        return self.contexts.get(parent_work_item_id)

    def get_context_by_child(self, child_work_item_id: str) -> tuple[MIExecutionContext, MIChildInstance] | None:
        """Get context and child by child work item ID.

        Parameters
        ----------
        child_work_item_id : str
            Child work item ID

        Returns
        -------
        tuple[MIExecutionContext, MIChildInstance] | None
            Context and child, or None
        """
        for context in self.contexts.values():
            child = context.get_child_by_work_item(child_work_item_id)
            if child:
                return context, child
        return None

    def add_instance(
        self, parent_work_item_id: str, input_data: dict[str, Any] | None = None
    ) -> MIChildInstance | None:
        """Add a new instance dynamically (WCP-15).

        Parameters
        ----------
        parent_work_item_id : str
            Parent work item ID
        input_data : dict[str, Any] | None
            Input data for new instance

        Returns
        -------
        MIChildInstance | None
            New child or None if not allowed
        """
        context = self.contexts.get(parent_work_item_id)
        if not context:
            return None

        if context.config.creation_mode != MICreationMode.DYNAMIC:
            return None

        try:
            return context.create_child(input_data)
        except ValueError:
            return None  # Maximum reached

    def complete_context(self, parent_work_item_id: str) -> bool:
        """Complete and remove a context.

        Parameters
        ----------
        parent_work_item_id : str
            Parent work item ID

        Returns
        -------
        bool
            True if removed
        """
        if parent_work_item_id in self.contexts:
            del self.contexts[parent_work_item_id]
            return True
        return False

    def get_instances_to_start(self, parent_work_item_id: str) -> list[MIChildInstance]:
        """Get child instances ready to start.

        Parameters
        ----------
        parent_work_item_id : str
            Parent work item ID

        Returns
        -------
        list[MIChildInstance]
            Instances ready for work item creation
        """
        context = self.contexts.get(parent_work_item_id)
        if not context:
            return []

        if context.config.ordering_mode == MIOrderingMode.SEQUENTIAL:
            next_child = context.get_next_to_execute()
            return [next_child] if next_child else []

        # Parallel: return all pending
        return [c for c in context.children.values() if c.status == MIChildStatus.PENDING]
