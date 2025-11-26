"""Workflow pattern fixtures for KGCL v3 testing.

This package provides RDF graph fixtures for all 43 Van der Aalst
Workflow Control Patterns (WCP).

Usage:
    from tests.fixtures import wcp01_sequence, wcp07_structured_synchronizing_merge

    def test_sequence_execution(wcp01_sequence):
        graph = wcp01_sequence
        # Test execution...

Categories:
    - Basic Control Flow (1-5): Sequence, AND-split/join, XOR-split/join
    - Advanced Branching (6-11): OR-split/join, Multi-merge, Discriminator, Cycles
    - Multiple Instance (12-15): MI with/without sync, design-time/runtime knowledge
    - State-Based (16-18): Deferred choice, Interleaved routing, Milestone
    - Cancellation (19-25): Cancel activity/case/region/MI, Loop, Recursion, Trigger
    - MI Join (34-36): Static/Cancelling/Dynamic partial join
    - Termination (43): Explicit termination
"""

from __future__ import annotations

from .workflow_patterns import (
    create_workflow_pattern,  # Plain function for non-test usage
    wcp01_sequence,
    wcp02_parallel_split,
    wcp03_synchronization,
    wcp04_exclusive_choice,
    wcp05_simple_merge,
    wcp06_multi_choice,
    wcp07_structured_synchronizing_merge,
    wcp08_multi_merge,
    wcp09_structured_discriminator,
    wcp10_arbitrary_cycles,
    wcp11_implicit_termination,
    wcp12_mi_without_synchronization,
    wcp13_mi_with_design_time_knowledge,
    wcp14_mi_with_runtime_knowledge,
    wcp15_mi_without_runtime_knowledge,
    wcp16_deferred_choice,
    wcp17_interleaved_parallel_routing,
    wcp18_milestone,
    wcp19_cancel_activity,
    wcp20_cancel_case,
    wcp21_cancel_region,
    wcp22_cancel_multiple_instance_activity,
    wcp23_structured_loop,
    wcp24_recursion,
    wcp25_transient_trigger,
    wcp34_static_partial_join,
    wcp35_cancelling_partial_join,
    wcp36_dynamic_partial_join,
    wcp43_explicit_termination,
    workflow_pattern_factory,
)

__all__ = [
    "wcp01_sequence",
    "wcp02_parallel_split",
    "wcp03_synchronization",
    "wcp04_exclusive_choice",
    "wcp05_simple_merge",
    "wcp06_multi_choice",
    "wcp07_structured_synchronizing_merge",
    "wcp08_multi_merge",
    "wcp09_structured_discriminator",
    "wcp10_arbitrary_cycles",
    "wcp11_implicit_termination",
    "wcp12_mi_without_synchronization",
    "wcp13_mi_with_design_time_knowledge",
    "wcp14_mi_with_runtime_knowledge",
    "wcp15_mi_without_runtime_knowledge",
    "wcp16_deferred_choice",
    "wcp17_interleaved_parallel_routing",
    "wcp18_milestone",
    "wcp19_cancel_activity",
    "wcp20_cancel_case",
    "wcp21_cancel_region",
    "wcp22_cancel_multiple_instance_activity",
    "wcp23_structured_loop",
    "wcp24_recursion",
    "wcp25_transient_trigger",
    "wcp34_static_partial_join",
    "wcp35_cancelling_partial_join",
    "wcp36_dynamic_partial_join",
    "wcp43_explicit_termination",
    "workflow_pattern_factory",
]
