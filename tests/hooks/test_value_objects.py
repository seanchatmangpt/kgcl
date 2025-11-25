"""Tests for hook value objects."""

import pytest

from kgcl.hooks.value_objects import ExecutionId, HookName, LifecycleEventType


class TestHookName:
    """Validate HookName poka-yoke behavior."""

    def test_hook_name_trims_and_validates(self) -> None:
        name = HookName.new("  valid-hook_01 ")
        assert isinstance(name, HookName)
        assert name == "valid-hook_01"

    @pytest.mark.parametrize("raw", ["", "   ", "bad name", "name/with space", "x" * 200])
    def test_invalid_names_raise(self, raw: str) -> None:
        with pytest.raises(ValueError):
            HookName.new(raw)


class TestExecutionId:
    """ExecutionId enforces UUID formatting."""

    def test_execution_id_new_is_valid_uuid(self) -> None:
        execution_id = ExecutionId.new()
        assert ExecutionId.ensure(execution_id) == execution_id

    def test_execution_id_rejects_invalid(self) -> None:
        with pytest.raises(ValueError):
            ExecutionId.ensure("not-a-uuid")


def test_lifecycle_event_type_values() -> None:
    """Lifecycle event enums remain stable."""
    assert LifecycleEventType.PRE_CONDITION.value == "pre_condition"
    assert LifecycleEventType.POST_EXECUTE.value == "post_execute"
