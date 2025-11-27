"""Kaizen (Continuous Improvement) test package for WCP-43 patterns.

Kaizen is the lean manufacturing philosophy of continuous, incremental improvement.
This package verifies that WCP-43 patterns continuously improve through:

1. **Muda (Waste)**: Test for and eliminate unnecessary operations
2. **Muri (Overburden)**: Test for excessive complexity
3. **Mura (Unevenness)**: Test for inconsistent behavior
4. **5S**: Test Sort, Set, Shine, Standardize, Sustain
5. **Gemba Kaizen**: Test improvements at the actual workflow level

Modules
-------
metrics : KaizenMetric and KaizenReport dataclasses
test_muda : Waste elimination tests
test_muri : Overburden tests
test_mura : Unevenness tests
test_5s : 5S methodology tests
test_gemba_kaizen : Shop floor improvement tests

References
----------
- Kaizen: The Key to Japan's Competitive Success (Imai, 1986)
- Toyota Production System: Beyond Large-Scale Production (Ohno, 1988)
- WCP-43: YAWL Workflow Control Patterns
"""

from __future__ import annotations

from tests.hybrid.lss.kaizen.metrics import KaizenMetric, KaizenReport

__all__ = ["KaizenMetric", "KaizenReport"]
