"""Tests for kgcl.codegen.dspy_config module.

Chicago School TDD tests verifying DSPy configuration behavior.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from kgcl.codegen.dspy_config import configure_dspy, get_configured_lm, is_dspy_configured


@pytest.fixture
def clean_dspy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clean DSPy environment variables before each test."""
    monkeypatch.delenv("DSPY_MODEL", raising=False)
    monkeypatch.delenv("DSPY_API_BASE", raising=False)
    monkeypatch.delenv("DSPY_API_KEY", raising=False)
    monkeypatch.delenv("DSPY_AUTO_CONFIGURE", raising=False)


def test_configure_dspy_with_defaults(clean_dspy_env: None) -> None:
    """Test configure_dspy uses granite4 model by default."""
    with patch("kgcl.codegen.dspy_config.dspy") as mock_dspy:
        mock_lm = MagicMock()
        mock_dspy.LM.return_value = mock_lm

        lm = configure_dspy()

        mock_dspy.LM.assert_called_once_with("ollama/granite4", api_base="http://localhost:11434", api_key="")
        mock_dspy.configure.assert_called_once_with(lm=mock_lm)
        assert lm is mock_lm


def test_configure_dspy_with_custom_model(clean_dspy_env: None) -> None:
    """Test configure_dspy accepts custom model."""
    with patch("kgcl.codegen.dspy_config.dspy") as mock_dspy:
        mock_lm = MagicMock()
        mock_dspy.LM.return_value = mock_lm

        lm = configure_dspy(model="ollama/llama3.2")

        mock_dspy.LM.assert_called_once_with("ollama/llama3.2", api_base="http://localhost:11434", api_key="")
        assert lm is mock_lm


def test_configure_dspy_with_custom_api_base(clean_dspy_env: None) -> None:
    """Test configure_dspy accepts custom API base URL."""
    with patch("kgcl.codegen.dspy_config.dspy") as mock_dspy:
        mock_lm = MagicMock()
        mock_dspy.LM.return_value = mock_lm

        lm = configure_dspy(api_base="http://remote:11434")

        mock_dspy.LM.assert_called_once_with("ollama/granite4", api_base="http://remote:11434", api_key="")
        assert lm is mock_lm


def test_configure_dspy_with_api_key(clean_dspy_env: None) -> None:
    """Test configure_dspy accepts API key."""
    with patch("kgcl.codegen.dspy_config.dspy") as mock_dspy:
        mock_lm = MagicMock()
        mock_dspy.LM.return_value = mock_lm

        lm = configure_dspy(api_key="test-key")

        mock_dspy.LM.assert_called_once_with("ollama/granite4", api_base="http://localhost:11434", api_key="test-key")
        assert lm is mock_lm


def test_configure_dspy_with_env_var_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test configure_dspy reads DSPY_MODEL environment variable."""
    monkeypatch.setenv("DSPY_MODEL", "ollama/custom-model")

    with patch("kgcl.codegen.dspy_config.dspy") as mock_dspy:
        mock_lm = MagicMock()
        mock_dspy.LM.return_value = mock_lm

        lm = configure_dspy()

        mock_dspy.LM.assert_called_once_with("ollama/custom-model", api_base="http://localhost:11434", api_key="")
        assert lm is mock_lm


def test_configure_dspy_with_env_var_api_base(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test configure_dspy reads DSPY_API_BASE environment variable."""
    monkeypatch.setenv("DSPY_API_BASE", "http://custom:8080")

    with patch("kgcl.codegen.dspy_config.dspy") as mock_dspy:
        mock_lm = MagicMock()
        mock_dspy.LM.return_value = mock_lm

        lm = configure_dspy()

        mock_dspy.LM.assert_called_once_with("ollama/granite4", api_base="http://custom:8080", api_key="")
        assert lm is mock_lm


def test_configure_dspy_with_env_var_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test configure_dspy reads DSPY_API_KEY environment variable."""
    monkeypatch.setenv("DSPY_API_KEY", "env-key")

    with patch("kgcl.codegen.dspy_config.dspy") as mock_dspy:
        mock_lm = MagicMock()
        mock_dspy.LM.return_value = mock_lm

        lm = configure_dspy()

        mock_dspy.LM.assert_called_once_with("ollama/granite4", api_base="http://localhost:11434", api_key="env-key")
        assert lm is mock_lm


def test_configure_dspy_parameter_overrides_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test parameter values override environment variables."""
    monkeypatch.setenv("DSPY_MODEL", "ollama/env-model")

    with patch("kgcl.codegen.dspy_config.dspy") as mock_dspy:
        mock_lm = MagicMock()
        mock_dspy.LM.return_value = mock_lm

        lm = configure_dspy(model="ollama/param-model")

        mock_dspy.LM.assert_called_once_with("ollama/param-model", api_base="http://localhost:11434", api_key="")
        assert lm is mock_lm


def test_configure_dspy_with_kwargs(clean_dspy_env: None) -> None:
    """Test configure_dspy passes additional kwargs to dspy.LM."""
    with patch("kgcl.codegen.dspy_config.dspy") as mock_dspy:
        mock_lm = MagicMock()
        mock_dspy.LM.return_value = mock_lm

        lm = configure_dspy(temperature=0.7, max_tokens=1000)

        mock_dspy.LM.assert_called_once_with(
            "ollama/granite4", api_base="http://localhost:11434", api_key="", temperature=0.7, max_tokens=1000
        )
        assert lm is mock_lm


def test_get_configured_lm_when_configured() -> None:
    """Test get_configured_lm returns configured model."""
    with patch("kgcl.codegen.dspy_config.dspy") as mock_dspy:
        mock_lm = MagicMock()
        mock_dspy.settings.lm = mock_lm

        result = get_configured_lm()

        assert result is mock_lm


def test_get_configured_lm_when_not_configured() -> None:
    """Test get_configured_lm returns None when not configured."""
    with patch("kgcl.codegen.dspy_config.dspy") as mock_dspy:
        del mock_dspy.settings.lm

        result = get_configured_lm()

        assert result is None


def test_is_dspy_configured_when_configured() -> None:
    """Test is_dspy_configured returns True when configured."""
    with patch("kgcl.codegen.dspy_config.dspy") as mock_dspy:
        mock_dspy.settings.lm = MagicMock()

        result = is_dspy_configured()

        assert result is True


def test_is_dspy_configured_when_not_configured() -> None:
    """Test is_dspy_configured returns False when not configured."""
    with patch("kgcl.codegen.dspy_config.dspy") as mock_dspy:
        del mock_dspy.settings.lm

        result = is_dspy_configured()

        assert result is False


def test_auto_configure_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test auto-configure is disabled by default."""
    monkeypatch.delenv("DSPY_AUTO_CONFIGURE", raising=False)

    with patch("kgcl.codegen.dspy_config.dspy") as mock_dspy:
        import importlib

        import kgcl.codegen.dspy_config

        importlib.reload(kgcl.codegen.dspy_config)

        mock_dspy.configure.assert_not_called()
