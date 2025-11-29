"""Data models for YAWL client operations.

This module provides data transfer objects matching Java's client models
including RunningCase, UploadResult, PiledTask, ChainedCase, etc.

Java Parity:
    - YSpecVersion.java: Major.minor version with comparison
    - YSpecificationID.java: identifier + version + uri
    - RunningCase.java: Spec ID + Case ID tuple
    - UploadResult: Parsed upload response
    - PiledTask.java: Spec ID + Task ID for piled tasks
    - ChainedCase.java: Spec ID + Case ID for chained cases
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from functools import total_ordering
from typing import Any
from xml.etree import ElementTree as ET


@total_ordering
@dataclass
class YSpecVersion:
    """Specification version (mirrors Java YSpecVersion).

    A simple version numbering implementation stored as a major part and a minor part
    (both int) but represented externally as a dotted String (eg 5.12).

    Parameters
    ----------
    major : int
        Major version number
    minor : int
        Minor version number

    Examples
    --------
    >>> v = YSpecVersion(1, 0)
    >>> str(v)
    '1.0'
    >>> v.minor_increment()
    '1.1'
    """

    major: int = 0
    minor: int = 1

    @classmethod
    def from_string(cls, version: str | None) -> YSpecVersion:
        """Parse version from string.

        Parameters
        ----------
        version : str | None
            Version string like "1.0" or "2"

        Returns
        -------
        YSpecVersion
            Parsed version object
        """
        if version is None:
            return cls(0, 1)

        try:
            if "." in version:
                parts = version.split(".")
                return cls(int(parts[0]), int(parts[1]))
            else:
                major = int(version)
                return cls(major, 1 if major == 0 else 0)
        except (ValueError, IndexError):
            return cls(0, 1)

    def __str__(self) -> str:
        """Return version as dotted string."""
        return f"{self.major}.{self.minor}"

    def __eq__(self, other: object) -> bool:
        """Check version equality."""
        if not isinstance(other, YSpecVersion):
            return NotImplemented
        return self.major == other.major and self.minor == other.minor

    def __lt__(self, other: object) -> bool:
        """Compare versions for ordering."""
        if not isinstance(other, YSpecVersion):
            return NotImplemented
        if self.major != other.major:
            return self.major < other.major
        return self.minor < other.minor

    def __hash__(self) -> int:
        """Return hash for version."""
        return (17 * self.major) * (31 * self.minor)

    def to_double(self) -> float:
        """Return version as double (legacy method).

        Returns
        -------
        float
            Version as floating point number
        """
        try:
            return float(str(self))
        except ValueError:
            return 0.1

    def minor_increment(self) -> str:
        """Increment minor version.

        Returns
        -------
        str
            New version string
        """
        self.minor += 1
        return str(self)

    def major_increment(self) -> str:
        """Increment major version.

        Returns
        -------
        str
            New version string
        """
        self.major += 1
        return str(self)

    def minor_rollback(self) -> str:
        """Decrement minor version.

        Returns
        -------
        str
            New version string
        """
        self.minor -= 1
        return str(self)

    def major_rollback(self) -> str:
        """Decrement major version.

        Returns
        -------
        str
            New version string
        """
        self.major -= 1
        return str(self)

    def equals_major_version(self, other: YSpecVersion) -> bool:
        """Check if major versions match.

        Parameters
        ----------
        other : YSpecVersion
            Version to compare

        Returns
        -------
        bool
            True if major versions equal
        """
        return self.major == other.major

    def equals_minor_version(self, other: YSpecVersion) -> bool:
        """Check if minor versions match.

        Parameters
        ----------
        other : YSpecVersion
            Version to compare

        Returns
        -------
        bool
            True if minor versions equal
        """
        return self.minor == other.minor


@dataclass(frozen=True)
class YSpecificationID:
    """Specification identifier (mirrors Java YSpecificationID).

    Parameters
    ----------
    identifier : str
        Unique specification identifier (UUID string in Java)
    version : YSpecVersion | str
        Specification version (accepts string for convenience)
    uri : str
        User-defined specification name/URI

    Examples
    --------
    >>> spec_id = YSpecificationID("my-spec", "1.0", "http://example.com/my-spec")
    >>> print(spec_id)
    my-spec v1.0 (http://example.com/my-spec)
    >>> spec_id.get_version_as_string()
    '1.0'
    """

    identifier: str
    version: YSpecVersion | str = field(default_factory=lambda: YSpecVersion(0, 1))
    uri: str = ""

    def __post_init__(self) -> None:
        """Convert string version to YSpecVersion if needed."""
        if isinstance(self.version, str):
            # Use object.__setattr__ since frozen=True
            object.__setattr__(self, "version", YSpecVersion.from_string(self.version))

    def __str__(self) -> str:
        """Return human-readable representation."""
        version_str = self.get_version_as_string()
        if self.uri:
            return f"{self.identifier} v{version_str} ({self.uri})"
        return f"{self.identifier} v{version_str}"

    def get_identifier(self) -> str:
        """Get identifier (Java parity method).

        Returns
        -------
        str
            The specification identifier
        """
        return self.identifier

    def get_version_as_string(self) -> str:
        """Get version as string (Java parity method).

        Returns
        -------
        str
            Version string like "1.0"
        """
        if isinstance(self.version, YSpecVersion):
            return str(self.version)
        return str(self.version)

    def get_uri(self) -> str:
        """Get URI (Java parity method).

        Returns
        -------
        str
            The specification URI
        """
        return self.uri

    @classmethod
    def from_xml(cls, xml_str: str) -> YSpecificationID:
        """Parse specification ID from XML.

        Parameters
        ----------
        xml_str : str
            XML string containing spec ID attributes

        Returns
        -------
        YSpecificationID
            Parsed specification ID
        """
        root = ET.fromstring(xml_str)
        return cls(identifier=root.get("id", ""), version=root.get("version", "0.1"), uri=root.get("uri", ""))


@dataclass(frozen=True)
class RunningCase:
    """Running case tuple (mirrors Java RunningCase).

    Parameters
    ----------
    spec_id : YSpecificationID
        Specification identifier
    case_id : str
        Running case identifier

    Examples
    --------
    >>> case = RunningCase(YSpecificationID("spec-001", "1.0", "MySpec"), "case-12345")
    >>> case.get_case_id()
    'case-12345'
    >>> case.get_spec_name()
    'MySpec'
    """

    spec_id: YSpecificationID
    case_id: str

    def __str__(self) -> str:
        """Return human-readable representation."""
        return f"Case {self.case_id} of {self.spec_id}"

    def get_case_id(self) -> str:
        """Get case ID (Java parity method).

        Returns
        -------
        str
            The case identifier
        """
        return self.case_id

    def get_spec_name(self) -> str:
        """Get specification name/URI (Java parity method).

        Returns
        -------
        str
            The specification URI (user-defined name)
        """
        return self.spec_id.get_uri()

    def get_spec_version(self) -> str:
        """Get specification version (Java parity method).

        Returns
        -------
        str
            The specification version string
        """
        return self.spec_id.get_version_as_string()


@dataclass
class UploadResult:
    """Result of specification upload (mirrors Java upload handling).

    Parameters
    ----------
    specifications : list[YSpecificationID]
        Successfully uploaded specifications
    warnings : list[str]
        Warning messages
    errors : list[str]
        Error messages
    raw_response : str
        Raw XML response from engine

    Examples
    --------
    >>> result = UploadResult.from_xml("<success>...</success>")
    >>> print(len(result.specifications))
    1
    """

    specifications: list[YSpecificationID] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    raw_response: str = ""

    @property
    def successful(self) -> bool:
        """Check if upload was successful."""
        return len(self.errors) == 0 and len(self.specifications) > 0

    @classmethod
    def from_xml(cls, xml_str: str) -> UploadResult:
        """Parse upload result from XML response.

        Parameters
        ----------
        xml_str : str
            XML response from engine

        Returns
        -------
        UploadResult
            Parsed upload result
        """
        result = cls(raw_response=xml_str)

        try:
            root = ET.fromstring(xml_str)

            # Check for error response
            if root.tag == "failure" or "<failure>" in xml_str:
                result.errors.append(root.text or xml_str)
                return result

            # Parse successful response
            for spec_elem in root.findall(".//specification"):
                spec_id = YSpecificationID(
                    identifier=spec_elem.get("id", ""),
                    version=spec_elem.get("version", "1.0"),
                    uri=spec_elem.get("uri", ""),
                )
                result.specifications.append(spec_id)

            # Parse warnings if any
            for warning_elem in root.findall(".//warning"):
                if warning_elem.text:
                    result.warnings.append(warning_elem.text)

        except ET.ParseError:
            # If not XML, treat as simple success/failure message
            if "success" in xml_str.lower():
                result.specifications.append(YSpecificationID(identifier="uploaded", version="1.0"))
            else:
                result.errors.append(xml_str)

        return result


@dataclass(frozen=True)
class PiledTask:
    """Task piled for batch execution (mirrors Java PiledTask).

    When a participant piles a task, all future instances of that task
    are automatically started for them without re-offering.

    Parameters
    ----------
    spec_id : YSpecificationID
        Specification identifier
    task_id : str
        Task identifier

    Examples
    --------
    >>> piled = PiledTask(YSpecificationID("spec-001"), "Task_A")
    >>> print(piled)
    spec-001 v1.0 :: Task_A
    """

    spec_id: YSpecificationID
    task_id: str

    def __str__(self) -> str:
        """Return string in Java format: 'uri v.version :: taskID'."""
        return f"{self.spec_id.uri or self.spec_id.identifier} v.{self.spec_id.version} :: {self.task_id}"

    @classmethod
    def from_xml(cls, xml_str: str) -> PiledTask:
        """Parse piled task from XML.

        Parameters
        ----------
        xml_str : str
            XML string containing piled task data

        Returns
        -------
        PiledTask
            Parsed piled task
        """
        root = ET.fromstring(xml_str)
        spec_id = YSpecificationID(
            identifier=root.get("specid", ""), version=root.get("version", "1.0"), uri=root.get("uri", "")
        )
        return cls(spec_id=spec_id, task_id=root.get("taskid", ""))


@dataclass(frozen=True)
class ChainedCase:
    """Case chained for sequential execution (mirrors Java ChainedCase).

    When a case is chained, completion of a work item in one case
    automatically starts the next item in the chained case.

    Parameters
    ----------
    spec_id : YSpecificationID
        Specification identifier
    case_id : str
        Case identifier

    Examples
    --------
    >>> chained = ChainedCase(YSpecificationID("spec-001"), "case-123")
    >>> print(chained)
    case-123 :: spec-001 v.1.0
    """

    spec_id: YSpecificationID
    case_id: str

    def __str__(self) -> str:
        """Return string in Java format: 'caseID :: uri v.version'."""
        return f"{self.case_id} :: {self.spec_id.uri or self.spec_id.identifier} v.{self.spec_id.version}"

    @classmethod
    def from_xml(cls, xml_str: str) -> ChainedCase:
        """Parse chained case from XML.

        Parameters
        ----------
        xml_str : str
            XML string containing chained case data

        Returns
        -------
        ChainedCase
            Parsed chained case
        """
        root = ET.fromstring(xml_str)
        spec_id = YSpecificationID(
            identifier=root.get("specid", ""), version=root.get("version", "1.0"), uri=root.get("uri", "")
        )
        return cls(spec_id=spec_id, case_id=root.get("caseid", ""))


@dataclass(frozen=True)
class TaskInformation:
    """Task information (mirrors Java TaskInformation).

    Contains metadata about a task for display and processing.

    Parameters
    ----------
    task_id : str
        Task identifier
    task_name : str
        Human-readable task name
    spec_id : YSpecificationID
        Specification containing this task
    decomposition_id : str
        ID of task decomposition
    input_params : dict[str, Any]
        Input parameter definitions
    output_params : dict[str, Any]
        Output parameter definitions
    documentation : str
        Task documentation
    """

    task_id: str
    task_name: str
    spec_id: YSpecificationID
    decomposition_id: str = ""
    input_params: dict[str, Any] = field(default_factory=dict)
    output_params: dict[str, Any] = field(default_factory=dict)
    documentation: str = ""


@dataclass(frozen=True)
class WorkQueue:
    """Work queue containing work items (mirrors Java work queue).

    Parameters
    ----------
    queue_type : str
        Queue type (offered, allocated, started, suspended)
    items : list[str]
        Work item IDs in the queue

    Examples
    --------
    >>> queue = WorkQueue("offered", ["wi-001", "wi-002"])
    >>> print(len(queue.items))
    2
    """

    queue_type: str
    items: list[str] = field(default_factory=list)


@dataclass
class NonHumanResource:
    """Non-human resource (mirrors Java NonHumanResource).

    Parameters
    ----------
    resource_id : str
        Resource identifier
    name : str
        Resource name
    category : str
        Resource category
    description : str
        Resource description
    """

    resource_id: str
    name: str
    category: str
    description: str = ""


@dataclass
class CalendarEntry:
    """Calendar entry for resource availability (mirrors Java calendar).

    Parameters
    ----------
    entry_id : str
        Entry identifier
    resource_id : str
        Resource this applies to
    start_time : datetime
        Start of period
    end_time : datetime
        End of period
    entry_type : str
        Type: available, unavailable, holiday
    comment : str
        Optional comment
    """

    entry_id: str
    resource_id: str
    start_time: datetime
    end_time: datetime
    entry_type: str = "unavailable"
    comment: str = ""
