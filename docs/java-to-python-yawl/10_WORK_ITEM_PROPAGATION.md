# Gap 10: Work Item Propagation

## Problem Statement

After completing a work item, the engine should automatically create work items for all newly enabled tasks. Currently this works partially but has bugs causing missing work items in some scenarios.

## Current Behavior

```python
# src/kgcl/yawl/engine/y_engine.py:745-791
def complete_work_item(
    self,
    work_item_id: str,
    output_data: dict[str, Any] | None = None,
) -> bool:
    # ... complete work item ...

    # Fire the task in the net runner
    runner_key = f"{case.id}:{work_item.net_id}"
    runner = self.net_runners.get(runner_key)
    if runner:
        try:
            runner.fire_task(work_item.task_id, output_data)
        except ValueError:
            pass  # Task may have been disabled

        # Check for completion
        if runner.completed:
            case.complete(output_data)
            self._emit_event("CASE_COMPLETED", case_id=case.id)
        else:
            # Create work items for newly enabled tasks
            self._create_work_items_for_enabled_tasks(case, runner)
```

## Observed Issues

### Issue 1: Parallel Branch Work Items Missing

**Test case**: `test_parallel_tasks_create_multiple_work_items`

```
[start] → [Split(AND)] → [c_a] → [A]
                       → [c_b] → [B]
```

After completing Split task:
- **Expected**: Work items for A and B
- **Actual**: Only work item for Split exists

### Issue 2: Work Item Deduplication Too Aggressive

```python
# src/kgcl/yawl/engine/y_engine.py:516-552
def _create_work_items_for_enabled_tasks(
    self,
    case: YCase,
    runner: YNetRunner,
) -> list[YWorkItem]:
    for task_id in enabled_task_ids:
        # Check if work item already exists for this task
        existing = case.get_work_items_for_task(task_id)
        active_existing = [wi for wi in existing if wi.is_active()]
        if active_existing:
            continue  # ← May skip valid new work items
```

**Problem**: If a task had a work item that was completed, `get_work_items_for_task` returns it, but `is_active()` returns False. New work item IS created. But if timing is off or task appears enabled before prior work item is marked complete...

### Issue 3: Fire Task May Fail Silently

```python
try:
    runner.fire_task(work_item.task_id, output_data)
except ValueError:
    pass  # Task may have been disabled
```

**Problem**: If fire fails, tokens don't move, but we still try to create work items for enabled tasks. The enabled tasks haven't changed because fire failed.

## Root Cause Analysis

### Timing Issue
```
complete_work_item("Split")
    │
    ├─► work_item.complete()           # WI marked complete
    │
    ├─► runner.fire_task("Split")      # Tokens: start→c_a, start→c_b
    │       │
    │       └─► get_enabled_tasks()    # Returns ["A", "B"]
    │
    └─► _create_work_items_for_enabled_tasks()
            │
            └─► For "A": existing = [] → CREATE ✓
            └─► For "B": existing = [] → CREATE ✓
```

This SHOULD work. Let's check actual behavior...

### Debugging Steps

1. Add logging to trace flow:
```python
def _create_work_items_for_enabled_tasks(self, case, runner):
    enabled = runner.get_enabled_tasks()
    print(f"Enabled tasks: {enabled}")

    for task_id in enabled:
        existing = case.get_work_items_for_task(task_id)
        active = [wi for wi in existing if wi.is_active()]
        print(f"Task {task_id}: existing={len(existing)}, active={len(active)}")
```

2. Verify token placement after fire:
```python
result = runner.fire_task(task_id)
print(f"Fire result: consumed={result.consumed_tokens}, produced={result.produced_tokens}")
print(f"Marking: {runner.get_marking_snapshot()}")
```

## Proposed Fixes

### Fix 1: Improve Logging/Tracing

```python
def _create_work_items_for_enabled_tasks(
    self,
    case: YCase,
    runner: YNetRunner,
) -> list[YWorkItem]:
    """Create work items for all enabled tasks."""
    work_items = []
    enabled_task_ids = runner.get_enabled_tasks()

    for task_id in enabled_task_ids:
        # Check for ACTIVE work items only
        existing = case.get_work_items_for_task(task_id)
        active_existing = [wi for wi in existing if wi.is_active()]

        if active_existing:
            # Already has active work item, skip
            continue

        task = runner.net.tasks.get(task_id)
        if task is None:
            continue

        work_item = self._create_work_item(case, task, runner.net.id)
        work_items.append(work_item)
        self._resource_work_item(work_item, task)

    return work_items
```

### Fix 2: Handle Fire Failure Better

```python
def complete_work_item(self, work_item_id: str, output_data=None) -> bool:
    work_item = self._find_work_item(work_item_id)
    if work_item is None or work_item.status not in (...):
        return False

    work_item.complete(output_data)

    case = self.cases.get(work_item.case_id)
    if case:
        case.update_work_item_status(work_item_id)

        runner_key = f"{case.id}:{work_item.net_id}"
        runner = self.net_runners.get(runner_key)
        if runner:
            # Fire task - don't swallow errors
            fire_success = False
            try:
                runner.fire_task(work_item.task_id, output_data)
                fire_success = True
            except ValueError as e:
                # Log but continue - task might already be fired
                pass

            if runner.completed:
                case.complete(output_data)
                self._emit_event("CASE_COMPLETED", case_id=case.id)
            elif fire_success:
                # Only create new work items if fire succeeded
                self._create_work_items_for_enabled_tasks(case, runner)

    self._emit_event("WORK_ITEM_COMPLETED", ...)
    return True
```

### Fix 3: Ensure Token Flow Before Work Item Creation

```python
def _create_work_items_for_enabled_tasks(
    self,
    case: YCase,
    runner: YNetRunner,
) -> list[YWorkItem]:
    """Create work items for all enabled tasks.

    Only call this AFTER tokens have been moved by fire_task().
    """
    work_items = []

    # Get current enabled tasks based on marking
    enabled_task_ids = runner.get_enabled_tasks()

    # Get all existing work item task IDs
    existing_task_ids = {
        wi.task_id for wi in case.work_items.values()
        if wi.is_active()
    }

    # Create work items for newly enabled tasks
    for task_id in enabled_task_ids:
        if task_id in existing_task_ids:
            continue

        task = runner.net.tasks.get(task_id)
        if task:
            work_item = self._create_work_item(case, task, runner.net.id)
            work_items.append(work_item)
            self._resource_work_item(work_item, task)
            existing_task_ids.add(task_id)  # Prevent duplicates in this batch

    return work_items
```

## Test Cases to Add

```python
class TestWorkItemPropagation:
    """Tests for automatic work item creation after task completion."""

    def test_and_split_creates_parallel_work_items(self) -> None:
        """AND-split creates work items for all branches."""
        # start → Split(AND) → [c_a, c_b] → [A, B]
        # Complete Split
        # Assert: Work items for both A and B exist

    def test_xor_split_creates_single_work_item(self) -> None:
        """XOR-split creates work item for taken path only."""
        # start → Split(XOR) → [c_a, c_b] → [A, B]
        # Complete Split (takes path A)
        # Assert: Work item for A, NOT for B

    def test_sequential_work_items(self) -> None:
        """Completing task creates work item for next task."""
        # start → A → c1 → B → end
        # Complete A
        # Assert: Work item for B exists

    def test_no_duplicate_work_items(self) -> None:
        """Don't create duplicate work items for same task."""
        # Somehow try to trigger creation twice
        # Assert: Only one work item per task

    def test_work_item_after_join(self) -> None:
        """Work item created after join fires."""
        # [c_a, c_b] → Join(AND) → end
        # Complete both inputs
        # Assert: Join task work item created

    def test_chain_of_completions(self) -> None:
        """Complete chain of tasks in sequence."""
        # start → A → c1 → B → c2 → C → end
        # Complete A, B, C in sequence
        # Assert: Each creates next work item
```

## Implementation Order

1. Add detailed logging (temporary for debugging)
2. Write failing test cases that reproduce the bug
3. Identify exact failure point
4. Apply fix
5. Verify all tests pass
6. Remove debugging logging

## Estimated Effort

- Debugging: 2-4 hours
- Fix: 1-2 hours
- Testing: 2-3 hours
- Total: 0.5-1 day

## Priority: HIGH

This is blocking correct workflow execution and should be fixed first before other features.
