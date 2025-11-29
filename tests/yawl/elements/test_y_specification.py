"""Tests for YSpecification - mirrors TestYSpecification.java.

Verifies specification creation, net management, and validation.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from kgcl.yawl.elements.y_condition import ConditionType, YCondition
from kgcl.yawl.elements.y_flow import YFlow
from kgcl.yawl.elements.y_net import YNet
from kgcl.yawl.elements.y_specification import SpecificationStatus, YMetaData, YSpecification, YSpecificationVersion
from kgcl.yawl.elements.y_task import YTask


def build_valid_net(net_id: str = "main") -> YNet:
    """Build a valid net for testing."""
    net = YNet(id=net_id)
    start = YCondition(id="start", condition_type=ConditionType.INPUT)
    end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
    task = YTask(id="A")

    net.add_condition(start)
    net.add_condition(end)
    net.add_task(task)
    net.add_flow(YFlow(id="f1", source_id="start", target_id="A"))
    net.add_flow(YFlow(id="f2", source_id="A", target_id="end"))

    return net


class TestSpecificationVersion:
    """Tests for version management."""

    def test_create_version(self) -> None:
        """Create version with defaults."""
        version = YSpecificationVersion()

        assert version.major == 0
        assert version.minor == 1
        assert version.build == ""

    def test_version_string(self) -> None:
        """Version string formatting."""
        version = YSpecificationVersion(major=1, minor=2)

        assert str(version) == "1.2"

    def test_version_with_build(self) -> None:
        """Version string with build."""
        version = YSpecificationVersion(major=1, minor=0, build="beta1")

        assert str(version) == "1.0.beta1"

    def test_version_comparison(self) -> None:
        """Version comparison."""
        v1 = YSpecificationVersion(major=1, minor=0)
        v2 = YSpecificationVersion(major=1, minor=1)
        v3 = YSpecificationVersion(major=2, minor=0)

        assert v1 < v2
        assert v2 < v3
        assert v1 < v3


class TestMetaData:
    """Tests for specification metadata."""

    def test_create_metadata(self) -> None:
        """Create metadata with defaults."""
        meta = YMetaData()

        assert meta.title == ""
        assert meta.creator == ""
        assert meta.created is not None
        assert meta.persistent is True

    def test_metadata_fields(self) -> None:
        """Set metadata fields."""
        meta = YMetaData(
            title="Order Processing",
            creator="John Doe",
            description="Handles customer orders",
            subject="workflow, orders",
        )

        assert meta.title == "Order Processing"
        assert meta.creator == "John Doe"
        assert meta.description == "Handles customer orders"
        assert meta.subject == "workflow, orders"

    def test_metadata_validity(self) -> None:
        """Metadata validity period."""
        valid_from = datetime(2024, 1, 1)
        valid_until = datetime(2024, 12, 31)

        meta = YMetaData(title="Seasonal", valid_from=valid_from, valid_until=valid_until)

        assert meta.valid_from == valid_from
        assert meta.valid_until == valid_until


class TestSpecificationCreation:
    """Tests for specification creation."""

    def test_create_specification(self) -> None:
        """Create specification with ID."""
        spec = YSpecification(id="urn:example:order-process")

        assert spec.id == "urn:example:order-process"
        assert spec.name == ""
        assert spec.status == SpecificationStatus.EDITING
        assert spec.root_net_id is None

    def test_create_with_name(self) -> None:
        """Create specification with name."""
        spec = YSpecification(id="urn:example:order", name="Order Processing")

        assert spec.name == "Order Processing"

    def test_specification_equality(self) -> None:
        """Specification equality by ID."""
        s1 = YSpecification(id="same")
        s2 = YSpecification(id="same")
        s3 = YSpecification(id="different")

        assert s1 == s2
        assert s1 != s3
        assert hash(s1) == hash(s2)


class TestNetManagement:
    """Tests for managing nets in specification."""

    def test_set_root_net(self) -> None:
        """Set root net."""
        spec = YSpecification(id="test")
        net = build_valid_net("main")

        spec.set_root_net(net)

        assert spec.root_net_id == "main"
        assert "main" in spec.nets

    def test_get_root_net(self) -> None:
        """Get root net."""
        spec = YSpecification(id="test")
        net = build_valid_net("main")
        spec.set_root_net(net)

        result = spec.get_root_net()

        assert result is net

    def test_get_root_net_none(self) -> None:
        """Get root net when not set."""
        spec = YSpecification(id="test")

        result = spec.get_root_net()

        assert result is None

    def test_add_net(self) -> None:
        """Add net to specification."""
        spec = YSpecification(id="test")
        net = build_valid_net("subnet")

        spec.add_net(net)

        assert "subnet" in spec.nets
        assert net.specification_id == "test"

    def test_get_net(self) -> None:
        """Get net by ID."""
        spec = YSpecification(id="test")
        net = build_valid_net("main")
        spec.add_net(net)

        result = spec.get_net("main")

        assert result is net

    def test_get_net_not_found(self) -> None:
        """Get nonexistent net returns None."""
        spec = YSpecification(id="test")

        result = spec.get_net("nonexistent")

        assert result is None


class TestDecompositionManagement:
    """Tests for decomposition management."""

    def test_net_added_as_decomposition(self) -> None:
        """Net is also added as decomposition."""
        spec = YSpecification(id="test")
        net = build_valid_net("main")

        spec.add_net(net)

        assert "main" in spec.decompositions

    def test_get_decomposition(self) -> None:
        """Get decomposition by ID."""
        spec = YSpecification(id="test")
        net = build_valid_net("main")
        spec.add_net(net)

        result = spec.get_decomposition("main")

        assert result is net


class TestDataTypeDefinitions:
    """Tests for custom data type definitions."""

    def test_add_data_type(self) -> None:
        """Add custom data type."""
        spec = YSpecification(id="test")

        spec.add_data_type_definition("OrderType", "<xs:complexType>...</xs:complexType>")

        assert "OrderType" in spec.data_type_definitions

    def test_get_data_type(self) -> None:
        """Get data type definition."""
        spec = YSpecification(id="test")
        spec.add_data_type_definition("Amount", "<xs:simpleType>...</xs:simpleType>")

        result = spec.get_data_type_definition("Amount")

        assert result is not None
        assert "simpleType" in result

    def test_get_unknown_data_type(self) -> None:
        """Get unknown data type returns None."""
        spec = YSpecification(id="test")

        result = spec.get_data_type_definition("Unknown")

        assert result is None


class TestTaskRetrieval:
    """Tests for retrieving tasks across nets."""

    def test_get_all_task_ids(self) -> None:
        """Get all task IDs from all nets."""
        spec = YSpecification(id="test")

        net1 = build_valid_net("net1")
        net1.add_task(YTask(id="B"))

        net2 = build_valid_net("net2")
        net2.add_task(YTask(id="C"))

        spec.add_net(net1)
        spec.add_net(net2)

        task_ids = spec.get_all_task_ids()

        # Each net has task "A" from build_valid_net, plus added tasks
        assert "A" in task_ids
        assert "B" in task_ids
        assert "C" in task_ids

    def test_get_task(self) -> None:
        """Get task by ID from any net."""
        spec = YSpecification(id="test")
        net = build_valid_net("main")
        spec.add_net(net)

        task = spec.get_task("A")

        assert task is not None
        assert task.id == "A"

    def test_get_task_not_found(self) -> None:
        """Get unknown task returns None."""
        spec = YSpecification(id="test")
        net = build_valid_net("main")
        spec.add_net(net)

        task = spec.get_task("Unknown")

        assert task is None


class TestSpecificationValidation:
    """Tests for specification validation."""

    def test_valid_specification(self) -> None:
        """Valid specification passes validation."""
        spec = YSpecification(id="test")
        net = build_valid_net("main")
        spec.set_root_net(net)

        is_valid, errors = spec.is_valid()

        assert is_valid
        assert len(errors) == 0

    def test_invalid_no_root_net(self) -> None:
        """Specification without root net is invalid."""
        spec = YSpecification(id="test")

        is_valid, errors = spec.is_valid()

        assert not is_valid
        assert any("root net" in e.lower() for e in errors)

    def test_invalid_root_net_not_found(self) -> None:
        """Specification with missing root net is invalid."""
        spec = YSpecification(id="test")
        spec.root_net_id = "missing"

        is_valid, errors = spec.is_valid()

        assert not is_valid
        assert any("not found" in e.lower() for e in errors)

    def test_invalid_root_net_structure(self) -> None:
        """Specification with invalid root net is invalid."""
        spec = YSpecification(id="test")
        net = YNet(id="invalid")  # No input/output/tasks
        spec.set_root_net(net)

        is_valid, errors = spec.is_valid()

        assert not is_valid
        assert any("invalid" in e.lower() for e in errors)


class TestSpecificationStatus:
    """Tests for specification status management."""

    def test_default_status(self) -> None:
        """Default status is EDITING."""
        spec = YSpecification(id="test")

        assert spec.status == SpecificationStatus.EDITING

    def test_activate(self) -> None:
        """Activate specification."""
        spec = YSpecification(id="test")

        spec.activate()

        assert spec.status == SpecificationStatus.ACTIVE
        assert spec.can_create_case()

    def test_suspend(self) -> None:
        """Suspend specification."""
        spec = YSpecification(id="test")
        spec.activate()

        spec.suspend()

        assert spec.status == SpecificationStatus.SUSPENDED
        assert not spec.can_create_case()

    def test_retire(self) -> None:
        """Retire specification."""
        spec = YSpecification(id="test")
        spec.activate()

        spec.retire()

        assert spec.status == SpecificationStatus.RETIRED
        assert not spec.can_create_case()

    def test_can_create_case(self) -> None:
        """Only active specifications can create cases."""
        spec = YSpecification(id="test")

        assert not spec.can_create_case()  # EDITING

        spec.activate()
        assert spec.can_create_case()

        spec.suspend()
        assert not spec.can_create_case()


class TestExtendedAttributes:
    """Tests for extended attributes."""

    def test_set_attribute(self) -> None:
        """Set extended attribute."""
        spec = YSpecification(id="test")

        spec.set_attribute("priority", "high")
        spec.set_attribute("department", "sales")

        assert spec.get_attribute("priority") == "high"
        assert spec.get_attribute("department") == "sales"

    def test_get_unknown_attribute(self) -> None:
        """Get unknown attribute returns None."""
        spec = YSpecification(id="test")

        result = spec.get_attribute("unknown")

        assert result is None


class TestSpecificationDocumentation:
    """Tests for specification documentation."""

    def test_documentation(self) -> None:
        """Set specification documentation."""
        spec = YSpecification(id="test", documentation="This workflow handles order processing.")

        assert "order processing" in spec.documentation

    def test_schema(self) -> None:
        """Specification has schema reference."""
        spec = YSpecification(id="test")

        assert "yawl" in spec.schema.lower()
