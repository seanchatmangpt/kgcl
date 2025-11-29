"""Tests for PiledTask data model."""

import pytest

from kgcl.yawl_ui.models.case import SpecificationID
from kgcl.yawl_ui.models.task import PiledTask


class TestPiledTask:
    """Test suite for PiledTask."""

    def test_creation(self) -> None:
        """Test creating a PiledTask."""
        spec_id = SpecificationID(uri="OrderProcess", version="1.0")
        task = PiledTask(spec_id=spec_id, task_id="ApproveOrder")

        assert task.spec_id == spec_id
        assert task.task_id == "ApproveOrder"

    def test_str_representation(self) -> None:
        """Test string representation of PiledTask."""
        spec_id = SpecificationID(uri="OrderProcess", version="1.0")
        task = PiledTask(spec_id=spec_id, task_id="ApproveOrder")

        result = str(task)

        assert result == "OrderProcess v.1.0 :: ApproveOrder"

    def test_str_with_different_version(self) -> None:
        """Test string representation with different version."""
        spec_id = SpecificationID(uri="PaymentFlow", version="2.5")
        task = PiledTask(spec_id=spec_id, task_id="ProcessPayment")

        result = str(task)

        assert result == "PaymentFlow v.2.5 :: ProcessPayment"

    def test_str_with_complex_task_id(self) -> None:
        """Test string representation with complex task ID."""
        spec_id = SpecificationID(uri="SupplyChain", version="3.0")
        task = PiledTask(spec_id=spec_id, task_id="Validate_Supplier_Credentials")

        result = str(task)

        assert result == "SupplyChain v.3.0 :: Validate_Supplier_Credentials"

    def test_frozen(self) -> None:
        """Test that PiledTask is frozen (immutable)."""
        spec_id = SpecificationID(uri="OrderProcess", version="1.0")
        task = PiledTask(spec_id=spec_id, task_id="ApproveOrder")

        with pytest.raises(AttributeError):
            task.task_id = "RejectOrder"  # type: ignore[misc]

    def test_multiple_tasks_same_spec(self) -> None:
        """Test multiple tasks from same specification."""
        spec_id = SpecificationID(uri="OrderProcess", version="1.0")

        task1 = PiledTask(spec_id=spec_id, task_id="ApproveOrder")
        task2 = PiledTask(spec_id=spec_id, task_id="ShipOrder")

        assert task1.spec_id == task2.spec_id
        assert task1.task_id != task2.task_id
        assert str(task1) == "OrderProcess v.1.0 :: ApproveOrder"
        assert str(task2) == "OrderProcess v.1.0 :: ShipOrder"
