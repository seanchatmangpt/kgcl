"""Workflow net definition (mirrors Java YNet).

A YNet is a Petri net with one input condition (start place),
one output condition (end place), and tasks and conditions
connected by flows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from kgcl.yawl.elements.y_condition import ConditionType, YCondition
from kgcl.yawl.elements.y_flow import YFlow
from kgcl.yawl.elements.y_task import YTask

if TYPE_CHECKING:
    pass


@dataclass
class YNet:
    """Workflow net definition (mirrors Java YNet).

    A YNet is a Petri net with exactly one input condition (start place)
    and one output condition (end place). Tasks and conditions are
    connected by flows.

    This follows the YAWL formal semantics where a workflow net is a
    tuple (P, T, F, i, o) where:
    - P is a set of places (conditions)
    - T is a set of transitions (tasks)
    - F is a set of arcs (flows)
    - i is the unique input place
    - o is the unique output place

    Parameters
    ----------
    id : str
        Unique identifier for this net
    name : str
        Human-readable name
    input_condition : YCondition | None
        Start place (unique input condition)
    output_condition : YCondition | None
        End place (unique output condition)
    conditions : dict[str, YCondition]
        All conditions by ID
    tasks : dict[str, YTask]
        All tasks by ID
    flows : dict[str, YFlow]
        All flows by ID
    local_variables : dict[str, str]
        Local data elements (name → type)

    Examples
    --------
    >>> net = YNet(id="simple")
    >>> start = YCondition(id="start", condition_type=ConditionType.INPUT)
    >>> end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
    >>> net.input_condition = start
    >>> net.output_condition = end
    >>> net.add_condition(start)
    >>> net.add_condition(end)
    """

    id: str
    name: str = ""

    # Special conditions
    input_condition: YCondition | None = None
    output_condition: YCondition | None = None

    # Elements
    conditions: dict[str, YCondition] = field(default_factory=dict)
    tasks: dict[str, YTask] = field(default_factory=dict)
    flows: dict[str, YFlow] = field(default_factory=dict)

    # Local variables (data elements)
    local_variables: dict[str, str] = field(default_factory=dict)

    def add_condition(self, condition: YCondition) -> None:
        """Add condition to net.

        Parameters
        ----------
        condition : YCondition
            Condition to add

        Examples
        --------
        >>> net = YNet(id="test")
        >>> cond = YCondition(id="c1")
        >>> net.add_condition(cond)
        >>> "c1" in net.conditions
        True
        """
        condition.net_id = self.id
        self.conditions[condition.id] = condition

        # Auto-set input/output if type indicates
        if condition.condition_type == ConditionType.INPUT:
            self.input_condition = condition
        elif condition.condition_type == ConditionType.OUTPUT:
            self.output_condition = condition

    def add_task(self, task: YTask) -> None:
        """Add task to net.

        Parameters
        ----------
        task : YTask
            Task to add

        Examples
        --------
        >>> net = YNet(id="test")
        >>> task = YTask(id="A")
        >>> net.add_task(task)
        >>> "A" in net.tasks
        True
        """
        task.net_id = self.id
        self.tasks[task.id] = task

    def add_flow(self, flow: YFlow) -> None:
        """Add flow and update element connections.

        Automatically updates the preset/postset lists of
        connected elements.

        Parameters
        ----------
        flow : YFlow
            Flow to add

        Examples
        --------
        >>> net = YNet(id="test")
        >>> cond = YCondition(id="c1")
        >>> task = YTask(id="A")
        >>> net.add_condition(cond)
        >>> net.add_task(task)
        >>> net.add_flow(YFlow(id="f1", source_id="c1", target_id="A"))
        >>> "f1" in cond.postset_flows
        True
        >>> "f1" in task.preset_flows
        True
        """
        self.flows[flow.id] = flow

        # Update source element's postset
        if flow.source_id in self.conditions:
            self.conditions[flow.source_id].postset_flows.append(flow.id)
        elif flow.source_id in self.tasks:
            self.tasks[flow.source_id].postset_flows.append(flow.id)

        # Update target element's preset
        if flow.target_id in self.conditions:
            self.conditions[flow.target_id].preset_flows.append(flow.id)
        elif flow.target_id in self.tasks:
            self.tasks[flow.target_id].preset_flows.append(flow.id)

    def get_element(self, element_id: str) -> YCondition | YTask | None:
        """Get element by ID (condition or task).

        Parameters
        ----------
        element_id : str
            ID of element to retrieve

        Returns
        -------
        YCondition | YTask | None
            Element or None if not found

        Examples
        --------
        >>> net = YNet(id="test")
        >>> net.add_condition(YCondition(id="c1"))
        >>> net.get_element("c1").id
        'c1'
        """
        return self.conditions.get(element_id) or self.tasks.get(element_id)

    def get_flow(self, flow_id: str) -> YFlow | None:
        """Get flow by ID.

        Parameters
        ----------
        flow_id : str
            ID of flow to retrieve

        Returns
        -------
        YFlow | None
            Flow or None if not found
        """
        return self.flows.get(flow_id)

    def get_preset_elements(self, element_id: str) -> list[YCondition | YTask]:
        """Get all elements in the preset of an element.

        Parameters
        ----------
        element_id : str
            ID of element

        Returns
        -------
        list[YCondition | YTask]
            Elements with flows leading to this element
        """
        element = self.get_element(element_id)
        if element is None:
            return []

        preset = []
        for flow_id in element.preset_flows:
            flow = self.flows.get(flow_id)
            if flow:
                source = self.get_element(flow.source_id)
                if source:
                    preset.append(source)
        return preset

    def get_postset_elements(self, element_id: str) -> list[YCondition | YTask]:
        """Get all elements in the postset of an element.

        Parameters
        ----------
        element_id : str
            ID of element

        Returns
        -------
        list[YCondition | YTask]
            Elements with flows from this element
        """
        element = self.get_element(element_id)
        if element is None:
            return []

        postset = []
        for flow_id in element.postset_flows:
            flow = self.flows.get(flow_id)
            if flow:
                target = self.get_element(flow.target_id)
                if target:
                    postset.append(target)
        return postset

    def get_condition_count(self) -> int:
        """Get number of conditions.

        Returns
        -------
        int
            Number of conditions in net
        """
        return len(self.conditions)

    def get_task_count(self) -> int:
        """Get number of tasks.

        Returns
        -------
        int
            Number of tasks in net
        """
        return len(self.tasks)

    def get_flow_count(self) -> int:
        """Get number of flows.

        Returns
        -------
        int
            Number of flows in net
        """
        return len(self.flows)

    def is_valid(self) -> bool:
        """Check if net has required structure.

        A valid YAWL net must have:
        - Exactly one input condition
        - Exactly one output condition
        - At least one task

        Returns
        -------
        bool
            True if net is structurally valid
        """
        return self.input_condition is not None and self.output_condition is not None and len(self.tasks) > 0

    def add_local_variable(self, name: str, var_type: str) -> None:
        """Add local variable to net.

        Parameters
        ----------
        name : str
            Variable name
        var_type : str
            Variable type (e.g., "string", "integer", "boolean")
        """
        self.local_variables[name] = var_type

    def __hash__(self) -> int:
        """Hash by ID for use in sets/dicts."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Equality by ID."""
        if not isinstance(other, YNet):
            return NotImplemented
        return self.id == other.id
