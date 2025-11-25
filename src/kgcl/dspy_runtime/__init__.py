"""
DSPy + Ollama runtime for KGCL.

Provides production-ready integration between DSPy signatures and Ollama LLMs
with comprehensive observability, error handling, and UNRDF integration.
"""

from .ollama_config import OllamaLM, OllamaConfig, configure_ollama, health_check, DSPY_AVAILABLE
from .invoker import SignatureInvoker, InvocationResult
from .receipts import Receipt, ReceiptGenerator
from .unrdf_bridge import UNRDFBridge

__all__ = [
    "OllamaLM",
    "OllamaConfig",
    "configure_ollama",
    "health_check",
    "DSPY_AVAILABLE",
    "SignatureInvoker",
    "InvocationResult",
    "Receipt",
    "ReceiptGenerator",
    "UNRDFBridge",
]

__version__ = "0.1.0"
