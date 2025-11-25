"""
Security Module - Sandbox Restrictions.

Ported from UNRDF security/sandbox-restrictions.mjs.
Provides configuration for isolated hook execution environments.
"""

from dataclasses import dataclass, field
from typing import List
from pathlib import Path


@dataclass
class SandboxRestrictions:
    """
    Configuration for isolated hook execution environments.

    Prevents:
    - File system access beyond allowed_paths
    - Network calls (if no_network=True)
    - Process spawning (if no_process_spawn=True)
    - Excessive memory usage
    - Long-running operations

    Parameters
    ----------
    allowed_paths : List[str]
        List of allowed file system paths for access
    no_network : bool
        Whether to block network access
    no_process_spawn : bool
        Whether to block process spawning
    memory_limit_mb : int
        Maximum memory usage in megabytes
    timeout_ms : int
        Maximum execution time in milliseconds
    read_only : bool
        Whether file system access is read-only
    max_open_files : int
        Maximum number of open file handles
    """

    allowed_paths: List[str] = field(default_factory=list)
    no_network: bool = True
    no_process_spawn: bool = True
    memory_limit_mb: int = 512
    timeout_ms: int = 30000
    read_only: bool = False
    max_open_files: int = 100

    def validate_path(self, path: str) -> bool:
        """
        Check if path is allowed for access.

        Parameters
        ----------
        path : str
            File path to validate

        Returns
        -------
        bool
            True if path is allowed, False otherwise
        """
        if not self.allowed_paths:
            return False

        try:
            # Normalize and resolve path (handles symlinks, .., etc.)
            normalized = str(Path(path).resolve())

            # Check if path is within any allowed path
            for allowed in self.allowed_paths:
                allowed_normalized = str(Path(allowed).resolve())
                if normalized.startswith(allowed_normalized):
                    return True
        except Exception:
            # If path resolution fails, deny access
            return False

        return False

    def validate_restrictions(self) -> bool:
        """
        Verify sandbox configuration is valid.

        Returns
        -------
        bool
            True if all constraints are satisfied
        """
        return (
            self.memory_limit_mb > 0
            and self.timeout_ms > 0
            and self.max_open_files > 0
            and len(self.allowed_paths) > 0
        )
