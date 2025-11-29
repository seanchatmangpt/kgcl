"""Tests for UploadResult data model."""

import pytest

from kgcl.yawl_ui.models.case import SpecificationID
from kgcl.yawl_ui.models.upload import UploadResult


class TestUploadResult:
    """Test suite for UploadResult."""

    def test_empty_creation(self) -> None:
        """Test creating an empty UploadResult."""
        result = UploadResult()

        assert result.specs == []
        assert result.warnings == []
        assert result.errors == []

    def test_creation_with_specs_only(self) -> None:
        """Test creating UploadResult with specifications only."""
        spec = SpecificationID(uri="OrderProcess", version="1.0")
        result = UploadResult(specs=[spec])

        assert len(result.specs) == 1
        assert result.specs[0] == spec
        assert result.warnings == []
        assert result.errors == []

    def test_creation_with_warnings(self) -> None:
        """Test creating UploadResult with warnings."""
        result = UploadResult(warnings=["Minor validation issue"])

        assert result.specs == []
        assert len(result.warnings) == 1
        assert result.warnings[0] == "Minor validation issue"
        assert result.errors == []

    def test_creation_with_errors(self) -> None:
        """Test creating UploadResult with errors."""
        result = UploadResult(errors=["Critical validation failure"])

        assert result.specs == []
        assert result.warnings == []
        assert len(result.errors) == 1
        assert result.errors[0] == "Critical validation failure"

    def test_creation_with_all_fields(self) -> None:
        """Test creating UploadResult with all fields populated."""
        spec1 = SpecificationID(uri="OrderProcess", version="1.0")
        spec2 = SpecificationID(uri="PaymentFlow", version="2.0")

        result = UploadResult(specs=[spec1, spec2], warnings=["Warning 1", "Warning 2"], errors=["Error 1"])

        assert len(result.specs) == 2
        assert len(result.warnings) == 2
        assert len(result.errors) == 1

    def test_has_warnings_true(self) -> None:
        """Test has_warnings returns True when warnings present."""
        result = UploadResult(warnings=["Warning"])

        assert result.has_warnings() is True

    def test_has_warnings_false(self) -> None:
        """Test has_warnings returns False when no warnings."""
        result = UploadResult()

        assert result.has_warnings() is False

    def test_has_errors_true(self) -> None:
        """Test has_errors returns True when errors present."""
        result = UploadResult(errors=["Error"])

        assert result.has_errors() is True

    def test_has_errors_false(self) -> None:
        """Test has_errors returns False when no errors."""
        result = UploadResult()

        assert result.has_errors() is False

    def test_has_messages_with_warnings(self) -> None:
        """Test has_messages returns True when warnings present."""
        result = UploadResult(warnings=["Warning"])

        assert result.has_messages() is True

    def test_has_messages_with_errors(self) -> None:
        """Test has_messages returns True when errors present."""
        result = UploadResult(errors=["Error"])

        assert result.has_messages() is True

    def test_has_messages_with_both(self) -> None:
        """Test has_messages returns True when both warnings and errors."""
        result = UploadResult(warnings=["Warning"], errors=["Error"])

        assert result.has_messages() is True

    def test_has_messages_false(self) -> None:
        """Test has_messages returns False when no messages."""
        result = UploadResult()

        assert result.has_messages() is False

    def test_has_spec_ids_true(self) -> None:
        """Test has_spec_ids returns True when specs present."""
        spec = SpecificationID(uri="OrderProcess", version="1.0")
        result = UploadResult(specs=[spec])

        assert result.has_spec_ids() is True

    def test_has_spec_ids_false(self) -> None:
        """Test has_spec_ids returns False when no specs."""
        result = UploadResult()

        assert result.has_spec_ids() is False

    def test_get_warnings(self) -> None:
        """Test getting warnings list."""
        warnings = ["Warning 1", "Warning 2"]
        result = UploadResult(warnings=warnings)

        retrieved = result.get_warnings()

        assert retrieved == warnings
        assert retrieved is not result.warnings  # Returns copy

    def test_get_errors(self) -> None:
        """Test getting errors list."""
        errors = ["Error 1", "Error 2"]
        result = UploadResult(errors=errors)

        retrieved = result.get_errors()

        assert retrieved == errors
        assert retrieved is not result.errors  # Returns copy

    def test_get_spec_ids(self) -> None:
        """Test getting specification IDs list."""
        spec1 = SpecificationID(uri="OrderProcess", version="1.0")
        spec2 = SpecificationID(uri="PaymentFlow", version="2.0")
        result = UploadResult(specs=[spec1, spec2])

        retrieved = result.get_spec_ids()

        assert retrieved == [spec1, spec2]
        assert retrieved is not result.specs  # Returns copy

    def test_frozen(self) -> None:
        """Test that UploadResult is frozen (immutable)."""
        result = UploadResult(warnings=["Warning"])

        with pytest.raises(AttributeError):
            result.warnings = []  # type: ignore[misc]

    def test_successful_upload_scenario(self) -> None:
        """Test scenario: successful upload with specs."""
        spec = SpecificationID(uri="OrderProcess", version="1.0")
        result = UploadResult(specs=[spec])

        assert result.has_spec_ids() is True
        assert result.has_warnings() is False
        assert result.has_errors() is False
        assert result.has_messages() is False

    def test_failed_upload_scenario(self) -> None:
        """Test scenario: failed upload with errors, no specs."""
        result = UploadResult(errors=["Invalid XML structure", "Missing required elements"])

        assert result.has_spec_ids() is False
        assert result.has_warnings() is False
        assert result.has_errors() is True
        assert result.has_messages() is True

    def test_partial_success_scenario(self) -> None:
        """Test scenario: upload succeeded but with warnings."""
        spec = SpecificationID(uri="OrderProcess", version="1.0")
        result = UploadResult(specs=[spec], warnings=["Deprecated syntax used", "Missing documentation"])

        assert result.has_spec_ids() is True
        assert result.has_warnings() is True
        assert result.has_errors() is False
        assert result.has_messages() is True
