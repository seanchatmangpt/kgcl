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
from typing import Any

from kgcl.yawl.elements.y_identifier import YIdentifier
from kgcl.yawl.elements.y_net import YNet
from kgcl.yawl.elements.y_task import JoinType, SplitType, YTask
from kgcl.yawl.engine.y_expression import YExpressionContext, YExpressionEvaluator
from kgcl.yawl.engine.y_or_join import YOrJoinAnalyzer
from kgcl.yawl.state.y_marking import YMarking


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
