"""Verification interface (mirrors Java YVerifiable).

Classes implementing this protocol can verify themselves against
YAWL language semantics.
"""

from __future__ import annotations

from typing import Protocol

from kgcl.yawl.engine.y_engine import YVerificationHandler


class YVerifiable(Protocol):
    """Protocol for classes that can verify themselves.

    Implementers must provide a verify method that checks the object
    against YAWL language semantics and reports errors/warnings.

    Examples
    --------
    >>> class MyElement:
    ...     def verify(self, handler: YVerificationHandler) -> None:
    ...         if not self.id:
    ...             handler.error(self, "Missing ID")
    >>> element = MyElement()
    >>> handler = YVerificationHandler()
    >>> element.verify(handler)
    """

    def verify(self, verification_handler: YVerificationHandler) -> None:
        """Verify object against YAWL language semantics.

        Parameters
        ----------
        verification_handler : YVerificationHandler
            Handler to report errors and warnings to
        """
        ...
