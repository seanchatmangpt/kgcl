"""Codelet protocol and base class (mirrors Java AbstractCodelet).

Codelets are automated task handlers that execute business logic
without human intervention. They are the Python equivalent of
Java's YAWLServiceGateway and custom codelet implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Protocol, runtime_checkable


class CodeletStatus(Enum):
    """Result status of codelet execution.

    Attributes
    ----------
    SUCCESS : auto
        Execution completed successfully
    FAILURE : auto
        Execution failed
    TIMEOUT : auto
        Execution timed out
    ERROR : auto
        Execution error (exception)
    """

    SUCCESS = auto()
    FAILURE = auto()
    TIMEOUT = auto()
    ERROR = auto()


@dataclass(frozen=True)
class CodeletContext:
    """Context for codelet execution.

    Provides access to work item data and case data during
    codelet execution.

    Parameters
    ----------
    work_item_id : str
        Work item ID
    case_id : str
        Case ID
    task_id : str
        Task ID
    input_data : dict[str, Any]
        Input data from work item
    case_data : dict[str, Any]
        Case-level data
    parameters : dict[str, Any]
        Codelet parameters (from decomposition)
    """

    work_item_id: str
    case_id: str
    task_id: str
    input_data: dict[str, Any] = field(default_factory=dict)
    case_data: dict[str, Any] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)

    def get_input(self, name: str, default: Any = None) -> Any:
        """Get input value.

        Parameters
        ----------
        name : str
            Input name
        default : Any
            Default value

        Returns
        -------
        Any
            Input value
        """
        return self.input_data.get(name, default)

    def get_case_variable(self, name: str, default: Any = None) -> Any:
        """Get case variable.

        Parameters
        ----------
        name : str
            Variable name
        default : Any
            Default value

        Returns
        -------
        Any
            Variable value
        """
        return self.case_data.get(name, default)

    def get_parameter(self, name: str, default: Any = None) -> Any:
        """Get codelet parameter.

        Parameters
        ----------
        name : str
            Parameter name
        default : Any
            Default value

        Returns
        -------
        Any
            Parameter value
        """
        return self.parameters.get(name, default)


@dataclass
class CodeletResult:
    """Result of codelet execution.

    Parameters
    ----------
    status : CodeletStatus
        Execution status
    output_data : dict[str, Any]
        Output data to set on work item
    message : str
        Status message
    error : str | None
        Error message if failed
    duration_ms : int
        Execution duration in milliseconds
    started : datetime
        Execution start time
    completed : datetime | None
        Execution completion time
    """

    status: CodeletStatus
    output_data: dict[str, Any] = field(default_factory=dict)
    message: str = ""
    error: str | None = None
    duration_ms: int = 0
    started: datetime = field(default_factory=datetime.now)
    completed: datetime | None = None

    @property
    def success(self) -> bool:
        """Check if execution was successful.

        Returns
        -------
        bool
            True if SUCCESS status
        """
        return self.status == CodeletStatus.SUCCESS

    @classmethod
    def success_result(cls, output_data: dict[str, Any] | None = None, message: str = "Success") -> CodeletResult:
        """Create success result.

        Parameters
        ----------
        output_data : dict[str, Any] | None
            Output data
        message : str
            Success message

        Returns
        -------
        CodeletResult
            Success result
        """
        return cls(
            status=CodeletStatus.SUCCESS, output_data=output_data or {}, message=message, completed=datetime.now()
        )

    @classmethod
    def failure_result(cls, error: str, output_data: dict[str, Any] | None = None) -> CodeletResult:
        """Create failure result.

        Parameters
        ----------
        error : str
            Error message
        output_data : dict[str, Any] | None
            Partial output data

        Returns
        -------
        CodeletResult
            Failure result
        """
        return cls(status=CodeletStatus.FAILURE, output_data=output_data or {}, error=error, completed=datetime.now())

    @classmethod
    def timeout_result(cls, timeout_seconds: float) -> CodeletResult:
        """Create timeout result.

        Parameters
        ----------
        timeout_seconds : float
            Timeout value

        Returns
        -------
        CodeletResult
            Timeout result
        """
        return cls(
            status=CodeletStatus.TIMEOUT,
            error=f"Execution timed out after {timeout_seconds}s",
            completed=datetime.now(),
        )

    @classmethod
    def error_result(cls, exception: Exception) -> CodeletResult:
        """Create error result from exception.

        Parameters
        ----------
        exception : Exception
            The exception

        Returns
        -------
        CodeletResult
            Error result
        """
        return cls(status=CodeletStatus.ERROR, error=str(exception), completed=datetime.now())


@runtime_checkable
class Codelet(Protocol):
    """Protocol for codelet implementations.

    Any class with an execute method matching this signature
    can be used as a codelet.
    """

    def execute(self, context: CodeletContext) -> CodeletResult:
        """Execute the codelet.

        Parameters
        ----------
        context : CodeletContext
            Execution context

        Returns
        -------
        CodeletResult
            Execution result
        """
        ...


class AbstractCodelet(ABC):
    """Base class for codelet implementations.

    Provides a template method pattern for codelet execution
    with pre/post execution hooks.

    Parameters
    ----------
    name : str
        Codelet name
    description : str
        Codelet description
    """

    def __init__(self, name: str = "", description: str = "") -> None:
        """Initialize codelet.

        Parameters
        ----------
        name : str
            Codelet name
        description : str
            Codelet description
        """
        self.name = name or self.__class__.__name__
        self.description = description

    def execute(self, context: CodeletContext) -> CodeletResult:
        """Execute the codelet with hooks.

        Parameters
        ----------
        context : CodeletContext
            Execution context

        Returns
        -------
        CodeletResult
            Execution result
        """
        started = datetime.now()
        try:
            # Pre-execution hook
            self.pre_execute(context)

            # Main execution
            result = self.do_execute(context)

            # Post-execution hook
            self.post_execute(context, result)

            # Set timing
            completed = datetime.now()
            result.completed = completed
            result.duration_ms = int((completed - started).total_seconds() * 1000)
            result.started = started

            return result

        except Exception as e:
            result = CodeletResult.error_result(e)
            result.started = started
            return result

    def pre_execute(self, context: CodeletContext) -> None:  # noqa: B027
        """Pre-execution hook (optional, default is no-op).

        Override to add pre-processing logic before do_execute runs.

        Parameters
        ----------
        context : CodeletContext
            Execution context
        """

    @abstractmethod
    def do_execute(self, context: CodeletContext) -> CodeletResult:
        """Main execution logic.

        Override to implement the codelet's business logic.

        Parameters
        ----------
        context : CodeletContext
            Execution context

        Returns
        -------
        CodeletResult
            Execution result
        """

    def post_execute(self, context: CodeletContext, result: CodeletResult) -> None:  # noqa: B027
        """Post-execution hook (optional, default is no-op).

        Override to add post-processing logic after do_execute completes.

        Parameters
        ----------
        context : CodeletContext
            Execution context
        result : CodeletResult
            Execution result
        """
