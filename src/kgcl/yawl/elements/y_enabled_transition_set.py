"""Enabled transition set for deferred choice (mirrors Java YEnabledTransitionSet).

This class collects the set of all currently enabled transitions (tasks) of a net.
It provides a completely correct implementation of the YAWL deferred choice semantics.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from kgcl.yawl.elements.y_atomic_task import YAtomicTask, YCompositeTask
from kgcl.yawl.elements.y_condition import YCondition
from kgcl.yawl.elements.y_external_net_element import YExternalNetElement
from kgcl.yawl.elements.y_task import YTask

# Type alias: YCompositeTask is YTask with decomposition
YCompositeTask = YTask

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_flow import YFlow
    from kgcl.yawl.elements.y_net import YNet


@dataclass
class TaskGroup:
    """Group of enabled tasks with shared enabling condition.

    Enabled transitions are grouped by the id of the enabling place (condition).
    For each place: if there is one or more composite tasks enabled, one of the
    composite tasks is chosen (randomly if more than one) and all other tasks
    are not fired; otherwise, all the atomic tasks are enabled, allowing a
    choice to be made from the environment.

    Parameters
    ----------
    group_id : str
        Unique identifier for this group
    composite_tasks : list[YCompositeTask]
        Composite tasks in this group
    atomic_tasks : list[YAtomicTask]
        Atomic tasks with decomposition in this group
    empty_atomic_tasks : list[YAtomicTask]
        Atomic tasks without decomposition in this group
    """

    group_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    composite_tasks: list[YCompositeTask] = field(default_factory=list)
    atomic_tasks: list[YAtomicTask] = field(default_factory=list)
    empty_atomic_tasks: list[YAtomicTask] = field(default_factory=list)

    def add(self, task: YTask) -> bool:
        """Add a task to this group.

        Parameters
        ----------
        task : YTask
            Task to add

        Returns
        -------
        bool
            True if task was added (not already present)
        """
        if isinstance(task, YCompositeTask):
            return self._add_composite_task(task)
        elif isinstance(task, YAtomicTask):
            return self._add_atomic_task(task)
        return False

    def _add_composite_task(self, task: YCompositeTask) -> bool:
        """Add composite task.

        Parameters
        ----------
        task : YCompositeTask
            Composite task to add

        Returns
        -------
        bool
            True if added
        """
        if task not in self.composite_tasks:
            self.composite_tasks.append(task)
            return True
        return False

    def _add_atomic_task(self, task: YAtomicTask) -> bool:
        """Add atomic task.

        Parameters
        ----------
        task : YAtomicTask
            Atomic task to add

        Returns
        -------
        bool
            True if added
        """
        if task.get_decomposition_prototype() is not None:
            if task not in self.atomic_tasks:
                self.atomic_tasks.append(task)
                return True
        elif task not in self.empty_atomic_tasks:
            self.empty_atomic_tasks.append(task)
            return True
        return False

    def get_atomic_tasks(self) -> set[YAtomicTask]:
        """Get set of atomic tasks in this group.

        Returns
        -------
        set[YAtomicTask]
            Set of enabled atomic tasks
        """
        return set(self.atomic_tasks)

    def has_empty_tasks(self) -> bool:
        """Check if group has at least one decomposition-less atomic task.

        Returns
        -------
        bool
            True if has empty tasks
        """
        return len(self.empty_atomic_tasks) > 0

    def get_composite_task_count(self) -> int:
        """Get number of composite tasks.

        Returns
        -------
        int
            Number of composite tasks
        """
        return len(self.composite_tasks)

    def get_empty_task_count(self) -> int:
        """Get number of empty atomic tasks.

        Returns
        -------
        int
            Number of empty atomic tasks
        """
        return len(self.empty_atomic_tasks)

    def has_composite_tasks(self) -> bool:
        """Check if group has at least one composite task.

        Returns
        -------
        bool
            True if has composite tasks
        """
        return len(self.composite_tasks) > 0

    def get_deferred_choice_id(self) -> str | None:
        """Get deferred choice UID for this group (if any).

        Returns
        -------
        str | None
            Group ID if multiple atomic tasks, None otherwise
        """
        return self.group_id if len(self.atomic_tasks) > 1 else None

    def get_random_composite_task_from_group(self) -> YCompositeTask | None:
        """Get randomly chosen composite task.

        YAWL semantics are that if there is more than one composite task
        enabled by a condition, one must be non-deterministically chosen
        to fire.

        Returns
        -------
        YCompositeTask | None
            The only composite task if one, randomly chosen one if several,
            or None if none
        """
        return self._get_random_task(self.composite_tasks)

    def get_random_empty_task_from_group(self) -> YAtomicTask | None:
        """Get randomly chosen empty task.

        Returns
        -------
        YAtomicTask | None
            Randomly chosen empty task, or None if none
        """
        return self._get_random_task(self.empty_atomic_tasks)

    def _get_random_task(self, task_list: list[YTask]) -> YTask | None:
        """Get random task from list.

        Parameters
        ----------
        task_list : list[YTask]
            List of tasks

        Returns
        -------
        YTask | None
            Random task, or None if list empty
        """
        if not task_list:
            return None
        if len(task_list) == 1:
            return task_list[0]
        return random.choice(task_list)


@dataclass
class YEnabledTransitionSet:
    """Set of enabled transitions grouped by enabling condition.

    This class collects the set of all currently enabled transitions (tasks)
    of a net. It is designed to provide a completely correct implementation
    of the YAWL deferred choice semantics.

    Enabled transitions are grouped by the id of the enabling place (condition).
    For each place: if there is one or more composite tasks enabled, one of the
    composite tasks is chosen (randomly if more than one) and all other tasks
    are not fired; otherwise, all the atomic tasks are enabled, allowing a
    choice to be made from the environment.

    Parameters
    ----------
    transitions : dict[str, TaskGroup]
        Map of [place id, set of enabled transitions]

    Examples
    --------
    >>> transition_set = YEnabledTransitionSet()
    >>> task = YTask(id="task1")
    >>> transition_set.add(task)
    >>> groups = transition_set.get_all_task_groups()
    """

    transitions: dict[str, TaskGroup] = field(default_factory=dict)

    def add(self, task: YTask, net: YNet | None = None) -> None:
        """Add an enabled task to the relevant task group.

        Parameters
        ----------
        task : YTask
            The enabled task
        net : YNet | None
            Net containing the task (for flow resolution)
        """
        for condition_id in self._get_flows_from_ids(task, net):
            self._add_to_group(condition_id, task)

    def get_all_task_groups(self) -> set[TaskGroup]:
        """Get the final set(s) of enabled transitions.

        Returns
        -------
        set[TaskGroup]
            Set of task groups (one for each enabling place)
        """
        return set(self.transitions.values())

    def is_empty(self) -> bool:
        """Check if there are no enabled transitions.

        Returns
        -------
        bool
            True if empty
        """
        return len(self.transitions) == 0

    def _add_to_group(self, condition_id: str, task: YTask) -> None:
        """Add a task to the group with the specified condition ID.

        Parameters
        ----------
        condition_id : str
            ID of the enabling condition
        task : YTask
            Enabled task
        """
        group = self.transitions.get(condition_id)
        if group is not None:
            group.add(task)
        else:
            self.transitions[condition_id] = TaskGroup()
            self.transitions[condition_id].add(task)

    def _get_flows_from_ids(self, task: YTask, net: YNet | None = None) -> set[str]:
        """Get list of condition IDs that are enabling this task.

        Parameters
        ----------
        task : YTask
            Enabled task
        net : YNet | None
            Net containing the task (for flow resolution)

        Returns
        -------
        set[str]
            Set of condition IDs
        """
        condition_ids: set[str] = set()
        if net is None:
            return condition_ids

        # Resolve preset flows to get enabling conditions
        for flow_id in task.preset_flows:
            flow = net.flows.get(flow_id)
            if flow:
                prior_element_id = flow.source_id
                prior_element = net.conditions.get(prior_element_id) or net.tasks.get(prior_element_id)
                if self._is_enabling_condition(prior_element):
                    condition_ids.add(prior_element_id)

        return condition_ids

    def _is_enabling_condition(self, element: YExternalNetElement | None) -> bool:
        """Check if element is an enabling condition.

        Parameters
        ----------
        element : YExternalNetElement | None
            Element to check

        Returns
        -------
        bool
            True if element is a condition with tokens
        """
        return isinstance(element, YCondition) and element.contains_identifier()
