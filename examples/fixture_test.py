"""Fixture-based test example."""

from src.core import fixture_test, TestFixture


class UserFixture(TestFixture):
    """Fixture that provides a test user."""

    def setup(self):
        """Setup test user."""
        self.user = {"id": 1, "name": "Alice", "email": "alice@example.com"}
        self._initialized = True

    def get_user(self):
        """Get test user."""
        return self.user

    def update_email(self, email):
        """Update user email."""
        self.user["email"] = email

    def cleanup(self):
        """Cleanup after test."""
        del self.user


@fixture_test(UserFixture)
def test_user_exists(fixture):
    """Test that fixture provides user."""
    user = fixture.get_user()
    assert user is not None
    assert user["name"] == "Alice"


@fixture_test(UserFixture)
def test_user_email_update(fixture):
    """Test user email update."""
    fixture.update_email("alice_new@example.com")
    user = fixture.get_user()
    assert user["email"] == "alice_new@example.com"


@fixture_test(UserFixture)
def test_metadata(fixture):
    """Test fixture metadata tracking."""
    metadata = fixture.metadata()
    assert metadata is not None
    assert metadata.age_seconds() >= 0


if __name__ == "__main__":
    import asyncio
    from src.core.decorators import TestMetadata

    # Manual execution
    test_user_exists()
    test_user_email_update()
    test_metadata()
    print("✓ All fixture tests passed!")
