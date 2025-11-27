"""Tests for TaskStatus domain object.

Tests verify status enumeration, priority ordering, and status resolution.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.domain.task_status import TaskStatus


class TestTaskStatusValues:
    """Tests for TaskStatus enum values."""

    def test_active_value(self) -> None:
        """ACTIVE has correct string value."""
        assert TaskStatus.ACTIVE.value == "Active"

    def test_completed_value(self) -> None:
        """COMPLETED has correct string value."""
        assert TaskStatus.COMPLETED.value == "Completed"

    def test_archived_value(self) -> None:
        """ARCHIVED has correct string value."""
        assert TaskStatus.ARCHIVED.value == "Archived"

    def test_pending_value(self) -> None:
        """PENDING has correct string value."""
        assert TaskStatus.PENDING.value == "Pending"

    def test_cancelled_value(self) -> None:
        """CANCELLED has correct string value."""
        assert TaskStatus.CANCELLED.value == "Cancelled"


class TestTaskStatusPriority:
    """Tests for status priority ordering."""

    def test_pending_has_lowest_priority(self) -> None:
        """PENDING has priority 0."""
        assert TaskStatus.PENDING.priority == 0

    def test_active_priority(self) -> None:
        """ACTIVE has priority 1."""
        assert TaskStatus.ACTIVE.priority == 1

    def test_completed_priority(self) -> None:
        """COMPLETED has priority 2."""
        assert TaskStatus.COMPLETED.priority == 2

    def test_archived_priority(self) -> None:
        """ARCHIVED has priority 3."""
        assert TaskStatus.ARCHIVED.priority == 3

    def test_cancelled_has_highest_priority(self) -> None:
        """CANCELLED has priority 4 (highest)."""
        assert TaskStatus.CANCELLED.priority == 4

    def test_priority_ordering(self) -> None:
        """Status priorities follow lifecycle progression."""
        assert TaskStatus.PENDING.priority < TaskStatus.ACTIVE.priority
        assert TaskStatus.ACTIVE.priority < TaskStatus.COMPLETED.priority
        assert TaskStatus.COMPLETED.priority < TaskStatus.ARCHIVED.priority
        assert TaskStatus.ARCHIVED.priority < TaskStatus.CANCELLED.priority


class TestTaskStatusFromString:
    """Tests for from_string factory method."""

    def test_from_string_active(self) -> None:
        """from_string parses 'Active'."""
        status = TaskStatus.from_string("Active")
        assert status == TaskStatus.ACTIVE

    def test_from_string_completed(self) -> None:
        """from_string parses 'Completed'."""
        status = TaskStatus.from_string("Completed")
        assert status == TaskStatus.COMPLETED

    def test_from_string_archived(self) -> None:
        """from_string parses 'Archived'."""
        status = TaskStatus.from_string("Archived")
        assert status == TaskStatus.ARCHIVED

    def test_from_string_unknown_raises(self) -> None:
        """from_string raises ValueError for unknown status."""
        with pytest.raises(ValueError, match="Unknown task status"):
            TaskStatus.from_string("Unknown")


class TestTaskStatusHighestPriority:
    """Tests for highest_priority class method."""

    def test_highest_priority_single_status(self) -> None:
        """Single status returns itself."""
        result = TaskStatus.highest_priority(["Active"])
        assert result == "Active"

    def test_highest_priority_active_vs_completed(self) -> None:
        """Completed wins over Active."""
        result = TaskStatus.highest_priority(["Active", "Completed"])
        assert result == "Completed"

    def test_highest_priority_multiple_statuses(self) -> None:
        """Archived wins over Active and Completed."""
        result = TaskStatus.highest_priority(["Active", "Completed", "Archived"])
        assert result == "Archived"

    def test_highest_priority_cancelled_wins(self) -> None:
        """Cancelled wins over all other statuses."""
        result = TaskStatus.highest_priority(["Active", "Completed", "Archived", "Cancelled"])
        assert result == "Cancelled"

    def test_highest_priority_empty_raises(self) -> None:
        """Empty list raises ValueError."""
        with pytest.raises(ValueError, match="empty list"):
            TaskStatus.highest_priority([])

    def test_highest_priority_order_independent(self) -> None:
        """Result is same regardless of input order."""
        result1 = TaskStatus.highest_priority(["Active", "Completed"])
        result2 = TaskStatus.highest_priority(["Completed", "Active"])
        assert result1 == result2 == "Completed"

    def test_highest_priority_unknown_status(self) -> None:
        """Unknown statuses get priority 0, known statuses win."""
        result = TaskStatus.highest_priority(["Unknown", "Active"])
        assert result == "Active"

    def test_highest_priority_all_unknown(self) -> None:
        """All unknown statuses returns first one."""
        result = TaskStatus.highest_priority(["Unknown1", "Unknown2"])
        assert result in ["Unknown1", "Unknown2"]  # Implementation-dependent
