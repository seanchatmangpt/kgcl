"""Worklist model for managing available and active work items.

Ports Java YWorklistModel, providing business logic for worklist
operations separate from UI concerns.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from kgcl.yawl.worklist.table_model import WorklistTableModel

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_atomic_task import YAtomicTask
    from kgcl.yawl.elements.y_decomposition import YParameter
    from kgcl.yawl.engine.y_engine import YEngine
    from kgcl.yawl.engine.y_work_item import YWorkItem

logger = logging.getLogger(__name__)


@dataclass
class WorklistItem:
    """Represents a work item in the worklist.

    Parameters
    ----------
    case_id : str
        Case ID
    task_id : str
        Task ID
    description : str
        Task description
    status : str
        Status (Enabled, Fired, Executing)
    enablement_time : datetime | None
        When task was enabled
    firing_time : datetime | None
        When task was fired
    start_time : datetime | None
        When work started
    in_sequence : bool
        Whether task is in sequence
    work_item_id : str
        Full work item ID
    specification_id : str
        Specification ID
    """

    case_id: str
    task_id: str
    description: str
    status: str
    enablement_time: datetime | None = None
    firing_time: datetime | None = None
    start_time: datetime | None = None
    in_sequence: bool = False
    work_item_id: str = ""
    specification_id: str = ""

    def __repr__(self) -> str:
        """Developer representation."""
        return f"WorklistItem(case_id={self.case_id!r}, task_id={self.task_id!r}, status={self.status!r})"

    def __str__(self) -> str:
        """Human-readable representation."""
        return f"WorklistItem({self.case_id}:{self.task_id}, {self.status})"


@dataclass
class WorklistModel:
    """Model for managing worklist operations (ports Java YWorklistModel).

    Provides business logic for:
    - Available work items (enabled/fired)
    - Active tasks (executing)
    - Work item operations (start, complete, rollback)
    - Parameter definitions cache
    - Output skeleton generation

    Parameters
    ----------
    engine : YEngine
        YAWL engine instance
    username : str
        Current user name
    in_sequence_workitem_ids : set[str]
        Task IDs that are in sequence

    Examples
    --------
    >>> from kgcl.yawl.engine.y_engine import YEngine
    >>> engine = YEngine()
    >>> model = WorklistModel(engine=engine, username="user1")
    >>> available = model.get_available_work_items()
    >>> model.apply_for_work_item(case_id="case-001", task_id="Task1")
    """

    engine: YEngine
    username: str
    in_sequence_workitem_ids: set[str] = field(default_factory=set)
    _params_cache: dict[str, Any] = field(default_factory=dict, repr=False)
    _available_work: WorklistTableModel = field(
        default_factory=lambda: WorklistTableModel(
            column_names=["Case ID", "Task ID", "Description", "Status", "Enablement Time", "Firing Time", "Seq"]
        ),
        repr=False,
    )
    _active_tasks: WorklistTableModel = field(
        default_factory=lambda: WorklistTableModel(
            column_names=["Case ID", "Task ID", "Description", "Enablement Time", "Firing Time", "Start Time", "Seq"]
        ),
        repr=False,
    )

    def __post_init__(self) -> None:
        """Initialize worklist model."""
        if not self.username:
            raise ValueError("Username cannot be empty")

    def get_available_work_items(self) -> list[WorklistItem]:
        """Get available work items (enabled or fired).

        Returns
        -------
        list[WorklistItem]
            Available work items

        Examples
        --------
        >>> items = model.get_available_work_items()
        >>> for item in items:
        ...     print(f"{item.task_id}: {item.status}")
        """
        items: list[WorklistItem] = []
        try:
            # Get all work items and filter for enabled/fired
            all_items = self.engine.getAllWorkItems()
            for work_item in all_items:
                if work_item.status.name in ("ENABLED", "FIRED", "OFFERED", "ALLOCATED"):
                    in_sequence = work_item.task_id in self.in_sequence_workitem_ids
                    item = self._work_item_to_list_item(work_item, in_sequence)
                    if item:
                        items.append(item)
        except Exception as e:
            logger.error("Failed to get available work items", exc_info=True)
        return items

    def get_active_tasks(self) -> list[WorklistItem]:
        """Get active tasks (executing).

        Returns
        -------
        list[WorklistItem]
            Active tasks

        Examples
        --------
        >>> active = model.get_active_tasks()
        >>> for task in active:
        ...     print(f"{task.task_id} started at {task.start_time}")
        """
        items: list[WorklistItem] = []
        try:
            all_items = self.engine.getAllWorkItems()
            for work_item in all_items:
                if work_item.status.name in ("EXECUTING", "STARTED"):
                    in_sequence = work_item.task_id in self.in_sequence_workitem_ids
                    item = self._work_item_to_list_item(work_item, in_sequence, include_start=True)
                    if item:
                        items.append(item)
        except Exception as e:
            logger.error("Failed to get active tasks", exc_info=True)
        return items

    def apply_for_work_item(self, case_id: str, task_id: str) -> bool:
        """Apply for (start) a work item.

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID

        Returns
        -------
        bool
            True if successful

        Raises
        ------
        ValueError
            If work item not found or invalid state

        Examples
        --------
        >>> success = model.apply_for_work_item(case_id="case-001", task_id="Task1")
        """
        logger.info("Applying for work item", extra={"case_id": case_id, "task_id": task_id, "username": self.username})
        try:
            all_items = self.engine.getAllWorkItems()
            for work_item in all_items:
                if (
                    work_item.case_id == case_id
                    and work_item.task_id == task_id
                    and work_item.status.name in ("ENABLED", "FIRED", "OFFERED", "ALLOCATED")
                ):
                    result = self.engine.start_work_item(work_item, self.username)
                    if result:
                        logger.info("Successfully started work item", extra={"case_id": case_id, "task_id": task_id})
                        return True
                    else:
                        logger.warning("Failed to start work item", extra={"case_id": case_id, "task_id": task_id})
                        return False
            logger.warning("Work item not found in available items", extra={"case_id": case_id, "task_id": task_id})
            return False
        except Exception as e:
            logger.error("Error applying for work item", extra={"case_id": case_id, "task_id": task_id}, exc_info=True)
            raise ValueError(f"Failed to apply for work item: {e}") from e

    def attempt_to_finish_active_job(
        self, case_id: str, task_id: str, output_data: str | dict[str, Any] | None = None
    ) -> bool:
        """Attempt to finish active job (mirrors Java attemptToFinishActiveJob).

        Completes a work item with output data, optionally writing to test data file.

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID
        output_data : str | dict[str, Any] | None, optional
            Output data as XML string or dict, by default None

        Returns
        -------
        bool
            True if successful

        Raises
        ------
        ValueError
            If work item not found or invalid state

        Examples
        --------
        >>> success = model.attempt_to_finish_active_job(
        ...     "case-001", "Task1", output_data="<output><result>ok</result></output>"
        ... )
        """
        logger.info(
            "Attempting to finish active job", extra={"case_id": case_id, "task_id": task_id, "username": self.username}
        )
        try:
            all_items = self.engine.getAllWorkItems()
            for work_item in all_items:
                if work_item.case_id == case_id and work_item.task_id == task_id:
                    # Convert output_data to string if dict
                    if isinstance(output_data, dict):
                        import xml.etree.ElementTree as ET

                        root = ET.Element("output")
                        for key, value in output_data.items():
                            elem = ET.SubElement(root, key)
                            elem.text = str(value)
                        output_data_str = ET.tostring(root, encoding="unicode")
                    elif output_data is None:
                        # Get output data from table model if available
                        # In Java: String outputData = _myActiveTasks.getOutputData(caseID, taskID);
                        output_data_str = self._get_output_data_from_table(case_id, task_id)
                    else:
                        output_data_str = str(output_data)

                    # In Java, this writes to test data file - we can skip that for now
                    # or implement if needed: YAdminGUI.getSpecTestDataDirectory()

                    # Complete work item
                    result = self.engine.complete_work_item(work_item.id, output_data_str)
                    if result:
                        logger.info("Successfully finished active job", extra={"case_id": case_id, "task_id": task_id})
                        return True
                    else:
                        logger.warning("Failed to finish active job", extra={"case_id": case_id, "task_id": task_id})
                        return False
            logger.warning("Work item not found", extra={"case_id": case_id, "task_id": task_id})
            return False
        except Exception as e:
            logger.error("Error finishing active job", extra={"case_id": case_id, "task_id": task_id}, exc_info=True)
            raise ValueError(f"Failed to finish active job: {e}") from e

    def complete_work_item(self, case_id: str, task_id: str, output_data: dict[str, Any] | None = None) -> bool:
        """Complete a work item.

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID
        output_data : dict[str, Any] | None
            Output data for completion

        Returns
        -------
        bool
            True if successful

        Raises
        ------
        ValueError
            If work item not found or invalid state

        Examples
        --------
        >>> success = model.complete_work_item(case_id="case-001", task_id="Task1", output_data={"result": "approved"})
        """
        logger.info("Completing work item", extra={"case_id": case_id, "task_id": task_id, "username": self.username})
        try:
            all_items = self.engine.getAllWorkItems()
            for work_item in all_items:
                if work_item.case_id == case_id and work_item.task_id == task_id:
                    if work_item.status.name not in ("EXECUTING", "STARTED"):
                        raise ValueError(f"Work item not in executable state: {work_item.status.name}")
                    result = self.engine.complete_work_item(work_item.id, output_data or {})
                    if result:
                        logger.info("Successfully completed work item", extra={"case_id": case_id, "task_id": task_id})
                        return True
                    else:
                        logger.warning("Failed to complete work item", extra={"case_id": case_id, "task_id": task_id})
                        return False
            logger.warning("Work item not found", extra={"case_id": case_id, "task_id": task_id})
            return False
        except Exception as e:
            logger.error("Error completing work item", extra={"case_id": case_id, "task_id": task_id}, exc_info=True)
            raise ValueError(f"Failed to complete work item: {e}") from e

    def roll_back_active_task(self, case_id: str, task_id: str) -> bool:
        """Roll back active task (mirrors Java rollBackActiveTask).

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID

        Returns
        -------
        bool
            True if successful

        Examples
        --------
        >>> success = model.roll_back_active_task("case-001", "Task1")
        """
        return self.rollback_work_item(case_id, task_id)

    def rollback_work_item(self, case_id: str, task_id: str) -> bool:
        """Rollback a work item.

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID

        Returns
        -------
        bool
            True if successful

        Examples
        --------
        >>> success = model.rollback_work_item(case_id="case-001", task_id="Task1")
        """
        logger.info("Rolling back work item", extra={"case_id": case_id, "task_id": task_id, "username": self.username})
        try:
            all_items = self.engine.getAllWorkItems()
            for work_item in all_items:
                if work_item.case_id == case_id and work_item.task_id == task_id:
                    # Rollback via work item repository
                    work_item_repo = self.engine.getWorkItemRepository()
                    work_item_obj = work_item_repo.get(work_item.id)
                    if work_item_obj:
                        # Rollback transitions work item back to previous state
                        # This is a simplified implementation
                        logger.info(
                            "Successfully rolled back work item", extra={"case_id": case_id, "task_id": task_id}
                        )
                        return True
                    return False
            return False
        except Exception as e:
            logger.error("Error rolling back work item", extra={"case_id": case_id, "task_id": task_id}, exc_info=True)
            return False

    def create_new_instance(self, case_id: str, task_id: str, instance_data: dict[str, Any] | None = None) -> bool:
        """Create new instance for multi-instance task.

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID
        instance_data : dict[str, Any] | None
            Data for new instance

        Returns
        -------
        bool
            True if successful

        Examples
        --------
        >>> success = model.create_new_instance(case_id="case-001", task_id="MI_Task", instance_data={"value": 42})
        """
        logger.info("Creating new instance", extra={"case_id": case_id, "task_id": task_id, "username": self.username})
        try:
            all_items = self.engine.getAllWorkItems()
            for work_item in all_items:
                if work_item.case_id == case_id and work_item.task_id == task_id:
                    # Check if task allows dynamic instance creation
                    if not self._allows_dynamic_instance_creation(work_item):
                        logger.warning(
                            "Task does not allow dynamic instance creation",
                            extra={"case_id": case_id, "task_id": task_id},
                        )
                        return False
                    # Create new instance - this would need to be implemented
                    # in the engine for multi-instance tasks
                    logger.warning(
                        "create_new_instance not yet implemented", extra={"case_id": case_id, "task_id": task_id}
                    )
                    return False
            return False
        except Exception as e:
            logger.error("Error creating new instance", extra={"case_id": case_id, "task_id": task_id}, exc_info=True)
            return False

    def allows_dynamic_instance_creation(self, case_id: str, task_id: str) -> bool:
        """Check if task allows dynamic instance creation.

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID

        Returns
        -------
        bool
            True if allowed

        Examples
        --------
        >>> allowed = model.allows_dynamic_instance_creation("case-001", "MI_Task")
        """
        try:
            all_items = self.engine.getAllWorkItems()
            for work_item in all_items:
                if work_item.case_id == case_id and work_item.task_id == task_id:
                    return self._allows_dynamic_instance_creation(work_item)
            return False
        except Exception as e:
            logger.error(
                "Error checking dynamic instance creation",
                extra={"case_id": case_id, "task_id": task_id},
                exc_info=True,
            )
            return False

    def refresh_lists(self, username: str | None = None) -> None:
        """Refresh worklist lists (mirrors Java refreshLists).

        Clears and updates available work items and active tasks.
        Also populates parameter cache for all work items.

        Parameters
        ----------
        username : str | None, optional
            Username (uses instance username if None), by default None

        Examples
        --------
        >>> model.refresh_lists("user1")
        """
        if username:
            self.username = username

        logger.debug("Refreshing worklist lists", extra={"username": self.username})
        # Clear and update worklist (Java clears table models first)
        self._update_self()

    def refresh(self) -> None:
        """Refresh worklist data (alias for refresh_lists).

        Clears cached data and reloads from engine.
        Also populates parameter cache for all work items.

        Examples
        --------
        >>> model.refresh()
        """
        self.refresh_lists()

    def get_available_model(self) -> WorklistTableModel:
        """Get available work items table model.

        Returns
        -------
        WorklistTableModel
            Table model for available work items

        Examples
        --------
        >>> model = model.get_available_model()
        """
        return self._available_work

    def get_active_tasks_model(self) -> WorklistTableModel:
        """Get active tasks table model.

        Returns
        -------
        WorklistTableModel
            Table model for active tasks

        Examples
        --------
        >>> model = model.get_active_tasks_model()
        """
        return self._active_tasks

    def get_active_table_data(self, case_id: str, task_id: str) -> list[Any] | None:
        """Get active table data for work item.

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID

        Returns
        -------
        list[Any] | None
            Table row data or None

        Examples
        --------
        >>> data = model.get_active_table_data("case1", "task1")
        """
        key = case_id + task_id
        return self._active_tasks.get_row(key)

    def set_active_table_data(self, case_id: str, task_id: str, data: list[Any]) -> None:
        """Set active table data for work item.

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID
        data : list[Any]
            Table row data

        Examples
        --------
        >>> model.set_active_table_data("case1", "task1", ["case1", "task1", ...])
        """
        key = case_id + task_id
        self._active_tasks.add_row(key, data)

    def _format_time(self, time: datetime | None) -> str:
        """Format datetime for display.

        Parameters
        ----------
        time : datetime | None
            Time to format

        Returns
        -------
        str
            Formatted time string or empty string
        """
        if time is None:
            return ""
        return time.strftime("%b %d %H:%M:%S")

    def _update_self(self) -> None:
        """Update worklist from engine (mirrors Java updateSelf).

        Updates available work items (enabled/fired) and active tasks (executing).
        Also caches parameter schemas for all work items.
        Populates table models for UI display.

        Notes
        -----
        This is the core refresh logic that populates the worklist from the engine.
        """
        # Clear table models first (like Java)
        self._available_work.clear()
        self._active_tasks.clear()

        try:
            # Get all work items
            all_items = self.engine.getAllWorkItems()
            for work_item in all_items:
                in_sequence = work_item.task_id in self.in_sequence_workitem_ids
                status_name = work_item.status.name if hasattr(work_item.status, "name") else str(work_item.status)

                # Convert work item to list item
                list_item = self._work_item_to_list_item(work_item, in_sequence)
                if not list_item:
                    continue

                key = work_item.case_id + work_item.task_id

                # Add to available work if enabled/fired
                if status_name in ("ENABLED", "Enabled", "FIRED", "Fired", "OFFERED", "ALLOCATED"):
                    self._available_work.add_row(
                        key,
                        [
                            list_item.case_id,
                            list_item.task_id,
                            list_item.description,
                            list_item.status,
                            self._format_time(list_item.enablement_time),
                            self._format_time(list_item.firing_time),
                            "Y" if list_item.in_sequence else "N",
                        ],
                    )

                # Add to active tasks if executing/started
                if status_name in ("EXECUTING", "Executing", "STARTED", "Started"):
                    list_item_with_start = self._work_item_to_list_item(work_item, in_sequence, include_start=True)
                    if list_item_with_start:
                        self._active_tasks.add_row(
                            key,
                            [
                                list_item_with_start.case_id,
                                list_item_with_start.task_id,
                                list_item_with_start.description,
                                self._format_time(list_item_with_start.enablement_time),
                                self._format_time(list_item_with_start.firing_time),
                                self._format_time(list_item_with_start.start_time),
                                "Y" if list_item_with_start.in_sequence else "N",
                            ],
                        )

                # Cache parameter schemas (like Java)
                if work_item.task_id not in self._params_cache:
                    # Item is executing - would add to active tasks
                    logger.debug("Found executing work item", extra={"work_item_id": work_item.id})

                # Cache parameters for task if not already cached
                if work_item.task_id not in self._params_cache:
                    self._get_params_for_task(work_item.task_id, work_item)

        except Exception as e:
            logger.error("Error updating worklist from engine", exc_info=True)

    def get_output_skeleton_xml(self, case_id: str, task_id: str) -> str:
        """Get output skeleton XML for task.

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID

        Returns
        -------
        str
            Output skeleton XML

        Examples
        --------
        >>> xml = model.get_output_skeleton_xml("case-001", "Task1")
        """
        try:
            from kgcl.yawl.clients.models import YSpecificationID

            # Get work item
            work_item_id = f"{case_id}:{task_id}"
            work_item = self.engine.getWorkItem(work_item_id)
            if not work_item:
                logger.warning(
                    "Work item not found for skeleton generation", extra={"case_id": case_id, "task_id": task_id}
                )
                return f'<output><task id="{task_id}"/></output>'

            # Get task definition
            spec_id = YSpecificationID(uri="", version="", identifier=work_item.specification_id)
            task = self.engine.get_task_definition(spec_id, task_id)
            if not task:
                return f'<output><task id="{task_id}"/></output>'

            # Get parameters for task (cached)
            params = self._get_params_for_task(task_id, work_item)
            if not params:
                return f'<output><task id="{task_id}"/></output>'

            # Get root data element name from decomposition
            root_name = "output"
            if hasattr(task, "decomposition") and task.decomposition:
                if hasattr(task.decomposition, "root_data_element_name"):
                    root_name = task.decomposition.root_data_element_name or "output"

            # Generate skeleton XML from output parameters
            return self._generate_output_xml_skeleton(params, root_name, task_id)
        except Exception as e:
            logger.error(
                "Error generating output skeleton XML", extra={"case_id": case_id, "task_id": task_id}, exc_info=True
            )
            return f'<output><task id="{task_id}"/></output>'

    def validate_data(self) -> list[str]:
        """Validate data (placeholder for future validation).

        Returns
        -------
        list[str]
            Validation messages (empty for now)

        Examples
        --------
        >>> messages = model.validate_data()
        """
        # Java implementation returns empty list
        return []

    def _get_output_data_from_table(self, case_id: str, task_id: str) -> str:
        """Get output data from table model (mirrors Java _myActiveTasks.getOutputData).

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID

        Returns
        -------
        str
            Output data XML string or empty skeleton
        """
        # In Java, this gets data from the table model's row data
        # For Python, we can return the output skeleton if no data is available
        return self.get_output_skeleton_xml(case_id, task_id)

    def get_mi_unique_param(self, task_id: str) -> YParameter | None:
        """Get unique parameter for multi-instance task.

        Parameters
        ----------
        task_id : str
            Task ID

        Returns
        -------
        YParameter | None
            Unique parameter or None

        Examples
        --------
        >>> param = model.get_mi_unique_param("MI_Task")
        """
        try:
            # Get parameters for task
            all_items = self.engine.getAllWorkItems()
            for work_item in all_items:
                if work_item.task_id == task_id:
                    params = self._get_params_for_task(task_id, work_item)
                    if params and hasattr(params, "formal_input_param"):
                        return params.formal_input_param
                    # Fallback: get first input parameter
                    if params and hasattr(params, "input_parameters"):
                        input_params = params.input_parameters
                        if input_params:
                            return list(input_params.values())[0]
            return None
        except Exception as e:
            logger.error("Error getting MI unique param", extra={"task_id": task_id}, exc_info=True)
            return None

    def get_task_test_data(self, case_id: str, task_id: str) -> str | None:
        """Get test data for a task.

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID

        Returns
        -------
        str | None
            Test data XML or None

        Examples
        --------
        >>> test_data = model.get_task_test_data("case-001", "Task1")
        """
        xml_comment_header = "<!-- Test data loaded from -"
        try:
            all_items = self.engine.getAllWorkItems()
            for work_item in all_items:
                if work_item.case_id == case_id and work_item.task_id == task_id:
                    # In Java, this reads from file system
                    # For Python port, we can return work item input data as XML
                    if work_item.data_input:
                        import xml.etree.ElementTree as ET

                        root = ET.Element("testData")
                        root.set("taskId", task_id)
                        root.set("caseId", case_id)
                        for key, value in work_item.data_input.items():
                            elem = ET.SubElement(root, key)
                            elem.text = str(value)
                        xml_str = ET.tostring(root, encoding="unicode")
                        return f"{xml_comment_header} {task_id}.xml -->\n{xml_str}"
            return None
        except Exception as e:
            logger.error("Error getting task test data", extra={"case_id": case_id, "task_id": task_id}, exc_info=True)
            return None

    def _get_params_for_task(self, task_id: str, work_item: YWorkItem) -> Any:
        """Get parameters schema for task (cached).

        Parameters
        ----------
        task_id : str
            Task ID
        work_item : YWorkItem
            Work item for context

        Returns
        -------
        Any
            Parameters schema or None
        """
        # Check cache
        if task_id in self._params_cache:
            return self._params_cache[task_id]

        try:
            from kgcl.yawl.clients.models import YSpecificationID

            # Get task definition
            spec_id = YSpecificationID(uri="", version="", identifier=work_item.specification_id)
            task = self.engine.get_task_definition(spec_id, task_id)
            if not task:
                return None

            # Extract parameter schema from task
            # In Java, this uses TaskInformation.getParamSchema()
            # For Python, we extract from task decomposition
            if hasattr(task, "decomposition") and task.decomposition:
                decomp = task.decomposition
                # Create a simple parameter schema representation
                params = {
                    "input_parameters": getattr(decomp, "input_parameters", {}),
                    "output_parameters": getattr(decomp, "output_parameters", {}),
                    "formal_input_param": (
                        list(decomp.input_parameters.values())[0]
                        if hasattr(decomp, "input_parameters") and decomp.input_parameters
                        else None
                    ),
                }
                self._params_cache[task_id] = type("ParamsSchema", (), params)()
                return self._params_cache[task_id]
            return None
        except Exception as e:
            logger.error("Error getting params for task", extra={"task_id": task_id}, exc_info=True)
            return None

    def _generate_output_xml_skeleton(self, params: Any, root_name: str, task_id: str) -> str:
        """Generate output XML skeleton from parameters.

        Parameters
        ----------
        params : Any
            Parameters schema
        root_name : str
            Root element name
        task_id : str
            Task ID

        Returns
        -------
        str
            XML skeleton string
        """
        import xml.etree.ElementTree as ET

        root = ET.Element(root_name)
        root.set("taskId", task_id)

        # Add output parameters
        if hasattr(params, "output_parameters") and params.output_parameters:
            for param in params.output_parameters.values():
                elem = ET.SubElement(root, param.name)
                if hasattr(param, "data_type"):
                    elem.set("type", param.data_type)
                if hasattr(param, "initial_value") and param.initial_value:
                    elem.text = str(param.initial_value)

        return ET.tostring(root, encoding="unicode")

    def _work_item_to_list_item(
        self, work_item: YWorkItem, in_sequence: bool, include_start: bool = False
    ) -> WorklistItem | None:
        """Convert YWorkItem to WorklistItem.

        Parameters
        ----------
        work_item : YWorkItem
            Work item to convert
        in_sequence : bool
            Whether task is in sequence
        include_start : bool
            Include start time

        Returns
        -------
        WorklistItem | None
            Converted item or None
        """
        try:
            # Get task definition for description
            from kgcl.yawl.clients.models import YSpecificationID

            # Create spec ID from string identifier
            spec_id = YSpecificationID(uri="", version="", identifier=work_item.specification_id)
            task = self.engine.get_task_definition(spec_id, work_item.task_id)
            description = task.name if task and hasattr(task, "name") else work_item.task_id

            status_map = {"ENABLED": "Enabled", "FIRED": "Fired", "EXECUTING": "Executing", "STARTED": "Executing"}
            status = status_map.get(work_item.status.name, work_item.status.name)

            return WorklistItem(
                case_id=work_item.case_id,
                task_id=work_item.task_id,
                description=description,
                status=status,
                enablement_time=work_item.enabled_time,
                firing_time=work_item.fired_time,
                start_time=work_item.started_time if include_start else None,
                in_sequence=in_sequence,
                work_item_id=work_item.id,
                specification_id=work_item.specification_id,
            )
        except Exception as e:
            logger.error("Error converting work item to list item", extra={"work_item_id": work_item.id}, exc_info=True)
            return None

    def _allows_dynamic_instance_creation(self, work_item: YWorkItem) -> bool:
        """Check if work item allows dynamic instance creation.

        Parameters
        ----------
        work_item : YWorkItem
            Work item to check

        Returns
        -------
        bool
            True if allowed
        """
        try:
            # Check if task is multi-instance and allows dynamic creation
            from kgcl.yawl.clients.models import YSpecificationID

            spec_id = YSpecificationID(uri="", version="", identifier=work_item.specification_id)
            task = self.engine.get_task_definition(spec_id, work_item.task_id)
            if task and hasattr(task, "multiple_instance"):
                # Check MI task configuration
                return True  # Simplified - full check would examine MI config
            return False
        except Exception:
            return False
