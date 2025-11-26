"""Pytest fixtures for YAWL Engine tests."""

from __future__ import annotations

import pytest

from kgcl.engine import Atman


@pytest.fixture
def atman() -> Atman:
    """Create fresh Atman engine for YAWL workflow execution."""
    return Atman()
