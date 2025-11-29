"""Dynamic form exception.

Custom exception for dynamic form generation errors.

Converted from org.yawlfoundation.yawl.ui.dynform.DynFormException
"""

from __future__ import annotations


class DynFormException(Exception):
    """Exception raised during dynamic form generation.

    Raised when form generation from XSD schema fails due to:
    - Invalid schema structure
    - Missing required elements
    - Type conversion errors
    - Field assembly failures

    Examples
    --------
    >>> raise DynFormException("Failed to parse XSD schema")
    >>> raise DynFormException()  # No message
    """
