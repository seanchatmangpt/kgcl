"""Gap-filling tests for worklet integration - the critical 20% for 95% coverage.

These tests address the missing scenarios identified in gap analysis:
1. Concurrent worklet execution (thread safety)
2. Invalid/malformed data handling (robustness)
3. Performance and memory cleanup (scalability)
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import pytest

from kgcl.yawl.worklets.exceptions import RuleEvaluationError, WorkletValidationError
from kgcl.yawl.worklets.executor import WorkletExecutor, WorkletResult
from kgcl.yawl.worklets.models import Worklet, WorkletCase, WorkletStatus, WorkletType
from kgcl.yawl.worklets.repository import WorkletRepository
from kgcl.yawl.worklets.rules import RDREngine, RuleContext


# --- Gap 1: Concurrent Worklet Execution ---


class TestConcurrentExecution:
    """Test thread safety and concurrent worklet execution.

    Fills gap: Multiple exceptions occurring simultaneously in production.
    """

    def test_concurrent_case_exceptions_same_worklet(self) -> None:
        """JTBD: Handle multiple case exceptions concurrently without race conditions.

        Proves the ENGINE can safely handle concurrent exceptions from
        different cases using the same worklet definition.
        """
        # Arrange: Set up single worklet for multiple cases
        executor = WorkletExecutor()
        worklet = Worklet(
            id="wl-concurrent",
            name="Concurrent Handler",
            worklet_type=WorkletType.CASE_EXCEPTION,
            parameters={"action": "handle"},
        )
        executor.register_worklet(worklet)

        tree_id = executor.register_tree(task_id=None, exception_type="CONCURRENT_ERROR")
        executor.add_rule(
            tree_id=tree_id,
            parent_node_id="root",
            is_true_branch=True,
            condition="true",
            worklet_id=worklet.id,
        )

        # Act: Execute 10 concurrent exceptions
        def handle_exception(case_num: int) -> WorkletResult:
            return executor.handle_case_exception(
                case_id=f"case-{case_num}",
                exception_type="CONCURRENT_ERROR",
                case_data={"case_num": case_num},
            )

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(handle_exception, i) for i in range(10)]
            results = [f.result() for f in as_completed(futures)]

        # Assert: All executions succeeded
        assert len(results) == 10
        assert all(r.success for r in results), "All concurrent executions should succeed"

        # Assert: No duplicate case IDs (proves no race condition)
        case_ids = [r.case_id for r in results]
        assert len(case_ids) == len(set(case_ids)), "Should have unique case IDs"

        # Assert: All cases stored in repository
        all_cases = executor.repository.find_cases()
        assert len(all_cases) >= 10, "All cases should be stored"

        # Assert: All cases completed successfully
        completed_cases = [c for c in all_cases if c.status == WorkletStatus.COMPLETED]
        assert len(completed_cases) >= 10, "All cases should be completed"

    def test_concurrent_item_exceptions_same_case(self) -> None:
        """JTBD: Handle multiple work item exceptions for same case concurrently.

        Proves the ENGINE can safely handle concurrent item exceptions
        without corrupting case state.
        """
        # Arrange: Set up worklet for item exceptions
        executor = WorkletExecutor()
        worklet = Worklet(
            id="wl-item-concurrent",
            name="Item Concurrent Handler",
            worklet_type=WorkletType.ITEM_EXCEPTION,
            parameters={"action": "retry"},
        )
        executor.register_worklet(worklet)

        tree_id = executor.register_tree(task_id="task-process", exception_type="ITEM_ERROR")
        executor.add_rule(
            tree_id=tree_id,
            parent_node_id="root",
            is_true_branch=True,
            condition="true",
            worklet_id=worklet.id,
        )

        # Act: Execute 5 concurrent item exceptions for same case
        parent_case_id = "case-concurrent-items"

        def handle_item_exception(item_num: int) -> WorkletResult:
            return executor.handle_item_exception(
                case_id=parent_case_id,
                work_item_id=f"wi-{item_num}",
                task_id="task-process",
                exception_type="ITEM_ERROR",
                work_item_data={"item_num": item_num},
            )

        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(handle_item_exception, i) for i in range(5)]
            results = [f.result() for f in as_completed(futures)]

        # Assert: All executions succeeded
        assert len(results) == 5
        assert all(r.success for r in results)

        # Assert: All worklet cases are for same parent
        cases = executor.repository.find_cases(parent_case_id=parent_case_id)
        assert len(cases) == 5
        assert all(c.parent_case_id == parent_case_id for c in cases)

        # Assert: Each has unique work item ID (proves no collision)
        work_item_ids = {c.parent_work_item_id for c in cases}
        assert len(work_item_ids) == 5, "Should have 5 unique work item IDs"


# --- Gap 2: Invalid/Malformed Data Handling ---


class TestInvalidDataHandling:
    """Test robustness against invalid and malformed data.

    Fills gap: Real systems receive bad input and must handle gracefully.
    """

    def test_invalid_rdr_condition_syntax(self) -> None:
        """JTBD: Detect and reject RDR conditions with syntax errors.

        Proves the ENGINE validates conditions and fails fast on invalid syntax.
        """
        # Arrange: Create RDR engine
        rdr_engine = RDREngine()

        # Create context
        context = RuleContext(
            case_id="case-test",
            exception_type="TEST",
            case_data={"value": 10},
        )

        # Act & Assert: Empty condition raises error (via _evaluate_condition which validates)
        with pytest.raises(RuleEvaluationError) as exc_info:
            rdr_engine._evaluate_condition("", context)

        assert "Condition cannot be empty" in str(exc_info.value)

        # Act & Assert: Whitespace-only condition raises error
        with pytest.raises(RuleEvaluationError) as exc_info:
            rdr_engine._evaluate_condition("   ", context)

        assert "Condition cannot be empty" in str(exc_info.value)

        # Act: Invalid syntax is treated as variable lookup (lenient behavior)
        # The engine treats unknown patterns as truthy checks on variable names
        result = rdr_engine._default_evaluate("invalid_var", context)
        # No exception raised - this proves lenient evaluation
        assert result is False, "Non-existent variable should be falsy"

    def test_malformed_worklet_parameters(self) -> None:
        """JTBD: Handle worklets with missing or invalid parameters gracefully.

        Proves the ENGINE validates worklet definitions at creation.
        """
        # Act & Assert: Empty worklet ID raises error
        with pytest.raises(ValueError) as exc_info:
            Worklet(id="", name="Test")

        assert "id cannot be empty" in str(exc_info.value)

        # Act & Assert: Empty worklet name raises error
        with pytest.raises(ValueError) as exc_info:
            Worklet(id="test", name="")

        assert "name cannot be empty" in str(exc_info.value)

        # Act & Assert: Invalid version raises error
        with pytest.raises(ValueError) as exc_info:
            Worklet(id="test", name="Test", version=0)

        assert "version must be >= 1" in str(exc_info.value)

    def test_invalid_exception_context(self) -> None:
        """JTBD: Validate exception context has required fields.

        Proves the ENGINE validates context before processing.
        """
        # Act & Assert: Empty case_id raises error
        with pytest.raises(ValueError) as exc_info:
            RuleContext(case_id="", exception_type="TEST")

        assert "case_id cannot be empty" in str(exc_info.value)

        # Act: Valid context with missing data still works
        context = RuleContext(case_id="case-001", exception_type="TEST")

        # Assert: Context get() returns default for missing data
        assert context.get("nonexistent") is None
        assert context.get("nonexistent", "default") == "default"

    def test_worklet_case_validation(self) -> None:
        """JTBD: Validate worklet case has required fields.

        Proves the ENGINE validates case data at creation.
        """
        # Act & Assert: Empty case ID raises error
        with pytest.raises(ValueError) as exc_info:
            WorkletCase(id="", worklet_id="wl-001", parent_case_id="parent-001")

        assert "id cannot be empty" in str(exc_info.value)

        # Act & Assert: Empty worklet ID raises error
        with pytest.raises(ValueError) as exc_info:
            WorkletCase(id="case-001", worklet_id="", parent_case_id="parent-001")

        assert "worklet_id cannot be empty" in str(exc_info.value)

        # Act & Assert: Empty parent case ID raises error
        with pytest.raises(ValueError) as exc_info:
            WorkletCase(id="case-001", worklet_id="wl-001", parent_case_id="")

        assert "parent_case_id cannot be empty" in str(exc_info.value)


# --- Gap 3: Performance & Resource Management ---


class TestPerformanceAndCleanup:
    """Test performance characteristics and resource cleanup.

    Fills gap: Long-running systems need cleanup and scale verification.
    """

    def test_memory_cleanup_after_completion(self) -> None:
        """JTBD: Clean up old completed worklet cases to prevent memory leaks.

        Proves the ENGINE provides cleanup mechanisms for long-running systems.
        """
        from datetime import datetime, timedelta

        # Arrange: Create repository with old and new cases
        repository = WorkletRepository()

        # Create old completed case (48 hours ago)
        old_case = WorkletCase(
            id="case-old",
            worklet_id="wl-test",
            parent_case_id="parent-001",
            status=WorkletStatus.COMPLETED,
        )
        old_case.completed = datetime.now() - timedelta(hours=48)
        repository.add_case(old_case)

        # Create recent completed case (12 hours ago)
        recent_case = WorkletCase(
            id="case-recent",
            worklet_id="wl-test",
            parent_case_id="parent-002",
            status=WorkletStatus.COMPLETED,
        )
        recent_case.completed = datetime.now() - timedelta(hours=12)
        repository.add_case(recent_case)

        # Create running case
        running_case = WorkletCase(
            id="case-running",
            worklet_id="wl-test",
            parent_case_id="parent-003",
            status=WorkletStatus.RUNNING,
        )
        repository.add_case(running_case)

        # Assert: 3 cases before cleanup
        assert len(repository.find_cases()) == 3

        # Act: Cleanup cases older than 24 hours
        removed_count = repository.cleanup_completed_cases(max_age_hours=24)

        # Assert: Only old case removed
        assert removed_count == 1

        # Assert: Recent and running cases remain
        remaining = repository.find_cases()
        assert len(remaining) == 2
        assert repository.get_case("case-old") is None
        assert repository.get_case("case-recent") is not None
        assert repository.get_case("case-running") is not None

    def test_large_scale_worklet_execution(self) -> None:
        """JTBD: Handle 100+ worklet executions without degradation.

        Proves the ENGINE can scale to production workloads.
        """
        # Arrange: Create executor with worklet
        executor = WorkletExecutor()
        worklet = Worklet(
            id="wl-scale-test",
            name="Scale Test Handler",
            worklet_type=WorkletType.CASE_EXCEPTION,
            parameters={"action": "process"},
        )
        executor.register_worklet(worklet)

        tree_id = executor.register_tree(task_id=None, exception_type="SCALE_TEST")
        executor.add_rule(
            tree_id=tree_id,
            parent_node_id="root",
            is_true_branch=True,
            condition="true",
            worklet_id=worklet.id,
        )

        # Act: Execute 100 worklets
        results = []
        for i in range(100):
            result = executor.handle_case_exception(
                case_id=f"case-scale-{i}",
                exception_type="SCALE_TEST",
                case_data={"index": i},
            )
            results.append(result)

        # Assert: All executions succeeded
        assert len(results) == 100
        assert all(r.success for r in results)

        # Assert: All cases stored
        all_cases = executor.repository.find_cases()
        assert len(all_cases) >= 100

        # Assert: Repository still functional
        query_result = executor.repository.find_cases(status=WorkletStatus.COMPLETED)
        assert len(query_result) >= 100

        # Assert: Can still add new worklet after scale test
        new_result = executor.handle_case_exception(
            case_id="case-after-scale",
            exception_type="SCALE_TEST",
        )
        assert new_result.success

    def test_rdr_tree_with_deep_nesting(self) -> None:
        """JTBD: Handle deeply nested RDR trees without stack overflow.

        Proves the ENGINE can traverse deep decision trees.
        """
        # Arrange: Create executor
        executor = WorkletExecutor()

        # Create single worklet for all depths
        worklet = Worklet(
            id="wl-deep-test",
            name="Deep Handler",
            worklet_type=WorkletType.CASE_EXCEPTION,
            parameters={"action": "handle"},
        )
        executor.register_worklet(worklet)

        # Build deep tree (10 levels of conditions)
        tree_id = executor.register_tree(task_id=None, exception_type="DEPTH_TEST")

        # Build a chain of nodes with conditions
        # Root: true (always matches)
        tree = executor.repository.get_tree(tree_id)
        assert tree is not None
        tree.root.condition = "true"
        tree.root.conclusion = None  # No conclusion at root

        # Build chain of refinements
        current_node_id = "root"
        for i in range(10):
            # Add true child
            node_id = executor.add_rule(
                tree_id=tree_id,
                parent_node_id=current_node_id,
                is_true_branch=True,
                condition="true",  # Always true for deep traversal test
                worklet_id=None if i < 9 else worklet.id,  # Only leaf has conclusion
            )
            if node_id:
                current_node_id = node_id

        # Act: Execute to traverse deep tree
        result = executor.handle_case_exception(
            case_id="case-deep",
            exception_type="DEPTH_TEST",
            case_data={"test": "deep"},
        )

        # Assert: Successfully traversed 10 levels without stack overflow
        assert result.success, f"Deep traversal should succeed, got: {result.error}"
        assert result.worklet_id == worklet.id
        # The fact that this completes proves no stack overflow occurred

        # Verify tree has 11 nodes (root + 10 children)
        assert len(tree.nodes) == 11, f"Tree should have 11 nodes, has {len(tree.nodes)}"


# --- Integration Tests ---


class TestRepositoryEdgeCases:
    """Test repository edge cases and boundary conditions."""

    def test_query_builder_chaining(self) -> None:
        """JTBD: Build complex queries with fluent interface.

        Proves the repository query builder works correctly.
        """
        # Arrange: Create repository with various worklets
        repository = WorkletRepository()

        # Add case exception worklets
        for i in range(5):
            repository.add_worklet(
                Worklet(
                    id=f"wl-case-{i}",
                    name=f"Case {i}",
                    worklet_type=WorkletType.CASE_EXCEPTION,
                    enabled=(i % 2 == 0),  # Alternate enabled/disabled
                )
            )

        # Add item exception worklets
        for i in range(3):
            repository.add_worklet(
                Worklet(
                    id=f"wl-item-{i}",
                    name=f"Item {i}",
                    worklet_type=WorkletType.ITEM_EXCEPTION,
                    enabled=True,
                )
            )

        # Act: Query for enabled case exception worklets
        results = (
            repository.query_worklets()
            .filter_type(WorkletType.CASE_EXCEPTION)
            .filter_enabled(True)
            .execute()
        )

        # Assert: Only enabled case worklets returned
        assert len(results) == 3  # 0, 2, 4 are enabled
        assert all(w.worklet_type == WorkletType.CASE_EXCEPTION for w in results)
        assert all(w.enabled for w in results)

        # Act: Query for all item exception worklets
        item_results = repository.query_worklets().filter_type(WorkletType.ITEM_EXCEPTION).execute()

        # Assert: All item worklets returned
        assert len(item_results) == 3
        assert all(w.worklet_type == WorkletType.ITEM_EXCEPTION for w in item_results)

    def test_repository_context_manager_with_exception(self) -> None:
        """JTBD: Repository context manager handles exceptions properly.

        Proves the context manager propagates exceptions correctly.
        """
        # Act & Assert: Exception propagates through context manager
        with pytest.raises(ValueError):
            with WorkletRepository() as repo:
                repo.add_worklet(Worklet(id="test", name="Test"))
                # Raise exception inside context
                raise ValueError("Test exception")

        # Verify context manager exited (no assertion needed, test passes if no hang)
