"""HTTP utility functions.

Pythonic equivalents to HttpUtil.java for URL resolution, connectivity
checks, and file downloads.
"""

from __future__ import annotations

import socket
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from urllib.parse import ParseResult

try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    try:
        import requests

        HAS_REQUESTS = True
    except ImportError:
        HAS_REQUESTS = False

_TIMEOUT_SECONDS = 2.0


def is_responsive(url: str) -> bool:
    """Check if a URL is responsive.

    Parameters
    ----------
    url : str
        URL to check

    Returns
    -------
    bool
        True if URL is responsive, False otherwise
    """
    try:
        resolved = resolve_url(url)
        return resolved is not None
    except Exception:
        return False


def resolve_url(url_string: str) -> str:
    """Resolve URL following redirects and return final URL.

    Follows redirects and returns the final URL after all redirects.

    Parameters
    ----------
    url_string : str
        URL string to resolve

    Returns
    -------
    str
        Final URL after following redirects

    Raises
    ------
    OSError
        If URL cannot be resolved or connection fails
    """
    from urllib.parse import urlparse

    url = urlparse(url_string)

    if HAS_HTTPX:
        return _resolve_url_httpx(url_string)
    elif HAS_REQUESTS:
        return _resolve_url_requests(url_string)
    else:
        # Fallback to basic URL parsing
        return url_string


def _resolve_url_httpx(url_string: str) -> str:
    """Resolve URL using httpx.

    Parameters
    ----------
    url_string : str
        URL to resolve

    Returns
    -------
    str
        Final URL after redirects

    Raises
    ------
    OSError
        If resolution fails
    """
    import httpx

    with httpx.Client(follow_redirects=True, timeout=_TIMEOUT_SECONDS) as client:
        try:
            response = client.head(url_string, follow_redirects=True)
            if response.status_code < 300:
                return str(response.url)
            elif 300 <= response.status_code < 400:
                location = response.headers.get("Location")
                if location:
                    return resolve_url(location)
                raise OSError(f"Redirect without Location header: {response.status_code}")
            else:
                raise OSError(f"HTTP error: {response.status_code}")
        except httpx.RequestError as e:
            raise OSError(f"Request failed: {e}") from e


def _resolve_url_requests(url_string: str) -> str:
    """Resolve URL using requests.

    Parameters
    ----------
    url_string : str
        URL to resolve

    Returns
    -------
    str
        Final URL after redirects

    Raises
    ------
    OSError
        If resolution fails
    """
    import requests

    try:
        response = requests.head(url_string, allow_redirects=True, timeout=_TIMEOUT_SECONDS)
        if response.status_code < 300:
            return response.url
        elif 300 <= response.status_code < 400:
            location = response.headers.get("Location")
            if location:
                return resolve_url(location)
            raise OSError(f"Redirect without Location header: {response.status_code}")
        else:
            raise OSError(f"HTTP error: {response.status_code}")
    except requests.RequestException as e:
        raise OSError(f"Request failed: {e}") from e


def is_port_active(host: str, port: int) -> bool:
    """Check if a port is active on a host.

    Parameters
    ----------
    host : str
        Hostname or IP address
    port : int
        Port number

    Returns
    -------
    bool
        True if port is active, False otherwise
    """
    try:
        return _simple_ping(host, port)
    except Exception:
        return False


def _simple_ping(host: str, port: int) -> bool:
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
        True if connection succeeds

    Raises
    ------
    OSError
        If parameters are invalid or connection fails
    """
    if host is None or port < 0:
        raise OSError("Error: bad parameters")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(_TIMEOUT_SECONDS)
    try:
        sock.connect((host, port))
        return True
    finally:
        sock.close()


def download(from_url: str, to_file: str | Path) -> None:
    """Download a file from a URL.

    Parameters
    ----------
    from_url : str
        URL to download from
    to_file : str | Path
        File path to save to

    Raises
    ------
    OSError
        If download fails
    """
    file_path = Path(to_file)
    resolved_url = resolve_url(from_url)

    if HAS_HTTPX:
        _download_httpx(resolved_url, file_path)
    elif HAS_REQUESTS:
        _download_requests(resolved_url, file_path)
    else:
        raise OSError("No HTTP library available (httpx or requests required)")


def _download_httpx(url: str, file_path: Path) -> None:
    """Download using httpx.

    Parameters
    ----------
    url : str
        URL to download
    file_path : Path
        File path to save to

    Raises
    ------
    OSError
        If download fails
    """
    import httpx

    with httpx.stream("GET", url, timeout=_TIMEOUT_SECONDS) as response:
        response.raise_for_status()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("wb") as f:
            for chunk in response.iter_bytes():
                f.write(chunk)


def _download_requests(url: str, file_path: Path) -> None:
    """Download using requests.

    Parameters
    ----------
    url : str
        URL to download
    file_path : Path
        File path to save to

    Raises
    ------
    OSError
        If download fails
    """
    import requests

    response = requests.get(url, stream=True, timeout=_TIMEOUT_SECONDS)
    response.raise_for_status()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
