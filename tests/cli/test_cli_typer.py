"""Tests for Typer CLI integration.

Verifies that all CLI commands are properly connected and importable.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from kgcl.cli.app import app


@pytest.fixture
def runner() -> CliRunner:
    """Create CLI test runner.

    Returns
    -------
    CliRunner
        Typer CLI test runner instance
    """
    return CliRunner()


def test_app_imports() -> None:
    """Test that main app imports successfully."""
    from kgcl.cli import app as app_module

    assert hasattr(app_module, "app")
    assert app is not None


def test_app_help(runner: CliRunner) -> None:
    """Test main app help command.

    Parameters
    ----------
    runner : CliRunner
        CLI test runner
    """
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "KGCL" in result.stdout
    assert "engine" in result.stdout
    assert "store" in result.stdout
    assert "yawl" in result.stdout


def test_app_version(runner: CliRunner) -> None:
    """Test version command.

    Parameters
    ----------
    runner : CliRunner
        CLI test runner
    """
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "2.0.0" in result.stdout


def test_engine_help(runner: CliRunner) -> None:
    """Test engine subcommand help.

    Parameters
    ----------
    runner : CliRunner
        CLI test runner
    """
    result = runner.invoke(app, ["engine", "--help"])
    assert result.exit_code == 0
    assert "HybridEngine" in result.stdout


def test_store_help(runner: CliRunner) -> None:
    """Test store subcommand help.

    Parameters
    ----------
    runner : CliRunner
        CLI test runner
    """
    result = runner.invoke(app, ["store", "--help"])
    assert result.exit_code == 0
    assert "Triple store" in result.stdout


def test_yawl_help(runner: CliRunner) -> None:
    """Test YAWL subcommand help.

    Parameters
    ----------
    runner : CliRunner
        CLI test runner
    """
    result = runner.invoke(app, ["yawl", "--help"])
    assert result.exit_code == 0
    assert "YAWL" in result.stdout


def test_yawl_spec_help(runner: CliRunner) -> None:
    """Test YAWL spec subcommand help.

    Parameters
    ----------
    runner : CliRunner
        CLI test runner
    """
    result = runner.invoke(app, ["yawl", "spec", "--help"])
    assert result.exit_code == 0
    assert "Specification" in result.stdout


def test_yawl_case_help(runner: CliRunner) -> None:
    """Test YAWL case subcommand help.

    Parameters
    ----------
    runner : CliRunner
        CLI test runner
    """
    result = runner.invoke(app, ["yawl", "case", "--help"])
    assert result.exit_code == 0
    assert "Case" in result.stdout


def test_codegen_help(runner: CliRunner) -> None:
    """Test codegen subcommand help.

    Parameters
    ----------
    runner : CliRunner
        CLI test runner
    """
    result = runner.invoke(app, ["codegen", "--help"])
    assert result.exit_code == 0
    assert "Code generation" in result.stdout


def test_proj_help(runner: CliRunner) -> None:
    """Test projection subcommand help.

    Parameters
    ----------
    runner : CliRunner
        CLI test runner
    """
    result = runner.invoke(app, ["proj", "--help"])
    assert result.exit_code == 0
    assert "Projection" in result.stdout or "template" in result.stdout


def test_all_commands_importable() -> None:
    """Test that all CLI command modules import successfully."""
    from kgcl.cli import engine, physics, store, system, task, yawl
    from kgcl.codegen import cli as codegen_cli
    from kgcl.observability import cli as obs_cli
    from kgcl.projection import cli as proj_cli

    assert engine.engine is not None
    assert physics.physics is not None
    assert store.store is not None
    assert system.system is not None
    assert task.task is not None
    assert yawl.yawl is not None
    assert codegen_cli.codegen is not None
    assert obs_cli.health is not None
    assert proj_cli.proj is not None
