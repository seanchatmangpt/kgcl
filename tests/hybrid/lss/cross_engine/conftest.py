"""PyTest configuration for cross-engine WCP tests.

This module provides fixtures for cross-engine testing.
"""

from __future__ import annotations

import shutil

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine


@pytest.fixture(scope="module")
def eye_available() -> bool:
    """Check if EYE reasoner is installed and available.

    Returns
    -------
    bool
        True if EYE is installed, False otherwise
    """
    return shutil.which("eye") is not None


@pytest.fixture
def oxigraph_engine() -> HybridEngine:
    """Create a fresh HybridEngine for testing.

    Returns
    -------
    HybridEngine
        Clean engine instance
    """
    return HybridEngine()


@pytest.fixture
def eye_engine(eye_available: bool) -> HybridEngine:
    """Create a HybridEngine configured for EYE testing.

    Parameters
    ----------
    eye_available : bool
        Whether EYE reasoner is installed

    Returns
    -------
    HybridEngine
        Engine instance for EYE testing

    Raises
    ------
    pytest.skip
        If EYE reasoner is not installed
    """
    if not eye_available:
        pytest.skip("EYE reasoner not installed")
    return HybridEngine()
