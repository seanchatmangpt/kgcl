"""
Ollama LM configuration for DSPy.

Provides DSPy language model setup with Ollama backend, environment-based
configuration, and fallback handling.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any

import requests

try:
    import dspy

    DSPY_AVAILABLE = True
except ImportError:
    DSPY_AVAILABLE = False
    logging.warning("DSPy not available. Install with: pip install dspy-ai")

logger = logging.getLogger(__name__)


@dataclass
class OllamaConfig:
    """Configuration for Ollama LM."""

    model: str = "llama3.1"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 30

    @classmethod
    def from_env(cls) -> "OllamaConfig":
        """Load configuration from environment variables."""
        return cls(
            model=os.getenv("OLLAMA_MODEL", cls.model),
            base_url=os.getenv("OLLAMA_BASE_URL", cls.base_url),
            temperature=float(os.getenv("OLLAMA_TEMPERATURE", str(cls.temperature))),
            max_tokens=int(os.getenv("OLLAMA_MAX_TOKENS", str(cls.max_tokens))),
            timeout=int(os.getenv("OLLAMA_TIMEOUT", str(cls.timeout))),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model": self.model,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
        }


class OllamaLM:
    """Ollama language model wrapper for DSPy."""

    def __init__(self, config: OllamaConfig | None = None):
        """
        Initialize Ollama LM.

        Args:
            config: Ollama configuration. If None, loads from environment.

        Raises
        ------
            RuntimeError: If DSPy is not available
            ConnectionError: If Ollama is not accessible
        """
        if not DSPY_AVAILABLE:
            raise RuntimeError("DSPy is not installed. Install with: pip install dspy-ai")

        self.config = config or OllamaConfig.from_env()
        self._lm = None
        self._initialized = False

        logger.info(f"Initializing Ollama LM with config: {self.config.to_dict()}")

    def initialize(self) -> None:
        """
        Initialize DSPy LM connection.

        Raises
        ------
            ConnectionError: If Ollama is not accessible
        """
        if self._initialized:
            return

        # Check Ollama availability
        if not self.is_available():
            raise ConnectionError(
                f"Ollama is not accessible at {self.config.base_url}. "
                "Please start Ollama: ollama serve"
            )

        # Check model availability
        if not self.is_model_available():
            logger.warning(
                f"Model {self.config.model} not found. "
                f"Pull it with: ollama pull {self.config.model}"
            )

        # Configure DSPy LM
        try:
            self._lm = dspy.OllamaLocal(
                model=self.config.model,
                base_url=self.config.base_url,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout,
            )
            dspy.settings.configure(lm=self._lm)
            self._initialized = True
            logger.info(f"Successfully initialized Ollama LM: {self.config.model}")
        except Exception as e:
            logger.error(f"Failed to initialize Ollama LM: {e}")
            raise

    def is_available(self) -> bool:
        """Check if Ollama service is available."""
        try:
            response = requests.get(f"{self.config.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Ollama availability check failed: {e}")
            return False

    def is_model_available(self) -> bool:
        """Check if configured model is available."""
        try:
            response = requests.get(f"{self.config.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                return False

            models = response.json().get("models", [])
            model_names = [m.get("name", "").split(":")[0] for m in models]
            return self.config.model in model_names
        except Exception as e:
            logger.debug(f"Model availability check failed: {e}")
            return False

    def list_models(self) -> list[dict[str, Any]]:
        """
        List available Ollama models.

        Returns
        -------
            List of model information dictionaries

        Raises
        ------
            ConnectionError: If Ollama is not accessible
        """
        if not self.is_available():
            raise ConnectionError(f"Ollama is not accessible at {self.config.base_url}")

        try:
            response = requests.get(f"{self.config.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            return response.json().get("models", [])
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            raise

    def get_model_info(self, model_name: str | None = None) -> dict[str, Any]:
        """
        Get information about a model.

        Args:
            model_name: Model name. If None, uses configured model.

        Returns
        -------
            Model information dictionary

        Raises
        ------
            ConnectionError: If Ollama is not accessible
            ValueError: If model not found
        """
        model = model_name or self.config.model

        try:
            response = requests.post(
                f"{self.config.base_url}/api/show", json={"name": model}, timeout=5
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Model not found: {model}")
            raise
        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
            raise

    @property
    def lm(self):
        """Get DSPy LM instance."""
        if not self._initialized:
            self.initialize()
        return self._lm


def configure_ollama(config: OllamaConfig | None = None) -> OllamaLM:
    """
    Configure Ollama LM for DSPy.

    Args:
        config: Ollama configuration. If None, loads from environment.

    Returns
    -------
        Configured OllamaLM instance

    Raises
    ------
        RuntimeError: If DSPy is not available
        ConnectionError: If Ollama is not accessible
    """
    lm = OllamaLM(config)
    lm.initialize()
    return lm


def health_check() -> dict[str, Any]:
    """
    Perform health check for Ollama service.

    Returns
    -------
        Health check results with status and details
    """
    config = OllamaConfig.from_env()
    lm = OllamaLM(config)

    result = {
        "status": "unknown",
        "ollama_available": False,
        "model_available": False,
        "base_url": config.base_url,
        "model": config.model,
        "dspy_available": DSPY_AVAILABLE,
    }

    try:
        result["ollama_available"] = lm.is_available()

        if result["ollama_available"]:
            result["model_available"] = lm.is_model_available()

            if result["model_available"]:
                result["status"] = "healthy"
            else:
                result["status"] = "degraded"
                result["message"] = f"Model {config.model} not available"
        else:
            result["status"] = "unhealthy"
            result["message"] = "Ollama service not accessible"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result
