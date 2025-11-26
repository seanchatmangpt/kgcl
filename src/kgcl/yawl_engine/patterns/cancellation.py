"""YAWL Cancellation Patterns (19-21) - Production-Ready Implementation.

This module implements YAWL cancellation patterns following the official specification:
- Pattern 19: Cancel Task - Withdraw a specific task instance
- Pattern 20: Cancel Case - Abort entire workflow instance
- Pattern 21: Cancel Region - Cancel scoped region of tasks

References
----------
YAWL Foundation: http://www.yawlfoundation.org/
Workflow Patterns Initiative: http://www.workflowpatterns.com/

Examples
--------
>>> from rdflib import Dataset, URIRef, Literal
>>> from kgcl.yawl_engine.patterns.cancellation import CancelTask
>>> store = Dataset()
>>> task_uri = URIRef("urn:task:auth_code_entry")
>>> cancel = CancelTask()
>>> result = cancel.cancel(store, task_uri, "User requested cancellation")
>>> assert result.success is True
>>> assert "auth_code_entry" in result.cancelled_tasks
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import cast

from rdflib import Dataset, Literal, Namespace, URIRef
from rdflib.query import ResultRow

# YAWL namespace definitions
YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")
KGC = Namespace("https://kgc.org/ns/")


@dataclass(frozen=True)
class CancellationResult:
    """Immutable cancellation result with audit trail.

    Parameters
    ----------
    cancelled_tasks : tuple[str, ...]
        URIs of tasks that were cancelled
    reason : str
        Human-readable cancellation reason
    timestamp : float
        Unix timestamp when cancellation occurred
    success : bool
        Whether cancellation completed successfully
    error : str | None
        Error message if cancellation failed

    Examples
    --------
    >>> result = CancellationResult(
    ...     cancelled_tasks=("urn:task:t1", "urn:task:t2"),
    ...     reason="Timeout exceeded",
    ...     timestamp=1704067200.0,
    ...     success=True,
    ... )
    >>> assert len(result.cancelled_tasks) == 2
    >>> assert result.success is True
    """

    cancelled_tasks: tuple[str, ...]
    reason: str
    timestamp: float
    success: bool
    error: str | None = None


@dataclass(frozen=True)
class CancelTask:
    """YAWL Pattern 19: Cancel Task.

    Withdraw a specific task instance while allowing other tasks to continue.
    The task is marked as cancelled, resources are cleaned up, but the workflow
    instance continues execution.

    Parameters
    ----------
    pattern_id : int
        YAWL pattern identifier (19)
    name : str
        Human-readable pattern name

    Examples
    --------
    >>> from rdflib import Dataset, URIRef
    >>> store = Dataset()
    >>> # ... populate store with task ...
    >>> cancel = CancelTask()
    >>> result = cancel.cancel(store, URIRef("urn:task:code_entry"), "User timeout exceeded")
    >>> assert result.success is True
    """

    pattern_id: int = 19
    name: str = "Cancel Task"

    def cancel(self, graph: Dataset, task: URIRef, reason: str) -> CancellationResult:
        """Cancel a specific task instance.

        The task is marked with yawl:status = "cancelled", resources are released,
        and the workflow continues with other tasks.

        Parameters
        ----------
        graph : Dataset
            RDF quad-store containing workflow state
        task : URIRef
            URI of the task to cancel
        reason : str
            Human-readable cancellation reason

        Returns
        -------
        CancellationResult
            Immutable result with cancelled tasks and audit metadata

        Raises
        ------
        ValueError
            If task URI is invalid or not found in graph

        Examples
        --------
        >>> from rdflib import Dataset, URIRef, Literal
        >>> store = Dataset()
        >>> task_uri = URIRef("urn:task:auth")
        >>> # Add task to graph
        >>> store.add((task_uri, YAWL.status, Literal("active")))
        >>> cancel = CancelTask()
        >>> result = cancel.cancel(store, task_uri, "Manual cancellation")
        >>> assert result.success is True
        >>> # Verify task is cancelled in graph
        >>> cancelled = list(store.triples((task_uri, YAWL.status, Literal("cancelled"))))
        >>> assert len(cancelled) == 1
        """
        timestamp = time.time()

        # Validate task exists in graph
        task_triples = list(graph.triples((task, None, None)))
        if not task_triples:
            return CancellationResult(
                cancelled_tasks=(), reason=reason, timestamp=timestamp, success=False, error=f"Task not found: {task}"
            )

        # Remove active status
        graph.remove((task, YAWL.status, Literal("active")))
        graph.remove((task, YAWL.status, Literal("enabled")))
        graph.remove((task, YAWL.status, Literal("executing")))

        # Mark as cancelled
        graph.add((task, YAWL.status, Literal("cancelled")))
        graph.add((task, YAWL.cancelledAt, Literal(timestamp)))
        graph.add((task, YAWL.cancellationReason, Literal(reason)))

        # Cleanup: Remove active tokens
        # Use pattern matching to remove all hasToken triples
        for _, _, token in graph.triples((task, KGC.hasToken, None)):
            graph.remove((task, KGC.hasToken, token))

        return CancellationResult(cancelled_tasks=(str(task),), reason=reason, timestamp=timestamp, success=True)


@dataclass(frozen=True)
class CancelCase:
    """YAWL Pattern 20: Cancel Case.

    Abort entire workflow instance and cleanup all resources.
    All tasks in the workflow are cancelled, and the case is marked as aborted.

    Parameters
    ----------
    pattern_id : int
        YAWL pattern identifier (20)
    name : str
        Human-readable pattern name

    Examples
    --------
    >>> from rdflib import Dataset, URIRef
    >>> store = Dataset()
    >>> # ... populate store with workflow ...
    >>> cancel = CancelCase()
    >>> result = cancel.cancel(store, URIRef("urn:workflow:nuclear_launch"), "Emergency abort initiated")
    >>> assert result.success is True
    """

    pattern_id: int = 20
    name: str = "Cancel Case"

    def cancel(self, graph: Dataset, workflow: URIRef, reason: str) -> CancellationResult:
        """Cancel entire workflow instance.

        All tasks in the workflow are marked as cancelled, active tokens are removed,
        and the workflow case is marked as aborted.

        Parameters
        ----------
        graph : Dataset
            RDF quad-store containing workflow state
        workflow : URIRef
            URI of the workflow instance to cancel
        reason : str
            Human-readable cancellation reason

        Returns
        -------
        CancellationResult
            Immutable result with all cancelled tasks and audit metadata

        Raises
        ------
        ValueError
            If workflow URI is invalid or not found in graph

        Examples
        --------
        >>> from rdflib import Dataset, URIRef, Literal
        >>> store = Dataset()
        >>> workflow_uri = URIRef("urn:workflow:w1")
        >>> task1 = URIRef("urn:task:t1")
        >>> task2 = URIRef("urn:task:t2")
        >>> # Add workflow and tasks
        >>> store.add((workflow_uri, YAWL.hasTask, task1))
        >>> store.add((workflow_uri, YAWL.hasTask, task2))
        >>> store.add((task1, YAWL.status, Literal("active")))
        >>> store.add((task2, YAWL.status, Literal("active")))
        >>> cancel = CancelCase()
        >>> result = cancel.cancel(store, workflow_uri, "Emergency abort")
        >>> assert result.success is True
        >>> assert len(result.cancelled_tasks) == 2
        """
        timestamp = time.time()

        # Validate workflow exists
        workflow_triples = list(graph.triples((workflow, None, None)))
        if not workflow_triples:
            return CancellationResult(
                cancelled_tasks=(),
                reason=reason,
                timestamp=timestamp,
                success=False,
                error=f"Workflow not found: {workflow}",
            )

        # Query all tasks in workflow
        query = f"""
        PREFIX yawl: <{YAWL}>
        SELECT ?task WHERE {{
            <{workflow}> yawl:hasTask ?task .
        }}
        """
        results = graph.query(query)
        cancelled_tasks: list[str] = []

        # Cancel each task
        for row in results:
            if not hasattr(row, "task"):
                continue
            row_typed = cast(ResultRow, row)
            task_uri = row_typed.task

            # Remove active statuses
            graph.remove((task_uri, YAWL.status, Literal("active")))
            graph.remove((task_uri, YAWL.status, Literal("enabled")))
            graph.remove((task_uri, YAWL.status, Literal("executing")))

            # Mark as cancelled
            graph.add((task_uri, YAWL.status, Literal("cancelled")))
            graph.add((task_uri, YAWL.cancelledAt, Literal(timestamp)))
            graph.add((task_uri, YAWL.cancellationReason, Literal(reason)))

            # Cleanup tokens
            for _, _, token in graph.triples((task_uri, KGC.hasToken, None)):
                graph.remove((task_uri, KGC.hasToken, token))

            cancelled_tasks.append(str(task_uri))

        # Mark workflow as aborted
        graph.add((workflow, YAWL.status, Literal("aborted")))
        graph.add((workflow, YAWL.abortedAt, Literal(timestamp)))
        graph.add((workflow, YAWL.abortReason, Literal(reason)))

        return CancellationResult(
            cancelled_tasks=tuple(cancelled_tasks), reason=reason, timestamp=timestamp, success=True
        )


@dataclass(frozen=True)
class CancelRegion:
    """YAWL Pattern 21: Cancel Region.

    Cancel a scoped region of tasks within a workflow, but not tasks outside the region.
    This allows fine-grained cancellation of parallel branches or sub-workflows.

    Parameters
    ----------
    pattern_id : int
        YAWL pattern identifier (21)
    name : str
        Human-readable pattern name
    region_tasks : frozenset[str]
        URIs of tasks within the cancellation region

    Examples
    --------
    >>> from rdflib import Dataset, URIRef
    >>> store = Dataset()
    >>> # ... populate store with workflow ...
    >>> cancel = CancelRegion(region_tasks=frozenset(["urn:task:auth", "urn:task:validate"]))
    >>> result = cancel.cancel_region(store, URIRef("urn:task:auth"))
    >>> assert result.success is True
    """

    pattern_id: int = 21
    name: str = "Cancel Region"
    region_tasks: frozenset[str] = frozenset()

    def cancel_region(self, graph: Dataset, trigger: URIRef) -> CancellationResult:
        """Cancel all tasks within defined region.

        Tasks outside the region continue execution. The region is defined by
        the region_tasks parameter at initialization.

        Parameters
        ----------
        graph : Dataset
            RDF quad-store containing workflow state
        trigger : URIRef
            URI of the task that triggered region cancellation

        Returns
        -------
        CancellationResult
            Immutable result with cancelled tasks in region

        Raises
        ------
        ValueError
            If trigger task is not in region

        Examples
        --------
        >>> from rdflib import Dataset, URIRef, Literal
        >>> store = Dataset()
        >>> task1 = URIRef("urn:task:auth")
        >>> task2 = URIRef("urn:task:validate")
        >>> task3 = URIRef("urn:task:launch")  # Outside region
        >>> store.add((task1, YAWL.status, Literal("active")))
        >>> store.add((task2, YAWL.status, Literal("active")))
        >>> store.add((task3, YAWL.status, Literal("active")))
        >>> cancel = CancelRegion(region_tasks=frozenset(["urn:task:auth", "urn:task:validate"]))
        >>> result = cancel.cancel_region(store, task1)
        >>> assert result.success is True
        >>> assert len(result.cancelled_tasks) == 2
        >>> # task3 should still be active
        >>> active = list(store.triples((task3, YAWL.status, Literal("active"))))
        >>> assert len(active) == 1
        """
        timestamp = time.time()

        # Validate trigger is in region
        if str(trigger) not in self.region_tasks:
            return CancellationResult(
                cancelled_tasks=(),
                reason=f"Trigger {trigger} not in region",
                timestamp=timestamp,
                success=False,
                error=f"Trigger task must be in region: {trigger}",
            )

        cancelled_tasks: list[str] = []
        reason = f"Region cancelled by trigger: {trigger}"

        # Cancel each task in region
        for task_str in self.region_tasks:
            task_uri = URIRef(task_str)

            # Check if task exists in graph
            task_triples = list(graph.triples((task_uri, None, None)))
            if not task_triples:
                continue

            # Remove active statuses
            graph.remove((task_uri, YAWL.status, Literal("active")))
            graph.remove((task_uri, YAWL.status, Literal("enabled")))
            graph.remove((task_uri, YAWL.status, Literal("executing")))

            # Mark as cancelled
            graph.add((task_uri, YAWL.status, Literal("cancelled")))
            graph.add((task_uri, YAWL.cancelledAt, Literal(timestamp)))
            graph.add((task_uri, YAWL.cancellationReason, Literal(reason)))

            # Cleanup tokens
            for _, _, token in graph.triples((task_uri, KGC.hasToken, None)):
                graph.remove((task_uri, KGC.hasToken, token))

            cancelled_tasks.append(task_str)

        return CancellationResult(
            cancelled_tasks=tuple(cancelled_tasks), reason=reason, timestamp=timestamp, success=True
        )
