"""External client authentication.

Represents the authentication credentials of an external application that may
connect to the Engine via the various interfaces (as opposed to a custom service).

Note that the generic user "admin" is represented by an instance of this class.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

from kgcl.yawl.authentication.y_client import YClient


class YExternalClient(YClient):
    """External client authentication credentials.

    Represents authentication for external applications connecting to the engine
    (as opposed to custom services). The "admin" user is represented by this class.

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
    >>> client = YExternalClient(user_id="admin", password="hashed_pwd")
    >>> client.get_user_name()
    'admin'
    """

    def __init__(
        self, user_id: str | None = None, password: str | None = None, documentation: str | None = None
    ) -> None:
        """Initialize external client.

        Parameters
        ----------
        user_id : str | None, optional
            User ID/username, by default None
        password : str | None, optional
            Password (hashed), by default None
        documentation : str | None, optional
            Documentation string, by default None
        """
        super().__init__(user_id, password, documentation)

    def get_userid(self) -> str | None:
        """Get user ID (for JSF table compatibility).

        Returns
        -------
        str | None
            User ID
        """
        return self._user_name

    def get_documentation(self) -> str | None:
        """Get documentation (for JSF table compatibility).

        Returns
        -------
        str | None
            Documentation
        """
        return self._documentation
