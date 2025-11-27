"""Tests for safe Jinja filters."""

import pytest

from kgcl.projection.filters.safe_filters import (
    camel_case,
    group_by,
    indent,
    kebab_case,
    pascal_case,
    pluck,
    slugify,
    snake_case,
    sort_by,
    truncate,
    unique,
)


class TestCaseConversions:
    """Test case conversion filters."""

    def test_snake_case_from_camel(self) -> None:
        """Convert camelCase to snake_case."""
        assert snake_case("helloWorld") == "hello_world"
        assert snake_case("someCamelCase") == "some_camel_case"

    def test_snake_case_from_pascal(self) -> None:
        """Convert PascalCase to snake_case."""
        assert snake_case("HelloWorld") == "hello_world"
        assert snake_case("UserProfile") == "user_profile"

    def test_snake_case_already_snake(self) -> None:
        """Handle already snake_case strings."""
        assert snake_case("already_snake") == "already_snake"
        assert snake_case("snake_case_text") == "snake_case_text"

    def test_snake_case_with_spaces(self) -> None:
        """Convert spaces to underscores."""
        assert snake_case("Hello World") == "hello_world"
        assert snake_case("Multiple Word String") == "multiple_word_string"

    def test_snake_case_consecutive_caps(self) -> None:
        """Handle consecutive uppercase letters."""
        assert snake_case("HTTPServer") == "http_server"
        assert snake_case("XMLParser") == "xml_parser"

    def test_camel_case_from_snake(self) -> None:
        """Convert snake_case to camelCase."""
        assert camel_case("hello_world") == "helloWorld"
        assert camel_case("user_profile") == "userProfile"

    def test_camel_case_from_kebab(self) -> None:
        """Convert kebab-case to camelCase."""
        assert camel_case("hello-world") == "helloWorld"
        assert camel_case("some-kebab-case") == "someKebabCase"

    def test_camel_case_from_spaces(self) -> None:
        """Convert spaced words to camelCase."""
        assert camel_case("Hello World") == "helloWorld"
        assert camel_case("Multiple Words Here") == "multipleWordsHere"

    def test_camel_case_empty(self) -> None:
        """Handle empty string."""
        assert camel_case("") == ""

    def test_pascal_case_from_snake(self) -> None:
        """Convert snake_case to PascalCase."""
        assert pascal_case("hello_world") == "HelloWorld"
        assert pascal_case("user_profile") == "UserProfile"

    def test_pascal_case_from_kebab(self) -> None:
        """Convert kebab-case to PascalCase."""
        assert pascal_case("hello-world") == "HelloWorld"
        assert pascal_case("some-kebab-case") == "SomeKebabCase"

    def test_pascal_case_from_spaces(self) -> None:
        """Convert spaced words to PascalCase."""
        assert pascal_case("hello world") == "HelloWorld"
        assert pascal_case("already PascalCase") == "AlreadyPascalcase"

    def test_kebab_case_from_camel(self) -> None:
        """Convert camelCase to kebab-case."""
        assert kebab_case("helloWorld") == "hello-world"
        assert kebab_case("someCamelCase") == "some-camel-case"

    def test_kebab_case_from_snake(self) -> None:
        """Convert snake_case to kebab-case."""
        assert kebab_case("hello_world") == "hello-world"
        assert kebab_case("some_snake_case") == "some-snake-case"

    def test_kebab_case_from_spaces(self) -> None:
        """Convert spaces to hyphens."""
        assert kebab_case("Hello World") == "hello-world"
        assert kebab_case("Already Kebab") == "already-kebab"

    def test_kebab_case_consecutive_caps(self) -> None:
        """Handle consecutive uppercase letters."""
        assert kebab_case("HTTPServer") == "http-server"
        assert kebab_case("XMLParser") == "xml-parser"


class TestSlugify:
    """Test slugify filter."""

    def test_slugify_basic(self) -> None:
        """Convert basic string to slug."""
        assert slugify("Hello World") == "hello-world"
        assert slugify("Simple Test") == "simple-test"

    def test_slugify_special_chars(self) -> None:
        """Remove special characters."""
        assert slugify("Hello World!") == "hello-world"
        assert slugify("Complex: String (with) Special#Chars") == "complex-string-with-specialchars"

    def test_slugify_multiple_spaces(self) -> None:
        """Collapse multiple spaces."""
        assert slugify("  Multiple   Spaces  ") == "multiple-spaces"
        assert slugify("Too    Many    Spaces") == "too-many-spaces"

    def test_slugify_existing_hyphens(self) -> None:
        """Handle existing hyphens."""
        assert slugify("already-hyphenated") == "already-hyphenated"
        assert slugify("mixed--hyphens") == "mixed-hyphens"


class TestTruncate:
    """Test truncate filter."""

    def test_truncate_shorter_than_limit(self) -> None:
        """Don't truncate if under limit."""
        assert truncate("Short", 10) == "Short"
        assert truncate("Test", 10) == "Test"

    def test_truncate_at_limit(self) -> None:
        """Truncate at exact limit."""
        assert truncate("Hello World", 8) == "Hello..."
        assert truncate("Testing", 6) == "Tes..."

    def test_truncate_custom_suffix(self) -> None:
        """Use custom suffix."""
        assert truncate("Truncate me", 8, "…") == "Truncat…"
        assert truncate("Long text here", 10, ">>") == "Long tex>>"

    def test_truncate_suffix_longer_than_limit(self) -> None:
        """Handle suffix longer than limit."""
        result = truncate("Test", 2, "...")
        assert len(result) <= 5  # Shouldn't crash
        assert result == "..."  # Just the suffix


class TestIndent:
    """Test indent filter."""

    def test_indent_default(self) -> None:
        """Indent with default 4 spaces."""
        assert indent("line1\nline2") == "line1\n    line2"
        assert indent("first\nsecond\nthird") == "first\n    second\n    third"

    def test_indent_custom_width(self) -> None:
        """Indent with custom width."""
        assert indent("line1\nline2", 2) == "line1\n  line2"
        assert indent("a\nb", 6) == "a\n      b"

    def test_indent_first_line(self) -> None:
        """Indent first line when requested."""
        assert indent("line1\nline2", 2, first=True) == "  line1\n  line2"
        assert indent("single", 4, first=True) == "    single"

    def test_indent_empty_string(self) -> None:
        """Handle empty string."""
        assert indent("", 4) == ""
        assert indent("", 4, first=True) == ""

    def test_indent_single_line(self) -> None:
        """Handle single line."""
        assert indent("single", 2) == "single"
        assert indent("single", 2, first=True) == "  single"


class TestCollectionFilters:
    """Test collection manipulation filters."""

    def test_sort_by_string_key(self) -> None:
        """Sort by string key."""
        items = [{"name": "Bob", "age": 30}, {"name": "Alice", "age": 25}]
        result = sort_by(items, "name")
        assert result[0]["name"] == "Alice"
        assert result[1]["name"] == "Bob"

    def test_sort_by_numeric_key(self) -> None:
        """Sort by numeric key."""
        items = [{"name": "Bob", "age": 30}, {"name": "Alice", "age": 25}]
        result = sort_by(items, "age")
        assert result[0]["age"] == 25
        assert result[1]["age"] == 30

    def test_unique_preserves_order(self) -> None:
        """Remove duplicates while preserving order."""
        assert unique([1, 2, 2, 3, 1]) == [1, 2, 3]
        assert unique(["a", "b", "a", "c"]) == ["a", "b", "c"]

    def test_unique_all_unique(self) -> None:
        """Handle list with no duplicates."""
        assert unique([1, 2, 3]) == [1, 2, 3]
        assert unique(["x", "y", "z"]) == ["x", "y", "z"]

    def test_unique_all_same(self) -> None:
        """Handle list with all same values."""
        assert unique([1, 1, 1]) == [1]
        assert unique(["a", "a"]) == ["a"]

    def test_group_by_creates_groups(self) -> None:
        """Group items by key value."""
        items = [{"type": "A", "value": 1}, {"type": "B", "value": 2}, {"type": "A", "value": 3}]
        result = group_by(items, "type")

        assert len(result["A"]) == 2
        assert result["A"][0]["value"] == 1
        assert result["A"][1]["value"] == 3

        assert len(result["B"]) == 1
        assert result["B"][0]["value"] == 2

    def test_group_by_empty_list(self) -> None:
        """Handle empty list."""
        result = group_by([], "key")
        assert result == {}

    def test_group_by_missing_key(self) -> None:
        """Handle items missing the group key."""
        items = [{"type": "A"}, {"value": 1}]
        result = group_by(items, "type")
        assert "A" in result
        assert "" in result  # Missing key becomes empty string

    def test_pluck_extracts_values(self) -> None:
        """Extract values for key."""
        items = [{"name": "Alice", "age": 25}, {"name": "Bob", "age": 30}]
        assert pluck(items, "name") == ["Alice", "Bob"]
        assert pluck(items, "age") == [25, 30]

    def test_pluck_missing_key(self) -> None:
        """Handle missing keys."""
        items = [{"name": "Alice"}, {"age": 30}]
        result = pluck(items, "name")
        assert result == ["Alice", None]

    def test_pluck_empty_list(self) -> None:
        """Handle empty list."""
        assert pluck([], "key") == []


class TestFilterExports:
    """Test SAFE_FILTERS export."""

    def test_all_filters_exported(self) -> None:
        """Verify all filters are in SAFE_FILTERS dict."""
        from kgcl.projection.filters.safe_filters import SAFE_FILTERS

        expected_filters = {
            "snake_case",
            "camel_case",
            "pascal_case",
            "kebab_case",
            "slugify",
            "truncate",
            "indent",
            "sort_by",
            "unique",
            "group_by",
            "pluck",
        }
        assert set(SAFE_FILTERS.keys()) == expected_filters

    def test_filters_are_callable(self) -> None:
        """Verify all exported filters are callable."""
        from kgcl.projection.filters.safe_filters import SAFE_FILTERS

        for name, func in SAFE_FILTERS.items():
            assert callable(func), f"Filter {name} is not callable"
