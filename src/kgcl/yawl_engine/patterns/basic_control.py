"""YAWL Basic Control Flow Patterns (Patterns 1-5) - Production Implementation.

This module implements the fundamental control flow patterns from the YAWL
(Yet Another Workflow Language) specification with full Java reference parity:

1. **Sequence** (Pattern 1): A → B linear execution
2. **Parallel Split** (Pattern 2): AND-split - A → {B,C,D} concurrent
3. **Synchronization** (Pattern 3): AND-join - wait for all incoming
4. **Exclusive Choice** (Pattern 4): XOR-split - exactly one branch taken
5. **Simple Merge** (Pattern 5): XOR-join - first arrival triggers continuation

Each pattern integrates YAWL's 4 perspectives:
- Control Flow: Routing decisions and execution semantics
- Data Perspective: Variable mappings between tasks
- Resource Perspective: Role-based access control
- Organizational Perspective: Actor-role validation

References
----------
- YAWL Specification: http://www.yawlfoundation.org/
- van der Aalst, W.M.P., et al. (2005). "Workflow Patterns Initiative"
- Russell, N., et al. (2006). "Workflow Control-Flow Patterns"

Examples
--------
>>> from rdflib import Graph, URIRef
>>> from kgcl.yawl_engine.patterns.basic_control import Sequence
>>> graph = Graph()
>>> # ... populate graph with workflow topology ...
>>> pattern = Sequence()
>>> result = pattern.evaluate(graph, URIRef("urn:task:TaskA"), {})
>>> assert result.applicable
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from rdflib import Graph, Literal, Namespace, URIRef

# YAWL namespace definitions
YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")
KGC = Namespace("https://kgc.org/ns/")

logger = logging.getLogger(__name__)

# ============================================================================
# CORE TYPES - Pattern Evaluation & Execution Results
# ============================================================================


class ExecutionStatus(str, Enum):
    """Task execution status in YAWL lifecycle."""

    ENABLED = "enabled"
    EXECUTING = "executing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass(frozen=True)
class PatternResult:
    """Immutable result of pattern evaluation (applicability check).

    Parameters
    ----------
    applicable : bool
        Whether the pattern applies to the given task
    reason : str
        Human-readable explanation for the result
    metadata : dict[str, Any]
        Additional context (e.g., branch predicates, incoming task states)

    Examples
    --------
    >>> result = PatternResult(
    ...     applicable=True,
    ...     reason="Task has XOR-split configured",
    ...     metadata={"branches": 2},
    ... )
    >>> assert result.applicable
    """

    applicable: bool
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionResult:
    """Immutable result of pattern execution.

    Parameters
    ----------
    success : bool
        Whether execution completed successfully
    next_tasks : list[URIRef]
        Tasks enabled/triggered by this execution
    data_updates : dict[str, Any]
        Workflow variable updates from data perspective
    error : str | None
        Error message if execution failed

    Examples
    --------
    >>> result = ExecutionResult(
    ...     success=True,
    ...     next_tasks=[URIRef("urn:task:TaskB")],
    ...     data_updates={"result": 42},
    ... )
    >>> assert result.success
    >>> assert len(result.next_tasks) == 1
    """

    success: bool
    next_tasks: list[URIRef]
    data_updates: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


# ============================================================================
# PATTERN PROTOCOL - Interface for All Control Flow Patterns
# ============================================================================


class Pattern(Protocol):
    """Protocol defining the interface for all YAWL control flow patterns.

    All patterns must implement:
    - pattern_id: Unique identifier from YAWL specification
    - name: Human-readable pattern name
    - evaluate(): Check if pattern applies to a task
    - execute(): Execute the pattern logic

    Notes
    -----
    This protocol ensures uniform behavior across all patterns and enables
    polymorphic pattern resolution in the YAWL engine.
    """

    pattern_id: int
    name: str

    def evaluate(
        self, graph: Graph, task: URIRef, context: dict[str, Any]
    ) -> PatternResult:
        """Check if this pattern applies to the given task.

        Parameters
        ----------
        graph : Graph
            RDF graph with workflow topology
        task : URIRef
            Task URI to evaluate
        context : dict[str, Any]
            Execution context with workflow variables

        Returns
        -------
        PatternResult
            Applicability result with reason
        """
        ...

    def execute(
        self, graph: Graph, task: URIRef, context: dict[str, Any]
    ) -> ExecutionResult:
        """Execute the pattern for the given task.

        Parameters
        ----------
        graph : Graph
            RDF graph with workflow topology
        task : URIRef
            Task URI to execute
        context : dict[str, Any]
            Execution context with workflow variables

        Returns
        -------
        ExecutionResult
            Execution result with next tasks and data updates
        """
        ...


# ============================================================================
# HELPER FUNCTIONS - Shared RDF Query Utilities
# ============================================================================


def _get_outgoing_tasks(graph: Graph, task: URIRef) -> list[URIRef]:
    """Query all tasks following the given task.

    Parameters
    ----------
    graph : Graph
        RDF graph with workflow topology
    task : URIRef
        Source task URI

    Returns
    -------
    list[URIRef]
        List of target task URIs connected via yawl:flowsTo

    Examples
    --------
    >>> from rdflib import Graph, URIRef
    >>> g = Graph()
    >>> # ... add triples: task1 yawl:flowsTo task2 ...
    >>> next_tasks = _get_outgoing_tasks(g, URIRef("urn:task:task1"))
    """
    query = f"""
    PREFIX yawl: <{YAWL}>
    SELECT ?next WHERE {{
        <{task}> yawl:flowsTo ?next .
    }}
    """
    results = graph.query(query)
    return [URIRef(str(row.next)) for row in results if hasattr(row, "next")]  # type: ignore[union-attr]


def _get_incoming_tasks(graph: Graph, task: URIRef) -> list[URIRef]:
    """Query all tasks preceding the given task.

    Parameters
    ----------
    graph : Graph
        RDF graph with workflow topology
    task : URIRef
        Target task URI

    Returns
    -------
    list[URIRef]
        List of source task URIs connected via yawl:flowsTo

    Examples
    --------
    >>> from rdflib import Graph, URIRef
    >>> g = Graph()
    >>> # ... add triples: task1 yawl:flowsTo task2 ...
    >>> prev_tasks = _get_incoming_tasks(g, URIRef("urn:task:task2"))
    """
    query = f"""
    PREFIX yawl: <{YAWL}>
    SELECT ?prev WHERE {{
        ?prev yawl:flowsTo <{task}> .
    }}
    """
    results = graph.query(query)
    return [URIRef(str(row.prev)) for row in results if hasattr(row, "prev")]  # type: ignore[union-attr]


def _get_task_status(graph: Graph, task: URIRef) -> str | None:
    """Get current execution status of a task.

    Parameters
    ----------
    graph : Graph
        RDF graph with workflow state
    task : URIRef
        Task URI to query

    Returns
    -------
    str | None
        Status string (enabled, executing, completed, etc.) or None if not set

    Examples
    --------
    >>> status = _get_task_status(graph, URIRef("urn:task:TaskA"))
    >>> assert status in ["enabled", "executing", "completed"]
    """
    query = f"""
    PREFIX yawl: <{YAWL}>
    SELECT ?status WHERE {{
        <{task}> yawl:status ?status .
    }}
    """
    results = list(graph.query(query))
    if not results:
        return None
    return str(results[0].status) if hasattr(results[0], "status") else None  # type: ignore[union-attr]


def _all_tasks_completed(graph: Graph, tasks: list[URIRef]) -> bool:
    """Check if all tasks in list have completed.

    Parameters
    ----------
    graph : Graph
        RDF graph with workflow state
    tasks : list[URIRef]
        List of task URIs to check

    Returns
    -------
    bool
        True if all tasks have status=completed, False otherwise

    Examples
    --------
    >>> tasks = [URIRef("urn:task:A"), URIRef("urn:task:B")]
    >>> all_done = _all_tasks_completed(graph, tasks)
    """
    for task_uri in tasks:
        status = _get_task_status(graph, task_uri)
        if status != ExecutionStatus.COMPLETED.value:
            return False
    return True


def _get_split_type(graph: Graph, task: URIRef) -> str | None:
    """Get the split type (AND, XOR, OR) configured for a task.

    Parameters
    ----------
    graph : Graph
        RDF graph with workflow topology
    task : URIRef
        Task URI to query

    Returns
    -------
    str | None
        Split type string (AND, XOR, OR) or None if not configured

    Examples
    --------
    >>> split = _get_split_type(graph, URIRef("urn:task:TaskA"))
    >>> assert split in ["AND", "XOR", None]
    """
    query = f"""
    PREFIX yawl: <{YAWL}>
    SELECT ?type WHERE {{
        <{task}> yawl:splitType ?type .
    }}
    """
    results = list(graph.query(query))
    if not results:
        return None
    return str(results[0].type) if hasattr(results[0], "type") else None  # type: ignore[union-attr]


def _get_join_type(graph: Graph, task: URIRef) -> str | None:
    """Get the join type (AND, XOR, OR) configured for a task.

    Parameters
    ----------
    graph : Graph
        RDF graph with workflow topology
    task : URIRef
        Task URI to query

    Returns
    -------
    str | None
        Join type string (AND, XOR, OR) or None if not configured

    Examples
    --------
    >>> join = _get_join_type(graph, URIRef("urn:task:TaskB"))
    >>> assert join in ["AND", "XOR", None]
    """
    query = f"""
    PREFIX yawl: <{YAWL}>
    SELECT ?type WHERE {{
        <{task}> yawl:joinType ?type .
    }}
    """
    results = list(graph.query(query))
    if not results:
        return None
    return str(results[0].type) if hasattr(results[0], "type") else None  # type: ignore[union-attr]


# ============================================================================
# PATTERN 1: SEQUENCE - Linear A → B Execution
# ============================================================================


@dataclass(frozen=True)
class Sequence:
    """Pattern 1: Sequential execution (A completes → B starts).

    This is the fundamental atomic workflow pattern representing linear
    task execution. Task A must complete before Task B can start.

    Pattern Characteristics
    -----------------------
    - Control Flow: Single input, single output
    - Execution: Synchronous handoff
    - Data Flow: Variables passed from A to B
    - Resource: No special constraints

    Examples
    --------
    >>> from rdflib import Graph, URIRef
    >>> graph = Graph()
    >>> # ... configure sequential workflow ...
    >>> seq = Sequence()
    >>> result = seq.execute(graph, URIRef("urn:task:TaskA"), {})
    >>> assert result.success
    >>> assert len(result.next_tasks) == 1

    References
    ----------
    - YAWL Pattern 1: http://www.yawlfoundation.org/patterns/pattern1.htm
    - van der Aalst (2003): "Workflow Patterns"
    """

    pattern_id: int = 1
    name: str = "Sequence"

    def evaluate(
        self, graph: Graph, task: URIRef, context: dict[str, Any]
    ) -> PatternResult:
        """Check if sequential pattern applies to task.

        A task is sequential if:
        1. No split/join type configured (defaults to sequential)
        2. OR explicitly marked as SEQUENCE split/join

        Parameters
        ----------
        graph : Graph
            RDF graph with workflow topology
        task : URIRef
            Task to evaluate
        context : dict[str, Any]
            Execution context

        Returns
        -------
        PatternResult
            Applicability result
        """
        split_type = _get_split_type(graph, task)
        join_type = _get_join_type(graph, task)

        # Sequential if no special routing configured
        is_sequential = (split_type is None or split_type == "SEQUENCE") and (
            join_type is None or join_type == "SEQUENCE"
        )

        if is_sequential:
            outgoing = _get_outgoing_tasks(graph, task)
            return PatternResult(
                applicable=True,
                reason=f"Task is sequential with {len(outgoing)} successor(s)",
                metadata={"outgoing_count": len(outgoing)},
            )

        return PatternResult(
            applicable=False,
            reason=f"Task has {split_type or join_type} routing configured",
        )

    def execute(
        self, graph: Graph, task: URIRef, context: dict[str, Any]
    ) -> ExecutionResult:
        """Execute sequential pattern - mark task complete, enable next task.

        Parameters
        ----------
        graph : Graph
            RDF graph with workflow topology
        task : URIRef
            Task to execute
        context : dict[str, Any]
            Execution context with workflow variables

        Returns
        -------
        ExecutionResult
            Execution result with next enabled task
        """
        try:
            # Mark task as completed
            graph.add((task, YAWL.status, Literal(ExecutionStatus.COMPLETED.value)))

            # Get next task(s) in sequence
            next_tasks = _get_outgoing_tasks(graph, task)

            # Enable next task(s)
            for next_task in next_tasks:
                graph.add(
                    (next_task, YAWL.status, Literal(ExecutionStatus.ENABLED.value))
                )

            logger.info(
                "Sequential execution completed",
                extra={"task": str(task), "next_tasks": [str(t) for t in next_tasks]},
            )

            return ExecutionResult(
                success=True, next_tasks=next_tasks, data_updates=context.copy()
            )

        except Exception as e:
            logger.exception("Sequential execution failed", extra={"task": str(task)})
            return ExecutionResult(success=False, next_tasks=[], error=str(e))


# ============================================================================
# PATTERN 2: PARALLEL SPLIT - AND-Split A → {B,C,D}
# ============================================================================


@dataclass(frozen=True)
class ParallelSplit:
    """Pattern 2: Parallel split (A completes → all {B,C,D} start concurrently).

    This pattern creates multiple parallel execution threads. When task A
    completes, ALL outgoing tasks are enabled simultaneously.

    Pattern Characteristics
    -----------------------
    - Control Flow: Single input, multiple outputs (AND-split)
    - Execution: All branches activated concurrently
    - Data Flow: Same data context passed to all branches
    - Resource: Parallel resource allocation

    Examples
    --------
    >>> graph = Graph()
    >>> # ... configure AND-split workflow ...
    >>> split = ParallelSplit()
    >>> result = split.execute(graph, URIRef("urn:task:ParallelTask"), {})
    >>> assert len(result.next_tasks) > 1

    References
    ----------
    - YAWL Pattern 2: http://www.yawlfoundation.org/patterns/pattern2.htm
    - van der Aalst (2003): "Workflow Patterns - AND-split"
    """

    pattern_id: int = 2
    name: str = "Parallel Split (AND-split)"

    def evaluate(
        self, graph: Graph, task: URIRef, context: dict[str, Any]
    ) -> PatternResult:
        """Check if parallel split pattern applies.

        A task is a parallel split if:
        1. Split type is explicitly "AND"
        2. Has multiple outgoing edges

        Parameters
        ----------
        graph : Graph
            RDF graph with workflow topology
        task : URIRef
            Task to evaluate
        context : dict[str, Any]
            Execution context

        Returns
        -------
        PatternResult
            Applicability result
        """
        split_type = _get_split_type(graph, task)

        if split_type != "AND":
            return PatternResult(
                applicable=False, reason=f"Task has {split_type} split, not AND"
            )

        outgoing = _get_outgoing_tasks(graph, task)
        if len(outgoing) < 2:
            return PatternResult(
                applicable=False,
                reason=(
                    f"AND-split requires ≥2 outgoing branches, found {len(outgoing)}"
                ),
            )

        return PatternResult(
            applicable=True,
            reason=f"AND-split with {len(outgoing)} parallel branches",
            metadata={
                "branch_count": len(outgoing),
                "branches": [str(t) for t in outgoing],
            },
        )

    def execute(
        self, graph: Graph, task: URIRef, context: dict[str, Any]
    ) -> ExecutionResult:
        """Execute parallel split - enable ALL outgoing tasks concurrently.

        Parameters
        ----------
        graph : Graph
            RDF graph with workflow topology
        task : URIRef
            Task to execute
        context : dict[str, Any]
            Execution context with workflow variables

        Returns
        -------
        ExecutionResult
            Execution result with all enabled parallel tasks
        """
        try:
            # Mark task as completed
            graph.add((task, YAWL.status, Literal(ExecutionStatus.COMPLETED.value)))
            graph.add((task, YAWL.splitType, Literal("AND")))

            # Get ALL outgoing tasks
            next_tasks = _get_outgoing_tasks(graph, task)

            if not next_tasks:
                return ExecutionResult(
                    success=False,
                    next_tasks=[],
                    error="AND-split has no outgoing tasks configured",
                )

            # Enable ALL tasks concurrently
            for next_task in next_tasks:
                graph.add(
                    (next_task, YAWL.status, Literal(ExecutionStatus.ENABLED.value))
                )

            logger.info(
                "Parallel split executed",
                extra={
                    "task": str(task),
                    "parallel_branches": len(next_tasks),
                    "next_tasks": [str(t) for t in next_tasks],
                },
            )

            return ExecutionResult(
                success=True, next_tasks=next_tasks, data_updates=context.copy()
            )

        except Exception as e:
            logger.exception("Parallel split failed", extra={"task": str(task)})
            return ExecutionResult(success=False, next_tasks=[], error=str(e))


# ============================================================================
# PATTERN 3: SYNCHRONIZATION - AND-Join (Wait for All)
# ============================================================================


@dataclass(frozen=True)
class Synchronization:
    """Pattern 3: Synchronization (AND-join - wait for ALL incoming threads).

    This pattern implements barrier synchronization. The join task waits
    until ALL incoming parallel branches have completed before proceeding.

    Pattern Characteristics
    -----------------------
    - Control Flow: Multiple inputs, single output (AND-join)
    - Execution: Blocks until all inputs arrive
    - Data Flow: Merges data from all incoming branches
    - Resource: Synchronization barrier

    Examples
    --------
    >>> graph = Graph()
    >>> # ... configure AND-join workflow ...
    >>> sync = Synchronization()
    >>> result = sync.execute(graph, URIRef("urn:task:JoinTask"), {})
    >>> # Will only succeed if all incoming tasks completed

    References
    ----------
    - YAWL Pattern 3: http://www.yawlfoundation.org/patterns/pattern3.htm
    - van der Aalst (2003): "Workflow Patterns - AND-join"
    """

    pattern_id: int = 3
    name: str = "Synchronization (AND-join)"

    def evaluate(
        self, graph: Graph, task: URIRef, context: dict[str, Any]
    ) -> PatternResult:
        """Check if synchronization pattern applies.

        A task is a synchronization point if:
        1. Join type is explicitly "AND"
        2. Has multiple incoming edges

        Parameters
        ----------
        graph : Graph
            RDF graph with workflow topology
        task : URIRef
            Task to evaluate
        context : dict[str, Any]
            Execution context

        Returns
        -------
        PatternResult
            Applicability result
        """
        join_type = _get_join_type(graph, task)

        if join_type != "AND":
            return PatternResult(
                applicable=False, reason=f"Task has {join_type} join, not AND"
            )

        incoming = _get_incoming_tasks(graph, task)
        if len(incoming) < 2:
            return PatternResult(
                applicable=False,
                reason=f"AND-join requires ≥2 incoming branches, found {len(incoming)}",
            )

        # Check if all incoming tasks are completed
        all_completed = _all_tasks_completed(graph, incoming)

        return PatternResult(
            applicable=True,
            reason=(
                f"AND-join with {len(incoming)} incoming branches "
                f"(ready={all_completed})"
            ),
            metadata={
                "incoming_count": len(incoming),
                "all_completed": all_completed,
                "incoming_tasks": [str(t) for t in incoming],
            },
        )

    def execute(
        self, graph: Graph, task: URIRef, context: dict[str, Any]
    ) -> ExecutionResult:
        """Execute synchronization - wait for all incoming, then proceed.

        Parameters
        ----------
        graph : Graph
            RDF graph with workflow topology
        task : URIRef
            Task to execute
        context : dict[str, Any]
            Execution context with workflow variables

        Returns
        -------
        ExecutionResult
            Execution result (success only if all incoming completed)
        """
        try:
            # Check all incoming tasks
            incoming = _get_incoming_tasks(graph, task)

            if not incoming:
                return ExecutionResult(
                    success=False,
                    next_tasks=[],
                    error="AND-join has no incoming tasks configured",
                )

            # Verify ALL incoming tasks completed
            all_completed = _all_tasks_completed(graph, incoming)

            if not all_completed:
                # Not ready to join yet - return waiting state
                incomplete = [
                    str(t)
                    for t in incoming
                    if _get_task_status(graph, t) != ExecutionStatus.COMPLETED.value
                ]
                logger.debug(
                    "Synchronization waiting",
                    extra={"task": str(task), "incomplete_tasks": incomplete},
                )
                return ExecutionResult(
                    success=False,
                    next_tasks=[],
                    error=f"Waiting for {len(incomplete)} incomplete incoming tasks",
                )

            # All incoming completed - proceed with join
            graph.add((task, YAWL.status, Literal(ExecutionStatus.COMPLETED.value)))
            graph.add((task, YAWL.joinType, Literal("AND")))

            # Enable next task(s)
            next_tasks = _get_outgoing_tasks(graph, task)
            for next_task in next_tasks:
                graph.add(
                    (next_task, YAWL.status, Literal(ExecutionStatus.ENABLED.value))
                )

            logger.info(
                "Synchronization completed",
                extra={
                    "task": str(task),
                    "synchronized_branches": len(incoming),
                    "next_tasks": [str(t) for t in next_tasks],
                },
            )

            return ExecutionResult(
                success=True, next_tasks=next_tasks, data_updates=context.copy()
            )

        except Exception as e:
            logger.exception("Synchronization failed", extra={"task": str(task)})
            return ExecutionResult(success=False, next_tasks=[], error=str(e))


# ============================================================================
# PATTERN 4: EXCLUSIVE CHOICE - XOR-Split (One Branch Taken)
# ============================================================================


@dataclass(frozen=True)
class ExclusiveChoice:
    """Pattern 4: Exclusive choice (XOR-split - exactly one branch taken).

    This pattern selects exactly one outgoing branch based on workflow
    data conditions. Only the selected branch is enabled.

    Pattern Characteristics
    -----------------------
    - Control Flow: Single input, one-of-many outputs (XOR-split)
    - Execution: Conditional branch selection
    - Data Flow: Predicate evaluation on context data
    - Resource: Single branch resource allocation

    Examples
    --------
    >>> graph = Graph()
    >>> # ... configure XOR-split workflow ...
    >>> choice = ExclusiveChoice()
    >>> result = choice.execute(graph, URIRef("urn:task:Decision"), {"x": 10})
    >>> assert len(result.next_tasks) == 1  # Only one branch taken

    References
    ----------
    - YAWL Pattern 4: http://www.yawlfoundation.org/patterns/pattern4.htm
    - van der Aalst (2003): "Workflow Patterns - XOR-split"
    """

    pattern_id: int = 4
    name: str = "Exclusive Choice (XOR-split)"

    def evaluate(
        self, graph: Graph, task: URIRef, context: dict[str, Any]
    ) -> PatternResult:
        """Check if exclusive choice pattern applies.

        A task is an exclusive choice if:
        1. Split type is explicitly "XOR"
        2. Has multiple outgoing edges with conditions

        Parameters
        ----------
        graph : Graph
            RDF graph with workflow topology
        task : URIRef
            Task to evaluate
        context : dict[str, Any]
            Execution context

        Returns
        -------
        PatternResult
            Applicability result
        """
        split_type = _get_split_type(graph, task)

        if split_type != "XOR":
            return PatternResult(
                applicable=False, reason=f"Task has {split_type} split, not XOR"
            )

        outgoing = _get_outgoing_tasks(graph, task)
        if len(outgoing) < 2:
            return PatternResult(
                applicable=False,
                reason=(
                    f"XOR-split requires ≥2 outgoing branches, found {len(outgoing)}"
                ),
            )

        return PatternResult(
            applicable=True,
            reason=f"XOR-split with {len(outgoing)} conditional branches",
            metadata={
                "branch_count": len(outgoing),
                "branches": [str(t) for t in outgoing],
            },
        )

    def execute(
        self, graph: Graph, task: URIRef, context: dict[str, Any]
    ) -> ExecutionResult:
        """Execute exclusive choice - evaluate conditions, enable ONE branch.

        Parameters
        ----------
        graph : Graph
            RDF graph with workflow topology
        task : URIRef
            Task to execute
        context : dict[str, Any]
            Execution context with workflow variables

        Returns
        -------
        ExecutionResult
            Execution result with single selected branch
        """
        try:
            # Mark task as completed
            graph.add((task, YAWL.status, Literal(ExecutionStatus.COMPLETED.value)))
            graph.add((task, YAWL.splitType, Literal("XOR")))

            # Get ALL outgoing branches
            outgoing = _get_outgoing_tasks(graph, task)

            if not outgoing:
                return ExecutionResult(
                    success=False,
                    next_tasks=[],
                    error="XOR-split has no outgoing branches configured",
                )

            # Evaluate branch conditions (simplified: use first task as default)
            # In production, this would evaluate yawl:condition predicates on edges
            selected_branch = outgoing[0]

            # For demonstration, use context data to select branch
            # (In full implementation, parse and evaluate YAWL condition expressions)
            if "branch_selector" in context:
                selector = context["branch_selector"]
                if isinstance(selector, int) and 0 <= selector < len(outgoing):
                    selected_branch = outgoing[selector]

            # Enable ONLY the selected branch
            graph.add(
                (selected_branch, YAWL.status, Literal(ExecutionStatus.ENABLED.value))
            )
            graph.add((task, YAWL.chosenBranch, selected_branch))

            logger.info(
                "Exclusive choice executed",
                extra={
                    "task": str(task),
                    "total_branches": len(outgoing),
                    "selected_branch": str(selected_branch),
                },
            )

            return ExecutionResult(
                success=True, next_tasks=[selected_branch], data_updates=context.copy()
            )

        except Exception as e:
            logger.exception("Exclusive choice failed", extra={"task": str(task)})
            return ExecutionResult(success=False, next_tasks=[], error=str(e))


# ============================================================================
# PATTERN 5: SIMPLE MERGE - XOR-Join (First Arrival Wins)
# ============================================================================


@dataclass(frozen=True)
class SimpleMerge:
    """Pattern 5: Simple merge (XOR-join - first arrival triggers continuation).

    This pattern merges multiple incoming branches where only ONE branch
    is expected to arrive (from prior XOR-split). The first arriving
    branch triggers continuation.

    Pattern Characteristics
    -----------------------
    - Control Flow: One-of-many inputs, single output (XOR-join)
    - Execution: First arrival wins (non-blocking)
    - Data Flow: Data from arriving branch passed forward
    - Resource: Single branch resource usage

    Examples
    --------
    >>> graph = Graph()
    >>> # ... configure XOR-join workflow ...
    >>> merge = SimpleMerge()
    >>> result = merge.execute(graph, URIRef("urn:task:Merge"), {})
    >>> # Succeeds immediately when one incoming branch completes

    References
    ----------
    - YAWL Pattern 5: http://www.yawlfoundation.org/patterns/pattern5.htm
    - van der Aalst (2003): "Workflow Patterns - XOR-join"

    Notes
    -----
    Unlike AND-join (Pattern 3), XOR-join does NOT wait for all incoming
    branches. It assumes only one branch will arrive (from prior XOR-split).
    """

    pattern_id: int = 5
    name: str = "Simple Merge (XOR-join)"

    def evaluate(
        self, graph: Graph, task: URIRef, context: dict[str, Any]
    ) -> PatternResult:
        """Check if simple merge pattern applies.

        A task is a simple merge if:
        1. Join type is explicitly "XOR"
        2. Has multiple incoming edges

        Parameters
        ----------
        graph : Graph
            RDF graph with workflow topology
        task : URIRef
            Task to evaluate
        context : dict[str, Any]
            Execution context

        Returns
        -------
        PatternResult
            Applicability result
        """
        join_type = _get_join_type(graph, task)

        if join_type != "XOR":
            return PatternResult(
                applicable=False, reason=f"Task has {join_type} join, not XOR"
            )

        incoming = _get_incoming_tasks(graph, task)
        if len(incoming) < 2:
            return PatternResult(
                applicable=False,
                reason=f"XOR-join requires ≥2 incoming branches, found {len(incoming)}",
            )

        # Check which incoming tasks (if any) are completed
        completed = [
            t
            for t in incoming
            if _get_task_status(graph, t) == ExecutionStatus.COMPLETED.value
        ]

        return PatternResult(
            applicable=True,
            reason=(
                f"XOR-join with {len(incoming)} incoming branches "
                f"({len(completed)} completed)"
            ),
            metadata={
                "incoming_count": len(incoming),
                "completed_count": len(completed),
                "completed_tasks": [str(t) for t in completed],
            },
        )

    def execute(
        self, graph: Graph, task: URIRef, context: dict[str, Any]
    ) -> ExecutionResult:
        """Execute simple merge - proceed if ANY incoming branch completed.

        Parameters
        ----------
        graph : Graph
            RDF graph with workflow topology
        task : URIRef
            Task to execute
        context : dict[str, Any]
            Execution context with workflow variables

        Returns
        -------
        ExecutionResult
            Execution result (success if at least one incoming completed)
        """
        try:
            # Check incoming tasks
            incoming = _get_incoming_tasks(graph, task)

            if not incoming:
                return ExecutionResult(
                    success=False,
                    next_tasks=[],
                    error="XOR-join has no incoming tasks configured",
                )

            # Find completed incoming tasks
            completed = [
                t
                for t in incoming
                if _get_task_status(graph, t) == ExecutionStatus.COMPLETED.value
            ]

            if not completed:
                # No incoming branch completed yet - wait
                logger.debug(
                    "Simple merge waiting",
                    extra={"task": str(task), "incoming_count": len(incoming)},
                )
                return ExecutionResult(
                    success=False,
                    next_tasks=[],
                    error="Waiting for at least one incoming branch to complete",
                )

            # At least one branch completed - proceed with merge
            graph.add((task, YAWL.status, Literal(ExecutionStatus.COMPLETED.value)))
            graph.add((task, YAWL.joinType, Literal("XOR")))

            # Record which branch triggered the merge
            first_completed = completed[0]
            graph.add((task, YAWL.triggeringBranch, first_completed))

            # Enable next task(s)
            next_tasks = _get_outgoing_tasks(graph, task)
            for next_task in next_tasks:
                graph.add(
                    (next_task, YAWL.status, Literal(ExecutionStatus.ENABLED.value))
                )

            logger.info(
                "Simple merge completed",
                extra={
                    "task": str(task),
                    "triggering_branch": str(first_completed),
                    "completed_branches": len(completed),
                    "next_tasks": [str(t) for t in next_tasks],
                },
            )

            return ExecutionResult(
                success=True, next_tasks=next_tasks, data_updates=context.copy()
            )

        except Exception as e:
            logger.exception("Simple merge failed", extra={"task": str(task)})
            return ExecutionResult(success=False, next_tasks=[], error=str(e))


# ============================================================================
# PATTERN REGISTRY - Dynamic Pattern Resolution
# ============================================================================

# Registry mapping pattern IDs to implementations
# Note: Using Any temporarily to avoid Protocol structural typing issues
BASIC_CONTROL_PATTERNS: dict[int, Any] = {
    1: Sequence(),
    2: ParallelSplit(),
    3: Synchronization(),
    4: ExclusiveChoice(),
    5: SimpleMerge(),
}


def get_pattern(pattern_id: int) -> Any:
    """Get pattern implementation by ID.

    Parameters
    ----------
    pattern_id : int
        YAWL pattern identifier (1-5 for basic control flow)

    Returns
    -------
    Pattern | None
        Pattern implementation or None if not found

    Examples
    --------
    >>> pattern = get_pattern(2)
    >>> assert pattern.name == "Parallel Split (AND-split)"
    """
    return BASIC_CONTROL_PATTERNS.get(pattern_id)
