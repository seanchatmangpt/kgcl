"""File Resolution with SHA256 Integrity Checking.

Implements file loading and verification for SPARQL/SHACL conditions,
ported from UNRDF condition-evaluator.mjs.

Features:
- Load SPARQL/SHACL from local and remote files
- SHA256 integrity verification
- Path security validation
- Environment variable substitution support
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Optional
import urllib.request


class FileResolverError(Exception):
    """Raised when file resolution fails."""

    pass


class FileResolver:
    """Resolve and verify condition files with SHA256 integrity checking.

    Features:
    - Load SPARQL/SHACL from files
    - Verify file integrity with SHA256
    - Support for multiple file formats
    - Environment variable substitution

    Examples
    --------
    >>> resolver = FileResolver(allowed_paths=["/path/to/queries"])
    >>> content = resolver.load_file("file:///path/to/query.sparql")
    >>> verified = resolver.load_file(
    ...     "file:///path/to/query.sparql",
    ...     expected_sha256="abc123..."
    ... )

    """

    def __init__(self, allowed_paths: Optional[list[str]] = None) -> None:
        """Initialize resolver.

        Parameters
        ----------
        allowed_paths : list[str], optional
            List of allowed base paths for security

        """
        self.allowed_paths = allowed_paths or []

    def load_file(self, uri: str, expected_sha256: Optional[str] = None) -> str:
        """Load file and optionally verify integrity.

        Parameters
        ----------
        uri : str
            File URI (file:///, http://, https://)
        expected_sha256 : str, optional
            Expected SHA256 hash for integrity verification

        Returns
        -------
        str
            File contents as string

        Raises
        ------
        FileResolverError
            If file not found, integrity check fails, or URI scheme unsupported

        Examples
        --------
        >>> resolver = FileResolver()
        >>> content = resolver.load_file("file:///tmp/query.sparql")
        >>> # With integrity check
        >>> content = resolver.load_file(
        ...     "file:///tmp/query.sparql",
        ...     expected_sha256="abc123..."
        ... )

        """
        if uri.startswith("file://"):
            path = uri[7:]  # Remove 'file://' prefix
            return self._load_local_file(path, expected_sha256)
        elif uri.startswith("http://") or uri.startswith("https://"):
            return self._load_remote_file(uri, expected_sha256)
        else:
            msg = f"Unsupported URI scheme: {uri}"
            raise FileResolverError(msg)

    def _load_local_file(self, path: str, expected_sha256: Optional[str]) -> str:
        """Load local file with integrity check.

        Parameters
        ----------
        path : str
            Local file path
        expected_sha256 : str, optional
            Expected SHA256 hash

        Returns
        -------
        str
            File contents

        Raises
        ------
        FileResolverError
            If path not allowed, file not found, or integrity check fails

        """
        path_obj = Path(path)

        # Security: verify path is allowed
        if self.allowed_paths:
            normalized = str(path_obj.resolve())
            allowed = any(
                normalized.startswith(str(Path(ap).resolve()))
                for ap in self.allowed_paths
            )
            if not allowed:
                msg = f"Path not allowed: {path}"
                raise FileResolverError(msg)

        if not path_obj.exists():
            msg = f"File not found: {path}"
            raise FileResolverError(msg)

        # Read file content
        with open(path_obj) as f:
            content = f.read()

        # Verify integrity if hash provided
        if expected_sha256:
            actual_hash = sha256(content.encode()).hexdigest()
            if actual_hash != expected_sha256:
                msg = (
                    f"Integrity check failed for {path}: "
                    f"expected {expected_sha256}, got {actual_hash}"
                )
                raise FileResolverError(msg)

        return content

    def _load_remote_file(self, uri: str, expected_sha256: Optional[str]) -> str:
        """Load remote file with integrity check.

        Parameters
        ----------
        uri : str
            Remote file URI (http:// or https://)
        expected_sha256 : str, optional
            Expected SHA256 hash

        Returns
        -------
        str
            File contents

        Raises
        ------
        FileResolverError
            If download fails or integrity check fails

        """
        try:
            with urllib.request.urlopen(uri) as response:
                content = response.read().decode()
        except Exception as e:
            msg = f"Failed to load remote file {uri}: {e}"
            raise FileResolverError(msg) from e

        # Verify integrity if hash provided
        if expected_sha256:
            actual_hash = sha256(content.encode()).hexdigest()
            if actual_hash != expected_sha256:
                msg = (
                    f"Integrity check failed for {uri}: "
                    f"expected {expected_sha256}, got {actual_hash}"
                )
                raise FileResolverError(msg)

        return content

    def compute_sha256(self, content: str) -> str:
        """Compute SHA256 hash of content.

        Parameters
        ----------
        content : str
            Content to hash

        Returns
        -------
        str
            SHA256 hash as hex string

        Examples
        --------
        >>> resolver = FileResolver()
        >>> hash_val = resolver.compute_sha256("SELECT * WHERE { ?s ?p ?o }")

        """
        return sha256(content.encode()).hexdigest()
