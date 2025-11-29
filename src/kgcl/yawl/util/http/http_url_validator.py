"""HTTP URL validator utility.

Validates URLs and checks server responsiveness.
"""

from __future__ import annotations

import socket
import time
from urllib.parse import urlparse

from kgcl.yawl.util.string_util import wrap

_CONNECT_TIMEOUT = 1.0
_cancelled = False


def validate(url_str: str) -> str:
    """Validate a URL string.

    Checks that the URL is valid and that the server is responsive.

    Parameters
    ----------
    url_str : str
        URL string to validate

    Returns
    -------
    str
        Success message "<success/>" or error message wrapped in XML
    """
    try:
        url = _create_url(url_str)
        return _validate_url(url)
    except ValueError as e:
        return _get_error_message(str(e))


def cancel_all() -> None:
    """Cancel all pending validations.

    Called on shutdown to stop any current pings.
    """
    global _cancelled
    _cancelled = True


def ping_until_available(url_str: str, timeout_seconds: int) -> bool:
    """Ping URL until it becomes available or timeout.

    Parameters
    ----------
    url_str : str
        URL to ping
    timeout_seconds : int
        Timeout in seconds

    Returns
    -------
    bool
        True if URL becomes available, False if timeout

    Raises
    ------
    ValueError
        If URL is malformed
    """
    url = _create_url(url_str)
    now = time.time()
    timeout_moment = now + timeout_seconds

    while now <= timeout_moment:
        if _validate_url(url) == "<success/>":
            return True

        if _cancelled:
            return False

        time.sleep(_CONNECT_TIMEOUT)
        now = time.time()

    return False


def simple_ping(host: str, port: int) -> bool:
    """Simple ping by attempting socket connection.

    Parameters
    ----------
    host : str
        Hostname or IP address
    port : int
        Port number

    Returns
    -------
    bool
        True if connection succeeds, False otherwise
    """
    if host is None or port < 0:
        return False

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(_CONNECT_TIMEOUT)
        sock.connect((host, port))
        sock.close()
        return True
    except Exception:
        return False


def is_tomcat_running(url_str: str) -> bool:
    """Check if Tomcat server is running.

    Parameters
    ----------
    url_str : str
        URL string

    Returns
    -------
    bool
        True if Tomcat is running, False otherwise
    """
    try:
        parsed = urlparse(url_str)
        host = parsed.hostname
        if not host:
            return False

        # Try to get Tomcat port from config (simplified)
        port = _get_tomcat_server_port()
        if port < 0:
            # Default Tomcat port
            port = 8080

        return simple_ping(host, port)
    except Exception:
        return False


def _validate_url(url: str) -> str:
    """Validate a URL by checking server response.

    Parameters
    ----------
    url : str
        URL to validate

    Returns
    -------
    str
        Success message "<success/>" or error message
    """
    try:
        from kgcl.yawl.util.http.http_util import resolve_url

        resolved = resolve_url(url)
        if resolved:
            return "<success/>"
        else:
            return _get_error_message("URL validation failed")
    except Exception as e:
        return _get_error_message(f"Error attempting to validate URL: {e!s}")


def _create_url(url_str: str) -> str:
    """Create and validate URL string.

    Parameters
    ----------
    url_str : str
        URL string

    Returns
    -------
    str
        Validated URL string

    Raises
    ------
    ValueError
        If URL is invalid or malformed
    """
    if url_str is None:
        raise ValueError("URL is null")

    if not (url_str.startswith("http://") or url_str.startswith("https://")):
        raise ValueError("Invalid protocol for http")

    # Validate URL format
    parsed = urlparse(url_str)
    if not parsed.netloc:
        raise ValueError("Invalid URL format")

    return url_str


def _get_error_message(msg: str) -> str:
    """Format error message as XML.

    Parameters
    ----------
    msg : str
        Error message

    Returns
    -------
    str
        XML-wrapped error message
    """
    return wrap(msg, "failure")


def _get_tomcat_server_port() -> int:
    """Get Tomcat server port from config file.

    Returns
    -------
    int
        Port number, or -1 if not found
    """
    # Simplified implementation - would need to read server.xml
    # For now, return -1 to indicate not found
    return -1
