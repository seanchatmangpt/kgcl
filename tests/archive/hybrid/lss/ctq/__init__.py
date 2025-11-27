"""CTQ (Critical-to-Quality) Mapping Framework for WCP-43 Patterns.

This package implements comprehensive CTQ factor validation across all 43 YAWL
Workflow Control Patterns. Each pattern is tested against 5 CTQ dimensions derived
from Lean Six Sigma manufacturing quality standards.

Modules
-------
factors
    CTQFactor dataclass and CTQDimension enum with doctests
test_correctness
    Correctness CTQ tests (expected state transitions)
test_completeness
    Completeness CTQ tests (all execution paths handled)
test_consistency
    Consistency CTQ tests (deterministic behavior)
test_performance
    Performance CTQ tests (tick/time bounds)
test_reliability
    Reliability CTQ tests (edge cases and failure modes)

CTQ Dimensions
--------------
1. **Correctness**: Pattern produces expected state transitions
2. **Completeness**: All execution paths are handled
3. **Consistency**: Deterministic behavior across multiple runs
4. **Performance**: Execution within acceptable tick/time bounds
5. **Reliability**: Graceful handling of edge cases and failure modes

Pattern Categories (8 Total)
-----------------------------
1. Basic Control Flow (WCP 1-5): Sequential, parallel, choice patterns
2. Advanced Branching (WCP 6-9): OR-splits, discriminators
3. Structural (WCP 10-11): Loops, termination
4. Multiple Instances (WCP 12-15): Dynamic parallelism
5. State-Based (WCP 16-18): Deferred choice, milestones
6. Cancellation (WCP 19-20, 25-27): Cancellation semantics
7. Iteration & Triggers (WCP 21-24): Loops, events
8. Advanced Joins (WCP 28-43): Complex synchronization

Testing Methodology
-------------------
- **Chicago School TDD**: Behavior verification, not implementation
- **AAA Structure**: Arrange-Act-Assert
- **Minimal Coverage**: 80%+ test coverage across all CTQ factors
- **Performance**: <1s total test runtime, <100ms per physics tick

Quality Gates
-------------
- All tests must pass (0 failures)
- Type hints: 100% coverage
- Docstrings: NumPy style, all public classes/functions
- No suppression comments (type: ignore, noqa)

References
----------
- YAWL Foundation: http://www.workflowpatterns.com
- Russell et al. (2006) "Workflow Control-Flow Patterns: A Revised View"
- ISO 9001:2015 Quality Management Systems

Examples
--------
>>> from tests.hybrid.lss.ctq.factors import CTQDimension, CTQFactor
>>> factor = CTQFactor(
...     dimension=CTQDimension.CORRECTNESS,
...     pattern_id=1,
...     description="WCP-1 Sequence produces correct linear state transition",
... )
>>> factor.dimension.value
'correctness'
>>> factor.is_valid()
True
"""

from __future__ import annotations

from tests.hybrid.lss.ctq.factors import CTQDimension, CTQFactor

__all__ = ["CTQDimension", "CTQFactor"]
