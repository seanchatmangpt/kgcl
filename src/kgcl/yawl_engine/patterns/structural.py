"""YAWL Structural Patterns - Arbitrary Cycles and Implicit Termination.

This module implements YAWL workflow patterns 10-11 for advanced control flow:
- Pattern 10: Arbitrary Cycles - Loops with backward edges and iteration
  tracking
- Pattern 11: Implicit Termination - Workflow completion when no tasks are
  enabled/running

These patterns align with the Java YAWL Foundation reference implementation.

Examples
--------
>>> from rdflib import Graph, URIRef
>>> graph = Graph()
>>> # ... populate graph with workflow topology ...
>>> cycles = ArbitraryCycles(max_iterations=100)
>>> result = cycles.evaluate(graph, URIRef("urn:task:LoopTask"), {})
>>> assert result.success
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from rdflib import Graph, Literal, Namespace, URIRef

# YAWL Foundation namespace
YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")
KGC = Namespace("https://kgc.org/ns/")

logger = logging.getLogger(__name__)


# ============================================================================
# Pattern Result Types
# ============================================================================


class PatternStatus(str, Enum):
    """Pattern evaluation status."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PENDING = "PENDING"
    CYCLE_DETECTED = "CYCLE_DETECTED"
    MAX_ITERATIONS = "MAX_ITERATIONS"


@dataclass(frozen=True)
class PatternResult:
    """Immutable pattern evaluation result.

    Parameters
    ----------
    success : bool
        Whether pattern evaluation succeeded
    status : PatternStatus
        Detailed evaluation status
    message : str
        Human-readable result message
    metadata : dict[str, Any]
        Additional pattern-specific metadata

    Examples
    --------
    >>> result = PatternResult(
    ...     success=True,
    ...     status=PatternStatus.SUCCESS,
    ...     message="Cycle completed after 3 iterations",
    ...     metadata={"iterations": 3, "cycle_path": ["A", "B", "C"]},
    ... )
    """

    success: bool
    status: PatternStatus
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionResult:
    """Immutable pattern execution result.

    Parameters
    ----------
    committed : bool
        Whether execution was committed to graph
    task : URIRef
        Task that was executed
    updates : list[tuple[str, str, str]]
        RDF triples added during execution
    data_updates : dict[str, Any]
        Workflow data variable updates

    Examples
    --------
    >>> result = ExecutionResult(
    ...     committed=True,
    ...     task=URIRef("urn:task:LoopTask"),
    ...     updates=[("urn:task:LoopTask", "yawl:status", "completed")],
    ...     data_updates={"iteration_count": 5},
    ... )
    """

    committed: bool
    task: URIRef
    updates: list[tuple[str, str, str]] = field(default_factory=list)
    data_updates: dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Pattern 10: Arbitrary Cycles
# ============================================================================


@dataclass(frozen=True)
class ArbitraryCycles:
    """YAWL Pattern 10: Arbitrary Cycles.

    Supports loops with backward edges (A→B→C→B). Tracks iteration counts
    to prevent infinite loops and provides cycle detection.

    Java YAWL Requirements:
    - Detect backward flow edges in workflow graph
    - Track iteration counts per task instance
    - Enforce maximum iteration limits
    - Handle cycle entry/exit conditions

    Parameters
    ----------
    pattern_id : int
        YAWL pattern identifier (10)
    name : str
        Pattern name
    max_iterations : int
        Maximum allowed loop iterations (default: 1000)

    Examples
    --------
    >>> from rdflib import Graph, URIRef
    >>> graph = Graph()
    >>> # Add cycle: TaskA → TaskB → TaskC → TaskA (backward edge)
    >>> graph.add((URIRef("urn:task:TaskA"), YAWL.flowsTo, URIRef("urn:task:TaskB")))
    >>> graph.add((URIRef("urn:task:TaskB"), YAWL.flowsTo, URIRef("urn:task:TaskC")))
    >>> graph.add((URIRef("urn:task:TaskC"), YAWL.flowsTo, URIRef("urn:task:TaskA")))
    >>> cycles = ArbitraryCycles(max_iterations=10)
    >>> path = cycles.detect_cycle(graph, URIRef("urn:task:TaskA"))
    >>> assert len(path) > 0  # Cycle detected
    """

    pattern_id: int = 10
    name: str = "Arbitrary Cycles"
    max_iterations: int = 1000

    def detect_cycle(self, graph: Graph, start: URIRef) -> list[URIRef]:
        """Detect cycle starting from a given task using DFS.

        Parameters
        ----------
        graph : Graph
            RDF workflow graph
        start : URIRef
            Starting task for cycle detection

        Returns
        -------
        list[URIRef]
            Cycle path if detected, empty list otherwise

        Examples
        --------
        >>> graph = Graph()
        >>> # Create cycle: A → B → C → A
        >>> graph.add((URIRef("urn:task:A"), YAWL.flowsTo, URIRef("urn:task:B")))
        >>> graph.add((URIRef("urn:task:B"), YAWL.flowsTo, URIRef("urn:task:C")))
        >>> graph.add((URIRef("urn:task:C"), YAWL.flowsTo, URIRef("urn:task:A")))
        >>> cycles = ArbitraryCycles()
        >>> path = cycles.detect_cycle(graph, URIRef("urn:task:A"))
        >>> assert URIRef("urn:task:A") in path
        """
        visited: set[URIRef] = set()
        rec_stack: set[URIRef] = set()
        path: list[URIRef] = []

        def dfs(node: URIRef) -> bool:
            """Depth-first search for cycle detection."""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            # Query outgoing edges
            query = f"""
            PREFIX yawl: <{YAWL}>
            SELECT ?next WHERE {{
                <{node}> yawl:flowsTo ?next .
            }}
            """
            for row in graph.query(query):
                if not hasattr(row, "next"):
                    continue
                # Extract next node from ResultRow
                next_node = getattr(row, "next", None)
                if next_node is None or not isinstance(next_node, URIRef):
                    continue

                if next_node not in visited:
                    if dfs(next_node):
                        return True
                elif next_node in rec_stack:
                    # Cycle detected - add cycle-closing node
                    path.append(next_node)
                    return True

            rec_stack.remove(node)
            path.pop()
            return False

        if dfs(start):
            return path
        return []

    def evaluate(self, graph: Graph, task: URIRef, context: dict[str, Any]) -> PatternResult:
        """Evaluate cycle pattern for a given task.

        Parameters
        ----------
        graph : Graph
            RDF workflow graph
        task : URIRef
            Task to evaluate
        context : dict[str, Any]
            Execution context with iteration tracking

        Returns
        -------
        PatternResult
            Evaluation result with cycle detection and iteration count

        Examples
        --------
        >>> graph = Graph()
        >>> cycles = ArbitraryCycles(max_iterations=5)
        >>> context = {"iteration_counts": {"urn:task:LoopTask": 3}}
        >>> result = cycles.evaluate(graph, URIRef("urn:task:LoopTask"), context)
        >>> assert result.success
        """
        iteration_counts = context.get("iteration_counts", {})
        task_str = str(task)
        current_iteration = iteration_counts.get(task_str, 0)

        # Check iteration limit
        if current_iteration >= self.max_iterations:
            logger.warning(
                "Max iterations exceeded",
                extra={"task": task_str, "iterations": current_iteration, "max": self.max_iterations},
            )
            return PatternResult(
                success=False,
                status=PatternStatus.MAX_ITERATIONS,
                message=(f"Task {task_str} exceeded max iterations ({self.max_iterations})"),
                metadata={"iterations": current_iteration},
            )

        # Detect cycle
        cycle_path = self.detect_cycle(graph, task)
        if cycle_path:
            logger.info(
                "Cycle detected",
                extra={"task": task_str, "cycle_length": len(cycle_path), "iteration": current_iteration},
            )
            return PatternResult(
                success=True,
                status=PatternStatus.CYCLE_DETECTED,
                message=f"Cycle detected at iteration {current_iteration}",
                metadata={
                    "cycle_path": [str(n) for n in cycle_path],
                    "cycle_length": len(cycle_path),
                    "iterations": current_iteration,
                },
            )

        return PatternResult(
            success=True,
            status=PatternStatus.SUCCESS,
            message=f"No cycle detected (iteration {current_iteration})",
            metadata={"iterations": current_iteration},
        )

    def execute(self, graph: Graph, task: URIRef, context: dict[str, Any]) -> ExecutionResult:
        """Execute cycle pattern - increment iteration counter and mark task.

        Parameters
        ----------
        graph : Graph
            RDF workflow graph
        task : URIRef
            Task to execute
        context : dict[str, Any]
            Execution context with iteration tracking

        Returns
        -------
        ExecutionResult
            Execution result with updated iteration count

        Examples
        --------
        >>> graph = Graph()
        >>> cycles = ArbitraryCycles()
        >>> context = {"iteration_counts": {}}
        >>> result = cycles.execute(graph, URIRef("urn:task:LoopTask"), context)
        >>> assert result.committed
        >>> assert result.data_updates["iteration_counts"]["urn:task:LoopTask"] == 1
        """
        iteration_counts = context.get("iteration_counts", {})
        task_str = str(task)
        current_iteration = iteration_counts.get(task_str, 0)
        new_iteration = current_iteration + 1

        # Update iteration count
        updated_counts = {**iteration_counts, task_str: new_iteration}

        # Mark task as completed with iteration metadata
        updates = [
            (task_str, str(YAWL.status), "completed"),
            (task_str, str(YAWL.iterationCount), str(new_iteration)),
            (task_str, str(KGC.patternId), "10"),
        ]

        logger.info(
            "Cycle iteration executed", extra={"task": task_str, "iteration": new_iteration, "pattern": self.name}
        )

        return ExecutionResult(
            committed=True, task=task, updates=updates, data_updates={"iteration_counts": updated_counts}
        )


# ============================================================================
# Pattern 11: Implicit Termination
# ============================================================================


@dataclass(frozen=True)
class ImplicitTermination:
    """YAWL Pattern 11: Implicit Termination.

    Workflow terminates when no tasks are in 'enabled' or 'running' state.
    No explicit end node required - termination is detected automatically.

    Java YAWL Requirements:
    - Check all task states in workflow
    - Terminate if no tasks are enabled/running
    - Handle workflows without explicit end nodes
    - Support graceful shutdown

    Parameters
    ----------
    pattern_id : int
        YAWL pattern identifier (11)
    name : str
        Pattern name

    Examples
    --------
    >>> from rdflib import Graph, URIRef
    >>> graph = Graph()
    >>> # All tasks completed - implicit termination
    >>> graph.add((URIRef("urn:task:TaskA"), YAWL.status, Literal("completed")))
    >>> graph.add((URIRef("urn:task:TaskB"), YAWL.status, Literal("completed")))
    >>> termination = ImplicitTermination()
    >>> should_terminate = termination.check_termination(graph, URIRef("urn:workflow:W1"))
    >>> assert should_terminate is True
    """

    pattern_id: int = 11
    name: str = "Implicit Termination"

    def check_termination(self, graph: Graph, workflow: URIRef) -> bool:
        """Check if workflow should terminate (no tasks enabled/running).

        Parameters
        ----------
        graph : Graph
            RDF workflow graph
        workflow : URIRef
            Workflow instance to check

        Returns
        -------
        bool
            True if workflow should terminate, False otherwise

        Examples
        --------
        >>> graph = Graph()
        >>> # All tasks completed
        >>> graph.add((URIRef("urn:task:A"), YAWL.status, Literal("completed")))
        >>> graph.add((URIRef("urn:task:B"), YAWL.status, Literal("completed")))
        >>> termination = ImplicitTermination()
        >>> assert termination.check_termination(graph, URIRef("urn:workflow:W1"))
        """
        # Query for tasks that are enabled or running
        query = f"""
        PREFIX yawl: <{YAWL}>
        ASK {{
            ?task yawl:status ?status .
            FILTER(?status IN ("enabled", "running"))
        }}
        """
        has_active_tasks = graph.query(query).askAnswer

        if has_active_tasks:
            logger.debug("Workflow has active tasks", extra={"workflow": str(workflow), "pattern": self.name})
            return False

        # No active tasks - implicit termination
        logger.info("Implicit termination triggered", extra={"workflow": str(workflow), "pattern": self.name})
        return True

    def evaluate(self, graph: Graph, workflow: URIRef, context: dict[str, Any]) -> PatternResult:
        """Evaluate implicit termination pattern.

        Parameters
        ----------
        graph : Graph
            RDF workflow graph
        workflow : URIRef
            Workflow instance to evaluate
        context : dict[str, Any]
            Execution context

        Returns
        -------
        PatternResult
            Evaluation result indicating if termination should occur

        Examples
        --------
        >>> graph = Graph()
        >>> termination = ImplicitTermination()
        >>> result = termination.evaluate(graph, URIRef("urn:workflow:W1"), {})
        >>> assert result.status in (PatternStatus.SUCCESS, PatternStatus.PENDING)
        """
        should_terminate = self.check_termination(graph, workflow)

        if should_terminate:
            # Count completed tasks
            query = f"""
            PREFIX yawl: <{YAWL}>
            SELECT (COUNT(?task) as ?cnt) WHERE {{
                ?task yawl:status "completed" .
            }}
            """
            completed_count = 0
            for row in graph.query(query):
                # Access via attribute (renamed to avoid conflict with count() method)
                if hasattr(row, "cnt"):
                    cnt_val = getattr(row, "cnt", None)
                    if cnt_val is not None:
                        # SPARQL COUNT returns Literal with integer value
                        if isinstance(cnt_val, Literal):
                            completed_count = int(cnt_val.value)
                        else:
                            completed_count = int(cnt_val)

            return PatternResult(
                success=True,
                status=PatternStatus.SUCCESS,
                message=f"Workflow {workflow} terminated implicitly",
                metadata={"completed_tasks": completed_count, "termination_type": "implicit"},
            )

        return PatternResult(
            success=False,
            status=PatternStatus.PENDING,
            message=f"Workflow {workflow} still has active tasks",
            metadata={"termination_type": "pending"},
        )

    def execute(self, graph: Graph, workflow: URIRef, context: dict[str, Any]) -> ExecutionResult:
        """Execute implicit termination - mark workflow as completed.

        Parameters
        ----------
        graph : Graph
            RDF workflow graph
        workflow : URIRef
            Workflow instance to terminate
        context : dict[str, Any]
            Execution context

        Returns
        -------
        ExecutionResult
            Execution result with workflow completion marker

        Examples
        --------
        >>> graph = Graph()
        >>> termination = ImplicitTermination()
        >>> result = termination.execute(graph, URIRef("urn:workflow:W1"), {})
        >>> assert result.committed
        """
        workflow_str = str(workflow)

        # Mark workflow as completed
        updates = [
            (workflow_str, str(YAWL.status), "completed"),
            (workflow_str, str(YAWL.terminationType), "implicit"),
            (workflow_str, str(KGC.patternId), "11"),
        ]

        logger.info("Workflow terminated implicitly", extra={"workflow": workflow_str, "pattern": self.name})

        return ExecutionResult(
            committed=True, task=workflow, updates=updates, data_updates={"workflow_terminated": True}
        )
