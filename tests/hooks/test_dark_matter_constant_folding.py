"""Test constant folding implementation in dark_matter.py."""

from kgcl.hooks.dark_matter import DarkMatterOptimizer


def test_constant_folding_arithmetic() -> None:
    """Constant folding evaluates arithmetic expressions."""
    optimizer = DarkMatterOptimizer()
    steps = [
        {"step_id": 1, "operation": "filter", "expression": "2 + 3", "cost": 1.0},
        {"step_id": 2, "operation": "filter", "expression": "10 * 5", "cost": 1.0},
    ]

    result = optimizer._apply_constant_folding(steps)

    assert result["applied"] is True
    assert result["steps"][0]["expression"] == "5"
    assert result["steps"][1]["expression"] == "50"


def test_constant_folding_comparison() -> None:
    """Constant folding evaluates comparison expressions."""
    optimizer = DarkMatterOptimizer()
    steps = [
        {"step_id": 1, "operation": "filter", "expression": "5 > 3", "cost": 1.0},
        {"step_id": 2, "operation": "filter", "expression": "10 == 10", "cost": 1.0},
    ]

    result = optimizer._apply_constant_folding(steps)

    assert result["applied"] is True
    assert result["steps"][0]["expression"] == "True"
    assert result["steps"][1]["expression"] == "True"


def test_constant_folding_no_change_for_variables() -> None:
    """Constant folding skips expressions with variables."""
    optimizer = DarkMatterOptimizer()
    steps = [
        {"step_id": 1, "operation": "filter", "expression": "x + 3", "cost": 1.0},
        {"step_id": 2, "operation": "filter", "expression": "foo()", "cost": 1.0},
    ]

    result = optimizer._apply_constant_folding(steps)

    assert result["applied"] is False
    assert result["steps"][0]["expression"] == "x + 3"
    assert result["steps"][1]["expression"] == "foo()"


def test_constant_folding_complex_expression() -> None:
    """Constant folding handles complex nested expressions."""
    optimizer = DarkMatterOptimizer()
    steps = [
        {"step_id": 1, "operation": "filter", "expression": "(2 + 3) * 4", "cost": 1.0},
        {"step_id": 2, "operation": "filter", "expression": "10 - 2 * 3", "cost": 1.0},
    ]

    result = optimizer._apply_constant_folding(steps)

    assert result["applied"] is True
    assert result["steps"][0]["expression"] == "20"
    assert result["steps"][1]["expression"] == "4"


def test_constant_folding_unary_operators() -> None:
    """Constant folding handles unary operators."""
    optimizer = DarkMatterOptimizer()
    steps = [
        {"step_id": 1, "operation": "filter", "expression": "-(2 + 3)", "cost": 1.0},
        {"step_id": 2, "operation": "filter", "expression": "+(5 * 2)", "cost": 1.0},
    ]

    result = optimizer._apply_constant_folding(steps)

    assert result["applied"] is True
    assert result["steps"][0]["expression"] == "-5"
    assert result["steps"][1]["expression"] == "10"


def test_constant_folding_no_expression_field() -> None:
    """Constant folding skips steps without expression field."""
    optimizer = DarkMatterOptimizer()
    steps = [
        {"step_id": 1, "operation": "scan", "cost": 1.0},
        {"step_id": 2, "operation": "join", "cost": 10.0},
    ]

    result = optimizer._apply_constant_folding(steps)

    assert result["applied"] is False
    assert len(result["steps"]) == 2


def test_constant_folding_invalid_syntax() -> None:
    """Constant folding handles invalid syntax gracefully."""
    optimizer = DarkMatterOptimizer()
    steps = [
        {"step_id": 1, "operation": "filter", "expression": "2 +", "cost": 1.0},
        {"step_id": 2, "operation": "filter", "expression": "(()", "cost": 1.0},
    ]

    result = optimizer._apply_constant_folding(steps)

    # Invalid expressions should not be folded
    assert result["applied"] is False
    assert result["steps"][0]["expression"] == "2 +"
    assert result["steps"][1]["expression"] == "(()"


def test_constant_folding_division() -> None:
    """Constant folding handles division operations."""
    optimizer = DarkMatterOptimizer()
    steps = [
        {"step_id": 1, "operation": "filter", "expression": "10 / 2", "cost": 1.0},
        {"step_id": 2, "operation": "filter", "expression": "15 // 4", "cost": 1.0},
    ]

    result = optimizer._apply_constant_folding(steps)

    assert result["applied"] is True
    assert result["steps"][0]["expression"] == "5.0"
    assert result["steps"][1]["expression"] == "3"


def test_constant_folding_preserves_non_expression_fields() -> None:
    """Constant folding preserves all other step fields."""
    optimizer = DarkMatterOptimizer()
    steps = [
        {
            "step_id": 1,
            "operation": "filter",
            "expression": "2 + 3",
            "cost": 1.0,
            "dependencies": [0],
            "metadata": {"source": "test"},
        }
    ]

    result = optimizer._apply_constant_folding(steps)

    assert result["applied"] is True
    assert result["steps"][0]["expression"] == "5"
    assert result["steps"][0]["step_id"] == 1
    assert result["steps"][0]["operation"] == "filter"
    assert result["steps"][0]["cost"] == 1.0
    assert result["steps"][0]["dependencies"] == [0]
    assert result["steps"][0]["metadata"] == {"source": "test"}
