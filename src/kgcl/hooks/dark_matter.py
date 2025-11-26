"""
Dark Matter Query Optimizer.

Advanced query optimization techniques including critical path analysis,
query plan rewriting, cost-based optimization, and parallel execution planning.
Ported from UNRDF dark-matter-core.mjs and dark-matter/optimizer.mjs.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class OptimizationRule(Enum):
    """Optimization rule types."""

    FILTER_PUSHDOWN = "filter_pushdown"
    JOIN_REORDERING = "join_reordering"
    PREDICATE_ELIMINATION = "predicate_elimination"
    CONSTANT_FOLDING = "constant_folding"
    SUBQUERY_FLATTENING = "subquery_flattening"
    PROJECTION_PUSHDOWN = "projection_pushdown"


@dataclass
class QueryStep:
    """Single step in query execution plan."""

    step_id: int
    operation: str
    cost: float
    dependencies: list[int] = field(default_factory=list)
    parallelizable: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizedPlan:
    """Result of dark matter optimization."""

    original_cost: float
    optimized_cost: float
    rewrite_rules_applied: list[str]
    parallelizable_steps: list[int]
    estimated_improvement: float  # Percentage
    critical_path: list[int] = field(default_factory=list)
    optimization_metadata: dict[str, Any] = field(default_factory=dict)


class DarkMatterOptimizer:
    """Apply advanced query optimization techniques.

    Implements:
    - Critical path analysis for execution ordering
    - Query plan rewriting (filter pushdown, join reordering)
    - Cost-based optimization
    - Parallel execution planning
    - Predicate elimination
    """

    def __init__(self) -> None:
        """Initialize dark matter optimizer."""
        self.optimization_rules: dict[str, Callable[..., Any]] = {}
        self.cost_model: dict[str, float] = {
            "scan": 10.0,
            "filter": 1.0,
            "join": 50.0,
            "project": 2.0,
            "aggregate": 15.0,
            "sort": 25.0,
        }
        self._register_rules()

    def _register_rules(self) -> None:
        """Register optimization rules."""
        self.optimization_rules[OptimizationRule.FILTER_PUSHDOWN.value] = self._apply_filter_pushdown
        self.optimization_rules[OptimizationRule.JOIN_REORDERING.value] = self._apply_join_reordering
        self.optimization_rules[OptimizationRule.PREDICATE_ELIMINATION.value] = self._apply_predicate_elimination
        self.optimization_rules[OptimizationRule.CONSTANT_FOLDING.value] = self._apply_constant_folding
        self.optimization_rules[OptimizationRule.PROJECTION_PUSHDOWN.value] = self._apply_projection_pushdown

    def optimize_query_plan(self, plan: dict[str, Any]) -> OptimizedPlan:
        """Apply optimization rules to query plan.

        Parameters
        ----------
        plan : Dict[str, Any]
            Query execution plan with steps

        Returns
        -------
        OptimizedPlan
            Optimized plan with metrics
        """
        steps = plan.get("steps", [])
        original_cost = self._calculate_plan_cost(steps)

        # Apply optimization rules
        optimized_steps = steps.copy()
        rules_applied: list[str] = []

        for rule_name, rule_fn in self.optimization_rules.items():
            result = rule_fn(optimized_steps)
            if result["applied"]:
                optimized_steps = result["steps"]
                rules_applied.append(rule_name)

        optimized_cost = self._calculate_plan_cost(optimized_steps)
        improvement = ((original_cost - optimized_cost) / original_cost * 100) if original_cost > 0 else 0.0

        # Find parallelizable steps
        parallelizable = self._find_parallelizable_steps(optimized_steps)

        # Compute critical path
        critical_path = self.analyze_critical_path(optimized_steps)

        return OptimizedPlan(
            original_cost=original_cost,
            optimized_cost=optimized_cost,
            rewrite_rules_applied=rules_applied,
            parallelizable_steps=parallelizable,
            estimated_improvement=improvement,
            critical_path=critical_path,
            optimization_metadata={"total_steps": len(optimized_steps)},
        )

    def _calculate_plan_cost(self, steps: list[dict[str, Any]]) -> float:
        """Calculate total cost of execution plan."""
        total_cost = 0.0
        for step in steps:
            operation = step.get("operation", "scan")
            base_cost = self.cost_model.get(operation, 10.0)
            cardinality = step.get("cardinality", 1.0)
            total_cost += base_cost * cardinality
        return total_cost

    def _apply_filter_pushdown(self, steps: list[dict[str, Any]]) -> dict[str, Any]:
        """Push filters closer to data source.

        Filter pushdown reduces intermediate result sizes by applying
        filters as early as possible.
        """
        # Find filter steps and their positions
        filter_indices = [i for i, s in enumerate(steps) if s.get("operation") == "filter"]

        if not filter_indices:
            return {"applied": False, "steps": steps}

        # Try to move filters earlier
        modified = False
        new_steps = steps.copy()

        for filter_idx in filter_indices:
            # Find the earliest position this filter can move to
            filter_step = new_steps[filter_idx]
            dependencies = set(filter_step.get("dependencies", []))

            # Move filter as early as possible
            target_idx = 0
            for i in range(filter_idx):
                if new_steps[i].get("step_id") in dependencies:
                    target_idx = i + 1

            if target_idx < filter_idx:
                # Move filter to earlier position
                new_steps.insert(target_idx, new_steps.pop(filter_idx))
                modified = True

        return {"applied": modified, "steps": new_steps}

    def _apply_join_reordering(self, steps: list[dict[str, Any]]) -> dict[str, Any]:
        """Reorder joins based on estimated cardinality.

        Smaller intermediate results first reduces join cost.
        """
        join_indices = [i for i, s in enumerate(steps) if s.get("operation") == "join"]

        if len(join_indices) < 2:
            return {"applied": False, "steps": steps}

        # Sort joins by estimated cardinality
        new_steps = steps.copy()
        joins = [(i, new_steps[i]) for i in join_indices]
        joins.sort(key=lambda x: x[1].get("cardinality", float("inf")))

        # Reorder if beneficial
        modified = False
        for new_pos, (old_pos, join_step) in enumerate(joins):
            if new_pos != old_pos:
                modified = True

        if modified:
            # Rebuild steps list with reordered joins
            non_joins = [(i, s) for i, s in enumerate(new_steps) if s.get("operation") != "join"]
            result_steps = []
            join_idx = 0

            for i, step in enumerate(new_steps):
                if step.get("operation") == "join" and join_idx < len(joins):
                    result_steps.append(joins[join_idx][1])
                    join_idx += 1
                else:
                    result_steps.append(step)

            return {"applied": True, "steps": result_steps}

        return {"applied": False, "steps": steps}

    def _apply_predicate_elimination(self, steps: list[dict[str, Any]]) -> dict[str, Any]:
        """Eliminate redundant predicates."""
        # Remove duplicate filters
        seen_predicates: set[str] = set()
        new_steps = []
        modified = False

        for step in steps:
            if step.get("operation") == "filter":
                predicate = str(step.get("predicate", ""))
                if predicate in seen_predicates:
                    modified = True
                    continue
                seen_predicates.add(predicate)

            new_steps.append(step)

        return {"applied": modified, "steps": new_steps}

    def _apply_constant_folding(self, steps: list[dict[str, Any]]) -> dict[str, Any]:
        """Fold constant expressions at optimization time.

        Evaluates constant expressions and replaces them with computed values:
        - Arithmetic: "2 + 3" -> "5"
        - String concat: "'foo' + 'bar'" -> "'foobar'"
        - Boolean: "true AND false" -> "false"
        - Comparisons: "5 > 3" -> "true"

        Parameters
        ----------
        steps : list[dict[str, Any]]
            Query execution steps with potential constant expressions

        Returns
        -------
        dict[str, Any]
            {"applied": bool, "steps": list[dict]} with folded constants
        """
        import ast
        import operator as op

        SAFE_OPERATORS = {
            ast.Add: op.add,
            ast.Sub: op.sub,
            ast.Mult: op.mul,
            ast.Div: op.truediv,
            ast.FloorDiv: op.floordiv,
            ast.Mod: op.mod,
            ast.Pow: op.pow,
            ast.BitOr: op.or_,
            ast.BitAnd: op.and_,
            ast.BitXor: op.xor,
            ast.Eq: op.eq,
            ast.NotEq: op.ne,
            ast.Lt: op.lt,
            ast.LtE: op.le,
            ast.Gt: op.gt,
            ast.GtE: op.ge,
        }

        def is_constant_expr(expr: str) -> bool:
            """Check if expression contains only literals and operators."""
            if not expr or not isinstance(expr, str):
                return False
            try:
                tree = ast.parse(expr, mode="eval")
                # Check if all nodes are literals or operators
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Constant, ast.Expr, ast.Expression, ast.BinOp, ast.UnaryOp, ast.Compare)):
                        continue
                    if type(node) in SAFE_OPERATORS:
                        continue
                    # Allow unary operator nodes
                    if isinstance(node, (ast.UAdd, ast.USub, ast.Not, ast.Invert)):
                        continue
                    if isinstance(node, (ast.Load, ast.Store)):
                        continue
                    # Variables, function calls, etc. are not constant
                    return False
                return True
            except (SyntaxError, ValueError):
                return False

        def eval_constant(expr: str) -> str:
            """Safely evaluate constant expression using AST."""
            try:
                tree = ast.parse(expr, mode="eval")
                result = self._eval_node(tree.body)
                return str(result)
            except Exception:
                # If evaluation fails, return original
                return expr

        modified = False
        new_steps = []
        for step in steps:
            if "expression" in step and is_constant_expr(step["expression"]):
                folded = eval_constant(step["expression"])
                if folded != step["expression"]:
                    new_step = {**step, "expression": folded}
                    new_steps.append(new_step)
                    modified = True
                else:
                    new_steps.append(step)
            else:
                new_steps.append(step)

        return {"applied": modified, "steps": new_steps}

    def _eval_node(self, node: Any) -> Any:
        """Recursively evaluate AST node."""
        import ast
        import operator as op
        from collections.abc import Callable

        SAFE_OPERATORS: dict[type, Callable[[Any, Any], Any]] = {
            ast.Add: op.add,
            ast.Sub: op.sub,
            ast.Mult: op.mul,
            ast.Div: op.truediv,
            ast.FloorDiv: op.floordiv,
            ast.Mod: op.mod,
            ast.Pow: op.pow,
            ast.BitOr: op.or_,
            ast.BitAnd: op.and_,
            ast.BitXor: op.xor,
            ast.Eq: op.eq,
            ast.NotEq: op.ne,
            ast.Lt: op.lt,
            ast.LtE: op.le,
            ast.Gt: op.gt,
            ast.GtE: op.ge,
        }

        SAFE_UNARY: dict[type, Callable[[Any], Any]] = {
            ast.UAdd: op.pos,
            ast.USub: op.neg,
            ast.Not: op.not_,
            ast.Invert: op.invert,
        }

        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            operator_fn = SAFE_OPERATORS.get(type(node.op))
            if operator_fn:
                return operator_fn(left, right)
        if isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            operator_type = type(node.op)
            if operator_type in SAFE_UNARY:
                unary_fn = SAFE_UNARY[operator_type]
                return unary_fn(operand)
        if isinstance(node, ast.Compare):
            left = self._eval_node(node.left)
            if len(node.ops) == 1 and len(node.comparators) == 1:
                right = self._eval_node(node.comparators[0])
                operator_fn = SAFE_OPERATORS.get(type(node.ops[0]))
                if operator_fn:
                    return operator_fn(left, right)
        msg = f"Unsupported node type: {type(node).__name__}"
        raise ValueError(msg)

    def _apply_projection_pushdown(self, steps: list[dict[str, Any]]) -> dict[str, Any]:
        """Push projections (column selection) closer to source."""
        # Find projection steps
        projection_indices = [i for i, s in enumerate(steps) if s.get("operation") == "project"]

        if not projection_indices:
            return {"applied": False, "steps": steps}

        # Move projections earlier when possible
        modified = False
        new_steps = steps.copy()

        for proj_idx in projection_indices:
            proj_step = new_steps[proj_idx]
            columns = set(proj_step.get("columns", []))

            # Find earliest position based on column dependencies
            target_idx = 0
            for i in range(proj_idx):
                step_output = set(new_steps[i].get("output_columns", []))
                if columns.intersection(step_output):
                    target_idx = i + 1

            if target_idx < proj_idx:
                new_steps.insert(target_idx, new_steps.pop(proj_idx))
                modified = True

        return {"applied": modified, "steps": new_steps}

    def _find_parallelizable_steps(self, steps: list[dict[str, Any]]) -> list[int]:
        """Find steps that can be executed in parallel.

        Steps are parallelizable if they have no dependencies between them.
        """
        parallelizable: list[int] = []

        for i, step in enumerate(steps):
            dependencies = set(step.get("dependencies", []))
            # Check if any prior steps in current parallel group depend on this
            can_parallelize = True

            for j in parallelizable:
                other_deps = set(steps[j].get("dependencies", []))
                if step.get("step_id") in other_deps or steps[j].get("step_id") in dependencies:
                    can_parallelize = False
                    break

            if can_parallelize:
                parallelizable.append(i)

        return parallelizable

    def analyze_critical_path(self, steps: list[dict[str, Any]]) -> list[int]:
        """Find critical path in execution steps.

        The critical path is the longest sequence of dependent steps
        that determines minimum execution time.

        Parameters
        ----------
        steps : List[Dict[str, Any]]
            Execution plan steps

        Returns
        -------
        List[int]
            Step IDs in critical path
        """
        if not steps:
            return []

        # Build dependency graph
        step_costs = {}
        dependencies = {}

        for step in steps:
            step_id = step.get("step_id", 0)
            step_costs[step_id] = step.get("cost", 1.0)
            dependencies[step_id] = step.get("dependencies", [])

        # Compute longest path using dynamic programming
        memo: dict[int, tuple[float, list[int]]] = {}

        def longest_path(step_id: int) -> tuple[float, list[int]]:
            """Recursively compute longest path from step_id."""
            if step_id in memo:
                return memo[step_id]

            deps = dependencies.get(step_id, [])
            if not deps:
                # Leaf node
                result = (step_costs.get(step_id, 0.0), [step_id])
                memo[step_id] = result
                return result

            # Find longest path through dependencies
            max_cost = 0.0
            max_path: list[int] = []

            for dep_id in deps:
                dep_cost, dep_path = longest_path(dep_id)
                if dep_cost > max_cost:
                    max_cost = dep_cost
                    max_path = dep_path

            current_cost = step_costs.get(step_id, 0.0)
            result = (max_cost + current_cost, [*max_path, step_id])
            memo[step_id] = result
            return result

        # Find overall longest path
        max_total_cost = 0.0
        critical_path: list[int] = []

        for step_id in step_costs:
            cost, path = longest_path(step_id)
            if cost > max_total_cost:
                max_total_cost = cost
                critical_path = path

        return critical_path

    def suggest_parallelization(self, plan: dict[str, Any]) -> list[tuple[int, int]]:
        """Suggest step pairs that can run in parallel.

        Parameters
        ----------
        plan : Dict[str, Any]
            Query execution plan

        Returns
        -------
        List[Tuple[int, int]]
            Pairs of step IDs that can execute in parallel
        """
        steps = plan.get("steps", [])
        parallel_pairs: list[tuple[int, int]] = []

        for i, step_a in enumerate(steps):
            step_a_id = step_a.get("step_id")
            deps_a = set(step_a.get("dependencies", []))

            for j, step_b in enumerate(steps[i + 1 :], start=i + 1):
                step_b_id = step_b.get("step_id")
                deps_b = set(step_b.get("dependencies", []))

                # Can parallelize if neither depends on the other
                if step_a_id not in deps_b and step_b_id not in deps_a:
                    parallel_pairs.append((step_a_id, step_b_id))

        return parallel_pairs

    def estimate_speedup(self, plan: dict[str, Any], parallel_degree: int = 4) -> float:
        """Estimate speedup from parallelization.

        Parameters
        ----------
        plan : Dict[str, Any]
            Query execution plan
        parallel_degree : int
            Number of parallel workers

        Returns
        -------
        float
            Estimated speedup factor
        """
        steps = plan.get("steps", [])
        critical_path = self.analyze_critical_path(steps)

        # Calculate total work
        total_cost = sum(s.get("cost", 1.0) for s in steps)

        # Calculate critical path cost
        critical_cost = sum(s.get("cost", 1.0) for s in steps if s.get("step_id") in critical_path)

        # Amdahl's law: speedup limited by critical path
        parallel_cost = critical_cost + (total_cost - critical_cost) / parallel_degree
        speedup = total_cost / parallel_cost if parallel_cost > 0 else 1.0

        return speedup
