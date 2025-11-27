"""Integration tests for kgcl system CLI commands.

Chicago School TDD: Real CLI invocations, real component checks.
No mocking. Tests verify actual system dependencies.
"""

from __future__ import annotations

from click.testing import CliRunner

from kgcl.cli.app import app


class TestSystemCheck:
    """Integration tests for 'kgcl system check' command."""

    def test_system_check_shows_all_components(self) -> None:
        """Check displays all system components.

        Verifies:
        - Python version shown
        - PyOxigraph status shown
        - EYE reasoner status shown
        - HybridEngine status shown
        """
        runner = CliRunner()
        result = runner.invoke(app, ["system", "check"])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        # Should check Python
        assert "Python" in result.output
        # Should check PyOxigraph
        assert "PyOxigraph" in result.output
        # Should check EYE
        assert "EYE" in result.output
        # Should check HybridEngine
        assert "HybridEngine" in result.output

    def test_system_check_all_components_ready(self) -> None:
        """Check confirms all components are available.

        This is critical - proves the system is properly configured.
        """
        runner = CliRunner()
        result = runner.invoke(app, ["system", "check"])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        # All components should have checkmarks
        assert result.output.count("✓") >= 4
        # Should show success message
        assert "ready" in result.output.lower() or "All systems" in result.output


class TestSystemInfo:
    """Integration tests for 'kgcl system info' command."""

    def test_system_info_shows_architecture(self) -> None:
        """Info displays architecture explanation.

        Verifies:
        - PyOxigraph role explained
        - EYE role explained
        - Python role explained
        """
        runner = CliRunner()
        result = runner.invoke(app, ["system", "info"])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        # Should explain components
        assert "PyOxigraph" in result.output
        assert "EYE" in result.output
        # Should explain architecture metaphor
        assert "Matter" in result.output or "State" in result.output.lower()
        assert "Physics" in result.output or "Force" in result.output

    def test_system_info_shows_workflow_patterns(self) -> None:
        """Info displays supported workflow control patterns.

        Verifies WCP documentation.
        """
        runner = CliRunner()
        result = runner.invoke(app, ["system", "info"])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        # Should list WCP patterns
        assert "WCP" in result.output or "Workflow" in result.output
        # Should show basic patterns
        assert "Sequence" in result.output
