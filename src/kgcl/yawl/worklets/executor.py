"""Worklet executor for running exception handling workflows.

Executes worklets in response to case and work item exceptions,
coordinating with the main workflow engine.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from kgcl.yawl.worklets.models import Worklet, WorkletCase, WorkletStatus, WorkletType
from kgcl.yawl.worklets.repository import WorkletRepository
from kgcl.yawl.worklets.rules import RDREngine, RuleContext

if TYPE_CHECKING:
    pass


@dataclass
class WorkletResult:
    """Result of worklet execution.

    Parameters
    ----------
    success : bool
        Whether execution succeeded
    case_id : str
        Worklet case ID
    worklet_id : str | None
        Worklet ID that was executed
    output_data : dict[str, Any]
        Output data from worklet
    error : str | None
        Error message if failed
    """

    success: bool
    case_id: str
    worklet_id: str | None = None
    output_data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class WorkletExecutor:
    """Executor for worklet exception handling.

    Coordinates worklet selection, execution, and result handling.

    Parameters
    ----------
    repository : WorkletRepository
        Worklet storage
    rdr_engine : RDREngine
        Rule engine for worklet selection
    engine_callback : Callable[[str, dict[str, Any]], None] | None
        Callback to notify main engine
    """

    repository: WorkletRepository = field(default_factory=WorkletRepository)
    rdr_engine: RDREngine = field(default_factory=RDREngine)
    engine_callback: Callable[[str, dict[str, Any]], None] | None = None

    # --- Worklet selection ---

    def select_worklet(self, context: RuleContext, task_id: str | None = None) -> Worklet | None:
        """Select appropriate worklet for exception.

        Uses RDR engine to find matching worklet.

        Parameters
        ----------
        context : RuleContext
            Exception context
        task_id : str | None
            Task ID for item-level exceptions

        Returns
        -------
        Worklet | None
            Selected worklet or None
        """
        worklet_id = self.rdr_engine.find_worklet(context, task_id)
        if worklet_id:
            return self.repository.get_worklet(worklet_id)
        return None

    # --- Case exception handling ---

    def handle_case_exception(
        self, case_id: str, exception_type: str, exception_message: str = "", case_data: dict[str, Any] | None = None
    ) -> WorkletResult:
        """Handle a case-level exception.

        Parameters
        ----------
        case_id : str
            Parent case ID
        exception_type : str
            Type of exception
        exception_message : str
            Exception message
        case_data : dict[str, Any] | None
            Case data

        Returns
        -------
        WorkletResult
            Execution result
        """
        context = RuleContext(
            case_id=case_id,
            exception_type=exception_type,
            exception_message=exception_message,
            case_data=case_data or {},
        )

        worklet = self.select_worklet(context)
        if not worklet:
            return WorkletResult(success=False, case_id="", error=f"No worklet found for exception: {exception_type}")

        return self._execute_worklet(worklet, context, case_id, None)

    # --- Item exception handling ---

    def handle_item_exception(
        self,
        case_id: str,
        work_item_id: str,
        task_id: str,
        exception_type: str,
        exception_message: str = "",
        case_data: dict[str, Any] | None = None,
        work_item_data: dict[str, Any] | None = None,
    ) -> WorkletResult:
        """Handle a work item exception.

        Parameters
        ----------
        case_id : str
            Parent case ID
        work_item_id : str
            Work item ID
        task_id : str
            Task ID
        exception_type : str
            Type of exception
        exception_message : str
            Exception message
        case_data : dict[str, Any] | None
            Case data
        work_item_data : dict[str, Any] | None
            Work item data

        Returns
        -------
        WorkletResult
            Execution result
        """
        context = RuleContext(
            case_id=case_id,
            task_id=task_id,
            work_item_id=work_item_id,
            exception_type=exception_type,
            exception_message=exception_message,
            case_data=case_data or {},
            work_item_data=work_item_data or {},
        )

        worklet = self.select_worklet(context, task_id)
        if not worklet:
            return WorkletResult(
                success=False, case_id="", error=f"No worklet found for task {task_id} exception: {exception_type}"
            )

        return self._execute_worklet(worklet, context, case_id, work_item_id)

    # --- Worklet execution ---

    def _execute_worklet(
        self, worklet: Worklet, context: RuleContext, parent_case_id: str, parent_work_item_id: str | None
    ) -> WorkletResult:
        """Execute a worklet.

        Parameters
        ----------
        worklet : Worklet
            Worklet to execute
        context : RuleContext
            Exception context
        parent_case_id : str
            Parent case ID
        parent_work_item_id : str | None
            Parent work item ID

        Returns
        -------
        WorkletResult
            Execution result
        """
        # Create worklet case
        worklet_case = WorkletCase(
            id=str(uuid.uuid4()),
            worklet_id=worklet.id,
            parent_case_id=parent_case_id,
            parent_work_item_id=parent_work_item_id,
            exception_type=context.exception_type,
            exception_data={
                "message": context.exception_message,
                "case_data": context.case_data,
                "work_item_data": context.work_item_data,
            },
        )

        # Store case
        self.repository.add_case(worklet_case)

        # Start execution
        worklet_case.start()

        try:
            # Execute worklet logic
            result_data = self._run_worklet(worklet, context, worklet_case)

            # Mark completed
            worklet_case.complete(result_data)

            # Notify engine if callback set
            if self.engine_callback:
                self.engine_callback(
                    "WORKLET_COMPLETED",
                    {
                        "worklet_case_id": worklet_case.id,
                        "worklet_id": worklet.id,
                        "parent_case_id": parent_case_id,
                        "parent_work_item_id": parent_work_item_id,
                        "result_data": result_data,
                    },
                )

            return WorkletResult(success=True, case_id=worklet_case.id, worklet_id=worklet.id, output_data=result_data)

        except Exception as e:
            worklet_case.fail(str(e))
            return WorkletResult(success=False, case_id=worklet_case.id, worklet_id=worklet.id, error=str(e))

    def _run_worklet(self, worklet: Worklet, context: RuleContext, worklet_case: WorkletCase) -> dict[str, Any]:
        """Run worklet logic.

        Executes the worklet by extracting its action from parameters.
        Full workflow-based worklet execution requires a specification
        engine integration which is documented in CLAUDE.md as pending.

        Parameters
        ----------
        worklet : Worklet
            Worklet definition
        context : RuleContext
            Exception context
        worklet_case : WorkletCase
            Running case

        Returns
        -------
        dict[str, Any]
            Result data including:
            - worklet_id: The worklet identifier
            - worklet_name: Human-readable name
            - action: The action taken (from worklet parameters)
            - exception_handled: False (no real handling performed)

        Raises
        ------
        WorkletExecutionError
            If worklet specifies a specification_id (workflow execution not supported)
        """
        # Check if worklet expects full workflow execution
        if worklet.parameters.get("specification_id"):
            raise WorkletExecutionError(
                worklet_id=worklet.id,
                message="Workflow-based worklet execution not implemented. "
                "Worklet has specification_id but no engine integration exists.",
            )

        # Simple worklets: extract action and parameters (no workflow execution)
        action = worklet.parameters.get("action", "continue")
        return {
            "worklet_id": worklet.id,
            "worklet_name": worklet.name,
            "action": action,
            "exception_handled": False,  # Honest: no real exception handling performed
            "parameters_applied": worklet.parameters,
        }

    # --- Worklet management ---

    def register_worklet(self, worklet: Worklet) -> None:
        """Register a worklet.

        Parameters
        ----------
        worklet : Worklet
            Worklet to register
        """
        self.repository.add_worklet(worklet)

    def register_tree(self, task_id: str | None, exception_type: str) -> str:
        """Register an RDR tree.

        Parameters
        ----------
        task_id : str | None
            Task ID (None for case-level)
        exception_type : str
            Exception type

        Returns
        -------
        str
            Tree ID
        """
        from kgcl.yawl.worklets.models import RDRNode, RDRTree

        tree_id = str(uuid.uuid4())
        tree = RDRTree(
            id=tree_id,
            name=f"RDR_{task_id or 'case'}_{exception_type}",
            root=RDRNode(id="root"),
            task_id=task_id,
            exception_type=exception_type,
        )

        self.repository.add_tree(tree)
        self.rdr_engine.add_tree(tree)

        return tree_id

    def add_rule(
        self,
        tree_id: str,
        parent_node_id: str,
        is_true_branch: bool,
        condition: str,
        worklet_id: str | None,
        cornerstone_case: dict[str, Any] | None = None,
    ) -> str | None:
        """Add a rule to an RDR tree.

        Parameters
        ----------
        tree_id : str
            Tree ID
        parent_node_id : str
            Parent node ID
        is_true_branch : bool
            Add on true branch
        condition : str
            Condition expression
        worklet_id : str | None
            Worklet to execute
        cornerstone_case : dict[str, Any] | None
            Case that prompted this rule

        Returns
        -------
        str | None
            New node ID or None
        """
        node = self.rdr_engine.add_rule(
            tree_id=tree_id,
            parent_node_id=parent_node_id,
            is_true_branch=is_true_branch,
            condition=condition,
            conclusion=worklet_id,
            cornerstone_case=cornerstone_case,
        )

        return node.id if node else None

    # --- Query methods ---

    def get_active_worklets(self, parent_case_id: str) -> list[WorkletCase]:
        """Get active worklet cases for parent.

        Parameters
        ----------
        parent_case_id : str
            Parent case ID

        Returns
        -------
        list[WorkletCase]
            Active worklet cases
        """
        return self.repository.get_active_cases(parent_case_id)

    def get_worklet_status(self, worklet_case_id: str) -> WorkletStatus | None:
        """Get worklet case status.

        Parameters
        ----------
        worklet_case_id : str
            Worklet case ID

        Returns
        -------
        WorkletStatus | None
            Status or None
        """
        case = self.repository.get_case(worklet_case_id)
        return case.status if case else None

    def cancel_worklet(self, worklet_case_id: str) -> bool:
        """Cancel a running worklet.

        Parameters
        ----------
        worklet_case_id : str
            Worklet case ID

        Returns
        -------
        bool
            True if cancelled
        """
        case = self.repository.get_case(worklet_case_id)
        if case and case.status in (WorkletStatus.PENDING, WorkletStatus.RUNNING):
            case.cancel()
            return True
        return False
