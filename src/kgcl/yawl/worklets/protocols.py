"""Protocol interfaces for worklet service components.

Defines extensible interfaces using Python Protocols,
allowing flexible implementations while maintaining type safety.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from kgcl.yawl.worklets.models import RDRTree, Worklet, WorkletCase, WorkletType
    from kgcl.yawl.worklets.rules import RuleContext


@runtime_checkable
class WorkletExecutorProtocol(Protocol):
    """Protocol for worklet executor implementations.

    Defines the interface for executing worklets in response
    to exceptions. Implementations can provide different
    execution strategies (sync, async, distributed, etc.).

    Examples
    --------
    >>> class AsyncWorkletExecutor:
    ...     async def handle_case_exception(self, case_id: str, exception_type: str) -> WorkletResult: ...
    >>> executor: WorkletExecutorProtocol = AsyncWorkletExecutor()
    """

    def select_worklet(self, context: RuleContext, task_id: str | None = None) -> Worklet | None:
        """Select appropriate worklet for exception.

        Parameters
        ----------
        context : RuleContext
            Exception context
        task_id : str | None
            Task ID for item-level exceptions

        Returns
        -------
        Worklet | None
            Selected worklet or None
        """
        ...

    def handle_case_exception(
        self, case_id: str, exception_type: str, exception_message: str = "", case_data: dict[str, Any] | None = None
    ) -> Any:  # WorkletResult
        """Handle a case-level exception.

        Parameters
        ----------
        case_id : str
            Parent case ID
        exception_type : str
            Type of exception
        exception_message : str
            Exception message
        case_data : dict[str, Any] | None
            Case data

        Returns
        -------
        Any
            Execution result (WorkletResult)
        """
        ...

    def handle_item_exception(
        self,
        case_id: str,
        work_item_id: str,
        task_id: str,
        exception_type: str,
        exception_message: str = "",
        case_data: dict[str, Any] | None = None,
        work_item_data: dict[str, Any] | None = None,
    ) -> Any:  # WorkletResult
        """Handle a work item exception.

        Parameters
        ----------
        case_id : str
            Parent case ID
        work_item_id : str
            Work item ID
        task_id : str
            Task ID
        exception_type : str
            Type of exception
        exception_message : str
            Exception message
        case_data : dict[str, Any] | None
            Case data
        work_item_data : dict[str, Any] | None
            Work item data

        Returns
        -------
        Any
            Execution result (WorkletResult)
        """
        ...

    def register_worklet(self, worklet: Worklet) -> None:
        """Register a worklet.

        Parameters
        ----------
        worklet : Worklet
            Worklet to register
        """
        ...


@runtime_checkable
class WorkletRepositoryProtocol(Protocol):
    """Protocol for worklet repository implementations.

    Defines the interface for storing and retrieving worklets,
    RDR trees, and worklet cases. Implementations can provide
    different storage backends (in-memory, database, etc.).

    Examples
    --------
    >>> class DatabaseRepository:
    ...     def add_worklet(self, worklet: Worklet) -> None:
    ...         # Store in database
    ...         ...
    >>> repo: WorkletRepositoryProtocol = DatabaseRepository()
    """

    def add_worklet(self, worklet: Worklet) -> None:
        """Add a worklet definition.

        Parameters
        ----------
        worklet : Worklet
            Worklet to add
        """
        ...

    def get_worklet(self, worklet_id: str) -> Worklet | None:
        """Get worklet by ID.

        Parameters
        ----------
        worklet_id : str
            Worklet ID

        Returns
        -------
        Worklet | None
            Worklet or None
        """
        ...

    def find_worklets(self, worklet_type: WorkletType | None = None, enabled_only: bool = True) -> list[Worklet]:
        """Find worklets matching criteria.

        Parameters
        ----------
        worklet_type : WorkletType | None
            Filter by type
        enabled_only : bool
            Only include enabled worklets

        Returns
        -------
        list[Worklet]
            Matching worklets
        """
        ...

    def add_tree(self, tree: RDRTree) -> None:
        """Add an RDR tree.

        Parameters
        ----------
        tree : RDRTree
            Tree to add
        """
        ...

    def get_tree(self, tree_id: str) -> RDRTree | None:
        """Get tree by ID.

        Parameters
        ----------
        tree_id : str
            Tree ID

        Returns
        -------
        RDRTree | None
            Tree or None
        """
        ...

    def add_case(self, case: WorkletCase) -> None:
        """Add a worklet case.

        Parameters
        ----------
        case : WorkletCase
            Case to add
        """
        ...

    def get_case(self, case_id: str) -> WorkletCase | None:
        """Get case by ID.

        Parameters
        ----------
        case_id : str
            Case ID

        Returns
        -------
        WorkletCase | None
            Case or None
        """
        ...


@runtime_checkable
class RDREvaluatorProtocol(Protocol):
    """Protocol for RDR condition evaluators.

    Defines the interface for evaluating condition expressions
    in RDR trees. Implementations can provide different evaluation
    strategies (simple, Python eval, SPARQL, etc.).

    Examples
    --------
    >>> class SafePythonEvaluator:
    ...     def evaluate(self, condition: str, context: RuleContext) -> bool:
    ...         # Safe Python evaluation
    ...         ...
    >>> evaluator: RDREvaluatorProtocol = SafePythonEvaluator()
    """

    def evaluate(self, condition: str, context: RuleContext) -> bool:
        """Evaluate a condition expression.

        Parameters
        ----------
        condition : str
            Condition expression
        context : RuleContext
            Evaluation context

        Returns
        -------
        bool
            Evaluation result

        Raises
        ------
        RuleEvaluationError
            If condition evaluation fails
        """
        ...


@runtime_checkable
class WorkletLoaderProtocol(Protocol):
    """Protocol for worklet loading implementations.

    Defines the interface for loading worklet specifications
    from various sources (files, database, URLs, etc.).

    Examples
    --------
    >>> class FileWorkletLoader:
    ...     def load_worklet(self, uri: str) -> Worklet:
    ...         # Load from file
    ...         ...
    >>> loader: WorkletLoaderProtocol = FileWorkletLoader()
    """

    def load_worklet(self, uri: str) -> Worklet:
        """Load a worklet from URI.

        Parameters
        ----------
        uri : str
            Worklet specification URI

        Returns
        -------
        Worklet
            Loaded worklet

        Raises
        ------
        WorkletNotFoundError
            If worklet cannot be loaded
        WorkletValidationError
            If worklet is invalid
        """
        ...

    def load_worklets(self, uris: list[str]) -> list[Worklet]:
        """Load multiple worklets from URIs.

        Parameters
        ----------
        uris : list[str]
            Worklet specification URIs

        Returns
        -------
        list[Worklet]
            Loaded worklets
        """
        ...
