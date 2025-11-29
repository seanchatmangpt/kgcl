"""Tests for Settings class."""

import pytest

from kgcl.yawl_ui.utils.settings import Settings


class TestSettings:
    """Test suite for Settings class."""

    def test_default_value(self) -> None:
        """Test default value is False."""
        # Reset to known state
        Settings.set_directly_to_me(False)
        assert Settings.is_directly_to_me() is False

    def test_set_true(self) -> None:
        """Test setting to True."""
        Settings.set_directly_to_me(True)
        assert Settings.is_directly_to_me() is True

    def test_set_false(self) -> None:
        """Test setting to False."""
        Settings.set_directly_to_me(False)
        assert Settings.is_directly_to_me() is False

    def test_toggle_behavior(self) -> None:
        """Test toggling between True and False."""
        Settings.set_directly_to_me(True)
        assert Settings.is_directly_to_me() is True

        Settings.set_directly_to_me(False)
        assert Settings.is_directly_to_me() is False

        Settings.set_directly_to_me(True)
        assert Settings.is_directly_to_me() is True

    def test_class_level_state(self) -> None:
        """Test that state is maintained at class level."""
        Settings.set_directly_to_me(True)

        # Access from different reference should see same value
        assert Settings.is_directly_to_me() is True

        Settings.set_directly_to_me(False)
        assert Settings.is_directly_to_me() is False
