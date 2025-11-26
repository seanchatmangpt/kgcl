"""
DSPy + Ollama runtime for KGCL.

Provides production-ready integration between DSPy signatures and Ollama LLMs
with comprehensive observability, error handling, and UNRDF integration.
"""

from .invoker import InvocationResult, SignatureInvoker
from .ollama_config import DSPY_AVAILABLE, OllamaConfig, OllamaLM, configure_ollama, health_check
from .receipts import Receipt, ReceiptGenerator
from .unrdf_bridge import UNRDFBridge

__all__ = [
    "DSPY_AVAILABLE",
    "InvocationResult",
    "OllamaConfig",
    "OllamaLM",
    "Receipt",
    "ReceiptGenerator",
    "SignatureInvoker",
    "UNRDFBridge",
    "configure_ollama",
    "health_check",
]

__version__ = "0.1.0"
