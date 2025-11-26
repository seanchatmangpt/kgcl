"""Clipboard gateway abstraction."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass
class ClipboardGateway:
    """Cross-platform clipboard helper with graceful fallbacks."""

    def copy(self, text: str) -> bool:
        """Copy text to system clipboard."""
        return (
            self._run(["pbcopy"], text)
            or self._run(["xclip", "-selection", "clipboard"], text)
            or self._run(["xsel", "--clipboard", "--input"], text)
        )

    @staticmethod
    def _run(command: list[str], text: str) -> bool:
        try:
            subprocess.run(
                command, input=text.encode(), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False
