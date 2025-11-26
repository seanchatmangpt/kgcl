"""POC: Dark Matter Query Plan Optimization - Constant Folding.

This single file contains a complete working implementation of constant folding
optimization for query execution plans. Constant folding evaluates constant
expressions at optimization time, reducing runtime overhead.

Features:
- Arithmetic constant folding (2 + 3 -> 5)
- String concatenation folding ('foo' + 'bar' -> 'foobar')
- Boolean expression folding (true AND false -> false)
- Filter step elimination for always-true/false predicates
- Cost reduction calculation
- Safe expression evaluation (no exec/eval)

Run: python examples/poc_dark_matter.py
"""

from __future__ import annotations

import ast
import operator
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class QueryStep:
    """Single step in query execution plan.

    Parameters
    ----------
    step_id : int
        Unique identifier for this step
    operation : str
        Operation type (FILTER, PROJECT, JOIN, SCAN, etc.)
    cost : float
        Estimated execution cost
    expression : str | None
        Expression to evaluate (None for non-expression steps)
    dependencies : tuple[int, ...]
        IDs of steps this step depends on
    is_constant : bool
        Whether this step's expression contains only constants
    """

    step_id: int
    operation: str
    cost: float
    expression: str | None = None
    dependencies: tuple[int, ...] = ()
    is_constant: bool = False


@dataclass(frozen=True)
class ConstantFoldResult:
    """Result of constant folding optimization.

    Parameters
    ----------
    original_steps : tuple[QueryStep, ...]
        Original query plan steps
    optimized_steps : tuple[QueryStep, ...]
        Optimized steps after constant folding
    folded_count : int
        Number of expressions folded
    cost_reduction : float
        Total cost reduction achieved
    """

    original_steps: tuple[QueryStep, ...]
    optimized_steps: tuple[QueryStep, ...]
    folded_count: int
    cost_reduction: float


class DarkMatterConstantFolder:
    """Apply constant folding optimization to query execution plans.

    Constant folding identifies expressions containing only literal values
    and evaluates them at optimization time, replacing the expression with
    the computed result. This eliminates runtime evaluation overhead.

    Examples
    --------
    >>> folder = DarkMatterConstantFolder()
    >>> steps = [
    ...     QueryStep(1, "FILTER", 10.0, "2 + 3 > 4", (), True),
    ...     QueryStep(2, "PROJECT", 5.0, "column_a", (1,), False)
    ... ]
    >>> result = folder.fold_constants(steps)
    >>> result.folded_count
    1
    >>> result.cost_reduction > 0
    True
    """

    # Operators supported in constant expressions
    _OPERATORS: dict[type[ast.operator], Any] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.LShift: operator.lshift,
        ast.RShift: operator.rshift,
        ast.BitOr: operator.or_,
        ast.BitXor: operator.xor,
        ast.BitAnd: operator.and_,
    }

    _COMPARISONS: dict[type[ast.cmpop], Any] = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
    }

    _BOOL_OPS: dict[type[ast.boolop], Any] = {
        ast.And: lambda a, b: a and b,
        ast.Or: lambda a, b: a or b,
    }

    _UNARY_OPS: dict[type[ast.unaryop], Any] = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
        ast.Not: operator.not_,
        ast.Invert: operator.invert,
    }

    def fold_constants(self, steps: list[QueryStep]) -> ConstantFoldResult:
        """Apply constant folding to query execution plan.

        This method:
        1. Identifies steps with constant expressions
        2. Evaluates constant expressions safely using AST
        3. Replaces expressions with computed values
        4. Eliminates redundant filter steps (always true/false)
        5. Calculates cost reduction from optimization

        Parameters
        ----------
        steps : list[QueryStep]
            Original query execution plan steps

        Returns
        -------
        ConstantFoldResult
            Optimization result with original, optimized steps, fold count,
            and cost reduction

        Examples
        --------
        >>> folder = DarkMatterConstantFolder()
        >>> steps = [QueryStep(1, "FILTER", 10.0, "5 + 3", (), True)]
        >>> result = folder.fold_constants(steps)
        >>> result.optimized_steps[0].expression
        '8'
        """
        original_steps = tuple(steps)
        optimized: list[QueryStep] = []
        folded_count = 0

        for step in steps:
            # Skip steps without expressions or non-constant expressions
            if not step.expression or not step.is_constant:
                optimized.append(step)
                continue

            # Attempt to fold the constant expression
            try:
                folded_value = self.evaluate_constant(step.expression)
                folded_count += 1

                # For FILTER steps, check if we can eliminate them
                if step.operation == "FILTER":
                    # If filter is always true, skip it (no filtering needed)
                    if folded_value == "True":
                        continue
                    # If filter is always false, this indicates dead code
                    # (no rows pass), but we keep it to signal the issue
                    if folded_value == "False":
                        optimized.append(
                            QueryStep(
                                step.step_id,
                                step.operation,
                                0.0,  # Zero cost for eliminated step
                                folded_value,
                                step.dependencies,
                                True,
                            )
                        )
                        continue

                # Replace with folded expression
                optimized.append(
                    QueryStep(
                        step.step_id,
                        step.operation,
                        step.cost * 0.1,  # Folded expressions cost ~10% of original
                        folded_value,
                        step.dependencies,
                        True,
                    )
                )
            except (ValueError, SyntaxError, TypeError):
                # If folding fails, keep original step
                optimized.append(step)

        cost_reduction = self.calculate_cost_reduction(list(original_steps), optimized)

        return ConstantFoldResult(
            original_steps=original_steps,
            optimized_steps=tuple(optimized),
            folded_count=folded_count,
            cost_reduction=cost_reduction,
        )

    def is_constant_expression(self, expr: str) -> bool:
        """Check if expression contains only constant values.

        An expression is constant if it contains only:
        - Numeric literals (42, 3.14)
        - String literals ('foo', "bar")
        - Boolean literals (true, false, True, False)
        - Operators (+, -, *, /, AND, OR, etc.)
        - Parentheses for grouping

        Parameters
        ----------
        expr : str
            Expression to check

        Returns
        -------
        bool
            True if expression contains only constants

        Examples
        --------
        >>> folder = DarkMatterConstantFolder()
        >>> folder.is_constant_expression("2 + 3")
        True
        >>> folder.is_constant_expression("column_a + 3")
        False
        """
        # Normalize boolean literals
        normalized = expr.replace("true", "True").replace("false", "False")
        normalized = normalized.replace("AND", "and").replace("OR", "or")
        normalized = normalized.replace("NOT", "not")

        try:
            tree = ast.parse(normalized, mode="eval")
            return self._is_constant_node(tree.body)
        except SyntaxError:
            return False

    def _is_constant_node(self, node: ast.AST) -> bool:
        """Recursively check if AST node represents a constant expression.

        Parameters
        ----------
        node : ast.AST
            AST node to check

        Returns
        -------
        bool
            True if node and all children are constant
        """
        # Constant literals (Python 3.8+)
        if isinstance(node, ast.Constant):
            return True

        # Binary operations
        if isinstance(node, ast.BinOp):
            return self._is_constant_node(node.left) and self._is_constant_node(
                node.right
            )

        # Comparisons
        if isinstance(node, ast.Compare):
            return self._is_constant_node(node.left) and all(
                self._is_constant_node(comp) for comp in node.comparators
            )

        # Boolean operations
        if isinstance(node, ast.BoolOp):
            return all(self._is_constant_node(val) for val in node.values)

        # Unary operations
        if isinstance(node, ast.UnaryOp):
            return self._is_constant_node(node.operand)

        # Not a constant expression
        return False

    def evaluate_constant(self, expr: str) -> str:
        """Evaluate constant expression at optimization time.

        Uses Python's AST to safely evaluate expressions without exec/eval.
        Supports arithmetic, string concatenation, boolean logic, and comparisons.

        Parameters
        ----------
        expr : str
            Constant expression to evaluate

        Returns
        -------
        str
            String representation of evaluated result

        Raises
        ------
        ValueError
            If expression is not constant or cannot be evaluated
        SyntaxError
            If expression has invalid syntax

        Examples
        --------
        >>> folder = DarkMatterConstantFolder()
        >>> folder.evaluate_constant("2 + 3")
        '5'
        >>> folder.evaluate_constant("'foo' + 'bar'")
        "'foobar'"
        >>> folder.evaluate_constant("10 > 5")
        'True'
        """
        if not self.is_constant_expression(expr):
            raise ValueError(f"Expression is not constant: {expr}")

        # Normalize boolean literals
        normalized = expr.replace("true", "True").replace("false", "False")
        normalized = normalized.replace("AND", "and").replace("OR", "or")
        normalized = normalized.replace("NOT", "not")

        try:
            tree = ast.parse(normalized, mode="eval")
            result = self._eval_node(tree.body)
            return repr(result) if isinstance(result, str) else str(result)
        except Exception as e:
            raise ValueError(f"Failed to evaluate expression: {expr}") from e

    def _eval_node(self, node: ast.AST) -> Any:
        """Recursively evaluate AST node.

        Parameters
        ----------
        node : ast.AST
            Node to evaluate

        Returns
        -------
        Any
            Evaluated value (int, float, str, bool)

        Raises
        ------
        TypeError
            If node type is not supported
        """
        # Constant values (Python 3.8+)
        if isinstance(node, ast.Constant):
            return node.value

        # Binary operations
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op_type = type(node.op)
            if op_type not in self._OPERATORS:
                raise TypeError(f"Unsupported binary operator: {op_type}")
            return self._OPERATORS[op_type](left, right)

        # Comparisons
        if isinstance(node, ast.Compare):
            left = self._eval_node(node.left)
            result = True
            for op, comp in zip(node.ops, node.comparators):
                right = self._eval_node(comp)
                op_type = type(op)
                if op_type not in self._COMPARISONS:
                    raise TypeError(f"Unsupported comparison: {op_type}")
                result = result and self._COMPARISONS[op_type](left, right)
                left = right
            return result

        # Boolean operations
        if isinstance(node, ast.BoolOp):
            op_type = type(node.op)
            if op_type not in self._BOOL_OPS:
                raise TypeError(f"Unsupported boolean operator: {op_type}")
            # Evaluate all values
            values = [self._eval_node(val) for val in node.values]
            # For And, return True if all are True, else False
            if isinstance(node.op, ast.And):
                return all(values)
            # For Or, return True if any are True, else False
            if isinstance(node.op, ast.Or):
                return any(values)
            # Fallback (shouldn't reach here)
            result = values[0]
            for val in values[1:]:
                result = self._BOOL_OPS[op_type](result, val)
            return result

        # Unary operations
        if isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            op_type = type(node.op)
            if op_type not in self._UNARY_OPS:
                raise TypeError(f"Unsupported unary operator: {op_type}")
            return self._UNARY_OPS[op_type](operand)

        raise TypeError(f"Unsupported node type: {type(node)}")

    def calculate_cost_reduction(
        self, original: list[QueryStep], optimized: list[QueryStep]
    ) -> float:
        """Calculate total cost reduction from constant folding.

        Parameters
        ----------
        original : list[QueryStep]
            Original query plan steps
        optimized : list[QueryStep]
            Optimized steps after folding

        Returns
        -------
        float
            Total cost reduction (original_cost - optimized_cost)

        Examples
        --------
        >>> folder = DarkMatterConstantFolder()
        >>> original = [QueryStep(1, "FILTER", 10.0, "2 + 3", (), True)]
        >>> optimized = [QueryStep(1, "FILTER", 1.0, "5", (), True)]
        >>> folder.calculate_cost_reduction(original, optimized)
        9.0
        """
        original_cost = sum(step.cost for step in original)
        optimized_cost = sum(step.cost for step in optimized)
        return original_cost - optimized_cost


# ============================================================================
# INLINE TESTS
# ============================================================================


def test_fold_arithmetic_constants() -> None:
    """Constant arithmetic expressions are evaluated at optimization time."""
    folder = DarkMatterConstantFolder()

    steps = [
        QueryStep(1, "FILTER", 10.0, "2 + 3", (), True),
        QueryStep(2, "FILTER", 10.0, "10 * 5", (), True),
        QueryStep(3, "FILTER", 10.0, "100 / 4", (), True),
    ]

    result = folder.fold_constants(steps)

    assert result.folded_count == 3
    assert result.optimized_steps[0].expression == "5"
    assert result.optimized_steps[1].expression == "50"
    assert result.optimized_steps[2].expression == "25.0"
    assert result.cost_reduction > 0


def test_fold_string_concatenation() -> None:
    """String concatenation constants are folded."""
    folder = DarkMatterConstantFolder()

    steps = [QueryStep(1, "PROJECT", 5.0, "'foo' + 'bar'", (), True)]

    result = folder.fold_constants(steps)

    assert result.folded_count == 1
    assert result.optimized_steps[0].expression == "'foobar'"


def test_fold_boolean_expressions() -> None:
    """Boolean constant expressions are evaluated."""
    folder = DarkMatterConstantFolder()

    steps = [
        QueryStep(1, "FILTER", 10.0, "True and False", (), True),
        QueryStep(2, "PROJECT", 10.0, "True or False", (), True),  # Non-filter to preserve
        QueryStep(3, "PROJECT", 10.0, "not False", (), True),  # Non-filter to preserve
    ]

    result = folder.fold_constants(steps)

    assert result.folded_count == 3
    # First is FILTER with False - kept to signal dead code
    assert result.optimized_steps[0].expression == "False"
    # Second and third are PROJECT steps, kept with folded expressions
    assert result.optimized_steps[1].expression == "True"
    assert result.optimized_steps[2].expression == "True"


def test_no_folding_needed() -> None:
    """Steps without constant expressions are not folded."""
    folder = DarkMatterConstantFolder()

    steps = [
        QueryStep(1, "SCAN", 100.0, None, (), False),
        QueryStep(2, "FILTER", 10.0, "column_a > 5", (), False),
    ]

    result = folder.fold_constants(steps)

    assert result.folded_count == 0
    assert result.optimized_steps == tuple(steps)
    assert result.cost_reduction == 0.0


def test_partial_constant_folding() -> None:
    """Only constant expressions are folded in mixed plans."""
    folder = DarkMatterConstantFolder()

    steps = [
        QueryStep(1, "FILTER", 10.0, "2 + 3", (), True),  # Constant
        QueryStep(2, "FILTER", 10.0, "column_a + 5", (), False),  # Not constant
        QueryStep(3, "FILTER", 10.0, "10 * 2", (), True),  # Constant
    ]

    result = folder.fold_constants(steps)

    assert result.folded_count == 2
    assert result.optimized_steps[0].expression == "5"
    assert result.optimized_steps[1].expression == "column_a + 5"  # Unchanged
    assert result.optimized_steps[2].expression == "20"


def test_nested_constant_expressions() -> None:
    """Nested constant expressions are fully evaluated."""
    folder = DarkMatterConstantFolder()

    steps = [
        QueryStep(1, "PROJECT", 10.0, "(2 + 3) * (4 - 1)", (), True),  # Non-filter
        QueryStep(2, "PROJECT", 10.0, "10 > (3 + 2)", (), True),  # Non-filter
    ]

    result = folder.fold_constants(steps)

    assert result.folded_count == 2
    assert result.optimized_steps[0].expression == "15"
    assert result.optimized_steps[1].expression == "True"


def test_cost_reduction_calculation() -> None:
    """Cost reduction is accurately calculated."""
    folder = DarkMatterConstantFolder()

    steps = [
        QueryStep(1, "FILTER", 100.0, "2 + 3", (), True),
        QueryStep(2, "FILTER", 50.0, "10 * 5", (), True),
    ]

    result = folder.fold_constants(steps)

    # Folded steps cost 10% of original
    expected_optimized_cost = (100.0 * 0.1) + (50.0 * 0.1)
    expected_reduction = 150.0 - expected_optimized_cost

    assert abs(result.cost_reduction - expected_reduction) < 0.01


def test_filter_elimination() -> None:
    """Always-true FILTER steps are eliminated."""
    folder = DarkMatterConstantFolder()

    steps = [
        QueryStep(1, "FILTER", 10.0, "5 > 3", (), True),  # Always true
        QueryStep(2, "PROJECT", 5.0, "column_a", (1,), False),
    ]

    result = folder.fold_constants(steps)

    assert result.folded_count == 1
    # Filter step should be eliminated
    assert len(result.optimized_steps) == 1
    assert result.optimized_steps[0].operation == "PROJECT"


def test_complex_plan_optimization() -> None:
    """Complex query plan with multiple constant folding opportunities."""
    folder = DarkMatterConstantFolder()

    steps = [
        QueryStep(1, "SCAN", 100.0, None, (), False),
        QueryStep(2, "FILTER", 20.0, "10 > 5", (), True),  # Always true - eliminate
        QueryStep(3, "FILTER", 20.0, "2 + 3", (), True),  # Fold to 5
        QueryStep(4, "PROJECT", 10.0, "'prefix_' + 'suffix'", (3,), True),  # Fold
        QueryStep(5, "FILTER", 20.0, "column_x > 10", (4,), False),  # Keep
    ]

    result = folder.fold_constants(steps)

    assert result.folded_count == 3
    assert result.cost_reduction > 0

    # Verify specific optimizations
    optimized_ops = [step.operation for step in result.optimized_steps]
    assert optimized_ops.count("FILTER") == 2  # One eliminated
    assert result.optimized_steps[-1].expression == "column_x > 10"  # Preserved


def test_performance_improvement() -> None:
    """Folding 100 steps completes in under 10ms."""
    import time

    folder = DarkMatterConstantFolder()

    # Create 100 steps with constant expressions
    steps = [
        QueryStep(i, "FILTER", 10.0, f"{i} + {i+1}", (), True) for i in range(100)
    ]

    start = time.perf_counter()
    result = folder.fold_constants(steps)
    duration_ms = (time.perf_counter() - start) * 1000

    assert result.folded_count == 100
    assert duration_ms < 10.0  # Must complete in under 10ms


def test_is_constant_expression() -> None:
    """Constant expression detection is accurate."""
    folder = DarkMatterConstantFolder()

    # Constants
    assert folder.is_constant_expression("2 + 3")
    assert folder.is_constant_expression("'foo' + 'bar'")
    assert folder.is_constant_expression("True and False")
    assert folder.is_constant_expression("10 > 5")
    assert folder.is_constant_expression("(2 + 3) * 4")

    # Not constants
    assert not folder.is_constant_expression("column_a + 3")
    assert not folder.is_constant_expression("func(5)")
    assert not folder.is_constant_expression("x > 10")


def test_evaluate_constant() -> None:
    """Constant evaluation produces correct results."""
    folder = DarkMatterConstantFolder()

    assert folder.evaluate_constant("5 + 3") == "8"
    assert folder.evaluate_constant("10 - 4") == "6"
    assert folder.evaluate_constant("3 * 7") == "21"
    assert folder.evaluate_constant("20 / 4") == "5.0"
    assert folder.evaluate_constant("2 ** 3") == "8"
    assert folder.evaluate_constant("10 > 5") == "True"
    assert folder.evaluate_constant("3 < 2") == "False"
    assert folder.evaluate_constant("True and False") == "False"
    assert folder.evaluate_constant("True or False") == "True"
    assert folder.evaluate_constant("not True") == "False"


def test_invalid_expression_handling() -> None:
    """Invalid expressions raise appropriate errors."""
    folder = DarkMatterConstantFolder()

    try:
        folder.evaluate_constant("column_a + 3")
        assert False, "Should raise ValueError for non-constant expression"
    except ValueError as e:
        assert "not constant" in str(e)

    try:
        folder.evaluate_constant("invalid syntax !!!")
        assert False, "Should raise error for invalid syntax"
    except (ValueError, SyntaxError):
        pass


# ============================================================================
# MAIN - Run all tests
# ============================================================================

if __name__ == "__main__":
    import sys

    tests = [
        ("Fold arithmetic constants", test_fold_arithmetic_constants),
        ("Fold string concatenation", test_fold_string_concatenation),
        ("Fold boolean expressions", test_fold_boolean_expressions),
        ("No folding needed", test_no_folding_needed),
        ("Partial constant folding", test_partial_constant_folding),
        ("Nested constant expressions", test_nested_constant_expressions),
        ("Cost reduction calculation", test_cost_reduction_calculation),
        ("Filter elimination", test_filter_elimination),
        ("Complex plan optimization", test_complex_plan_optimization),
        ("Performance improvement", test_performance_improvement),
        ("Is constant expression", test_is_constant_expression),
        ("Evaluate constant", test_evaluate_constant),
        ("Invalid expression handling", test_invalid_expression_handling),
    ]

    passed = 0
    failed = 0

    print("Running Dark Matter Constant Folding POC Tests...")
    print("=" * 60)

    for name, test_fn in tests:
        try:
            test_fn()
            print(f"✓ {name}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {name}: {type(e).__name__}: {e}")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")

    if failed > 0:
        sys.exit(1)

    # Demo usage
    print("\nDemo: Optimizing a sample query plan")
    print("-" * 60)

    folder = DarkMatterConstantFolder()
    demo_steps = [
        QueryStep(1, "SCAN", 100.0, None, (), False),
        QueryStep(2, "FILTER", 20.0, "10 > 5", (), True),
        QueryStep(3, "FILTER", 20.0, "(2 + 3) * 4", (), True),
        QueryStep(4, "PROJECT", 10.0, "'result_' + 'value'", (3,), True),
        QueryStep(5, "FILTER", 20.0, "column_x > 100", (4,), False),
    ]

    print("\nOriginal plan:")
    for step in demo_steps:
        print(
            f"  Step {step.step_id}: {step.operation:10} "
            f"cost={step.cost:6.1f} expr={step.expression}"
        )

    result = folder.fold_constants(demo_steps)

    print(f"\nOptimized plan (folded {result.folded_count} expressions):")
    for step in result.optimized_steps:
        print(
            f"  Step {step.step_id}: {step.operation:10} "
            f"cost={step.cost:6.1f} expr={step.expression}"
        )

    print(f"\nCost reduction: {result.cost_reduction:.1f}")
    print(
        f"Improvement: {result.cost_reduction / sum(s.cost for s in demo_steps) * 100:.1f}%"
    )

    sys.exit(0)
