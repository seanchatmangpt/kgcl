"""Tests for feature list CLI command."""

from click.testing import CliRunner

from kgcl.cli.feature_list import feature_list


def test_feature_list_help():
    """Test feature list help output."""
    runner = CliRunner()
    result = runner.invoke(feature_list, ["--help"])
    assert result.exit_code == 0
    assert "List features" in result.output
    assert "--category" in result.output
    assert "--search" in result.output


def test_feature_list_basic():
    """Test basic feature listing."""
    runner = CliRunner()
    result = runner.invoke(feature_list)
    assert result.exit_code == 0
    assert "Listed" in result.output


def test_feature_list_with_category():
    """Test feature list filtered by category."""
    runner = CliRunner()
    result = runner.invoke(feature_list, ["--category", "testing", "--verbose"])
    assert result.exit_code == 0


def test_feature_list_with_search():
    """Test feature list with search term."""
    runner = CliRunner()
    result = runner.invoke(feature_list, ["--search", "test", "--verbose"])
    assert result.exit_code == 0


def test_feature_list_templates_only():
    """Test feature list showing only templates."""
    runner = CliRunner()
    result = runner.invoke(feature_list, ["--templates-only"])
    assert result.exit_code == 0


def test_feature_list_instances_only():
    """Test feature list showing only instances."""
    runner = CliRunner()
    result = runner.invoke(feature_list, ["--instances-only"])
    assert result.exit_code == 0


def test_feature_list_output_formats():
    """Test different output formats."""
    runner = CliRunner()

    # Test table format
    result = runner.invoke(feature_list, ["--format", "table"])
    assert result.exit_code == 0

    # Test JSON format
    result = runner.invoke(feature_list, ["--format", "json"])
    assert result.exit_code == 0


def test_feature_list_sort_by():
    """Test feature list sorting."""
    runner = CliRunner()

    # Sort by name
    result = runner.invoke(feature_list, ["--sort-by", "name"])
    assert result.exit_code == 0

    # Sort by category
    result = runner.invoke(feature_list, ["--sort-by", "category"])
    assert result.exit_code == 0


def test_feature_list_with_output_file():
    """Test feature list with output file."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(feature_list, ["--format", "json", "--output", "features.json"])
        assert result.exit_code == 0


def test_feature_list_verbose():
    """Test feature list with verbose output."""
    runner = CliRunner()
    result = runner.invoke(feature_list, ["--verbose"])
    assert result.exit_code == 0
