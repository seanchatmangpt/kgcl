"""Named thread factory utility.

Factory for creating threads with consistent naming.
"""

from __future__ import annotations

import threading
from typing import Callable


class NamedThreadFactory:
    """Factory for creating threads with consistent naming.

    Parameters
    ----------
    prefix : str
        Prefix for thread names
    """

    def __init__(self, prefix: str) -> None:
        """Initialize named thread factory.

        Parameters
        ----------
        prefix : str
            Prefix for thread names
        """
        self._prefix = f"{prefix}-"
        self._index = 0
        self._lock = threading.Lock()

    def new_thread(self, target: Callable[[], None]) -> threading.Thread:
        """Create a new thread with a unique name.

        Parameters
        ----------
        target : Callable[[], None]
            Callable to run in the thread

        Returns
        -------
        threading.Thread
            New thread with unique name
        """
        with self._lock:
            name = f"{self._prefix}{self._index}"
            self._index += 1

        thread = threading.Thread(target=target, name=name)
        return thread
