"""DMAIC (Define-Measure-Analyze-Improve-Control) Test Suite for WCP-43.

This package implements comprehensive DMAIC testing methodology for all 43 YAWL
Workflow Control Patterns. Each phase validates different aspects of pattern execution.

DMAIC Phases
------------
1. **DEFINE**: Verify all 43 patterns are correctly defined in ontology
2. **MEASURE**: Validate measurable metrics (tick counts, delta, duration)
3. **ANALYZE**: Test pattern analysis capabilities (correlation, root cause)
4. **IMPROVE**: Verify optimization and improvement paths
5. **CONTROL**: Test control mechanisms (max_ticks, convergence, boundaries)

Test Strategy
-------------
- Chicago School TDD: Tests verify BEHAVIOR, not implementation
- Real execution: All tests use HybridEngine with EYE reasoner
- Comprehensive coverage: 15+ tests across all 5 DMAIC phases
- Production patterns: Based on real WCP-43 ontology and physics

Quality Standards
-----------------
- 100% type hints on all functions
- NumPy-style docstrings with doctests
- AAA pattern (Arrange-Act-Assert)
- <1s test runtime per test
- Zero mocking of domain objects

Examples
--------
Run all DMAIC tests:

>>> # pytest tests/hybrid/lss/dmaic/

Run specific phase:

>>> # pytest tests/hybrid/lss/dmaic/test_define.py

Check pattern phases:

>>> from tests.hybrid.lss.dmaic.phases import DMAICPhase
>>> list(DMAICPhase)  # doctest: +NORMALIZE_WHITESPACE
[<DMAICPhase.DEFINE: 'define'>, <DMAICPhase.MEASURE: 'measure'>,
 <DMAICPhase.ANALYZE: 'analyze'>, <DMAICPhase.IMPROVE: 'improve'>,
 <DMAICPhase.CONTROL: 'control'>]

References
----------
- DMAIC Methodology: Six Sigma quality improvement framework
- WCP-43: All 43 YAWL Workflow Control Patterns
- Hybrid Engine: PyOxigraph + EYE reasoner architecture
"""

from __future__ import annotations

from tests.hybrid.lss.dmaic.phases import DMAICPhase, PhaseResult

__all__ = ["DMAICPhase", "PhaseResult"]
