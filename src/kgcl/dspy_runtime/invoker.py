"""
DSPy signature invoker.

Dynamically loads generated DSPy signatures and executes predictions with
comprehensive error handling and metrics collection.
"""

import importlib
import importlib.util
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

try:
    import dspy

    DSPY_AVAILABLE = True
except ImportError:
    DSPY_AVAILABLE = False
    if TYPE_CHECKING:
        import dspy

from opentelemetry import metrics, trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Metrics
prediction_counter = meter.create_counter(
    "dspy.predictions.total", description="Total number of predictions made", unit="1"
)
prediction_latency = meter.create_histogram(
    "dspy.predictions.latency", description="Prediction latency in seconds", unit="s"
)
prediction_errors = meter.create_counter(
    "dspy.predictions.errors", description="Total number of prediction errors", unit="1"
)


@dataclass
class InvocationResult:
    """Result of a signature invocation."""

    success: bool
    inputs: dict[str, Any]
    outputs: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "error": self.error,
            "metrics": self.metrics,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class SignatureInvoker:
    """Invokes DSPy signatures with inputs and returns predictions."""

    def __init__(self, lm=None):
        """
        Initialize signature invoker.

        Args:
            lm: DSPy language model. If None, uses configured LM.
        """
        if not DSPY_AVAILABLE:
            raise RuntimeError(
                "DSPy is not installed. Install with: pip install dspy-ai"
            )

        self._lm = lm
        self._signature_cache: dict[str, type[dspy.Signature]] = {}

    def load_signature(
        self, module_path: str, signature_name: str
    ) -> type["dspy.Signature"]:
        """
        Load DSPy signature from Python module.

        Args:
            module_path: Path to Python module file
            signature_name: Name of signature class

        Returns
        -------
            DSPy signature class

        Raises
        ------
            FileNotFoundError: If module file not found
            ImportError: If module cannot be imported
            AttributeError: If signature not found in module
        """
        cache_key = f"{module_path}:{signature_name}"

        # Check cache
        if cache_key in self._signature_cache:
            logger.debug(f"Using cached signature: {cache_key}")
            return self._signature_cache[cache_key]

        # Load module
        module_file = Path(module_path)
        if not module_file.exists():
            raise FileNotFoundError(f"Module not found: {module_path}")

        try:
            spec = importlib.util.spec_from_file_location(
                f"dynamic_signature_{id(self)}", module_file
            )
            if spec is None or spec.loader is None:
                raise ImportError(f"Failed to load module spec: {module_path}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Get signature class
            if not hasattr(module, signature_name):
                raise AttributeError(
                    f"Signature '{signature_name}' not found in module {module_path}"
                )

            signature_class = getattr(module, signature_name)

            # Validate it's a DSPy signature
            if not issubclass(signature_class, dspy.Signature):
                raise TypeError(f"{signature_name} is not a DSPy Signature subclass")

            # Cache and return
            self._signature_cache[cache_key] = signature_class
            logger.info(f"Loaded signature: {signature_name} from {module_path}")
            return signature_class

        except Exception as e:
            logger.error(f"Failed to load signature: {e}")
            raise

    def invoke(
        self, signature: type["dspy.Signature"], inputs: dict[str, Any], **kwargs
    ) -> InvocationResult:
        """
        Invoke DSPy signature with inputs.

        Args:
            signature: DSPy signature class
            inputs: Input field values
            **kwargs: Additional arguments for Predict

        Returns
        -------
            InvocationResult with outputs and metrics
        """
        start_time = time.time()

        with tracer.start_as_current_span("dspy.predict") as span:
            span.set_attribute("signature", signature.__name__)
            span.set_attribute("input_count", len(inputs))

            try:
                # Create predictor
                predictor = dspy.Predict(signature, **kwargs)

                # Execute prediction
                logger.info(
                    f"Invoking {signature.__name__} with inputs: {list(inputs.keys())}"
                )
                prediction = predictor(**inputs)

                # Extract outputs
                outputs = {}
                for field_name in signature.output_fields:
                    if hasattr(prediction, field_name):
                        outputs[field_name] = getattr(prediction, field_name)

                # Calculate metrics
                latency = time.time() - start_time
                metrics_data = {
                    "latency_seconds": latency,
                    "signature": signature.__name__,
                    "timestamp": time.time(),
                }

                # Record metrics
                prediction_counter.add(
                    1, {"signature": signature.__name__, "status": "success"}
                )
                prediction_latency.record(latency, {"signature": signature.__name__})

                span.set_attribute("success", True)
                span.set_attribute("output_count", len(outputs))
                span.set_attribute("latency_seconds", latency)

                logger.info(
                    f"Successfully invoked {signature.__name__} "
                    f"in {latency:.3f}s with {len(outputs)} outputs"
                )

                return InvocationResult(
                    success=True, inputs=inputs, outputs=outputs, metrics=metrics_data
                )

            except Exception as e:
                latency = time.time() - start_time
                error_msg = str(e)

                # Record error metrics
                prediction_counter.add(
                    1, {"signature": signature.__name__, "status": "error"}
                )
                prediction_errors.add(
                    1, {"signature": signature.__name__, "error_type": type(e).__name__}
                )

                span.set_attribute("success", False)
                span.set_attribute("error", error_msg)
                span.set_attribute("error_type", type(e).__name__)

                logger.error(
                    f"Prediction failed for {signature.__name__}: {e}", exc_info=True
                )

                return InvocationResult(
                    success=False,
                    inputs=inputs,
                    error=error_msg,
                    metrics={
                        "latency_seconds": latency,
                        "signature": signature.__name__,
                        "error_type": type(e).__name__,
                        "timestamp": time.time(),
                    },
                )

    def invoke_from_module(
        self, module_path: str, signature_name: str, inputs: dict[str, Any], **kwargs
    ) -> InvocationResult:
        """
        Load signature from module and invoke with inputs.

        Args:
            module_path: Path to Python module file
            signature_name: Name of signature class
            inputs: Input field values
            **kwargs: Additional arguments for Predict

        Returns
        -------
            InvocationResult with outputs and metrics
        """
        with tracer.start_as_current_span("dspy.invoke_from_module") as span:
            span.set_attribute("module_path", module_path)
            span.set_attribute("signature_name", signature_name)

            try:
                signature = self.load_signature(module_path, signature_name)
                return self.invoke(signature, inputs, **kwargs)
            except Exception as e:
                logger.error(f"Failed to invoke from module: {e}", exc_info=True)
                return InvocationResult(
                    success=False,
                    inputs=inputs,
                    error=str(e),
                    metrics={"error_type": type(e).__name__, "timestamp": time.time()},
                )

    def validate_inputs(
        self, signature: type["dspy.Signature"], inputs: dict[str, Any]
    ) -> tuple[bool, str | None]:
        """
        Validate inputs against signature fields.

        Args:
            signature: DSPy signature class
            inputs: Input field values

        Returns
        -------
            Tuple of (is_valid, error_message)
        """
        required_fields = set(signature.input_fields.keys())
        provided_fields = set(inputs.keys())

        missing = required_fields - provided_fields
        if missing:
            return False, f"Missing required input fields: {missing}"

        extra = provided_fields - required_fields
        if extra:
            logger.warning(f"Extra input fields will be ignored: {extra}")

        return True, None
