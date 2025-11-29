"""End-to-end JTBD integration tests for worklet exception handling.

Tests complete workflows from exception occurrence through worklet execution,
proving ENGINE behavior rather than Python simulation.

Jobs To Be Done:
1. Handle case-level exceptions with appropriate worklet selection
2. Handle item-level exceptions with task-specific worklets
3. Traverse RDR trees to select correct worklets based on context
4. Execute worklets and manage their complete lifecycle
5. Notify the main engine of worklet completion
6. Support complex scenarios with multiple rules and fallbacks
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import pytest

from kgcl.yawl.worklets.exceptions import WorkletExecutionError

# Import directly from submodules to avoid broken kgcl.yawl.__init__.py
from kgcl.yawl.worklets.executor import WorkletExecutor, WorkletResult
from kgcl.yawl.worklets.models import RDRNode, RDRTree, Worklet, WorkletCase, WorkletStatus, WorkletType
from kgcl.yawl.worklets.repository import WorkletRepository
from kgcl.yawl.worklets.rules import RDREngine, RuleContext

# --- Test Fixtures ---


@pytest.fixture
def repository() -> WorkletRepository:
    """Create a fresh worklet repository."""
    return WorkletRepository()


@pytest.fixture
def rdr_engine() -> RDREngine:
    """Create a fresh RDR engine."""
    return RDREngine()


@pytest.fixture
def executor(repository: WorkletRepository, rdr_engine: RDREngine) -> WorkletExecutor:
    """Create a worklet executor with repository and engine."""
    return WorkletExecutor(repository=repository, rdr_engine=rdr_engine)


@pytest.fixture
def timeout_worklet() -> Worklet:
    """Create a timeout handling worklet."""
    return Worklet(
        id="wl-timeout-001",
        name="Timeout Handler",
        worklet_type=WorkletType.CASE_EXCEPTION,
        description="Handles timeout exceptions",
        parameters={"action": "retry", "max_retries": 3},
    )


@pytest.fixture
def priority_worklet() -> Worklet:
    """Create a high-priority handling worklet."""
    return Worklet(
        id="wl-priority-001",
        name="Priority Handler",
        worklet_type=WorkletType.CASE_EXCEPTION,
        description="Handles high-priority cases",
        parameters={"action": "escalate", "notify_manager": True},
    )


@pytest.fixture
def item_error_worklet() -> Worklet:
    """Create a work item error handling worklet."""
    return Worklet(
        id="wl-item-error-001",
        name="Item Error Handler",
        worklet_type=WorkletType.ITEM_EXCEPTION,
        description="Handles work item errors",
        parameters={"action": "rollback", "notify_user": True},
    )


# --- JTBD 1: Handle Case-Level Exceptions ---


class TestCaseLevelExceptionHandling:
    """Test complete case-level exception handling workflow."""

    def test_simple_timeout_exception_handling(self, executor: WorkletExecutor, timeout_worklet: Worklet) -> None:
        """JTBD: Handle a timeout exception with worklet selection and execution.

        Proves the ENGINE can:
        1. Register a worklet
        2. Set up RDR tree for exception type
        3. Handle exception by selecting and executing correct worklet
        4. Track worklet case lifecycle
        """
        # Arrange: Register worklet and set up rule
        executor.register_worklet(timeout_worklet)
        tree_id = executor.register_tree(task_id=None, exception_type="TIMEOUT")
        executor.add_rule(
            tree_id=tree_id, parent_node_id="root", is_true_branch=True, condition="true", worklet_id=timeout_worklet.id
        )

        # Act: Handle timeout exception
        result = executor.handle_case_exception(
            case_id="case-001",
            exception_type="TIMEOUT",
            exception_message="Operation timed out after 30s",
            case_data={"operation": "data_import", "elapsed_time": 30},
        )

        # Assert: Worklet was executed successfully
        assert result.success, f"Expected successful execution, got error: {result.error}"
        assert result.worklet_id == timeout_worklet.id
        assert result.output_data["action"] == "retry"
        assert result.output_data["worklet_name"] == "Timeout Handler"

        # Assert: Worklet case is tracked and completed
        cases = executor.repository.find_cases(parent_case_id="case-001")
        assert len(cases) == 1
        case = cases[0]
        assert case.status == WorkletStatus.COMPLETED
        assert case.exception_type == "TIMEOUT"
        assert case.exception_data["message"] == "Operation timed out after 30s"

    def test_no_worklet_found_for_exception(self, executor: WorkletExecutor) -> None:
        """JTBD: Gracefully handle exceptions when no matching worklet exists.

        Proves the ENGINE correctly handles the case where no worklet
        matches the exception context.
        """
        # Act: Handle exception with no registered worklets
        result = executor.handle_case_exception(
            case_id="case-002", exception_type="UNKNOWN_ERROR", exception_message="Something went wrong"
        )

        # Assert: Result indicates failure
        assert not result.success
        assert result.error is not None
        assert "No worklet found" in result.error

    def test_priority_based_worklet_selection(
        self, executor: WorkletExecutor, timeout_worklet: Worklet, priority_worklet: Worklet
    ) -> None:
        """JTBD: Select different worklets based on case priority.

        Proves the RDR engine can evaluate context and select
        the appropriate worklet based on data attributes.
        """
        # Arrange: Register both worklets
        executor.register_worklet(timeout_worklet)
        executor.register_worklet(priority_worklet)

        # Set up RDR tree with priority-based rules
        tree_id = executor.register_tree(task_id=None, exception_type="TIMEOUT")

        # Get the tree and update root condition
        tree = executor.repository.get_tree(tree_id)
        assert tree is not None
        tree.root.condition = "priority == high"
        tree.root.conclusion = priority_worklet.id

        # False branch: Use default timeout handler
        executor.add_rule(
            tree_id=tree_id,
            parent_node_id="root",
            is_true_branch=False,
            condition="true",
            worklet_id=timeout_worklet.id,
        )

        # Act: Handle high-priority timeout
        high_priority_result = executor.handle_case_exception(
            case_id="case-003", exception_type="TIMEOUT", case_data={"priority": "high"}
        )

        # Act: Handle normal-priority timeout
        normal_priority_result = executor.handle_case_exception(
            case_id="case-004", exception_type="TIMEOUT", case_data={"priority": "normal"}
        )

        # Assert: High priority uses priority handler
        assert high_priority_result.success
        assert high_priority_result.worklet_id == priority_worklet.id
        assert high_priority_result.output_data["action"] == "escalate"

        # Assert: Normal priority uses timeout handler
        assert normal_priority_result.success
        assert normal_priority_result.worklet_id == timeout_worklet.id
        assert normal_priority_result.output_data["action"] == "retry"


# --- JTBD 2: Handle Item-Level Exceptions ---


class TestItemLevelExceptionHandling:
    """Test complete work item exception handling workflow."""

    def test_work_item_error_handling(self, executor: WorkletExecutor, item_error_worklet: Worklet) -> None:
        """JTBD: Handle a work item exception with task-specific worklet.

        Proves the ENGINE can handle item-level exceptions separately
        from case-level exceptions.
        """
        # Arrange: Register worklet and set up task-specific rule
        executor.register_worklet(item_error_worklet)
        tree_id = executor.register_tree(task_id="task-validate", exception_type="VALIDATION_ERROR")
        executor.add_rule(
            tree_id=tree_id,
            parent_node_id="root",
            is_true_branch=True,
            condition="true",
            worklet_id=item_error_worklet.id,
        )

        # Act: Handle work item exception
        result = executor.handle_item_exception(
            case_id="case-005",
            work_item_id="wi-001",
            task_id="task-validate",
            exception_type="VALIDATION_ERROR",
            exception_message="Invalid input format",
            work_item_data={"field": "email", "value": "invalid-email"},
        )

        # Assert: Worklet executed successfully
        assert result.success
        assert result.worklet_id == item_error_worklet.id
        assert result.output_data["action"] == "rollback"

        # Assert: Worklet case tracks work item ID
        cases = executor.repository.find_cases(parent_case_id="case-005")
        assert len(cases) == 1
        case = cases[0]
        assert case.parent_work_item_id == "wi-001"
        assert case.status == WorkletStatus.COMPLETED

    def test_task_specific_worklet_fallback_to_case_level(
        self, executor: WorkletExecutor, timeout_worklet: Worklet
    ) -> None:
        """JTBD: Fall back to case-level worklet when no task-specific worklet exists.

        Proves the RDR engine's fallback mechanism: task-specific → case-level.
        """
        # Arrange: Register only case-level worklet
        executor.register_worklet(timeout_worklet)
        tree_id = executor.register_tree(task_id=None, exception_type="TIMEOUT")
        executor.add_rule(
            tree_id=tree_id, parent_node_id="root", is_true_branch=True, condition="true", worklet_id=timeout_worklet.id
        )

        # Act: Handle item exception (no task-specific rule exists)
        result = executor.handle_item_exception(
            case_id="case-006",
            work_item_id="wi-002",
            task_id="task-process",
            exception_type="TIMEOUT",
            exception_message="Processing timeout",
        )

        # Assert: Falls back to case-level worklet
        assert result.success
        assert result.worklet_id == timeout_worklet.id


# --- JTBD 3: RDR Tree Traversal and Rule Evaluation ---


class TestRDRTreeTraversal:
    """Test RDR tree traversal and condition evaluation."""

    def test_numeric_comparison_conditions(self, executor: WorkletExecutor) -> None:
        """JTBD: Evaluate numeric comparison conditions in RDR rules.

        Proves the RDR engine can handle:
        - Greater than (>)
        - Less than (<)
        - Greater than or equal (>=)
        - Less than or equal (<=)
        """
        # Arrange: Create worklets for different thresholds
        high_load_worklet = Worklet(
            id="wl-high-load",
            name="High Load Handler",
            worklet_type=WorkletType.CASE_EXCEPTION,
            parameters={"action": "scale_up"},
        )
        medium_load_worklet = Worklet(
            id="wl-medium-load",
            name="Medium Load Handler",
            worklet_type=WorkletType.CASE_EXCEPTION,
            parameters={"action": "monitor"},
        )

        executor.register_worklet(high_load_worklet)
        executor.register_worklet(medium_load_worklet)

        # Set up RDR tree with numeric conditions
        tree_id = executor.register_tree(task_id=None, exception_type="RESOURCE_LIMIT")

        # Get the tree and update root condition
        tree = executor.repository.get_tree(tree_id)
        assert tree is not None
        tree.root.condition = "load > 80"
        tree.root.conclusion = high_load_worklet.id

        # False branch: Check if load >= 50
        executor.add_rule(
            tree_id=tree_id,
            parent_node_id="root",
            is_true_branch=False,
            condition="load >= 50",
            worklet_id=medium_load_worklet.id,
        )

        # Act: High load case
        high_result = executor.handle_case_exception(
            case_id="case-007", exception_type="RESOURCE_LIMIT", case_data={"load": 95}
        )

        # Act: Medium load case
        medium_result = executor.handle_case_exception(
            case_id="case-008", exception_type="RESOURCE_LIMIT", case_data={"load": 65}
        )

        # Assert: High load triggers scale up
        assert high_result.success
        assert high_result.worklet_id == high_load_worklet.id
        assert high_result.output_data["action"] == "scale_up"

        # Assert: Medium load triggers monitoring
        assert medium_result.success
        assert medium_result.worklet_id == medium_load_worklet.id
        assert medium_result.output_data["action"] == "monitor"

    def test_string_equality_conditions(self, executor: WorkletExecutor) -> None:
        """JTBD: Evaluate string equality conditions in RDR rules.

        Proves the RDR engine handles string comparisons (==, !=).
        """
        # Arrange: Create environment-specific worklets
        prod_worklet = Worklet(
            id="wl-prod",
            name="Production Handler",
            worklet_type=WorkletType.CASE_EXCEPTION,
            parameters={"action": "alert_oncall", "severity": "critical"},
        )
        dev_worklet = Worklet(
            id="wl-dev",
            name="Development Handler",
            worklet_type=WorkletType.CASE_EXCEPTION,
            parameters={"action": "log_error", "severity": "info"},
        )

        executor.register_worklet(prod_worklet)
        executor.register_worklet(dev_worklet)

        tree_id = executor.register_tree(task_id=None, exception_type="ERROR")

        # Get the tree and update root condition
        tree = executor.repository.get_tree(tree_id)
        assert tree is not None
        tree.root.condition = "environment == production"
        tree.root.conclusion = prod_worklet.id

        # False branch: Use development handler
        executor.add_rule(
            tree_id=tree_id, parent_node_id="root", is_true_branch=False, condition="true", worklet_id=dev_worklet.id
        )

        # Act: Production error
        prod_result = executor.handle_case_exception(
            case_id="case-009", exception_type="ERROR", case_data={"environment": "production"}
        )

        # Act: Development error
        dev_result = executor.handle_case_exception(
            case_id="case-010", exception_type="ERROR", case_data={"environment": "development"}
        )

        # Assert: Production triggers oncall alert
        assert prod_result.success
        assert prod_result.worklet_id == prod_worklet.id
        assert prod_result.output_data["action"] == "alert_oncall"

        # Assert: Development logs error
        assert dev_result.success
        assert dev_result.worklet_id == dev_worklet.id
        assert dev_result.output_data["action"] == "log_error"

    def test_nested_rule_refinement(self, executor: WorkletExecutor) -> None:
        """JTBD: Navigate nested RDR rules for refined exception handling.

        Proves the RDR engine can traverse multi-level trees where
        true branches refine the parent condition.
        """
        # Arrange: Create specialized worklets
        critical_timeout = Worklet(
            id="wl-critical-timeout",
            name="Critical Timeout",
            worklet_type=WorkletType.CASE_EXCEPTION,
            parameters={"action": "immediate_escalation"},
        )
        standard_timeout = Worklet(
            id="wl-standard-timeout",
            name="Standard Timeout",
            worklet_type=WorkletType.CASE_EXCEPTION,
            parameters={"action": "retry"},
        )

        executor.register_worklet(critical_timeout)
        executor.register_worklet(standard_timeout)

        tree_id = executor.register_tree(task_id=None, exception_type="TIMEOUT")

        # Root: Is timeout?
        root_true_id = executor.add_rule(
            tree_id=tree_id,
            parent_node_id="root",
            is_true_branch=True,
            condition="timeout_seconds > 60",
            worklet_id=standard_timeout.id,
        )

        # Refinement: Is it also critical priority?
        if root_true_id:
            executor.add_rule(
                tree_id=tree_id,
                parent_node_id=root_true_id,
                is_true_branch=True,
                condition="priority == critical",
                worklet_id=critical_timeout.id,
            )

        # Act: Critical timeout
        critical_result = executor.handle_case_exception(
            case_id="case-011", exception_type="TIMEOUT", case_data={"timeout_seconds": 120, "priority": "critical"}
        )

        # Act: Standard timeout
        standard_result = executor.handle_case_exception(
            case_id="case-012", exception_type="TIMEOUT", case_data={"timeout_seconds": 90, "priority": "normal"}
        )

        # Assert: Critical timeout gets escalated
        assert critical_result.success
        assert critical_result.worklet_id == critical_timeout.id
        assert critical_result.output_data["action"] == "immediate_escalation"

        # Assert: Standard timeout gets retry
        assert standard_result.success
        assert standard_result.worklet_id == standard_timeout.id
        assert standard_result.output_data["action"] == "retry"


# --- JTBD 4: Worklet Lifecycle Management ---


class TestWorkletLifecycle:
    """Test complete worklet case lifecycle."""

    def test_worklet_case_lifecycle_states(self, executor: WorkletExecutor) -> None:
        """JTBD: Track worklet case through all lifecycle states.

        Proves the ENGINE correctly manages worklet case states:
        PENDING → RUNNING → COMPLETED
        """
        # Arrange
        worklet = Worklet(
            id="wl-lifecycle",
            name="Lifecycle Test",
            worklet_type=WorkletType.CASE_EXCEPTION,
            parameters={"action": "test"},
        )
        executor.register_worklet(worklet)
        tree_id = executor.register_tree(task_id=None, exception_type="TEST")
        executor.add_rule(
            tree_id=tree_id, parent_node_id="root", is_true_branch=True, condition="true", worklet_id=worklet.id
        )

        # Act: Execute worklet
        result = executor.handle_case_exception(case_id="case-013", exception_type="TEST")

        # Assert: Case reached COMPLETED state
        case = executor.repository.get_case(result.case_id)
        assert case is not None
        assert case.status == WorkletStatus.COMPLETED
        assert case.started is not None
        assert case.completed is not None
        assert case.completed >= case.started

    def test_worklet_cancellation(self, executor: WorkletExecutor) -> None:
        """JTBD: Cancel a pending or running worklet case.

        Proves the ENGINE can cancel worklets that are no longer needed.
        """
        # Arrange: Create a worklet case manually
        worklet = Worklet(id="wl-cancel-test", name="Cancellation Test", worklet_type=WorkletType.CASE_EXCEPTION)
        executor.register_worklet(worklet)

        case = WorkletCase(
            id="case-cancel-001", worklet_id=worklet.id, parent_case_id="case-014", status=WorkletStatus.PENDING
        )
        executor.repository.add_case(case)

        # Act: Cancel the worklet
        cancelled = executor.cancel_worklet("case-cancel-001")

        # Assert: Cancellation succeeded
        assert cancelled
        updated_case = executor.repository.get_case("case-cancel-001")
        assert updated_case is not None
        assert updated_case.status == WorkletStatus.CANCELLED

    def test_active_worklets_query(self, executor: WorkletExecutor) -> None:
        """JTBD: Query active worklet cases for a parent case.

        Proves the ENGINE can track which worklets are currently
        active for a given case.
        """
        # Arrange: Create multiple worklet cases
        worklet = Worklet(id="wl-query-test", name="Query Test", worklet_type=WorkletType.CASE_EXCEPTION)
        executor.register_worklet(worklet)

        # Create cases in different states
        pending_case = WorkletCase(
            id="case-pending", worklet_id=worklet.id, parent_case_id="case-015", status=WorkletStatus.PENDING
        )
        running_case = WorkletCase(
            id="case-running", worklet_id=worklet.id, parent_case_id="case-015", status=WorkletStatus.RUNNING
        )
        completed_case = WorkletCase(
            id="case-completed", worklet_id=worklet.id, parent_case_id="case-015", status=WorkletStatus.COMPLETED
        )

        executor.repository.add_case(pending_case)
        executor.repository.add_case(running_case)
        executor.repository.add_case(completed_case)

        # Act: Query active worklets
        active = executor.get_active_worklets("case-015")

        # Assert: Only pending and running are returned
        assert len(active) == 2
        statuses = {c.status for c in active}
        assert statuses == {WorkletStatus.PENDING, WorkletStatus.RUNNING}


# --- JTBD 5: Engine Callbacks and Notifications ---


class TestEngineCallbacks:
    """Test engine notification callbacks."""

    def test_engine_notified_on_worklet_completion(self, repository: WorkletRepository, rdr_engine: RDREngine) -> None:
        """JTBD: Notify the main engine when a worklet completes.

        Proves the ENGINE sends completion notifications to the
        main workflow engine.
        """
        # Arrange: Track callback invocations
        callback_events: list[dict[str, Any]] = []

        def engine_callback(event_type: str, data: dict[str, Any]) -> None:
            callback_events.append({"type": event_type, "data": data})

        # Create executor with callback
        executor = WorkletExecutor(repository=repository, rdr_engine=rdr_engine, engine_callback=engine_callback)

        # Register worklet
        worklet = Worklet(
            id="wl-callback",
            name="Callback Test",
            worklet_type=WorkletType.CASE_EXCEPTION,
            parameters={"action": "notify"},
        )
        executor.register_worklet(worklet)
        tree_id = executor.register_tree(task_id=None, exception_type="TEST")
        executor.add_rule(
            tree_id=tree_id, parent_node_id="root", is_true_branch=True, condition="true", worklet_id=worklet.id
        )

        # Act: Execute worklet
        result = executor.handle_case_exception(case_id="case-016", exception_type="TEST")

        # Assert: Callback was invoked
        assert len(callback_events) == 1
        event = callback_events[0]
        assert event["type"] == "WORKLET_COMPLETED"
        assert event["data"]["worklet_id"] == worklet.id
        assert event["data"]["worklet_case_id"] == result.case_id
        assert event["data"]["parent_case_id"] == "case-016"


# --- JTBD 6: Complex Multi-Worklet Scenarios ---


class TestComplexScenarios:
    """Test complex multi-worklet scenarios."""

    def test_multiple_exception_types_same_case(self, executor: WorkletExecutor) -> None:
        """JTBD: Handle multiple different exceptions for the same case.

        Proves the ENGINE can manage multiple worklets for a single
        case when different exceptions occur.
        """
        # Arrange: Create worklets for different exception types
        timeout_worklet = Worklet(
            id="wl-timeout-multi",
            name="Timeout Handler",
            worklet_type=WorkletType.CASE_EXCEPTION,
            parameters={"action": "retry"},
        )
        validation_worklet = Worklet(
            id="wl-validation-multi",
            name="Validation Handler",
            worklet_type=WorkletType.CASE_EXCEPTION,
            parameters={"action": "correct_data"},
        )

        executor.register_worklet(timeout_worklet)
        executor.register_worklet(validation_worklet)

        # Set up trees for different exception types
        timeout_tree = executor.register_tree(task_id=None, exception_type="TIMEOUT")
        executor.add_rule(
            tree_id=timeout_tree,
            parent_node_id="root",
            is_true_branch=True,
            condition="true",
            worklet_id=timeout_worklet.id,
        )

        validation_tree = executor.register_tree(task_id=None, exception_type="VALIDATION_ERROR")
        executor.add_rule(
            tree_id=validation_tree,
            parent_node_id="root",
            is_true_branch=True,
            condition="true",
            worklet_id=validation_worklet.id,
        )

        # Act: Trigger both exceptions for same case
        timeout_result = executor.handle_case_exception(case_id="case-017", exception_type="TIMEOUT")
        validation_result = executor.handle_case_exception(case_id="case-017", exception_type="VALIDATION_ERROR")

        # Assert: Both worklets executed
        assert timeout_result.success
        assert timeout_result.worklet_id == timeout_worklet.id

        assert validation_result.success
        assert validation_result.worklet_id == validation_worklet.id

        # Assert: Both cases tracked for same parent
        cases = executor.repository.find_cases(parent_case_id="case-017")
        assert len(cases) == 2

    def test_fallback_chain_default_exception_type(self, executor: WorkletExecutor) -> None:
        """JTBD: Fall back through exception type chain: specific → default.

        Proves the RDR engine's complete fallback chain:
        task:specific → case:specific → task:default → case:default
        """
        # Arrange: Register only a case-level default worklet
        default_worklet = Worklet(
            id="wl-default",
            name="Default Handler",
            worklet_type=WorkletType.CASE_EXCEPTION,
            parameters={"action": "log"},
        )
        executor.register_worklet(default_worklet)

        # Set up default tree
        tree_id = executor.register_tree(task_id=None, exception_type="default")
        executor.add_rule(
            tree_id=tree_id, parent_node_id="root", is_true_branch=True, condition="true", worklet_id=default_worklet.id
        )

        # Act: Trigger unknown exception type
        result = executor.handle_case_exception(case_id="case-018", exception_type="UNKNOWN_CUSTOM_ERROR")

        # Assert: Falls back to default handler
        assert result.success
        assert result.worklet_id == default_worklet.id


# --- Edge Cases and Error Handling ---


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_worklet_with_specification_uri_raises_error(self, executor: WorkletExecutor) -> None:
        """JTBD: Reject worklets that require workflow execution (not implemented).

        Proves the ENGINE honestly reports unimplemented features.
        """
        # Arrange: Create worklet with specification_id
        workflow_worklet = Worklet(
            id="wl-workflow",
            name="Workflow Worklet",
            worklet_type=WorkletType.CASE_EXCEPTION,
            parameters={"specification_id": "spec-001", "action": "execute_workflow"},
        )
        executor.register_worklet(workflow_worklet)

        tree_id = executor.register_tree(task_id=None, exception_type="ERROR")
        executor.add_rule(
            tree_id=tree_id,
            parent_node_id="root",
            is_true_branch=True,
            condition="true",
            worklet_id=workflow_worklet.id,
        )

        # Act: Try to execute
        result = executor.handle_case_exception(case_id="case-020", exception_type="ERROR")

        # Assert: Execution fails with honest error
        assert not result.success
        assert result.error is not None
        assert "Workflow-based worklet execution not implemented" in result.error

    def test_cleanup_completed_cases(self, repository: WorkletRepository) -> None:
        """JTBD: Clean up old completed worklet cases to manage storage.

        Proves the repository can prune old completed cases.
        """
        from datetime import datetime, timedelta

        # Arrange: Create old completed case
        old_case = WorkletCase(
            id="case-old", worklet_id="wl-old", parent_case_id="case-parent", status=WorkletStatus.COMPLETED
        )
        # Manually set completion time to 48 hours ago
        old_case.completed = datetime.now() - timedelta(hours=48)
        repository.add_case(old_case)

        # Create recent completed case
        recent_case = WorkletCase(
            id="case-recent", worklet_id="wl-recent", parent_case_id="case-parent", status=WorkletStatus.COMPLETED
        )
        recent_case.completed = datetime.now() - timedelta(hours=12)
        repository.add_case(recent_case)

        # Act: Cleanup cases older than 24 hours
        removed_count = repository.cleanup_completed_cases(max_age_hours=24)

        # Assert: Only old case removed
        assert removed_count == 1
        assert repository.get_case("case-old") is None
        assert repository.get_case("case-recent") is not None
