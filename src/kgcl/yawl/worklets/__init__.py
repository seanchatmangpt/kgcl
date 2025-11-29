"""Worklet service for exception handling and dynamic task delegation.

Implements YAWL's worklet service with Ripple Down Rules (RDR) for
runtime case and task exception handling.
"""

import logging
from logging import Logger

from kgcl.yawl.worklets.exceptions import (
    RDRTreeError,
    RuleEvaluationError,
    WorkletError,
    WorkletExecutionError,
    WorkletNotFoundError,
    WorkletValidationError,
)
from kgcl.yawl.worklets.executor import WorkletExecutor, WorkletResult
from kgcl.yawl.worklets.models import RDRNode, RDRTree, Worklet, WorkletCase, WorkletStatus, WorkletType
from kgcl.yawl.worklets.protocols import (
    RDREvaluatorProtocol,
    WorkletExecutorProtocol,
    WorkletLoaderProtocol,
    WorkletRepositoryProtocol,
)
from kgcl.yawl.worklets.repository import WorkletQueryBuilder, WorkletRepository
from kgcl.yawl.worklets.rules import RDREngine, RuleContext

# Configure module-level logger
_logger: Logger = logging.getLogger(__name__)

# Set default logging level if not configured
if not _logger.handlers:
    handler = logging.NullHandler()
    _logger.addHandler(handler)
    _logger.setLevel(logging.WARNING)

__all__ = [
    # Models
    "Worklet",
    "WorkletType",
    "WorkletStatus",
    "WorkletCase",
    "RDRNode",
    "RDRTree",
    # Rules
    "RDREngine",
    "RuleContext",
    # Repository
    "WorkletRepository",
    "WorkletQueryBuilder",
    # Executor
    "WorkletExecutor",
    "WorkletResult",
    # Exceptions
    "WorkletError",
    "WorkletExecutionError",
    "WorkletNotFoundError",
    "WorkletValidationError",
    "RDRTreeError",
    "RuleEvaluationError",
    # Protocols
    "WorkletExecutorProtocol",
    "WorkletRepositoryProtocol",
    "RDREvaluatorProtocol",
    "WorkletLoaderProtocol",
]
