"""Base client class for authentication.

Base class that defines a custom service or external client application,
in particular their session authentication credentials.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

from kgcl.yawl.util.xml.xnode import XNode


class YClient:
    """Base class for custom service or external client.

    Defines authentication credentials (username, password) and documentation
    for clients connecting to the YAWL engine.

    Parameters
    ----------
    user_id : str | None, optional
        User ID/username, by default None
    password : str | None, optional
        Password (hashed), by default None
    documentation : str | None, optional
        Documentation string, by default None

    Examples
    --------
    >>> client = YClient(user_id="admin", password="hashed_pwd", documentation="Admin user")
    >>> client.get_user_name()
    'admin'
    """

    def __init__(
        self, user_id: str | None = None, password: str | None = None, documentation: str | None = None
    ) -> None:
        """Initialize client.

        Parameters
        ----------
        user_id : str | None, optional
            User ID/username, by default None
        password : str | None, optional
            Password (hashed), by default None
        documentation : str | None, optional
            Documentation string, by default None
        """
        self._user_name: str | None = user_id
        self._password: str | None = password
        self._documentation: str | None = documentation

    def get_user_name(self) -> str | None:
        """Get username.

        Returns
        -------
        str | None
            Username
        """
        return self._user_name

    def set_user_name(self, user_id: str) -> None:
        """Set username.

        Parameters
        ----------
        user_id : str
            Username to set
        """
        self._user_name = user_id

    def get_password(self) -> str | None:
        """Get password.

        Returns
        -------
        str | None
            Password (hashed)
        """
        return self._password

    def set_password(self, password: str) -> None:
        """Set password.

        Parameters
        ----------
        password : str
            Password (hashed) to set
        """
        self._password = password

    def get_documentation(self) -> str | None:
        """Get documentation.

        Returns
        -------
        str | None
            Documentation string
        """
        return self._documentation

    def set_documentation(self, documentation: str) -> None:
        """Set documentation.

        Parameters
        ----------
        documentation : str
            Documentation string to set
        """
        self._documentation = documentation

    def __eq__(self, other: object) -> bool:
        """Check equality based on username.

        Parameters
        ----------
        other : object
            Other object to compare

        Returns
        -------
        bool
            True if same username
        """
        if not isinstance(other, YClient):
            return False
        if self._user_name is not None:
            return self._user_name == other._user_name
        return super().__eq__(other)

    def __hash__(self) -> int:
        """Get hash based on username.

        Returns
        -------
        int
            Hash code
        """
        if self._user_name is not None:
            return hash(self._user_name)
        return super().__hash__()

    def to_xml(self) -> str:
        """Convert to XML representation.

        Returns
        -------
        str
            XML string representation
        """
        root = XNode("client")
        root.add_child("username", self._user_name)
        root.add_child("password", self._password)
        root.add_child("documentation", self._documentation)
        return root.to_string()
