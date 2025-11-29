"""YAWL case data models.

Ported from:
- org.yawlfoundation.yawl.ui.service.ChainedCase
- org.yawlfoundation.yawl.ui.service.RunningCase
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SpecificationID:
    """YAWL specification identifier.

    Parameters
    ----------
    uri : str
        Specification URI/name
    version : str
        Version string (e.g., "0.1", "1.0")
    identifier : str | None
        Optional unique identifier

    Examples
    --------
    >>> spec_id = SpecificationID("OrderProcess", "1.0")
    >>> spec_id.uri
    'OrderProcess'
    """

    uri: str
    version: str
    identifier: str | None = None

    def get_version_as_string(self) -> str:
        """Get version as string.

        Returns
        -------
        str
            Version string
        """
        return self.version


@dataclass(frozen=True)
class ChainedCase:
    """Represents a case in a workflow chain.

    A chained case is a workflow case that may be part of a larger
    case chain, tracking both the specification and case identifiers.

    Parameters
    ----------
    spec_id : SpecificationID
        Specification identifier
    case_id : str
        Case identifier

    Examples
    --------
    >>> spec = SpecificationID("OrderProcess", "1.0")
    >>> case = ChainedCase(spec, "case-001")
    >>> str(case)
    'case-001 :: OrderProcess v.1.0'
    """

    spec_id: SpecificationID
    case_id: str

    def __str__(self) -> str:
        """Return string representation.

        Returns
        -------
        str
            Formatted string: "{case_id} :: {uri} v.{version}"
        """
        return f"{self.case_id} :: {self.spec_id.uri} v.{self.spec_id.get_version_as_string()}"


@dataclass(frozen=True)
class RunningCase:
    """Represents a currently running workflow case.

    Parameters
    ----------
    spec_id : SpecificationID
        Specification identifier
    case_id : str
        Case identifier

    Examples
    --------
    >>> spec = SpecificationID("OrderProcess", "1.0")
    >>> case = RunningCase(spec, "case-001")
    >>> case.get_case_id()
    'case-001'
    >>> case.get_spec_name()
    'OrderProcess'
    """

    spec_id: SpecificationID
    case_id: str

    def get_case_id(self) -> str:
        """Get case identifier.

        Returns
        -------
        str
            Case ID
        """
        return self.case_id

    def get_spec_name(self) -> str:
        """Get specification name/URI.

        Returns
        -------
        str
            Specification URI
        """
        return self.spec_id.uri

    def get_spec_version(self) -> str:
        """Get specification version.

        Returns
        -------
        str
            Version string
        """
        return self.spec_id.get_version_as_string()
