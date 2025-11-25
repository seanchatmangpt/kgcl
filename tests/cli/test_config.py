"""Tests for config CLI command."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from kgcl.cli.config import DEFAULT_CONFIG, config


@pytest.fixture
def isolated_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Create isolated config directory for testing."""
    config_dir = tmp_path / ".config" / "kgcl"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "config.json"

    monkeypatch.setattr("kgcl.cli.utils.get_config_dir", lambda: config_dir)
    monkeypatch.setattr("kgcl.cli.utils.get_config_file", lambda *args: config_file)

    return config_file


def test_config_help():
    """Test config help output."""
    runner = CliRunner()
    result = runner.invoke(config, ["--help"])
    assert result.exit_code == 0
    assert "Manage KGCL configuration" in result.output


def test_config_init(isolated_config: Path):
    """Test config initialization."""
    runner = CliRunner()
    result = runner.invoke(config, ["init"])
    assert result.exit_code == 0
    assert "Configuration initialized" in result.output
    assert isolated_config.exists()


def test_config_show(isolated_config: Path):
    """Test showing configuration."""
    runner = CliRunner()

    # Initialize first
    runner.invoke(config, ["init"])

    # Show config
    result = runner.invoke(config, ["show"])
    assert result.exit_code == 0


def test_config_show_table_format(isolated_config: Path):
    """Test showing config in table format."""
    runner = CliRunner()
    runner.invoke(config, ["init"])

    result = runner.invoke(config, ["show", "--format", "table"])
    assert result.exit_code == 0


def test_config_set_get(isolated_config: Path):
    """Test setting and getting config values."""
    runner = CliRunner()
    runner.invoke(config, ["init"])

    # Set value
    result = runner.invoke(config, ["set", "test_key", "test_value"])
    assert result.exit_code == 0
    assert "Set test_key" in result.output

    # Get value
    result = runner.invoke(config, ["get", "test_key"])
    assert result.exit_code == 0
    assert "test_value" in result.output


def test_config_exclude_add(isolated_config: Path):
    """Test adding exclusions."""
    runner = CliRunner()
    runner.invoke(config, ["init"])

    # Add file exclusion
    result = runner.invoke(config, ["exclude", "add", "--file", "*.backup"])
    assert result.exit_code == 0
    assert "Added file exclusion" in result.output

    # Add directory exclusion
    result = runner.invoke(config, ["exclude", "add", "--directory", "build"])
    assert result.exit_code == 0
    assert "Added directory exclusion" in result.output


def test_config_exclude_list(isolated_config: Path):
    """Test listing exclusions."""
    runner = CliRunner()
    runner.invoke(config, ["init"])

    result = runner.invoke(config, ["exclude", "list"])
    assert result.exit_code == 0
    assert "exclusions" in result.output.lower()


def test_config_exclude_remove(isolated_config: Path):
    """Test removing exclusions."""
    runner = CliRunner()
    runner.invoke(config, ["init"])

    # Add then remove
    runner.invoke(config, ["exclude", "add", "--file", "*.test"])
    result = runner.invoke(config, ["exclude", "remove", "--file", "*.test"])
    assert result.exit_code == 0
    assert "Removed file exclusion" in result.output


def test_config_capability_enable(isolated_config: Path):
    """Test enabling capabilities."""
    runner = CliRunner()
    runner.invoke(config, ["init"])

    result = runner.invoke(config, ["capability", "enable", "telemetry"])
    assert result.exit_code == 0
    assert "Enabled capability" in result.output


def test_config_capability_disable(isolated_config: Path):
    """Test disabling capabilities."""
    runner = CliRunner()
    runner.invoke(config, ["init"])

    result = runner.invoke(config, ["capability", "disable", "auto_updates"])
    assert result.exit_code == 0
    assert "Disabled capability" in result.output


def test_config_capability_list(isolated_config: Path):
    """Test listing capabilities."""
    runner = CliRunner()
    runner.invoke(config, ["init"])

    result = runner.invoke(config, ["capability", "list"])
    assert result.exit_code == 0


def test_config_reset(isolated_config: Path):
    """Test resetting configuration."""
    runner = CliRunner()
    runner.invoke(config, ["init"])

    # Modify config
    runner.invoke(config, ["set", "test_key", "test_value"])

    # Reset (with confirmation)
    result = runner.invoke(config, ["reset"], input="y\n")
    assert result.exit_code == 0


def test_default_config_structure():
    """Test default config has expected structure."""
    assert "exclusions" in DEFAULT_CONFIG
    assert "capabilities" in DEFAULT_CONFIG
    assert "settings" in DEFAULT_CONFIG

    assert "files" in DEFAULT_CONFIG["exclusions"]
    assert "directories" in DEFAULT_CONFIG["exclusions"]
    assert "patterns" in DEFAULT_CONFIG["exclusions"]

    assert isinstance(DEFAULT_CONFIG["capabilities"], dict)
    assert isinstance(DEFAULT_CONFIG["settings"], dict)
