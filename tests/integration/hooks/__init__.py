"""Hook phase integration tests with containers.

Tests for all 5 hook phases with external services:
- PRE_TICK: External state validation
- ON_CHANGE: Event publishing
- POST_TICK: Audit persistence
- PRE_VALIDATION: SHACL loading
- POST_VALIDATION: Alert publishing
"""
