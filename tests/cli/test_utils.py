"""Tests for CLI utilities."""

import json
from pathlib import Path

import pytest

from kgcl.cli.utils import (
    OutputFormat,
    export_csv,
    export_json,
    export_tsv,
    get_config_dir,
    get_config_file,
    load_config,
    save_config,
)


def test_output_format_enum():
    """Test OutputFormat enum values."""
    assert OutputFormat.JSON.value == "json"
    assert OutputFormat.CSV.value == "csv"
    assert OutputFormat.TSV.value == "tsv"
    assert OutputFormat.TABLE.value == "table"
    assert OutputFormat.MARKDOWN.value == "markdown"


def test_export_json(tmp_path: Path):
    """Test JSON export."""
    output_file = tmp_path / "test.json"
    data = {"key": "value", "number": 42}

    export_json(data, output_file)

    assert output_file.exists()
    with output_file.open() as f:
        loaded = json.load(f)
    assert loaded == data


def test_export_csv(tmp_path: Path):
    """Test CSV export."""
    output_file = tmp_path / "test.csv"
    data = [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
    ]

    export_csv(data, output_file)

    assert output_file.exists()
    content = output_file.read_text()
    assert "name,age" in content
    assert "Alice,30" in content
    assert "Bob,25" in content


def test_export_csv_empty(tmp_path: Path):
    """Test CSV export with empty data."""
    output_file = tmp_path / "test.csv"
    export_csv([], output_file)
    # Should not create file or should be empty
    assert not output_file.exists() or output_file.stat().st_size == 0


def test_export_tsv(tmp_path: Path):
    """Test TSV export."""
    output_file = tmp_path / "test.tsv"
    data = [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
    ]

    export_tsv(data, output_file)

    assert output_file.exists()
    content = output_file.read_text()
    assert "name\tage" in content
    assert "Alice\t30" in content


def test_get_config_dir():
    """Test config directory creation."""
    config_dir = get_config_dir()
    assert config_dir.exists()
    assert config_dir.is_dir()
    assert str(config_dir).endswith(".config/kgcl")


def test_get_config_file():
    """Test config file path."""
    config_file = get_config_file()
    assert str(config_file).endswith(".config/kgcl/config.json")


def test_save_and_load_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test config save and load."""
    # Use temp directory for config
    config_file = tmp_path / "config.json"
    monkeypatch.setattr("kgcl.cli.utils.get_config_file", lambda *args: config_file)

    test_config = {"key": "value", "number": 42}
    save_config(test_config)

    loaded = load_config()
    assert loaded == test_config


def test_load_config_nonexistent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test loading non-existent config."""
    config_file = tmp_path / "nonexistent.json"
    monkeypatch.setattr("kgcl.cli.utils.get_config_file", lambda *args: config_file)

    config = load_config()
    assert config == {}
