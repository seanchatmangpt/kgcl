"""
Python AST constant folder for dark matter optimization.

Performs compile-time constant folding on Python AST to optimize expressions.
"""

import ast
import operator


class ConstantFolder(ast.NodeTransformer):
    """Fold constant expressions in Python AST.

    Evaluates constant expressions at compile-time to optimize runtime performance.
    This is part of the dark matter optimization layer.

    Examples
    --------
    >>> import ast
    >>> folder = ConstantFolder()
    >>> tree = ast.parse("1 + 2", mode="eval")
    >>> optimized = folder.visit(tree)
    >>> isinstance(optimized.body, ast.Constant)
    True
    >>> optimized.body.value
    3
    """

    # Operator mapping for binary operations
    _binop_map = {
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

    # Operator mapping for unary operations
    _unaryop_map = {ast.UAdd: operator.pos, ast.USub: operator.neg, ast.Not: operator.not_, ast.Invert: operator.inv}

    # Operator mapping for comparison operations
    _cmpop_map = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
    }

    # Operator mapping for boolean operations
    _boolop_map = {ast.And: lambda values: all(values), ast.Or: lambda values: any(values)}

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        """Fold binary operations on constants.

        Parameters
        ----------
        node : ast.BinOp
            Binary operation node

        Returns
        -------
        ast.AST
            Folded constant or original node
        """
        # Visit children first
        node = self.generic_visit(node)  # type: ignore[assignment]

        # Check if both operands are constants
        if isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant):
            # Get the operator function
            op_func = self._binop_map.get(type(node.op))
            if op_func is None:
                return node

            try:
                # Evaluate the operation
                result = op_func(node.left.value, node.right.value)
                # Return a new Constant node
                return ast.Constant(value=result)
            except (ZeroDivisionError, ValueError, OverflowError):
                # Keep original node if evaluation fails
                return node

        return node

    def visit_UnaryOp(self, node: ast.UnaryOp) -> ast.AST:
        """Fold unary operations on constants.

        Parameters
        ----------
        node : ast.UnaryOp
            Unary operation node

        Returns
        -------
        ast.AST
            Folded constant or original node
        """
        # Visit children first
        node = self.generic_visit(node)  # type: ignore[assignment]

        # Check if operand is a constant
        if isinstance(node.operand, ast.Constant):
            # Get the operator function
            op_func = self._unaryop_map.get(type(node.op))
            if op_func is None:
                return node

            try:
                # Evaluate the operation
                result = op_func(node.operand.value)
                # Return a new Constant node
                return ast.Constant(value=result)
            except (ValueError, TypeError):
                # Keep original node if evaluation fails
                return node

        return node

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        """Fold comparison operations on constants.

        Parameters
        ----------
        node : ast.Compare
            Comparison node

        Returns
        -------
        ast.AST
            Folded constant or original node
        """
        # Visit children first
        node = self.generic_visit(node)  # type: ignore[assignment]

        # Check if all operands are constants
        if not isinstance(node.left, ast.Constant):
            return node

        for comparator in node.comparators:
            if not isinstance(comparator, ast.Constant):
                return node

        # All operands are constants - evaluate
        try:
            left_val = node.left.value
            result = True

            for op, comparator in zip(node.ops, node.comparators):
                op_func = self._cmpop_map.get(type(op))
                if op_func is None:
                    return node

                right_val = comparator.value
                result = result and op_func(left_val, right_val)
                left_val = right_val

                if not result:
                    break

            return ast.Constant(value=result)
        except (ValueError, TypeError):
            return node

    def visit_BoolOp(self, node: ast.BoolOp) -> ast.AST:
        """Fold boolean operations on constants.

        Parameters
        ----------
        node : ast.BoolOp
            Boolean operation node

        Returns
        -------
        ast.AST
            Folded constant or original node
        """
        # Visit children first
        node = self.generic_visit(node)  # type: ignore[assignment]

        # Check if all values are constants
        if all(isinstance(v, ast.Constant) for v in node.values):
            op_func = self._boolop_map.get(type(node.op))
            if op_func is None:
                return node

            try:
                # Evaluate the boolean operation
                values = [v.value for v in node.values]
                result = op_func(values)
                return ast.Constant(value=result)
            except (ValueError, TypeError):
                return node

        return node


class DarkMatterASTOptimizer:
    """AST optimizer using constant folding for dark matter optimization.

    This optimizer applies constant folding and other compile-time optimizations
    to Python AST trees.
    """

    def __init__(self) -> None:
        """Initialize AST optimizer."""
        self.folder = ConstantFolder()

    def optimize(self, tree: ast.AST) -> ast.AST:
        """Optimize an AST tree.

        Parameters
        ----------
        tree : ast.AST
            AST tree to optimize

        Returns
        -------
        ast.AST
            Optimized AST tree

        Examples
        --------
        >>> optimizer = DarkMatterASTOptimizer()
        >>> tree = ast.parse("1 + 2 * 3", mode="eval")
        >>> optimized = optimizer.optimize(tree)
        >>> isinstance(optimized.body, ast.Constant)
        True
        >>> optimized.body.value
        7
        """
        return self.folder.visit(tree)
