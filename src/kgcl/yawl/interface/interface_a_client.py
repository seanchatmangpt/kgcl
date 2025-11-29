"""YAWL Engine Interface A HTTP Client.

Implements synchronous HTTP client for YAWL Engine Interface A operations.
This is a real HTTP client that communicates with a running YAWL engine,
not a mock or simulation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


class InterfaceAClient:
    """HTTP client for YAWL Engine Interface A.

    Provides methods to interact with a YAWL engine via Interface A,
    including authentication, session management, and service queries.

    This is a REAL HTTP client that makes actual network requests,
    not a mock or in-memory simulation.

    Parameters
    ----------
    base_url : str
        Base URL of the YAWL engine Interface A endpoint
    userid : str
        Userid for authentication
    password : str
        Password for authentication
    timeout : int, optional
        HTTP request timeout in seconds, by default 30
    """

    def __init__(self, base_url: str, userid: str, password: str, timeout: int = 30) -> None:
        """Initialize Interface A client.

        Parameters
        ----------
        base_url : str
            Base URL of YAWL engine (e.g., "http://localhost:8080/yawl/ia")
        userid : str
            Authentication userid
        password : str
            Authentication password
        timeout : int, optional
            Request timeout in seconds, by default 30
        """
        self.base_url = base_url.rstrip("/")
        self.userid = userid
        self.password = password
        self.timeout = timeout
        self.session_handle: str | None = None

    def connect(self) -> str:
        """Connect to the YAWL engine and establish a session.

        Makes an actual HTTP POST to /connect endpoint.

        Returns
        -------
        str
            Session handle if successful, or XML failure message

        Raises
        ------
        OSError
            If network error occurs during connection
        """
        try:
            params = {"userid": self.userid, "password": self.password}
            response = self._post("/connect", params)

            if response.startswith("<failure"):
                return response

            self.session_handle = response
            return response

        except (URLError, HTTPError) as e:
            logger.error(f"Failed to connect to Interface A: {e}")
            raise OSError(f"Connection failed: {e}") from e

    def disconnect(self, handle: str) -> bool:
        """Disconnect a session from the engine.

        Makes an actual HTTP POST to /disconnect endpoint.

        Parameters
        ----------
        handle : str
            Session handle to disconnect

        Returns
        -------
        bool
            True if successful

        Raises
        ------
        OSError
            If network error occurs
        """
        try:
            params = {"sessionHandle": handle}
            response = self._post("/disconnect", params)
            return not response.startswith("<failure")
        except (URLError, HTTPError) as e:
            logger.error(f"Failed to disconnect: {e}")
            raise OSError(f"Disconnect failed: {e}") from e

    def check_connection(self, handle: str) -> str:
        """Check if a session handle is still valid.

        Makes an actual HTTP GET to /checkConnection endpoint.

        Parameters
        ----------
        handle : str
            Session handle to check

        Returns
        -------
        str
            "true" if valid, XML failure message otherwise

        Raises
        ------
        OSError
            If network error occurs
        """
        try:
            params = {"sessionHandle": handle}
            return self._get("/checkConnection", params)
        except (URLError, HTTPError) as e:
            logger.error(f"Failed to check connection: {e}")
            raise OSError(f"Connection check failed: {e}") from e

    def get_client_password(self, userid: str, handle: str) -> str:
        """Get password for a client application from the engine.

        Makes an actual HTTP GET to /getClientPassword endpoint.

        Parameters
        ----------
        userid : str
            Client userid to get password for
        handle : str
            Valid session handle

        Returns
        -------
        str
            Password if found, XML failure message otherwise

        Raises
        ------
        OSError
            If network error occurs
        """
        try:
            params = {"userid": userid, "sessionHandle": handle}
            return self._get("/getClientPassword", params)
        except (URLError, HTTPError) as e:
            logger.error(f"Failed to get client password: {e}")
            raise OSError(f"Get password failed: {e}") from e

    def get_registered_services(self, handle: str) -> str:
        """Get list of registered YAWL services from the engine.

        Makes an actual HTTP GET to /getRegisteredYAWLServices endpoint.

        Parameters
        ----------
        handle : str
            Valid session handle

        Returns
        -------
        str
            XML list of services, or failure message

        Raises
        ------
        OSError
            If network error occurs
        """
        try:
            params = {"sessionHandle": handle}
            return self._get("/getRegisteredYAWLServices", params)
        except (URLError, HTTPError) as e:
            logger.error(f"Failed to get services: {e}")
            raise OSError(f"Get services failed: {e}") from e

    def successful(self, response: str) -> bool:
        """Check if a response indicates success.

        Parameters
        ----------
        response : str
            XML response from engine

        Returns
        -------
        bool
            True if response does not start with <failure>, False otherwise
        """
        return not response.startswith("<failure")

    def _get(self, endpoint: str, params: dict[str, str]) -> str:
        """Make GET request to Interface A endpoint.

        Parameters
        ----------
        endpoint : str
            API endpoint path
        params : dict[str, str]
            Query parameters

        Returns
        -------
        str
            Response body

        Raises
        ------
        URLError
            If network error occurs
        HTTPError
            If HTTP error occurs
        """
        url = urljoin(self.base_url, endpoint)
        query = "&".join(f"{k}={v}" for k, v in params.items())
        full_url = f"{url}?{query}"

        req = Request(full_url, method="GET")
        with urlopen(req, timeout=self.timeout) as response:
            return response.read().decode("utf-8")

    def _post(self, endpoint: str, params: dict[str, str]) -> str:
        """Make POST request to Interface A endpoint.

        Parameters
        ----------
        endpoint : str
            API endpoint path
        params : dict[str, str]
            Form parameters

        Returns
        -------
        str
            Response body

        Raises
        ------
        URLError
            If network error occurs
        HTTPError
            If HTTP error occurs
        """
        url = urljoin(self.base_url, endpoint)
        data = "&".join(f"{k}={v}" for k, v in params.items()).encode("utf-8")

        req = Request(url, data=data, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urlopen(req, timeout=self.timeout) as response:
            return response.read().decode("utf-8")
