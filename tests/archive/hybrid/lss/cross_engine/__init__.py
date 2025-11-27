"""Cross-Engine WCP-43 Validation Test Suite.

This package organizes cross-engine validation tests for all 43 YAWL Workflow
Control Patterns (WCP) across PyOxigraph and EYE reasoner engines.

Test Organization
-----------------
- fixtures.py: Shared test fixtures and topology definitions
- test_wcp_01_05.py: Basic Control Flow (WCP 1-5)
- test_wcp_06_11.py: Advanced Branching (WCP 6-11)
- test_wcp_12_20.py: Multiple Instances & Cancellation (WCP 12-20)
- test_wcp_21_43.py: Advanced Joins & Triggers (WCP 21-43)

Cross-Engine Testing
--------------------
Each pattern is tested on:
1. PyOxigraph (in-memory RDF store + N3 rules)
2. EYE Reasoner (external Euler reasoner subprocess)
3. Cross-engine consistency (both produce same results)

Markers
-------
- @pytest.mark.wcp(n): Pattern number (1-43)
- @pytest.mark.oxigraph: PyOxigraph-specific test
- @pytest.mark.eye: EYE reasoner-specific test
- @pytest.mark.cross_engine: Cross-engine consistency test

References
----------
- WCP Catalog: http://workflowpatterns.com/patterns/control/
- YAWL Foundation: http://www.yawlfoundation.org/
- N3 Specification: https://www.w3.org/TeamSubmission/n3/
"""

from __future__ import annotations

from .fixtures import (
    WCP1_SEQUENCE_TOPOLOGY,
    WCP2_PARALLEL_SPLIT_TOPOLOGY,
    WCP3_SYNCHRONIZATION_TOPOLOGY,
    WCP4_EXCLUSIVE_CHOICE_TOPOLOGY,
    WCP11_IMPLICIT_TERMINATION_TOPOLOGY,
    WCP43_EXPLICIT_TERMINATION_TOPOLOGY,
    assert_task_status,
    run_engine_test,
)

__all__: list[str] = [
    "WCP1_SEQUENCE_TOPOLOGY",
    "WCP2_PARALLEL_SPLIT_TOPOLOGY",
    "WCP3_SYNCHRONIZATION_TOPOLOGY",
    "WCP4_EXCLUSIVE_CHOICE_TOPOLOGY",
    "WCP11_IMPLICIT_TERMINATION_TOPOLOGY",
    "WCP43_EXPLICIT_TERMINATION_TOPOLOGY",
    "assert_task_status",
    "run_engine_test",
]
