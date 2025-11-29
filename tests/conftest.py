"""Root pytest configuration for KGCL test suite.

This module provides:
- Docker availability checking for container tests
- Common fixtures shared across all test modules
- Test collection hooks for skipping unavailable tests
- Implementation lies detection (mocking violations, etc.)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


def _is_docker_available() -> bool:
    """Check if Docker is available and running.

    Returns
    -------
    bool
        True if Docker daemon is accessible, False otherwise.
    """
    try:
        result = subprocess.run(["docker", "info"], capture_output=True, timeout=5, check=False)
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
    config.addinivalue_line("markers", "container: marks tests requiring Docker containers")
    config.addinivalue_line("markers", "chaos: marks chaos engineering tests (failure injection, recovery)")




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


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip container tests and run lies detector.

    This hook runs during test collection to:
    1. Skip container tests if Docker is not available
    2. Run implementation lies detector on collected test files

    Parameters
    ----------
    config : pytest.Config
        Pytest configuration object.
    items : list[pytest.Item]
        List of collected test items.
    """
    # Original container skipping logic
    if DOCKER_AVAILABLE:
        pass  # Don't skip if Docker is available
    else:
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

    # Run lies detector on collected test files
    # MANDATORY: Detection is more important than speed - always run, always fail on violations
    repo_root = Path(__file__).parent.parent
    detector_script = repo_root / "scripts" / "detect_implementation_lies.py"

    if not detector_script.exists():
        pytest.exit(
            f"Lies detector script not found: {detector_script}\n"
            "Cannot run tests without lies detection.",
            returncode=1,
        )

    # Get unique test file paths
    test_files = {Path(str(item.fspath)) for item in items if hasattr(item, "fspath")}

    if not test_files:
        # No test files collected, nothing to check
        return

    # Run detector on test files - MANDATORY, no exceptions
    # Increased timeout to 60s - detection is more important than speed
    try:
        result = subprocess.run(
            [sys.executable, str(detector_script)] + [str(f) for f in test_files],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(repo_root),
            check=False,  # We check returncode manually
        )
    except subprocess.TimeoutExpired:
        pytest.exit(
            "Lies detector timed out (>60s). This is unacceptable.\n"
            "Fix detector performance or reduce test file count.\n"
            "Detection is mandatory - tests cannot proceed.",
            returncode=1,
        )
    except FileNotFoundError:
        pytest.exit(
            f"Python interpreter not found: {sys.executable}\n"
            "Cannot run lies detector. Tests blocked.",
            returncode=1,
        )
    except Exception as e:
        pytest.exit(
            f"Lies detector failed with error: {e}\n"
            "Detection is mandatory - tests cannot proceed.\n"
            "Fix the detector script before running tests.",
            returncode=1,
        )

    # Check results - ANY non-zero return code means violations detected
    if result.returncode != 0:
        # Lies detected - print output and fail HARD
        print("\n" + "=" * 70)
        print("❌ IMPLEMENTATION LIES DETECTED - Chicago TDD Violations")
        print("=" * 70)
        print(result.stdout)
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
        print("=" * 70)
        print(
            "\n🚫 TESTS BLOCKED: Implementation lies detected in test files.\n"
            "Chicago School TDD requires real objects, not mocks.\n"
            "\nFix all violations before running tests:\n"
            "  1. See: docs/how-to/migrate-from-mocks-to-factories.md\n"
            "  2. See: docs/how-to/remove-mocking-violations.md\n"
            "  3. Run: uv run python scripts/detect_implementation_lies.py tests/\n"
            "\nDetection is MANDATORY - no bypass available.\n"
        )
        pytest.exit("Implementation lies detected - fix violations before running tests", returncode=1)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add command-line options for pytest.

    Parameters
    ----------
    parser : pytest.Parser
        Pytest argument parser.

    Note
    ----
    Lies detection is MANDATORY and cannot be bypassed.
    Detection is more important than speed - all violations must be fixed.
    """
    # No --no-lies-check option - detection is mandatory
    # If you need to bypass, fix the violations instead
