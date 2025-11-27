"""Root pytest configuration for KGCL test suite.

This module provides:
- Docker availability checking for container tests
- Common fixtures shared across all test modules
- Test collection hooks for skipping unavailable tests
"""

from __future__ import annotations

import subprocess

import pytest


def _is_docker_available() -> bool:
    """Check if Docker is available and running.

    Returns
    -------
    bool
        True if Docker daemon is accessible, False otherwise.
    """
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


# Check Docker availability at module load
DOCKER_AVAILABLE = _is_docker_available()


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers and settings.

    Parameters
    ----------
    config : pytest.Config
        Pytest configuration object.
    """
    # Register custom markers (also defined in pyproject.toml for IDE support)
    config.addinivalue_line(
        "markers",
        "container: marks tests requiring Docker containers",
    )
    config.addinivalue_line(
        "markers",
        "chaos: marks chaos engineering tests (failure injection, recovery)",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip container tests if Docker is not available.

    This hook runs during test collection and adds skip markers
    to any test marked with container-related markers.

    Parameters
    ----------
    config : pytest.Config
        Pytest configuration object.
    items : list[pytest.Item]
        List of collected test items.
    """
    if DOCKER_AVAILABLE:
        return

    skip_marker = pytest.mark.skip(reason="Docker not available")
    container_markers = {
        "container",
        "chaos",
        "postgres",
        "redis",
        "rabbitmq",
        "fuseki",
        "oxigraph_server",
        "multi_engine",
        "integration",
    }

    for item in items:
        # Check if item is in integration or chaos directories
        item_path = str(item.fspath)
        if "/integration/" in item_path or "/chaos/" in item_path:
            item.add_marker(skip_marker)
            continue

        # Check for container-related markers
        item_markers = {marker.name for marker in item.iter_markers()}
        if item_markers & container_markers:
            item.add_marker(skip_marker)


def pytest_report_header(config: pytest.Config) -> list[str]:
    """Add Docker availability status to test report header.

    Parameters
    ----------
    config : pytest.Config
        Pytest configuration object.

    Returns
    -------
    list[str]
        Lines to add to the report header.
    """
    status = "available" if DOCKER_AVAILABLE else "NOT available"
    return [f"Docker: {status}"]
