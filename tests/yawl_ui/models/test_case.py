"""Tests for case data models."""

import pytest

from kgcl.yawl_ui.models.case import ChainedCase, RunningCase, SpecificationID


class TestSpecificationID:
    """Test suite for SpecificationID."""

    def test_creation(self) -> None:
        """Test creating a SpecificationID."""
        spec_id = SpecificationID(uri="OrderProcess", version="1.0")

        assert spec_id.uri == "OrderProcess"
        assert spec_id.version == "1.0"
        assert spec_id.identifier is None

    def test_creation_with_identifier(self) -> None:
        """Test creating a SpecificationID with identifier."""
        spec_id = SpecificationID(uri="OrderProcess", version="1.0", identifier="spec-001")

        assert spec_id.uri == "OrderProcess"
        assert spec_id.version == "1.0"
        assert spec_id.identifier == "spec-001"

    def test_get_version_as_string(self) -> None:
        """Test getting version as string."""
        spec_id = SpecificationID(uri="OrderProcess", version="2.5")

        assert spec_id.get_version_as_string() == "2.5"

    def test_frozen(self) -> None:
        """Test that SpecificationID is frozen (immutable)."""
        spec_id = SpecificationID(uri="OrderProcess", version="1.0")

        with pytest.raises(AttributeError):
            spec_id.uri = "NewProcess"  # type: ignore[misc]


class TestChainedCase:
    """Test suite for ChainedCase."""

    def test_creation(self) -> None:
        """Test creating a ChainedCase."""
        spec_id = SpecificationID(uri="OrderProcess", version="1.0")
        case = ChainedCase(spec_id=spec_id, case_id="case-001")

        assert case.spec_id == spec_id
        assert case.case_id == "case-001"

    def test_str_representation(self) -> None:
        """Test string representation of ChainedCase."""
        spec_id = SpecificationID(uri="OrderProcess", version="1.0")
        case = ChainedCase(spec_id=spec_id, case_id="case-001")

        result = str(case)

        assert result == "case-001 :: OrderProcess v.1.0"

    def test_str_with_different_version(self) -> None:
        """Test string representation with different version."""
        spec_id = SpecificationID(uri="PaymentFlow", version="2.5")
        case = ChainedCase(spec_id=spec_id, case_id="case-999")

        result = str(case)

        assert result == "case-999 :: PaymentFlow v.2.5"

    def test_frozen(self) -> None:
        """Test that ChainedCase is frozen (immutable)."""
        spec_id = SpecificationID(uri="OrderProcess", version="1.0")
        case = ChainedCase(spec_id=spec_id, case_id="case-001")

        with pytest.raises(AttributeError):
            case.case_id = "case-002"  # type: ignore[misc]


class TestRunningCase:
    """Test suite for RunningCase."""

    def test_creation(self) -> None:
        """Test creating a RunningCase."""
        spec_id = SpecificationID(uri="OrderProcess", version="1.0")
        case = RunningCase(spec_id=spec_id, case_id="case-001")

        assert case.spec_id == spec_id
        assert case.case_id == "case-001"

    def test_get_case_id(self) -> None:
        """Test getting case ID."""
        spec_id = SpecificationID(uri="OrderProcess", version="1.0")
        case = RunningCase(spec_id=spec_id, case_id="case-001")

        assert case.get_case_id() == "case-001"

    def test_get_spec_name(self) -> None:
        """Test getting specification name."""
        spec_id = SpecificationID(uri="OrderProcess", version="1.0")
        case = RunningCase(spec_id=spec_id, case_id="case-001")

        assert case.get_spec_name() == "OrderProcess"

    def test_get_spec_version(self) -> None:
        """Test getting specification version."""
        spec_id = SpecificationID(uri="OrderProcess", version="1.0")
        case = RunningCase(spec_id=spec_id, case_id="case-001")

        assert case.get_spec_version() == "1.0"

    def test_all_accessors(self) -> None:
        """Test all accessor methods together."""
        spec_id = SpecificationID(uri="PaymentFlow", version="2.5")
        case = RunningCase(spec_id=spec_id, case_id="case-999")

        assert case.get_case_id() == "case-999"
        assert case.get_spec_name() == "PaymentFlow"
        assert case.get_spec_version() == "2.5"

    def test_frozen(self) -> None:
        """Test that RunningCase is frozen (immutable)."""
        spec_id = SpecificationID(uri="OrderProcess", version="1.0")
        case = RunningCase(spec_id=spec_id, case_id="case-001")

        with pytest.raises(AttributeError):
            case.case_id = "case-002"  # type: ignore[misc]
