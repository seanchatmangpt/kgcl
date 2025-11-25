"""Test kgcl."""

import kgcl


def test_import() -> None:
    """Test that the package can be imported."""
    assert isinstance(kgcl.__name__, str)
