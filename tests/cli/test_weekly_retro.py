"""Tests for weekly retrospective CLI command."""

from click.testing import CliRunner

from kgcl.cli.weekly_retro import weekly_retro


def test_weekly_retro_help():
    """Test weekly retro help output."""
    runner = CliRunner()
    result = runner.invoke(weekly_retro, ["--help"])
    assert result.exit_code == 0
    assert "Generate a weekly retrospective" in result.output
    assert "--days" in result.output
    assert "--include-metrics" in result.output


def test_weekly_retro_basic():
    """Test basic weekly retrospective generation."""
    runner = CliRunner()
    result = runner.invoke(weekly_retro, ["--verbose"])
    assert result.exit_code == 0
    assert "Weekly retrospective generated successfully" in result.output


def test_weekly_retro_with_custom_days():
    """Test weekly retro with custom day range."""
    runner = CliRunner()
    result = runner.invoke(weekly_retro, ["--days", "14", "--verbose"])
    assert result.exit_code == 0


def test_weekly_retro_with_metrics():
    """Test weekly retro with metrics included."""
    runner = CliRunner()
    result = runner.invoke(weekly_retro, ["--include-metrics", "--verbose"])
    assert result.exit_code == 0


def test_weekly_retro_output_formats():
    """Test different output formats."""
    runner = CliRunner()

    # Test markdown format
    result = runner.invoke(weekly_retro, ["--format", "markdown"])
    assert result.exit_code == 0

    # Test JSON format
    result = runner.invoke(weekly_retro, ["--format", "json"])
    assert result.exit_code == 0


def test_weekly_retro_with_output_file():
    """Test weekly retro with output file."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(weekly_retro, ["--output", "retro.md"])
        assert result.exit_code == 0


def test_weekly_retro_end_date():
    """Test weekly retro with specific end date."""
    runner = CliRunner()
    result = runner.invoke(weekly_retro, ["--end-date", "2024-01-15", "--verbose"])
    assert result.exit_code == 0
