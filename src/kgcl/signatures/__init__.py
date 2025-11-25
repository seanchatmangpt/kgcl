"""KGCL DSPy Signatures - Production-ready reasoning modules.

This package provides DSPy signatures and modules for core reasoning tasks:
- Daily briefs from activity metrics
- Weekly retrospectives with trend analysis
- Feature time series analysis
- Multi-feature pattern detection
- Context classification for activities
- Wellbeing and health analysis

All modules support both LLM-powered (DSPy) and fallback (rule-based) modes
with comprehensive observability, error handling, and graceful degradation.
"""

import logging
import os
from typing import Optional

from kgcl.signatures.context_classifier import (
    ContextClassifierInput,
    ContextClassifierModule,
    ContextClassifierOutput,
    ContextLabel,
)

# Import all signature modules
from kgcl.signatures.daily_brief import DailyBriefInput, DailyBriefModule, DailyBriefOutput
from kgcl.signatures.feature_analyzer import (
    FeatureAnalyzerInput,
    FeatureAnalyzerModule,
    FeatureAnalyzerOutput,
)
from kgcl.signatures.pattern_detector import (
    DetectedPattern,
    PatternDetectorInput,
    PatternDetectorModule,
    PatternDetectorOutput,
)
from kgcl.signatures.weekly_retro import WeeklyRetroInput, WeeklyRetroModule, WeeklyRetroOutput
from kgcl.signatures.wellbeing import WellbeingInput, WellbeingModule, WellbeingOutput

# Check DSPy availability
try:
    import dspy

    DSPY_AVAILABLE = True
except ImportError:
    DSPY_AVAILABLE = False

logger = logging.getLogger(__name__)


# Export all public classes
__all__ = [
    # Daily Brief
    "DailyBriefInput",
    "DailyBriefOutput",
    "DailyBriefModule",
    # Weekly Retro
    "WeeklyRetroInput",
    "WeeklyRetroOutput",
    "WeeklyRetroModule",
    # Feature Analyzer
    "FeatureAnalyzerInput",
    "FeatureAnalyzerOutput",
    "FeatureAnalyzerModule",
    # Pattern Detector
    "PatternDetectorInput",
    "PatternDetectorOutput",
    "DetectedPattern",
    "PatternDetectorModule",
    # Context Classifier
    "ContextClassifierInput",
    "ContextClassifierOutput",
    "ContextLabel",
    "ContextClassifierModule",
    # Wellbeing
    "WellbeingInput",
    "WellbeingOutput",
    "WellbeingModule",
    # Utilities
    "SignatureConfig",
    "configure_signatures",
    "create_all_modules",
    "health_check",
    "DSPY_AVAILABLE",
]


class SignatureConfig:
    """Configuration for signature modules.

    Attributes
    ----------
        use_llm: Enable LLM-powered reasoning (requires DSPy and Ollama)
        temperature: LLM temperature for generation (0.0-1.0)
        model: Ollama model name (default: llama3.1)
        base_url: Ollama base URL (default: http://localhost:11434)
        fallback_on_error: Automatically fallback to rule-based on LLM errors
        enable_telemetry: Enable OpenTelemetry tracing
    """

    def __init__(
        self,
        use_llm: bool = True,
        temperature: float = 0.7,
        model: str = "llama3.1",
        base_url: str = "http://localhost:11434",
        fallback_on_error: bool = True,
        enable_telemetry: bool = True,
    ):
        """Initialize signature configuration.

        Args:
            use_llm: Enable LLM-powered reasoning
            temperature: LLM temperature (0.0-1.0)
            model: Ollama model name
            base_url: Ollama base URL
            fallback_on_error: Auto-fallback on errors
            enable_telemetry: Enable OpenTelemetry
        """
        self.use_llm = use_llm and DSPY_AVAILABLE
        self.temperature = temperature
        self.model = model
        self.base_url = base_url
        self.fallback_on_error = fallback_on_error
        self.enable_telemetry = enable_telemetry

        if use_llm and not DSPY_AVAILABLE:
            logger.warning("DSPy not available. Install with: pip install dspy-ai")
            logger.warning("Falling back to rule-based mode for all signatures")

    @classmethod
    def from_env(cls) -> "SignatureConfig":
        """Load configuration from environment variables.

        Environment variables:
            KGCL_USE_LLM: Enable LLM mode (default: true)
            KGCL_TEMPERATURE: LLM temperature (default: 0.7)
            OLLAMA_MODEL: Ollama model name (default: llama3.1)
            OLLAMA_BASE_URL: Ollama base URL (default: http://localhost:11434)
            KGCL_FALLBACK_ON_ERROR: Auto-fallback (default: true)
            KGCL_ENABLE_TELEMETRY: Enable telemetry (default: true)

        Returns
        -------
            SignatureConfig loaded from environment
        """
        return cls(
            use_llm=os.getenv("KGCL_USE_LLM", "true").lower() == "true",
            temperature=float(os.getenv("KGCL_TEMPERATURE", "0.7")),
            model=os.getenv("OLLAMA_MODEL", "llama3.1"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            fallback_on_error=os.getenv("KGCL_FALLBACK_ON_ERROR", "true").lower() == "true",
            enable_telemetry=os.getenv("KGCL_ENABLE_TELEMETRY", "true").lower() == "true",
        )

    def to_dict(self) -> dict:
        """Convert configuration to dictionary.

        Returns
        -------
            Dictionary representation of config
        """
        return {
            "use_llm": self.use_llm,
            "temperature": self.temperature,
            "model": self.model,
            "base_url": self.base_url,
            "fallback_on_error": self.fallback_on_error,
            "enable_telemetry": self.enable_telemetry,
            "dspy_available": DSPY_AVAILABLE,
        }


def configure_signatures(config: SignatureConfig | None = None) -> SignatureConfig:
    """Configure signature modules globally.

    Args:
        config: Signature configuration. If None, loads from environment.

    Returns
    -------
        Active configuration

    Example:
        >>> from kgcl.signatures import configure_signatures, SignatureConfig
        >>> config = SignatureConfig(use_llm=True, temperature=0.7)
        >>> configure_signatures(config)
    """
    if config is None:
        config = SignatureConfig.from_env()

    if config.use_llm and DSPY_AVAILABLE:
        try:
            # Configure DSPy with Ollama
            from kgcl.dspy_runtime import OllamaConfig, configure_ollama

            ollama_config = OllamaConfig(
                model=config.model, base_url=config.base_url, temperature=config.temperature
            )

            configure_ollama(ollama_config)
            logger.info(f"DSPy configured with Ollama: {config.model}")
        except Exception as e:
            logger.warning(f"Failed to configure DSPy: {e}")
            if config.fallback_on_error:
                logger.info("Falling back to rule-based mode")
                config.use_llm = False

    return config


def create_all_modules(config: SignatureConfig | None = None) -> dict[str, object]:
    """Create all signature modules with configuration.

    Args:
        config: Signature configuration. If None, loads from environment.

    Returns
    -------
        Dictionary mapping module names to instances

    Example:
        >>> from kgcl.signatures import create_all_modules
        >>> modules = create_all_modules()
        >>> daily_brief = modules["daily_brief"]
        >>> output = daily_brief.generate(input_data)
    """
    if config is None:
        config = configure_signatures()

    modules = {
        "daily_brief": DailyBriefModule(use_llm=config.use_llm, temperature=config.temperature),
        "weekly_retro": WeeklyRetroModule(use_llm=config.use_llm, temperature=config.temperature),
        "feature_analyzer": FeatureAnalyzerModule(
            use_llm=config.use_llm, temperature=config.temperature
        ),
        "pattern_detector": PatternDetectorModule(
            use_llm=config.use_llm, temperature=config.temperature
        ),
        "context_classifier": ContextClassifierModule(
            use_llm=config.use_llm,
            temperature=0.3,  # Lower temperature for consistent classification
        ),
        "wellbeing": WellbeingModule(use_llm=config.use_llm, temperature=config.temperature),
    }

    logger.info(f"Created {len(modules)} signature modules (LLM mode: {config.use_llm})")
    return modules


def health_check() -> dict[str, object]:
    """Perform health check on signature modules.

    Returns
    -------
        Health check results with status and module availability

    Example:
        >>> from kgcl.signatures import health_check
        >>> status = health_check()
        >>> print(status["status"])
        'healthy'
    """
    result = {
        "status": "unknown",
        "dspy_available": DSPY_AVAILABLE,
        "modules_available": [
            "daily_brief",
            "weekly_retro",
            "feature_analyzer",
            "pattern_detector",
            "context_classifier",
            "wellbeing",
        ],
        "fallback_mode": "always_available",
    }

    try:
        # Check if we can create modules
        config = SignatureConfig(use_llm=False)  # Always test fallback mode
        modules = create_all_modules(config)

        # Verify all modules created successfully
        if len(modules) == 6:
            result["status"] = "healthy"
            result["message"] = "All signature modules available"
        else:
            result["status"] = "degraded"
            result["message"] = f"Only {len(modules)}/6 modules available"

        # If DSPy available, check Ollama connection
        if DSPY_AVAILABLE:
            try:
                from kgcl.dspy_runtime import health_check as dspy_health_check

                dspy_status = dspy_health_check()
                result["ollama_status"] = dspy_status
                if dspy_status.get("status") == "healthy":
                    result["llm_mode"] = "available"
                else:
                    result["llm_mode"] = "unavailable"
                    result["message"] += " (LLM mode unavailable, using fallback)"
            except Exception as e:
                result["llm_mode"] = "error"
                result["llm_error"] = str(e)
        else:
            result["llm_mode"] = "not_installed"
            result["message"] += " (DSPy not installed)"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        logger.error(f"Health check failed: {e}", exc_info=True)

    return result


# Utility functions for prompt construction
def build_prompt_context(
    feature_names: list[str], time_window: str, additional_context: str = ""
) -> str:
    """Build context string for DSPy prompts.

    Args:
        feature_names: List of feature names
        time_window: Time window (hourly, daily, weekly)
        additional_context: Additional context to include

    Returns
    -------
        Formatted context string
    """
    context_parts = [f"Time window: {time_window}", f"Features: {', '.join(feature_names)}"]

    if additional_context:
        context_parts.append(additional_context)

    return " | ".join(context_parts)


def validate_module_inputs(module_name: str, input_data: object) -> tuple[bool, str | None]:
    """Validate inputs for a signature module.

    Args:
        module_name: Name of the module
        input_data: Input data to validate

    Returns
    -------
        Tuple of (is_valid, error_message)
    """
    try:
        # Map module names to input types
        input_types = {
            "daily_brief": DailyBriefInput,
            "weekly_retro": WeeklyRetroInput,
            "feature_analyzer": FeatureAnalyzerInput,
            "pattern_detector": PatternDetectorInput,
            "context_classifier": ContextClassifierInput,
            "wellbeing": WellbeingInput,
        }

        if module_name not in input_types:
            return False, f"Unknown module: {module_name}"

        expected_type = input_types[module_name]
        if not isinstance(input_data, expected_type):
            return False, f"Expected {expected_type.__name__}, got {type(input_data).__name__}"

        # Pydantic validation happens automatically on instantiation
        return True, None

    except Exception as e:
        return False, str(e)


# Version information
__version__ = "1.0.0"
__author__ = "KGCL Team"
__description__ = "Production-ready DSPy signatures for reasoning tasks"


# Module initialization logging
logger.info(f"KGCL Signatures v{__version__} initialized")
logger.info(f"DSPy available: {DSPY_AVAILABLE}")
logger.info(f"Modules: {', '.join(__all__[:6])}")  # Log main module names
