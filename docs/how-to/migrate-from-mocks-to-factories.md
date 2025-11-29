# Migrating from Mocks to Factory Boy Factories

## Overview

Chicago School TDD requires **real objects, not mocks** for domain objects. This guide explains how to migrate from `unittest.mock` to `factory_boy` factories.

## Why No Mocking?

Chicago School TDD principles:

1. **Real Behavior**: Tests should verify actual behavior, not mocked behavior
2. **Integration Confidence**: Real objects catch integration issues early
3. **Refactoring Safety**: Tests with real objects survive refactoring better
4. **Documentation**: Real object usage documents the API

## What Gets Detected

The implementation lies detector catches:

- `from unittest.mock import MagicMock, Mock, patch`
- `@patch` decorators
- `MagicMock()`, `Mock()`, `patch()` calls
- Custom `Mock*` classes (e.g., `MockEngine`, `MockResponse`)

## Available Factories

All factories are in `tests/factories/`:

### Hook Factories

```python
from tests.factories import HookFactory, HookReceiptFactory

# Create a hook
hook = HookFactory(name="validate-person", phase=HookPhase.ON_CHANGE)

# Create a receipt
receipt = HookReceiptFactory(hook_id=hook.hook_id, condition_matched=True)
```

### Condition Factories

```python
from tests.factories import ConditionFactory, ConditionResultFactory

# Create a condition
condition = ConditionFactory(
    kind=ConditionKind.THRESHOLD,
    expression="errorRate > 0.05"
)

# Create a result
result = ConditionResultFactory(matched=True, duration_ms=2.0)
```

### YAWL Factories

```python
from tests.factories import YCaseFactory, YWorkItemFactory, YTaskFactory

# Create a case
case = YCaseFactory(id="case-001", specification_id="spec-order")

# Create a work item
work_item = YWorkItemFactory(case_id=case.id, task_id="task-review")

# Create a task
task = YTaskFactory(id="task-001", name="Review Order")
```

### Receipt Factories

```python
from tests.factories import ReceiptFactory, ChainAnchorFactory

# Create a receipt
receipt = ReceiptFactory(hook_id="urn:hook:test", condition_result=True)

# Create a chain anchor
anchor = ChainAnchorFactory(chain_height=0)
```

## Migration Examples

### Example 1: Replacing MagicMock

**Before (Mocking):**
```python
from unittest.mock import MagicMock

def test_hook_execution():
    hook = MagicMock()
    hook.name = "test-hook"
    hook.phase = HookPhase.ON_CHANGE
    
    result = execute_hook(hook)
    assert result.success
```

**After (Factory):**
```python
from tests.factories import HookFactory

def test_hook_execution():
    hook = HookFactory(name="test-hook", phase=HookPhase.ON_CHANGE)
    
    result = execute_hook(hook)
    assert result.success
```

### Example 2: Replacing @patch

**Before (Mocking):**
```python
from unittest.mock import patch

@patch('kgcl.hybrid.knowledge_hooks.HookRegistry.get_hook')
def test_hook_registry(mock_get):
    mock_get.return_value = MagicMock(name="test-hook")
    
    registry = HookRegistry()
    hook = registry.get_hook("test-hook")
    assert hook.name == "test-hook"
```

**After (Factory):**
```python
from tests.factories import HookFactory

def test_hook_registry():
    hook = HookFactory(name="test-hook")
    registry = HookRegistry()
    registry.register(hook)
    
    retrieved = registry.get_hook(hook.hook_id)
    assert retrieved.name == "test-hook"
```

### Example 3: Replacing Custom Mock Classes

**Before (Mocking):**
```python
class MockEngine:
    def __init__(self):
        self.state_turtle = ""
    
    def _dump_state(self):
        return self.state_turtle

def test_engine_state():
    engine = MockEngine()
    assert engine._dump_state() == ""
```

**After (Factory):**
```python
from tests.factories import YCaseFactory
from kgcl.hybrid.hybrid_engine import HybridEngine

def test_engine_state():
    engine = HybridEngine()  # Real engine, not mock
    case = YCaseFactory()  # Use factory for test data
    
    engine.load_case(case)
    state = engine._dump_state()
    assert state is not None
```

## When Mocking is Acceptable

Mocking is **only acceptable** for infrastructure that cannot be easily instantiated:

- External HTTP clients (with `# pragma: allowlist mock` comment)
- File system operations (with `# pragma: allowlist mock` comment)
- Database connections (with `# pragma: allowlist mock` comment)

**Never mock domain objects:**
- ❌ `Hook`, `HookReceipt`, `Condition`
- ❌ `YCase`, `YWorkItem`, `YTask`
- ❌ `Receipt`, `ChainAnchor`

## Factory Customization

Factories support customization:

```python
# Override defaults
hook = HookFactory(
    name="custom-hook",
    priority=100,
    enabled=False
)

# Use sequences for unique values
hook1 = HookFactory()  # hook_id = "urn:hook:hook-0"
hook2 = HookFactory()  # hook_id = "urn:hook:hook-1"

# Use LazyFunction for dynamic values
receipt = HookReceiptFactory(
    timestamp=datetime.now(UTC)  # Real timestamp
)
```

## Running the Detector

Check for mocking violations:

```bash
# Check all files
uv run python scripts/detect_implementation_lies.py tests/

# Check staged files only
uv run python scripts/detect_implementation_lies.py --staged
```

The detector will:
1. Identify all mocking violations
2. Suggest appropriate factories
3. Block commits (pre-commit) and pushes (pre-push)

## Benefits

1. **Real Behavior**: Tests verify actual object behavior
2. **Type Safety**: Factories create properly typed objects
3. **Maintainability**: Changes to domain objects are caught in tests
4. **Documentation**: Factory usage shows how to create objects
5. **Refactoring**: Tests survive refactoring better

## See Also

- [Chicago School TDD Checklist](chicago-tdd-checklist.md)
- [Implementation Lies Detector](../../scripts/detect_implementation_lies.py)
- [Factory Boy Documentation](https://factoryboy.readthedocs.io/)


