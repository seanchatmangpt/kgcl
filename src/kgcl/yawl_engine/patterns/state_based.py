"""State-Based YAWL Workflow Patterns (16-18).

This module implements state-based control flow patterns from the YAWL workflow
patterns catalog. These patterns handle runtime decisions, interleaved execution,
and conditional enablement based on workflow state.

Patterns Implemented
--------------------
16. Deferred Choice - Runtime decision where first event wins
17. Interleaved Parallel Routing - Sequential execution in any order
18. Milestone - Conditional enablement based on state

References
----------
- YAWL Patterns Catalog: http://www.workflowpatterns.com/patterns/control/
- Java YAWL Engine: https://github.com/yawlfoundation/yawl

Examples
--------
>>> from rdflib import Graph, URIRef, Namespace
>>> from kgcl.yawl_engine.patterns.state_based import DeferredChoice
>>>
>>> # Deferred Choice: First event wins
>>> graph = Graph()
>>> EX = Namespace("http://example.org/")
>>> choice = DeferredChoice(task_uri=EX.TaskA)
>>> branches = choice.enable_branches(graph, EX.TaskA)
>>> # First event to arrive selects the branch
>>> result = choice.on_event(graph, branches[0], {"data": "value"})
>>> assert result.success
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, FrozenSet

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF

from kgcl.yawl_engine.core.execution import ExecutionResult

logger = logging.getLogger(__name__)

# YAWL workflow ontology namespace
YAWL = Namespace("http://yawlfoundation.org/yawlschema#")
STATE = Namespace("http://yawlfoundation.org/state#")


@dataclass(frozen=True)
class DeferredChoice:
    """Pattern 16: Deferred Choice.

    Runtime decision point where multiple branches are enabled simultaneously,
    and the first event to arrive determines which branch executes. All other
    branches are disabled once the choice is made.

    This differs from XOR-Split (Pattern 4) where the decision is made at
    design time or based on data conditions. Deferred Choice waits for
    external events to make the decision at runtime.

    Parameters
    ----------
    pattern_id : int
        YAWL pattern identifier (always 16)
    name : str
        Pattern name for logging and debugging
    task_uri : URIRef
        URI of the task where choice is deferred
    enabled_branches : FrozenSet[URIRef]
        Set of currently enabled branch URIs
    chosen_branch : URIRef | None
        The branch selected by first event (None until choice made)

    Examples
    --------
    >>> from rdflib import Graph, Namespace
    >>> EX = Namespace("http://example.org/")
    >>> graph = Graph()
    >>>
    >>> # Define task with multiple outgoing branches
    >>> graph.add((EX.TaskA, YAWL.outgoing, EX.BranchX))
    >>> graph.add((EX.TaskA, YAWL.outgoing, EX.BranchY))
    >>>
    >>> # Enable deferred choice
    >>> choice = DeferredChoice(task_uri=EX.TaskA)
    >>> branches = choice.enable_branches(graph, EX.TaskA)
    >>> assert len(branches) == 2
    >>>
    >>> # First event wins
    >>> result = choice.on_event(graph, EX.BranchX, {"customer_call": True})
    >>> assert result.success
    >>> assert choice.chosen_branch == EX.BranchX
    """

    pattern_id: int = 16
    name: str = "Deferred Choice"
    task_uri: URIRef = field(default_factory=lambda: URIRef(""))
    enabled_branches: frozenset[URIRef] = frozenset()
    chosen_branch: URIRef | None = None

    def enable_branches(self, graph: Graph, task: URIRef) -> list[URIRef]:
        """Enable all outgoing branches for deferred choice.

        All branches become enabled simultaneously. The choice is deferred
        until the first event arrives.

        Parameters
        ----------
        graph : Graph
            RDF graph containing workflow definition
        task : URIRef
            Task URI where choice originates

        Returns
        -------
        list[URIRef]
            List of enabled branch URIs

        Raises
        ------
        ValueError
            If task has no outgoing branches

        Examples
        --------
        >>> graph = Graph()
        >>> EX = Namespace("http://example.org/")
        >>> graph.add((EX.Task1, YAWL.outgoing, EX.Branch1))
        >>> graph.add((EX.Task1, YAWL.outgoing, EX.Branch2))
        >>>
        >>> choice = DeferredChoice(task_uri=EX.Task1)
        >>> branches = choice.enable_branches(graph, EX.Task1)
        >>> assert len(branches) == 2
        >>> assert all(isinstance(b, URIRef) for b in branches)
        """
        branches = list(graph.objects(task, YAWL.outgoing))

        if not branches:
            msg = f"Task {task} has no outgoing branches for deferred choice"
            raise ValueError(msg)

        # Mark all branches as enabled in the graph
        for branch in branches:
            graph.add((branch, STATE.enabled, Literal(True)))
            graph.add((branch, STATE.choiceType, Literal("deferred")))

        logger.info(
            "Enabled %d branches for deferred choice at task %s", len(branches), task
        )

        return branches

    def on_event(
        self, graph: Graph, branch: URIRef, event: dict[str, Any]
    ) -> ExecutionResult:
        """Handle event arrival - first event wins.

        When an event arrives for a branch, that branch is selected and all
        other branches are disabled. This implements the "first event wins"
        semantics of deferred choice.

        Parameters
        ----------
        graph : Graph
            RDF graph containing workflow state
        branch : URIRef
            Branch URI receiving the event
        event : dict[str, Any]
            Event data triggering the choice

        Returns
        -------
        ExecutionResult
            Result indicating success/failure and chosen branch

        Raises
        ------
        ValueError
            If branch is not currently enabled
        RuntimeError
            If choice has already been made

        Examples
        --------
        >>> graph = Graph()
        >>> EX = Namespace("http://example.org/")
        >>> graph.add((EX.Branch1, STATE.enabled, Literal(True)))
        >>> graph.add((EX.Branch2, STATE.enabled, Literal(True)))
        >>>
        >>> choice = DeferredChoice(task_uri=EX.Task1)
        >>> result = choice.on_event(graph, EX.Branch1, {"source": "customer"})
        >>> assert result.success
        >>> assert result.data.get("chosen_branch") == EX.Branch1
        """
        # Check if branch is enabled
        is_enabled = graph.value(branch, STATE.enabled)
        if not is_enabled or is_enabled != Literal(True):
            msg = f"Branch {branch} is not enabled for deferred choice"
            raise ValueError(msg)

        # Check if choice already made
        if self.chosen_branch is not None:
            msg = f"Deferred choice already made: {self.chosen_branch}"
            raise RuntimeError(msg)

        # Disable all other branches
        task = self.task_uri
        all_branches = list(graph.objects(task, YAWL.outgoing))

        for other_branch in all_branches:
            if other_branch != branch:
                graph.set((other_branch, STATE.enabled, Literal(False)))
                graph.add((other_branch, STATE.disabled, Literal(True)))
                graph.add(
                    (
                        other_branch,
                        STATE.disabledReason,
                        Literal("deferred_choice_lost"),
                    )
                )

        # Mark chosen branch
        graph.add((branch, STATE.chosen, Literal(True)))
        graph.add((branch, STATE.eventData, Literal(str(event))))

        logger.info(
            "Deferred choice made: branch %s selected (event: %s)", branch, event
        )

        # Return execution result with chosen branch
        return ExecutionResult(
            success=True,
            data={
                "chosen_branch": branch,
                "event": event,
                "disabled_branches": [b for b in all_branches if b != branch],
            },
            message=f"Deferred choice: {branch} selected",
        )


@dataclass(frozen=True)
class InterleavedParallel:
    """Pattern 17: Interleaved Parallel Routing.

    Tasks execute in any order but not concurrently - mutual exclusion ensures
    only one task from the set executes at a time. This is like parallel split
    but with serialization constraints.

    Common in scenarios where tasks can be done in any order but require
    exclusive access to a shared resource (e.g., database, equipment).

    Parameters
    ----------
    pattern_id : int
        YAWL pattern identifier (always 17)
    name : str
        Pattern name for logging
    mutex_set : FrozenSet[str]
        Set of task URIs that cannot run concurrently
    active_task : URIRef | None
        Currently executing task (None if no task running)
    completed_tasks : FrozenSet[URIRef]
        Tasks that have completed execution

    Examples
    --------
    >>> from rdflib import Namespace
    >>> EX = Namespace("http://example.org/")
    >>>
    >>> # Define tasks requiring mutual exclusion
    >>> mutex_tasks = frozenset([str(EX.TaskA), str(EX.TaskB), str(EX.TaskC)])
    >>> interleaved = InterleavedParallel(mutex_set=mutex_tasks)
    >>>
    >>> # Acquire mutex for first task
    >>> graph = Graph()
    >>> acquired = interleaved.acquire_mutex(graph, EX.TaskA)
    >>> assert acquired
    >>>
    >>> # Second task blocked until first releases
    >>> acquired2 = interleaved.acquire_mutex(graph, EX.TaskB)
    >>> assert not acquired2
    """

    pattern_id: int = 17
    name: str = "Interleaved Parallel Routing"
    mutex_set: frozenset[str] = frozenset()
    active_task: URIRef | None = None
    completed_tasks: frozenset[URIRef] = frozenset()

    def acquire_mutex(self, graph: Graph, task: URIRef) -> bool:
        """Acquire mutex lock for task execution.

        Only one task from the mutex set can execute at a time. Returns True
        if lock acquired, False if another task is currently executing.

        Parameters
        ----------
        graph : Graph
            RDF graph containing workflow state
        task : URIRef
            Task requesting mutex lock

        Returns
        -------
        bool
            True if lock acquired, False if blocked

        Raises
        ------
        ValueError
            If task is not in the mutex set

        Examples
        --------
        >>> graph = Graph()
        >>> EX = Namespace("http://example.org/")
        >>> mutex_set = frozenset([str(EX.Task1), str(EX.Task2)])
        >>> interleaved = InterleavedParallel(mutex_set=mutex_set)
        >>>
        >>> # First acquisition succeeds
        >>> assert interleaved.acquire_mutex(graph, EX.Task1)
        >>>
        >>> # Second blocked
        >>> assert not interleaved.acquire_mutex(graph, EX.Task2)
        """
        task_str = str(task)
        if task_str not in self.mutex_set:
            msg = f"Task {task} not in mutex set: {self.mutex_set}"
            raise ValueError(msg)

        # Check if any task currently holds the lock
        for mutex_task_str in self.mutex_set:
            mutex_task = URIRef(mutex_task_str)
            is_active = graph.value(mutex_task, STATE.mutexActive)
            if is_active == Literal(True):
                logger.debug("Mutex blocked: task %s already executing", mutex_task)
                return False

        # Acquire lock
        graph.add((task, STATE.mutexActive, Literal(True)))
        graph.add((task, STATE.mutexSet, Literal(str(self.mutex_set))))

        logger.info("Mutex acquired for task %s", task)
        return True

    def release_mutex(self, graph: Graph, task: URIRef) -> None:
        """Release mutex lock after task completion.

        Allows next task in the mutex set to execute.

        Parameters
        ----------
        graph : Graph
            RDF graph containing workflow state
        task : URIRef
            Task releasing mutex lock

        Raises
        ------
        ValueError
            If task doesn't hold the lock

        Examples
        --------
        >>> graph = Graph()
        >>> EX = Namespace("http://example.org/")
        >>> mutex_set = frozenset([str(EX.Task1)])
        >>> interleaved = InterleavedParallel(mutex_set=mutex_set)
        >>>
        >>> # Acquire then release
        >>> interleaved.acquire_mutex(graph, EX.Task1)
        >>> interleaved.release_mutex(graph, EX.Task1)
        >>>
        >>> # Verify released
        >>> is_active = graph.value(EX.Task1, STATE.mutexActive)
        >>> assert is_active == Literal(False)
        """
        is_active = graph.value(task, STATE.mutexActive)
        if is_active != Literal(True):
            msg = f"Task {task} does not hold mutex lock"
            raise ValueError(msg)

        # Release lock
        graph.set((task, STATE.mutexActive, Literal(False)))
        graph.add((task, STATE.completed, Literal(True)))

        logger.info("Mutex released for task %s", task)


@dataclass(frozen=True)
class Milestone:
    """Pattern 18: Milestone.

    Task is enabled only while a milestone condition holds. If the condition
    becomes false before the task executes, the task is disabled. This is
    different from a guard condition (evaluated once) - milestone conditions
    are continuously evaluated.

    Common in time-sensitive workflows or workflows with changing business rules.

    Parameters
    ----------
    pattern_id : int
        YAWL pattern identifier (always 18)
    name : str
        Pattern name for logging
    milestone_condition : str
        SPARQL ASK query defining the milestone condition
    task_uri : URIRef
        Task controlled by this milestone
    was_enabled : bool
        Whether task was previously enabled by milestone

    Examples
    --------
    >>> from rdflib import Namespace
    >>> EX = Namespace("http://example.org/")
    >>>
    >>> # Define milestone: task enabled only during business hours
    >>> condition = '''
    ... ASK {
    ...   ?time a :BusinessHours ;
    ...        :hour ?h .
    ...   FILTER(?h >= 9 && ?h < 17)
    ... }
    ... '''
    >>> milestone = Milestone(task_uri=EX.ProcessOrder, milestone_condition=condition)
    >>>
    >>> # Check if task should be enabled
    >>> graph = Graph()
    >>> enabled = milestone.check_milestone(graph)
    """

    pattern_id: int = 18
    name: str = "Milestone"
    milestone_condition: str = ""
    task_uri: URIRef = field(default_factory=lambda: URIRef(""))
    was_enabled: bool = False

    def check_milestone(self, graph: Graph) -> bool:
        """Evaluate milestone condition.

        Executes SPARQL ASK query to determine if milestone condition holds.
        Task is enabled only while condition is True.

        Parameters
        ----------
        graph : Graph
            RDF graph containing workflow state and data

        Returns
        -------
        bool
            True if milestone condition holds, False otherwise

        Raises
        ------
        ValueError
            If milestone condition is empty or invalid SPARQL

        Examples
        --------
        >>> from rdflib import Graph, Literal, Namespace
        >>> EX = Namespace("http://example.org/")
        >>> graph = Graph()
        >>>
        >>> # Add milestone state
        >>> graph.add((EX.State1, RDF.type, EX.WorkflowState))
        >>> graph.add((EX.State1, EX.reached, Literal(True)))
        >>>
        >>> # Define milestone condition
        >>> condition = "ASK { ?s a <http://example.org/WorkflowState> }"
        >>> milestone = Milestone(task_uri=EX.Task1, milestone_condition=condition)
        >>>
        >>> # Evaluate
        >>> assert milestone.check_milestone(graph)
        """
        if not self.milestone_condition.strip():
            msg = "Milestone condition cannot be empty"
            raise ValueError(msg)

        try:
            # Execute SPARQL ASK query
            result = graph.query(self.milestone_condition)
            condition_holds = bool(result.askAnswer)

            # Update task state based on milestone
            if condition_holds:
                graph.set((self.task_uri, STATE.milestoneEnabled, Literal(True)))
                if not self.was_enabled:
                    logger.info("Milestone enabled task %s", self.task_uri)
            else:
                graph.set((self.task_uri, STATE.milestoneEnabled, Literal(False)))
                if self.was_enabled:
                    logger.info("Milestone disabled task %s", self.task_uri)

            return condition_holds

        except Exception as e:
            msg = f"Failed to evaluate milestone condition: {e}"
            logger.error(msg)
            raise ValueError(msg) from e


# Public API
__all__ = ["STATE", "YAWL", "DeferredChoice", "InterleavedParallel", "Milestone"]
