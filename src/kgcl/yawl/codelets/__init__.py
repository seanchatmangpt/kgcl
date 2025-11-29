"""Codelet execution framework for automated tasks.

Codelets are Java-like automated task handlers that execute
work item logic without human intervention.

This module provides:
- Codelet protocol and base class
- Codelet executor with timeout
- Codelet registry with decorators
"""

from kgcl.yawl.codelets.base import AbstractCodelet, Codelet, CodeletContext, CodeletResult, CodeletStatus
from kgcl.yawl.codelets.executor import CodeletExecutor
from kgcl.yawl.codelets.registry import CodeletRegistry, codelet

__all__ = [
    "AbstractCodelet",
    "Codelet",
    "CodeletContext",
    "CodeletExecutor",
    "CodeletRegistry",
    "CodeletResult",
    "CodeletStatus",
    "codelet",
]
