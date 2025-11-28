"""Scenario-based integration tests demonstrating real-world WCP usage.

These tests exercise workflow patterns in realistic scenarios:
- test_nuclear_launch_simulation.py: Dual-key authorization, all 5 verbs
- test_nato_maximum_stress.py: Tier V patterns, FMEA risk matrix, Andon signals
- test_nato_symposium.py: Robert's Rules of Order parliamentary procedure

NOTE: test_nato_symposium.py is marked @wip - many tests are aspirational,
documenting expected behavior for full WCP pattern support. Run with:
    pytest -m wip tests/scenarios/test_nato_symposium.py -v
"""
