"""Tests for YAWL exception handling service.

Verifies exception rules, retry logic, and compensation.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from kgcl.yawl.engine.y_exception import (
    CompensationHandler,
    ExceptionAction,
    ExceptionRule,
    ExceptionType,
    RetryContext,
    YCompensationService,
    YExceptionService,
    YWorkflowException,
)


class TestYWorkflowException:
    """Tests for workflow exception creation."""

    def test_create_exception(self) -> None:
        """Create workflow exception."""
        exc = YWorkflowException(
            id="exc-001", exception_type=ExceptionType.TASK_FAILURE, message="Task failed to execute"
        )

        assert exc.id == "exc-001"
        assert exc.exception_type == ExceptionType.TASK_FAILURE
        assert exc.message == "Task failed to execute"
        assert not exc.handled

    def test_exception_with_context(self) -> None:
        """Exception with case/work item context."""
        exc = YWorkflowException(
            id="exc-001",
            exception_type=ExceptionType.TIMEOUT,
            message="Execution timed out",
            case_id="case-001",
            work_item_id="wi-001",
            task_id="task-A",
        )

        assert exc.case_id == "case-001"
        assert exc.work_item_id == "wi-001"
        assert exc.task_id == "task-A"

    def test_exception_with_data(self) -> None:
        """Exception with additional data."""
        exc = YWorkflowException(
            id="exc-001",
            exception_type=ExceptionType.EXTERNAL_FAILURE,
            message="Service unavailable",
            data={"service": "payment-api", "status_code": 503},
        )

        assert exc.data["service"] == "payment-api"
        assert exc.data["status_code"] == 503

    def test_mark_handled(self) -> None:
        """Mark exception as handled."""
        exc = YWorkflowException(id="exc-001", exception_type=ExceptionType.TASK_FAILURE, message="Task failed")

        exc.mark_handled(ExceptionAction.RETRY)

        assert exc.handled
        assert exc.action_taken == ExceptionAction.RETRY


class TestExceptionTypes:
    """Tests for exception type enumeration."""

    def test_all_exception_types(self) -> None:
        """All expected exception types exist."""
        assert ExceptionType.TASK_FAILURE
        assert ExceptionType.TIMEOUT
        assert ExceptionType.RESOURCE_UNAVAILABLE
        assert ExceptionType.DATA_ERROR
        assert ExceptionType.CONSTRAINT_VIOLATION
        assert ExceptionType.EXTERNAL_FAILURE
        assert ExceptionType.CANCELLATION
        assert ExceptionType.DEADLOCK
        assert ExceptionType.SYSTEM_ERROR
        assert ExceptionType.CUSTOM


class TestExceptionActions:
    """Tests for exception action enumeration."""

    def test_all_exception_actions(self) -> None:
        """All expected exception actions exist."""
        assert ExceptionAction.IGNORE
        assert ExceptionAction.RETRY
        assert ExceptionAction.SKIP
        assert ExceptionAction.COMPLETE
        assert ExceptionAction.FAIL
        assert ExceptionAction.CANCEL_TASK
        assert ExceptionAction.CANCEL_CASE
        assert ExceptionAction.SUSPEND
        assert ExceptionAction.ESCALATE
        assert ExceptionAction.WORKLET
        assert ExceptionAction.COMPENSATE


class TestExceptionRule:
    """Tests for exception handling rules."""

    def test_create_rule(self) -> None:
        """Create exception rule."""
        rule = ExceptionRule(
            id="rule-001",
            name="Retry on timeout",
            exception_types={ExceptionType.TIMEOUT},
            action=ExceptionAction.RETRY,
            action_params={"max_retries": 3},
        )

        assert rule.id == "rule-001"
        assert rule.name == "Retry on timeout"
        assert ExceptionType.TIMEOUT in rule.exception_types
        assert rule.action == ExceptionAction.RETRY

    def test_rule_matches_exception_type(self) -> None:
        """Rule matches by exception type."""
        rule = ExceptionRule(
            id="rule-001",
            exception_types={ExceptionType.TIMEOUT, ExceptionType.EXTERNAL_FAILURE},
            action=ExceptionAction.RETRY,
        )

        timeout_exc = YWorkflowException(id="exc-001", exception_type=ExceptionType.TIMEOUT, message="Timed out")
        data_exc = YWorkflowException(id="exc-002", exception_type=ExceptionType.DATA_ERROR, message="Invalid data")

        assert rule.matches(timeout_exc)
        assert not rule.matches(data_exc)

    def test_rule_matches_task_id(self) -> None:
        """Rule matches by specific task ID."""
        rule = ExceptionRule(
            id="rule-001",
            exception_types={ExceptionType.TASK_FAILURE},
            task_ids={"task-A", "task-B"},
            action=ExceptionAction.RETRY,
        )

        exc_a = YWorkflowException(
            id="exc-001", exception_type=ExceptionType.TASK_FAILURE, message="Failed", task_id="task-A"
        )
        exc_c = YWorkflowException(
            id="exc-002", exception_type=ExceptionType.TASK_FAILURE, message="Failed", task_id="task-C"
        )

        assert rule.matches(exc_a)
        assert not rule.matches(exc_c)

    def test_disabled_rule_does_not_match(self) -> None:
        """Disabled rule does not match."""
        rule = ExceptionRule(
            id="rule-001", exception_types={ExceptionType.TIMEOUT}, action=ExceptionAction.RETRY, enabled=False
        )

        exc = YWorkflowException(id="exc-001", exception_type=ExceptionType.TIMEOUT, message="Timed out")

        assert not rule.matches(exc)


class TestRetryContext:
    """Tests for retry context management."""

    def test_create_retry_context(self) -> None:
        """Create retry context."""
        ctx = RetryContext(work_item_id="wi-001", max_retries=3)

        assert ctx.work_item_id == "wi-001"
        assert ctx.max_retries == 3
        assert ctx.retry_count == 0

    def test_can_retry(self) -> None:
        """Check if retries available."""
        ctx = RetryContext(work_item_id="wi-001", max_retries=3, retry_count=2)

        assert ctx.can_retry()

        ctx.retry_count = 3
        assert not ctx.can_retry()

    def test_increment_retry(self) -> None:
        """Increment retry count."""
        ctx = RetryContext(work_item_id="wi-001", max_retries=3)

        ctx.increment_retry()

        assert ctx.retry_count == 1
        assert ctx.last_retry is not None


class TestYExceptionService:
    """Tests for exception service."""

    def test_create_service(self) -> None:
        """Create exception service."""
        service = YExceptionService()

        assert len(service.rules) == 0
        assert len(service.exceptions) == 0

    def test_add_rule(self) -> None:
        """Add exception rule."""
        service = YExceptionService()
        rule = ExceptionRule(id="rule-001", exception_types={ExceptionType.TIMEOUT}, action=ExceptionAction.RETRY)

        service.add_rule(rule)

        assert len(service.rules) == 1

    def test_rules_sorted_by_priority(self) -> None:
        """Rules sorted by priority (highest first)."""
        service = YExceptionService()

        low = ExceptionRule(id="low", exception_types={ExceptionType.TIMEOUT}, action=ExceptionAction.RETRY, priority=1)
        high = ExceptionRule(
            id="high", exception_types={ExceptionType.TIMEOUT}, action=ExceptionAction.FAIL, priority=10
        )
        medium = ExceptionRule(
            id="medium", exception_types={ExceptionType.TIMEOUT}, action=ExceptionAction.SKIP, priority=5
        )

        service.add_rule(low)
        service.add_rule(high)
        service.add_rule(medium)

        assert service.rules[0].id == "high"
        assert service.rules[1].id == "medium"
        assert service.rules[2].id == "low"

    def test_handle_exception_with_rule(self) -> None:
        """Handle exception using matching rule."""
        service = YExceptionService()
        service.add_rule(
            ExceptionRule(id="rule-001", exception_types={ExceptionType.TIMEOUT}, action=ExceptionAction.SKIP)
        )

        exc = YWorkflowException(id="exc-001", exception_type=ExceptionType.TIMEOUT, message="Timed out")

        action = service.handle_exception(exc)

        assert action == ExceptionAction.SKIP
        assert exc.handled
        assert exc.action_taken == ExceptionAction.SKIP

    def test_handle_exception_default_action(self) -> None:
        """Use default action when no rule matches."""
        service = YExceptionService()
        service.default_action = ExceptionAction.FAIL

        exc = YWorkflowException(id="exc-001", exception_type=ExceptionType.DATA_ERROR, message="Bad data")

        action = service.handle_exception(exc)

        assert action == ExceptionAction.FAIL

    def test_handle_retry_with_context(self) -> None:
        """Retry action creates/uses retry context."""
        service = YExceptionService()
        service.add_rule(
            ExceptionRule(
                id="rule-001",
                exception_types={ExceptionType.EXTERNAL_FAILURE},
                action=ExceptionAction.RETRY,
                action_params={"max_retries": 3},
            )
        )

        exc = YWorkflowException(
            id="exc-001",
            exception_type=ExceptionType.EXTERNAL_FAILURE,
            message="Service unavailable",
            work_item_id="wi-001",
        )

        # First retry
        action1 = service.handle_exception(exc)
        assert action1 == ExceptionAction.RETRY

        # Second retry
        exc2 = service.create_exception(ExceptionType.EXTERNAL_FAILURE, "Still unavailable", work_item_id="wi-001")
        action2 = service.handle_exception(exc2)
        assert action2 == ExceptionAction.RETRY

        # Third retry
        exc3 = service.create_exception(ExceptionType.EXTERNAL_FAILURE, "Still unavailable", work_item_id="wi-001")
        action3 = service.handle_exception(exc3)
        assert action3 == ExceptionAction.RETRY

        # Fourth attempt - max exceeded
        exc4 = service.create_exception(ExceptionType.EXTERNAL_FAILURE, "Still unavailable", work_item_id="wi-001")
        action4 = service.handle_exception(exc4)
        assert action4 == ExceptionAction.FAIL

    def test_get_exceptions_for_case(self) -> None:
        """Get exceptions filtered by case."""
        service = YExceptionService()

        exc1 = service.create_exception(ExceptionType.TASK_FAILURE, "Failed 1", case_id="case-001")
        exc2 = service.create_exception(ExceptionType.TASK_FAILURE, "Failed 2", case_id="case-001")
        exc3 = service.create_exception(ExceptionType.TASK_FAILURE, "Failed 3", case_id="case-002")

        service.handle_exception(exc1)
        service.handle_exception(exc2)
        service.handle_exception(exc3)

        case1_excs = service.get_exceptions_for_case("case-001")

        assert len(case1_excs) == 2

    def test_get_unhandled_exceptions(self) -> None:
        """Get unhandled exceptions."""
        service = YExceptionService()

        exc1 = YWorkflowException(id="exc-001", exception_type=ExceptionType.TASK_FAILURE, message="Failed")
        exc2 = YWorkflowException(id="exc-002", exception_type=ExceptionType.TASK_FAILURE, message="Failed again")

        service.exceptions.append(exc1)
        service.exceptions.append(exc2)

        exc1.mark_handled(ExceptionAction.RETRY)

        unhandled = service.get_unhandled_exceptions()

        assert len(unhandled) == 1
        assert unhandled[0].id == "exc-002"


class TestCompensationHandler:
    """Tests for compensation handler."""

    def test_create_handler(self) -> None:
        """Create compensation handler."""
        handler = CompensationHandler(task_id="task-A", compensation_task_id="task-A-compensation")

        assert handler.task_id == "task-A"
        assert handler.compensation_task_id == "task-A-compensation"

    def test_compensation_with_logic(self) -> None:
        """Compensation with custom logic."""
        result = {"compensated": False}

        def compensate(ctx: dict) -> None:
            result["compensated"] = True
            result["amount"] = ctx.get("amount", 0)

        handler = CompensationHandler(task_id="task-A", compensation_logic=compensate)

        success = handler.compensate({"amount": 100})

        assert success
        assert result["compensated"]
        assert result["amount"] == 100


class TestYCompensationService:
    """Tests for compensation service."""

    def test_create_service(self) -> None:
        """Create compensation service."""
        service = YCompensationService()

        assert len(service.handlers) == 0
        assert len(service.compensation_stack) == 0

    def test_record_completion(self) -> None:
        """Record task completion for potential compensation."""
        service = YCompensationService()

        service.record_completion("task-A", {"order_id": "123"})
        service.record_completion("task-B", {"order_id": "123", "approved": True})

        assert len(service.compensation_stack) == 2

    def test_compensate_all(self) -> None:
        """Compensate all completed tasks in reverse order."""
        compensations = []

        def make_handler(task_id: str) -> CompensationHandler:
            def logic(ctx: dict) -> None:
                compensations.append(task_id)

            return CompensationHandler(task_id=task_id, compensation_logic=logic)

        service = YCompensationService()
        service.register_handler(make_handler("task-A"))
        service.register_handler(make_handler("task-B"))
        service.register_handler(make_handler("task-C"))

        service.record_completion("task-A", {})
        service.record_completion("task-B", {})
        service.record_completion("task-C", {})

        compensated = service.compensate_all()

        # Should be in reverse order (stack)
        assert compensations == ["task-C", "task-B", "task-A"]
        assert len(compensated) == 3

    def test_compensate_to_specific_task(self) -> None:
        """Compensate back to specific task."""
        compensations = []

        def make_handler(task_id: str) -> CompensationHandler:
            def logic(ctx: dict) -> None:
                compensations.append(task_id)

            return CompensationHandler(task_id=task_id, compensation_logic=logic)

        service = YCompensationService()
        service.register_handler(make_handler("task-A"))
        service.register_handler(make_handler("task-B"))
        service.register_handler(make_handler("task-C"))

        service.record_completion("task-A", {})
        service.record_completion("task-B", {})
        service.record_completion("task-C", {})

        # Compensate only C and B, stop at A
        compensated = service.compensate_to("task-A")

        assert compensations == ["task-C", "task-B"]
        assert len(compensated) == 2
        # task-A should still be on stack
        assert len(service.compensation_stack) == 1
        assert service.compensation_stack[0][0] == "task-A"
