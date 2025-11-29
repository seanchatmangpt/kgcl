"""Build information and version management.

Ported from org.yawlfoundation.yawl.ui.util.BuildInformation
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BuildProperties:
    """Build properties for a service component.

    Parameters
    ----------
    version : str | None
        Version string (e.g., "5.2.0")
    number : str | None
        Build number
    date : str | None
        Build date string

    Examples
    --------
    >>> props = BuildProperties("5.2.0", "1234", "2022-11-28")
    >>> props.as_dict()
    {'BuildDate': '2022-11-28', 'Version': '5.2.0', 'BuildNumber': '1234'}
    """

    version: str | None
    number: str | None
    date: str | None

    def as_dict(self) -> dict[str, str | None]:
        """Convert properties to dictionary.

        Returns
        -------
        dict[str, str | None]
            Dictionary with keys: BuildDate, Version, BuildNumber
        """
        return {"BuildDate": self.date, "Version": self.version, "BuildNumber": self.number}


class BuildInformation:
    """Manages build information from properties.

    This class loads and provides access to build properties for various
    YAWL service components. In production, properties would be loaded from
    a build.properties resource file.

    Attributes
    ----------
    _build_props : dict[str, str]
        Build properties loaded from configuration

    Examples
    --------
    >>> info = BuildInformation()
    >>> ui_props = info.get_ui_properties()
    >>> ui_props.version
    '5.2.0'
    """

    def __init__(self, properties: dict[str, str] | None = None) -> None:
        """Initialize build information.

        Parameters
        ----------
        properties : dict[str, str] | None, optional
            Build properties dictionary. If None, initializes empty.
        """
        self._build_props: dict[str, str] = properties or {}

    def get(self, key: str) -> str | None:
        """Get a build property value.

        Parameters
        ----------
        key : str
            Property key

        Returns
        -------
        str | None
            Property value, or None if not found
        """
        return self._build_props.get(key)

    def get_ui_properties(self) -> BuildProperties:
        """Get UI service build properties.

        Returns
        -------
        BuildProperties
            UI service version, build number, and date
        """
        return self._get_properties("ui")

    def get_mail_service_properties(self) -> BuildProperties:
        """Get mail service build properties.

        Returns
        -------
        BuildProperties
            Mail service version, build number, and date
        """
        return self._get_properties("mail")

    def get_invoker_service_properties(self) -> BuildProperties:
        """Get invoker service build properties.

        Returns
        -------
        BuildProperties
            Invoker service version, build number, and date
        """
        return self._get_properties("invoker")

    def get_docstore_properties(self) -> BuildProperties:
        """Get document store build properties.

        Returns
        -------
        BuildProperties
            Document store version, build number, and date
        """
        return self._get_properties("docstore")

    def _get_properties(self, prefix: str) -> BuildProperties:
        """Get build properties for a service by prefix.

        Parameters
        ----------
        prefix : str
            Service prefix (e.g., "ui", "mail", "invoker", "docstore")

        Returns
        -------
        BuildProperties
            Build properties for the specified service
        """
        version = self.get(f"{prefix}.service.version")
        number = self.get(f"{prefix}.service.build")
        date = self.get(f"{prefix}.service.build.date")
        return BuildProperties(version=version, number=number, date=date)
