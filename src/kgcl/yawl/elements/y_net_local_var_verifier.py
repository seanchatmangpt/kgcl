"""Net local variable verifier (mirrors Java YNetLocalVarVerifier).

Walks the net in reverse to discover any task-level input data variables
that map from net-level local variables that have no initial value and
won't be assigned a value by a task earlier in the net.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from kgcl.yawl.elements.y_atomic_task import YAtomicTask
from kgcl.yawl.elements.y_condition import YCondition, YInputCondition
from kgcl.yawl.elements.y_decomposition import YParameter, YVariable
from kgcl.yawl.elements.y_external_net_element import YExternalNetElement
from kgcl.yawl.elements.y_net import YNet
from kgcl.yawl.elements.y_task import YTask
from kgcl.yawl.engine.y_engine import YVerificationHandler

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Parameter type constants (mirrors Java YParameter)
_INPUT_PARAM_TYPE = 0
_OUTPUT_PARAM_TYPE = 1


@dataclass
class LocalTaskMap:
    """Stores tasks that reference a specific uninitialized local variable.

    Parameters
    ----------
    local_var : YVariable
        The uninitialized local variable
    input_tasks : set[YTask]
        Tasks that reference this variable as input
    output_tasks : dict[YTask, bool]
        Tasks that output to this variable (value indicates if mandatory)
    """

    local_var: YVariable
    input_tasks: set[YTask] = field(default_factory=set)
    output_tasks: dict[YTask, bool] = field(default_factory=dict)

    def is_initialising_task(self, task: YTask) -> bool:
        """Check if task will map a value to the local variable.

        Parameters
        ----------
        task : YTask
            Task to check

        Returns
        -------
        bool
            True if task maps a mandatory value
        """
        return self.output_tasks.get(task, False)

    def add(self, task: YTask, param_type: int, param_name: str) -> None:
        """Add task to map.

        Parameters
        ----------
        task : YTask
            Task to add
        param_type : int
            Parameter type (INPUT or OUTPUT)
        param_name : str
            Parameter name
        """
        if param_type == _INPUT_PARAM_TYPE:
            self.input_tasks.add(task)
        else:
            # Check if parameter is optional
            optional = self._is_optional_param(task, param_name)
            self.output_tasks[task] = not optional

    def _is_optional_param(self, task: YTask, param_name: str) -> bool:
        """Check if variable is optional.

        Parameters
        ----------
        task : YTask
            Task containing the variable
        param_name : str
            Parameter name

        Returns
        -------
        bool
            True if optional
        """
        if isinstance(task, YAtomicTask):
            decomp = task.get_decomposition_prototype()
            if decomp:
                output_params = decomp.get_output_parameters()
                if output_params:
                    param = output_params.get(param_name)
                    if param:
                        return not param.is_mandatory
        return False


@dataclass
class YNetLocalVarVerifier:
    """Verifies net-level local variables are initialized before use.

    Walks the net in reverse to discover any task-level input data variables
    that map from net-level local variables that have no initial value and
    won't be assigned a value by a task earlier in the net.

    Parameters
    ----------
    net : YNet
        Net to verify
    """

    net: YNet
    _uninitialised_local_vars: dict[str, LocalTaskMap] = field(default_factory=dict, init=False, repr=False)

    def verify(self, handler: YVerificationHandler) -> None:
        """Verify the net.

        Parameters
        ----------
        handler : YVerificationHandler
            Verification handler to report issues
        """
        # Get all local vars that don't have an initial value
        self._get_uninitialised_local_vars()

        # Populate maps with tasks that have any uninitialised locals in mappings
        self._populate_local_task_maps()

        # Check all paths for each input task for each local var
        for local_task_map in self._uninitialised_local_vars.values():
            self._verify_paths(local_task_map, handler)

    def _get_uninitialised_local_vars(self) -> None:
        """Build set of uninitialised local variables for this net."""
        output_param_names = set(self.net.get_output_parameter_names())

        for local_var in self.net.get_local_variables().values():
            # If optional or complex type with minOccurs=0, doesn't need value
            if local_var.is_optional() or not local_var.requires_input_value():
                continue

            # If needs initial value but doesn't have one
            if not local_var.get_initial_value():
                # Output parameters have mirrored local vars, ignore those
                if local_var.get_preferred_name() not in output_param_names:
                    local_map = LocalTaskMap(local_var)
                    self._uninitialised_local_vars[local_var.get_preferred_name()] = local_map

    def _populate_local_task_maps(self) -> None:
        """Populate maps with tasks that reference uninitialised locals."""
        for task in self.net.get_net_tasks():
            self._populate_maps_for_task(task, _INPUT_PARAM_TYPE)
            self._populate_maps_for_task(task, _OUTPUT_PARAM_TYPE)

    def _populate_maps_for_task(self, task: YTask, param_type: int) -> None:
        """Add task to map if it references uninitialised local variable.

        Parameters
        ----------
        task : YTask
            Task to check
        param_type : int
            Parameter type (INPUT or OUTPUT)
        """
        param_names = self._get_param_names_for_task(task, param_type)
        for param_name in param_names:
            if param_name:
                self._add_task_if_query_has_local_var(task, param_name, param_type)

    def _get_param_names_for_task(self, task: YTask, param_type: int) -> list[str]:
        """Get parameter names for task.

        Parameters
        ----------
        task : YTask
            Task
        param_type : int
            Parameter type

        Returns
        -------
        list[str]
            List of parameter names
        """
        if param_type == _INPUT_PARAM_TYPE:
            return list(task.get_param_names_for_task_starting())
        else:
            return list(task.get_param_names_for_task_completion())

    def _add_task_if_query_has_local_var(self, task: YTask, param_name: str, param_type: int) -> None:
        """Add task if query references uninitialised local variable.

        Parameters
        ----------
        task : YTask
            Task to check
        param_name : str
            Parameter name
        param_type : int
            Parameter type
        """
        query = self._get_query_for_param(task, param_name, param_type)
        if query:
            for local_var_name in self._uninitialised_local_vars.keys():
                if self._query_references_local_var(
                    query, local_var_name, param_type
                ) or self._mi_task_outputs_to_local_var(task, query, local_var_name, param_type):
                    task_map = self._uninitialised_local_vars[local_var_name]
                    task_map.add(task, param_type, param_name)

    def _get_query_for_param(self, task: YTask, param_name: str, param_type: int) -> str | None:
        """Get XQuery mapping for task variable.

        Parameters
        ----------
        task : YTask
            Task
        param_name : str
            Parameter name
        param_type : int
            Parameter type

        Returns
        -------
        str | None
            XQuery mapping
        """
        if param_type == _INPUT_PARAM_TYPE:
            return task.get_data_binding_for_input_param(param_name)
        else:
            return task.get_data_binding_for_output_param(param_name)

    def _query_references_local_var(self, query: str, local_var_name: str, param_type: int) -> bool:
        """Check if XQuery references local variable.

        Parameters
        ----------
        query : str
            XQuery mapping
        local_var_name : str
            Local variable name
        param_type : int
            Parameter type

        Returns
        -------
        bool
            True if references local variable
        """
        mask = self._get_var_mask(local_var_name, param_type)
        if param_type == _INPUT_PARAM_TYPE:
            return mask in query
        else:
            return query.startswith(mask)

    def _get_var_mask(self, name: str, param_type: int) -> str:
        """Build template to search XQuery for local variable.

        Parameters
        ----------
        name : str
            Local variable name
        param_type : int
            Parameter type

        Returns
        -------
        str
            Search template
        """
        if param_type == _INPUT_PARAM_TYPE:
            # Input mapping contains XPath: /netID/variableName/
            return f"/{self.net.id}/{name}/"
        else:
            # Output mapping starts with XML element: <variableName>
            return f"<{name}>"

    def _mi_task_outputs_to_local_var(self, task: YTask, query: str, local_var_name: str, param_type: int) -> bool:
        """Check if MI task output maps to local variable.

        Parameters
        ----------
        task : YTask
            MI task
        query : str
            Output XQuery
        local_var_name : str
            Local variable name
        param_type : int
            Parameter type

        Returns
        -------
        bool
            True if output maps to local variable
        """
        if task.is_multi_instance() and param_type != _INPUT_PARAM_TYPE:
            # Simplified - would need actual MI output assignment var method
            return False
        return False

    def _verify_paths(self, local_task_map: LocalTaskMap, handler: YVerificationHandler) -> None:
        """Verify all tasks with variables referencing uninitialised local.

        Parameters
        ----------
        local_task_map : LocalTaskMap
            Map of referencing tasks
        handler : YVerificationHandler
            Verification handler
        """
        # For each affected task, check backward paths to start condition
        for task in local_task_map.input_tasks:
            self._verify_path(local_task_map, task, task, [], handler)

    def _verify_path(
        self,
        local_task_map: LocalTaskMap,
        subject_task: YTask,
        base_element: YExternalNetElement,
        visited: list[YExternalNetElement],
        handler: YVerificationHandler,
    ) -> None:
        """Recursively walk reverse path to find initializing task.

        Parameters
        ----------
        local_task_map : LocalTaskMap
            Map of tasks referencing local variable
        subject_task : YTask
            Originating task being checked
        base_element : YExternalNetElement
            Current element in traversal
        visited : list[YExternalNetElement]
            Elements visited so far
        handler : YVerificationHandler
            Verification handler
        """
        visited.append(base_element)

        # Get preset elements (simplified - would need net structure)
        preset_elements: list[YExternalNetElement] = []

        for pre_element in preset_elements:
            if pre_element in visited:
                continue

            if isinstance(pre_element, YInputCondition):
                # Reached start - add error/warning
                visited.append(pre_element)
                self._add_message(local_task_map, subject_task, visited, handler)
                visited = [base_element]
            elif isinstance(pre_element, YTask):
                pre_task = pre_element
                if local_task_map.is_initialising_task(pre_task):
                    # Path is OK - task initializes variable
                    visited = [base_element]
                else:
                    # Continue walking
                    self._verify_path(local_task_map, subject_task, pre_task, visited, handler)
            else:
                # Plain condition - continue
                self._verify_path(local_task_map, subject_task, pre_element, visited, handler)

    def _add_message(
        self,
        local_task_map: LocalTaskMap,
        task: YTask,
        visited: list[YExternalNetElement],
        handler: YVerificationHandler,
    ) -> None:
        """Construct verification message for path.

        Parameters
        ----------
        local_task_map : LocalTaskMap
            Map of tasks
        task : YTask
            Originating task
        visited : list[YExternalNetElement]
            Path elements
        handler : YVerificationHandler
            Verification handler
        """
        local_var = local_task_map.local_var

        # Tailor message for string types (warning) vs others (error)
        if local_var.get_data_type_name() == "string":
            sub_msg = "contain an empty string value when the mapping occurs"
            post_msg = ""
        else:
            sub_msg = "be uninitialised when the mapping is attempted"
            post_msg = (
                f" Please assign an initial value to '{local_var.get_preferred_name()}' "
                f"or ensure that a task which precedes task '{task.name}' has a "
                f"mandatory output mapping to '{local_var.get_preferred_name()}'."
            )

        # Construct chain of visited elements
        visited_chain = "["
        for i in range(len(visited) - 1, -1, -1):
            element = visited[i]
            if not (isinstance(element, YCondition) and element.is_implicit()):
                if len(visited_chain) > 1:
                    visited_chain += ", "
                visited_chain += element.id
        visited_chain += "]"

        msg = (
            f"Task '{task.name}' in Net '{self.net.id}' references Local Variable "
            f"'{local_var.get_preferred_name()}' via an input mapping, however it may "
            f"be possible for '{local_var.get_preferred_name()}' to {sub_msg}, via "
            f"the path {visited_chain}.{post_msg}"
        )

        if post_msg:
            handler.error(self.net, msg)
        else:
            handler.warn(self.net, msg)
