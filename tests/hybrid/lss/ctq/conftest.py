"""Pytest fixtures for CTQ test suite.

This module provides shared fixtures for Critical-to-Quality (CTQ) testing
across all WCP-43 pattern validation tests.

Fixtures
--------
engine
    Fresh HybridEngine instance for each test
load_and_run
    Factory fixture for loading topology and running physics
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine

if TYPE_CHECKING:
    from collections.abc import Callable

    from kgcl.hybrid.hybrid_engine import PhysicsResult


@pytest.fixture
def engine() -> HybridEngine:
    """Create fresh HybridEngine for CTQ testing.

    Returns
    -------
    HybridEngine
        Fresh in-memory engine with PyOxigraph store.

    Examples
    --------
    >>> def test_example(engine):
    ...     engine.load_data("@prefix kgc: <https://kgc.org/ns/> .")
    ...     results = engine.run_to_completion(max_ticks=5)
    ...     assert len(results) >= 1
    """
    return HybridEngine()
