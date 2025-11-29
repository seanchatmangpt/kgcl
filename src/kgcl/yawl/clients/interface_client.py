"""Base HTTP client for YAWL engine communication.

This module implements Interface_Client.java behavior - the base HTTP client
used by InterfaceA and InterfaceB clients to communicate with the YAWL engine.

Java Parity (Interface_Client.java):
    - executePost(String url, Map<String, String> params) -> String
    - executeGet(String url, Map<String, String> params) -> String
    - successful(String message) -> boolean
    - prepareParamMap(String action, String handle) -> Map<String, String>
    - stripOuterElement(String xml) -> String

Protocol:
    - All requests sent as POST (GETs rerouted for security)
    - Parameters: action, sessionHandle, + method-specific
    - Responses: XML strings, <failure> indicates error
    - UTF-8 encoding throughout
"""

from __future__ import annotations

import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any
from xml.etree import ElementTree as ET


class YAWLConnectionError(Exception):
    """Raised when connection to YAWL engine fails (Java: IOException)."""

    pass


class YAWLResponseError(Exception):
    """Raised when YAWL engine returns a failure response."""

    pass


@dataclass
class InterfaceClient:
    """Base HTTP client for YAWL engine interfaces.

    Mirrors Java's Interface_Client.java providing common HTTP functionality
    for InterfaceA (management) and InterfaceB (workflow) clients.

    Parameters
    ----------
    base_url : str
        Base URL of the YAWL engine (e.g., "http://localhost:8080/yawl")
    timeout : float
        Request timeout in seconds (default: 30.0)

    Examples
    --------
    >>> client = InterfaceClient("http://localhost:8080/yawl")
    >>> params = client.prepare_param_map("connect", None)
    >>> params["userid"] = "admin"
    >>> response = client.execute_post("/ia", params)
    """

    base_url: str
    timeout: float = 30.0
    _session_handle: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Normalize base URL."""
        self.base_url = self.base_url.rstrip("/")

    @property
    def session_handle(self) -> str | None:
        """Get current session handle.

        Returns
        -------
        str | None
            Active session handle or None if not connected
        """
        return self._session_handle

    @property
    def is_connected(self) -> bool:
        """Check if client has active session.

        Returns
        -------
        bool
            True if session handle is set
        """
        return self._session_handle is not None

    def successful(self, message: str | None) -> bool:
        """Check if response indicates success (Java parity).

        A response is successful if it's non-empty and doesn't
        contain a <failure> element.

        Parameters
        ----------
        message : str | None
            Response string from engine

        Returns
        -------
        bool
            True if response is successful
        """
        if not message:
            return False
        return "<failure>" not in message

    def prepare_param_map(self, action: str, handle: str | None) -> dict[str, str]:
        """Create parameter map with action and optional handle (Java parity).

        Parameters
        ----------
        action : str
            The action to perform
        handle : str | None
            Session handle (omitted if None)

        Returns
        -------
        dict[str, str]
            Mutable parameter dictionary
        """
        params: dict[str, str] = {"action": action}
        if handle is not None:
            params["sessionHandle"] = handle
        return params

    def strip_outer_element(self, xml: str) -> str:
        """Remove outer XML element, returning inner content (Java parity).

        Parameters
        ----------
        xml : str
            XML string with outer element

        Returns
        -------
        str
            Inner content without outer tags
        """
        if not xml:
            return ""

        try:
            # Parse the XML
            root = ET.fromstring(xml)

            # Handle self-closing tags (no content)
            if root.text is None and len(root) == 0:
                return ""

            # Build inner content
            inner_parts: list[str] = []

            # Add leading text
            if root.text:
                inner_parts.append(root.text)

            # Add child elements
            for child in root:
                inner_parts.append(ET.tostring(child, encoding="unicode"))

            # Join and return
            return "".join(inner_parts)

        except ET.ParseError:
            # If not valid XML, return as-is
            return xml

    def extract_failure_message(self, response: str) -> str:
        """Extract message from <failure> element.

        Parameters
        ----------
        response : str
            Response XML containing <failure> element

        Returns
        -------
        str
            Failure message or empty string if no failure
        """
        if not response or "<failure>" not in response:
            return ""

        # Try to parse as XML first
        try:
            root = ET.fromstring(response)
            failure = root.find(".//failure")
            if failure is not None and failure.text:
                return failure.text
            # If root IS the failure element
            if root.tag == "failure" and root.text:
                return root.text
        except ET.ParseError:
            pass

        # Fallback: regex extraction
        match = re.search(r"<failure>(.*?)</failure>", response, re.DOTALL)
        if match:
            return match.group(1).strip()

        return ""

    def execute_post(self, path: str, params: dict[str, str]) -> str:
        """Execute POST request to engine (Java parity).

        Parameters
        ----------
        path : str
            URL path (e.g., "/ia" or "/ib")
        params : dict[str, str]
            Request parameters

        Returns
        -------
        str
            Response body

        Raises
        ------
        YAWLConnectionError
            If connection fails (Java: IOException)
        """
        uri = self._build_uri(path)
        try:
            return self._send_request("POST", uri, params)
        except ConnectionError as e:
            raise YAWLConnectionError(str(e)) from e

    def execute_get(self, path: str, params: dict[str, str]) -> str:
        """Execute GET request (rerouted to POST for security - Java parity).

        Parameters
        ----------
        path : str
            URL path
        params : dict[str, str]
            Request parameters

        Returns
        -------
        str
            Response body

        Raises
        ------
        YAWLConnectionError
            If connection fails
        """
        # Java reroutes GETs to POSTs for security
        uri = self._build_uri(path)
        return self._send_request("POST", uri, params)

    def _build_uri(self, path: str) -> str:
        """Build full URI from base URL and path.

        Parameters
        ----------
        path : str
            URL path

        Returns
        -------
        str
            Full URI
        """
        if path.startswith("/"):
            return f"{self.base_url}{path}"
        return f"{self.base_url}/{path}"

    def _send_request(self, method: str, uri: str, params: dict[str, str]) -> str:
        """Send HTTP request to engine.

        Parameters
        ----------
        method : str
            HTTP method (always POST in practice)
        uri : str
            Full URI
        params : dict[str, str]
            Request parameters

        Returns
        -------
        str
            Response body

        Raises
        ------
        YAWLConnectionError
            If request fails
        """
        try:
            # Encode parameters as UTF-8 form data
            data = urllib.parse.urlencode(params).encode("utf-8")

            # Create request
            request = urllib.request.Request(
                uri,
                data=data,
                method=method,
                headers={"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"},
            )

            # Send request
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read().decode("utf-8")

        except urllib.error.URLError as e:
            raise YAWLConnectionError(f"Connection failed: {e.reason}") from e
        except ConnectionError as e:
            raise YAWLConnectionError(str(e)) from e
        except TimeoutError as e:
            raise YAWLConnectionError(f"Request timed out: {e}") from e
