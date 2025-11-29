"""Token execution engine (mirrors Java YNetRunner).

The NetRunner maintains the marking and fires enabled tasks,
implementing the operational semantics of YAWL.

Key features ported from Java YNetRunner:
- Deferred choice (WCP-16): Racing tasks where first to fire wins
- Busy task tracking: Tasks in execution are tracked separately
- Execution status: Support for suspend/resume during execution
- Task withdrawal: When tokens consumed elsewhere, withdraw enabled tasks
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

from kgcl.yawl.elements.y_identifier import YIdentifier
from kgcl.yawl.elements.y_net import YNet
from kgcl.yawl.elements.y_task import JoinType, SplitType, YTask
from kgcl.yawl.engine.y_expression import YExpressionContext, YExpressionEvaluator
from kgcl.yawl.engine.y_or_join import YOrJoinAnalyzer
from kgcl.yawl.state.y_marking import YMarking

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_atomic_task import YAtomicTask, YCompositeTask
    from kgcl.yawl.elements.y_condition import YCondition
    from kgcl.yawl.engine.y_work_item import YWorkItem


class ExecutionStatus(Enum):
    """Execution status for net runner (mirrors Java YNetRunner execution states).

    Attributes
    ----------
    NORMAL : auto
        Normal execution, tasks can fire
    SUSPENDING : auto
        Transitioning to suspended (waiting for busy tasks)
    SUSPENDED : auto
        Fully suspended, no new tasks will fire
    RESUMING : auto
        Transitioning back to normal
    """

    NORMAL = auto()
    SUSPENDING = auto()
    SUSPENDED = auto()
    RESUMING = auto()


# ruff: noqa: N803  # Allow Java-style parameter names to match Java YAWL API
@dataclass
class DeferredChoiceGroup:
    """Group of tasks in a deferred choice relationship (WCP-16).

    In deferred choice, multiple tasks share the same preset conditions.
    When one fires, all others must be withdrawn (disabled).

    Parameters
    ----------
    group_id : str
        Unique identifier for this deferred choice group
    task_ids : set[str]
        IDs of tasks in the group
    """

    group_id: str
    task_ids: set[str] = field(default_factory=set)

    def contains(self, task_id: str) -> bool:
        """Check if task is in this group."""
        return task_id in self.task_ids


@dataclass
class FireResult:
    """Result of firing a task.

    Parameters
    ----------
    task_id : str
        ID of the fired task
    consumed_tokens : list[str]
        Token IDs consumed from input conditions
    produced_tokens : list[str]
        Token IDs produced to output conditions
    cancelled_tokens : list[str]
        Token IDs cancelled via cancellation set
    """

    task_id: str
    consumed_tokens: list[str]
    produced_tokens: list[str]
    cancelled_tokens: list[str]


@dataclass
class YNetRunner:
    """Executes token flow in a YAWL net (mirrors Java YNetRunner).

    The NetRunner is the core execution engine. It maintains the marking
    (token distribution) and fires enabled tasks according to YAWL semantics.

    Key features (ported from Java YNetRunner):
    - Enabled task tracking: Tasks whose join conditions are satisfied
    - Busy task tracking: Tasks currently in execution
    - Deferred choice (WCP-16): Racing enabled tasks where first wins
    - Execution status: Suspend/resume during case execution
    - Task withdrawal: Remove enabled tasks when tokens consumed elsewhere

    Parameters
    ----------
    net : YNet
        The workflow net to execute
    case_id : str
        Unique identifier for this case (auto-generated if not provided)
    marking : YMarking
        Current token marking
    tokens : dict[str, YIdentifier]
        All tokens by ID (for lineage tracking)
    completed : bool
        True when token reaches output condition
    execution_status : ExecutionStatus
        Current execution status (Normal, Suspending, Suspended, Resuming)
    enabled_tasks : set[str]
        IDs of tasks whose join conditions are satisfied
    busy_tasks : set[str]
        IDs of tasks currently in execution (fired but not completed)
    deferred_choice_groups : dict[str, DeferredChoiceGroup]
        Deferred choice groups by group ID
    withdrawn_tasks : set[str]
        IDs of tasks withdrawn due to deferred choice

    Examples
    --------
    >>> from kgcl.yawl import YNet, YCondition, YTask, YFlow, ConditionType
    >>> net = YNet(id="simple")
    >>> start = YCondition(id="start", condition_type=ConditionType.INPUT)
    >>> end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
    >>> task = YTask(id="A")
    >>> net.add_condition(start)
    >>> net.add_condition(end)
    >>> net.add_task(task)
    >>> net.add_flow(YFlow(id="f1", source_id="start", target_id="A"))
    >>> net.add_flow(YFlow(id="f2", source_id="A", target_id="end"))
    >>> runner = YNetRunner(net)
    >>> runner.start()
    YIdentifier(...)
    >>> runner.fire_task("A")
    FireResult(...)
    >>> runner.completed
    True
    """

    net: YNet
    case_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    marking: YMarking = field(default_factory=YMarking)
    tokens: dict[str, YIdentifier] = field(default_factory=dict)
    completed: bool = False

    # Execution status (Gap 3: mirrors Java ExecutionStatus)
    execution_status: ExecutionStatus = ExecutionStatus.NORMAL

    # Task tracking (Gap 2: mirrors Java _enabledTasks and _busyTasks)
    enabled_tasks: set[str] = field(default_factory=set)
    busy_tasks: set[str] = field(default_factory=set)

    # Deferred choice groups (Gap 1: mirrors Java TaskGroup for WCP-16)
    deferred_choice_groups: dict[str, DeferredChoiceGroup] = field(default_factory=dict)
    withdrawn_tasks: set[str] = field(default_factory=set)

    # Internal state
    _token_counter: int = field(default=0, repr=False)
    _expression_evaluator: YExpressionEvaluator = field(default_factory=YExpressionEvaluator, repr=False)
    _or_join_analyzer: YOrJoinAnalyzer | None = field(default=None, repr=False)

    def start(self) -> YIdentifier:
        """Start case by placing token in input condition.

        Returns
        -------
        YIdentifier
            The initial token placed at input condition

        Raises
        ------
        ValueError
            If net has no input condition

        Examples
        --------
        >>> runner = YNetRunner(net)
        >>> token = runner.start()
        >>> token.location == net.input_condition.id
        True
        """
        if self.net.input_condition is None:
            raise ValueError("Net has no input condition")

        token = YIdentifier(id=f"{self.case_id}-{self._token_counter}")
        token.location = self.net.input_condition.id
        self.tokens[token.id] = token
        self.marking.add_token(self.net.input_condition.id, token.id)
        self._token_counter += 1
        return token

    def get_enabled_tasks(self) -> list[str]:
        """Get IDs of all enabled tasks.

        A task is enabled when its join condition is satisfied
        based on the current marking.

        Returns
        -------
        list[str]
            IDs of tasks that can fire

        Examples
        --------
        >>> runner = YNetRunner(net)
        >>> runner.start()
        >>> "A" in runner.get_enabled_tasks()
        True
        """
        enabled = []
        for task_id, task in self.net.tasks.items():
            if self._is_task_enabled(task):
                enabled.append(task_id)
        return enabled

    def _is_task_enabled(self, task: YTask) -> bool:
        """Check if task is enabled based on join type.

        Parameters
        ----------
        task : YTask
            Task to check

        Returns
        -------
        bool
            True if task can fire
        """
        preset_conditions = self._get_preset_conditions(task)

        if not preset_conditions:
            return False

        if task.join_type == JoinType.AND:
            # All preset conditions must have tokens
            return all(self.marking.has_tokens(cond_id) for cond_id in preset_conditions)
        elif task.join_type == JoinType.XOR:
            # Any one preset condition has tokens
            return any(self.marking.has_tokens(cond_id) for cond_id in preset_conditions)
        else:  # OR join - full backwards reachability analysis (WCP-7)
            return self._is_or_join_enabled(task)

    def _is_or_join_enabled(self, task: YTask) -> bool:
        """Check if OR-join task is enabled using backwards reachability.

        The OR-join must wait until no unmarked preset condition can
        still receive a token from an active path in the net.

        Parameters
        ----------
        task : YTask
            OR-join task to check

        Returns
        -------
        bool
            True if OR-join can safely fire
        """
        # Create or refresh analyzer with current marking
        if self._or_join_analyzer is None:
            self._or_join_analyzer = YOrJoinAnalyzer(net=self.net, marking=self.marking)
        else:
            # Refresh analyzer reference to current marking
            self._or_join_analyzer = YOrJoinAnalyzer(net=self.net, marking=self.marking)

        result = self._or_join_analyzer.is_or_join_enabled(task)
        return result.is_enabled

    def _get_preset_conditions(self, task: YTask) -> list[str]:
        """Get condition IDs in task's preset.

        Parameters
        ----------
        task : YTask
            Task to get preset for

        Returns
        -------
        list[str]
            Condition IDs feeding into this task
        """
        conditions = []
        for flow_id in task.preset_flows:
            flow = self.net.flows.get(flow_id)
            if flow and flow.source_id in self.net.conditions:
                conditions.append(flow.source_id)
        return conditions

    def _get_postset_conditions(self, task: YTask) -> list[str]:
        """Get condition IDs in task's postset.

        Parameters
        ----------
        task : YTask
            Task to get postset for

        Returns
        -------
        list[str]
            Condition IDs fed by this task
        """
        conditions = []
        for flow_id in task.postset_flows:
            flow = self.net.flows.get(flow_id)
            if flow and flow.target_id in self.net.conditions:
                conditions.append(flow.target_id)
        return conditions

    def fire_task(self, task_id: str, data: dict[str, Any] | None = None) -> FireResult:
        """Fire a task: consume input tokens, produce output tokens.

        Parameters
        ----------
        task_id : str
            ID of task to fire
        data : dict[str, Any] | None
            Data for predicate evaluation and token payload

        Returns
        -------
        FireResult
            Result with consumed, produced, and cancelled tokens

        Raises
        ------
        ValueError
            If task doesn't exist or is not enabled

        Examples
        --------
        >>> result = runner.fire_task("A")
        >>> len(result.produced_tokens) > 0
        True
        """
        task = self.net.tasks.get(task_id)
        if task is None:
            raise ValueError(f"Unknown task: {task_id}")

        if not self._is_task_enabled(task):
            raise ValueError(f"Task not enabled: {task_id}")

        # 1. Consume tokens from preset conditions (based on join)
        consumed = self._consume_tokens(task)

        # 2. Execute cancellation set (reset net semantics)
        cancelled = []
        if task.cancellation_set:
            cancelled = self._execute_cancellation(task.cancellation_set)

        # 3. Produce tokens to postset conditions (based on split)
        produced = self._produce_tokens(task, consumed, data)

        # 4. Check for completion
        if self.net.output_condition:
            if self.marking.has_tokens(self.net.output_condition.id):
                self.completed = True

        return FireResult(
            task_id=task_id, consumed_tokens=consumed, produced_tokens=produced, cancelled_tokens=cancelled
        )

    def _consume_tokens(self, task: YTask) -> list[str]:
        """Consume tokens from preset based on join type.

        Parameters
        ----------
        task : YTask
            Task consuming tokens

        Returns
        -------
        list[str]
            Token IDs that were consumed
        """
        consumed = []
        preset_conditions = self._get_preset_conditions(task)

        if task.join_type == JoinType.AND:
            # Consume one token from each preset
            for cond_id in preset_conditions:
                token_id = self.marking.remove_one_token(cond_id)
                if token_id:
                    consumed.append(token_id)
        elif task.join_type == JoinType.XOR:
            # Consume from first preset with tokens
            for cond_id in preset_conditions:
                if self.marking.has_tokens(cond_id):
                    token_id = self.marking.remove_one_token(cond_id)
                    if token_id:
                        consumed.append(token_id)
                    break
        else:  # OR join
            # Consume from all presets with tokens
            for cond_id in preset_conditions:
                if self.marking.has_tokens(cond_id):
                    token_id = self.marking.remove_one_token(cond_id)
                    if token_id:
                        consumed.append(token_id)

        return consumed

    def _produce_tokens(self, task: YTask, consumed: list[str], data: dict[str, Any] | None) -> list[str]:
        """Produce tokens to postset based on split type.

        Parameters
        ----------
        task : YTask
            Task producing tokens
        consumed : list[str]
            Token IDs that were consumed
        data : dict[str, Any] | None
            Data for predicate evaluation

        Returns
        -------
        list[str]
            Token IDs that were produced
        """
        produced = []
        postset_conditions = self._get_postset_conditions(task)

        # Get parent token for lineage
        parent_token = self.tokens.get(consumed[0]) if consumed else None

        if task.split_type == SplitType.AND:
            # Produce to ALL postset conditions
            for cond_id in postset_conditions:
                token_id = self._create_token(parent_token, cond_id, data)
                produced.append(token_id)
        elif task.split_type == SplitType.XOR:
            # Produce to FIRST condition with true predicate (or default)
            target = self._evaluate_xor_split(task, postset_conditions, data)
            if target:
                token_id = self._create_token(parent_token, target, data)
                produced.append(token_id)
        else:  # OR split
            # Produce to ALL conditions with true predicates
            targets = self._evaluate_or_split(task, postset_conditions, data)
            for target in targets:
                token_id = self._create_token(parent_token, target, data)
                produced.append(token_id)

        return produced

    def _create_token(self, parent: YIdentifier | None, location: str, data: dict[str, Any] | None) -> str:
        """Create new token at location.

        Parameters
        ----------
        parent : YIdentifier | None
            Parent token for lineage
        location : str
            Condition ID for new token
        data : dict[str, Any] | None
            Data payload for token

        Returns
        -------
        str
            ID of created token
        """
        token_id = f"{self.case_id}-{self._token_counter}"
        self._token_counter += 1

        token = YIdentifier(id=token_id, parent=parent, location=location, data=data.copy() if data else {})
        if parent:
            parent.children.append(token)

        self.tokens[token_id] = token
        self.marking.add_token(location, token_id)
        return token_id

    def _evaluate_xor_split(self, task: YTask, conditions: list[str], data: dict[str, Any] | None) -> str | None:
        """Evaluate XOR split predicates, return first true target.

        Parameters
        ----------
        task : YTask
            Task with XOR split
        conditions : list[str]
            Possible target condition IDs
        data : dict[str, Any] | None
            Data for predicate evaluation

        Returns
        -------
        str | None
            Target condition ID or None
        """
        # Evaluate flows in order
        flows_with_order = []
        for flow_id in task.postset_flows:
            flow = self.net.flows.get(flow_id)
            if flow and flow.target_id in conditions:
                flows_with_order.append((flow.ordering, flow))

        flows_with_order.sort(key=lambda x: x[0])

        default_target = None
        for _, flow in flows_with_order:
            if flow.is_default:
                default_target = flow.target_id
                continue

            predicate = task.flow_predicates.get(flow.id, "true")
            if self._evaluate_predicate(predicate, data):
                return flow.target_id

        # Fall back to default or first condition
        return default_target or (conditions[0] if conditions else None)

    def _evaluate_or_split(self, task: YTask, conditions: list[str], data: dict[str, Any] | None) -> list[str]:
        """Evaluate OR split predicates, return all true targets.

        Parameters
        ----------
        task : YTask
            Task with OR split
        conditions : list[str]
            Possible target condition IDs
        data : dict[str, Any] | None
            Data for predicate evaluation

        Returns
        -------
        list[str]
            Target condition IDs with true predicates
        """
        targets = []
        for flow_id in task.postset_flows:
            flow = self.net.flows.get(flow_id)
            if flow and flow.target_id in conditions:
                predicate = task.flow_predicates.get(flow_id, "true")
                if self._evaluate_predicate(predicate, data):
                    targets.append(flow.target_id)

        # Must have at least one target
        return targets if targets else [conditions[0]] if conditions else []

    def _evaluate_predicate(self, predicate: str, data: dict[str, Any] | None) -> bool:
        """Evaluate predicate expression.

        Supports multiple expression types via YExpressionEvaluator:
        - Literal: "true" / "false"
        - Simple paths: "order_id", "customer.name"
        - XPath: "/data/order/amount > 100"

        Parameters
        ----------
        predicate : str
            Predicate expression
        data : dict[str, Any] | None
            Data for evaluation

        Returns
        -------
        bool
            Evaluation result
        """
        context = YExpressionContext(
            variables=data if data else {},
            net_variables={},  # Can be extended for net-level variables
        )
        return self._expression_evaluator.evaluate_boolean(predicate, context)

    def _execute_cancellation(self, cancellation_set: set[str]) -> list[str]:
        """Remove tokens from cancellation set (reset net).

        Parameters
        ----------
        cancellation_set : set[str]
            IDs of elements to cancel

        Returns
        -------
        list[str]
            Token IDs that were cancelled
        """
        cancelled = []
        for element_id in cancellation_set:
            if element_id in self.net.conditions:
                # Remove all tokens from this condition
                tokens = self.marking.get_tokens(element_id)
                for token_id in list(tokens):
                    self.marking.remove_token(element_id, token_id)
                    cancelled.append(token_id)
        return cancelled

    def get_token(self, token_id: str) -> YIdentifier | None:
        """Get token by ID.

        Parameters
        ----------
        token_id : str
            Token ID

        Returns
        -------
        YIdentifier | None
            Token or None if not found
        """
        return self.tokens.get(token_id)

    def get_marking_snapshot(self) -> dict[str, set[str]]:
        """Get snapshot of current marking.

        Returns
        -------
        dict[str, set[str]]
            Copy of marking state
        """
        return {cid: self.marking.get_tokens(cid) for cid in self.marking.get_marked_conditions()}

    def is_deadlocked(self) -> bool:
        """Check if execution is deadlocked.

        Returns
        -------
        bool
            True if no tasks are enabled and not completed
        """
        return not self.completed and not self.marking.is_empty() and len(self.get_enabled_tasks()) == 0

    # --- Execution Status Methods (Gap 3: mirrors Java ExecutionStatus) ---

    def is_in_suspense(self) -> bool:
        """Check if runner is in any suspended state.

        Returns
        -------
        bool
            True if suspending or suspended
        """
        return self.execution_status in (ExecutionStatus.SUSPENDING, ExecutionStatus.SUSPENDED)

    def suspend(self) -> bool:
        """Suspend execution (no new tasks will fire).

        If there are busy tasks, enters SUSPENDING state until they complete.
        Otherwise, enters SUSPENDED state immediately.

        Returns
        -------
        bool
            True if suspension initiated
        """
        if self.execution_status != ExecutionStatus.NORMAL:
            return False

        if self.busy_tasks:
            # Wait for busy tasks to complete
            self.execution_status = ExecutionStatus.SUSPENDING
        else:
            self.execution_status = ExecutionStatus.SUSPENDED
        return True

    def resume(self) -> bool:
        """Resume execution after suspension.

        Returns
        -------
        bool
            True if resumed
        """
        if self.execution_status not in (ExecutionStatus.SUSPENDING, ExecutionStatus.SUSPENDED):
            return False

        self.execution_status = ExecutionStatus.RESUMING
        # Update enabled tasks after resume
        self._update_enabled_tasks()
        self.execution_status = ExecutionStatus.NORMAL
        return True

    def _check_suspension_complete(self) -> None:
        """Check if we can transition from SUSPENDING to SUSPENDED."""
        if self.execution_status == ExecutionStatus.SUSPENDING and not self.busy_tasks:
            self.execution_status = ExecutionStatus.SUSPENDED

    # --- Busy Task Tracking (Gap 2: mirrors Java _busyTasks) ---

    def mark_task_busy(self, task_id: str) -> None:
        """Mark task as busy (in execution).

        Called when a work item is created and started.

        Parameters
        ----------
        task_id : str
            Task ID
        """
        self.busy_tasks.add(task_id)
        # Remove from enabled since it's now busy
        self.enabled_tasks.discard(task_id)

    def mark_task_complete(self, task_id: str) -> None:
        """Mark task as no longer busy.

        Called when a work item completes.

        Parameters
        ----------
        task_id : str
            Task ID
        """
        self.busy_tasks.discard(task_id)
        self._check_suspension_complete()

    def has_active_tasks(self) -> bool:
        """Check if there are any active tasks (enabled or busy).

        Returns
        -------
        bool
            True if any tasks are enabled or busy
        """
        return bool(self.enabled_tasks) or bool(self.busy_tasks)

    # --- Deferred Choice (Gap 1: WCP-16, mirrors Java TaskGroup) ---

    def register_deferred_choice_group(self, group_id: str, task_ids: set[str]) -> DeferredChoiceGroup:
        """Register a deferred choice group (WCP-16).

        Tasks in a deferred choice group share the same preset conditions.
        When one fires (the race winner), all others are withdrawn.

        Parameters
        ----------
        group_id : str
            Unique identifier for the group
        task_ids : set[str]
            IDs of tasks in the group

        Returns
        -------
        DeferredChoiceGroup
            The registered group

        Examples
        --------
        >>> runner.register_deferred_choice_group("choice1", {"TaskA", "TaskB", "TaskC"})
        >>> runner.fire_task("TaskA")  # TaskB and TaskC are now withdrawn
        """
        group = DeferredChoiceGroup(group_id=group_id, task_ids=task_ids)
        self.deferred_choice_groups[group_id] = group
        return group

    def get_deferred_choice_group_for_task(self, task_id: str) -> DeferredChoiceGroup | None:
        """Find deferred choice group containing a task.

        Parameters
        ----------
        task_id : str
            Task ID to find

        Returns
        -------
        DeferredChoiceGroup | None
            The group or None if task not in any group
        """
        for group in self.deferred_choice_groups.values():
            if group.contains(task_id):
                return group
        return None

    def _withdraw_deferred_choice_losers(self, winner_task_id: str) -> list[str]:
        """Withdraw losing tasks when a deferred choice is made.

        When one task in a deferred choice group fires (wins the race),
        all other tasks in the group must be withdrawn (disabled).

        Parameters
        ----------
        winner_task_id : str
            ID of the task that fired

        Returns
        -------
        list[str]
            IDs of withdrawn tasks
        """
        group = self.get_deferred_choice_group_for_task(winner_task_id)
        if not group:
            return []

        withdrawn = []
        for task_id in group.task_ids:
            if task_id != winner_task_id and task_id in self.enabled_tasks:
                self._withdraw_task(task_id)
                withdrawn.append(task_id)

        return withdrawn

    def _withdraw_task(self, task_id: str) -> None:
        """Withdraw an enabled task (disable it).

        Called when:
        - Task loses a deferred choice race
        - Task's join condition becomes false after token movement

        Parameters
        ----------
        task_id : str
            Task ID to withdraw
        """
        self.enabled_tasks.discard(task_id)
        self.withdrawn_tasks.add(task_id)

    def is_task_withdrawn(self, task_id: str) -> bool:
        """Check if a task has been withdrawn.

        Parameters
        ----------
        task_id : str
            Task ID

        Returns
        -------
        bool
            True if task was withdrawn
        """
        return task_id in self.withdrawn_tasks

    # --- Task Enablement Update (Gap 4: mirrors Java continueIfPossible) ---

    def continue_if_possible(self) -> bool:
        """Continue execution by updating enabled tasks and firing if possible.

        This mirrors Java's continueIfPossible method. It:
        1. Checks if we're suspended (returns early if so)
        2. Checks if we're completed (returns early if so)
        3. Updates the set of enabled tasks
        4. Withdraws tasks that are no longer enabled
        5. Returns whether there are still active tasks

        Returns
        -------
        bool
            True if there are active tasks (enabled or busy)
        """
        # If suspended, don't continue
        if self.is_in_suspense():
            return True

        # If completed, we're done
        if self.completed:
            return False

        # Update enabled tasks
        self._update_enabled_tasks()

        return self.has_active_tasks()

    def _update_enabled_tasks(self) -> None:
        """Recalculate which tasks are enabled.

        This mirrors Java's task enablement check in continueIfPossible.
        Tasks that were enabled but are no longer get withdrawn.
        """
        newly_enabled = set()

        for task_id, task in self.net.tasks.items():
            # Skip busy tasks (they're executing)
            if task_id in self.busy_tasks:
                continue

            if self._is_task_enabled(task):
                if task_id not in self.enabled_tasks:
                    newly_enabled.add(task_id)
            # Task was enabled but no longer - withdraw it
            elif task_id in self.enabled_tasks:
                self._withdraw_task(task_id)

        # Add newly enabled tasks
        self.enabled_tasks.update(newly_enabled)

    # --- Empty Task Handling (Gap 5: mirrors Java empty task passthrough) ---

    def is_empty_task(self, task: YTask) -> bool:
        """Check if task is an empty (passthrough) task.

        An empty task has no decomposition - tokens pass through immediately.

        Parameters
        ----------
        task : YTask
            Task to check

        Returns
        -------
        bool
            True if task is empty
        """
        return task.decomposition_id is None

    def fire_empty_task(self, task_id: str, data: dict[str, Any] | None = None) -> FireResult:
        """Fire an empty task immediately (passthrough).

        Empty tasks don't create work items - tokens flow through.
        This is useful for routing-only tasks in the workflow.

        Parameters
        ----------
        task_id : str
            Task ID
        data : dict[str, Any] | None
            Data for predicate evaluation

        Returns
        -------
        FireResult
            Result of firing

        Raises
        ------
        ValueError
            If task doesn't exist or is not empty
        """
        task = self.net.tasks.get(task_id)
        if task is None:
            raise ValueError(f"Unknown task: {task_id}")

        if not self.is_empty_task(task):
            raise ValueError(f"Task is not empty: {task_id}")

        # Empty tasks fire immediately without creating work items
        return self.fire_task(task_id, data)

    # --- Enhanced fire_task with busy tracking ---

    def fire_task_with_tracking(self, task_id: str, data: dict[str, Any] | None = None) -> FireResult:
        """Fire a task with full busy tracking and deferred choice handling.

        This is the enhanced version of fire_task that:
        1. Marks the task as busy
        2. Handles deferred choice (withdraws losers)
        3. Fires the task
        4. Updates enabled tasks

        Parameters
        ----------
        task_id : str
            Task ID
        data : dict[str, Any] | None
            Data for predicate evaluation

        Returns
        -------
        FireResult
            Result of firing
        """
        # Mark as busy
        self.mark_task_busy(task_id)

        # Handle deferred choice - withdraw losing tasks
        withdrawn = self._withdraw_deferred_choice_losers(task_id)

        # Fire the task
        result = self.fire_task(task_id, data)

        # Update enabled tasks after marking moved
        self._update_enabled_tasks()

        return result

    def complete_task_execution(self, task_id: str) -> None:
        """Complete task execution (called when work item completes).

        This should be called after fire_task when the work item completes.
        It marks the task as no longer busy and updates enabled tasks.

        Parameters
        ----------
        task_id : str
            Task ID
        """
        self.mark_task_complete(task_id)
        self.continue_if_possible()

    # --- Additional State Fields (for Java compatibility) ---

    # These fields support the full Java YNetRunner API
    _case_id_for_net: YIdentifier | None = field(default=None, repr=False)
    _containing_task_id: str = field(default="", repr=False)
    _specification_id: str = field(default="", repr=False)
    _start_time: int = field(default=0, repr=False)
    _observer: str = field(default="", repr=False)
    _timer_states: dict[str, Any] = field(default_factory=dict, repr=False)
    _child_runners: set[YNetRunner] = field(default_factory=set, repr=False)
    _parent_runner: YNetRunner | None = field(default=None, repr=False)
    _work_item_repository: Any = field(default=None, repr=False)  # YWorkItemRepository
    _announcer: Any = field(default=None, repr=False)  # YAnnouncer
    _engine: Any = field(default=None, repr=False)  # YEngine

    # --- Child Runner Management (Gap 6: Sub-case handling) ---

    def addChildRunner(self, child: YNetRunner) -> bool:
        """Add child runner for sub-case (composite task).

        Java signature: boolean addChildRunner(YNetRunner child)

        Parameters
        ----------
        child : YNetRunner
            Child runner to add

        Returns
        -------
        bool
            True if added successfully
        """
        if child not in self._child_runners:
            self._child_runners.add(child)
            child._parent_runner = self
            return True
        return False

    def removeChildRunner(self, child: YNetRunner) -> bool:
        """Remove child runner.

        Java signature: boolean removeChildRunner(YNetRunner child)

        Parameters
        ----------
        child : YNetRunner
            Child runner to remove

        Returns
        -------
        bool
            True if removed
        """
        if child in self._child_runners:
            self._child_runners.discard(child)
            child._parent_runner = None
            return True
        return False

    def getAllRunnersForCase(self) -> set[YNetRunner]:
        """Get all runners for this case at same level.

        Java signature: Set getAllRunnersForCase()

        Returns
        -------
        set[YNetRunner]
            All runners at same case level
        """
        # For same case, return self (single runner per case in this implementation)
        return {self}

    def getAllRunnersInTree(self) -> set[YNetRunner]:
        """Get all runners in tree (self + all descendants).

        Java signature: Set getAllRunnersInTree()

        Returns
        -------
        set[YNetRunner]
            All runners in tree
        """
        runners = {self}
        for child in self._child_runners:
            runners.update(child.getAllRunnersInTree())
        return runners

    def getTopRunner(self) -> YNetRunner:
        """Get top-level runner (root of tree).

        Java signature: YNetRunner getTopRunner()

        Returns
        -------
        YNetRunner
            Top runner
        """
        current = self
        while current._parent_runner is not None:
            current = current._parent_runner
        return current

    def getCaseRunner(self, id: YIdentifier) -> YNetRunner | None:
        """Get case runner by identifier.

        Java signature: YNetRunner getCaseRunner(YIdentifier id)

        Parameters
        ----------
        id : YIdentifier
            Case identifier

        Returns
        -------
        YNetRunner | None
            Runner or None if not found
        """
        if self._case_id_for_net and self._case_id_for_net.id == id.id:
            return self
        for child in self._child_runners:
            runner = child.getCaseRunner(id)
            if runner:
                return runner
        return None

    def getRunnerWithID(self, id: YIdentifier) -> YNetRunner | None:
        """Get runner with matching case ID.

        Java signature: YNetRunner getRunnerWithID(YIdentifier id)

        Parameters
        ----------
        id : YIdentifier
            Identifier to match

        Returns
        -------
        YNetRunner | None
            Runner or None
        """
        return self.getCaseRunner(id)

    # --- Work Item Management (Gap 7: Work item lifecycle) ---

    def createEnabledWorkItem(
        self, caseIDForNet: YIdentifier, atomicTask: YAtomicTask, pmgr: Any | None = None
    ) -> YWorkItem:
        """Create enabled work item for atomic task.

        Java signature: YWorkItem createEnabledWorkItem(YIdentifier caseIDForNet, YAtomicTask atomicTask)
        Java signature: YWorkItem createEnabledWorkItem(YPersistenceManager pmgr, YIdentifier caseIDForNet, YAtomicTask atomicTask)

        Parameters
        ----------
        caseIDForNet : YIdentifier
            Case identifier
        atomicTask : YAtomicTask
            Task to create work item for
        pmgr : Any | None
            Persistence manager (optional)

        Returns
        -------
        YWorkItem
            Created work item
        """
        from kgcl.yawl.engine.y_work_item import WorkItemStatus, YWorkItem

        work_item = YWorkItem(
            id=f"{caseIDForNet.id}-{atomicTask.id}-{self._token_counter}",
            case_id=caseIDForNet.id,
            task_id=atomicTask.id,
            specification_id=self._specification_id,
            net_id=self.net.id,
            status=WorkItemStatus.ENABLED,
        )
        self._token_counter += 1

        if self._work_item_repository:
            self._work_item_repository.add(work_item)

        if pmgr:
            # Persist if manager provided
            pass

        return work_item

    def startWorkItemInTask(
        self,
        workItem: YWorkItem | None = None,
        caseID: YIdentifier | None = None,
        taskID: str = "",
        pmgr: Any | None = None,
    ) -> None:
        """Start work item in task.

        Java signature: void startWorkItemInTask(YWorkItem workItem)
        Java signature: void startWorkItemInTask(YIdentifier caseID, String taskID)
        Java signature: void startWorkItemInTask(YPersistenceManager pmgr, YWorkItem workItem)
        Java signature: void startWorkItemInTask(YPersistenceManager pmgr, YIdentifier caseID, String taskID)

        Parameters
        ----------
        workItem : YWorkItem | None
            Work item to start
        caseID : YIdentifier | None
            Case ID (alternative)
        taskID : str
            Task ID (alternative)
        pmgr : Any | None
            Persistence manager
        """
        if workItem:
            workItem.start()
            if pmgr:
                pass  # Persist
        elif caseID and taskID:
            # Find work item by case+task
            if self._work_item_repository:
                items = self._work_item_repository.get_by_case_and_task(caseID.id, taskID)
                for item in items:
                    item.start()

    def completeWorkItemInTask(
        self,
        workItem: YWorkItem,
        caseID: YIdentifier | None = None,
        taskID: str = "",
        outputData: Any | None = None,
        completionType: str = "normal",
        pmgr: Any | None = None,
    ) -> bool:
        """Complete work item in task.

        Java signature: boolean completeWorkItemInTask(YWorkItem workItem, Document outputData, WorkItemCompletion completionType)
        Java signature: boolean completeWorkItemInTask(YWorkItem workItem, YIdentifier caseID, String taskID, Document outputData, WorkItemCompletion completionType)
        Java signature: boolean completeWorkItemInTask(YPersistenceManager pmgr, YWorkItem workItem, Document outputData)
        Java signature: boolean completeWorkItemInTask(YPersistenceManager pmgr, YWorkItem workItem, YIdentifier caseID, String taskID, Document outputData)

        Parameters
        ----------
        workItem : YWorkItem
            Work item to complete
        caseID : YIdentifier | None
            Case ID
        taskID : str
            Task ID
        outputData : Any | None
            Output data
        completionType : str
            Completion type
        pmgr : Any | None
            Persistence manager

        Returns
        -------
        bool
            True if successful
        """
        if outputData:
            workItem.complete(output_data=outputData if isinstance(outputData, dict) else {})
        else:
            workItem.complete()

        # Mark task as complete
        self.mark_task_complete(workItem.task_id)

        if pmgr:
            pass  # Persist

        return True

    def completeTask(
        self,
        workItem: YWorkItem,
        atomicTask: YAtomicTask,
        identifier: YIdentifier,
        outputData: Any | None = None,
        completionType: str = "normal",
        pmgr: Any | None = None,
    ) -> bool:
        """Complete atomic task execution.

        Java signature: boolean completeTask(YWorkItem workItem, YAtomicTask atomicTask, YIdentifier identifier, Document outputData, WorkItemCompletion completionType)
        Java signature: boolean completeTask(YPersistenceManager pmgr, YWorkItem workItem, YAtomicTask atomicTask, YIdentifier identifier, Document outputData)

        Parameters
        ----------
        workItem : YWorkItem
            Work item
        atomicTask : YAtomicTask
            Task
        identifier : YIdentifier
            Case identifier
        outputData : Any | None
            Output data
        completionType : str
            Completion type
        pmgr : Any | None
            Persistence manager

        Returns
        -------
        bool
            True if successful
        """
        return self.completeWorkItemInTask(
            workItem=workItem, outputData=outputData, completionType=completionType, pmgr=pmgr
        )

    def rollbackWorkItem(self, caseID: YIdentifier, taskID: str, pmgr: Any | None = None) -> bool:
        """Rollback work item to enabled state.

        Java signature: boolean rollbackWorkItem(YIdentifier caseID, String taskID)
        Java signature: boolean rollbackWorkItem(YPersistenceManager pmgr, YIdentifier caseID, String taskID)

        Parameters
        ----------
        caseID : YIdentifier
            Case ID
        taskID : str
            Task ID
        pmgr : Any | None
            Persistence manager

        Returns
        -------
        bool
            True if successful
        """
        # Find and rollback work item
        if self._work_item_repository:
            items = self._work_item_repository.get_by_case_and_task(caseID.id, taskID)
            for item in items:
                # Reset to enabled
                from kgcl.yawl.engine.y_work_item import WorkItemStatus

                item.status = WorkItemStatus.ENABLED
                if pmgr:
                    pass  # Persist
                return True
        return False

    # --- Composite Task Handling (Gap 8: Sub-net execution) ---

    def fireCompositeTask(self, task: YCompositeTask, pmgr: Any | None = None) -> None:
        """Fire composite task (start sub-net).

        Java signature: void fireCompositeTask(YCompositeTask task)
        Java signature: void fireCompositeTask(YCompositeTask task, YPersistenceManager pmgr)

        Parameters
        ----------
        task : YCompositeTask
            Composite task to fire
        pmgr : Any | None
            Persistence manager
        """
        # Mark task as busy
        self.mark_task_busy(task.id)

        # Create child runner for subnet
        if task.subnet_id and self._engine:
            subnet = self._engine.get_net(task.subnet_id)
            if subnet:
                child_case_id = YIdentifier(id=f"{self.case_id}-{task.id}-{self._token_counter}")
                self._token_counter += 1

                child_runner = YNetRunner(net=subnet, case_id=child_case_id.id)
                child_runner._case_id_for_net = child_case_id
                child_runner._containing_task_id = task.id
                child_runner._specification_id = self._specification_id
                child_runner._engine = self._engine

                self.addChildRunner(child_runner)

                # Start child net
                child_runner.start()

                if pmgr:
                    pass  # Persist

    def processCompletedSubnet(
        self,
        caseIDForSubnet: YIdentifier,
        busyCompositeTask: YCompositeTask,
        rawSubnetData: Any | None = None,
        pmgr: Any | None = None,
    ) -> None:
        """Process completed sub-net.

        Java signature: void processCompletedSubnet(YIdentifier caseIDForSubnet, YCompositeTask busyCompositeTask, Document rawSubnetData)
        Java signature: void processCompletedSubnet(YPersistenceManager pmgr, YIdentifier caseIDForSubnet, YCompositeTask busyCompositeTask, Document rawSubnetData)

        Parameters
        ----------
        caseIDForSubnet : YIdentifier
            Sub-net case ID
        busyCompositeTask : YCompositeTask
            Parent composite task
        rawSubnetData : Any | None
            Output data from subnet
        pmgr : Any | None
            Persistence manager
        """
        # Find child runner
        child = self.getCaseRunner(caseIDForSubnet)
        if child:
            # Remove child runner
            self.removeChildRunner(child)

        # Mark task as complete
        self.mark_task_complete(busyCompositeTask.id)

        # Fire task to produce output tokens
        data = rawSubnetData if isinstance(rawSubnetData, dict) else {}
        self.fire_task(busyCompositeTask.id, data)

        # Continue execution
        self.continue_if_possible()

        if pmgr:
            pass  # Persist

    def logCompletingTask(self, caseIDForSubnet: YIdentifier, busyCompositeTask: YCompositeTask) -> None:
        """Log composite task completion.

        Java signature: void logCompletingTask(YIdentifier caseIDForSubnet, YCompositeTask busyCompositeTask)

        Parameters
        ----------
        caseIDForSubnet : YIdentifier
            Subnet case ID
        busyCompositeTask : YCompositeTask
            Composite task
        """
        # Logging hook for composite task completion
        pass

    # --- Cancellation (Gap 9: Cancellation propagation) ---

    def cancel(self, pmgr: Any | None = None) -> None:
        """Cancel this case and all children.

        Java signature: void cancel()
        Java signature: void cancel(YPersistenceManager pmgr)

        Parameters
        ----------
        pmgr : Any | None
            Persistence manager
        """
        # Cancel all child runners
        for child in list(self._child_runners):
            child.cancel(pmgr)
            self.removeChildRunner(child)

        # Cancel all work items
        if self._work_item_repository:
            items = self._work_item_repository.get_by_case(self.case_id)
            for item in items:
                if item.is_active():
                    item.cancel()

        # Clear state
        self.busy_tasks.clear()
        self.enabled_tasks.clear()
        self.completed = True

        if pmgr:
            pass  # Persist

    def cancelTask(self, taskID: str, pmgr: Any | None = None) -> None:
        """Cancel specific task.

        Java signature: void cancelTask(String taskID)
        Java signature: void cancelTask(YPersistenceManager pmgr, String taskID)

        Parameters
        ----------
        taskID : str
            Task ID to cancel
        pmgr : Any | None
            Persistence manager
        """
        # Cancel work items for task
        if self._work_item_repository:
            items = self._work_item_repository.get_by_case_and_task(self.case_id, taskID)
            for item in items:
                if item.is_active():
                    item.cancel()

        # Remove from busy/enabled
        self.busy_tasks.discard(taskID)
        self.enabled_tasks.discard(taskID)

        if pmgr:
            pass  # Persist

    # --- Task State Tracking (Gap 10: Enhanced state management) ---

    def addBusyTask(self, ext: YTask) -> None:
        """Add task to busy set.

        Java signature: void addBusyTask(YTask ext)

        Parameters
        ----------
        ext : YTask
            Task to mark busy
        """
        self.mark_task_busy(ext.id)

    def addEnabledTask(self, ext: YTask) -> None:
        """Add task to enabled set.

        Java signature: void addEnabledTask(YTask ext)

        Parameters
        ----------
        ext : YTask
            Task to mark enabled
        """
        self.enabled_tasks.add(ext.id)

    def removeActiveTask(self, task: YTask, pmgr: Any | None = None) -> None:
        """Remove task from active sets.

        Java signature: void removeActiveTask(YTask task)
        Java signature: void removeActiveTask(YPersistenceManager pmgr, YTask task)

        Parameters
        ----------
        task : YTask
            Task to remove
        pmgr : Any | None
            Persistence manager
        """
        self.busy_tasks.discard(task.id)
        self.enabled_tasks.discard(task.id)

        if pmgr:
            pass  # Persist

    def withdrawEnabledTask(self, task: YTask, pmgr: Any | None = None) -> None:
        """Withdraw enabled task.

        Java signature: void withdrawEnabledTask(YTask task)
        Java signature: void withdrawEnabledTask(YTask task, YPersistenceManager pmgr)

        Parameters
        ----------
        task : YTask
            Task to withdraw
        pmgr : Any | None
            Persistence manager
        """
        self._withdraw_task(task.id)

        if pmgr:
            pass  # Persist

    # --- Getters (Gap 11: State access) ---

    def getNet(self) -> YNet:
        """Get the net being executed.

        Java signature: YNet getNet()

        Returns
        -------
        YNet
            The net
        """
        return self.net

    def getNetData(self) -> dict[str, Any]:
        """Get net data variables.

        Java signature: YNetData getNetData()

        Returns
        -------
        dict[str, Any]
            Net data
        """
        # Return net-level data (simplified - Java has YNetData object)
        return {}

    def getCaseID(self) -> YIdentifier:
        """Get case identifier.

        Java signature: YIdentifier getCaseID()

        Returns
        -------
        YIdentifier
            Case ID
        """
        if self._case_id_for_net:
            return self._case_id_for_net
        # Create if not set
        self._case_id_for_net = YIdentifier(id=self.case_id)
        return self._case_id_for_net

    def get_caseIDForNet(self) -> YIdentifier:
        """Get case ID for net.

        Java signature: YIdentifier get_caseIDForNet()

        Returns
        -------
        YIdentifier
            Case ID
        """
        return self.getCaseID()

    def get_caseID(self) -> str:
        """Get case ID string.

        Java signature: String get_caseID()

        Returns
        -------
        str
            Case ID string
        """
        return self.case_id

    def getContainingTaskID(self) -> str:
        """Get containing task ID (for subnets).

        Java signature: String getContainingTaskID()

        Returns
        -------
        str
            Task ID or empty string
        """
        return self._containing_task_id

    def getSpecificationID(self) -> str:
        """Get specification ID.

        Java signature: YSpecificationID getSpecificationID()

        Returns
        -------
        str
            Specification ID
        """
        return self._specification_id

    def getStartTime(self) -> int:
        """Get case start time (Unix timestamp in milliseconds).

        Java signature: long getStartTime()

        Returns
        -------
        int
            Start time
        """
        return self._start_time

    def getExecutionStatus(self) -> str:
        """Get execution status as string.

        Java signature: String getExecutionStatus()

        Returns
        -------
        str
            Status name
        """
        return self.execution_status.name

    def getActiveTasks(self) -> set[str]:
        """Get active task IDs (enabled + busy).

        Java signature: Set getActiveTasks()

        Returns
        -------
        set[str]
            Active task IDs
        """
        return self.enabled_tasks | self.busy_tasks

    def getBusyTaskNames(self) -> set[str]:
        """Get busy task names.

        Java signature: Set getBusyTaskNames()

        Returns
        -------
        set[str]
            Busy task IDs
        """
        return self.busy_tasks.copy()

    def getBusyTasks(self) -> set[YTask]:
        """Get busy tasks.

        Java signature: Set getBusyTasks()

        Returns
        -------
        set[YTask]
            Busy task objects
        """
        return {self.net.tasks[tid] for tid in self.busy_tasks if tid in self.net.tasks}

    def getEnabledTaskNames(self) -> set[str]:
        """Get enabled task names.

        Java signature: Set getEnabledTaskNames()

        Returns
        -------
        set[str]
            Enabled task IDs
        """
        return self.enabled_tasks.copy()

    def getNetElement(self, id: str) -> YTask | YCondition | None:
        """Get net element by ID.

        Java signature: YExternalNetElement getNetElement(String id)

        Parameters
        ----------
        id : str
            Element ID

        Returns
        -------
        YTask | YCondition | None
            Element or None
        """
        if id in self.net.tasks:
            return self.net.tasks[id]
        if id in self.net.conditions:
            return self.net.conditions[id]
        return None

    def getFlowsIntoTaskID(self, task: YTask) -> str:
        """Get task ID that flows into this task (for MI).

        Java signature: String getFlowsIntoTaskID(YTask task)

        Parameters
        ----------
        task : YTask
            Task to check

        Returns
        -------
        str
            Task ID or empty
        """
        # Get task that produces tokens for this task
        for flow_id in task.preset_flows:
            flow = self.net.flows.get(flow_id)
            if flow and flow.source_id in self.net.tasks:
                return flow.source_id
        return ""

    def getAnnouncer(self) -> Any:
        """Get announcer.

        Java signature: YAnnouncer getAnnouncer()

        Returns
        -------
        Any
            Announcer
        """
        return self._announcer

    def getWorkItemRepository(self) -> Any:
        """Get work item repository.

        Java signature: YWorkItemRepository getWorkItemRepository()

        Returns
        -------
        Any
            Repository
        """
        return self._work_item_repository

    def get_caseObserverStr(self) -> str:
        """Get case observer string.

        Java signature: String get_caseObserverStr()

        Returns
        -------
        str
            Observer string
        """
        return self._observer

    def get_timerStates(self) -> dict[str, Any]:
        """Get timer states.

        Java signature: Map get_timerStates()

        Returns
        -------
        dict[str, Any]
            Timer states
        """
        return self._timer_states.copy()

    # --- Setters (Gap 12: State mutation) ---

    def setNet(self, net: YNet) -> None:
        """Set the net.

        Java signature: void setNet(YNet net)

        Parameters
        ----------
        net : YNet
            Net to set
        """
        self.net = net

    def setNetData(self, data: dict[str, Any]) -> None:
        """Set net data.

        Java signature: void setNetData(YNetData data)

        Parameters
        ----------
        data : dict[str, Any]
            Net data
        """
        # Store in net-level data (simplified)
        pass

    def set_caseIDForNet(self, id: YIdentifier) -> None:
        """Set case ID for net.

        Java signature: void set_caseIDForNet(YIdentifier id)

        Parameters
        ----------
        id : YIdentifier
            Case ID
        """
        self._case_id_for_net = id
        self.case_id = id.id

    def set_caseID(self, ID: str) -> None:
        """Set case ID string.

        Java signature: void set_caseID(String ID)

        Parameters
        ----------
        ID : str
            Case ID
        """
        self.case_id = ID

    def setContainingTaskID(self, taskid: str) -> None:
        """Set containing task ID.

        Java signature: void setContainingTaskID(String taskid)

        Parameters
        ----------
        taskid : str
            Task ID
        """
        self._containing_task_id = taskid

    def setContainingTask(self, task: YCompositeTask) -> None:
        """Set containing task.

        Java signature: void setContainingTask(YCompositeTask task)

        Parameters
        ----------
        task : YCompositeTask
            Task
        """
        self._containing_task_id = task.id

    def setSpecificationID(self, id: str) -> None:
        """Set specification ID.

        Java signature: void setSpecificationID(YSpecificationID id)

        Parameters
        ----------
        id : str
            Specification ID
        """
        self._specification_id = id

    def setStartTime(self, time: int) -> None:
        """Set start time.

        Java signature: void setStartTime(long time)

        Parameters
        ----------
        time : int
            Unix timestamp in milliseconds
        """
        self._start_time = time

    def setExecutionStatus(self, status: str) -> None:
        """Set execution status from string.

        Java signature: void setExecutionStatus(String status)

        Parameters
        ----------
        status : str
            Status name
        """
        try:
            self.execution_status = ExecutionStatus[status]
        except KeyError:
            pass

    def setStateNormal(self) -> None:
        """Set execution state to normal.

        Java signature: void setStateNormal()
        """
        self.execution_status = ExecutionStatus.NORMAL

    def setStateSuspending(self) -> None:
        """Set execution state to suspending.

        Java signature: void setStateSuspending()
        """
        self.execution_status = ExecutionStatus.SUSPENDING

    def setStateSuspended(self) -> None:
        """Set execution state to suspended.

        Java signature: void setStateSuspended()
        """
        self.execution_status = ExecutionStatus.SUSPENDED

    def setStateResuming(self) -> None:
        """Set execution state to resuming.

        Java signature: void setStateResuming()
        """
        self.execution_status = ExecutionStatus.RESUMING

    def setBusyTaskNames(self, names: set[str]) -> None:
        """Set busy task names.

        Java signature: void setBusyTaskNames(Set names)

        Parameters
        ----------
        names : set[str]
            Task IDs
        """
        self.busy_tasks = names.copy()

    def setEnabledTaskNames(self, names: set[str]) -> None:
        """Set enabled task names.

        Java signature: void setEnabledTaskNames(Set names)

        Parameters
        ----------
        names : set[str]
            Task IDs
        """
        self.enabled_tasks = names.copy()

    def setAnnouncer(self, announcer: Any) -> None:
        """Set announcer.

        Java signature: void setAnnouncer(YAnnouncer announcer)

        Parameters
        ----------
        announcer : Any
            Announcer
        """
        self._announcer = announcer

    def setEngine(self, engine: Any) -> None:
        """Set engine reference.

        Java signature: void setEngine(YEngine engine)

        Parameters
        ----------
        engine : Any
            Engine
        """
        self._engine = engine

    def setObserver(self, observer: str) -> None:
        """Set case observer.

        Java signature: void setObserver(YAWLServiceReference observer)

        Parameters
        ----------
        observer : str
            Observer reference
        """
        self._observer = observer

    def set_caseObserverStr(self, obStr: str) -> None:
        """Set case observer string.

        Java signature: void set_caseObserverStr(String obStr)

        Parameters
        ----------
        obStr : str
            Observer string
        """
        self._observer = obStr

    def set_timerStates(self, states: dict[str, Any]) -> None:
        """Set timer states.

        Java signature: void set_timerStates(Map states)

        Parameters
        ----------
        states : dict[str, Any]
            Timer states
        """
        self._timer_states = states.copy()

    # --- Timer Support (Gap 13: Timer management) ---

    def initTimerStates(self) -> None:
        """Initialize timer states.

        Java signature: void initTimerStates()
        """
        self._timer_states = {}

    def restoreTimerStates(self) -> None:
        """Restore timer states from persistence.

        Java signature: void restoreTimerStates()
        """
        # Hook for restoring timers
        pass

    def updateTimerState(self, task: YTask, state: Any) -> None:
        """Update timer state for task.

        Java signature: void updateTimerState(YTask task, YWorkItemTimer state)
        Java signature: void updateTimerState(YTask task, State state)

        Parameters
        ----------
        task : YTask
            Task
        state : Any
            Timer state
        """
        self._timer_states[task.id] = state

    def getTimerVariable(self, taskName: str) -> Any:
        """Get timer variable for task.

        Java signature: YTimerVariable getTimerVariable(String taskName)

        Parameters
        ----------
        taskName : str
            Task name

        Returns
        -------
        Any
            Timer variable or None
        """
        return self._timer_states.get(taskName)

    def getTimeOutTaskSet(self, item: YWorkItem) -> list[str]:
        """Get timeout task set for work item.

        Java signature: List getTimeOutTaskSet(YWorkItem item)

        Parameters
        ----------
        item : YWorkItem
            Work item

        Returns
        -------
        list[str]
            Task IDs with timeouts
        """
        # Return tasks with timers
        return [tid for tid in self._timer_states.keys()]

    def isTimeServiceTask(self, item: YWorkItem) -> bool:
        """Check if work item is time service task.

        Java signature: boolean isTimeServiceTask(YWorkItem item)

        Parameters
        ----------
        item : YWorkItem
            Work item

        Returns
        -------
        bool
            True if time service task
        """
        return item.task_id in self._timer_states

    def restartTimerIfRequired(self, item: YWorkItem) -> None:
        """Restart timer if required.

        Java signature: void restartTimerIfRequired(YWorkItem item)

        Parameters
        ----------
        item : YWorkItem
            Work item
        """
        # Hook for restarting timers
        pass

    def evaluateTimerPredicate(self, predicate: str) -> bool:
        """Evaluate timer predicate.

        Java signature: boolean evaluateTimerPredicate(String predicate)

        Parameters
        ----------
        predicate : str
            Predicate expression

        Returns
        -------
        bool
            Evaluation result
        """
        return self._evaluate_predicate(predicate, {})

    # --- Multi-Instance Support (Gap 14: Dynamic instances) ---

    def addNewInstance(
        self, taskID: str, aSiblingInstance: YIdentifier, newInstanceData: Any | None = None, pmgr: Any | None = None
    ) -> YIdentifier:
        """Add new MI instance dynamically.

        Java signature: YIdentifier addNewInstance(String taskID, YIdentifier aSiblingInstance, Element newInstanceData)
        Java signature: YIdentifier addNewInstance(YPersistenceManager pmgr, String taskID, YIdentifier aSiblingInstance, Element newInstanceData)

        Parameters
        ----------
        taskID : str
            Task ID
        aSiblingInstance : YIdentifier
            Sibling instance identifier
        newInstanceData : Any | None
            Data for new instance
        pmgr : Any | None
            Persistence manager

        Returns
        -------
        YIdentifier
            New instance identifier
        """
        # Create new MI instance
        new_id = YIdentifier(id=f"{aSiblingInstance.id}-{self._token_counter}", parent=aSiblingInstance)
        self._token_counter += 1

        if newInstanceData:
            new_id.data = newInstanceData if isinstance(newInstanceData, dict) else {}

        if pmgr:
            pass  # Persist

        return new_id

    def isAddEnabled(self, taskID: str, childID: YIdentifier) -> bool:
        """Check if adding MI instance is enabled.

        Java signature: boolean isAddEnabled(String taskID, YIdentifier childID)

        Parameters
        ----------
        taskID : str
            Task ID
        childID : YIdentifier
            Child identifier

        Returns
        -------
        bool
            True if add enabled
        """
        # Check if task allows dynamic instances
        task = self.net.tasks.get(taskID)
        if task and hasattr(task, "mi_creation_mode"):
            return task.mi_creation_mode == "dynamic"
        return False

    # --- Atomic Task Firing (Gap 15: Atomic task execution) ---

    def attemptToFireAtomicTask(self, taskID: str, pmgr: Any | None = None) -> list[YWorkItem]:
        """Attempt to fire atomic task.

        Java signature: List attemptToFireAtomicTask(String taskID)
        Java signature: List attemptToFireAtomicTask(YPersistenceManager pmgr, String taskID)

        Parameters
        ----------
        taskID : str
            Task ID
        pmgr : Any | None
            Persistence manager

        Returns
        -------
        list[YWorkItem]
            Created work items
        """
        task = self.net.tasks.get(taskID)
        if not task or not self._is_task_enabled(task):
            return []

        from kgcl.yawl.elements.y_atomic_task import YAtomicTask

        if isinstance(task, YAtomicTask):
            work_item = self.createEnabledWorkItem(self.getCaseID(), task, pmgr)
            return [work_item]

        return []

    def fireAtomicTask(self, task: YAtomicTask, groupID: str = "", pmgr: Any | None = None) -> Any:
        """Fire atomic task.

        Java signature: YWorkItemEvent fireAtomicTask(YAtomicTask task, String groupID)
        Java signature: YAnnouncement fireAtomicTask(YAtomicTask task, String groupID, YPersistenceManager pmgr)

        Parameters
        ----------
        task : YAtomicTask
            Task to fire
        groupID : str
            Group ID for deferred choice
        pmgr : Any | None
            Persistence manager

        Returns
        -------
        Any
            Work item event or announcement
        """
        # Create work item
        work_item = self.createEnabledWorkItem(self.getCaseID(), task, pmgr)

        # Fire work item
        work_item.fire()

        # Mark task busy
        self.mark_task_busy(task.id)

        if pmgr:
            pass  # Persist

        return work_item

    def processEmptyTask(self, task: YAtomicTask, pmgr: Any | None = None) -> None:
        """Process empty (passthrough) task.

        Java signature: void processEmptyTask(YAtomicTask task)
        Java signature: void processEmptyTask(YAtomicTask task, YPersistenceManager pmgr)

        Parameters
        ----------
        task : YAtomicTask
            Empty task
        pmgr : Any | None
            Persistence manager
        """
        if self.is_empty_task(task):
            self.fire_empty_task(task.id)

        if pmgr:
            pass  # Persist

    # --- Lifecycle & Initialization (Gap 16: Initialization) ---

    def init(self) -> None:
        """Initialize runner.

        Java signature: void init()
        """
        self.initTimerStates()
        self._update_enabled_tasks()

    def initialise(
        self, netPrototype: YNet, caseIDForNet: YIdentifier, incomingData: Any | None = None, pmgr: Any | None = None
    ) -> None:
        """Initialize runner with net and case ID.

        Java signature: void initialise(YNet netPrototype, YIdentifier caseIDForNet, Element incomingData)
        Java signature: void initialise(YPersistenceManager pmgr, YNet netPrototype, YIdentifier caseIDForNet, Element incomingData)

        Parameters
        ----------
        netPrototype : YNet
            Net to execute
        caseIDForNet : YIdentifier
            Case identifier
        incomingData : Any | None
            Input data
        pmgr : Any | None
            Persistence manager
        """
        self.net = netPrototype
        self._case_id_for_net = caseIDForNet
        self.case_id = caseIDForNet.id

        if incomingData:
            # Store incoming data
            pass

        self.init()

        if pmgr:
            pass  # Persist

    def prepare(self, pmgr: Any | None = None) -> None:
        """Prepare runner for execution.

        Java signature: void prepare()
        Java signature: void prepare(YPersistenceManager pmgr)

        Parameters
        ----------
        pmgr : Any | None
            Persistence manager
        """
        self._update_enabled_tasks()

        if pmgr:
            pass  # Persist

    def kick(self, pmgr: Any | None = None) -> None:
        """Kick runner to continue execution.

        Java signature: void kick()
        Java signature: void kick(YPersistenceManager pmgr)

        Parameters
        ----------
        pmgr : Any | None
            Persistence manager
        """
        self.continue_if_possible()

        if pmgr:
            pass  # Persist

    def restoreObservers(self) -> None:
        """Restore observers from persistence.

        Java signature: void restoreObservers()
        """
        # Hook for restoring observers
        pass

    # --- Fire Tasks (Gap 17: Batch firing) ---

    def fireTasks(self, enabledSet: Any, pmgr: Any | None = None) -> None:
        """Fire multiple enabled tasks.

        Java signature: void fireTasks(YEnabledTransitionSet enabledSet)
        Java signature: void fireTasks(YEnabledTransitionSet enabledSet, YPersistenceManager pmgr)

        Parameters
        ----------
        enabledSet : Any
            Set of enabled tasks
        pmgr : Any | None
            Persistence manager
        """
        # Fire all tasks in enabled set
        if hasattr(enabledSet, "tasks"):
            for task in enabledSet.tasks:
                if isinstance(task, YAtomicTask):
                    self.fireAtomicTask(task, pmgr=pmgr)
                elif isinstance(task, YCompositeTask):
                    self.fireCompositeTask(task, pmgr)

    # --- Status Checks (Gap 18: State queries) ---

    def isRootNet(self) -> bool:
        """Check if this is root net runner.

        Java signature: boolean isRootNet()

        Returns
        -------
        bool
            True if root
        """
        return self._parent_runner is None

    def isAlive(self) -> bool:
        """Check if runner is alive (not completed).

        Java signature: boolean isAlive()

        Returns
        -------
        bool
            True if alive
        """
        return not self.completed

    def isCompleted(self) -> bool:
        """Check if runner completed.

        Java signature: boolean isCompleted()

        Returns
        -------
        bool
            True if completed
        """
        return self.completed

    def isEmpty(self) -> bool:
        """Check if net is empty (no active tasks).

        Java signature: boolean isEmpty()

        Returns
        -------
        bool
            True if empty
        """
        return not self.has_active_tasks()

    def isSuspending(self) -> bool:
        """Check if suspending.

        Java signature: boolean isSuspending()

        Returns
        -------
        bool
            True if suspending
        """
        return self.execution_status == ExecutionStatus.SUSPENDING

    def isSuspended(self) -> bool:
        """Check if suspended.

        Java signature: boolean isSuspended()

        Returns
        -------
        bool
            True if suspended
        """
        return self.execution_status == ExecutionStatus.SUSPENDED

    def isResuming(self) -> bool:
        """Check if resuming.

        Java signature: boolean isResuming()

        Returns
        -------
        bool
            True if resuming
        """
        return self.execution_status == ExecutionStatus.RESUMING

    def hasNormalState(self) -> bool:
        """Check if in normal execution state.

        Java signature: boolean hasNormalState()

        Returns
        -------
        bool
            True if normal
        """
        return self.execution_status == ExecutionStatus.NORMAL

    def deadLocked(self) -> bool:
        """Check if deadlocked.

        Java signature: boolean deadLocked()

        Returns
        -------
        bool
            True if deadlocked
        """
        return self.is_deadlocked()

    def endOfNetReached(self) -> bool:
        """Check if end of net reached.

        Java signature: boolean endOfNetReached()

        Returns
        -------
        bool
            True if at end
        """
        return self.completed

    def warnIfNetNotEmpty(self) -> bool:
        """Warn if net not empty at completion.

        Java signature: boolean warnIfNetNotEmpty()

        Returns
        -------
        bool
            True if warning issued
        """
        if self.completed and not self.marking.is_empty():
            return True
        return False

    # --- Announcements (Gap 19: Event announcements) ---

    def announceCaseCompletion(self) -> None:
        """Announce case completion.

        Java signature: void announceCaseCompletion()
        """
        # Hook for announcing completion
        if self._announcer:
            pass  # Announce

    def refreshAnnouncements(self) -> set[Any]:
        """Refresh announcements for restore.

        Java signature: Set refreshAnnouncements()

        Returns
        -------
        set[Any]
            Announcements
        """
        return set()

    def generateItemReannouncements(self) -> list[Any]:
        """Generate work item re-announcements.

        Java signature: List generateItemReannouncements()

        Returns
        -------
        list[Any]
            Re-announcements
        """
        return []

    def getLogPredicate(self, logPredicate: Any, trigger: str) -> Any:
        """Get log predicate.

        Java signature: YLogDataItemList getLogPredicate(YLogPredicate logPredicate, String trigger)

        Parameters
        ----------
        logPredicate : Any
            Log predicate
        trigger : str
            Trigger type

        Returns
        -------
        Any
            Log data items
        """
        return None

    # --- Deadlock Handling (Gap 20: Deadlock detection) ---

    def notifyDeadLock(self, pmgr: Any | None = None) -> None:
        """Notify of deadlock condition.

        Java signature: void notifyDeadLock()
        Java signature: void notifyDeadLock(YPersistenceManager pmgr)

        Parameters
        ----------
        pmgr : Any | None
            Persistence manager
        """
        # Hook for deadlock notification
        if self._announcer:
            pass  # Announce deadlock

        if pmgr:
            pass  # Persist

    def createDeadlockItem(self, pmgr: Any, task: YTask) -> None:
        """Create deadlock work item.

        Java signature: void createDeadlockItem(YPersistenceManager pmgr, YTask task)

        Parameters
        ----------
        pmgr : Any
            Persistence manager
        task : YTask
            Deadlocked task
        """
        from kgcl.yawl.engine.y_work_item import WorkItemStatus, YWorkItem

        deadlock_item = YWorkItem(
            id=f"{self.case_id}-deadlock-{task.id}",
            case_id=self.case_id,
            task_id=task.id,
            status=WorkItemStatus.DEADLOCKED,
        )

        if self._work_item_repository:
            self._work_item_repository.add(deadlock_item)

    # --- Persistence (Gap 21: Persistence hooks) ---

    def removeFromPersistence(self, pmgr: Any) -> None:
        """Remove from persistence.

        Java signature: void removeFromPersistence(YPersistenceManager pmgr)

        Parameters
        ----------
        pmgr : Any
            Persistence manager
        """
        # Hook for removal from persistence
        pass

    # --- Utility Methods (Gap 22: Debugging & display) ---

    def dump(self, tasks: set[YTask] | None = None, label: str = "") -> None:
        """Dump state for debugging.

        Java signature: void dump()
        Java signature: void dump(Set tasks, String label)

        Parameters
        ----------
        tasks : set[YTask] | None
            Tasks to dump
        label : str
            Label for dump
        """
        # Debugging output
        if label:
            print(f"=== {label} ===")
        print(f"Case: {self.case_id}")
        print(f"Status: {self.execution_status.name}")
        print(f"Completed: {self.completed}")
        print(f"Enabled: {self.enabled_tasks}")
        print(f"Busy: {self.busy_tasks}")
        if tasks:
            print(f"Tasks: {[t.id for t in tasks]}")

    def toString(self) -> str:
        """String representation.

        Java signature: String toString()

        Returns
        -------
        str
            String representation
        """
        return f"YNetRunner(case={self.case_id}, net={self.net.id}, status={self.execution_status.name})"

    def setToCSV(self, tasks: set[YTask]) -> str:
        """Convert task set to CSV.

        Java signature: String setToCSV(Set tasks)

        Parameters
        ----------
        tasks : set[YTask]
            Tasks

        Returns
        -------
        str
            CSV string
        """
        return ",".join(t.id for t in tasks)

    def equals(self, other: object) -> bool:
        """Equality check.

        Java signature: boolean equals(Object other)

        Parameters
        ----------
        other : object
            Other object

        Returns
        -------
        bool
            True if equal
        """
        if not isinstance(other, YNetRunner):
            return False
        return self.case_id == other.case_id and self.net.id == other.net.id

    def hashCode(self) -> int:
        """Hash code.

        Java signature: int hashCode()

        Returns
        -------
        int
            Hash code
        """
        return hash((self.case_id, self.net.id))

    def __hash__(self) -> int:
        """Python hash for set/dict use."""
        return self.hashCode()

    def __eq__(self, other: object) -> bool:
        """Python equality for set/dict use."""
        return self.equals(other)
