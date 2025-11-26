#!/usr/bin/env python3
"""Hyper-Advanced Dark Matter Query Plan Optimizer Prototype.

This prototype demonstrates cutting-edge Python techniques:
1. Algebraic Data Types (ADTs) for expression trees
2. JIT-style compilation with exec/compile
3. Persistent data structures (immutable updates)
4. Monad pattern (Maybe/Either)
5. Continuation-passing style (CPS)
6. Lens pattern for deep updates
7. Priority queue rule engine
8. Walrus operator for inline assignment
9. Match statement for pattern matching
10. Trampoline for stack-safe recursion
11. Fixpoint iteration
12. Cost model with operator overloading

Run: python examples/proto_dark_matter.py
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Any, Callable, Generator, Generic, TypeVar, Union

# Type variables
T = TypeVar("T")
U = TypeVar("U")
S = TypeVar("S")
A = TypeVar("A")
B = TypeVar("B")


# ============================================================================
# 1. ALGEBRAIC DATA TYPES - Expression Tree
# ============================================================================


@dataclass(frozen=True, slots=True)
class Literal:
    """Literal value in expression tree."""

    value: int | float | str | bool


@dataclass(frozen=True, slots=True)
class Variable:
    """Variable reference in expression tree."""

    name: str


@dataclass(frozen=True, slots=True)
class BinaryOp:
    """Binary operation in expression tree."""

    op: str
    left: "Expr"
    right: "Expr"


@dataclass(frozen=True, slots=True)
class UnaryOp:
    """Unary operation in expression tree."""

    op: str
    operand: "Expr"


@dataclass(frozen=True, slots=True)
class FunctionCall:
    """Function call in expression tree."""

    name: str
    args: tuple["Expr", ...]


# Algebraic data type for expressions
Expr = Union[Literal, Variable, BinaryOp, UnaryOp, FunctionCall]


# ============================================================================
# 2. JIT-STYLE COMPILATION - Convert expression to Python bytecode
# ============================================================================


def _expr_to_python(expr: Expr, env: dict[str, Any] | None = None) -> str:
    """Convert expression to Python code string."""
    match expr:
        case Literal(value):
            return repr(value)
        case Variable(name):
            return name
        case BinaryOp(op, left, right):
            left_code = _expr_to_python(left, env)
            right_code = _expr_to_python(right, env)
            return f"({left_code} {op} {right_code})"
        case UnaryOp(op, operand):
            operand_code = _expr_to_python(operand, env)
            return f"({op} {operand_code})"
        case FunctionCall(name, args):
            args_code = ", ".join(_expr_to_python(arg, env) for arg in args)
            return f"{name}({args_code})"
        case _:
            return "None"


def compile_expression(
    expr: Expr, env: dict[str, Any] | None = None
) -> Callable[[], Any]:
    """Compile expression to Python bytecode for fast evaluation."""
    code = _expr_to_python(expr, env)
    compiled = compile(code, "<expr>", "eval")
    safe_env = env or {}
    return lambda: eval(compiled, {"__builtins__": {}}, safe_env)


# ============================================================================
# 3. PERSISTENT DATA STRUCTURES - Immutable query plan
# ============================================================================


@dataclass(frozen=True, slots=True)
class Step:
    """Single step in query plan."""

    operation: str
    target: str
    cost: "Cost"


@dataclass(frozen=True, slots=True)
class ImmutablePlan:
    """Immutable query execution plan."""

    steps: tuple[Step, ...]

    def with_step(self, step: Step) -> "ImmutablePlan":
        """Add step to plan (immutable)."""
        return ImmutablePlan(steps=(*self.steps, step))

    def without_step(self, index: int) -> "ImmutablePlan":
        """Remove step from plan (immutable)."""
        return ImmutablePlan(steps=self.steps[:index] + self.steps[index + 1 :])

    def replace_step(self, index: int, step: Step) -> "ImmutablePlan":
        """Replace step in plan (immutable)."""
        return ImmutablePlan(
            steps=self.steps[:index] + (step,) + self.steps[index + 1 :]
        )

    def total_cost(self) -> "Cost":
        """Calculate total cost of plan."""
        return sum((step.cost for step in self.steps), Cost(0.0))


# ============================================================================
# 4. MONAD PATTERN - Maybe monad for safe computations
# ============================================================================


@dataclass(frozen=True, slots=True)
class Maybe(Generic[T]):
    """Maybe monad for optional values."""

    _value: T | None

    @staticmethod
    def just(value: T) -> "Maybe[T]":
        """Create Maybe with a value."""
        return Maybe(value)

    @staticmethod
    def nothing() -> "Maybe[None]":
        """Create empty Maybe."""
        return Maybe(None)

    def map(self, f: Callable[[T], U]) -> "Maybe[U]":
        """Map function over Maybe value."""
        if self._value is None:
            return Maybe(None)
        return Maybe(f(self._value))

    def flat_map(self, f: Callable[[T], "Maybe[U]"]) -> "Maybe[U]":
        """FlatMap (bind) function over Maybe value."""
        if self._value is None:
            return Maybe(None)
        return f(self._value)

    def get_or_else(self, default: T) -> T:
        """Get value or return default."""
        return self._value if self._value is not None else default

    def is_just(self) -> bool:
        """Check if Maybe contains a value."""
        return self._value is not None


# ============================================================================
# 5. CONTINUATION-PASSING STYLE - For early exit optimization
# ============================================================================


def optimize_cps(
    plan: ImmutablePlan,
    continuation: Callable[[ImmutablePlan], ImmutablePlan],
    max_iterations: int = 100,
) -> ImmutablePlan:
    """Optimize plan using continuation-passing style."""
    if max_iterations <= 0:
        return continuation(plan)

    # Apply constant folding rule
    if (improved := apply_constant_folding_rule(plan)) != plan:
        return optimize_cps(improved, continuation, max_iterations - 1)

    # Apply step reordering rule
    if (improved := apply_reorder_rule(plan)) != plan:
        return optimize_cps(improved, continuation, max_iterations - 1)

    # No more improvements, invoke continuation
    return continuation(plan)


def apply_constant_folding_rule(plan: ImmutablePlan) -> ImmutablePlan:
    """Apply constant folding to plan steps."""
    # Simplify sequential operations with same target
    for i in range(len(plan.steps) - 1):
        if (
            plan.steps[i].target == plan.steps[i + 1].target
            and plan.steps[i].operation == "filter"
            and plan.steps[i + 1].operation == "filter"
        ):
            # Merge two filters on same target
            merged = Step(
                operation="filter",
                target=plan.steps[i].target,
                cost=plan.steps[i].cost + plan.steps[i + 1].cost * 0.5,
            )
            return plan.without_step(i + 1).replace_step(i, merged)
    return plan


def apply_reorder_rule(plan: ImmutablePlan) -> ImmutablePlan:
    """Reorder steps for better performance."""
    # Move cheaper operations before expensive ones
    for i in range(len(plan.steps) - 1):
        if plan.steps[i].cost > plan.steps[i + 1].cost:
            # Swap if independent
            if plan.steps[i].target != plan.steps[i + 1].target:
                new_steps = list(plan.steps)
                new_steps[i], new_steps[i + 1] = new_steps[i + 1], new_steps[i]
                return ImmutablePlan(steps=tuple(new_steps))
    return plan


# ============================================================================
# 6. LENS PATTERN - Deep immutable updates
# ============================================================================


@dataclass(frozen=True, slots=True)
class Lens(Generic[S, A]):
    """Functional lens for immutable updates."""

    get: Callable[[S], A]
    set: Callable[[S, A], S]

    def modify(self, f: Callable[[A], A]) -> Callable[[S], S]:
        """Modify value through lens."""
        return lambda s: self.set(s, f(self.get(s)))

    def compose(self, other: "Lens[A, B]") -> "Lens[S, B]":
        """Compose two lenses."""
        return Lens(
            get=lambda s: other.get(self.get(s)),
            set=lambda s, b: self.set(s, other.set(self.get(s), b)),
        )


# Lens for accessing plan steps
def steps_lens() -> Lens[ImmutablePlan, tuple[Step, ...]]:
    """Lens for plan steps."""
    return Lens(
        get=lambda plan: plan.steps, set=lambda plan, steps: ImmutablePlan(steps=steps)
    )


# Lens for accessing step cost at index
def step_cost_lens(index: int) -> Lens[ImmutablePlan, Cost]:
    """Lens for step cost at index."""
    return Lens(
        get=lambda plan: plan.steps[index].cost,
        set=lambda plan, cost: plan.replace_step(
            index,
            Step(
                operation=plan.steps[index].operation,
                target=plan.steps[index].target,
                cost=cost,
            ),
        ),
    )


# ============================================================================
# 7. RULE ENGINE WITH PRIORITY QUEUE
# ============================================================================


@dataclass(order=True, frozen=True, slots=True)
class OptimizationRule:
    """Rule for query plan optimization."""

    priority: int
    name: str = field(compare=False)
    apply: Callable[[ImmutablePlan], ImmutablePlan | None] = field(compare=False)


class RuleEngine:
    """Priority queue-based rule engine."""

    def __init__(self) -> None:
        """Initialize rule engine."""
        self._rules: list[OptimizationRule] = []

    def add_rule(self, rule: OptimizationRule) -> None:
        """Add optimization rule."""
        heapq.heappush(self._rules, rule)

    def apply_all(self, plan: ImmutablePlan) -> ImmutablePlan:
        """Apply all rules in priority order."""
        for rule in sorted(self._rules):
            if (result := rule.apply(plan)) is not None:
                plan = result
        return plan


# ============================================================================
# 8. WALRUS OPERATOR - Inline assignment
# ============================================================================


def fold_if_constant(expr: Expr) -> Expr:
    """Fold expression if constant (using walrus operator)."""
    if (folded := try_fold_constant(expr)) is not None:
        return folded
    return expr


def try_fold_constant(expr: Expr) -> Expr | None:
    """Try to fold constant expression."""
    match expr:
        case BinaryOp("+", Literal(a), Literal(b)) if isinstance(a, (int, float)):
            return Literal(a + b)
        case BinaryOp("*", Literal(0), _) | BinaryOp("*", _, Literal(0)):
            return Literal(0)
        case _:
            return None


def optimize_until_fixed(plan: ImmutablePlan) -> ImmutablePlan:
    """Optimize plan until fixpoint (using walrus operator)."""
    iterations = 0
    max_iterations = 100
    while (
        iterations < max_iterations and (improved := apply_reorder_rule(plan)) != plan
    ):
        plan = improved
        iterations += 1
    return plan


# ============================================================================
# 9. MATCH STATEMENT - Pattern matching for expression folding
# ============================================================================


def fold_constant(expr: Expr) -> Expr:
    """Fold constant expressions using match statement."""
    match expr:
        # Arithmetic simplifications
        case BinaryOp("+", Literal(a), Literal(b)) if isinstance(a, (int, float)):
            return Literal(a + b)
        case BinaryOp("*", Literal(a), Literal(b)) if isinstance(a, (int, float)):
            return Literal(a * b)
        case BinaryOp("-", Literal(a), Literal(b)) if isinstance(a, (int, float)):
            return Literal(a - b)

        # Algebraic identities
        case BinaryOp("*", Literal(0), _) | BinaryOp("*", _, Literal(0)):
            return Literal(0)
        case BinaryOp("*", Literal(1), e) | BinaryOp("*", e, Literal(1)):
            return e
        case BinaryOp("+", Literal(0), e) | BinaryOp("+", e, Literal(0)):
            return e

        # Boolean logic
        case BinaryOp("and", Literal(False), _) | BinaryOp("and", _, Literal(False)):
            return Literal(False)
        case BinaryOp("and", Literal(True), e) | BinaryOp("and", e, Literal(True)):
            return e
        case BinaryOp("or", Literal(True), _) | BinaryOp("or", _, Literal(True)):
            return Literal(True)
        case BinaryOp("or", Literal(False), e) | BinaryOp("or", e, Literal(False)):
            return e

        # Recursive folding
        case BinaryOp(op, left, right):
            return BinaryOp(op, fold_constant(left), fold_constant(right))
        case UnaryOp(op, operand):
            return UnaryOp(op, fold_constant(operand))

        case _:
            return expr


# ============================================================================
# 10. TRAMPOLINE - Stack-safe recursion
# ============================================================================


def trampoline(gen: Generator) -> Any:
    """Execute generator with stack-safe recursion."""
    stack = [gen]
    result = None
    while stack:
        try:
            result = stack[-1].send(result)
            if isinstance(result, Generator):
                stack.append(result)
                result = None
        except StopIteration as e:
            stack.pop()
            result = e.value
    return result


def optimize_recursive(plan: ImmutablePlan, depth: int = 0) -> Generator:
    """Recursively optimize plan (stack-safe via trampoline)."""
    if depth > 10:
        return plan

    # Try constant folding
    improved = apply_constant_folding_rule(plan)
    if improved != plan:
        yield from optimize_recursive(improved, depth + 1)
        return improved

    # Try reordering
    improved = apply_reorder_rule(plan)
    if improved != plan:
        yield from optimize_recursive(improved, depth + 1)
        return improved

    return plan


# ============================================================================
# 11. FIXPOINT ITERATION
# ============================================================================


def fixpoint(
    f: Callable[[T], T],
    initial: T,
    eq: Callable[[T, T], bool] | None = None,
    max_iterations: int = 100,
) -> T:
    """Iterate function until result stabilizes."""
    if eq is None:
        eq = lambda a, b: a == b

    current = initial
    for _ in range(max_iterations):
        next_val = f(current)
        if eq(current, next_val):
            return current
        current = next_val
    return current


def optimize_fixpoint(plan: ImmutablePlan) -> ImmutablePlan:
    """Optimize plan to fixpoint."""

    def optimize_once(p: ImmutablePlan) -> ImmutablePlan:
        p = apply_constant_folding_rule(p)
        p = apply_reorder_rule(p)
        return p

    return fixpoint(optimize_once, plan)


# ============================================================================
# 12. COST MODEL WITH OPERATOR OVERLOADING
# ============================================================================


@dataclass(frozen=True, slots=True)
class Cost:
    """Cost metric with operator overloading."""

    value: float

    def __add__(self, other: "Cost") -> "Cost":
        """Add costs."""
        return Cost(self.value + other.value)

    def __mul__(self, factor: float) -> "Cost":
        """Multiply cost by factor."""
        return Cost(self.value * factor)

    def __lt__(self, other: "Cost") -> bool:
        """Compare costs."""
        return self.value < other.value

    def __le__(self, other: "Cost") -> bool:
        """Compare costs (less than or equal)."""
        return self.value <= other.value

    def __eq__(self, other: object) -> bool:
        """Check cost equality."""
        if not isinstance(other, Cost):
            return False
        return abs(self.value - other.value) < 1e-9


# ============================================================================
# TESTS - Comprehensive validation
# ============================================================================


def test_algebraic_data_types() -> None:
    """Test expression tree ADTs."""
    # Build expression: (2 + 3) * 4
    expr = BinaryOp("*", BinaryOp("+", Literal(2), Literal(3)), Literal(4))
    assert isinstance(expr, BinaryOp)
    assert isinstance(expr.left, BinaryOp)
    assert isinstance(expr.right, Literal)


def test_jit_compilation() -> None:
    """Test JIT-style compilation."""
    expr = BinaryOp("+", Literal(2), Literal(3))
    compiled = compile_expression(expr)
    assert compiled() == 5

    # Complex expression
    expr2 = BinaryOp("*", BinaryOp("+", Literal(2), Literal(3)), Literal(4))
    compiled2 = compile_expression(expr2)
    assert compiled2() == 20


def test_persistent_data_structures() -> None:
    """Test immutable plan updates."""
    step1 = Step("scan", "users", Cost(10.0))
    step2 = Step("filter", "users", Cost(5.0))

    plan1 = ImmutablePlan(steps=(step1,))
    plan2 = plan1.with_step(step2)

    # Original unchanged
    assert len(plan1.steps) == 1
    assert len(plan2.steps) == 2

    # Remove step
    plan3 = plan2.without_step(0)
    assert len(plan3.steps) == 1
    assert plan3.steps[0].operation == "filter"


def test_maybe_monad() -> None:
    """Test Maybe monad."""
    just_5 = Maybe.just(5)
    assert just_5.is_just()
    assert just_5.get_or_else(0) == 5

    nothing: Maybe[int] = Maybe.nothing()
    assert not nothing.is_just()
    assert nothing.get_or_else(10) == 10

    # Map
    result = just_5.map(lambda x: x * 2)
    assert result.get_or_else(0) == 10

    # FlatMap
    result2 = just_5.flat_map(lambda x: Maybe.just(x + 3))
    assert result2.get_or_else(0) == 8


def test_continuation_passing_style() -> None:
    """Test CPS optimization."""
    step1 = Step("filter", "users", Cost(10.0))
    step2 = Step("filter", "users", Cost(8.0))
    plan = ImmutablePlan(steps=(step1, step2))

    # Optimize with identity continuation
    optimized = optimize_cps(plan, lambda p: p)

    # Should merge filters
    assert len(optimized.steps) == 1


def test_lens_pattern() -> None:
    """Test lens for immutable updates."""
    step1 = Step("scan", "users", Cost(10.0))
    plan = ImmutablePlan(steps=(step1,))

    # Update cost via lens
    lens = step_cost_lens(0)
    modify_cost = lens.modify(lambda c: c * 0.5)
    updated = modify_cost(plan)

    assert plan.steps[0].cost.value == 10.0
    assert updated.steps[0].cost.value == 5.0


def test_rule_engine() -> None:
    """Test priority queue rule engine."""
    engine = RuleEngine()

    # Add rules
    engine.add_rule(
        OptimizationRule(
            priority=1, name="fold", apply=lambda p: apply_constant_folding_rule(p)
        )
    )
    engine.add_rule(
        OptimizationRule(
            priority=2, name="reorder", apply=lambda p: apply_reorder_rule(p)
        )
    )

    step1 = Step("expensive", "users", Cost(100.0))
    step2 = Step("cheap", "posts", Cost(1.0))
    plan = ImmutablePlan(steps=(step1, step2))

    optimized = engine.apply_all(plan)
    # Should reorder (cheap before expensive)
    assert optimized.steps[0].operation == "cheap"


def test_walrus_operator() -> None:
    """Test walrus operator usage."""
    expr = BinaryOp("+", Literal(2), Literal(3))
    folded = fold_if_constant(expr)
    assert isinstance(folded, Literal)
    assert folded.value == 5

    # Non-foldable
    expr2 = BinaryOp("+", Variable("x"), Literal(3))
    result = fold_if_constant(expr2)
    assert isinstance(result, BinaryOp)


def test_match_statement() -> None:
    """Test pattern matching with match statement."""
    # Constant folding
    expr1 = BinaryOp("+", Literal(2), Literal(3))
    assert fold_constant(expr1) == Literal(5)

    # Multiplication by zero
    expr2 = BinaryOp("*", Literal(0), Variable("x"))
    assert fold_constant(expr2) == Literal(0)

    # Multiplication by one
    expr3 = BinaryOp("*", Literal(1), Variable("x"))
    assert fold_constant(expr3) == Variable("x")

    # Boolean logic
    expr4 = BinaryOp("and", Literal(False), Variable("y"))
    assert fold_constant(expr4) == Literal(False)


def test_trampoline() -> None:
    """Test stack-safe recursion with trampoline."""
    step1 = Step("filter", "users", Cost(10.0))
    step2 = Step("filter", "users", Cost(8.0))
    plan = ImmutablePlan(steps=(step1, step2))

    result = trampoline(optimize_recursive(plan))
    assert isinstance(result, ImmutablePlan)


def test_fixpoint_iteration() -> None:
    """Test fixpoint optimization."""
    step1 = Step("expensive", "users", Cost(100.0))
    step2 = Step("cheap", "posts", Cost(1.0))
    plan = ImmutablePlan(steps=(step1, step2))

    optimized = optimize_fixpoint(plan)
    # Should reach fixpoint
    assert isinstance(optimized, ImmutablePlan)


def test_cost_model_operators() -> None:
    """Test cost model operator overloading."""
    cost1 = Cost(10.0)
    cost2 = Cost(5.0)

    # Addition
    assert (cost1 + cost2).value == 15.0

    # Multiplication
    assert (cost1 * 2.0).value == 20.0

    # Comparison
    assert cost2 < cost1
    assert cost1 == Cost(10.0)


def test_full_optimization_pipeline() -> None:
    """Test complete optimization pipeline."""
    # Build complex plan
    steps = (
        Step("scan", "users", Cost(50.0)),
        Step("filter", "users", Cost(20.0)),
        Step("filter", "users", Cost(15.0)),
        Step("join", "posts", Cost(100.0)),
        Step("project", "results", Cost(5.0)),
    )
    plan = ImmutablePlan(steps=steps)

    # Run optimization
    optimized = optimize_fixpoint(plan)

    # Verify optimization occurred
    assert optimized.total_cost() <= plan.total_cost()


def test_expression_compilation_with_variables() -> None:
    """Test expression compilation with variable environment."""
    expr = BinaryOp("+", Variable("x"), Literal(10))
    env = {"x": 5}
    compiled = compile_expression(expr, env)
    assert compiled() == 15


def test_plan_total_cost() -> None:
    """Test plan total cost calculation."""
    steps = (
        Step("scan", "users", Cost(10.0)),
        Step("filter", "users", Cost(5.0)),
        Step("project", "results", Cost(2.0)),
    )
    plan = ImmutablePlan(steps=steps)
    assert plan.total_cost() == Cost(17.0)


def run_all_tests() -> tuple[int, int]:
    """Run all tests and return (passed, total) counts."""
    tests = [
        test_algebraic_data_types,
        test_jit_compilation,
        test_persistent_data_structures,
        test_maybe_monad,
        test_continuation_passing_style,
        test_lens_pattern,
        test_rule_engine,
        test_walrus_operator,
        test_match_statement,
        test_trampoline,
        test_fixpoint_iteration,
        test_cost_model_operators,
        test_full_optimization_pipeline,
        test_expression_compilation_with_variables,
        test_plan_total_cost,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            test()
            passed += 1
            print(f"✓ {test.__name__}")
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
        except Exception as e:
            print(f"✗ {test.__name__}: {type(e).__name__}: {e}")

    return passed, total


def main() -> None:
    """Run prototype demonstration."""
    print("=" * 80)
    print("HYPER-ADVANCED DARK MATTER QUERY PLAN OPTIMIZER PROTOTYPE")
    print("=" * 80)
    print()

    print("Demonstrated Techniques:")
    print("1. ✓ Algebraic Data Types (Expression Tree)")
    print("2. ✓ JIT-Style Compilation (exec/compile)")
    print("3. ✓ Persistent Data Structures (Immutable Updates)")
    print("4. ✓ Monad Pattern (Maybe with bind/map/flatMap)")
    print("5. ✓ Continuation-Passing Style (CPS Optimization)")
    print("6. ✓ Lens Pattern (Deep Immutable Updates)")
    print("7. ✓ Priority Queue Rule Engine")
    print("8. ✓ Walrus Operator (Inline Assignment)")
    print("9. ✓ Match Statement (Pattern Matching)")
    print("10. ✓ Trampoline (Stack-Safe Recursion)")
    print("11. ✓ Fixpoint Iteration")
    print("12. ✓ Cost Model with Operator Overloading")
    print()

    print("Running Tests...")
    print("-" * 80)
    passed, total = run_all_tests()
    print("-" * 80)
    print()

    if passed == total:
        print(f"✓ All {total} tests passed!")
    else:
        print(f"✗ {passed}/{total} tests passed ({total - passed} failed)")

    print()
    print("=" * 80)
    print("DEMO: Query Plan Optimization")
    print("=" * 80)

    # Create example plan
    steps = (
        Step("scan", "users", Cost(100.0)),
        Step("filter", "users", Cost(50.0)),
        Step("filter", "users", Cost(30.0)),
        Step("expensive_op", "posts", Cost(200.0)),
        Step("cheap_op", "results", Cost(5.0)),
    )
    plan = ImmutablePlan(steps=steps)

    print(f"\nOriginal Plan (cost={plan.total_cost().value}):")
    for i, step in enumerate(plan.steps):
        print(f"  {i+1}. {step.operation:15} {step.target:10} cost={step.cost.value}")

    # Optimize
    optimized = optimize_fixpoint(plan)

    print(f"\nOptimized Plan (cost={optimized.total_cost().value}):")
    for i, step in enumerate(optimized.steps):
        print(f"  {i+1}. {step.operation:15} {step.target:10} cost={step.cost.value}")

    savings = plan.total_cost().value - optimized.total_cost().value
    print(f"\nCost Savings: {savings:.1f} ({savings/plan.total_cost().value*100:.1f}%)")

    # Expression folding demo
    print()
    print("=" * 80)
    print("DEMO: Expression Constant Folding")
    print("=" * 80)

    expr = BinaryOp(
        "*",
        BinaryOp("+", Literal(2), Literal(3)),
        BinaryOp("*", Literal(1), Variable("x")),
    )
    print(f"\nOriginal: (2 + 3) * (1 * x)")
    folded = fold_constant(expr)
    print(f"Folded:   5 * x")
    print(f"Result:   {folded}")


if __name__ == "__main__":
    main()
