"""Tests for YAWL client data models.

Tests YSpecVersion, YSpecificationID, RunningCase, and other models
matching Java's data shape semantics.

Java Parity:
    - YSpecVersion.java: Major.minor version with comparison
    - YSpecificationID.java: identifier + version + uri
    - RunningCase.java: Spec ID + Case ID tuple with getters
"""

import pytest

from kgcl.yawl.clients.models import ChainedCase, PiledTask, RunningCase, UploadResult, YSpecificationID, YSpecVersion


class TestYSpecVersion:
    """Tests for YSpecVersion matching Java YSpecVersion.java."""

    def test_default_version_is_0_1(self) -> None:
        """Default version is 0.1 (Java parity)."""
        v = YSpecVersion()
        assert v.major == 0
        assert v.minor == 1
        assert str(v) == "0.1"

    def test_create_with_major_minor(self) -> None:
        """Can create with major and minor parts."""
        v = YSpecVersion(5, 12)
        assert v.major == 5
        assert v.minor == 12
        assert str(v) == "5.12"

    def test_from_string_with_dot(self) -> None:
        """Parse version from dotted string."""
        v = YSpecVersion.from_string("3.7")
        assert v.major == 3
        assert v.minor == 7

    def test_from_string_without_dot(self) -> None:
        """Parse version from integer string (Java parity)."""
        v = YSpecVersion.from_string("2")
        assert v.major == 2
        assert v.minor == 0  # Java: _minor = _major == 0 ? 1 : 0

    def test_from_string_zero_without_dot(self) -> None:
        """Parse '0' gives 0.1 (Java parity)."""
        v = YSpecVersion.from_string("0")
        assert v.major == 0
        assert v.minor == 1

    def test_from_string_none_gives_default(self) -> None:
        """Parse None gives default 0.1 (Java parity)."""
        v = YSpecVersion.from_string(None)
        assert v.major == 0
        assert v.minor == 1

    def test_from_string_invalid_gives_default(self) -> None:
        """Parse invalid string gives default 0.1 (Java parity)."""
        v = YSpecVersion.from_string("invalid")
        assert v.major == 0
        assert v.minor == 1

    def test_to_double(self) -> None:
        """to_double() returns float (legacy Java method)."""
        v = YSpecVersion(1, 5)
        assert v.to_double() == 1.5

    def test_minor_increment(self) -> None:
        """minor_increment() increments minor and returns string."""
        v = YSpecVersion(1, 0)
        result = v.minor_increment()
        assert result == "1.1"
        assert v.minor == 1

    def test_major_increment(self) -> None:
        """major_increment() increments major and returns string."""
        v = YSpecVersion(1, 5)
        result = v.major_increment()
        assert result == "2.5"
        assert v.major == 2

    def test_minor_rollback(self) -> None:
        """minor_rollback() decrements minor and returns string."""
        v = YSpecVersion(1, 5)
        result = v.minor_rollback()
        assert result == "1.4"
        assert v.minor == 4

    def test_major_rollback(self) -> None:
        """major_rollback() decrements major and returns string."""
        v = YSpecVersion(2, 0)
        result = v.major_rollback()
        assert result == "1.0"
        assert v.major == 1

    def test_equality(self) -> None:
        """Versions with same major.minor are equal."""
        v1 = YSpecVersion(1, 5)
        v2 = YSpecVersion(1, 5)
        assert v1 == v2

    def test_inequality(self) -> None:
        """Versions with different major or minor are not equal."""
        v1 = YSpecVersion(1, 5)
        v2 = YSpecVersion(1, 6)
        v3 = YSpecVersion(2, 5)
        assert v1 != v2
        assert v1 != v3

    def test_comparison_by_major(self) -> None:
        """Versions compare by major first."""
        v1 = YSpecVersion(1, 9)
        v2 = YSpecVersion(2, 0)
        assert v1 < v2
        assert v2 > v1

    def test_comparison_by_minor(self) -> None:
        """Versions with same major compare by minor."""
        v1 = YSpecVersion(1, 5)
        v2 = YSpecVersion(1, 6)
        assert v1 < v2
        assert v2 > v1

    def test_equals_major_version(self) -> None:
        """equals_major_version() checks major only."""
        v1 = YSpecVersion(1, 5)
        v2 = YSpecVersion(1, 9)
        v3 = YSpecVersion(2, 5)
        assert v1.equals_major_version(v2)
        assert not v1.equals_major_version(v3)

    def test_equals_minor_version(self) -> None:
        """equals_minor_version() checks minor only."""
        v1 = YSpecVersion(1, 5)
        v2 = YSpecVersion(2, 5)
        v3 = YSpecVersion(1, 6)
        assert v1.equals_minor_version(v2)
        assert not v1.equals_minor_version(v3)

    def test_hash(self) -> None:
        """Versions with same value have same hash."""
        v1 = YSpecVersion(1, 5)
        v2 = YSpecVersion(1, 5)
        assert hash(v1) == hash(v2)


class TestYSpecificationID:
    """Tests for YSpecificationID matching Java YSpecificationID.java."""

    def test_create_with_identifier_only(self) -> None:
        """Can create with just identifier."""
        spec_id = YSpecificationID("my-spec")
        assert spec_id.identifier == "my-spec"
        assert spec_id.get_identifier() == "my-spec"

    def test_create_with_string_version(self) -> None:
        """String version is converted to YSpecVersion."""
        spec_id = YSpecificationID("my-spec", "1.5")
        assert isinstance(spec_id.version, YSpecVersion)
        assert spec_id.get_version_as_string() == "1.5"

    def test_create_with_yspec_version_object(self) -> None:
        """Can create with YSpecVersion object directly."""
        version = YSpecVersion(2, 3)
        spec_id = YSpecificationID("my-spec", version)
        assert spec_id.version == version
        assert spec_id.get_version_as_string() == "2.3"

    def test_get_identifier_java_parity(self) -> None:
        """get_identifier() returns identifier (Java parity)."""
        spec_id = YSpecificationID("spec-001", "1.0", "http://example.com")
        assert spec_id.get_identifier() == "spec-001"

    def test_get_version_as_string_java_parity(self) -> None:
        """get_version_as_string() returns version string (Java parity)."""
        spec_id = YSpecificationID("spec-001", "2.5")
        assert spec_id.get_version_as_string() == "2.5"

    def test_get_uri_java_parity(self) -> None:
        """get_uri() returns URI (Java parity)."""
        spec_id = YSpecificationID("spec-001", "1.0", "http://example.com/spec")
        assert spec_id.get_uri() == "http://example.com/spec"

    def test_str_with_uri(self) -> None:
        """String representation includes URI when present."""
        spec_id = YSpecificationID("spec-001", "1.0", "http://example.com")
        assert "spec-001" in str(spec_id)
        assert "1.0" in str(spec_id)
        assert "http://example.com" in str(spec_id)

    def test_str_without_uri(self) -> None:
        """String representation without URI."""
        spec_id = YSpecificationID("spec-001", "1.0")
        result = str(spec_id)
        assert "spec-001" in result
        assert "1.0" in result

    def test_frozen_dataclass(self) -> None:
        """YSpecificationID is frozen (immutable)."""
        spec_id = YSpecificationID("spec-001", "1.0")
        with pytest.raises(AttributeError):
            spec_id.identifier = "new-id"  # type: ignore[misc]

    def test_from_xml(self) -> None:
        """Can parse from XML string."""
        xml = '<spec id="spec-001" version="2.0" uri="http://test.com"/>'
        spec_id = YSpecificationID.from_xml(xml)
        assert spec_id.identifier == "spec-001"
        assert spec_id.get_version_as_string() == "2.0"
        assert spec_id.uri == "http://test.com"


class TestRunningCase:
    """Tests for RunningCase matching Java RunningCase.java."""

    def test_create_with_spec_and_case(self) -> None:
        """Can create with spec_id and case_id."""
        spec_id = YSpecificationID("spec-001", "1.0", "MySpec")
        case = RunningCase(spec_id=spec_id, case_id="case-12345")
        assert case.spec_id == spec_id
        assert case.case_id == "case-12345"

    def test_get_case_id_java_parity(self) -> None:
        """get_case_id() returns case ID (Java parity)."""
        spec_id = YSpecificationID("spec-001", "1.0", "MySpec")
        case = RunningCase(spec_id=spec_id, case_id="case-12345")
        assert case.get_case_id() == "case-12345"

    def test_get_spec_name_java_parity(self) -> None:
        """get_spec_name() returns URI (Java parity: _specID.getUri())."""
        spec_id = YSpecificationID("spec-001", "1.0", "MySpecName")
        case = RunningCase(spec_id=spec_id, case_id="case-12345")
        assert case.get_spec_name() == "MySpecName"

    def test_get_spec_version_java_parity(self) -> None:
        """get_spec_version() returns version string (Java parity)."""
        spec_id = YSpecificationID("spec-001", "2.5", "MySpec")
        case = RunningCase(spec_id=spec_id, case_id="case-12345")
        assert case.get_spec_version() == "2.5"

    def test_str_representation(self) -> None:
        """String representation is readable."""
        spec_id = YSpecificationID("spec-001", "1.0")
        case = RunningCase(spec_id=spec_id, case_id="case-12345")
        result = str(case)
        assert "case-12345" in result

    def test_frozen_dataclass(self) -> None:
        """RunningCase is frozen (immutable)."""
        spec_id = YSpecificationID("spec-001")
        case = RunningCase(spec_id=spec_id, case_id="case-001")
        with pytest.raises(AttributeError):
            case.case_id = "new-id"  # type: ignore[misc]


class TestPiledTask:
    """Tests for PiledTask matching Java PiledTask.java."""

    def test_create_with_spec_and_task(self) -> None:
        """Can create with spec_id and task_id."""
        spec_id = YSpecificationID("spec-001", "1.0", "MySpec")
        piled = PiledTask(spec_id=spec_id, task_id="Task_A")
        assert piled.spec_id == spec_id
        assert piled.task_id == "Task_A"

    def test_str_format_matches_java(self) -> None:
        """String format: 'uri v.version :: taskID' (Java parity)."""
        spec_id = YSpecificationID("spec-001", "1.0", "MySpec")
        piled = PiledTask(spec_id=spec_id, task_id="Task_A")
        result = str(piled)
        assert "MySpec" in result
        assert "Task_A" in result
        assert "::" in result


class TestChainedCase:
    """Tests for ChainedCase matching Java ChainedCase.java."""

    def test_create_with_spec_and_case(self) -> None:
        """Can create with spec_id and case_id."""
        spec_id = YSpecificationID("spec-001", "1.0", "MySpec")
        chained = ChainedCase(spec_id=spec_id, case_id="case-123")
        assert chained.spec_id == spec_id
        assert chained.case_id == "case-123"

    def test_str_format_matches_java(self) -> None:
        """String format: 'caseID :: uri v.version' (Java parity)."""
        spec_id = YSpecificationID("spec-001", "1.0", "MySpec")
        chained = ChainedCase(spec_id=spec_id, case_id="case-123")
        result = str(chained)
        assert "case-123" in result
        assert "MySpec" in result
        assert "::" in result


class TestUploadResult:
    """Tests for UploadResult."""

    def test_successful_when_specs_and_no_errors(self) -> None:
        """successful is True when specs present and no errors."""
        result = UploadResult(specifications=[YSpecificationID("spec-001")], errors=[])
        assert result.successful is True

    def test_not_successful_when_errors(self) -> None:
        """successful is False when errors present."""
        result = UploadResult(specifications=[YSpecificationID("spec-001")], errors=["Some error"])
        assert result.successful is False

    def test_not_successful_when_no_specs(self) -> None:
        """successful is False when no specs uploaded."""
        result = UploadResult(specifications=[], errors=[])
        assert result.successful is False

    def test_from_xml_success(self) -> None:
        """Can parse success XML response."""
        xml = '<response><specification id="spec-001" version="1.0"/></response>'
        result = UploadResult.from_xml(xml)
        assert len(result.specifications) == 1
        assert result.specifications[0].identifier == "spec-001"

    def test_from_xml_failure(self) -> None:
        """Can parse failure XML response."""
        xml = "<failure>Invalid specification format</failure>"
        result = UploadResult.from_xml(xml)
        assert len(result.errors) == 1
