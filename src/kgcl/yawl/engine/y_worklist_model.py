"""Worklist model for managing available and active work items (mirrors Java YWorklistModel).

This class provides the core worklist management logic without GUI dependencies.
It manages available work items (enabled/fired) and active tasks (started/executing).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_task import YTask
    from kgcl.yawl.engine.y_engine import YEngine
    from kgcl.yawl.engine.y_work_item import YWorkItem


@dataclass
class WorklistTableModel:
    """Table model for worklist data (mirrors Java YWorklistTableModel).

    Parameters
    ----------
    columns : list[str]
        Column names
    rows : dict[str, dict[str, Any]]
        Row data by key (caseID + taskID)
    """

    columns: list[str] = field(default_factory=list)
    rows: dict[str, dict[str, Any]] = field(default_factory=dict)

    def add_row(self, key: str, data: dict[str, Any]) -> None:
        """Add row to table.

        Parameters
        ----------
        key : str
            Row key (caseID + taskID)
        data : dict[str, Any]
            Row data
        """
        self.rows[key] = data

    def remove_row(self, key: str) -> None:
        """Remove row from table.

        Parameters
        ----------
        key : str
            Row key to remove
        """
        self.rows.pop(key, None)

    def get_row(self, key: str) -> dict[str, Any] | None:
        """Get row data.

        Parameters
        ----------
        key : str
            Row key

        Returns
        -------
        dict[str, Any] | None
            Row data or None
        """
        return self.rows.get(key)

    def clear(self) -> None:
        """Clear all rows."""
        self.rows.clear()


@dataclass
class YWorklistModel:
    """Worklist model for managing work items (mirrors Java YWorklistModel).

    Manages available work items (enabled/fired) and active tasks (started/executing)
    without GUI dependencies.

    Parameters
    ----------
    username : str
        Username for this worklist
    engine : YEngine | None
        Engine instance (optional, will get singleton if None)
    available_work : WorklistTableModel
        Model for available work items
    active_tasks : WorklistTableModel
        Model for active tasks
    in_sequence_workitem_ids : set[str]
        Task IDs that are in sequence
    formatter : str
        Date format string

    Examples
    --------
    >>> model = YWorklistModel("user1")
    >>> model.refresh_lists()
    >>> available = model.get_available_work()
    """

    username: str
    engine: Any | None = field(default=None, repr=False)
    available_work: WorklistTableModel = field(
        default_factory=lambda: WorklistTableModel(
            columns=["Case ID", "Task ID", "Description", "Status", "Enablement Time", "Firing Time", "Seq"]
        )
    )
    active_tasks: WorklistTableModel = field(
        default_factory=lambda: WorklistTableModel(
            columns=["Case ID", "Task ID", "Description", "Enablement Time", "Firing Time", "Start Time", "Seq"]
        )
    )
    in_sequence_workitem_ids: set[str] = field(default_factory=set)
    formatter: str = "%b %d %H:%M:%S"
    _params_definitions: Any = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize engine reference."""
        if self.engine is None:
            from kgcl.yawl.engine.y_engine import YEngine

            self.engine = YEngine.get_instance()

        if self._params_definitions is None:
            from kgcl.yawl.worklist.params_definitions import ParamsDefinitions

            self._params_definitions = ParamsDefinitions()

    def _format_time(self, time: datetime | None) -> str:
        """Format datetime to string.

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
        return time.strftime(self.formatter)

    def _remove_unstarted_work_item(self, case_id: str, task_id: str) -> None:
        """Remove unstarted work item from available work.

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID
        """
        key = case_id + task_id
        self.available_work.remove_row(key)

    def _add_enabled_work_item(self, work_item: YWorkItem, in_sequence: bool) -> None:
        """Add enabled work item to available work.

        Parameters
        ----------
        work_item : YWorkItem
            Work item to add
        in_sequence : bool
            Whether item is in sequence
        """
        from kgcl.yawl.engine.y_work_item import WorkItemStatus

        case_id_str = work_item.get_case_id()
        task_id = work_item.get_task_id()
        spec_id = work_item.get_specification_id()

        task = self._get_task_definition(spec_id, task_id)
        task_description = self._get_task_description(task)

        key = case_id_str + task_id
        self.available_work.add_row(
            key,
            {
                "Case ID": case_id_str,
                "Task ID": task_id,
                "Description": task_description,
                "Status": "Enabled",
                "Enablement Time": self._format_time(work_item.get_enablement_time()),
                "Firing Time": "",
                "Seq": "Y" if in_sequence else "N",
            },
        )

    def _add_fired_work_item(self, work_item: YWorkItem, in_sequence: bool) -> None:
        """Add fired work item to available work.

        Parameters
        ----------
        work_item : YWorkItem
            Work item to add
        in_sequence : bool
            Whether item is in sequence
        """
        case_id_str = work_item.get_case_id()
        task_id = work_item.get_task_id()
        spec_id = work_item.get_specification_id()

        task = self._get_task_definition(spec_id, task_id)
        task_description = self._get_task_description(task)

        key = case_id_str + task_id
        self.available_work.add_row(
            key,
            {
                "Case ID": case_id_str,
                "Task ID": task_id,
                "Description": task_description,
                "Status": "Fired",
                "Enablement Time": self._format_time(work_item.get_enablement_time()),
                "Firing Time": self._format_time(work_item.get_firing_time()),
                "Seq": "Y" if in_sequence else "N",
            },
        )

    def _remove_started_item(self, case_id: str, task_id: str) -> None:
        """Remove started item from active tasks.

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID
        """
        key = case_id + task_id
        self.active_tasks.remove_row(key)

    def _add_started_work_item(self, item: YWorkItem, in_sequence: bool) -> None:
        """Add started work item to active tasks.

        Parameters
        ----------
        item : YWorkItem
            Work item to add
        in_sequence : bool
            Whether item is in sequence
        """
        case_id_str = item.get_case_id()
        task_id = item.get_task_id()
        spec_id = item.get_specification_id()

        task = self._get_task_definition(spec_id, task_id)
        task_description = self._get_task_description(task)

        allows_dynamic = self._allows_dynamic_instance_creation(item)

        key = case_id_str + task_id
        self.active_tasks.add_row(
            key,
            {
                "Case ID": case_id_str,
                "Task ID": task_id,
                "Description": task_description,
                "Enablement Time": self._format_time(item.get_enablement_time()),
                "Firing Time": self._format_time(item.get_firing_time()),
                "Start Time": self._format_time(item.get_start_time()),
                "Seq": "Y" if in_sequence else "N",
                "AllowsDynamicCreation": allows_dynamic,
                "DataString": item.get_data_string(),
                "OutputSkeletonXML": self._get_output_skeleton_xml(case_id_str, task_id),
            },
        )

    def _get_task_definition(self, spec_id: str, task_id: str) -> Any | None:
        """Get task definition from engine.

        Parameters
        ----------
        spec_id : str
            Specification ID
        task_id : str
            Task ID

        Returns
        -------
        Any | None
            Task object or None
        """
        if self.engine and hasattr(self.engine, "get_task_definition"):
            return self.engine.get_task_definition(spec_id, task_id)
        return None

    def _get_task_description(self, task: Any | None) -> str:
        """Get task description.

        Parameters
        ----------
        task : Any | None
            Task object

        Returns
        -------
        str
            Task description or task ID
        """
        if task is None:
            return ""
        if hasattr(task, "get_decomposition_prototype"):
            decomp = task.get_decomposition_prototype()
            if decomp and hasattr(decomp, "id"):
                task_id = getattr(decomp, "id", None)
                if task_id is not None:
                    return str(task_id)
        if hasattr(task, "id"):
            task_id = getattr(task, "id", None)
            if task_id is not None:
                return str(task_id)
        return ""

    def _allows_dynamic_instance_creation(self, item: YWorkItem) -> bool:
        """Check if work item allows dynamic instance creation.

        Parameters
        ----------
        item : YWorkItem
            Work item

        Returns
        -------
        bool
            True if dynamic creation allowed
        """
        if self.engine and hasattr(self.engine, "check_eligibility_to_add_instances"):
            try:
                self.engine.check_eligibility_to_add_instances(item.get_unique_id())
                return True
            except Exception:
                return False
        return item.get_allows_dynamic_creation()

    def _get_output_skeleton_xml(self, case_id: str, task_id: str) -> str:
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

        Notes
        -----
        Generates XML skeleton from task output parameters.
        Uses ParamsDefinitions cache and Marshaller.getOutputParamsInXML()
        """
        from kgcl.yawl.clients.marshaller import Marshaller

        params = self._params_definitions.get_params_for_task(task_id)
        if not self.engine:
            return f'<output><task id="{task_id}"/></output>'

        work_item = None
        if hasattr(self.engine, "get_work_item"):
            work_item = self.engine.get_work_item(f"{case_id}:{task_id}")

        if not work_item:
            return f'<output><task id="{task_id}"/></output>'

        spec_id = work_item.get_specification_id()
        task = self._get_task_definition(spec_id, task_id)
        if not task:
            return f'<output><task id="{task_id}"/></output>'

        root_name = "output"
        if hasattr(task, "get_decomposition_prototype"):
            decomp = task.get_decomposition_prototype()
            if decomp and hasattr(decomp, "get_root_data_element_name"):
                root_name = decomp.get_root_data_element_name()

        return Marshaller.get_output_params_in_xml(params, root_name)

    def get_active_table_data(self, case_id: str, task_id: str) -> dict[str, Any] | None:
        """Get active table data for work item.

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID

        Returns
        -------
        dict[str, Any] | None
            Table data or None

        Notes
        -----
        Java signature: Object[] getActiveTableData(String caseIDStr, String taskIDStr)
        """
        key = case_id + task_id
        return self.active_tasks.get_row(key)

    def set_active_table_data(self, data: dict[str, Any]) -> None:
        """Set active table data.

        Parameters
        ----------
        data : dict[str, Any]
            Table data (must contain "Case ID" and "Task ID")

        Notes
        -----
        Java signature: void setActiveTableData(Object[] data)
        """
        case_id = str(data.get("Case ID", ""))
        task_id = str(data.get("Task ID", ""))
        key = case_id + task_id
        self.active_tasks.add_row(key, data)

    def apply_for_work_item(self, case_id: str, task_id: str) -> None:
        """Apply for (start) a work item.

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID

        Raises
        ------
        Exception
            If work item cannot be started

        Notes
        -----
        Java signature: void applyForWorkItem(String caseID, String taskID) throws YPersistenceException
        """
        if self.engine and hasattr(self.engine, "get_available_work_items"):
            work_items = self.engine.get_available_work_items()
            for item in work_items:
                if item.get_case_id() == case_id and item.get_task_id() == task_id:
                    if hasattr(self.engine, "start_work_item"):
                        self.engine.start_work_item(item, None)
                    return

    def create_new_instance(self, case_id: str, task_id: str, new_instance_data: str) -> None:
        """Create new multi-instance.

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID
        new_instance_data : str
            New instance data XML

        Notes
        -----
        Java signature: void createNewInstance(String caseID, String taskID, String newInstanceData) throws YPersistenceException
        """
        if self.engine and hasattr(self.engine, "get_all_work_items"):
            work_items = self.engine.get_all_work_items()
            for item in work_items:
                if item.get_case_id() == case_id and item.get_task_id() == task_id:
                    if hasattr(self.engine, "create_new_instance"):
                        self.engine.create_new_instance(item, new_instance_data)
                    return

    def allows_dynamic_instance_creation(self, case_id: str, task_id: str) -> bool:
        """Check if work item allows dynamic instance creation.

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID

        Returns
        -------
        bool
            True if dynamic creation allowed

        Notes
        -----
        Java signature: boolean allowsDynamicInstanceCreation(String caseID, String taskID)
        """
        if self.engine and hasattr(self.engine, "get_all_work_items"):
            work_items = self.engine.get_all_work_items()
            for item in work_items:
                if item.get_case_id() == case_id and item.get_task_id() == task_id:
                    return self._allows_dynamic_instance_creation(item)
        return False

    def attempt_to_finish_active_job(self, case_id: str, task_id: str) -> None:
        """Attempt to finish (complete) active job.

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID

        Raises
        ------
        Exception
            If completion fails

        Notes
        -----
        Java signature: void attemptToFinishActiveJob(String caseID, String taskID)
        """
        if self.engine and hasattr(self.engine, "get_all_work_items"):
            work_items = self.engine.get_all_work_items()
            for item in work_items:
                if item.get_case_id() == case_id and item.get_task_id() == task_id:
                    output_data = self._get_output_data(case_id, task_id)
                    if hasattr(self.engine, "complete_work_item"):
                        from kgcl.yawl.engine.y_work_item import WorkItemStatus

                        self.engine.complete_work_item(item, output_data, None, WorkItemStatus.COMPLETED)
                    return

    def _get_output_data(self, case_id: str, task_id: str) -> str:
        """Get output data for work item.

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID

        Returns
        -------
        str
            Output data XML
        """
        row_data = self.get_active_table_data(case_id, task_id)
        if row_data and "OutputSkeletonXML" in row_data:
            return str(row_data["OutputSkeletonXML"])
        return ""

    def rollback_active_task(self, case_id: str, task_id: str) -> None:
        """Rollback active task.

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID

        Notes
        -----
        Java signature: void rollBackActiveTask(String caseID, String taskID) throws YPersistenceException, YLogException
        """
        if self.engine and hasattr(self.engine, "get_all_work_items"):
            work_items = self.engine.get_all_work_items()
            for item in work_items:
                if item.get_case_id() == case_id and item.get_task_id() == task_id:
                    if hasattr(self.engine, "rollback_work_item"):
                        self.engine.rollback_work_item(item.get_unique_id())
                    return

    def refresh_lists(self, username: str | None = None) -> None:
        """Refresh worklist lists.

        Parameters
        ----------
        username : str | None
            Username (optional, uses instance username if None)

        Notes
        -----
        Java signature: void refreshLists(String userName)
        """
        # Clear models
        self.available_work.clear()
        self.active_tasks.clear()

        # Update from engine
        self._update_self()

    def _update_self(self) -> None:
        """Update worklist from engine state.

        Notes
        -----
        Java signature: private void updateSelf()
        """
        from kgcl.yawl.clients.marshaller import Marshaller
        from kgcl.yawl.engine.y_work_item import WorkItemStatus

        if not self.engine:
            return

        # Get available work items
        if hasattr(self.engine, "get_available_work_items"):
            available_items = self.engine.get_available_work_items()
            for item in available_items:
                in_sequence = item.get_task_id() in self.in_sequence_workitem_ids
                status = item.get_status()

                if status == WorkItemStatus.ENABLED:
                    self._add_enabled_work_item(item, in_sequence)
                elif status == WorkItemStatus.FIRED:
                    self._add_fired_work_item(item, in_sequence)

        # Get all work items for active tasks and cache parameter schemas
        if hasattr(self.engine, "get_all_work_items"):
            all_items = self.engine.get_all_work_items()
            for item in all_items:
                in_sequence = item.get_task_id() in self.in_sequence_workitem_ids
                status = item.get_status()

                if status == WorkItemStatus.EXECUTING:
                    self._add_started_work_item(item, in_sequence)

                task_id = item.get_task_id()
                self._load_parameter_definitions(item)

    def get_available_model(self) -> WorklistTableModel:
        """Get available work model.

        Returns
        -------
        WorklistTableModel
            Available work model

        Notes
        -----
        Java signature: YWorklistTableModel getAvaliableModel()
        """
        return self.available_work

    def get_active_tasks_model(self) -> WorklistTableModel:
        """Get active tasks model.

        Returns
        -------
        WorklistTableModel
            Active tasks model

        Notes
        -----
        Java signature: YWorklistTableModel getActiveTasksModel()
        """
        return self.active_tasks

    def get_output_skeleton_xml(self, case_id: str, task_id: str) -> str:
        """Get output skeleton XML.

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

        Notes
        -----
        Java signature: String getOutputSkeletonXML(String caseID, String taskID)
        """
        return self._get_output_skeleton_xml(case_id, task_id)

    def get_task_test_data(self, case_id: str, task_id: str) -> str | None:
        """Get task test data from file.

        Java signature: String getTaskTestData(String caseID, String taskID)

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID

        Returns
        -------
        str | None
            Test data XML or None if not found

        Notes
        -----
        Mirrors Java YAWL YWorklistModel.getTaskTestData()
        Loads test data from spec test data directory
        """
        xml_comment_header = "<!-- Test data loaded from -"

        if not self.engine:
            return None

        all_items = []
        if hasattr(self.engine, "get_all_work_items"):
            all_items = self.engine.get_all_work_items()

        for item in all_items:
            if item.get_case_id() == case_id and item.get_task_id() == task_id:
                try:
                    spec_id = item.get_specification_id()
                    spec_key = spec_id.get_key() if hasattr(spec_id, "get_key") else str(spec_id)

                    test_data_dir = Path.home() / ".yawl" / "testdata" / spec_key
                    task_input_data_file = test_data_dir / f"{task_id}.xml"

                    if task_input_data_file.exists():
                        test_data = task_input_data_file.read_text(encoding="utf-8")
                        if test_data.startswith(xml_comment_header):
                            return test_data
                        else:
                            return f"{xml_comment_header} {task_input_data_file.name} -->\n{test_data}"
                except Exception:
                    pass

        return None

    def get_mi_unique_param(self, task_id: str) -> Any | None:
        """Get MI unique parameter for task.

        Java signature: YParameter getMIUniqueParam(String taskID)

        Parameters
        ----------
        task_id : str
            Task ID

        Returns
        -------
        Any | None
            MI formal input parameter or None

        Notes
        -----
        Mirrors Java YAWL YWorklistModel.getMIUniqueParam()
        Returns the formal input parameter for multi-instance tasks
        """
        params = self._params_definitions.get_params_for_task(task_id)
        if params is None:
            return None

        if hasattr(params, "get_formal_input_param"):
            return params.get_formal_input_param()
        elif hasattr(params, "formal_input_param"):
            return params.formal_input_param

        return None

    def validate_data(self) -> list[str]:
        """Validate worklist data.

        Returns
        -------
        list[str]
            Validation messages

        Notes
        -----
        Java signature: List validateData()
        """
        return []

    def get_task_test_data(self, case_id: str, task_id: str) -> str | None:
        """Get XML test data for a specified task.

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID

        Returns
        -------
        str | None
            Test data XML or None if not found

        Notes
        -----
        Java signature: String getTaskTestData(String caseID, String taskID)
        Returns test data with XML comment header if loaded from file.
        Test data directory mechanism would be provided by admin/configuration layer.
        """
        xml_comment_header = "<!-- Test data loaded from -"

        if not self.engine or not hasattr(self.engine, "get_all_work_items"):
            return None

        work_items = self.engine.get_all_work_items()
        for item in work_items:
            if item.get_case_id() == case_id and item.get_task_id() == task_id:
                spec_id = item.get_specification_id()
                # Test data directory access would be provided by admin layer
                # This method returns None when test data is not available
                # Full implementation requires test data directory configuration
                return None

        return None

    def get_mi_unique_param(self, task_id: str) -> Any | None:
        """Get MI unique parameter for task.

        Parameters
        ----------
        task_id : str
            Task ID

        Returns
        -------
        Any | None
            Parameter or None if not found

        Notes
        -----
        Java signature: YParameter getMIUniqueParam(String taskID)
        Returns the formal input parameter for multi-instance tasks.
        Parameter definitions are loaded during worklist refresh.
        """
        # Parameter definitions would be stored in _params_definitions cache
        # This method returns None when parameters are not cached
        # Full implementation requires parameter definitions storage mechanism
        return None

    def _load_parameter_definitions(self, item: YWorkItem) -> None:
        """Load parameter definitions for work item task.

        Parameters
        ----------
        item : YWorkItem
            Work item

        Notes
        -----
        Mirrors Java YWorklistModel.updateSelf() parameter loading logic.
        Loads task parameters if not already cached.
        Parameter definitions are extracted from task information.
        """
        from kgcl.yawl.clients.marshaller import Marshaller

        task_id = item.get_task_id()
        if self._params_definitions.get_params_for_task(task_id) is not None:
            return

        try:
            spec_id = item.get_specification_id()
            task = self._get_task_definition(spec_id, task_id)
            if task and hasattr(task, "get_information"):
                task_info_xml = task.get_information()
                task_info = Marshaller.unmarshal_task_information(task_info_xml)
                if task_info and hasattr(task_info, "get_param_schema"):
                    param_schema = task_info.get_param_schema()
                    if param_schema:
                        self._params_definitions.set_params_for_task(task_id, param_schema)
        except Exception:
            pass
