"""DMAIC Phases for Knowledge Hooks.

This package provides DMAIC methodology phases specialized for Knowledge Hooks,
enabling systematic quality improvement of hook behavior and performance.
"""

from __future__ import annotations

from .phases import (
    HookAnalyzePhase,
    HookControlPhase,
    HookDefinePhase,
    HookDMAICPhase,
    HookImprovePhase,
    HookMeasurePhase,
)

__all__ = [
    "HookAnalyzePhase",
    "HookControlPhase",
    "HookDefinePhase",
    "HookDMAICPhase",
    "HookImprovePhase",
    "HookMeasurePhase",
]
