# Gap 11: Expression Evaluation (XPath/XQuery)

## Problem Statement

YAWL uses XPath 2.0 and XQuery 1.0 for:
- Flow predicates (routing decisions)
- Data bindings (input/output mapping)
- MI queries (instance count determination)
- Variable expressions

Current implementation only handles literal `"true"`/`"false"` and simple key lookup.

## Current State

```python
# src/kgcl/yawl/engine/y_net_runner.py:477-504
def _evaluate_predicate(
    self, predicate: str, data: dict[str, Any] | None
) -> bool:
    if predicate == "true":
        return True
    if predicate == "false":
        return False
    if data and predicate in data:
        return bool(data[predicate])
    return True  # Default true
```

**Limitations**:
- No XPath syntax
- No comparisons (`> < = !=`)
- No boolean operators (`and or not`)
- No path navigation (`/order/total`)
- No functions (`count(), string()`)

## YAWL Expression Requirements

### Flow Predicates
```xpath
/order/total > 1000
/order/priority = 'high' and /order/express = true()
count(/order/items/item) > 0
not(empty(/customer/address))
```

### Data Bindings
```xpath
<!-- Input binding -->
/order/customer_id

<!-- Output binding with transformation -->
concat(/result/status, '-', /result/code)
```

### MI Queries
```xpath
<!-- Count items -->
/order/line_items/item

<!-- Unique identifier per instance -->
./item_id
```

## Implementation Options

### Option 1: elementpath (Recommended)

Pure Python XPath 2.0 implementation.

```bash
uv add elementpath
```

```python
from elementpath import select, XPath2Parser

# Parse and evaluate XPath
result = select(xml_element, "/order/total > 1000")
```

**Pros**: Pure Python, XPath 2.0 compliant, well-maintained
**Cons**: Requires XML input, not dict-native

### Option 2: lxml.etree

Built-in XPath 1.0 support.

```python
from lxml import etree

tree = etree.fromstring(xml_string)
result = tree.xpath("/order/total > 1000")
```

**Pros**: Fast, widely used
**Cons**: XPath 1.0 only, requires XML

### Option 3: Custom Expression Parser

Build minimal expression evaluator for common patterns.

```python
# Support basic patterns without full XPath
"/order/total > 1000"  → data["order"]["total"] > 1000
"approved = true()"    → data["approved"] == True
```

**Pros**: No dependencies, dict-native
**Cons**: Limited, not standards-compliant

### Recommended: Hybrid Approach

1. Use `elementpath` for full XPath 2.0
2. Provide dict-to-XML conversion layer
3. Cache parsed expressions

## Implementation Plan

### New Module: `src/kgcl/yawl/expression/`

```
src/kgcl/yawl/expression/
├── __init__.py
├── y_expression.py      # Main evaluator interface
├── y_xpath.py           # XPath implementation
└── y_data_converter.py  # Dict <-> XML conversion
```

### Core Interface

```python
# src/kgcl/yawl/expression/y_expression.py
"""Expression evaluation for YAWL workflows."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from lxml import etree


class YExpressionEvaluator(ABC):
    """Abstract expression evaluator."""

    @abstractmethod
    def evaluate(self, expression: str, context: Any) -> Any:
        """Evaluate expression against context.

        Parameters
        ----------
        expression : str
            Expression to evaluate
        context : Any
            Evaluation context (dict, XML, etc.)

        Returns
        -------
        Any
            Evaluation result
        """
        pass

    @abstractmethod
    def evaluate_boolean(self, expression: str, context: Any) -> bool:
        """Evaluate expression as boolean.

        Parameters
        ----------
        expression : str
            Boolean expression
        context : Any
            Evaluation context

        Returns
        -------
        bool
            Boolean result
        """
        pass


@dataclass
class YXPathEvaluator(YExpressionEvaluator):
    """XPath 2.0 expression evaluator.

    Uses elementpath for XPath 2.0 compliance.

    Parameters
    ----------
    cache_enabled : bool
        Cache parsed expressions
    namespaces : dict[str, str]
        XML namespace mappings
    """

    cache_enabled: bool = True
    namespaces: dict[str, str] = field(default_factory=dict)
    _cache: dict[str, Any] = field(default_factory=dict, repr=False)

    def evaluate(self, expression: str, context: Any) -> Any:
        """Evaluate XPath expression.

        Parameters
        ----------
        expression : str
            XPath expression
        context : Any
            Context (dict or XML element)

        Returns
        -------
        Any
            Evaluation result
        """
        # Convert dict to XML if needed
        if isinstance(context, dict):
            xml_context = self._dict_to_xml(context)
        elif isinstance(context, (str, bytes)):
            xml_context = etree.fromstring(context)
        else:
            xml_context = context

        # Use elementpath for XPath 2.0
        try:
            from elementpath import select
            result = select(xml_context, expression, namespaces=self.namespaces)
            return self._normalize_result(result)
        except ImportError:
            # Fallback to lxml XPath 1.0
            return xml_context.xpath(expression, namespaces=self.namespaces)

    def evaluate_boolean(self, expression: str, context: Any) -> bool:
        """Evaluate as boolean."""
        result = self.evaluate(expression, context)
        return self._to_boolean(result)

    def _dict_to_xml(self, data: dict[str, Any], root_name: str = "root") -> etree._Element:
        """Convert dict to XML element.

        Parameters
        ----------
        data : dict[str, Any]
            Data dictionary
        root_name : str
            Root element name

        Returns
        -------
        etree._Element
            XML element
        """
        root = etree.Element(root_name)
        self._dict_to_xml_recursive(data, root)
        return root

    def _dict_to_xml_recursive(
        self,
        data: Any,
        parent: etree._Element,
    ) -> None:
        """Recursively convert dict to XML."""
        if isinstance(data, dict):
            for key, value in data.items():
                child = etree.SubElement(parent, str(key))
                self._dict_to_xml_recursive(value, child)
        elif isinstance(data, list):
            for item in data:
                # Use parent tag name for list items
                item_elem = etree.SubElement(parent.getparent() or parent, parent.tag)
                parent.getparent().remove(parent) if parent.getparent() is not None else None
                self._dict_to_xml_recursive(item, item_elem)
        else:
            parent.text = str(data) if data is not None else ""

    def _normalize_result(self, result: Any) -> Any:
        """Normalize XPath result to Python types."""
        if isinstance(result, list):
            if len(result) == 0:
                return None
            elif len(result) == 1:
                return self._normalize_result(result[0])
            else:
                return [self._normalize_result(r) for r in result]
        elif hasattr(result, 'text'):
            # XML element - return text content
            return result.text
        else:
            return result

    def _to_boolean(self, value: Any) -> bool:
        """Convert value to boolean using XPath rules."""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return len(value) > 0
        if isinstance(value, list):
            return len(value) > 0
        return bool(value)
```

### Simple Expression Fallback

For environments without elementpath:

```python
# src/kgcl/yawl/expression/y_simple_expr.py
"""Simple expression evaluator for basic patterns."""

import re
from typing import Any


class YSimpleEvaluator:
    """Simple expression evaluator without XPath dependency.

    Supports:
    - Literals: true, false, numbers, strings
    - Path access: /root/child/value
    - Comparisons: =, !=, <, >, <=, >=
    - Boolean: and, or, not()
    """

    def evaluate(self, expression: str, context: dict[str, Any]) -> Any:
        """Evaluate simple expression."""
        expression = expression.strip()

        # Literals
        if expression == "true" or expression == "true()":
            return True
        if expression == "false" or expression == "false()":
            return False

        # Try numeric
        try:
            return float(expression) if '.' in expression else int(expression)
        except ValueError:
            pass

        # String literal
        if expression.startswith(("'", '"')):
            return expression[1:-1]

        # Path access
        if expression.startswith("/"):
            return self._evaluate_path(expression, context)

        # Comparison
        for op in ["!=", "<=", ">=", "=", "<", ">"]:
            if op in expression:
                return self._evaluate_comparison(expression, op, context)

        # Boolean operators
        if " and " in expression:
            parts = expression.split(" and ")
            return all(self.evaluate(p.strip(), context) for p in parts)
        if " or " in expression:
            parts = expression.split(" or ")
            return any(self.evaluate(p.strip(), context) for p in parts)
        if expression.startswith("not("):
            inner = expression[4:-1]
            return not self.evaluate(inner, context)

        # Simple key lookup
        return context.get(expression)

    def _evaluate_path(self, path: str, context: dict[str, Any]) -> Any:
        """Evaluate path like /order/total."""
        parts = path.strip("/").split("/")
        current = context
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            if current is None:
                return None
        return current

    def _evaluate_comparison(
        self,
        expression: str,
        operator: str,
        context: dict[str, Any],
    ) -> bool:
        """Evaluate comparison expression."""
        left, right = expression.split(operator, 1)
        left_val = self.evaluate(left.strip(), context)
        right_val = self.evaluate(right.strip(), context)

        # Type coercion
        if isinstance(left_val, str) and isinstance(right_val, (int, float)):
            try:
                left_val = float(left_val)
            except ValueError:
                pass
        if isinstance(right_val, str) and isinstance(left_val, (int, float)):
            try:
                right_val = float(right_val)
            except ValueError:
                pass

        ops = {
            "=": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
            "<": lambda a, b: a < b,
            ">": lambda a, b: a > b,
            "<=": lambda a, b: a <= b,
            ">=": lambda a, b: a >= b,
        }
        return ops[operator](left_val, right_val)

    def evaluate_boolean(self, expression: str, context: dict[str, Any]) -> bool:
        """Evaluate as boolean."""
        result = self.evaluate(expression, context)
        if isinstance(result, bool):
            return result
        if result is None:
            return False
        if isinstance(result, (list, str)):
            return len(result) > 0
        return bool(result)
```

### Integration with YNetRunner

```python
# src/kgcl/yawl/engine/y_net_runner.py

from kgcl.yawl.expression import YExpressionEvaluator, YSimpleEvaluator

@dataclass
class YNetRunner:
    # ... existing fields ...
    expression_evaluator: YExpressionEvaluator = field(
        default_factory=YSimpleEvaluator
    )

    def _evaluate_predicate(
        self, predicate: str, data: dict[str, Any] | None
    ) -> bool:
        """Evaluate predicate using expression evaluator."""
        if data is None:
            data = {}

        return self.expression_evaluator.evaluate_boolean(predicate, data)
```

## Test Cases

```python
class TestExpressionEvaluator:
    """Tests for expression evaluation."""

    def test_literal_true(self) -> None:
        assert evaluator.evaluate("true", {}) is True
        assert evaluator.evaluate("true()", {}) is True

    def test_literal_false(self) -> None:
        assert evaluator.evaluate("false", {}) is False

    def test_path_access(self) -> None:
        data = {"order": {"total": 100}}
        assert evaluator.evaluate("/order/total", data) == 100

    def test_comparison_greater(self) -> None:
        data = {"order": {"total": 150}}
        assert evaluator.evaluate_boolean("/order/total > 100", data) is True

    def test_comparison_equal_string(self) -> None:
        data = {"status": "approved"}
        assert evaluator.evaluate_boolean("/status = 'approved'", data) is True

    def test_boolean_and(self) -> None:
        data = {"a": True, "b": True}
        assert evaluator.evaluate_boolean("/a and /b", data) is True

    def test_boolean_or(self) -> None:
        data = {"a": False, "b": True}
        assert evaluator.evaluate_boolean("/a or /b", data) is True

    def test_not(self) -> None:
        data = {"approved": False}
        assert evaluator.evaluate_boolean("not(/approved)", data) is True

    def test_nested_path(self) -> None:
        data = {"order": {"customer": {"name": "Alice"}}}
        assert evaluator.evaluate("/order/customer/name", data) == "Alice"
```

## Dependencies

- **Optional**: `elementpath` for full XPath 2.0
- **Fallback**: Custom simple evaluator

## Complexity: HIGH

- Full XPath 2.0 spec is large
- Must handle type coercion
- Performance considerations for complex expressions

## Estimated Effort

- Simple evaluator: 4-6 hours
- XPath integration: 4-6 hours
- Testing: 4-6 hours
- Total: 2-3 days

## Priority: HIGH

Blocks Gap 1 (OR-join), Gap 2 (MI), and Gap 9 (Data binding).
