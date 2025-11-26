"""YAWL Data Patterns (28-35): Data Visibility and Interaction.

This module implements the 8 YAWL data patterns covering data scoping,
visibility levels, and inter-task/workflow data transfer mechanisms.

Pattern Categories
------------------
**Visibility Patterns (28-32)**: Control data scope across workflow layers
**Interaction Patterns (33-35)**: Define data transfer mechanisms

References
----------
- YAWL Data Patterns: http://www.workflowpatterns.com/patterns/data/
- YAWL Foundation: http://www.yawlfoundation.org/

Examples
--------
>>> # Pattern 28: Task Data (scoped to single task)
>>> task_data = TaskData()
>>> task_data.set(URIRef("urn:task:T1"), "local_var", 42)
>>> assert task_data.get(URIRef("urn:task:T1"), "local_var") == 42

>>> # Pattern 33: Task-to-Task Data Interaction
>>> interaction = DataInteractionTaskToTask(source_task="T1", target_task="T2", mappings={"output_x": "input_y"})
>>> result = interaction.transfer(graph, {"output_x": 100})
>>> assert result["input_y"] == 100
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, cast

from rdflib import Graph, Namespace, URIRef
from rdflib.query import ResultRow

if TYPE_CHECKING:
    from collections.abc import Callable

# YAWL Ontology Namespaces
YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")
YAWL_DATA = Namespace("http://bitflow.ai/ontology/yawl/data/v1#")


class DataScope(str, Enum):
    """Data visibility scope levels (Patterns 28-32).

    Attributes
    ----------
    TASK : str
        Data visible only within a single task instance
    BLOCK : str
        Data visible within a structured block (composite task)
    CASE : str
        Data visible across entire workflow case (instance)
    WORKFLOW : str
        Data visible across all workflow instances (global)
    ENVIRONMENT : str
        Data from external environment (OS, config, services)
    """

    TASK = "task"
    BLOCK = "block"
    CASE = "case"
    WORKFLOW = "workflow"
    ENVIRONMENT = "environment"


# ============================================================================
# VISIBILITY PATTERNS (28-32)
# ============================================================================


@dataclass(frozen=True)
class TaskData:
    """Pattern 28: Task Data - Variables scoped to single task instance.

    Data is visible only within the task that declares it. Once the task
    completes, the data is destroyed unless explicitly passed to another task.

    Attributes
    ----------
    pattern_id : int
        YAWL pattern identifier (28)
    scope : DataScope
        Visibility scope (TASK)
    storage : dict[str, dict[str, Any]]
        Task-local variable storage (task_uri → {var_name → value})

    Examples
    --------
    >>> task_data = TaskData()
    >>> task_uri = URIRef("urn:task:ProcessOrder")
    >>> task_data.set(task_uri, "order_id", "12345")
    >>> assert task_data.get(task_uri, "order_id") == "12345"
    >>> assert task_data.get(URIRef("urn:task:Other"), "order_id") is None
    """

    pattern_id: int = 28
    scope: DataScope = DataScope.TASK
    storage: dict[str, dict[str, Any]] = field(default_factory=dict)

    def get(self, task: URIRef, key: str) -> Any:
        """Retrieve task-local variable.

        Parameters
        ----------
        task : URIRef
            Task URI
        key : str
            Variable name

        Returns
        -------
        Any
            Variable value or None if not found
        """
        task_str = str(task)
        if task_str not in self.storage:
            return None
        return self.storage[task_str].get(key)

    def set(self, task: URIRef, key: str, value: Any) -> None:
        """Set task-local variable.

        Parameters
        ----------
        task : URIRef
            Task URI
        key : str
            Variable name
        value : Any
            Variable value
        """
        task_str = str(task)
        if task_str not in self.storage:
            # Bypass frozen dataclass by using object.__setattr__
            object.__setattr__(self, "storage", {**self.storage, task_str: {key: value}})
        else:
            current_vars = self.storage[task_str].copy()
            current_vars[key] = value
            updated_storage = self.storage.copy()
            updated_storage[task_str] = current_vars
            object.__setattr__(self, "storage", updated_storage)

    def clear_task(self, task: URIRef) -> None:
        """Clear all variables for a task (called on task completion).

        Parameters
        ----------
        task : URIRef
            Task URI to clear
        """
        task_str = str(task)
        if task_str in self.storage:
            updated_storage = self.storage.copy()
            del updated_storage[task_str]
            object.__setattr__(self, "storage", updated_storage)


@dataclass(frozen=True)
class BlockData:
    """Pattern 29: Block Data - Variables scoped to structured block.

    Data is visible to all tasks within a composite task or sub-workflow.
    Block data persists for the lifetime of the block execution.

    Attributes
    ----------
    pattern_id : int
        YAWL pattern identifier (29)
    scope : DataScope
        Visibility scope (BLOCK)
    storage : dict[str, dict[str, Any]]
        Block-scoped variable storage (block_uri → {var_name → value})

    Examples
    --------
    >>> block_data = BlockData()
    >>> block_uri = URIRef("urn:block:OrderProcessing")
    >>> block_data.set(block_uri, "total_amount", 500.0)
    >>> assert block_data.get(block_uri, "total_amount") == 500.0
    """

    pattern_id: int = 29
    scope: DataScope = DataScope.BLOCK
    storage: dict[str, dict[str, Any]] = field(default_factory=dict)

    def get(self, block: URIRef, key: str) -> Any:
        """Retrieve block-scoped variable.

        Parameters
        ----------
        block : URIRef
            Block URI (composite task)
        key : str
            Variable name

        Returns
        -------
        Any
            Variable value or None if not found
        """
        block_str = str(block)
        if block_str not in self.storage:
            return None
        return self.storage[block_str].get(key)

    def set(self, block: URIRef, key: str, value: Any) -> None:
        """Set block-scoped variable.

        Parameters
        ----------
        block : URIRef
            Block URI
        key : str
            Variable name
        value : Any
            Variable value
        """
        block_str = str(block)
        if block_str not in self.storage:
            object.__setattr__(self, "storage", {**self.storage, block_str: {key: value}})
        else:
            current_vars = self.storage[block_str].copy()
            current_vars[key] = value
            updated_storage = self.storage.copy()
            updated_storage[block_str] = current_vars
            object.__setattr__(self, "storage", updated_storage)


@dataclass(frozen=True)
class CaseData:
    """Pattern 30: Case Data - Variables scoped to workflow case instance.

    Data is visible across all tasks in a single workflow instance (case).
    This is the most common data scope in YAWL workflows.

    Attributes
    ----------
    pattern_id : int
        YAWL pattern identifier (30)
    scope : DataScope
        Visibility scope (CASE)
    storage : dict[str, dict[str, Any]]
        Case-scoped variable storage (case_id → {var_name → value})

    Examples
    --------
    >>> case_data = CaseData()
    >>> case_data.set("case-12345", "customer_id", "CUST-999")
    >>> case_data.set("case-12345", "order_total", 1200.0)
    >>> assert case_data.get("case-12345", "customer_id") == "CUST-999"
    """

    pattern_id: int = 30
    scope: DataScope = DataScope.CASE
    storage: dict[str, dict[str, Any]] = field(default_factory=dict)

    def get(self, case_id: str, key: str) -> Any:
        """Retrieve case-scoped variable.

        Parameters
        ----------
        case_id : str
            Workflow case identifier
        key : str
            Variable name

        Returns
        -------
        Any
            Variable value or None if not found
        """
        if case_id not in self.storage:
            return None
        return self.storage[case_id].get(key)

    def set(self, case_id: str, key: str, value: Any) -> None:
        """Set case-scoped variable.

        Parameters
        ----------
        case_id : str
            Workflow case identifier
        key : str
            Variable name
        value : Any
            Variable value
        """
        if case_id not in self.storage:
            object.__setattr__(self, "storage", {**self.storage, case_id: {key: value}})
        else:
            current_vars = self.storage[case_id].copy()
            current_vars[key] = value
            updated_storage = self.storage.copy()
            updated_storage[case_id] = current_vars
            object.__setattr__(self, "storage", updated_storage)

    def get_all(self, case_id: str) -> dict[str, Any]:
        """Get all variables for a case.

        Parameters
        ----------
        case_id : str
            Workflow case identifier

        Returns
        -------
        dict[str, Any]
            All case variables
        """
        return self.storage.get(case_id, {}).copy()


@dataclass(frozen=True)
class WorkflowData:
    """Pattern 31: Workflow Data - Global variables across all instances.

    Data is shared across all instances of a workflow. Changes made by one
    instance are visible to all other instances (requires synchronization).

    Attributes
    ----------
    pattern_id : int
        YAWL pattern identifier (31)
    scope : DataScope
        Visibility scope (WORKFLOW)
    storage : dict[str, Any]
        Global workflow variable storage (var_name → value)

    Examples
    --------
    >>> workflow_data = WorkflowData()
    >>> workflow_data.set("global_counter", 0)
    >>> workflow_data.increment("global_counter", 1)
    >>> assert workflow_data.get("global_counter") == 1
    """

    pattern_id: int = 31
    scope: DataScope = DataScope.WORKFLOW
    storage: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str) -> Any:
        """Retrieve global workflow variable.

        Parameters
        ----------
        key : str
            Variable name

        Returns
        -------
        Any
            Variable value or None if not found
        """
        return self.storage.get(key)

    def set(self, key: str, value: Any) -> None:
        """Set global workflow variable.

        Parameters
        ----------
        key : str
            Variable name
        value : Any
            Variable value
        """
        updated_storage = self.storage.copy()
        updated_storage[key] = value
        object.__setattr__(self, "storage", updated_storage)

    def increment(self, key: str, delta: int) -> int:
        """Atomically increment a numeric global variable.

        Parameters
        ----------
        key : str
            Variable name
        delta : int
            Increment value

        Returns
        -------
        int
            New value after increment
        """
        current = self.get(key) or 0
        new_value = current + delta
        self.set(key, new_value)
        return new_value


@dataclass(frozen=True)
class EnvironmentData:
    """Pattern 32: Environment Data - External data sources.

    Data retrieved from external environment (OS variables, config files,
    web services, databases) at workflow execution time.

    Attributes
    ----------
    pattern_id : int
        YAWL pattern identifier (32)
    scope : DataScope
        Visibility scope (ENVIRONMENT)
    providers : dict[str, Callable[[], Any]]
        External data providers (name → fetch function)

    Examples
    --------
    >>> import os
    >>> env_data = EnvironmentData()
    >>> env_data.register_provider("api_key", lambda: os.getenv("API_KEY"))
    >>> api_key = env_data.get("api_key")
    """

    pattern_id: int = 32
    scope: DataScope = DataScope.ENVIRONMENT
    providers: dict[str, Callable[[], Any]] = field(default_factory=dict)

    def register_provider(self, name: str, fetch_fn: Callable[[], Any]) -> None:
        """Register an external data provider.

        Parameters
        ----------
        name : str
            Provider name (e.g., "database", "api_config")
        fetch_fn : Callable[[], Any]
            Function to fetch data from external source
        """
        updated_providers = self.providers.copy()
        updated_providers[name] = fetch_fn
        object.__setattr__(self, "providers", updated_providers)

    def get(self, name: str) -> Any:
        """Fetch data from external provider.

        Parameters
        ----------
        name : str
            Provider name

        Returns
        -------
        Any
            Fetched data or None if provider not found

        Raises
        ------
        RuntimeError
            If provider function fails
        """
        if name not in self.providers:
            return None
        try:
            return self.providers[name]()
        except Exception as e:
            msg = f"Failed to fetch environment data '{name}': {e}"
            raise RuntimeError(msg) from e


# ============================================================================
# INTERACTION PATTERNS (33-35)
# ============================================================================


@dataclass(frozen=True)
class DataInteractionTaskToTask:
    """Pattern 33: Task-to-Task Data Interaction - Direct data passing.

    Data is explicitly passed from one task to another via variable mappings.
    This is the fundamental mechanism for data flow in YAWL workflows.

    Attributes
    ----------
    pattern_id : int
        YAWL pattern identifier (33)
    source_task : str
        Source task URI
    target_task : str
        Target task URI
    mappings : dict[str, str]
        Variable mappings (source_var → target_var)

    Examples
    --------
    >>> interaction = DataInteractionTaskToTask(
    ...     source_task="urn:task:CalculatePrice",
    ...     target_task="urn:task:GenerateInvoice",
    ...     mappings={"total_price": "invoice_amount", "discount": "discount_applied"},
    ... )
    >>> source_data = {"total_price": 1000.0, "discount": 0.1}
    >>> result = interaction.transfer(Graph(), source_data)
    >>> assert result["invoice_amount"] == 1000.0
    >>> assert result["discount_applied"] == 0.1
    """

    source_task: str
    target_task: str
    mappings: dict[str, str]
    pattern_id: int = 33

    def transfer(self, graph: Graph, source_context: dict[str, Any]) -> dict[str, Any]:
        """Transfer data from source to target task.

        Parameters
        ----------
        graph : Graph
            RDF graph with workflow topology (unused in basic implementation)
        source_context : dict[str, Any]
            Source task's output variables

        Returns
        -------
        dict[str, Any]
            Target task's input variables after mapping

        Examples
        --------
        >>> interaction = DataInteractionTaskToTask(source_task="T1", target_task="T2", mappings={"out": "in"})
        >>> result = interaction.transfer(Graph(), {"out": 42})
        >>> assert result["in"] == 42
        """
        target_context: dict[str, Any] = {}

        for source_var, target_var in self.mappings.items():
            if source_var in source_context:
                target_context[target_var] = source_context[source_var]

        return target_context

    @staticmethod
    def extract_from_graph(graph: Graph, source: URIRef, target: URIRef) -> DataInteractionTaskToTask:
        """Extract task-to-task data mappings from RDF graph.

        Parameters
        ----------
        graph : Graph
            RDF graph with YAWL workflow definition
        source : URIRef
            Source task URI
        target : URIRef
            Target task URI

        Returns
        -------
        DataInteractionTaskToTask
            Data interaction pattern with extracted mappings
        """
        # Query for output mappings from source task
        query = f"""
        PREFIX yawl: <{YAWL}>
        SELECT ?mapping WHERE {{
            <{source}> yawl:outputMapping ?mapping .
        }}
        """
        results = graph.query(query)

        mappings: dict[str, str] = {}
        for row in results:
            if not hasattr(row, "mapping"):
                continue
            row_typed = cast(ResultRow, row)
            mapping_str = str(row_typed.mapping)
            # Parse "source_var -> target_var" format
            if " -> " in mapping_str:
                source_var, target_var = mapping_str.split(" -> ", 1)
                mappings[source_var.strip()] = target_var.strip()

        return DataInteractionTaskToTask(source_task=str(source), target_task=str(target), mappings=mappings)


@dataclass(frozen=True)
class DataInteractionBlockToSubWorkflow:
    """Pattern 34: Block-to-Sub-Workflow Data Interaction.

    Data is passed from a parent workflow block to a nested sub-workflow.
    This enables hierarchical workflow composition with data flow.

    Attributes
    ----------
    pattern_id : int
        YAWL pattern identifier (34)
    parent_block : str
        Parent block/workflow URI
    sub_workflow : str
        Sub-workflow URI
    input_mappings : dict[str, str]
        Parent variables → sub-workflow parameters
    output_mappings : dict[str, str]
        Sub-workflow results → parent variables

    Examples
    --------
    >>> interaction = DataInteractionBlockToSubWorkflow(
    ...     parent_block="urn:workflow:MainProcess",
    ...     sub_workflow="urn:workflow:CreditCheck",
    ...     input_mappings={"customer_id": "input_customer"},
    ...     output_mappings={"credit_score": "output_score"},
    ... )
    >>> parent_data = {"customer_id": "CUST-123"}
    >>> sub_inputs = interaction.transfer_to_sub(parent_data)
    >>> assert sub_inputs["input_customer"] == "CUST-123"
    """

    parent_block: str
    sub_workflow: str
    input_mappings: dict[str, str]
    output_mappings: dict[str, str]
    pattern_id: int = 34

    def transfer_to_sub(self, parent_context: dict[str, Any]) -> dict[str, Any]:
        """Transfer data from parent to sub-workflow (input mappings).

        Parameters
        ----------
        parent_context : dict[str, Any]
            Parent workflow variables

        Returns
        -------
        dict[str, Any]
            Sub-workflow input parameters
        """
        sub_inputs: dict[str, Any] = {}
        for parent_var, sub_param in self.input_mappings.items():
            if parent_var in parent_context:
                sub_inputs[sub_param] = parent_context[parent_var]
        return sub_inputs

    def transfer_to_parent(self, sub_context: dict[str, Any]) -> dict[str, Any]:
        """Transfer data from sub-workflow back to parent (output mappings).

        Parameters
        ----------
        sub_context : dict[str, Any]
            Sub-workflow output variables

        Returns
        -------
        dict[str, Any]
            Parent workflow variables to update
        """
        parent_updates: dict[str, Any] = {}
        for sub_var, parent_var in self.output_mappings.items():
            if sub_var in sub_context:
                parent_updates[parent_var] = sub_context[sub_var]
        return parent_updates


@dataclass(frozen=True)
class DataInteractionCaseToCase:
    """Pattern 35: Case-to-Case Data Interaction - Inter-instance communication.

    Data is shared between different workflow instances (cases). This enables
    workflow orchestration patterns like parent-child relationships, event
    passing, and distributed workflow coordination.

    Attributes
    ----------
    pattern_id : int
        YAWL pattern identifier (35)
    source_case : str
        Source workflow case ID
    target_case : str
        Target workflow case ID
    shared_variables : dict[str, str]
        Variable mappings between cases
    interaction_type : str
        Type of interaction (event, signal, data_copy)

    Examples
    --------
    >>> interaction = DataInteractionCaseToCase(
    ...     source_case="case-001",
    ...     target_case="case-002",
    ...     shared_variables={"order_status": "upstream_status"},
    ...     interaction_type="event",
    ... )
    >>> source_data = {"order_status": "APPROVED"}
    >>> target_data = interaction.transfer(source_data)
    >>> assert target_data["upstream_status"] == "APPROVED"
    """

    source_case: str
    target_case: str
    shared_variables: dict[str, str]
    interaction_type: str = "data_copy"
    pattern_id: int = 35

    def transfer(self, source_context: dict[str, Any]) -> dict[str, Any]:
        """Transfer data from source case to target case.

        Parameters
        ----------
        source_context : dict[str, Any]
            Source case variables

        Returns
        -------
        dict[str, Any]
            Target case variables to update
        """
        target_updates: dict[str, Any] = {}
        for source_var, target_var in self.shared_variables.items():
            if source_var in source_context:
                target_updates[target_var] = source_context[source_var]
        return target_updates

    def is_event_based(self) -> bool:
        """Check if interaction is event-based (asynchronous).

        Returns
        -------
        bool
            True if interaction_type is "event" or "signal"
        """
        return self.interaction_type in {"event", "signal"}


# ============================================================================
# UNIFIED DATA CONTEXT - Integrating All 8 Patterns
# ============================================================================


@dataclass(frozen=True)
class DataContext:
    """Unified data context integrating all 8 visibility and interaction patterns.

    This class provides a single interface for managing workflow data across
    all scoping levels (task, block, case, workflow, environment) and handling
    data transfer between workflow elements.

    Attributes
    ----------
    task_data : TaskData
        Pattern 28: Task-scoped variables
    block_data : BlockData
        Pattern 29: Block-scoped variables
    case_data : CaseData
        Pattern 30: Case-scoped variables
    workflow_data : WorkflowData
        Pattern 31: Global workflow variables
    env_data : EnvironmentData
        Pattern 32: External environment data

    Examples
    --------
    >>> context = DataContext()
    >>> context.case_data.set("case-123", "customer", "CUST-999")
    >>> context.workflow_data.set("instance_count", 42)
    >>> assert context.case_data.get("case-123", "customer") == "CUST-999"
    """

    task_data: TaskData = field(default_factory=TaskData)
    block_data: BlockData = field(default_factory=BlockData)
    case_data: CaseData = field(default_factory=CaseData)
    workflow_data: WorkflowData = field(default_factory=WorkflowData)
    env_data: EnvironmentData = field(default_factory=EnvironmentData)

    def resolve_variable(self, case_id: str, task: URIRef, block: URIRef | None, var_name: str) -> Any:
        """Resolve variable with scope precedence.

        Precedence: task → block → case → workflow → env.

        Parameters
        ----------
        case_id : str
            Current case ID
        task : URIRef
            Current task URI
        block : URIRef | None
            Current block URI (if in composite task)
        var_name : str
            Variable name to resolve

        Returns
        -------
        Any
            Variable value from highest priority scope, or None if not found
        """
        # Scope precedence: TASK > BLOCK > CASE > WORKFLOW > ENVIRONMENT
        value = self.task_data.get(task, var_name)
        if value is not None:
            return value

        if block is not None:
            value = self.block_data.get(block, var_name)
            if value is not None:
                return value

        value = self.case_data.get(case_id, var_name)
        if value is not None:
            return value

        value = self.workflow_data.get(var_name)
        if value is not None:
            return value

        # Fallback to environment
        return self.env_data.get(var_name)
