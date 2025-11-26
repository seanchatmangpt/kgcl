"""KGC Hybrid Engine Validation Scenarios.

This module contains validation scenarios for testing the Compiled Physics
architecture against real-world workflow patterns.

Scenarios
---------
- `nuclear_launch`: Nuclear launch authorization workflow demonstrating
  all essential YAWL Workflow Control Patterns (WCP-1 through WCP-11)
"""

from __future__ import annotations

from kgcl.hybrid.scenarios.nuclear_launch import (
    EXPECTED_ABORT_FINAL_STATE,
    EXPECTED_LAUNCH_FINAL_STATE,
    NUCLEAR_LAUNCH_ONTOLOGY,
    NUCLEAR_LAUNCH_TOPOLOGY,
    create_abort_scenario,
    create_launch_scenario,
    create_timeout_scenario,
    load_nuclear_launch_ontology,
)

__all__ = [
    "NUCLEAR_LAUNCH_ONTOLOGY",
    "NUCLEAR_LAUNCH_TOPOLOGY",
    "EXPECTED_ABORT_FINAL_STATE",
    "EXPECTED_LAUNCH_FINAL_STATE",
    "load_nuclear_launch_ontology",
    "create_abort_scenario",
    "create_launch_scenario",
    "create_timeout_scenario",
]
