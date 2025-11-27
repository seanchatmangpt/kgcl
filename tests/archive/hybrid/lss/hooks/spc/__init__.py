"""SPC metrics for Knowledge Hooks.

This package provides Statistical Process Control analysis for hook execution,
tracking execution times, success rates, and process capability using Six Sigma
methodology.
"""

from __future__ import annotations

from .metrics import HookSPCMetrics, calculate_hook_moving_range, calculate_hook_spc_metrics, check_hook_stability

__all__ = ["HookSPCMetrics", "calculate_hook_spc_metrics", "calculate_hook_moving_range", "check_hook_stability"]
