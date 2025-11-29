"""Ripple Down Rules engine for worklet selection.

Implements the RDR algorithm for traversing rule trees
and selecting appropriate worklets for exceptions.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from kgcl.yawl.worklets.exceptions import RDRTreeError, RuleEvaluationError
from kgcl.yawl.worklets.models import RDRNode, RDRTree
from kgcl.yawl.worklets.protocols import RDREvaluatorProtocol

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuleContext:
    """Context for rule evaluation.

    Provides data for condition evaluation during
    RDR tree traversal.

    Parameters
    ----------
    case_id : str
        Case ID
    task_id : str | None
        Task ID (if item-level)
    work_item_id : str | None
        Work item ID (if item-level)
    exception_type : str
        Type of exception
    exception_message : str
        Exception message
    case_data : dict[str, Any]
        Case-level data
    work_item_data : dict[str, Any]
        Work item data
    attributes : dict[str, Any]
        Additional attributes

    Examples
    --------
    >>> context = RuleContext(case_id="case-001", exception_type="TIMEOUT", case_data={"priority": "high"})
    >>> context.get("priority")
    'high'
    """

    case_id: str
    task_id: str | None = None
    work_item_id: str | None = None
    exception_type: str = ""
    exception_message: str = ""
    case_data: dict[str, Any] = field(default_factory=dict)
    work_item_data: dict[str, Any] = field(default_factory=dict)
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate rule context data."""
        if not self.case_id:
            raise ValueError("RuleContext case_id cannot be empty")

    def __repr__(self) -> str:
        """Developer representation."""
        return f"RuleContext(case_id={self.case_id!r}, exception_type={self.exception_type!r})"

    def __str__(self) -> str:
        """Human-readable representation."""
        return f"RuleContext(case_id={self.case_id}, exception={self.exception_type})"

    def __eq__(self, other: object) -> bool:
        """Equality comparison by case_id and work_item_id."""
        if not isinstance(other, RuleContext):
            return False
        return self.case_id == other.case_id and self.work_item_id == other.work_item_id

    def __hash__(self) -> int:
        """Hash by case_id and work_item_id."""
        return hash((self.case_id, self.work_item_id))

    def get(self, name: str, default: Any = None) -> Any:
        """Get context value.

        Looks in work_item_data, case_data, then attributes.

        Parameters
        ----------
        name : str
            Variable name
        default : Any
            Default value

        Returns
        -------
        Any
            Value or default
        """
        if name in self.work_item_data:
            return self.work_item_data[name]
        if name in self.case_data:
            return self.case_data[name]
        return self.attributes.get(name, default)


@dataclass
class RDREngine:
    """Engine for traversing RDR trees and selecting worklets.

    Implements the Ripple Down Rules algorithm for
    knowledge-based exception handling.

    Parameters
    ----------
    trees : dict[str, RDRTree]
        RDR trees by key (task_id:exception_type)
    evaluator : RDREvaluatorProtocol | None
        Custom condition evaluator (Protocol-based)
    enable_caching : bool
        Enable condition evaluation caching
    cache_size : int
        Maximum cache size for LRU cache

    Examples
    --------
    >>> engine = RDREngine()
    >>> engine.add_tree(tree)
    >>> worklet_id = engine.find_worklet(context)
    """

    trees: dict[str, RDRTree] = field(default_factory=dict)
    evaluator: RDREvaluatorProtocol | None = None
    enable_caching: bool = True
    cache_size: int = 128

    def add_tree(self, tree: RDRTree) -> None:
        """Add an RDR tree.

        Parameters
        ----------
        tree : RDRTree
            Tree to add
        """
        key = self._make_key(tree.task_id, tree.exception_type)
        self.trees[key] = tree

    def get_tree(self, task_id: str | None = None, exception_type: str = "default") -> RDRTree | None:
        """Get RDR tree for task and exception type.

        Parameters
        ----------
        task_id : str | None
            Task ID (None for case-level)
        exception_type : str
            Exception type

        Returns
        -------
        RDRTree | None
            Tree or None
        """
        key = self._make_key(task_id, exception_type)
        return self.trees.get(key)

    def find_worklet(self, context: RuleContext, task_id: str | None = None) -> str | None:
        """Find appropriate worklet for the given context.

        Traverses the RDR tree to find a matching rule.

        Parameters
        ----------
        context : RuleContext
            Exception context
        task_id : str | None
            Task ID for item-level exceptions

        Returns
        -------
        str | None
            Worklet ID to execute or None
        """
        # Try task-specific tree first
        tree = self.get_tree(task_id, context.exception_type)
        if tree:
            result = self._traverse(tree.root, context)
            if result:
                return result

        # Fall back to case-level tree
        if task_id:
            tree = self.get_tree(None, context.exception_type)
            if tree:
                result = self._traverse(tree.root, context)
                if result:
                    return result

        # Try default exception type
        tree = self.get_tree(task_id, "default")
        if tree:
            result = self._traverse(tree.root, context)
            if result:
                return result

        # Final fallback: case-level default
        if task_id:
            tree = self.get_tree(None, "default")
            if tree:
                return self._traverse(tree.root, context)

        return None

    def _traverse(self, node: RDRNode, context: RuleContext) -> str | None:
        """Traverse RDR tree from node.

        Parameters
        ----------
        node : RDRNode
            Starting node
        context : RuleContext
            Evaluation context

        Returns
        -------
        str | None
            Worklet ID or None
        """
        if self._evaluate_condition(node.condition, context):
            # Condition is true
            if node.true_child:
                # Try refinement
                result = self._traverse(node.true_child, context)
                if result:
                    return result
            # Return this node's conclusion
            return node.conclusion
        else:
            # Condition is false
            if node.false_child:
                return self._traverse(node.false_child, context)
            return None

    def _evaluate_condition(self, condition: str, context: RuleContext) -> bool:
        """Evaluate a condition expression.

        Parameters
        ----------
        condition : str
            Condition expression
        context : RuleContext
            Evaluation context

        Returns
        -------
        bool
            Evaluation result

        Raises
        ------
        RuleEvaluationError
            If condition evaluation fails
        """
        # Validate condition
        if not condition or not condition.strip():
            raise RuleEvaluationError(condition=condition, message="Condition cannot be empty")

        # Use custom evaluator if provided
        if self.evaluator:
            try:
                return self.evaluator.evaluate(condition, context)
            except Exception as e:
                raise RuleEvaluationError(condition=condition, message=f"Custom evaluator failed: {e}") from e

        # Built-in evaluation (caching disabled for now due to context complexity)
        # In production, implement proper caching with context serialization
        return self._default_evaluate(condition, context)

    def _default_evaluate(self, condition: str, context: RuleContext) -> bool:
        """Default condition evaluator.

        Supports simple conditions like:
        - "true" / "false"
        - "var == value"
        - "var != value"
        - "var > value" / "var < value"
        - "var in [a, b, c]"
        - Safe Python expressions (if enabled)

        Parameters
        ----------
        condition : str
            Condition expression
        context : RuleContext
            Evaluation context

        Returns
        -------
        bool
            Evaluation result

        Raises
        ------
        RuleEvaluationError
            If condition evaluation fails
        """
        condition = condition.strip()

        # Boolean literals (case-insensitive)
        condition_lower = condition.lower()
        if condition_lower in ("true", "1", "yes"):
            return True
        if condition_lower in ("false", "0", "no"):
            return False

        # Try to parse as comparison
        try:
            # Check for operators (order matters - check longer first)
            if ">=" in condition:
                parts = condition.split(">=", 1)
                var_name = parts[0].strip()
                threshold = float(parts[1].strip())
                actual = float(context.get(var_name, 0))
                return actual >= threshold

            if "<=" in condition:
                parts = condition.split("<=", 1)
                var_name = parts[0].strip()
                threshold = float(parts[1].strip())
                actual = float(context.get(var_name, 0))
                return actual <= threshold

            if "==" in condition:
                parts = condition.split("==", 1)
                var_name = parts[0].strip()
                expected = parts[1].strip().strip("'\"")
                actual = str(context.get(var_name, "")).lower()
                return actual == expected.lower()

            if "!=" in condition:
                parts = condition.split("!=", 1)
                var_name = parts[0].strip()
                expected = parts[1].strip().strip("'\"")
                actual = str(context.get(var_name, "")).lower()
                return actual != expected.lower()

            if ">" in condition and ">=" not in condition:
                parts = condition.split(">", 1)
                var_name = parts[0].strip()
                threshold = float(parts[1].strip())
                actual = float(context.get(var_name, 0))
                return actual > threshold

            if "<" in condition and "<=" not in condition:
                parts = condition.split("<", 1)
                var_name = parts[0].strip()
                threshold = float(parts[1].strip())
                actual = float(context.get(var_name, 0))
                return actual < threshold

            if " in " in condition:
                parts = condition.split(" in ", 1)
                var_name = parts[0].strip()
                values_str = parts[1].strip()
                # Parse list
                if values_str.startswith("[") and values_str.endswith("]"):
                    values_str = values_str[1:-1]
                values = [v.strip().strip("'\"") for v in values_str.split(",") if v.strip()]
                actual = str(context.get(var_name, "")).lower()
                return actual in [v.lower() for v in values]

            # Check if condition is just a variable name (truthy check)
            value = context.get(condition)
            return bool(value)

        except (ValueError, TypeError) as e:
            raise RuleEvaluationError(condition=condition, message=f"Failed to evaluate condition: {e}") from e

    def add_rule(
        self,
        tree_id: str,
        parent_node_id: str,
        is_true_branch: bool,
        condition: str,
        conclusion: str | None = None,
        cornerstone_case: dict[str, Any] | None = None,
    ) -> RDRNode:
        """Add a new rule to the tree.

        This is the incremental knowledge acquisition mechanism.

        Parameters
        ----------
        tree_id : str
            Tree ID
        parent_node_id : str
            Parent node ID
        is_true_branch : bool
            Whether to add on true or false branch
        condition : str
            Condition expression
        conclusion : str | None
            Worklet ID for conclusion
        cornerstone_case : dict[str, Any] | None
            Case that generated this rule

        Returns
        -------
        RDRNode
            Created node

        Raises
        ------
        RDRTreeError
            If tree or parent node not found
        RuleEvaluationError
            If condition is invalid
        """
        # Validate condition
        if not condition or not condition.strip():
            raise RuleEvaluationError(condition=condition, message="Condition cannot be empty")

        # Find tree by ID
        tree = None
        for t in self.trees.values():
            if t.id == tree_id:
                tree = t
                break

        if not tree:
            raise RDRTreeError(tree_id=tree_id, message=f"RDR tree not found: {tree_id}")

        parent = tree.get_node(parent_node_id)
        if not parent:
            raise RDRTreeError(
                tree_id=tree_id, node_id=parent_node_id, message=f"Parent node not found: {parent_node_id}"
            )

        # Create new node
        import uuid

        new_node = RDRNode(
            id=str(uuid.uuid4()), condition=condition, conclusion=conclusion, cornerstone_case=cornerstone_case
        )

        # Add to tree
        tree.add_node(new_node)

        # Link to parent
        if is_true_branch:
            parent.add_true_child(new_node)
        else:
            parent.add_false_child(new_node)

        logger.info(
            "Added RDR rule", extra={"tree_id": tree_id, "node_id": new_node.id, "parent_node_id": parent_node_id}
        )

        return new_node

    def _make_key(self, task_id: str | None, exception_type: str) -> str:
        """Make tree lookup key.

        Parameters
        ----------
        task_id : str | None
            Task ID
        exception_type : str
            Exception type

        Returns
        -------
        str
            Lookup key
        """
        return f"{task_id or '_case_'}:{exception_type}"
