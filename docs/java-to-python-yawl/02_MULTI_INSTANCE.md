# Gap 2: Multi-Instance Tasks (WCP 12-15)

## Problem Statement

Multi-instance (MI) tasks spawn multiple concurrent work items for a single task. This supports patterns like "review each line item in parallel" or "get approval from 3 of 5 committee members".

## Workflow Control Patterns

| Pattern | Name | Description |
|---------|------|-------------|
| WCP-12 | MI Without Synchronization | Fire-and-forget instances |
| WCP-13 | MI With Design-Time Knowledge | Fixed count known at design |
| WCP-14 | MI With Runtime Knowledge | Count from query at runtime |
| WCP-15 | MI Without a Priori Knowledge | Instances added dynamically |

## Current Implementation

### Defined but not wired:

```python
# src/kgcl/yawl/elements/y_multi_instance.py
@dataclass(frozen=True)
class YMultiInstanceAttributes:
    minimum: int = 1
    maximum: int | None = None
    threshold: int = 1
    creation_mode: MICreationMode = MICreationMode.STATIC
    completion_mode: MICompletionMode = MICompletionMode.ALL
    min_query: str | None = None
    max_query: str | None = None
    threshold_query: str | None = None

# src/kgcl/yawl/elements/y_atomic_task.py
@dataclass
class YMultipleInstanceTask(YAtomicTask):
    task_type: TaskType = TaskType.MULTIPLE_ATOMIC
    mi_minimum: int = 1
    mi_maximum: int = 1
    mi_threshold: int = 1
    mi_creation_mode: str = "static"
    mi_query: str | None = None
    mi_unique_input_expression: str | None = None
    mi_input_joiner: str | None = None
    mi_output_query: str | None = None
```

**Problem**: Engine ignores MI attributes, creates single work item.

## Target Behavior

### Execution Flow
```
MI Task becomes enabled
         │
         ▼
┌─────────────────────────────────┐
│  Evaluate mi_query to get       │
│  instance count (or use static) │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Create PARENT work item        │
│  status = PARENT                │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  For each instance (1..N):      │
│    - Create CHILD work item     │
│    - Extract unique input data  │
│    - Link to parent             │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Children execute in parallel   │
│  Each follows normal lifecycle  │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  On each child completion:      │
│    - Check threshold            │
│    - If threshold met:          │
│      - Aggregate outputs        │
│      - Complete parent          │
│      - Fire task in net         │
└─────────────────────────────────┘
```

## Implementation Plan

### 1. Extend YWorkItem for Parent/Child

```python
# src/kgcl/yawl/engine/y_work_item.py

@dataclass
class YWorkItem:
    # ... existing fields ...

    # Multi-instance fields
    parent_id: str | None = None      # For child work items
    children: list[str] = field(default_factory=list)  # For parent
    instance_index: int | None = None  # Which instance (0, 1, 2...)
    instance_data: dict[str, Any] = field(default_factory=dict)  # Per-instance input

    def is_mi_parent(self) -> bool:
        """Check if this is an MI parent work item."""
        return self.status == WorkItemStatus.PARENT

    def is_mi_child(self) -> bool:
        """Check if this is an MI child work item."""
        return self.parent_id is not None
```

### 2. MI Execution in YEngine

```python
# src/kgcl/yawl/engine/y_engine.py

def _create_work_items_for_enabled_tasks(
    self,
    case: YCase,
    runner: YNetRunner,
) -> list[YWorkItem]:
    """Create work items for all enabled tasks."""
    work_items = []
    enabled_task_ids = runner.get_enabled_tasks()

    for task_id in enabled_task_ids:
        # Check for existing active work items
        existing = case.get_work_items_for_task(task_id)
        active_existing = [wi for wi in existing if wi.is_active()]
        if active_existing:
            continue

        task = runner.net.tasks.get(task_id)
        if task is None:
            continue

        # Check if MI task
        if isinstance(task, YMultipleInstanceTask):
            mi_items = self._create_mi_work_items(case, task, runner.net.id)
            work_items.extend(mi_items)
        else:
            work_item = self._create_work_item(case, task, runner.net.id)
            work_items.append(work_item)
            self._resource_work_item(work_item, task)

    return work_items


def _create_mi_work_items(
    self,
    case: YCase,
    task: YMultipleInstanceTask,
    net_id: str,
) -> list[YWorkItem]:
    """Create work items for multi-instance task.

    Parameters
    ----------
    case : YCase
        Case containing the work items
    task : YMultipleInstanceTask
        MI task definition
    net_id : str
        Net containing the task

    Returns
    -------
    list[YWorkItem]
        Created work items (parent + children)
    """
    work_items = []

    # Determine instance count
    if task.mi_creation_mode == "static":
        count = task.mi_maximum
    else:
        # Dynamic: evaluate mi_query
        count = self._evaluate_mi_count(task, case.data)

    # Clamp to min/max
    count = max(task.mi_minimum, min(count, task.mi_maximum or count))

    # Create parent work item
    parent = self._create_work_item(case, task, net_id)
    parent.status = WorkItemStatus.PARENT
    work_items.append(parent)

    # Create child work items
    instance_data_list = self._extract_mi_instance_data(task, case.data, count)

    for i in range(count):
        child = self._create_mi_child(
            case=case,
            task=task,
            parent=parent,
            index=i,
            instance_data=instance_data_list[i] if i < len(instance_data_list) else {},
            net_id=net_id,
        )
        parent.children.append(child.id)
        work_items.append(child)
        self._resource_work_item(child, task)

    self._emit_event(
        "MI_TASK_SPAWNED",
        case_id=case.id,
        work_item_id=parent.id,
        task_id=task.id,
        data={"instance_count": count},
    )

    return work_items


def _create_mi_child(
    self,
    case: YCase,
    task: YMultipleInstanceTask,
    parent: YWorkItem,
    index: int,
    instance_data: dict[str, Any],
    net_id: str,
) -> YWorkItem:
    """Create child work item for MI task."""
    self.work_item_counter += 1
    child = YWorkItem(
        id=f"{parent.id}:child:{index}",
        case_id=case.id,
        task_id=task.id,
        specification_id=case.specification_id,
        net_id=net_id,
        parent_id=parent.id,
        instance_index=index,
        instance_data=instance_data,
    )
    case.add_work_item(child)
    return child


def _evaluate_mi_count(
    self,
    task: YMultipleInstanceTask,
    case_data: YCaseData,
) -> int:
    """Evaluate MI query to determine instance count."""
    if task.mi_query is None:
        return task.mi_maximum or 1

    # Evaluate XPath query to get item count
    # e.g., "/order/items/item" → count of items
    result = self._evaluate_expression(task.mi_query, case_data.variables)

    if isinstance(result, list):
        return len(result)
    elif isinstance(result, int):
        return result
    else:
        return 1


def _extract_mi_instance_data(
    self,
    task: YMultipleInstanceTask,
    case_data: YCaseData,
    count: int,
) -> list[dict[str, Any]]:
    """Extract per-instance data using mi_unique_input_expression."""
    if task.mi_query is None or task.mi_unique_input_expression is None:
        return [{} for _ in range(count)]

    # Get items from query
    items = self._evaluate_expression(task.mi_query, case_data.variables)

    if not isinstance(items, list):
        items = [items]

    # Extract unique data for each instance
    instance_data = []
    for item in items[:count]:
        unique = self._evaluate_expression(
            task.mi_unique_input_expression,
            {"item": item, **case_data.variables},
        )
        instance_data.append({"_instance_input": unique, "_source_item": item})

    return instance_data
```

### 3. MI Completion Tracking

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

    # Handle MI child completion
    if work_item.is_mi_child():
        return self._complete_mi_child(work_item, output_data)

    # Regular completion
    # ... existing code ...


def _complete_mi_child(
    self,
    child: YWorkItem,
    output_data: dict[str, Any] | None,
) -> bool:
    """Complete MI child and check threshold."""
    # Complete the child
    if child.status not in (WorkItemStatus.STARTED, WorkItemStatus.EXECUTING):
        return False

    child.complete(output_data)

    # Find parent
    parent = self._find_work_item(child.parent_id)
    if parent is None:
        return True

    # Get task for threshold info
    case = self.cases.get(child.case_id)
    if case is None:
        return True

    spec = self.specifications.get(case.specification_id)
    if spec is None:
        return True

    task = spec.get_task(child.task_id)
    if not isinstance(task, YMultipleInstanceTask):
        return True

    # Count completions
    completed_count = sum(
        1 for cid in parent.children
        if self._find_work_item(cid).is_successful()
    )

    # Check threshold
    threshold = task.mi_threshold
    if task.mi_creation_mode == "dynamic" and task.threshold_query:
        threshold = self._evaluate_expression(
            task.threshold_query, case.data.variables
        )

    if completed_count >= threshold:
        self._complete_mi_parent(parent, task, case)

    self._emit_event(
        "MI_CHILD_COMPLETED",
        case_id=child.case_id,
        work_item_id=child.id,
        task_id=child.task_id,
        data={
            "completed_count": completed_count,
            "threshold": threshold,
            "parent_id": parent.id,
        },
    )

    return True


def _complete_mi_parent(
    self,
    parent: YWorkItem,
    task: YMultipleInstanceTask,
    case: YCase,
) -> None:
    """Complete MI parent and aggregate outputs."""
    # Aggregate child outputs
    aggregated_output = self._aggregate_mi_outputs(parent, task)

    # Mark parent complete
    parent.status = WorkItemStatus.COMPLETED
    parent.completed_time = datetime.now()
    parent.data_output = aggregated_output

    # Fire task in net runner
    runner_key = f"{case.id}:{parent.net_id}"
    runner = self.net_runners.get(runner_key)
    if runner:
        try:
            runner.fire_task(task.id, aggregated_output)
        except ValueError:
            pass

        if runner.completed:
            case.complete(aggregated_output)
            self._emit_event("CASE_COMPLETED", case_id=case.id)
        else:
            self._create_work_items_for_enabled_tasks(case, runner)

    # Cancel remaining children (optional cleanup)
    for child_id in parent.children:
        child = self._find_work_item(child_id)
        if child and child.is_active():
            child.cancel("Parent completed")


def _aggregate_mi_outputs(
    self,
    parent: YWorkItem,
    task: YMultipleInstanceTask,
) -> dict[str, Any]:
    """Aggregate outputs from completed MI children."""
    outputs = []

    for child_id in parent.children:
        child = self._find_work_item(child_id)
        if child and child.is_successful():
            outputs.append(child.data_output)

    # Use mi_output_query for aggregation if specified
    if task.mi_output_query:
        # Apply XQuery aggregation
        return {"_aggregated": self._evaluate_expression(
            task.mi_output_query,
            {"_outputs": outputs},
        )}
    else:
        # Default: list of outputs
        return {"_outputs": outputs}
```

## Test Cases

### WCP-13: Static Count
```python
def test_mi_static_three_instances(self) -> None:
    """MI task creates 3 child work items."""
    task = YMultipleInstanceTask(
        id="Review",
        mi_minimum=3,
        mi_maximum=3,
        mi_threshold=3,
        mi_creation_mode="static",
    )
    # ... create case, start ...
    # Assert: 1 parent + 3 children created
    # Complete all 3 → parent completes
```

### WCP-14: Runtime Count
```python
def test_mi_dynamic_from_query(self) -> None:
    """MI count determined by query."""
    task = YMultipleInstanceTask(
        id="ProcessItems",
        mi_query="/order/items/item",
        mi_unique_input_expression="./item_id",
        mi_creation_mode="dynamic",
    )
    case_data = {"order": {"items": {"item": [{"item_id": 1}, {"item_id": 2}]}}}
    # Assert: 2 children created (one per item)
```

### Threshold Completion
```python
def test_mi_threshold_early_completion(self) -> None:
    """MI completes when threshold reached."""
    task = YMultipleInstanceTask(
        id="GetApprovals",
        mi_maximum=5,
        mi_threshold=3,
        mi_creation_mode="static",
    )
    # Complete 3 of 5 children
    # Assert: parent completes, remaining 2 cancelled
```

## Dependencies

- **Expression Evaluation (Gap 11)**: For mi_query, mi_unique_input_expression
- **Data Binding (Gap 9)**: For input/output mapping

## Estimated Effort

- Implementation: 8-12 hours
- Testing: 6-8 hours
- Total: 2-3 days
