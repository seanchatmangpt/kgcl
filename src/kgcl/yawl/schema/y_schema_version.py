"""Schema version enumeration (mirrors Java YSchemaVersion).

Provides version constants and methods for generating version-specific
XML headers and schema locations.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import ClassVar
from urllib.parse import urljoin

from kgcl.yawl.util import string_util


class YSchemaVersion(Enum):
    """Schema version enumeration (mirrors Java YSchemaVersion).

    Represents different YAWL schema versions with associated metadata
    and methods for generating version-specific XML headers.

    Attributes
    ----------
    BETA2 : YSchemaVersion
        Beta 2 version (0.2)
    BETA3 : YSchemaVersion
        Beta 3 version (0.3)
    BETA4 : YSchemaVersion
        Beta 4 version (0.4)
    BETA6 : YSchemaVersion
        Beta 6 version (0.6)
    BETA7 : YSchemaVersion
        Beta 7.1 version (0.7)
    TWO_POINT_ZERO : YSchemaVersion
        Version 2.0
    TWO_POINT_ONE : YSchemaVersion
        Version 2.1
    TWO_POINT_TWO : YSchemaVersion
        Version 2.2
    THREE_POINT_ZERO : YSchemaVersion
        Version 3.0
    FOUR_POINT_ZERO : YSchemaVersion
        Version 4.0 (default)

    Examples
    --------
    >>> version = YSchemaVersion.FOUR_POINT_ZERO
    >>> header = version.get_header()
    >>> version.is_beta_version()
    False
    """

    BETA2 = ("Beta 2", 0.2)
    BETA3 = ("Beta 3", 0.3)
    BETA4 = ("Beta 4", 0.4)
    BETA6 = ("Beta 6", 0.6)
    BETA7 = ("Beta 7.1", 0.7)
    TWO_POINT_ZERO = ("2.0", 2.0)
    TWO_POINT_ONE = ("2.1", 2.1)
    TWO_POINT_TWO = ("2.2", 2.2)
    THREE_POINT_ZERO = ("3.0", 3.0)
    FOUR_POINT_ZERO = ("4.0", 4.0)

    DEFAULT_VERSION: ClassVar[YSchemaVersion] = FOUR_POINT_ZERO

    def __init__(self, name: str, compare_val: float) -> None:
        """Initialize schema version.

        Parameters
        ----------
        name : str
            Version name string
        compare_val : float
            Numeric value for comparison
        """
        self._name = name
        self._compare_val = compare_val

    def __str__(self) -> str:
        """Return version name string.

        Returns
        -------
        str
            Version name

        Notes
        -----
        Java signature: String toString()
        """
        return self._name

    @classmethod
    def from_string(cls, version_str: str | None) -> YSchemaVersion | None:
        """Get version from string.

        Parameters
        ----------
        version_str : str | None
            Version string

        Returns
        -------
        YSchemaVersion | None
            Version enum or None if not found

        Notes
        -----
        Java signature: static YSchemaVersion fromString(String s)
        """
        if version_str is None:
            return None

        for version in cls:
            if version._name == version_str:
                return version
        return None

    @classmethod
    def default_version(cls) -> YSchemaVersion:
        """Get default version.

        Returns
        -------
        YSchemaVersion
            Default version (4.0)

        Notes
        -----
        Java signature: static YSchemaVersion defaultVersion()
        """
        return cls.DEFAULT_VERSION

    @classmethod
    def is_valid_version_string(cls, version_str: str) -> bool:
        """Check if version string is valid.

        Parameters
        ----------
        version_str : str
            Version string to check

        Returns
        -------
        bool
            True if valid

        Notes
        -----
        Java signature: static boolean isValidVersionString(String s)
        """
        return cls.from_string(version_str) is not None

    def is_version_at_least(self, reference_version: YSchemaVersion) -> bool:
        """Check if this version is at least the reference version.

        Parameters
        ----------
        reference_version : YSchemaVersion
            Version to compare against

        Returns
        -------
        bool
            True if this version >= reference version

        Notes
        -----
        Java signature: boolean isVersionAtLeast(YSchemaVersion referenceVersion)
        """
        return self._compare_val >= reference_version._compare_val

    def is_beta_version(self) -> bool:
        """Check if this is a beta version.

        Returns
        -------
        bool
            True if beta version

        Notes
        -----
        Java signature: boolean isBetaVersion()
        """
        return self in (
            YSchemaVersion.BETA2,
            YSchemaVersion.BETA3,
            YSchemaVersion.BETA4,
            YSchemaVersion.BETA6,
            YSchemaVersion.BETA7,
        )

    def is_beta2(self) -> bool:
        """Check if this is Beta 2.

        Returns
        -------
        bool
            True if Beta 2

        Notes
        -----
        Java signature: boolean isBeta2()
        """
        return self == YSchemaVersion.BETA2

    def uses_simple_root_data(self) -> bool:
        """Check if version uses simple root data format.

        Returns
        -------
        bool
            True if Beta2 or Beta3

        Notes
        -----
        Java signature: boolean usesSimpleRootData()
        """
        return self.is_beta2() or self == YSchemaVersion.BETA3

    def is_schema_validating(self) -> bool:
        """Check if version supports schema validation.

        Returns
        -------
        bool
            True if not Beta2

        Notes
        -----
        Java signature: boolean isSchemaValidating()
        """
        return not self.is_beta2()

    def get_name_space(self) -> str:
        """Get XML namespace for this version.

        Returns
        -------
        str
            Namespace URI

        Notes
        -----
        Java signature: String getNameSpace()
        """
        if self.is_beta_version():
            return "http://www.citi.qut.edu.au/yawl"
        return "http://www.yawlfoundation.org/yawlschema"

    def get_schema_url(self) -> str:
        """Get schema URL for this version.

        Returns
        -------
        str
            Schema URL string

        Notes
        -----
        Java signature: URL getSchemaURL()
        Returns URL string instead of URL object for Python
        """
        schema_package_path = "/org/yawlfoundation/yawl/unmarshal/"
        schema_file = self._get_schema_file_name()
        return urljoin(schema_package_path, schema_file)

    def get_schema_location(self) -> str:
        """Get schema location string.

        Returns
        -------
        str
            Schema location (namespace + URL)

        Notes
        -----
        Java signature: String getSchemaLocation()
        """
        return f"{self.get_name_space()} {self.get_schema_url()}"

    def get_header(self) -> str:
        """Generate version-specific XML header.

        Returns
        -------
        str
            XML header string

        Notes
        -----
        Java signature: String getHeader()
        """
        header_template = (
            '<?xml version="1.0" encoding="UTF-8"?>\r\n'
            '<specificationSet version="{}" xmlns="{}" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xsi:schemaLocation="{}">'
        )

        if self.is_beta_version():
            beta_ns = "http://www.citi.qut.edu.au/yawl"
            beta_schema_location = "http://www.citi.qut.edu.au/yawl d:/yawl/schema/YAWL_SchemaBeta7.1.xsd"
            return header_template.format(YSchemaVersion.BETA7._name, beta_ns, beta_schema_location)
        else:
            release_ns = self.get_name_space()
            release_schema_location = self._get_release_schema_location()
            return header_template.format(self._name, release_ns, release_schema_location)

    def _get_release_schema_location(self) -> str:
        """Get release schema location.

        Returns
        -------
        str
            Schema location string
        """
        release_ns = self.get_name_space()
        schema_file = self._get_schema_file_name()
        return f"{release_ns} {release_ns}/{schema_file}"

    def _get_schema_file_name(self) -> str:
        """Get schema file name for this version.

        Returns
        -------
        str
            Schema file name

        Notes
        -----
        Java signature: private String getSchemaFileName()
        """
        if self.is_beta2():
            return "YAWL_Schema.xsd"
        compact_name = string_util.remove_all_white_space(self._name)
        return f"YAWL_Schema{compact_name}.xsd"
