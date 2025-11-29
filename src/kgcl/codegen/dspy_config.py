"""DSPy configuration with Ollama granite4 model as default.

Provides centralized DSPy configuration with environment variable support
for flexible model selection and API endpoint configuration.
"""

import os
from typing import Any

import dspy


def configure_dspy(model: str | None = None, api_base: str | None = None, api_key: str = "", **kwargs: Any) -> dspy.LM:
    """Configure DSPy with Ollama granite4 model as default.

    Parameters
    ----------
    model : str | None, default=None
        Model identifier (e.g., 'ollama/granite4', 'ollama/llama3.2')
        Defaults to DSPY_MODEL env var or 'ollama/granite4'
    api_base : str | None, default=None
        API base URL for Ollama server
        Defaults to DSPY_API_BASE env var or 'http://localhost:11434'
    api_key : str, default=""
        API key (empty string for local Ollama)
    **kwargs : Any
        Additional DSPy LM configuration options

    Returns
    -------
    dspy.LM
        Configured DSPy language model

    Examples
    --------
    >>> lm = configure_dspy()  # Uses defaults
    >>> lm = configure_dspy(model="ollama/llama3.2")  # Custom model
    >>> lm = configure_dspy(api_base="http://remote:11434")  # Remote server

    Environment Variables
    ---------------------
    DSPY_MODEL : str
        Default model (default: 'ollama/granite4')
    DSPY_API_BASE : str
        Default API base URL (default: 'http://localhost:11434')
    DSPY_API_KEY : str
        API key (default: '')
    """
    if model is None:
        model = os.getenv("DSPY_MODEL", "ollama/granite4")

    if api_base is None:
        api_base = os.getenv("DSPY_API_BASE", "http://localhost:11434")

    if not api_key:
        api_key = os.getenv("DSPY_API_KEY", "")

    lm = dspy.LM(model, api_base=api_base, api_key=api_key, **kwargs)

    dspy.configure(lm=lm)

    return lm


def get_configured_lm() -> dspy.LM | None:
    """Get currently configured DSPy language model.

    Returns
    -------
    dspy.LM | None
        Currently configured language model, or None if not configured

    Examples
    --------
    >>> configure_dspy()
    >>> lm = get_configured_lm()
    >>> lm is not None
    True
    """
    try:
        return dspy.settings.lm
    except AttributeError:
        return None


def is_dspy_configured() -> bool:
    """Check if DSPy is currently configured.

    Returns
    -------
    bool
        True if DSPy has a configured language model

    Examples
    --------
    >>> is_dspy_configured()
    False
    >>> configure_dspy()
    >>> is_dspy_configured()
    True
    """
    return get_configured_lm() is not None


# Auto-configure on import if DSPY_AUTO_CONFIGURE is set
if os.getenv("DSPY_AUTO_CONFIGURE", "").lower() in ("1", "true", "yes"):
    configure_dspy()
