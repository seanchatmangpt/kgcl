# Chicago TDD Tools - Python Playground

Interactive examples demonstrating the Chicago TDD Tools framework using the **installed package**, not source code.

## Overview

The playground contains working examples that show:
- Basic assertions and test decorators
- Fixtures with lifecycle management
- Property-based testing
- State machines
- Swarm coordination
- Advanced validation patterns

## Quick Start

### Option 1: Automated Setup (Recommended)

```bash
# From project root
bash playground/setup_and_run.sh
```

This script will:
1. Create a virtual environment
2. Build and install the package
3. Run all playground examples

### Option 2: Manual Setup

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package
pip install -e "..[dev]"

# Run examples
cd playground
python basic_usage.py
python advanced_workflows.py
```

## Examples

### `basic_usage.py` - Core Framework Demonstration

Demonstrates fundamental Chicago TDD features:

```python
@test
def example_basic_assertions():
    """Simple assertions"""
    assert_eq_with_msg(5 + 3, 8, "math works")

@fixture_test(CounterFixture)
def example_fixture(fixture):
    """Fixture-based testing"""
    assert fixture.increment() == 1

def example_property_testing():
    """Property-based tests"""
    test = (Property()
        .predicate(lambda a, b: a + b == b + a)
        .example(1, 2)
        .build())
    assert test.run()

def example_state_machine():
    """State workflow testing"""
    sm = StateMachine("pending")
    sm.add_transition("pending", "done", "process")
    sm.perform_action("process")

def example_swarm_coordination():
    """Distributed test execution"""
    coordinator = TestCoordinator()
    coordinator.register_member(worker1)
    results = coordinator.execute(task)
```

### `advanced_workflows.py` - Complex Scenarios

Demonstrates advanced patterns:

```python
# State management with validators
sm = StateManager(OrderState.PENDING)
sm.add_validator(OrderState.CONFIRMED, can_confirm)

# Fail-fast validation
validator = FailFastValidator(fail_fast=False)
validator.check_equal("test", expected, actual)

# Error prevention (Poka-Yoke)
value = Poka.unwrap(result, "message")
value = Poka.unwrap_or(result, default)

# Invariant checking
validator = InvariantValidator()
validator.add("positive", lambda x: x > 0)
validator.validate_all(data)

# Guard types
guard = Guard.validated(42, lambda x: x > 0)

# Snapshot testing for regression detection
test = SnapshotTest("api", response)
test.matches_snapshot("snapshot.json")
```

## Running Specific Examples

After setting up, you can run individual examples:

```bash
# Activate environment
source venv/bin/activate

# Run basic examples
cd playground
python basic_usage.py

# Run advanced examples
python advanced_workflows.py

# Run with Python directly
python -c "from basic_usage import *; example_basic_assertions()"
```

## Package Installation Verification

The playground verifies the package is properly installed:

```bash
# Check installation
python -c "from chicago_tdd_tools.core import test; print('✓ Installation verified')"

# List available modules
python -c "import chicago_tdd_tools; print(dir(chicago_tdd_tools))"
```

## What Gets Imported

The playground uses the **installed package**, not source files:

```python
# ✓ Correct - Uses installed package
from chicago_tdd_tools.core import test
from chicago_tdd_tools.swarm import TestCoordinator

# ✗ Wrong - Would use source files
from src.core import test
```

## Project Structure

```
playground/
├── README.md                 # This file
├── basic_usage.py           # Core framework examples
├── advanced_workflows.py    # Complex test scenarios
└── setup_and_run.sh        # Automated setup script
```

## Troubleshooting

### Import Error: No module named 'chicago_tdd_tools'

```bash
# Solution: Install the package
pip install -e ".."
```

### Command not found: setup_and_run.sh

```bash
# Make script executable
chmod +x playground/setup_and_run.sh
```

### Virtual environment not activating

```bash
# Recreate virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
```

## Integration with IDE

### VS Code

Add to `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true
}
```

### PyCharm

1. Go to Settings → Project → Python Interpreter
2. Click gear icon → Add → Existing Environment
3. Select `venv/bin/python`

## Next Steps

1. **Modify Examples**: Edit `basic_usage.py` and `advanced_workflows.py` to experiment
2. **Create Your Own**: Add new files following the same import pattern
3. **Run Tests**: `pytest tests/ -v` from project root
4. **Check Types**: `mypy playground/ --ignore-missing-imports`

## Important Notes

- The playground uses the **built/installed package**, not source files
- This ensures you're testing the actual distribution, not development code
- All imports should be from `chicago_tdd_tools.*`, not `src.*`
- Each example is independent and can be run individually

## License

MIT - Same as Chicago TDD Tools
