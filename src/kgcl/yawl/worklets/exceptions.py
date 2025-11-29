"""Custom exceptions for worklet service.

Provides exception hierarchy for worklet operations,
following Python best practices and codebase patterns.
"""

from __future__ import annotations


class WorkletError(Exception):
    """Base exception for all worklet-related errors.

    All worklet exceptions inherit from this base class,
    allowing catch-all exception handling when needed.

    Examples
    --------
    >>> try:
    ...     execute_worklet(worklet)
    ... except WorkletError as e:
    ...     logger.error(f"Worklet error: {e}")
    """

    def __init__(self, message: str, worklet_id: str | None = None) -> None:
        """Initialize worklet error.

        Parameters
        ----------
        message : str
            Error message
        worklet_id : str | None
            Related worklet ID if applicable
        """
        super().__init__(message)
        self.message = message
        self.worklet_id = worklet_id

    def __str__(self) -> str:
        """String representation of error."""
        if self.worklet_id:
            return f"{self.message} (worklet_id={self.worklet_id})"
        return self.message

    def __repr__(self) -> str:
        """Developer representation of error."""
        cls_name = self.__class__.__name__
        if self.worklet_id:
            return f"{cls_name}(message={self.message!r}, worklet_id={self.worklet_id!r})"
        return f"{cls_name}(message={self.message!r})"


class WorkletExecutionError(WorkletError):
    """Raised when worklet execution fails.

    This exception is raised when a worklet cannot be executed,
    such as when workflow-based execution is not supported or
    execution encounters a fatal error.

    Examples
    --------
    >>> raise WorkletExecutionError(worklet_id="wl-001", message="Workflow execution not implemented")
    """

    pass


class WorkletNotFoundError(WorkletError):
    """Raised when a worklet cannot be found.

    Examples
    --------
    >>> raise WorkletNotFoundError(worklet_id="wl-999", message="Worklet not found in repository")
    """

    pass


class WorkletValidationError(WorkletError):
    """Raised when worklet validation fails.

    Examples
    --------
    >>> raise WorkletValidationError(worklet_id="wl-001", message="Worklet missing required specification_uri")
    """

    pass


class RDRTreeError(WorkletError):
    """Raised when RDR tree operations fail.

    Examples
    --------
    >>> raise RDRTreeError(message="Tree node not found", worklet_id=None)
    """

    def __init__(
        self, message: str, tree_id: str | None = None, node_id: str | None = None, worklet_id: str | None = None
    ) -> None:
        """Initialize RDR tree error.

        Parameters
        ----------
        message : str
            Error message
        tree_id : str | None
            Related tree ID if applicable
        node_id : str | None
            Related node ID if applicable
        worklet_id : str | None
            Related worklet ID if applicable
        """
        super().__init__(message, worklet_id)
        self.tree_id = tree_id
        self.node_id = node_id

    def __str__(self) -> str:
        """String representation of error."""
        parts = [self.message]
        if self.tree_id:
            parts.append(f"tree_id={self.tree_id}")
        if self.node_id:
            parts.append(f"node_id={self.node_id}")
        if self.worklet_id:
            parts.append(f"worklet_id={self.worklet_id}")
        return " ".join(parts)

    def __repr__(self) -> str:
        """Developer representation of error."""
        return (
            f"RDRTreeError("
            f"message={self.message!r}, "
            f"tree_id={self.tree_id!r}, "
            f"node_id={self.node_id!r}, "
            f"worklet_id={self.worklet_id!r})"
        )


class RuleEvaluationError(WorkletError):
    """Raised when rule condition evaluation fails.

    Examples
    --------
    >>> raise RuleEvaluationError(message="Invalid condition expression: 'x =='", worklet_id=None)
    """

    def __init__(self, message: str, condition: str | None = None, worklet_id: str | None = None) -> None:
        """Initialize rule evaluation error.

        Parameters
        ----------
        message : str
            Error message
        condition : str | None
            Condition expression that failed
        worklet_id : str | None
            Related worklet ID if applicable
        """
        super().__init__(message, worklet_id)
        self.condition = condition

    def __str__(self) -> str:
        """String representation of error."""
        parts = [self.message]
        if self.condition:
            parts.append(f"condition={self.condition!r}")
        if self.worklet_id:
            parts.append(f"worklet_id={self.worklet_id}")
        return " ".join(parts)

    def __repr__(self) -> str:
        """Developer representation of error."""
        return (
            f"RuleEvaluationError("
            f"message={self.message!r}, "
            f"condition={self.condition!r}, "
            f"worklet_id={self.worklet_id!r})"
        )
