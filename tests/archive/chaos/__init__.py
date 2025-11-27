"""Chaos engineering tests for KGCL.

Tests for failure injection, recovery mechanisms, and multi-engine coordination:
- failure_injection/: Container crashes, network partitions, timeouts
- recovery/: Automatic retry, lockchain recovery, orphan cleanup
- multi_engine/: Shared store, event coordination, distributed locks
"""
