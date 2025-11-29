"""YAWL exception hierarchy (mirrors Java org.yawlfoundation.yawl.exceptions).

This module provides all YAWL-specific exceptions for workflow execution,
data validation, state management, and persistence operations.
"""

from kgcl.yawl.exceptions.y_exceptions import (
    Problem,
    YAuthenticationException,
    YAWLException,
    YConnectivityException,
    YDataQueryException,
    YDataStateException,
    YDataValidationException,
    YEngineStateException,
    YExternalDataException,
    YLogException,
    YPersistenceException,
    YQueryException,
    YSchemaBuildingException,
    YStateException,
    YSyntaxException,
)

__all__ = [
    "YAWLException",
    "YStateException",
    "YDataStateException",
    "YDataQueryException",
    "YDataValidationException",
    "YQueryException",
    "YPersistenceException",
    "YAuthenticationException",
    "YConnectivityException",
    "YEngineStateException",
    "YExternalDataException",
    "YLogException",
    "YSchemaBuildingException",
    "YSyntaxException",
    "Problem",
]

