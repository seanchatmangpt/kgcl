"""Integration tests for kgcl physics CLI commands.

Chicago School TDD: Real CLI invocations, real N3 physics rules.
No mocking. Tests verify actual N3 syntax and EYE validation.
"""

from __future__ import annotations

from click.testing import CliRunner

from kgcl.cli.app import app


class TestPhysicsShow:
    """Integration tests for 'kgcl physics show' command."""

    def test_physics_show_displays_n3_rules(self) -> None:
        """Show displays N3 physics rules.

        Verifies:
        - N3_PHYSICS constant is accessible
        - Output contains N3 syntax
        - Laws are documented
        """
        runner = CliRunner()
        result = runner.invoke(app, ["physics", "show"])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        # Should show N3 prefix declarations
        assert "@prefix" in result.output
        # Should show kgc namespace
        assert "kgc:" in result.output or "https://kgc.org/ns/" in result.output
        # Should show rule syntax (implications)
        assert "=>" in result.output
        # Should show LAW comments
        assert "LAW" in result.output

    def test_physics_show_contains_workflow_patterns(self) -> None:
        """Show includes workflow control pattern laws.

        Verifies WCP implementations are present.
        """
        runner = CliRunner()
        result = runner.invoke(app, ["physics", "show"])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        # Should have sequence law
        assert "Sequence" in result.output or "SEQUENCE" in result.output
        # Should have AND-split
        assert "AND-SPLIT" in result.output or "ControlTypeAnd" in result.output
        # Should have XOR-split
        assert "XOR-SPLIT" in result.output or "ControlTypeXor" in result.output


class TestPhysicsValidate:
    """Integration tests for 'kgcl physics validate' command."""

    def test_physics_validate_rules_are_valid_n3(self) -> None:
        """Validate confirms rules are syntactically valid N3.

        Verifies EYE reasoner can parse the physics rules.
        This is a critical integration test - proves rules work with EYE.
        """
        runner = CliRunner()
        result = runner.invoke(app, ["physics", "validate"])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        # Should show success message
        assert "valid" in result.output.lower()
        assert "✓" in result.output
