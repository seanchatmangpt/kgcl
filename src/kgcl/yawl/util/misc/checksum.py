"""Checksum utility for file and data verification.

Provides MD5 checksum calculation and comparison.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import IO


class CheckSummer:
    """MD5 checksum calculator and comparator."""

    def get_md5_hex(self, file_path: str | Path | IO[bytes]) -> str:
        """Get MD5 hex checksum of a file or stream.

        Parameters
        ----------
        file_path : str | Path | IO[bytes]
            File path or file-like object

        Returns
        -------
        str
            MD5 hex checksum (32-character hex string)

        Raises
        ------
        OSError
            If file cannot be read
        """
        if isinstance(file_path, (str, Path)):
            path = Path(file_path)
            with path.open("rb") as f:
                return self._get_md5_hex_stream(f)
        else:
            # File-like object
            return self._get_md5_hex_stream(file_path)

    def compare(self, file_path: str | Path | IO[bytes], hex_to_compare: str) -> bool:
        """Compare file checksum with expected hex value.

        Parameters
        ----------
        file_path : str | Path | IO[bytes]
            File path or file-like object
        hex_to_compare : str
            Expected MD5 hex checksum

        Returns
        -------
        bool
            True if checksums match, False otherwise

        Raises
        ------
        OSError
            If file cannot be read
        """
        return self.get_md5_hex(file_path) == hex_to_compare

    def _get_md5_hex_stream(self, stream: IO[bytes]) -> str:
        """Get MD5 hex checksum from a stream.

        Parameters
        ----------
        stream : IO[bytes]
            Binary stream to read from

        Returns
        -------
        str
            MD5 hex checksum (32-character hex string)

        Raises
        ------
        OSError
            If stream cannot be read
        """
        md = hashlib.md5()
        buffer_size = 8192

        while True:
            chunk = stream.read(buffer_size)
            if not chunk:
                break
            md.update(chunk)

        return md.hexdigest()

    @staticmethod
    def get_md5_hex_bytes(bytes_data: bytes) -> str:
        """Get MD5 hex checksum of byte data.

        Parameters
        ----------
        bytes_data : bytes
            Byte data to checksum

        Returns
        -------
        str
            MD5 hex checksum (32-character hex string)
        """
        md = hashlib.md5()
        md.update(bytes_data)
        return md.hexdigest()
