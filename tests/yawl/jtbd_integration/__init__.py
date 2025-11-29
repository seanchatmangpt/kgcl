"""Jobs-To-Be-Done (JTBD) integration tests for YAWL engine.

Tests organized by the jobs users need to accomplish with YAWL workflows,
rather than by technical implementation details.

Test organization:
- test_jtbd_execute_workflow.py: Execute workflows from start to finish
- test_jtbd_parallel_sync.py: Execute parallel work with synchronization
- test_jtbd_routing_decisions.py: Make data-driven routing decisions
- test_jtbd_multi_instance.py: Handle multiple task instances
- test_jtbd_cancellation.py: Cancel cases and handle cancellation regions
- test_jtbd_work_items.py: Manage work item lifecycle
- test_jtbd_persistence.py: Persist and restore workflow state
- test_jtbd_monitoring.py: Query and monitor workflow status
"""
