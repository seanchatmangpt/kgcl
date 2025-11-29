"""Expression evaluator for YAWL predicates and data bindings.

Supports:
- Literal values ("true", "false")
- Simple key lookup ("order_id")
- Dotted path navigation ("customer.name")
- XPath expressions ("/order/amount > 100")

Java Reference: YExpressionEvaluator
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any
from xml.etree.ElementTree import Element, SubElement


class ExpressionLanguage(Enum):
    """Supported expression languages."""

    LITERAL = auto()
    SIMPLE = auto()  # Direct key or dotted path
    XPATH = auto()


@dataclass(frozen=True)
class ExpressionResult:
    """Result of expression evaluation.

    Parameters
    ----------
    value : Any
        Evaluated value
    success : bool
        Whether evaluation succeeded
    error : str | None
        Error message if failed
    """

    value: Any
    success: bool
    error: str | None = None


@dataclass
class YExpressionContext:
    """Context for expression evaluation with case data.

    Parameters
    ----------
    variables : dict[str, Any]
        Case variables for evaluation
    net_variables : dict[str, str]
        Net-level variable definitions
    """

    variables: dict[str, Any] = field(default_factory=dict)
    net_variables: dict[str, str] = field(default_factory=dict)

    def to_xml_element(self) -> Element:
        """Convert case data to XML element for XPath evaluation.

        Returns
        -------
        Element
            XML representation of variables
        """
        return dict_to_xml(self.variables, "data")


def dict_to_xml(data: dict[str, Any], root_name: str = "data") -> Element:
    """Convert Python dict to XML element for XPath evaluation.

    Parameters
    ----------
    data : dict[str, Any]
        Data to convert
    root_name : str
        Root element name

    Returns
    -------
    Element
        XML element tree

    Examples
    --------
    >>> data = {"order": {"amount": 100, "status": "pending"}}
    >>> elem = dict_to_xml(data)
    >>> # Results in:
    >>> # <data>
    >>> #   <order>
    >>> #     <amount>100</amount>
    >>> #     <status>pending</status>
    >>> #   </order>
    >>> # </data>
    """
    root = Element(root_name)
    _dict_to_xml_recursive(data, root)
    return root


def _dict_to_xml_recursive(data: Any, parent: Element) -> None:
    """Recursively build XML from dict.

    Parameters
    ----------
    data : Any
        Data to convert
    parent : Element
        Parent element to add to
    """
    if isinstance(data, dict):
        for key, value in data.items():
            child = SubElement(parent, str(key))
            _dict_to_xml_recursive(value, child)
    elif isinstance(data, list):
        for item in data:
            item_elem = SubElement(parent, "item")
            _dict_to_xml_recursive(item, item_elem)
    else:
        parent.text = str(data) if data is not None else ""


@dataclass
class YExpressionEvaluator:
    """Evaluator for expressions against case data.

    Supports multiple expression types:
    - Literals: "true", "false"
    - Simple paths: "order_id", "customer.name"
    - XPath: "/data/order/amount > 100"

    Parameters
    ----------
    enable_xpath : bool
        Whether to enable XPath evaluation (requires elementpath)
    xpath_evaluator : Any | None
        Cached XPath evaluator instance
    """

    enable_xpath: bool = True
    _xpath_available: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        """Check if XPath library is available."""
        if self.enable_xpath:
            try:
                import elementpath  # noqa: F401

                self._xpath_available = True
            except ImportError:
                self._xpath_available = False

    def evaluate(self, expression: str, context: YExpressionContext) -> ExpressionResult:
        """Evaluate expression against context.

        Parameters
        ----------
        expression : str
            Expression to evaluate
        context : YExpressionContext
            Evaluation context with variables

        Returns
        -------
        ExpressionResult
            Evaluation result
        """
        # Detect expression type
        lang = self._detect_language(expression)

        try:
            if lang == ExpressionLanguage.LITERAL:
                value = self._evaluate_literal(expression)
            elif lang == ExpressionLanguage.XPATH:
                value = self._evaluate_xpath(expression, context)
            else:
                value = self._evaluate_simple(expression, context)

            return ExpressionResult(value=value, success=True)
        except Exception as e:
            return ExpressionResult(value=None, success=False, error=str(e))

    def evaluate_boolean(self, expression: str, context: YExpressionContext) -> bool:
        """Evaluate expression as boolean (for predicates).

        Parameters
        ----------
        expression : str
            Expression to evaluate
        context : YExpressionContext
            Evaluation context

        Returns
        -------
        bool
            Boolean result (defaults to True on error)
        """
        result = self.evaluate(expression, context)
        if not result.success:
            return True  # Default true for predicates

        return coerce_to_bool(result.value)

    def evaluate_string(self, expression: str, context: YExpressionContext) -> str:
        """Evaluate expression as string.

        Parameters
        ----------
        expression : str
            Expression to evaluate
        context : YExpressionContext
            Evaluation context

        Returns
        -------
        str
            String result
        """
        result = self.evaluate(expression, context)
        if not result.success:
            return ""

        return str(result.value) if result.value is not None else ""

    def evaluate_number(self, expression: str, context: YExpressionContext) -> float | None:
        """Evaluate expression as number.

        Parameters
        ----------
        expression : str
            Expression to evaluate
        context : YExpressionContext
            Evaluation context

        Returns
        -------
        float | None
            Numeric result or None
        """
        result = self.evaluate(expression, context)
        if not result.success:
            return None

        try:
            return float(result.value)
        except (TypeError, ValueError):
            return None

    def _detect_language(self, expression: str) -> ExpressionLanguage:
        """Detect expression language from syntax.

        Parameters
        ----------
        expression : str
            Expression to analyze

        Returns
        -------
        ExpressionLanguage
            Detected language
        """
        expression = expression.strip()

        # Literals
        if expression.lower() in ("true", "false"):
            return ExpressionLanguage.LITERAL

        # XPath indicators
        if expression.startswith("/"):
            return ExpressionLanguage.XPATH
        if any(op in expression for op in [">=", "<=", "!=", ">", "<", "="]):
            return ExpressionLanguage.XPATH
        if any(func in expression for func in ["count(", "sum(", "not(", "contains(", "starts-with("]):
            return ExpressionLanguage.XPATH

        return ExpressionLanguage.SIMPLE

    def _evaluate_literal(self, expression: str) -> bool:
        """Evaluate literal boolean.

        Parameters
        ----------
        expression : str
            Literal expression

        Returns
        -------
        bool
            Boolean value
        """
        return expression.strip().lower() == "true"

    def _evaluate_simple(self, expression: str, context: YExpressionContext) -> Any:
        """Evaluate simple path expression.

        Parameters
        ----------
        expression : str
            Simple expression (key or dotted path)
        context : YExpressionContext
            Evaluation context

        Returns
        -------
        Any
            Evaluated value
        """
        expression = expression.strip()

        # Direct key lookup
        if expression in context.variables:
            return context.variables[expression]

        # Dotted path navigation
        if "." in expression:
            parts = expression.split(".")
            value: Any = context.variables
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return None
            return value

        # Check net variables
        if expression in context.net_variables:
            return context.net_variables[expression]

        return None

    def _evaluate_xpath(self, expression: str, context: YExpressionContext) -> Any:
        """Evaluate XPath expression against XML representation.

        Parameters
        ----------
        expression : str
            XPath expression
        context : YExpressionContext
            Evaluation context

        Returns
        -------
        Any
            XPath result
        """
        if not self._xpath_available:
            # Fallback: try simple evaluation
            return self._evaluate_simple_xpath_fallback(expression, context)

        import elementpath

        xml_elem = context.to_xml_element()

        # Normalize expression for our XML structure
        normalized = self._normalize_xpath(expression)

        try:
            result = elementpath.select(xml_elem, normalized)
            if isinstance(result, list):
                if len(result) == 0:
                    return None
                if len(result) == 1:
                    return result[0]
                return result
            return result
        except Exception:
            # Try as boolean expression
            try:
                return elementpath.select(xml_elem, normalized) is not None
            except Exception:
                return None

    def _normalize_xpath(self, expression: str) -> str:
        """Normalize XPath expression for our XML structure.

        Parameters
        ----------
        expression : str
            Original expression

        Returns
        -------
        str
            Normalized expression
        """
        expr = expression.strip()

        # If starts with /data, keep as-is
        if expr.startswith("/data"):
            return expr

        # If starts with just /, prepend /data
        if expr.startswith("/"):
            return f"/data{expr}"

        return expr

    def _evaluate_simple_xpath_fallback(self, expression: str, context: YExpressionContext) -> Any:
        """Fallback XPath evaluation without elementpath.

        Handles simple cases like "/data/order/amount > 100".

        Parameters
        ----------
        expression : str
            XPath-like expression
        context : YExpressionContext
            Evaluation context

        Returns
        -------
        Any
            Evaluation result
        """
        expression = expression.strip()

        # Handle comparison expressions
        for op in [">=", "<=", "!=", ">", "<", "="]:
            if op in expression:
                parts = expression.split(op, 1)
                if len(parts) == 2:
                    left = self._resolve_path_value(parts[0].strip(), context)
                    right = self._parse_literal_value(parts[1].strip())

                    return self._compare_values(left, right, op)

        # Simple path lookup
        return self._resolve_path_value(expression, context)

    def _resolve_path_value(self, path: str, context: YExpressionContext) -> Any:
        """Resolve XPath-like path to value.

        Parameters
        ----------
        path : str
            Path like "/data/order/amount"
        context : YExpressionContext
            Evaluation context

        Returns
        -------
        Any
            Resolved value
        """
        # Remove leading /data if present
        path = path.strip()
        if path.startswith("/data/"):
            path = path[6:]
        elif path.startswith("/"):
            path = path[1:]

        # Convert to dotted path
        dotted = path.replace("/", ".")

        # Resolve
        value: Any = context.variables
        for part in dotted.split("."):
            if not part:
                continue
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None
        return value

    def _parse_literal_value(self, literal: str) -> Any:
        """Parse literal value from expression.

        Parameters
        ----------
        literal : str
            Literal string

        Returns
        -------
        Any
            Parsed value
        """
        literal = literal.strip()

        # String literal (quoted)
        if (literal.startswith("'") and literal.endswith("'")) or (literal.startswith('"') and literal.endswith('"')):
            return literal[1:-1]

        # Boolean
        if literal.lower() == "true":
            return True
        if literal.lower() == "false":
            return False

        # Number
        try:
            if "." in literal:
                return float(literal)
            return int(literal)
        except ValueError:
            return literal

    def _compare_values(self, left: Any, right: Any, op: str) -> bool:
        """Compare two values with operator.

        Parameters
        ----------
        left : Any
            Left operand
        right : Any
            Right operand
        op : str
            Comparison operator

        Returns
        -------
        bool
            Comparison result
        """
        try:
            if op == "=":
                return bool(left == right)
            if op == "!=":
                return bool(left != right)
            if op == ">":
                return float(left) > float(right)
            if op == "<":
                return float(left) < float(right)
            if op == ">=":
                return float(left) >= float(right)
            if op == "<=":
                return float(left) <= float(right)
        except (TypeError, ValueError):
            pass
        return False


def coerce_to_bool(value: Any) -> bool:
    """Coerce value to boolean.

    Parameters
    ----------
    value : Any
        Value to coerce

    Returns
    -------
    bool
        Boolean result
    """
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "yes", "1", "y")
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return bool(value)


def coerce_to_python(xpath_result: Any, target_type: type | None = None) -> Any:
    """Coerce XPath result to Python type.

    Parameters
    ----------
    xpath_result : Any
        XPath evaluation result
    target_type : type | None
        Target Python type (bool, int, float, str)

    Returns
    -------
    Any
        Coerced value
    """
    if xpath_result is None:
        return None

    # Handle Element text
    if hasattr(xpath_result, "text"):
        xpath_result = xpath_result.text

    if target_type is None:
        return xpath_result

    if target_type is bool:
        return coerce_to_bool(xpath_result)

    if target_type is int:
        try:
            return int(float(xpath_result))
        except (TypeError, ValueError):
            return 0

    if target_type is float:
        try:
            return float(xpath_result)
        except (TypeError, ValueError):
            return 0.0

    if target_type is str:
        return str(xpath_result) if xpath_result is not None else ""

    return xpath_result
