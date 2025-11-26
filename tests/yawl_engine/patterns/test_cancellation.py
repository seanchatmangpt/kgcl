"""Comprehensive tests for YAWL Cancellation Patterns (19-21).

Tests verify cancellation behavior using Chicago School TDD methodology:
- Use REAL RDF graphs and YAWL ontology (no mocking domain objects)
- Tests drive observable behavior (status changes, token cleanup, audit trail)
- Each test verifies complete state transitions

Performance targets:
- p99 < 100ms per cancellation operation
- All operations must complete within SLA

Examples
--------
>>> import pytest
>>> from rdflib import Dataset, URIRef, Literal
>>> from kgcl.yawl_engine.patterns.cancellation import CancelTask
>>> store = Dataset()
>>> task_uri = URIRef("urn:task:test")
>>> store.add((task_uri, YAWL.status, Literal("active")))
>>> cancel = CancelTask()
>>> result = cancel.cancel(store, task_uri, "Test cancellation")
>>> assert result.success is True
"""

from __future__ import annotations

import time

import pytest
from rdflib import Dataset, Literal, Namespace, URIRef

from kgcl.yawl_engine.patterns.cancellation import CancelCase, CancellationResult, CancelRegion, CancelTask

# YAWL namespace definitions
YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")
KGC = Namespace("https://kgc.org/ns/")

# Performance constants
P99_TARGET_MS: float = 100.0
SHA256_HEX_LENGTH: int = 64


# Fixtures
@pytest.fixture
def empty_store() -> Dataset:
    """Create empty RDF quad-store."""
    return Dataset()


@pytest.fixture
def store_with_single_task() -> Dataset:
    """Create store with single active task."""
    store = Dataset()
    task = URIRef("urn:task:auth_code_entry")
    store.add((task, YAWL.status, Literal("active")))
    store.add((task, YAWL.name, Literal("Authorization Code Entry")))
    store.add((task, KGC.hasToken, Literal("token_1")))
    return store


@pytest.fixture
def store_with_workflow() -> Dataset:
    """Create store with complete workflow instance."""
    store = Dataset()
    workflow = URIRef("urn:workflow:nuclear_launch")
    task1 = URIRef("urn:task:initiate")
    task2 = URIRef("urn:task:authorize")
    task3 = URIRef("urn:task:launch")

    # Workflow structure
    store.add((workflow, YAWL.hasTask, task1))
    store.add((workflow, YAWL.hasTask, task2))
    store.add((workflow, YAWL.hasTask, task3))
    store.add((workflow, YAWL.status, Literal("active")))

    # Task states
    for task in [task1, task2, task3]:
        store.add((task, YAWL.status, Literal("active")))
        store.add((task, KGC.hasToken, Literal(f"token_{task}")))

    return store


@pytest.fixture
def store_with_regions() -> Dataset:
    """Create store with parallel regions."""
    store = Dataset()
    workflow = URIRef("urn:workflow:parallel_ops")

    # Region A tasks
    region_a_1 = URIRef("urn:task:region_a_auth")
    region_a_2 = URIRef("urn:task:region_a_validate")

    # Region B tasks (separate region)
    region_b_1 = URIRef("urn:task:region_b_prepare")
    region_b_2 = URIRef("urn:task:region_b_execute")

    # Add workflow structure
    store.add((workflow, YAWL.hasTask, region_a_1))
    store.add((workflow, YAWL.hasTask, region_a_2))
    store.add((workflow, YAWL.hasTask, region_b_1))
    store.add((workflow, YAWL.hasTask, region_b_2))

    # All tasks active
    for task in [region_a_1, region_a_2, region_b_1, region_b_2]:
        store.add((task, YAWL.status, Literal("active")))
        store.add((task, KGC.hasToken, Literal(f"token_{task}")))

    return store


# Tests for Pattern 19: Cancel Task
class TestCancelTask:
    """Tests for YAWL Pattern 19: Cancel Task."""

    def test_cancel_task_marks_status_as_cancelled(self, store_with_single_task: Dataset) -> None:
        """Task status changes from 'active' to 'cancelled'."""
        task = URIRef("urn:task:auth_code_entry")
        cancel = CancelTask()

        result = cancel.cancel(store_with_single_task, task, "User timeout")

        # Verify status change
        assert result.success is True
        cancelled_status = list(store_with_single_task.triples((task, YAWL.status, Literal("cancelled"))))
        assert len(cancelled_status) == 1

        # Verify active status removed
        active_status = list(store_with_single_task.triples((task, YAWL.status, Literal("active"))))
        assert len(active_status) == 0

    def test_cancel_task_adds_audit_metadata(self, store_with_single_task: Dataset) -> None:
        """Cancellation adds timestamp and reason to graph."""
        task = URIRef("urn:task:auth_code_entry")
        cancel = CancelTask()
        reason = "Manual cancellation by operator"

        before = time.time()
        result = cancel.cancel(store_with_single_task, task, reason)
        after = time.time()

        # Verify audit metadata in graph
        assert result.success is True
        assert result.reason == reason

        # Check timestamp in graph
        timestamps = list(store_with_single_task.triples((task, YAWL.cancelledAt, None)))
        assert len(timestamps) == 1
        timestamp_value = float(timestamps[0][2])
        assert before <= timestamp_value <= after

        # Check reason in graph
        reasons = list(store_with_single_task.triples((task, YAWL.cancellationReason, None)))
        assert len(reasons) == 1
        assert str(reasons[0][2]) == reason

    def test_cancel_task_removes_active_tokens(self, store_with_single_task: Dataset) -> None:
        """Active tokens are cleaned up after cancellation."""
        task = URIRef("urn:task:auth_code_entry")
        cancel = CancelTask()

        # Verify token exists before cancellation
        tokens_before = list(store_with_single_task.triples((task, KGC.hasToken, None)))
        assert len(tokens_before) == 1

        result = cancel.cancel(store_with_single_task, task, "Cleanup test")

        # Verify token removed
        assert result.success is True
        tokens_after = list(store_with_single_task.triples((task, KGC.hasToken, None)))
        assert len(tokens_after) == 0

    def test_cancel_task_with_nonexistent_task_fails(self, empty_store: Dataset) -> None:
        """Cancelling non-existent task returns error."""
        task = URIRef("urn:task:does_not_exist")
        cancel = CancelTask()

        result = cancel.cancel(empty_store, task, "Test failure")

        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error.lower()
        assert len(result.cancelled_tasks) == 0

    def test_cancel_task_returns_cancelled_task_uri(self, store_with_single_task: Dataset) -> None:
        """CancellationResult includes cancelled task URI."""
        task = URIRef("urn:task:auth_code_entry")
        cancel = CancelTask()

        result = cancel.cancel(store_with_single_task, task, "Test result")

        assert result.success is True
        assert len(result.cancelled_tasks) == 1
        assert result.cancelled_tasks[0] == str(task)

    def test_cancel_task_removes_all_active_statuses(self, empty_store: Dataset) -> None:
        """Cancel removes active, enabled, and executing statuses."""
        task = URIRef("urn:task:multi_status")
        empty_store.add((task, YAWL.status, Literal("active")))
        empty_store.add((task, YAWL.status, Literal("enabled")))
        empty_store.add((task, YAWL.status, Literal("executing")))

        cancel = CancelTask()
        result = cancel.cancel(empty_store, task, "Test multi-status")

        assert result.success is True

        # Verify all statuses removed
        for status in ["active", "enabled", "executing"]:
            status_triples = list(empty_store.triples((task, YAWL.status, Literal(status))))
            assert len(status_triples) == 0

        # Verify cancelled status added
        cancelled = list(empty_store.triples((task, YAWL.status, Literal("cancelled"))))
        assert len(cancelled) == 1

    @pytest.mark.performance
    def test_cancel_task_performance_p99(self, store_with_single_task: Dataset) -> None:
        """Cancel task completes within p99 target (<100ms)."""
        task = URIRef("urn:task:auth_code_entry")
        cancel = CancelTask()

        start = time.perf_counter()
        result = cancel.cancel(store_with_single_task, task, "Performance test")
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert result.success is True
        assert elapsed_ms < P99_TARGET_MS, f"Cancel took {elapsed_ms:.2f}ms, target <{P99_TARGET_MS}ms"


# Tests for Pattern 20: Cancel Case
class TestCancelCase:
    """Tests for YAWL Pattern 20: Cancel Case."""

    def test_cancel_case_cancels_all_workflow_tasks(self, store_with_workflow: Dataset) -> None:
        """All tasks in workflow are marked as cancelled."""
        workflow = URIRef("urn:workflow:nuclear_launch")
        cancel = CancelCase()

        result = cancel.cancel(store_with_workflow, workflow, "Emergency abort")

        # Verify all tasks cancelled
        assert result.success is True
        assert len(result.cancelled_tasks) == 3

        # Check each task has cancelled status
        for task_str in result.cancelled_tasks:
            task = URIRef(task_str)
            cancelled_status = list(store_with_workflow.triples((task, YAWL.status, Literal("cancelled"))))
            assert len(cancelled_status) == 1

    def test_cancel_case_marks_workflow_as_aborted(self, store_with_workflow: Dataset) -> None:
        """Workflow instance status changes to 'aborted'."""
        workflow = URIRef("urn:workflow:nuclear_launch")
        cancel = CancelCase()

        result = cancel.cancel(store_with_workflow, workflow, "Abort protocol")

        assert result.success is True

        # Verify workflow aborted status
        aborted_status = list(store_with_workflow.triples((workflow, YAWL.status, Literal("aborted"))))
        assert len(aborted_status) == 1

    def test_cancel_case_adds_workflow_audit_trail(self, store_with_workflow: Dataset) -> None:
        """Workflow aborted timestamp and reason are recorded."""
        workflow = URIRef("urn:workflow:nuclear_launch")
        cancel = CancelCase()
        reason = "Safety protocol violation"

        before = time.time()
        result = cancel.cancel(store_with_workflow, workflow, reason)
        after = time.time()

        assert result.success is True

        # Check aborted timestamp
        timestamps = list(store_with_workflow.triples((workflow, YAWL.abortedAt, None)))
        assert len(timestamps) == 1
        timestamp_value = float(timestamps[0][2])
        assert before <= timestamp_value <= after

        # Check abort reason
        reasons = list(store_with_workflow.triples((workflow, YAWL.abortReason, None)))
        assert len(reasons) == 1
        assert str(reasons[0][2]) == reason

    def test_cancel_case_removes_all_task_tokens(self, store_with_workflow: Dataset) -> None:
        """All task tokens are cleaned up."""
        workflow = URIRef("urn:workflow:nuclear_launch")
        cancel = CancelCase()

        # Verify tokens exist before cancellation
        tokens_before = list(store_with_workflow.triples((None, KGC.hasToken, None)))
        assert len(tokens_before) == 3

        result = cancel.cancel(store_with_workflow, workflow, "Token cleanup")

        assert result.success is True

        # Verify all tokens removed
        tokens_after = list(store_with_workflow.triples((None, KGC.hasToken, None)))
        assert len(tokens_after) == 0

    def test_cancel_case_with_nonexistent_workflow_fails(self, empty_store: Dataset) -> None:
        """Cancelling non-existent workflow returns error."""
        workflow = URIRef("urn:workflow:does_not_exist")
        cancel = CancelCase()

        result = cancel.cancel(empty_store, workflow, "Test failure")

        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error.lower()
        assert len(result.cancelled_tasks) == 0

    def test_cancel_case_adds_audit_to_all_tasks(self, store_with_workflow: Dataset) -> None:
        """Each task gets cancellation timestamp and reason."""
        workflow = URIRef("urn:workflow:nuclear_launch")
        cancel = CancelCase()
        reason = "System-wide abort"

        before = time.time()
        result = cancel.cancel(store_with_workflow, workflow, reason)
        after = time.time()

        assert result.success is True

        # Verify each task has audit metadata
        for task_str in result.cancelled_tasks:
            task = URIRef(task_str)

            # Check timestamp
            timestamps = list(store_with_workflow.triples((task, YAWL.cancelledAt, None)))
            assert len(timestamps) == 1
            timestamp_value = float(timestamps[0][2])
            assert before <= timestamp_value <= after

            # Check reason
            reasons = list(store_with_workflow.triples((task, YAWL.cancellationReason, None)))
            assert len(reasons) == 1
            assert str(reasons[0][2]) == reason

    @pytest.mark.performance
    def test_cancel_case_performance_p99(self, store_with_workflow: Dataset) -> None:
        """Cancel case completes within p99 target (<100ms)."""
        workflow = URIRef("urn:workflow:nuclear_launch")
        cancel = CancelCase()

        start = time.perf_counter()
        result = cancel.cancel(store_with_workflow, workflow, "Performance test")
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert result.success is True
        assert elapsed_ms < P99_TARGET_MS, f"Cancel case took {elapsed_ms:.2f}ms, target <{P99_TARGET_MS}ms"


# Tests for Pattern 21: Cancel Region
class TestCancelRegion:
    """Tests for YAWL Pattern 21: Cancel Region."""

    def test_cancel_region_cancels_only_region_tasks(self, store_with_regions: Dataset) -> None:
        """Only tasks in region are cancelled, others continue."""
        region_a_tasks = frozenset(["urn:task:region_a_auth", "urn:task:region_a_validate"])
        cancel = CancelRegion(region_tasks=region_a_tasks)
        trigger = URIRef("urn:task:region_a_auth")

        result = cancel.cancel_region(store_with_regions, trigger)

        assert result.success is True
        assert len(result.cancelled_tasks) == 2

        # Verify region A tasks cancelled
        for task_str in region_a_tasks:
            task = URIRef(task_str)
            cancelled_status = list(store_with_regions.triples((task, YAWL.status, Literal("cancelled"))))
            assert len(cancelled_status) == 1

        # Verify region B tasks still active
        region_b_1 = URIRef("urn:task:region_b_prepare")
        region_b_2 = URIRef("urn:task:region_b_execute")
        for task in [region_b_1, region_b_2]:
            active_status = list(store_with_regions.triples((task, YAWL.status, Literal("active"))))
            assert len(active_status) == 1

    def test_cancel_region_with_trigger_outside_region_fails(self, store_with_regions: Dataset) -> None:
        """Trigger task must be in region."""
        region_a_tasks = frozenset(["urn:task:region_a_auth", "urn:task:region_a_validate"])
        cancel = CancelRegion(region_tasks=region_a_tasks)
        trigger = URIRef("urn:task:region_b_prepare")  # Outside region A

        result = cancel.cancel_region(store_with_regions, trigger)

        assert result.success is False
        assert result.error is not None
        assert "region" in result.error.lower()
        assert len(result.cancelled_tasks) == 0

    def test_cancel_region_removes_tokens_only_in_region(self, store_with_regions: Dataset) -> None:
        """Tokens removed from region tasks, not from others."""
        region_a_tasks = frozenset(["urn:task:region_a_auth", "urn:task:region_a_validate"])
        cancel = CancelRegion(region_tasks=region_a_tasks)
        trigger = URIRef("urn:task:region_a_auth")

        # Verify all tokens exist before
        tokens_before = list(store_with_regions.triples((None, KGC.hasToken, None)))
        assert len(tokens_before) == 4

        result = cancel.cancel_region(store_with_regions, trigger)

        assert result.success is True

        # Verify region A tokens removed
        for task_str in region_a_tasks:
            task = URIRef(task_str)
            tokens = list(store_with_regions.triples((task, KGC.hasToken, None)))
            assert len(tokens) == 0

        # Verify region B tokens still exist
        region_b_1 = URIRef("urn:task:region_b_prepare")
        region_b_2 = URIRef("urn:task:region_b_execute")
        for task in [region_b_1, region_b_2]:
            tokens = list(store_with_regions.triples((task, KGC.hasToken, None)))
            assert len(tokens) == 1

    def test_cancel_region_adds_audit_trail_with_trigger(self, store_with_regions: Dataset) -> None:
        """Cancellation reason includes trigger task URI."""
        region_a_tasks = frozenset(["urn:task:region_a_auth", "urn:task:region_a_validate"])
        cancel = CancelRegion(region_tasks=region_a_tasks)
        trigger = URIRef("urn:task:region_a_auth")

        before = time.time()
        result = cancel.cancel_region(store_with_regions, trigger)
        after = time.time()

        assert result.success is True
        assert str(trigger) in result.reason

        # Verify each task has audit metadata
        for task_str in region_a_tasks:
            task = URIRef(task_str)

            # Check timestamp
            timestamps = list(store_with_regions.triples((task, YAWL.cancelledAt, None)))
            assert len(timestamps) == 1
            timestamp_value = float(timestamps[0][2])
            assert before <= timestamp_value <= after

            # Check reason includes trigger
            reasons = list(store_with_regions.triples((task, YAWL.cancellationReason, None)))
            assert len(reasons) == 1
            assert str(trigger) in str(reasons[0][2])

    def test_cancel_region_with_empty_region(self, empty_store: Dataset) -> None:
        """Empty region cancels nothing, returns success."""
        cancel = CancelRegion(region_tasks=frozenset())
        trigger = URIRef("urn:task:any")

        result = cancel.cancel_region(empty_store, trigger)

        # Empty region with trigger outside should fail
        assert result.success is False
        assert len(result.cancelled_tasks) == 0

    def test_cancel_region_skips_nonexistent_tasks(self, store_with_regions: Dataset) -> None:
        """Region with non-existent tasks skips them gracefully."""
        region_with_missing = frozenset(
            [
                "urn:task:region_a_auth",  # Exists
                "urn:task:does_not_exist",  # Missing
            ]
        )
        cancel = CancelRegion(region_tasks=region_with_missing)
        trigger = URIRef("urn:task:region_a_auth")

        result = cancel.cancel_region(store_with_regions, trigger)

        assert result.success is True
        # Should cancel only the existing task
        assert "urn:task:region_a_auth" in result.cancelled_tasks

    @pytest.mark.performance
    def test_cancel_region_performance_p99(self, store_with_regions: Dataset) -> None:
        """Cancel region completes within p99 target (<100ms)."""
        region_a_tasks = frozenset(["urn:task:region_a_auth", "urn:task:region_a_validate"])
        cancel = CancelRegion(region_tasks=region_a_tasks)
        trigger = URIRef("urn:task:region_a_auth")

        start = time.perf_counter()
        result = cancel.cancel_region(store_with_regions, trigger)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert result.success is True
        assert elapsed_ms < P99_TARGET_MS, f"Cancel region took {elapsed_ms:.2f}ms, target <{P99_TARGET_MS}ms"


# Integration Tests
@pytest.mark.integration
class TestCancellationIntegration:
    """Integration tests for cancellation patterns."""

    def test_cancel_task_then_cancel_remaining_case(self, store_with_workflow: Dataset) -> None:
        """Cancel single task, then cancel entire workflow."""
        workflow = URIRef("urn:workflow:nuclear_launch")
        task1 = URIRef("urn:task:initiate")

        # Step 1: Cancel single task
        cancel_task = CancelTask()
        result1 = cancel_task.cancel(store_with_workflow, task1, "Task failure")

        assert result1.success is True
        assert len(result1.cancelled_tasks) == 1

        # Step 2: Cancel entire workflow
        cancel_case = CancelCase()
        result2 = cancel_case.cancel(store_with_workflow, workflow, "Abort all")

        assert result2.success is True
        assert len(result2.cancelled_tasks) == 3  # All tasks

        # Verify workflow aborted
        aborted = list(store_with_workflow.triples((workflow, YAWL.status, Literal("aborted"))))
        assert len(aborted) == 1

    def test_cancel_region_then_cancel_case(self, store_with_regions: Dataset) -> None:
        """Cancel region A, then cancel entire workflow."""
        workflow = URIRef("urn:workflow:parallel_ops")
        region_a_tasks = frozenset(["urn:task:region_a_auth", "urn:task:region_a_validate"])

        # Add workflow to store
        store_with_regions.add((workflow, YAWL.status, Literal("active")))

        # Step 1: Cancel region A
        cancel_region = CancelRegion(region_tasks=region_a_tasks)
        trigger = URIRef("urn:task:region_a_auth")
        result1 = cancel_region.cancel_region(store_with_regions, trigger)

        assert result1.success is True
        assert len(result1.cancelled_tasks) == 2

        # Step 2: Cancel entire workflow
        cancel_case = CancelCase()
        result2 = cancel_case.cancel(store_with_regions, workflow, "Full abort")

        assert result2.success is True
        # Should cancel all 4 tasks (even though 2 already cancelled)
        assert len(result2.cancelled_tasks) == 4

    def test_cancellation_result_immutability(self) -> None:
        """CancellationResult is immutable (frozen dataclass)."""
        result = CancellationResult(
            cancelled_tasks=("urn:task:t1",), reason="Test", timestamp=1704067200.0, success=True
        )

        # Verify frozen
        with pytest.raises(AttributeError):
            result.success = False  # type: ignore[misc]

        with pytest.raises(AttributeError):
            result.cancelled_tasks = ()  # type: ignore[misc]
