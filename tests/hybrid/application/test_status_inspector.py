"""Tests for StatusInspector application service.

Tests verify status querying and priority resolution.
"""

from __future__ import annotations

from kgcl.hybrid.adapters.oxigraph_adapter import OxigraphAdapter
from kgcl.hybrid.application.status_inspector import StatusInspector


class TestStatusInspectorGetTaskStatuses:
    """Tests for getting task statuses."""

    def test_empty_store_returns_empty_dict(self) -> None:
        """Empty store returns empty status dict."""
        store = OxigraphAdapter()
        inspector = StatusInspector(store)

        statuses = inspector.get_task_statuses()

        assert statuses == {}

    def test_single_task_status(self) -> None:
        """Single task returns its status."""
        store = OxigraphAdapter()
        store.load_turtle("""
            @prefix kgc: <https://kgc.org/ns/> .
            <urn:task:A> kgc:status "Active" .
        """)
        inspector = StatusInspector(store)

        statuses = inspector.get_task_statuses()

        assert statuses["urn:task:A"] == "Active"

    def test_multiple_tasks(self) -> None:
        """Multiple tasks each return their status."""
        store = OxigraphAdapter()
        store.load_turtle("""
            @prefix kgc: <https://kgc.org/ns/> .
            <urn:task:A> kgc:status "Active" .
            <urn:task:B> kgc:status "Completed" .
            <urn:task:C> kgc:status "Pending" .
        """)
        inspector = StatusInspector(store)

        statuses = inspector.get_task_statuses()

        assert statuses["urn:task:A"] == "Active"
        assert statuses["urn:task:B"] == "Completed"
        assert statuses["urn:task:C"] == "Pending"

    def test_monotonic_status_resolution(self) -> None:
        """Multiple statuses resolve to highest priority."""
        store = OxigraphAdapter()
        # Task has both Active and Completed status (monotonic accumulation)
        store.load_turtle("""
            @prefix kgc: <https://kgc.org/ns/> .
            <urn:task:A> kgc:status "Active" .
            <urn:task:A> kgc:status "Completed" .
        """)
        inspector = StatusInspector(store)

        statuses = inspector.get_task_statuses()

        # Completed has higher priority than Active
        assert statuses["urn:task:A"] == "Completed"


class TestStatusInspectorGetTasksByStatus:
    """Tests for filtering tasks by status."""

    def test_get_active_tasks(self) -> None:
        """get_tasks_by_status returns active tasks."""
        store = OxigraphAdapter()
        store.load_turtle("""
            @prefix kgc: <https://kgc.org/ns/> .
            <urn:task:A> kgc:status "Active" .
            <urn:task:B> kgc:status "Active" .
            <urn:task:C> kgc:status "Completed" .
        """)
        inspector = StatusInspector(store)

        active_tasks = inspector.get_tasks_by_status("Active")

        assert len(active_tasks) == 2
        assert "urn:task:A" in active_tasks
        assert "urn:task:B" in active_tasks
        assert "urn:task:C" not in active_tasks

    def test_get_completed_tasks(self) -> None:
        """get_tasks_by_status returns completed tasks."""
        store = OxigraphAdapter()
        store.load_turtle("""
            @prefix kgc: <https://kgc.org/ns/> .
            <urn:task:A> kgc:status "Active" .
            <urn:task:B> kgc:status "Completed" .
        """)
        inspector = StatusInspector(store)

        completed_tasks = inspector.get_tasks_by_status("Completed")

        assert len(completed_tasks) == 1
        assert "urn:task:B" in completed_tasks


class TestStatusInspectorConvenienceMethods:
    """Tests for convenience methods."""

    def test_get_active_tasks_method(self) -> None:
        """get_active_tasks returns Active tasks."""
        store = OxigraphAdapter()
        store.load_turtle("""
            @prefix kgc: <https://kgc.org/ns/> .
            <urn:task:A> kgc:status "Active" .
            <urn:task:B> kgc:status "Completed" .
        """)
        inspector = StatusInspector(store)

        active = inspector.get_active_tasks()

        assert "urn:task:A" in active
        assert "urn:task:B" not in active

    def test_get_completed_tasks_method(self) -> None:
        """get_completed_tasks returns Completed tasks."""
        store = OxigraphAdapter()
        store.load_turtle("""
            @prefix kgc: <https://kgc.org/ns/> .
            <urn:task:A> kgc:status "Active" .
            <urn:task:B> kgc:status "Completed" .
        """)
        inspector = StatusInspector(store)

        completed = inspector.get_completed_tasks()

        assert "urn:task:B" in completed


class TestStatusInspectorWorkflowComplete:
    """Tests for workflow completion checking."""

    def test_workflow_complete_all_archived(self) -> None:
        """Workflow complete when all tasks archived."""
        store = OxigraphAdapter()
        store.load_turtle("""
            @prefix kgc: <https://kgc.org/ns/> .
            <urn:task:A> kgc:status "Archived" .
            <urn:task:B> kgc:status "Archived" .
        """)
        inspector = StatusInspector(store)

        assert inspector.is_workflow_complete() is True

    def test_workflow_incomplete_with_active(self) -> None:
        """Workflow incomplete with active tasks."""
        store = OxigraphAdapter()
        store.load_turtle("""
            @prefix kgc: <https://kgc.org/ns/> .
            <urn:task:A> kgc:status "Active" .
            <urn:task:B> kgc:status "Completed" .
        """)
        inspector = StatusInspector(store)

        assert inspector.is_workflow_complete() is False

    def test_workflow_incomplete_with_pending(self) -> None:
        """Workflow incomplete with pending tasks."""
        store = OxigraphAdapter()
        store.load_turtle("""
            @prefix kgc: <https://kgc.org/ns/> .
            <urn:task:A> kgc:status "Completed" .
            <urn:task:B> kgc:status "Pending" .
        """)
        inspector = StatusInspector(store)

        assert inspector.is_workflow_complete() is False
