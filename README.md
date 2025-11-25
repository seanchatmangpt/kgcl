# Chicago TDD Tools - Python Implementation

A Python testing framework implementing Chicago-style TDD (Classicist Test-Driven Development) with runtime validation through type hints and decorators.

## Philosophy

Chicago-style TDD focuses on **behavior verification** using **real collaborators** instead of mocks. This framework enforces that philosophy through:

- **Type-First Design**: Python type hints guide test structure (AAA pattern)
- **Error Prevention (Poka-Yoke)**: Common testing mistakes caught early
- **Zero-Cost Abstractions**: All validation is optional for production use
- **80/20 Focus**: Solves 80% of testing problems with 20% extra framework effort

## Quick Start

### Basic Test

```python
from src.core import test, assert_eq_with_msg

@test
def test_addition():
    # Arrange
    x, y = 5, 3
    # Act
    result = x + y
    # Assert
    assert_eq_with_msg(result, 8, "5 + 3 should equal 8")
```

### Async Tests

```python
from src.core import async_test

@async_test
async def test_async_operation():
    result = await async_add(5, 3)
    assert result == 8
```

### Fixture-Based Tests

```python
from src.core import fixture_test, TestFixture

class CounterFixture(TestFixture):
    def setup(self):
        self.counter = 0

@fixture_test(CounterFixture)
def test_counter(fixture):
    assert fixture.counter >= 0
```

### Property-Based Testing

```python
from src.validation import Property

test = (Property()
    .name("commutative_addition")
    .predicate(lambda a, b: a + b == b + a)
    .example(1, 2)
    .example(5, 3)
    .build())

assert test.run()  # True if all examples pass
```

## Core Modules

### `src.core` - Fundamental Testing
- **assertions**: Custom assertion functions
- **decorators**: `@test`, `@async_test`, `@fixture_test`
- **fixture**: Test fixtures with lifecycle management
- **builders**: Fluent builder pattern for test objects
- **state**: State machines for test scenarios
- **fail_fast**: Early error detection
- **poka_yoke**: Error-proofing utilities

### `src.swarm` - Test Orchestration
- **coordinator**: Manage multiple test workers
- **member**: Individual test executor
- **task**: Distributed task execution
- **composition**: Combine multiple tests

### `src.validation` - Advanced Testing
- **property**: Property-based testing
- **invariants**: Invariant validation
- **guards**: Runtime validation guarantees

### `src.testing` - Advanced Utilities
- **property_based**: Property tests with statistics
- **state_machine**: State-based testing
- **snapshot**: Regression testing

## File Structure

```
src/
├── core/           # Assertions, fixtures, decorators
├── swarm/          # Test orchestration
├── validation/     # Property testing & invariants
└── testing/        # Advanced testing utilities

tests/              # Test suite
examples/           # Usage examples
docs/               # Documentation
```

## License

MIT
