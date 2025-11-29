"""Data binding evaluation for YAWL task inputs/outputs.

Implements input and output binding evaluation to transfer data
between case data and work item data. Mirrors Java's data binding
mechanisms.

Java Reference: YInputDataParser, YOutputDataParser
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from kgcl.yawl.engine.y_expression import YExpressionContext, YExpressionEvaluator


class BindingType(Enum):
    """Type of data binding."""

    INPUT = auto()
    OUTPUT = auto()


class CoercionMode(Enum):
    """Type coercion behavior."""

    STRICT = auto()  # Raise on type mismatch
    LENIENT = auto()  # Best-effort conversion


@dataclass(frozen=True)
class BindingSpec:
    """Specification for a single data binding.

    Parameters
    ----------
    name : str
        Target variable name
    expression : str
        Source expression to evaluate
    target_type : str | None
        Optional target type for coercion
    required : bool
        Whether binding is required
    default_value : Any
        Default value if expression returns None
    """

    name: str
    expression: str
    target_type: str | None = None
    required: bool = False
    default_value: Any = None


@dataclass(frozen=True)
class BindingResult:
    """Result of evaluating a binding.

    Parameters
    ----------
    name : str
        Variable name
    value : Any
        Evaluated and coerced value
    success : bool
        Whether evaluation succeeded
    error : str | None
        Error message if failed
    """

    name: str
    value: Any
    success: bool
    error: str | None = None


@dataclass
class TypeCoercer:
    """Coerces values to target types.

    Parameters
    ----------
    mode : CoercionMode
        Coercion behavior (strict or lenient)
    """

    mode: CoercionMode = CoercionMode.LENIENT

    def coerce(self, value: Any, target_type: str | None) -> Any:
        """Coerce value to target type.

        Parameters
        ----------
        value : Any
            Value to coerce
        target_type : str | None
            Target type name (string, integer, double, boolean, etc.)

        Returns
        -------
        Any
            Coerced value

        Raises
        ------
        ValueError
            In strict mode, if coercion fails
        """
        if value is None:
            return None

        if target_type is None:
            return value

        target_lower = target_type.lower()

        try:
            if target_lower in ("string", "str", "text"):
                return str(value)
            if target_lower in ("integer", "int", "long"):
                return self._to_int(value)
            if target_lower in ("double", "float", "decimal", "number"):
                return self._to_float(value)
            if target_lower in ("boolean", "bool"):
                return self._to_bool(value)
            if target_lower in ("date", "datetime", "time"):
                return self._to_datetime(value)
            # Unknown type - return as-is
            return value
        except (TypeError, ValueError) as e:
            if self.mode == CoercionMode.STRICT:
                raise ValueError(f"Cannot coerce {type(value).__name__} to {target_type}") from e
            return value

    def _to_int(self, value: Any) -> int:
        """Convert to integer.

        Parameters
        ----------
        value : Any
            Value to convert

        Returns
        -------
        int
            Integer value
        """
        if isinstance(value, bool):
            return 1 if value else 0
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            # Handle decimal strings
            return int(float(value))
        raise TypeError(f"Cannot convert {type(value).__name__} to int")

    def _to_float(self, value: Any) -> float:
        """Convert to float.

        Parameters
        ----------
        value : Any
            Value to convert

        Returns
        -------
        float
            Float value
        """
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            return float(value)
        raise TypeError(f"Cannot convert {type(value).__name__} to float")

    def _to_bool(self, value: Any) -> bool:
        """Convert to boolean.

        Parameters
        ----------
        value : Any
            Value to convert

        Returns
        -------
        bool
            Boolean value
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.lower() in ("true", "yes", "1", "y")
        return bool(value)

    def _to_datetime(self, value: Any) -> Any:
        """Convert to datetime.

        Parameters
        ----------
        value : Any
            Value to convert

        Returns
        -------
        Any
            Datetime value (string if parsing fails)
        """
        from datetime import datetime

        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            # Try common formats
            for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"]:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        return value  # Return as-is if can't parse


@dataclass
class BindingEvaluator:
    """Evaluates data bindings for task inputs and outputs.

    Parameters
    ----------
    expression_evaluator : YExpressionEvaluator
        Expression evaluator for binding expressions
    type_coercer : TypeCoercer
        Type coercer for value conversion
    """

    expression_evaluator: YExpressionEvaluator = field(default_factory=YExpressionEvaluator)
    type_coercer: TypeCoercer = field(default_factory=TypeCoercer)

    def evaluate_input_bindings(
        self, bindings: list[BindingSpec], case_data: dict[str, Any]
    ) -> dict[str, BindingResult]:
        """Evaluate input bindings from case data to work item.

        Parameters
        ----------
        bindings : list[BindingSpec]
            Input binding specifications
        case_data : dict[str, Any]
            Source case data

        Returns
        -------
        dict[str, BindingResult]
            Evaluated binding results by name
        """
        results: dict[str, BindingResult] = {}
        context = YExpressionContext(variables=case_data)

        for binding in bindings:
            result = self._evaluate_single_binding(binding, context)
            results[binding.name] = result

        return results

    def evaluate_output_bindings(
        self, bindings: list[BindingSpec], output_data: dict[str, Any], case_data: dict[str, Any]
    ) -> dict[str, BindingResult]:
        """Evaluate output bindings from work item to case data.

        Parameters
        ----------
        bindings : list[BindingSpec]
            Output binding specifications
        output_data : dict[str, Any]
            Work item output data
        case_data : dict[str, Any]
            Current case data (for expression context)

        Returns
        -------
        dict[str, BindingResult]
            Evaluated binding results by name
        """
        results: dict[str, BindingResult] = {}
        # Output bindings evaluate against output_data
        context = YExpressionContext(
            variables=output_data,
            net_variables=case_data,  # Case data available as fallback
        )

        for binding in bindings:
            result = self._evaluate_single_binding(binding, context)
            results[binding.name] = result

        return results

    def _evaluate_single_binding(self, binding: BindingSpec, context: YExpressionContext) -> BindingResult:
        """Evaluate a single binding specification.

        Parameters
        ----------
        binding : BindingSpec
            Binding specification
        context : YExpressionContext
            Evaluation context

        Returns
        -------
        BindingResult
            Evaluation result
        """
        expr_result = self.expression_evaluator.evaluate(binding.expression, context)

        if not expr_result.success:
            if binding.required:
                return BindingResult(
                    name=binding.name, value=None, success=False, error=f"Required binding failed: {expr_result.error}"
                )
            return BindingResult(name=binding.name, value=binding.default_value, success=True, error=None)

        value = expr_result.value

        # Apply default if None
        if value is None and binding.default_value is not None:
            value = binding.default_value

        # Check required
        if binding.required and value is None:
            return BindingResult(
                name=binding.name, value=None, success=False, error=f"Required binding '{binding.name}' is null"
            )

        # Type coercion
        try:
            value = self.type_coercer.coerce(value, binding.target_type)
        except ValueError as e:
            return BindingResult(name=binding.name, value=None, success=False, error=str(e))

        return BindingResult(name=binding.name, value=value, success=True, error=None)

    def apply_results_to_data(
        self, results: dict[str, BindingResult], target_data: dict[str, Any]
    ) -> tuple[dict[str, Any], list[str]]:
        """Apply successful binding results to target data.

        Parameters
        ----------
        results : dict[str, BindingResult]
            Binding results
        target_data : dict[str, Any]
            Target data dict to update

        Returns
        -------
        tuple[dict[str, Any], list[str]]
            Updated data and list of failed binding names
        """
        updated = target_data.copy()
        failures: list[str] = []

        for name, result in results.items():
            if result.success:
                self._set_nested_value(updated, name, result.value)
            else:
                failures.append(name)

        return updated, failures

    def _set_nested_value(self, data: dict[str, Any], path: str, value: Any) -> None:
        """Set value at potentially nested path.

        Parameters
        ----------
        data : dict[str, Any]
            Target dict
        path : str
            Dotted path (e.g., "customer.address.city")
        value : Any
            Value to set
        """
        parts = path.split(".")
        current = data

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
            if not isinstance(current, dict):
                # Can't navigate further
                return

        current[parts[-1]] = value


@dataclass
class CaseDataManager:
    """Manages case data with schema validation.

    Parameters
    ----------
    schema : dict[str, VariableSchema]
        Variable definitions with types
    data : dict[str, Any]
        Current case data
    binding_evaluator : BindingEvaluator
        Evaluator for bindings
    """

    schema: dict[str, VariableSchema] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)
    binding_evaluator: BindingEvaluator = field(default_factory=BindingEvaluator)

    def initialize(self, initial_data: dict[str, Any] | None = None) -> None:
        """Initialize case data with defaults.

        Parameters
        ----------
        initial_data : dict[str, Any] | None
            Initial values to set
        """
        # Set defaults from schema
        for name, var_schema in self.schema.items():
            if var_schema.default_value is not None:
                self.data[name] = var_schema.default_value
            elif var_schema.initial_value is not None:
                self.data[name] = var_schema.initial_value

        # Override with provided initial data
        if initial_data:
            self.data.update(initial_data)

    def get(self, name: str, default: Any = None) -> Any:
        """Get variable value.

        Parameters
        ----------
        name : str
            Variable name (may be dotted path)
        default : Any
            Default if not found

        Returns
        -------
        Any
            Variable value
        """
        if "." in name:
            parts = name.split(".")
            current: Any = self.data
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return default
            return current
        return self.data.get(name, default)

    def set(self, name: str, value: Any) -> bool:
        """Set variable value with validation.

        Parameters
        ----------
        name : str
            Variable name
        value : Any
            Value to set

        Returns
        -------
        bool
            True if set successfully
        """
        # Validate against schema if present
        if name in self.schema:
            var_schema = self.schema[name]
            if var_schema.data_type:
                coercer = TypeCoercer(mode=CoercionMode.STRICT)
                try:
                    value = coercer.coerce(value, var_schema.data_type)
                except ValueError:
                    return False

        # Set the value
        if "." in name:
            parts = name.split(".")
            current = self.data
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        else:
            self.data[name] = value

        return True

    def validate(self) -> list[str]:
        """Validate all data against schema.

        Returns
        -------
        list[str]
            List of validation errors
        """
        errors: list[str] = []

        for name, var_schema in self.schema.items():
            value = self.get(name)

            # Check required
            if var_schema.mandatory and value is None:
                errors.append(f"Required variable '{name}' is missing")
                continue

            # Check type if present
            if value is not None and var_schema.data_type:
                expected = var_schema.data_type.lower()
                actual_type = type(value).__name__.lower()

                # Simple type checking
                valid = False
                if expected in ("string", "str"):
                    valid = isinstance(value, str)
                elif expected in ("integer", "int", "long"):
                    valid = isinstance(value, int) and not isinstance(value, bool)
                elif expected in ("double", "float"):
                    valid = isinstance(value, (int, float))
                elif expected in ("boolean", "bool"):
                    valid = isinstance(value, bool)
                else:
                    valid = True  # Unknown types pass

                if not valid:
                    errors.append(f"Variable '{name}' type mismatch: expected {expected}, got {actual_type}")

        return errors


@dataclass(frozen=True)
class VariableSchema:
    """Schema definition for a case variable.

    Parameters
    ----------
    name : str
        Variable name
    data_type : str | None
        Expected type (string, integer, double, boolean)
    mandatory : bool
        Whether variable is required
    default_value : Any
        Default value
    initial_value : Any
        Initial value on case start
    """

    name: str
    data_type: str | None = None
    mandatory: bool = False
    default_value: Any = None
    initial_value: Any = None
