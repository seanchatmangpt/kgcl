"""Gemba Walk verification framework for WCP-43 patterns.

Gemba Walk ("go and see") is a lean management practice of observing the actual
work process in its natural environment. This package provides tools and tests
for verifying YAWL workflow control patterns through REAL HybridEngine execution.

Modules
-------
observations : GembaObservation and WalkResult dataclasses with doctests
test_sequence_walk : Sequence flow pattern verification
test_parallel_walk : Parallel split/join pattern verification
test_choice_walk : XOR/OR choice pattern verification
test_advanced_walk : Advanced pattern verification (cancel, milestone, iteration)

References
----------
- Toyota Production System: Gemba Kaizen
- Taiichi Ohno: "Go see, ask why, show respect"
- WCP-43: YAWL Workflow Control Patterns
"""

from __future__ import annotations

from tests.hybrid.lss.gemba.observations import GembaObservation, ObservationPoint, WalkResult, gemba_observe

__all__ = ["GembaObservation", "ObservationPoint", "WalkResult", "gemba_observe"]
