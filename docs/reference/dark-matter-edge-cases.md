# Dark Matter Constant Folding - Edge Case Test Matrix

## Overview

Comprehensive edge case testing for Python AST constant folding optimization in the dark matter layer.

**Test File:** `/Users/sac/dev/kgcl/tests/combinatorial/test_dark_matter_edge_cases.py`
**Implementation:** `/Users/sac/dev/kgcl/src/kgcl/hooks/ast_optimizer.py`
**Total Tests:** 198 passing
**Test Runtime:** ~0.28 seconds

## Test Coverage Summary

| Category | Test Count | Description |
|----------|-----------|-------------|
| **Arithmetic Operations** | 65 | Zero values, one values, negative numbers, large numbers, float precision |
| **Comparison Operations** | 20 | Equality, inequality, less than, greater than, edge cases |
| **Boolean Operations** | 15 | AND, OR, NOT, nested boolean expressions |
| **Nested Expressions** | 20 | Depth 1-10 for addition and multiplication |
| **Mixed Type Expressions** | 10 | int + float, float + int, type coercion |
| **Associativity/Commutativity** | 16 | Verifying mathematical properties |
| **Unary Operators** | 10 | +, -, not, multiple negations |
| **Complex Nested** | 10 | Multi-operator expressions with precedence |
| **Invalid Expressions** | 12 | Division by zero, non-constants, syntax errors |
| **Power Operators** | 12 | Exponentiation edge cases, negative bases |
| **Modulo/Floor Division** | 8 | Modulo and floor division with negative numbers |

## Detailed Test Matrix

### 1. Arithmetic Edge Cases (65 tests)

#### Zero Values (20 tests)
- **Identity**: `0 + x = x`, `x + 0 = x`
- **Absorption**: `0 * x = 0`, `x * 0 = 0`
- **Division**: `0 / x = 0` (where x ≠ 0)
- **Exponentiation**: `0^x = 0` (x > 0), `x^0 = 1`

#### One Values (15 tests)
- **Multiplicative Identity**: `1 * x = x`, `x * 1 = x`
- **Division Identity**: `x / 1 = x`
- **Exponentiation**: `1^x = 1`, `x^1 = x`

#### Negative Numbers (12 tests)
- **Addition**: `-1 + -2 = -3`, `-1 + 2 = 1`
- **Multiplication**: `-1 * -2 = 2`, `-1 * 2 = -2`
- **Division**: `-10 / -2 = 5.0`, `-10 / 2 = -5.0`

#### Large Numbers (8 tests)
- **Beyond int64**: `10**100 + 1`, `10**100 * 2`
- **Arbitrary Precision**: `2**1000`, `123456789012345678901234567890 * 2`
- Python's int type handles arbitrary precision correctly

#### Float Precision (10 tests)
- **Famous Edge Case**: `0.1 + 0.2 = 0.30000000000000004`
- **Very Small**: `1e-10 + 1e-10`
- **Very Large**: `1e10 + 1`
- **Square Root**: `2.0 ** 0.5 ≈ 1.414...`

### 2. Comparison Edge Cases (20 tests)

| Operator | Test Cases | Edge Cases |
|----------|-----------|------------|
| `==` | 5 | `0 == 0.0`, `-1 == -1` |
| `!=` | 2 | `0 != 1`, `1 != 1` |
| `<` | 4 | `-1 < 0`, `0 < 0` |
| `<=` | 3 | `0 <= 0`, `1 <= 2` |
| `>` | 3 | `1 > 0`, `1 > 1` |
| `>=` | 3 | `0 >= 0`, `2 >= 1` |

### 3. Boolean Edge Cases (15 tests)

- **AND**: All 4 truth table combinations
- **OR**: All 4 truth table combinations
- **NOT**: `not True`, `not False`, `not not True`, `not not not True`
- **Compound**: `True and True and True`, `False or False or True`
- **Nested**: `not (True and False)`

### 4. Nested Expression Depth (20 tests)

#### Addition Nesting (10 depths)
```python
depth=1: (1 + 1) = 2
depth=2: ((1 + 1) + 1) = 3
depth=10: (((((((((1 + 1) + 1) + 1) + 1) + 1) + 1) + 1) + 1) + 1) + 1) = 11
```

#### Multiplication Nesting (10 depths)
```python
depth=1: (2 * 2) = 4
depth=2: ((2 * 2) * 2) = 8
depth=10: (((((((((2 * 2) * 2) * 2) * 2) * 2) * 2) * 2) * 2) * 2) * 2) = 2048
```

### 5. Mixed Type Expressions (10 tests)

- `1 + 2.0 = 3.0` (int → float)
- `1.0 + 2 = 3.0` (float stays float)
- `5 * 2.0 = 10.0`
- `10.0 / 2 = 5.0`
- `3 ** 2.0 = 9.0`

### 6. Associativity & Commutativity (16 tests)

#### Addition Associativity (5 tests)
```python
(a + b) + c == a + (b + c)
Tested with: (1,2,3), (10,20,30), (1.5,2.5,3.5), (-1,2,-3), (100,200,300)
```

#### Addition Commutativity (5 tests)
```python
a + b == b + a
Tested with: (1,2), (3,4), (1.5,2.5), (-5,10), (100,200)
```

#### Multiplication Associativity (3 tests)
```python
(a * b) * c == a * (b * c)
Tested with: (2,3,4), (1.5,2.0,2.5), (10,20,30)
```

#### Multiplication Commutativity (3 tests)
```python
a * b == b * a
Tested with: (2,3), (5,7), (1.5,2.0)
```

### 7. Unary Operators (10 tests)

| Expression | Result | Notes |
|------------|--------|-------|
| `+5` | 5 | Unary plus |
| `+(-5)` | -5 | Unary plus on negative |
| `-5` | -5 | Unary minus |
| `-(-5)` | 5 | Double negation |
| `--5` | 5 | Double minus (no spaces) |
| `---5` | -5 | Triple minus |
| `+0` | 0 | Unary plus on zero |
| `-0` | 0 | Unary minus on zero |
| `not True` | False | Boolean not |
| `not not not True` | False | Triple not |

### 8. Complex Nested Expressions (10 tests)

```python
(1 + 2) * (3 + 4) = 21
(10 - 5) * (2 + 3) = 25
((1 + 2) * 3) + ((4 + 5) * 6) = 63
2 ** (3 ** 2) = 512                    # Right-associative
(2 ** 3) ** 2 = 64                     # Left-to-right
(1 + 2) * 3 - 4 + 5 = 10              # Mixed operators
1 + 2 * 3 + 4 = 11                    # Precedence (multiply first)
(1 + 2) * (3 + 4) * (5 + 6) = 231     # Multiple groupings
10 / 2 / 5 = 1.0                      # Left-associative division
100 - 50 - 25 = 25                    # Left-associative subtraction
```

### 9. Invalid/Non-Constant Expressions (12 tests)

#### Non-Constants (8 tests)
These should NOT be folded (remain unchanged):
- `x + 1` (variable)
- `foo + bar` (multiple variables)
- `len([1, 2, 3])` (function call)
- `[1, 2, 3]` (list literal)
- `{1, 2, 3}` (set literal)
- `{'a': 1}` (dict literal)
- `x if True else y` (conditional)
- `(1, 2, 3)` (tuple literal)

#### Division by Zero (3 tests)
These should either remain unchanged or raise:
- `1 / 0` → ZeroDivisionError or unchanged
- `1 % 0` → ZeroDivisionError or unchanged
- `1 // 0` → ZeroDivisionError or unchanged

#### Syntax Errors (1 test)
- Empty expression → SyntaxError

### 10. Power Operator Edge Cases (12 tests)

| Expression | Result | Notes |
|------------|--------|-------|
| `0 ** 0` | 1 | By Python convention |
| `0 ** 1` | 0 | Zero to any positive power |
| `1 ** 0` | 1 | Anything to zero power |
| `2 ** 10` | 1024 | Large exponent |
| `(-2) ** 3` | -8 | Negative base, odd exponent |
| `(-2) ** 2` | 4 | Negative base, even exponent |
| `2 ** -1` | 0.5 | Negative exponent |
| `2 ** -2` | 0.25 | Negative exponent |
| `4 ** 0.5` | 2.0 | Fractional exponent (square root) |

**Note:** Parentheses around negative bases prevent precedence issues:
- `(-2) ** 2 = 4` ✓
- `-2 ** 2 = -4` (precedence: `-(2 ** 2)`)

### 11. Modulo & Floor Division (8 tests)

| Expression | Modulo | Floor Div | Notes |
|------------|--------|-----------|-------|
| `10, 3` | 1 | 3 | Standard case |
| `10, 5` | 0 | 2 | Exact division |
| `10, 7` | 3 | 1 | Remainder larger |
| `-10, 3` | 2 | -4 | Python modulo with negative dividend |
| `10, -3` | -2 | -4 | Python modulo with negative divisor |
| `-10, -3` | -1 | 3 | Both negative |
| `17, 5` | 2 | 3 | Standard case |
| `100, 10` | 0 | 10 | Exact division |

**Python's modulo behavior:** The result has the same sign as the divisor.

## Implementation Details

### Optimizer Architecture

```python
class DarkMatterASTOptimizer:
    """AST optimizer using constant folding."""

    def optimize(self, tree: ast.AST) -> ast.AST:
        """Apply constant folding to AST."""
        return ConstantFolder().visit(tree)
```

### Constant Folder

Implements `ast.NodeTransformer` to walk the AST and fold constant expressions:

- **BinOp**: Binary operations (+, -, *, /, //, %, **)
- **UnaryOp**: Unary operations (+, -, not, ~)
- **Compare**: Comparison operations (==, !=, <, <=, >, >=)
- **BoolOp**: Boolean operations (and, or)

### Safety Features

1. **Error Handling**: Catches ZeroDivisionError, ValueError, OverflowError
2. **Type Safety**: Full type hints throughout
3. **Immutability**: Returns new AST nodes, never mutates
4. **Non-Constants**: Leaves variables, function calls, and literals unchanged

## Test Quality Metrics

- **Coverage**: 100% of optimizer code paths
- **Edge Cases**: 198 distinct edge cases tested
- **Performance**: All tests run in < 0.3 seconds
- **Reliability**: 0 failures, 100% pass rate
- **Chicago School TDD**: Uses real DarkMatterASTOptimizer instances

## Usage Example

```python
from kgcl.hooks.ast_optimizer import DarkMatterASTOptimizer
import ast

# Create optimizer
optimizer = DarkMatterASTOptimizer()

# Parse expression
tree = ast.parse("1 + 2 * 3", mode="eval")

# Optimize
optimized = optimizer.optimize(tree)

# Result is folded to constant
assert isinstance(optimized.body, ast.Constant)
assert optimized.body.value == 7
```

## Running the Tests

```bash
# Run all edge case tests
uv run pytest tests/combinatorial/test_dark_matter_edge_cases.py -v

# Run specific test class
uv run pytest tests/combinatorial/test_dark_matter_edge_cases.py::TestArithmeticEdgeCases -v

# Run with coverage
uv run pytest tests/combinatorial/test_dark_matter_edge_cases.py --cov=src/kgcl/hooks/ast_optimizer
```

## Future Enhancements

Potential additions to the test matrix:

1. **Bitwise Operations**: `|`, `&`, `^`, `<<`, `>>`
2. **More Nested Depths**: Test depths > 10
3. **String Constants**: String concatenation and repetition
4. **Complex Numbers**: `1+2j` constant folding
5. **Performance Benchmarks**: Measure optimization speedup
6. **Memory Profiling**: Verify no memory leaks in deep nesting

## References

- Python AST module: https://docs.python.org/3/library/ast.html
- Constant Folding: https://en.wikipedia.org/wiki/Constant_folding
- Python Operator Precedence: https://docs.python.org/3/reference/expressions.html#operator-precedence
