"""KGCL Observability module.

Provides health checks, metrics, and monitoring capabilities.
"""

from __future__ import annotations

__all__ = ["health_check", "get_metrics"]


def health_check() -> dict[str, bool]:
    """Check system health.

    Returns
    -------
    dict[str, bool]
        Health status for each component.
    """
    import subprocess

    status: dict[str, bool] = {}

    # Check PyOxigraph
    try:
        import pyoxigraph

        status["pyoxigraph"] = True
    except ImportError:
        status["pyoxigraph"] = False

    # Check EYE
    try:
        subprocess.run(["eye", "--version"], capture_output=True, timeout=5, check=True)
        status["eye_reasoner"] = True
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        status["eye_reasoner"] = False

    # Check HybridEngine
    try:
        from kgcl.hybrid import HybridEngine

        engine = HybridEngine()
        status["hybrid_engine"] = True
    except Exception:
        status["hybrid_engine"] = False

    return status


def get_metrics() -> dict[str, int | float]:
    """Get system metrics.

    Returns
    -------
    dict[str, int | float]
        Current system metrics.
    """
    return {"version": 2.0, "components": 3}
