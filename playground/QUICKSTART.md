# Playground Quick Start

Get started with Chicago TDD Tools in 2 minutes.

## One-Command Setup

```bash
bash playground/setup_and_run.sh
```

Done! This will:
- Create virtual environment
- Install the built package
- Run all examples

## Manual Steps (if preferred)

```bash
# 1. Create environment
python3 -m venv venv
source venv/bin/activate

# 2. Install package
pip install -e ".."

# 3. Run examples
cd playground
python basic_usage.py
python advanced_workflows.py
```

## Verify Installation

```bash
# Check package is installed
python -c "import chicago_tdd_tools; print(chicago_tdd_tools.__version__)"

# Should output: 1.4.0
```

## Key Example Patterns

### Basic Test
```python
from chicago_tdd_tools.core import test, assert_eq_with_msg

@test
def test_addition():
    assert_eq_with_msg(5 + 3, 8, "5 + 3 should equal 8")
```

### Fixture Test
```python
from chicago_tdd_tools.core import fixture_test, TestFixture

class MyFixture(TestFixture):
    def setup(self):
        self.value = 42

@fixture_test(MyFixture)
def test_with_fixture(fixture):
    assert fixture.value == 42
```

### Property Test
```python
from chicago_tdd_tools.validation import Property

test = (Property()
    .predicate(lambda a, b: a + b == b + a)
    .example(1, 2)
    .example(5, 3)
    .build())
assert test.run()
```

### State Machine
```python
from chicago_tdd_tools.testing import StateMachine

sm = StateMachine("pending")
sm.add_transition("pending", "done", "process")
sm.perform_action("process")
assert sm.current_state() == "done"
```

## Import Guide

**Always import from installed package:**
```python
# ✓ Correct
from chicago_tdd_tools.core import test

# ✗ Wrong
from src.core import test
```

## Run Individual Examples

```bash
# After setup, activate environment
source venv/bin/activate
cd playground

# Run specific example function
python -c "from basic_usage import example_basic_assertions; example_basic_assertions()"

# Or run entire file
python basic_usage.py
```

## What's in Each File

| File | Contains |
|------|----------|
| `basic_usage.py` | Assertions, fixtures, properties, state machines, swarm |
| `advanced_workflows.py` | State management, fail-fast, poka-yoke, invariants, guards, snapshots |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'chicago_tdd_tools'` | Run `pip install -e ".."` from project root |
| `Permission denied: setup_and_run.sh` | Run `chmod +x playground/setup_and_run.sh` |
| `Deactivated venv` | Run `source venv/bin/activate` |
| `Package won't update` | Run `pip install --force-reinstall -e ".."` |

## Next: Modify & Experiment

1. Edit `playground/basic_usage.py` to add your own tests
2. Create new `.py` files following the same pattern
3. Run with: `python your_file.py`

## Learn More

- Read `playground/README.md` for detailed documentation
- Check `examples/` directory for more patterns
- Run `pytest tests/ -v` to see full test suite

## Get Help

```bash
# Check package version
python -c "import chicago_tdd_tools; help(chicago_tdd_tools)"

# List all available modules
python -c "import chicago_tdd_tools.core; help(chicago_tdd_tools.core)"

# Run specific test module
pytest tests/test_core.py -v
```

That's it! You're ready to explore Chicago TDD Tools. 🎉
