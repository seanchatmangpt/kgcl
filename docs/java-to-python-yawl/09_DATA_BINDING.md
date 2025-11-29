# Gap 9: Data Binding Evaluation

## Problem Statement

YAWL uses data bindings to map data between case variables and work item inputs/outputs. Currently, bindings are defined but not evaluated.

## YAWL Data Binding Model

```
Case Data (net-level variables)
      │
      │  INPUT BINDING (XPath expression)
      │  Maps case data → work item input
      ▼
┌──────────────────┐
│    Work Item     │
│  (task-level)    │
│                  │
│  Input Data      │
│  Output Data     │
└──────────────────┘
      │
      │  OUTPUT BINDING (XPath expression)
      │  Maps work item output → case data
      ▼
Case Data (updated)
```

## Current State

```python
# src/kgcl/yawl/elements/y_atomic_task.py
@dataclass
class YAtomicTask(YTask):
    # Binding definitions exist but aren't used
    input_bindings: list[str] = field(default_factory=list)
    output_bindings: list[str] = field(default_factory=list)


# src/kgcl/yawl/engine/y_engine.py
def _create_work_item(self, case, task, net_id):
    # Work item created with empty data
    # No input binding evaluation
    pass

def complete_work_item(self, work_item_id, output_data):
    # Output stored on work item
    # Not mapped back to case data via output binding
    pass
```

**Problems**:
- Input bindings not evaluated when work item created
- Output bindings not applied when work item completes
- No variable scoping between net levels

## Target Behavior

### Input Binding Flow
```
Case has data: {order: {id: "123", items: [...], total: 500}}

Task "ProcessOrder" has input binding:
  /order/total → order_total
  /order/id → order_id

Work Item created with input_data:
  {order_total: 500, order_id: "123"}
```

### Output Binding Flow
```
Work Item completes with output:
  {approved: true, approver: "Alice"}

Task has output binding:
  /approved → /order/approval_status
  /approver → /order/approved_by

Case data updated:
  {order: {..., approval_status: true, approved_by: "Alice"}}
```

## Implementation Plan

### Step 1: Data Binding Definition

```python
# src/kgcl/yawl/elements/y_data_binding.py
"""Data binding definitions for YAWL tasks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BindingDirection(Enum):
    """Data binding direction."""

    INPUT = "input"      # Case → Work Item
    OUTPUT = "output"    # Work Item → Case


@dataclass(frozen=True)
class YDataBinding:
    """Data binding between case and work item.

    Parameters
    ----------
    expression : str
        XPath expression for source data extraction
    target : str
        Target variable/path for data placement
    direction : BindingDirection
        Binding direction (input/output)
    query : str | None
        Additional XQuery for transformation
    default : str | None
        Default value if source is empty
    """

    expression: str
    target: str
    direction: BindingDirection
    query: str | None = None
    default: str | None = None

    def is_input(self) -> bool:
        """Check if input binding."""
        return self.direction == BindingDirection.INPUT

    def is_output(self) -> bool:
        """Check if output binding."""
        return self.direction == BindingDirection.OUTPUT


@dataclass(frozen=True)
class YVariableDeclaration:
    """Variable declaration for task or net.

    Parameters
    ----------
    name : str
        Variable name
    data_type : str
        XSD data type (string, int, boolean, etc.)
    namespace : str | None
        XML namespace for complex types
    initial_value : str | None
        Initial value expression
    mandatory : bool
        Whether variable must have value
    """

    name: str
    data_type: str = "string"
    namespace: str | None = None
    initial_value: str | None = None
    mandatory: bool = False
```

### Step 2: Extend YAtomicTask

```python
# src/kgcl/yawl/elements/y_atomic_task.py

from kgcl.yawl.elements.y_data_binding import (
    YDataBinding,
    YVariableDeclaration,
    BindingDirection,
)

@dataclass
class YAtomicTask(YTask):
    # ... existing fields ...

    # Data binding
    input_bindings: list[YDataBinding] = field(default_factory=list)
    output_bindings: list[YDataBinding] = field(default_factory=list)
    local_variables: list[YVariableDeclaration] = field(default_factory=list)

    def add_input_binding(
        self,
        expression: str,
        target: str,
        query: str | None = None,
    ) -> None:
        """Add input binding from case to work item."""
        binding = YDataBinding(
            expression=expression,
            target=target,
            direction=BindingDirection.INPUT,
            query=query,
        )
        self.input_bindings.append(binding)

    def add_output_binding(
        self,
        expression: str,
        target: str,
        query: str | None = None,
    ) -> None:
        """Add output binding from work item to case."""
        binding = YDataBinding(
            expression=expression,
            target=target,
            direction=BindingDirection.OUTPUT,
            query=query,
        )
        self.output_bindings.append(binding)
```

### Step 3: Data Binding Evaluator

```python
# src/kgcl/yawl/engine/y_data_binder.py
"""Data binding evaluation for YAWL workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_data_binding import YDataBinding
    from kgcl.yawl.expression.y_expression import YExpressionEvaluator


@dataclass
class YDataBinder:
    """Evaluator for data bindings.

    Handles extraction and placement of data between
    case variables and work item data.

    Parameters
    ----------
    expression_evaluator : YExpressionEvaluator
        Evaluator for XPath/XQuery expressions
    """

    expression_evaluator: Any  # YExpressionEvaluator

    def evaluate_input_bindings(
        self,
        bindings: list[YDataBinding],
        case_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate input bindings to create work item input.

        Parameters
        ----------
        bindings : list[YDataBinding]
            Input binding definitions
        case_data : dict[str, Any]
            Source case data

        Returns
        -------
        dict[str, Any]
            Work item input data
        """
        result = {}

        for binding in bindings:
            if not binding.is_input():
                continue

            # Evaluate source expression against case data
            value = self._evaluate_expression(binding.expression, case_data)

            # Apply transformation query if present
            if binding.query and value is not None:
                value = self._evaluate_expression(
                    binding.query,
                    {"_value": value, **case_data},
                )

            # Use default if value is None
            if value is None and binding.default is not None:
                value = self._evaluate_expression(binding.default, case_data)

            # Set in result at target path
            self._set_value_at_path(result, binding.target, value)

        return result

    def evaluate_output_bindings(
        self,
        bindings: list[YDataBinding],
        work_item_output: dict[str, Any],
        case_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate output bindings to update case data.

        Parameters
        ----------
        bindings : list[YDataBinding]
            Output binding definitions
        work_item_output : dict[str, Any]
            Work item output data
        case_data : dict[str, Any]
            Current case data (will be modified)

        Returns
        -------
        dict[str, Any]
            Updated case data
        """
        for binding in bindings:
            if not binding.is_output():
                continue

            # Evaluate source expression against work item output
            value = self._evaluate_expression(
                binding.expression,
                work_item_output,
            )

            # Apply transformation query if present
            if binding.query and value is not None:
                value = self._evaluate_expression(
                    binding.query,
                    {"_value": value, **work_item_output},
                )

            # Use default if value is None
            if value is None and binding.default is not None:
                value = self._evaluate_expression(
                    binding.default, work_item_output
                )

            # Set in case data at target path
            self._set_value_at_path(case_data, binding.target, value)

        return case_data

    def _evaluate_expression(
        self,
        expression: str,
        context: dict[str, Any],
    ) -> Any:
        """Evaluate XPath expression."""
        if self.expression_evaluator:
            return self.expression_evaluator.evaluate(expression, context)

        # Fallback: simple path lookup
        return self._simple_path_lookup(expression, context)

    def _simple_path_lookup(
        self,
        path: str,
        data: dict[str, Any],
    ) -> Any:
        """Simple path lookup without XPath."""
        # Handle /root/child/value format
        parts = path.strip("/").split("/")
        current = data

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            if current is None:
                return None

        return current

    def _set_value_at_path(
        self,
        data: dict[str, Any],
        path: str,
        value: Any,
    ) -> None:
        """Set value at path in dictionary.

        Creates intermediate dictionaries as needed.

        Parameters
        ----------
        data : dict[str, Any]
            Target dictionary
        path : str
            Path like "/order/status" or "order_status"
        value : Any
            Value to set
        """
        # Handle simple variable name
        if "/" not in path:
            data[path] = value
            return

        # Handle path format
        parts = path.strip("/").split("/")
        current = data

        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value
```

### Step 4: Engine Integration

```python
# src/kgcl/yawl/engine/y_engine.py

from kgcl.yawl.engine.y_data_binder import YDataBinder

@dataclass
class YEngine:
    # ... existing fields ...

    data_binder: YDataBinder | None = None

    def __post_init__(self) -> None:
        """Initialize data binder."""
        if self.data_binder is None:
            # Use expression evaluator if available
            from kgcl.yawl.expression.y_simple_expr import YSimpleEvaluator
            self.data_binder = YDataBinder(
                expression_evaluator=YSimpleEvaluator()
            )

    def _create_work_item(
        self,
        case: YCase,
        task: YTask,
        net_id: str,
    ) -> YWorkItem:
        """Create work item with input data from bindings."""
        self.work_item_counter += 1

        # Evaluate input bindings
        input_data = {}
        if isinstance(task, YAtomicTask) and task.input_bindings:
            input_data = self.data_binder.evaluate_input_bindings(
                task.input_bindings,
                case.data.variables,
            )

        work_item = YWorkItem(
            id=f"WI-{self.work_item_counter}",
            case_id=case.id,
            task_id=task.id,
            specification_id=case.specification_id,
            net_id=net_id,
            data_input=input_data,  # Populated from bindings
        )

        case.add_work_item(work_item)

        self._emit_event(
            "WORK_ITEM_CREATED",
            case_id=case.id,
            work_item_id=work_item.id,
            task_id=task.id,
            data={"input_data": input_data},
        )

        return work_item

    def complete_work_item(
        self,
        work_item_id: str,
        output_data: dict[str, Any] | None = None,
    ) -> bool:
        """Complete work item and apply output bindings."""
        work_item = self._find_work_item(work_item_id)
        if work_item is None:
            return False

        # ... existing completion logic ...

        # Apply output bindings
        case = self.cases.get(work_item.case_id)
        if case and output_data:
            spec = self.specifications.get(case.specification_id)
            if spec:
                task = spec.get_task(work_item.task_id)
                if isinstance(task, YAtomicTask) and task.output_bindings:
                    self.data_binder.evaluate_output_bindings(
                        task.output_bindings,
                        output_data,
                        case.data.variables,
                    )

        # Store output on work item
        work_item.complete(output_data)

        # ... rest of completion logic ...
```

### Step 5: Variable Scoping

```python
# src/kgcl/yawl/state/y_case_data.py
"""Case data management with variable scoping."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class YCaseData:
    """Case data container with net-level scoping.

    Variables can be scoped to:
    - Case level (accessible everywhere)
    - Net level (accessible within net and subnets)
    - Task level (local to task execution)

    Parameters
    ----------
    variables : dict[str, Any]
        Case-level variables
    net_variables : dict[str, dict[str, Any]]
        Net-scoped variables (net_id → variables)
    """

    variables: dict[str, Any] = field(default_factory=dict)
    net_variables: dict[str, dict[str, Any]] = field(default_factory=dict)

    def get_variable(
        self,
        name: str,
        net_id: str | None = None,
    ) -> Any:
        """Get variable value with scoping.

        Checks net scope first, then case scope.

        Parameters
        ----------
        name : str
            Variable name
        net_id : str | None
            Net scope (if applicable)

        Returns
        -------
        Any
            Variable value or None
        """
        # Check net scope
        if net_id and net_id in self.net_variables:
            net_vars = self.net_variables[net_id]
            if name in net_vars:
                return net_vars[name]

        # Check case scope
        return self.variables.get(name)

    def set_variable(
        self,
        name: str,
        value: Any,
        net_id: str | None = None,
    ) -> None:
        """Set variable value with scoping.

        Parameters
        ----------
        name : str
            Variable name
        value : Any
            Value to set
        net_id : str | None
            Net scope (None for case level)
        """
        if net_id:
            if net_id not in self.net_variables:
                self.net_variables[net_id] = {}
            self.net_variables[net_id][name] = value
        else:
            self.variables[name] = value

    def get_context_for_net(self, net_id: str) -> dict[str, Any]:
        """Get combined variables for a net context.

        Merges case and net variables, net takes precedence.

        Parameters
        ----------
        net_id : str
            Net identifier

        Returns
        -------
        dict[str, Any]
            Combined variables
        """
        context = dict(self.variables)
        if net_id in self.net_variables:
            context.update(self.net_variables[net_id])
        return context

    def merge_from_subnet(
        self,
        subnet_id: str,
        parent_net_id: str,
        output_mappings: dict[str, str],
    ) -> None:
        """Merge subnet outputs to parent net scope.

        Parameters
        ----------
        subnet_id : str
            Completed subnet ID
        parent_net_id : str
            Parent net ID
        output_mappings : dict[str, str]
            subnet_var → parent_var mappings
        """
        subnet_vars = self.net_variables.get(subnet_id, {})

        for src_var, target_var in output_mappings.items():
            if src_var in subnet_vars:
                self.set_variable(target_var, subnet_vars[src_var], parent_net_id)

        # Cleanup subnet scope
        self.net_variables.pop(subnet_id, None)
```

## Test Cases

```python
class TestDataBinding:
    """Tests for data binding evaluation."""

    def test_input_binding_extracts_value(self) -> None:
        """Input binding extracts value from case data."""
        case_data = {"order": {"total": 500}}
        binding = YDataBinding(
            expression="/order/total",
            target="order_total",
            direction=BindingDirection.INPUT,
        )
        result = binder.evaluate_input_bindings([binding], case_data)
        assert result["order_total"] == 500

    def test_output_binding_updates_case(self) -> None:
        """Output binding updates case data."""
        case_data = {"order": {"id": "123"}}
        output = {"approved": True}
        binding = YDataBinding(
            expression="/approved",
            target="/order/status",
            direction=BindingDirection.OUTPUT,
        )
        binder.evaluate_output_bindings([binding], output, case_data)
        assert case_data["order"]["status"] is True

    def test_default_value_used(self) -> None:
        """Default value used when source empty."""
        binding = YDataBinding(
            expression="/missing",
            target="value",
            direction=BindingDirection.INPUT,
            default="default_value",
        )
        result = binder.evaluate_input_bindings([binding], {})
        assert result["value"] == "default_value"

    def test_transformation_query(self) -> None:
        """Transformation query applied to value."""
        # binding with query that transforms value

    def test_nested_path_creation(self) -> None:
        """Nested paths created automatically."""
        binding = YDataBinding(
            expression="/value",
            target="/deeply/nested/path",
            direction=BindingDirection.OUTPUT,
        )
        case_data = {}
        binder.evaluate_output_bindings([binding], {"value": 42}, case_data)
        assert case_data["deeply"]["nested"]["path"] == 42

    def test_work_item_receives_input_data(self) -> None:
        """Work item created with input data from bindings."""
        # Create task with input bindings
        # Create work item
        # Assert: work_item.data_input populated

    def test_case_updated_on_completion(self) -> None:
        """Case data updated when work item completes."""
        # Task with output bindings
        # Complete work item with output
        # Assert: case.data.variables updated

    def test_variable_scoping(self) -> None:
        """Net-scoped variables shadow case variables."""
        data = YCaseData()
        data.set_variable("x", "case_value")
        data.set_variable("x", "net_value", net_id="net1")
        assert data.get_variable("x", "net1") == "net_value"
        assert data.get_variable("x") == "case_value"
```

## Dependencies

- **Expression Evaluation (Gap 11)**: For XPath/XQuery evaluation

## Complexity: MEDIUM

- Path parsing and manipulation
- Variable scoping
- Integration with work item lifecycle

## Estimated Effort

- Implementation: 6-8 hours
- Testing: 4-6 hours
- Total: 1.5-2 days

## Priority: HIGH

Blocks proper task input/output mapping. Required for most real workflows.
