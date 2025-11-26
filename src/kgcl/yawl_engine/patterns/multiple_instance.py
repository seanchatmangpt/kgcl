"""Multiple Instance (MI) patterns for YAWL workflow engine.

Implements patterns 12-15 from the YAWL workflow patterns reference:
- Pattern 12: Multiple Instance without Synchronization
- Pattern 13: Multiple Instance with a priori Design-Time Knowledge
- Pattern 14: Multiple Instance with a priori Run-Time Knowledge
- Pattern 15: Multiple Instance without a priori Run-Time Knowledge

References
----------
- YAWL: Yet Another Workflow Language (van der Aalst & ter Hofstede, 2005)
- Workflow Patterns: http://www.workflowpatterns.com/

Examples
--------
>>> from rdflib import Graph, URIRef, Namespace
>>> ex = Namespace("http://example.org/")
>>> g = Graph()
>>> task = ex.processOrder
>>>
>>> # Pattern 12: Fire and forget
>>> mi_no_sync = MIWithoutSync()
>>> instances = mi_no_sync.spawn_instances(g, task, count=5)
>>> len(instances)
5
>>>
>>> # Pattern 13: Fixed count at design time
>>> mi_design = MIDesignTime(instance_count=3)
>>> result = mi_design.execute(g, task, context={})
>>> result.success
True
>>> len(result.instance_ids)
3
>>>
>>> # Pattern 14: Count from runtime variable
>>> mi_runtime = MIRunTimeKnown(instance_count_variable="order_count")
>>> result = mi_runtime.execute(g, task, context={"order_count": 7})
>>> len(result.instance_ids)
7
>>>
>>> # Pattern 15: Dynamic spawning
>>> mi_dynamic = MIDynamic(spawn_condition="new_order_received")
>>> result = mi_dynamic.execute(g, task, context={"events": ["order1", "order2"]})
>>> result.success
True
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, cast

from rdflib import Graph, Literal, Namespace, URIRef

logger = logging.getLogger(__name__)

# RDF namespaces
YAWL = Namespace("http://www.yawlsystem.com/yawl/elements/")
WF = Namespace("http://example.org/workflow/")


class MIState(Enum):
    """Multiple instance execution state."""

    PENDING = "pending"
    SPAWNING = "spawning"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class ExecutionResult:
    """Result of multiple instance execution.

    Attributes
    ----------
    success : bool
        Whether all required instances completed successfully
    instance_ids : list[str]
        Identifiers of spawned instances
    state : MIState
        Current execution state
    metadata : dict[str, Any]
        Additional execution metadata
    error : str | None
        Error message if execution failed
    """

    success: bool
    instance_ids: list[str]
    state: MIState
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def __post_init__(self) -> None:
        """Validate execution result invariants."""
        if not self.success and self.error is None:
            msg = "Failed execution must provide error message"
            raise ValueError(msg)
        if self.success and self.error is not None:
            msg = "Successful execution cannot have error message"
            raise ValueError(msg)


@dataclass(frozen=True)
class MIWithoutSync:
    """Pattern 12: Multiple Instance without Synchronization.

    Spawns multiple instances of a task without waiting for completion.
    Fire-and-forget pattern - no tracking of instance completion.

    Attributes
    ----------
    pattern_id : int
        YAWL pattern identifier (12)
    name : str
        Pattern name

    Examples
    --------
    >>> from rdflib import Graph, Namespace
    >>> ex = Namespace("http://example.org/")
    >>> g = Graph()
    >>> pattern = MIWithoutSync()
    >>> instances = pattern.spawn_instances(g, ex.sendEmail, count=10)
    >>> len(instances)
    10
    >>> all(isinstance(i, str) for i in instances)
    True
    """

    pattern_id: int = 12
    name: str = "MI without Synchronization"

    def spawn_instances(self, graph: Graph, task: URIRef, count: int) -> list[str]:
        """Spawn multiple task instances without synchronization.

        Parameters
        ----------
        graph : Graph
            RDF graph containing workflow definition
        task : URIRef
            Task to spawn instances of
        count : int
            Number of instances to spawn

        Returns
        -------
        list[str]
            List of instance identifiers

        Raises
        ------
        ValueError
            If count is not positive
        """
        if count <= 0:
            msg = f"Instance count must be positive, got {count}"
            raise ValueError(msg)

        instance_ids = []
        for i in range(count):
            instance_id = f"{task}#instance-{uuid.uuid4()}"
            instance_ids.append(instance_id)

            # Add instance to graph (fire and forget)
            instance_uri = URIRef(instance_id)
            graph.add((instance_uri, YAWL.instanceOf, task))
            graph.add((instance_uri, YAWL.instanceNumber, Literal(i)))
            graph.add((instance_uri, YAWL.state, Literal(MIState.RUNNING.value)))

            logger.info(
                "Spawned instance (no sync)",
                extra={"pattern": self.pattern_id, "task": str(task), "instance_id": instance_id, "instance_number": i},
            )

        return instance_ids

    def execute(self, graph: Graph, task: URIRef, context: dict[str, Any]) -> ExecutionResult:
        """Execute pattern with fire-and-forget semantics.

        Parameters
        ----------
        graph : Graph
            RDF graph containing workflow definition
        task : URIRef
            Task to execute
        context : dict[str, Any]
            Execution context (must contain 'count' key)

        Returns
        -------
        ExecutionResult
            Execution result with spawned instance IDs
        """
        count = context.get("count", 1)
        instance_ids = self.spawn_instances(graph, task, count)

        return ExecutionResult(
            success=True,
            instance_ids=instance_ids,
            state=MIState.RUNNING,
            metadata={"pattern": self.pattern_id, "sync": False},
        )


@dataclass(frozen=True)
class MIDesignTime:
    """Pattern 13: Multiple Instance with a priori Design-Time Knowledge.

    Instance count is fixed at design time (e.g., exactly 3 reviewers).
    All instances must complete before workflow continues.

    Attributes
    ----------
    pattern_id : int
        YAWL pattern identifier (13)
    name : str
        Pattern name
    instance_count : int
        Fixed number of instances (known at design time)

    Examples
    --------
    >>> from rdflib import Graph, Namespace
    >>> ex = Namespace("http://example.org/")
    >>> g = Graph()
    >>> pattern = MIDesignTime(instance_count=3)
    >>> result = pattern.execute(g, ex.reviewDocument, context={})
    >>> result.success
    True
    >>> len(result.instance_ids)
    3
    >>> result.metadata["requires_sync"]
    True
    """

    pattern_id: int = 13
    name: str = "MI with Design-Time Knowledge"
    instance_count: int = 3  # Fixed at design time

    def __post_init__(self) -> None:
        """Validate design-time instance count."""
        if self.instance_count <= 0:
            msg = f"Instance count must be positive, got {self.instance_count}"
            raise ValueError(msg)

    def execute(self, graph: Graph, task: URIRef, context: dict[str, Any]) -> ExecutionResult:
        """Execute with fixed instance count and synchronization.

        Parameters
        ----------
        graph : Graph
            RDF graph containing workflow definition
        task : URIRef
            Task to execute
        context : dict[str, Any]
            Execution context

        Returns
        -------
        ExecutionResult
            Execution result with all instance IDs
        """
        instance_ids = []
        parent_id = f"{task}#mi-parent-{uuid.uuid4()}"

        for i in range(self.instance_count):
            instance_id = f"{task}#instance-{uuid.uuid4()}"
            instance_ids.append(instance_id)

            instance_uri = URIRef(instance_id)
            graph.add((instance_uri, YAWL.instanceOf, task))
            graph.add((instance_uri, YAWL.instanceNumber, Literal(i)))
            graph.add((instance_uri, YAWL.parentMI, URIRef(parent_id)))
            graph.add((instance_uri, YAWL.state, Literal(MIState.RUNNING.value)))

            logger.info(
                "Spawned instance (design-time)",
                extra={
                    "pattern": self.pattern_id,
                    "task": str(task),
                    "instance_id": instance_id,
                    "instance_number": i,
                    "total_instances": self.instance_count,
                },
            )

        # Add synchronization barrier
        parent_uri = URIRef(parent_id)
        graph.add((parent_uri, YAWL.requiredInstances, Literal(self.instance_count)))
        graph.add((parent_uri, YAWL.completedInstances, Literal(0)))

        return ExecutionResult(
            success=True,
            instance_ids=instance_ids,
            state=MIState.RUNNING,
            metadata={
                "pattern": self.pattern_id,
                "requires_sync": True,
                "parent_id": parent_id,
                "instance_count": self.instance_count,
            },
        )


@dataclass(frozen=True)
class MIRunTimeKnown:
    """Pattern 14: Multiple Instance with a priori Run-Time Knowledge.

    Instance count is determined at runtime start from workflow data.
    For example, one instance per order in a batch.

    Attributes
    ----------
    pattern_id : int
        YAWL pattern identifier (14)
    name : str
        Pattern name
    instance_count_variable : str
        Variable name containing instance count at runtime

    Examples
    --------
    >>> from rdflib import Graph, Namespace
    >>> ex = Namespace("http://example.org/")
    >>> g = Graph()
    >>> pattern = MIRunTimeKnown(instance_count_variable="order_count")
    >>> result = pattern.execute(g, ex.processOrder, context={"order_count": 5})
    >>> result.success
    True
    >>> len(result.instance_ids)
    5
    """

    pattern_id: int = 14
    name: str = "MI with Run-Time Knowledge"
    instance_count_variable: str = "item_count"

    def execute(self, graph: Graph, task: URIRef, context: dict[str, Any]) -> ExecutionResult:
        """Execute with runtime-determined instance count.

        Parameters
        ----------
        graph : Graph
            RDF graph containing workflow definition
        task : URIRef
            Task to execute
        context : dict[str, Any]
            Execution context (must contain instance_count_variable)

        Returns
        -------
        ExecutionResult
            Execution result with all instance IDs

        Raises
        ------
        ValueError
            If instance count variable not found in context
        """
        if self.instance_count_variable not in context:
            msg = f"Instance count variable '{self.instance_count_variable}' not found in context"
            return ExecutionResult(success=False, instance_ids=[], state=MIState.FAILED, error=msg)

        instance_count = context[self.instance_count_variable]
        if not isinstance(instance_count, int) or instance_count <= 0:
            msg = f"Instance count must be positive integer, got {instance_count!r}"
            return ExecutionResult(success=False, instance_ids=[], state=MIState.FAILED, error=msg)

        instance_ids = []
        parent_id = f"{task}#mi-parent-{uuid.uuid4()}"

        for i in range(instance_count):
            instance_id = f"{task}#instance-{uuid.uuid4()}"
            instance_ids.append(instance_id)

            instance_uri = URIRef(instance_id)
            graph.add((instance_uri, YAWL.instanceOf, task))
            graph.add((instance_uri, YAWL.instanceNumber, Literal(i)))
            graph.add((instance_uri, YAWL.parentMI, URIRef(parent_id)))
            graph.add((instance_uri, YAWL.state, Literal(MIState.RUNNING.value)))

            logger.info(
                "Spawned instance (runtime-known)",
                extra={
                    "pattern": self.pattern_id,
                    "task": str(task),
                    "instance_id": instance_id,
                    "instance_number": i,
                    "total_instances": instance_count,
                },
            )

        # Add synchronization barrier
        parent_uri = URIRef(parent_id)
        graph.add((parent_uri, YAWL.requiredInstances, Literal(instance_count)))
        graph.add((parent_uri, YAWL.completedInstances, Literal(0)))

        return ExecutionResult(
            success=True,
            instance_ids=instance_ids,
            state=MIState.RUNNING,
            metadata={
                "pattern": self.pattern_id,
                "requires_sync": True,
                "parent_id": parent_id,
                "instance_count": instance_count,
                "count_variable": self.instance_count_variable,
            },
        )


@dataclass(frozen=True)
class MIDynamic:
    """Pattern 15: Multiple Instance without a priori Run-Time Knowledge.

    Instance count is unknown at start - instances spawn dynamically
    based on events or conditions during execution.

    Attributes
    ----------
    pattern_id : int
        YAWL pattern identifier (15)
    name : str
        Pattern name
    spawn_condition : str
        Condition triggering new instance spawning
    termination_condition : str | None
        Optional condition to stop spawning new instances

    Examples
    --------
    >>> from rdflib import Graph, Namespace
    >>> ex = Namespace("http://example.org/")
    >>> g = Graph()
    >>> pattern = MIDynamic(spawn_condition="new_order_received", termination_condition="all_orders_processed")
    >>> result = pattern.execute(g, ex.processOrder, context={"events": ["order1", "order2", "order3"]})
    >>> result.success
    True
    >>> len(result.instance_ids)
    3
    """

    pattern_id: int = 15
    name: str = "MI without a priori Run-Time Knowledge"
    spawn_condition: str = "event_received"
    termination_condition: str | None = None

    def spawn_instance(self, graph: Graph, task: URIRef, parent_id: str, instance_number: int, event_data: Any) -> str:
        """Spawn a single instance dynamically.

        Parameters
        ----------
        graph : Graph
            RDF graph containing workflow definition
        task : URIRef
            Task to spawn instance of
        parent_id : str
            Parent MI identifier
        instance_number : int
            Sequential instance number
        event_data : Any
            Event data triggering this spawn

        Returns
        -------
        str
            Instance identifier
        """
        instance_id = f"{task}#instance-{uuid.uuid4()}"

        instance_uri = URIRef(instance_id)
        graph.add((instance_uri, YAWL.instanceOf, task))
        graph.add((instance_uri, YAWL.instanceNumber, Literal(instance_number)))
        graph.add((instance_uri, YAWL.parentMI, URIRef(parent_id)))
        graph.add((instance_uri, YAWL.state, Literal(MIState.RUNNING.value)))
        graph.add((instance_uri, YAWL.triggerEvent, Literal(str(event_data))))

        logger.info(
            "Spawned dynamic instance",
            extra={
                "pattern": self.pattern_id,
                "task": str(task),
                "instance_id": instance_id,
                "instance_number": instance_number,
                "event": event_data,
            },
        )

        return instance_id

    def execute(self, graph: Graph, task: URIRef, context: dict[str, Any]) -> ExecutionResult:
        """Execute with dynamic instance spawning.

        Parameters
        ----------
        graph : Graph
            RDF graph containing workflow definition
        task : URIRef
            Task to execute
        context : dict[str, Any]
            Execution context (should contain 'events' or similar)

        Returns
        -------
        ExecutionResult
            Execution result with dynamically spawned instance IDs
        """
        parent_id = f"{task}#mi-parent-{uuid.uuid4()}"
        instance_ids = []

        # Get events that trigger spawning
        events = context.get("events", [])
        if not events:
            logger.warning("No events found for dynamic MI", extra={"pattern": self.pattern_id, "task": str(task)})

        # Spawn instance for each event
        for i, event in enumerate(events):
            instance_id = self.spawn_instance(graph, task, parent_id, i, event)
            instance_ids.append(instance_id)

        # Setup dynamic tracking
        parent_uri = URIRef(parent_id)
        graph.add((parent_uri, YAWL.spawnedInstances, Literal(len(instance_ids))))
        graph.add((parent_uri, YAWL.completedInstances, Literal(0)))
        graph.add((parent_uri, YAWL.dynamicSpawning, Literal(True)))
        graph.add((parent_uri, YAWL.spawnCondition, Literal(self.spawn_condition)))

        if self.termination_condition:
            graph.add((parent_uri, YAWL.terminationCondition, Literal(self.termination_condition)))

        return ExecutionResult(
            success=True,
            instance_ids=instance_ids,
            state=MIState.RUNNING,
            metadata={
                "pattern": self.pattern_id,
                "requires_sync": False,  # Dynamic - can't pre-determine count
                "parent_id": parent_id,
                "initial_instance_count": len(instance_ids),
                "spawn_condition": self.spawn_condition,
                "termination_condition": self.termination_condition,
            },
        )


def check_completion(graph: Graph, parent_id: str) -> bool:
    """Check if all MI instances have completed.

    Parameters
    ----------
    graph : Graph
        RDF graph containing workflow state
    parent_id : str
        Parent MI identifier

    Returns
    -------
    bool
        True if all required instances completed
    """
    parent_uri = URIRef(parent_id)

    # Get required and completed counts
    required: int | None = None
    completed: int | None = None

    for obj in graph.objects(parent_uri, YAWL.requiredInstances):
        required = int(cast(Literal, obj).value)
    for obj in graph.objects(parent_uri, YAWL.completedInstances):
        completed = int(cast(Literal, obj).value)

    if required is None or completed is None:
        return False

    return completed >= required


def mark_instance_complete(graph: Graph, instance_id: str) -> None:
    """Mark an MI instance as completed and update parent counter.

    Parameters
    ----------
    graph : Graph
        RDF graph containing workflow state
    instance_id : str
        Instance identifier to mark complete
    """
    instance_uri = URIRef(instance_id)

    # Update instance state
    graph.remove((instance_uri, YAWL.state, None))
    graph.add((instance_uri, YAWL.state, Literal(MIState.COMPLETED.value)))

    # Get parent and increment completed counter
    parent_uri = None
    for obj in graph.objects(instance_uri, YAWL.parentMI):
        parent_uri = obj
        break

    if parent_uri is None:
        return

    # Increment completed count
    current_count = 0
    for obj in graph.objects(parent_uri, YAWL.completedInstances):
        current_count = int(cast(Literal, obj).value)
        break

    graph.remove((parent_uri, YAWL.completedInstances, None))
    graph.add((parent_uri, YAWL.completedInstances, Literal(current_count + 1)))

    logger.info(
        "MI instance completed",
        extra={"instance_id": instance_id, "parent_id": str(parent_uri), "completed_count": current_count + 1},
    )
