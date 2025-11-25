"""Tests for daily brief CLI command."""

from datetime import datetime

from click.testing import CliRunner

from kgcl.cli.daily_brief import daily_brief


def test_daily_brief_help():
    """Test daily brief help output."""
    runner = CliRunner()
    result = runner.invoke(daily_brief, ["--help"])
    assert result.exit_code == 0
    assert "Generate a daily brief" in result.output
    assert "--date" in result.output
    assert "--lookback" in result.output


def test_daily_brief_basic():
    """Test basic daily brief generation."""
    runner = CliRunner()
    result = runner.invoke(daily_brief, ["--verbose"])
    assert result.exit_code == 0
    assert "Daily brief generated successfully" in result.output


def test_daily_brief_with_date():
    """Test daily brief with specific date."""
    runner = CliRunner()
    result = runner.invoke(daily_brief, ["--date", "2024-01-15", "--verbose"])
    assert result.exit_code == 0
    assert "2024-01-15" in result.output or "Daily brief generated" in result.output


def test_daily_brief_with_lookback():
    """Test daily brief with custom lookback period."""
    runner = CliRunner()
    result = runner.invoke(daily_brief, ["--lookback", "3", "--verbose"])
    assert result.exit_code == 0


def test_daily_brief_output_formats():
    """Test different output formats."""
    runner = CliRunner()

    # Test markdown format
    result = runner.invoke(daily_brief, ["--format", "markdown"])
    assert result.exit_code == 0

    # Test JSON format
    result = runner.invoke(daily_brief, ["--format", "json"])
    assert result.exit_code == 0


def test_daily_brief_with_output_file():
    """Test daily brief with output file."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(daily_brief, ["--output", "brief.md"])
        assert result.exit_code == 0


def test_daily_brief_with_model():
    """Test daily brief with custom model."""
    runner = CliRunner()
    result = runner.invoke(daily_brief, ["--model", "llama3.3", "--verbose"])
    assert result.exit_code == 0
    assert "llama3.3" in result.output or "Daily brief generated" in result.output
