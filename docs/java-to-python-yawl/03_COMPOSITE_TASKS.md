# Gap 3: Composite Task Subprocess Execution

## Problem Statement

Composite tasks (subnets) are defined but NOT executed. When a composite task fires, it should spawn a new net runner for the subprocess.

## Current State

```python
# src/kgcl/yawl/elements/y_composite_task.py
@dataclass
class YCompositeTask(YTask):
    """Composite task that decomposes into a subnet."""

    task_type: TaskType = TaskType.COMPOSITE
    decomposition_id: str | None = None  # Reference to subnet
```

```python
# src/kgcl/yawl/engine/y_engine.py - NO composite handling
def _create_work_item(self, case, task, net_id):
    # Creates work item but doesn't spawn subprocess
    pass
```

**Problem**: Composite tasks treated as atomic - no subprocess execution.

## Target Behavior

```
Composite Task becomes enabled
         │
         ▼
┌─────────────────────────────────┐
│  Create work item for composite │
│  status = EXECUTING             │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Look up decomposition (subnet) │
│  from specification             │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Create YNetRunner for subnet   │
│  Initialize with input data     │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Subnet executes to completion  │
│  (may have its own composites)  │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  On subnet completion:          │
│  - Extract output data          │
│  - Complete composite work item │
│  - Fire composite task in net   │
└─────────────────────────────────┘
```

## Implementation Plan

### Step 1: Track Subnet Runners

```python
# src/kgcl/yawl/engine/y_engine.py

@dataclass
class YEngine:
    # ... existing fields ...

    # Nested: runner_key → parent_runner_key
    subnet_parents: dict[str, str] = field(default_factory=dict)

    # Work item → subnet runner key
    composite_work_items: dict[str, str] = field(default_factory=dict)
```

### Step 2: Spawn Subnet on Composite Task

```python
def _resource_work_item(self, work_item: YWorkItem, task: YTask) -> None:
    """Resource a work item based on task configuration."""
    from kgcl.yawl.elements.y_composite_task import YCompositeTask

    if isinstance(task, YCompositeTask):
        # Don't offer to resources - execute as subprocess
        self._execute_composite_task(work_item, task)
    else:
        # Normal resourcing logic
        work_item.fire()
        # ... existing code ...


def _execute_composite_task(
    self,
    work_item: YWorkItem,
    task: YCompositeTask,
) -> None:
    """Execute composite task as subprocess.

    Parameters
    ----------
    work_item : YWorkItem
        Work item for the composite task
    task : YCompositeTask
        Composite task definition
    """
    case = self.cases.get(work_item.case_id)
    if case is None:
        return

    spec = self.specifications.get(case.specification_id)
    if spec is None:
        return

    # Get the subnet (decomposition)
    if task.decomposition_id is None:
        # No decomposition - treat as no-op
        work_item.complete({})
        return

    subnet = spec.decompositions.get(task.decomposition_id)
    if subnet is None:
        work_item.fail(f"Decomposition not found: {task.decomposition_id}")
        return

    # Mark work item as executing
    work_item.status = WorkItemStatus.EXECUTING
    work_item.started_time = datetime.now()

    # Create runner for subnet
    parent_runner_key = f"{case.id}:{work_item.net_id}"
    subnet_runner_key = f"{case.id}:{subnet.id}:{work_item.id}"

    subnet_runner = YNetRunner(
        net=subnet,
        case_id=case.id,
        specification_id=case.specification_id,
    )

    # Initialize with input data (from data bindings)
    input_data = self._extract_composite_input(work_item, task, case)
    subnet_runner.initialize(input_data)

    # Store runner
    self.net_runners[subnet_runner_key] = subnet_runner
    self.subnet_parents[subnet_runner_key] = parent_runner_key
    self.composite_work_items[work_item.id] = subnet_runner_key

    # Create work items for enabled tasks in subnet
    self._create_work_items_for_enabled_tasks(case, subnet_runner)

    self._emit_event(
        "SUBNET_STARTED",
        case_id=case.id,
        work_item_id=work_item.id,
        subnet_id=subnet.id,
        data={"parent_net": work_item.net_id},
    )


def _extract_composite_input(
    self,
    work_item: YWorkItem,
    task: YCompositeTask,
    case: YCase,
) -> dict[str, Any]:
    """Extract input data for composite task subprocess.

    Uses task's input bindings to map case data to subnet variables.
    """
    input_data = {}

    # Get input bindings from task
    for binding in task.input_bindings:
        # Evaluate XPath expression against case data
        value = self._evaluate_expression(binding.expression, case.data.variables)
        input_data[binding.target_variable] = value

    return input_data
```

### Step 3: Handle Subnet Completion

```python
def complete_work_item(
    self,
    work_item_id: str,
    output_data: dict[str, Any] | None = None,
) -> bool:
    """Complete a work item."""
    work_item = self._find_work_item(work_item_id)
    if work_item is None:
        return False

    case = self.cases.get(work_item.case_id)
    if case is None:
        return False

    # Get runner for this work item's net
    runner_key = f"{case.id}:{work_item.net_id}"
    runner = self.net_runners.get(runner_key)

    if runner:
        try:
            runner.fire_task(work_item.task_id, output_data)
        except ValueError:
            pass

        if runner.completed:
            # Check if this is a subnet
            if runner_key in self.subnet_parents:
                self._complete_subnet(runner_key, case, output_data)
            else:
                # Top-level net completed
                case.complete(output_data)
                self._emit_event("CASE_COMPLETED", case_id=case.id)
        else:
            self._create_work_items_for_enabled_tasks(case, runner)

    return True


def _complete_subnet(
    self,
    subnet_runner_key: str,
    case: YCase,
    output_data: dict[str, Any] | None,
) -> None:
    """Handle subnet completion.

    Parameters
    ----------
    subnet_runner_key : str
        Key of the completed subnet runner
    case : YCase
        Parent case
    output_data : dict[str, Any] | None
        Output from subnet
    """
    # Find composite work item
    composite_wi_id = None
    for wi_id, runner_key in self.composite_work_items.items():
        if runner_key == subnet_runner_key:
            composite_wi_id = wi_id
            break

    if composite_wi_id is None:
        return

    composite_wi = self._find_work_item(composite_wi_id)
    if composite_wi is None:
        return

    # Get output bindings and apply to case data
    spec = self.specifications.get(case.specification_id)
    if spec:
        task = spec.get_task(composite_wi.task_id)
        if isinstance(task, YCompositeTask):
            self._apply_composite_output(task, output_data, case)

    # Complete the composite work item
    composite_wi.complete(output_data)

    # Fire the composite task in parent net
    parent_runner_key = self.subnet_parents.get(subnet_runner_key)
    if parent_runner_key:
        parent_runner = self.net_runners.get(parent_runner_key)
        if parent_runner:
            try:
                parent_runner.fire_task(composite_wi.task_id, output_data)
            except ValueError:
                pass

            if parent_runner.completed:
                # Check if parent is also a subnet
                if parent_runner_key in self.subnet_parents:
                    self._complete_subnet(parent_runner_key, case, output_data)
                else:
                    case.complete(output_data)
                    self._emit_event("CASE_COMPLETED", case_id=case.id)
            else:
                self._create_work_items_for_enabled_tasks(case, parent_runner)

    # Cleanup
    del self.net_runners[subnet_runner_key]
    del self.subnet_parents[subnet_runner_key]
    del self.composite_work_items[composite_wi_id]

    self._emit_event(
        "SUBNET_COMPLETED",
        case_id=case.id,
        work_item_id=composite_wi_id,
        data={"output": output_data},
    )


def _apply_composite_output(
    self,
    task: YCompositeTask,
    output_data: dict[str, Any] | None,
    case: YCase,
) -> None:
    """Apply output bindings from composite task to case data."""
    if output_data is None:
        return

    for binding in task.output_bindings:
        # Get value from subnet output
        value = output_data.get(binding.source_variable)
        if value is not None:
            # Apply to case data using target expression
            # Simplified: direct assignment
            case.data.set_variable(binding.target_variable, value)
```

### Step 4: Extend YCompositeTask

```python
# src/kgcl/yawl/elements/y_composite_task.py

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DataBinding:
    """Data binding for composite task input/output.

    Parameters
    ----------
    expression : str
        XPath expression for source data
    target_variable : str
        Variable name in target scope
    source_variable : str | None
        Variable name in source scope (for output bindings)
    """

    expression: str
    target_variable: str
    source_variable: str | None = None


@dataclass
class YCompositeTask(YTask):
    """Composite task that decomposes into a subnet.

    Composite tasks execute a subprocess (subnet) when fired.
    The subnet runs to completion before the composite task completes.

    Parameters
    ----------
    decomposition_id : str | None
        ID of the subnet (YNet) to execute
    input_bindings : list[DataBinding]
        Bindings to map case data to subnet input
    output_bindings : list[DataBinding]
        Bindings to map subnet output to case data
    """

    task_type: TaskType = TaskType.COMPOSITE
    decomposition_id: str | None = None
    input_bindings: list[DataBinding] = field(default_factory=list)
    output_bindings: list[DataBinding] = field(default_factory=list)
```

## Recursive Subnets

Composite tasks can contain other composite tasks. The implementation handles this naturally:

1. Subnet runner completes
2. Check if parent is also a subnet
3. If yes, recursively complete parent subnet
4. Eventually reaches top-level net

```
Top Net
  └─► Composite A
        └─► Subnet A
              └─► Composite B
                    └─► Subnet B (deepest)
                          │
                          ▼
                    Subnet B completes
                          │
                          ▼
                    Composite B completes
                          │
                          ▼
                    Subnet A continues/completes
                          │
                          ▼
                    Composite A completes
                          │
                          ▼
                    Top Net continues/completes
```

## Test Cases

```python
class TestCompositeTasks:
    """Tests for composite task subprocess execution."""

    def test_composite_spawns_subnet(self) -> None:
        """Composite task creates subnet runner."""
        # Create spec with composite task referencing subnet
        # Start case
        # Complete start task
        # Assert: subnet runner created
        # Assert: work items for subnet tasks exist

    def test_subnet_completion_fires_parent(self) -> None:
        """Subnet completion fires composite task in parent net."""
        # Create case with composite task
        # Complete all subnet tasks
        # Assert: composite work item completed
        # Assert: next task in parent net enabled

    def test_nested_composites(self) -> None:
        """Composite inside composite works correctly."""
        # Three-level nesting
        # Complete deepest subnet
        # Assert: middle composite fires
        # Complete middle subnet
        # Assert: outer composite fires

    def test_input_bindings(self) -> None:
        """Input bindings map data to subnet."""
        # Composite with input binding /order/total → subnet_total
        # Assert: subnet runner has subnet_total in initial data

    def test_output_bindings(self) -> None:
        """Output bindings map subnet results to case."""
        # Composite with output binding result → /order/status
        # Complete subnet with result = "approved"
        # Assert: case.data has /order/status = "approved"

    def test_composite_cancellation(self) -> None:
        """Cancelling case cancels subnet runners."""
        # Start case with active subnet
        # Cancel case
        # Assert: subnet runner cleaned up
        # Assert: no dangling work items
```

## Dependencies

- **Data Binding (Gap 9)**: For input/output mapping with XPath
- **Expression Evaluation (Gap 11)**: For evaluating binding expressions

## Complexity: MEDIUM

- Runner lifecycle management
- Data flow between nets
- Recursive completion handling

## Estimated Effort

- Implementation: 6-8 hours
- Testing: 4-6 hours
- Total: 1.5-2 days

## Priority: MEDIUM

Composite tasks are common in complex workflows but not blocking basic execution.
