"""Pytest configuration for workflow pattern fixtures.

This module registers all 43 WCP fixtures and makes them available to tests.
Import this module to access workflow pattern generators.
"""

from __future__ import annotations

# Re-export all fixtures for pytest discovery
from .workflow_patterns import (
    # Basic Control Flow (1-5)
    wcp01_sequence,
    wcp02_parallel_split,
    wcp03_synchronization,
    wcp04_exclusive_choice,
    wcp05_simple_merge,
    # Advanced Branching (6-11)
    wcp06_multi_choice,
    wcp07_structured_synchronizing_merge,
    wcp08_multi_merge,
    wcp09_structured_discriminator,
    wcp10_arbitrary_cycles,
    wcp11_implicit_termination,
    # Multiple Instance (12-15)
    wcp12_mi_without_synchronization,
    wcp13_mi_with_design_time_knowledge,
    wcp14_mi_with_runtime_knowledge,
    wcp15_mi_without_runtime_knowledge,
    # State-Based (16-18)
    wcp16_deferred_choice,
    wcp17_interleaved_parallel_routing,
    wcp18_milestone,
    # Cancellation (19-25)
    wcp19_cancel_activity,
    wcp20_cancel_case,
    wcp21_cancel_region,
    wcp22_cancel_multiple_instance_activity,
    wcp23_structured_loop,
    wcp24_recursion,
    wcp25_transient_trigger,
    # MI Join (34-36)
    wcp34_static_partial_join,
    wcp35_cancelling_partial_join,
    wcp36_dynamic_partial_join,
    # Termination (43)
    wcp43_explicit_termination,
    # Factory
    workflow_pattern_factory,
)

__all__ = [
    # Basic Control Flow (1-5)
    "wcp01_sequence",
    "wcp02_parallel_split",
    "wcp03_synchronization",
    "wcp04_exclusive_choice",
    "wcp05_simple_merge",
    # Advanced Branching (6-11)
    "wcp06_multi_choice",
    "wcp07_structured_synchronizing_merge",
    "wcp08_multi_merge",
    "wcp09_structured_discriminator",
    "wcp10_arbitrary_cycles",
    "wcp11_implicit_termination",
    # Multiple Instance (12-15)
    "wcp12_mi_without_synchronization",
    "wcp13_mi_with_design_time_knowledge",
    "wcp14_mi_with_runtime_knowledge",
    "wcp15_mi_without_runtime_knowledge",
    # State-Based (16-18)
    "wcp16_deferred_choice",
    "wcp17_interleaved_parallel_routing",
    "wcp18_milestone",
    # Cancellation (19-25)
    "wcp19_cancel_activity",
    "wcp20_cancel_case",
    "wcp21_cancel_region",
    "wcp22_cancel_multiple_instance_activity",
    "wcp23_structured_loop",
    "wcp24_recursion",
    "wcp25_transient_trigger",
    # MI Join (34-36)
    "wcp34_static_partial_join",
    "wcp35_cancelling_partial_join",
    "wcp36_dynamic_partial_join",
    # Termination (43)
    "wcp43_explicit_termination",
    # Factory
    "workflow_pattern_factory",
]
