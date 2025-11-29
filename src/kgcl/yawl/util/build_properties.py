"""Build properties utility for YAWL.

Loads and manages build properties from properties files.
"""

from __future__ import annotations

import io
from typing import IO

from kgcl.yawl.util.xml.xnode import XNode


class YBuildProperties:
    """Build properties manager.

    Loads build properties from a properties file and provides access
    to version, build number, and build date information.

    Parameters
    ----------
    properties : dict[str, str] | None, optional
        Initial properties dictionary, by default None
    """

    def __init__(self, properties: dict[str, str] | None = None) -> None:
        """Initialize build properties.

        Parameters
        ----------
        properties : dict[str, str] | None, optional
            Initial properties dictionary, by default None
        """
        self._build_props: dict[str, str] = properties or {}

    def load(self, input_stream: IO[str] | IO[bytes]) -> None:
        """Load properties from an input stream.

        Parameters
        ----------
        input_stream : IO[str] | IO[bytes]
            Input stream containing properties (Java .properties format)
        """
        try:
            props: dict[str, str] = {}

            # Read and parse properties file
            if isinstance(input_stream, io.TextIOWrapper):
                content = input_stream.read()
            else:
                content = input_stream.read().decode("utf-8")

            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if "=" in line:
                    key, value = line.split("=", 1)
                    props[key.strip()] = value.strip()

            self._build_props = props
        except Exception:
            self._build_props = {}

    def get_build_number(self) -> str | None:
        """Get build number.

        Returns
        -------
        str | None
            Build number, or None if not set
        """
        return self._build_props.get("BuildNumber")

    def get_version(self) -> str | None:
        """Get version.

        Returns
        -------
        str | None
            Version, or None if not set
        """
        return self._build_props.get("Version")

    def get_build_date(self) -> str | None:
        """Get build date.

        Returns
        -------
        str | None
            Build date, or None if not set
        """
        return self._build_props.get("BuildDate")

    def get_full_version(self) -> str:
        """Get full version string (version + build number).

        Returns
        -------
        str
            Full version string (e.g., "1.0.0 (b.123)")
        """
        version = self.get_version() or "unknown"
        build_number = self.get_build_number() or "unknown"
        return f"{version} (b.{build_number})"

    def to_xml(self) -> str:
        """Convert properties to XML.

        Returns
        -------
        str
            XML representation of properties
        """
        root = XNode("buildproperties")
        for key, value in self._build_props.items():
            root.add_child(key, value)

        return root.to_string()
