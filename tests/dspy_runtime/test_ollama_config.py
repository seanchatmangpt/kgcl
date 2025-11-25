"""
Unit tests for Ollama LM configuration.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from kgcl.dspy_runtime.ollama_config import (
    OllamaConfig,
    OllamaLM,
    configure_ollama,
    health_check,
    DSPY_AVAILABLE
)


class TestOllamaConfig:
    """Test OllamaConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = OllamaConfig()

        assert config.model == "llama3.1"
        assert config.base_url == "http://localhost:11434"
        assert config.temperature == 0.7
        assert config.max_tokens == 2048
        assert config.timeout == 30

    def test_from_env(self):
        """Test loading configuration from environment."""
        with patch.dict(os.environ, {
            "OLLAMA_MODEL": "llama2",
            "OLLAMA_BASE_URL": "http://remote:11434",
            "OLLAMA_TEMPERATURE": "0.5",
            "OLLAMA_MAX_TOKENS": "1024",
            "OLLAMA_TIMEOUT": "60"
        }):
            config = OllamaConfig.from_env()

            assert config.model == "llama2"
            assert config.base_url == "http://remote:11434"
            assert config.temperature == 0.5
            assert config.max_tokens == 1024
            assert config.timeout == 60

    def test_from_env_with_defaults(self):
        """Test loading with missing environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            config = OllamaConfig.from_env()

            assert config.model == "llama3.1"
            assert config.base_url == "http://localhost:11434"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = OllamaConfig(model="test-model", temperature=0.8)
        config_dict = config.to_dict()

        assert config_dict["model"] == "test-model"
        assert config_dict["temperature"] == 0.8
        assert "base_url" in config_dict


class TestOllamaLM:
    """Test OllamaLM class."""

    @pytest.mark.skipif(not DSPY_AVAILABLE, reason="DSPy not available")
    def test_init_with_config(self):
        """Test initialization with custom config."""
        config = OllamaConfig(model="custom-model")
        lm = OllamaLM(config)

        assert lm.config.model == "custom-model"
        assert not lm._initialized

    @pytest.mark.skipif(not DSPY_AVAILABLE, reason="DSPy not available")
    def test_init_without_config(self):
        """Test initialization without config (loads from env)."""
        with patch.dict(os.environ, {"OLLAMA_MODEL": "env-model"}):
            lm = OllamaLM()
            assert lm.config.model == "env-model"

    def test_is_available_success(self):
        """Test Ollama availability check - success."""
        if not DSPY_AVAILABLE:
            pytest.skip("DSPy not available")
        lm = OllamaLM()

        mock_response = Mock()
        mock_response.status_code = 200

        with patch("requests.get", return_value=mock_response):
            assert lm.is_available() is True

    def test_is_available_failure(self):
        """Test Ollama availability check - failure."""
        if not DSPY_AVAILABLE:
            pytest.skip("DSPy not available")
        lm = OllamaLM()

        with patch("requests.get", side_effect=requests.ConnectionError()):
            assert lm.is_available() is False

    def test_is_model_available_success(self):
        """Test model availability check - success."""
        if not DSPY_AVAILABLE:
            pytest.skip("DSPy not available")
        lm = OllamaLM(OllamaConfig(model="llama3.1"))

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3.1:latest"},
                {"name": "llama2:latest"}
            ]
        }

        with patch("requests.get", return_value=mock_response):
            assert lm.is_model_available() is True

    def test_is_model_available_not_found(self):
        """Test model availability check - model not found."""
        if not DSPY_AVAILABLE:
            pytest.skip("DSPy not available")
        lm = OllamaLM(OllamaConfig(model="nonexistent"))

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "llama3.1:latest"}]
        }

        with patch("requests.get", return_value=mock_response):
            assert lm.is_model_available() is False

    def test_list_models(self):
        """Test listing models."""
        if not DSPY_AVAILABLE:
            pytest.skip("DSPy not available")
        lm = OllamaLM()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3.1", "size": 1000000},
                {"name": "llama2", "size": 2000000}
            ]
        }

        with patch("requests.get", return_value=mock_response):
            models = lm.list_models()
            assert len(models) == 2
            assert models[0]["name"] == "llama3.1"

    def test_list_models_unavailable(self):
        """Test listing models when Ollama unavailable."""
        if not DSPY_AVAILABLE:
            pytest.skip("DSPy not available")
        lm = OllamaLM()

        with patch("requests.get", side_effect=requests.ConnectionError()):
            with pytest.raises(ConnectionError):
                lm.list_models()

    def test_get_model_info(self):
        """Test getting model info."""
        if not DSPY_AVAILABLE:
            pytest.skip("DSPy not available")
        lm = OllamaLM()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "llama3.1", "details": {}}

        with patch("requests.post", return_value=mock_response):
            info = lm.get_model_info("llama3.1")
            assert info["name"] == "llama3.1"

    def test_get_model_info_not_found(self):
        """Test getting info for nonexistent model."""
        if not DSPY_AVAILABLE:
            pytest.skip("DSPy not available")
        lm = OllamaLM()

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(ValueError, match="Model not found"):
                lm.get_model_info("nonexistent")


class TestHelperFunctions:
    """Test helper functions."""

    def test_health_check_dspy_unavailable(self):
        """Test health check when DSPy not available."""
        with patch("kgcl.dspy_runtime.ollama_config.DSPY_AVAILABLE", False), \
             patch("kgcl.dspy_runtime.ollama_config.OllamaLM") as mock_lm_class:
            # Mock OllamaLM to avoid initialization when DSPy unavailable
            mock_lm = Mock()
            mock_lm.is_available.return_value = False
            mock_lm_class.return_value = mock_lm

            result = health_check()
            assert result["dspy_available"] is False

    def test_health_check_ollama_unavailable(self):
        """Test health check when Ollama unavailable."""
        if not DSPY_AVAILABLE:
            pytest.skip("DSPy not available")
        with patch("requests.get", side_effect=requests.ConnectionError()):
            result = health_check()

            assert result["status"] == "unhealthy"
            assert result["ollama_available"] is False

    def test_health_check_model_unavailable(self):
        """Test health check when model unavailable."""
        if not DSPY_AVAILABLE:
            pytest.skip("DSPy not available")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": []}

        with patch("requests.get", return_value=mock_response):
            result = health_check()

            assert result["status"] == "degraded"
            assert result["ollama_available"] is True
            assert result["model_available"] is False

    def test_health_check_healthy(self):
        """Test health check when all systems healthy."""
        if not DSPY_AVAILABLE:
            pytest.skip("DSPy not available")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "llama3.1:latest"}]
        }

        with patch("requests.get", return_value=mock_response):
            result = health_check()

            assert result["status"] == "healthy"
            assert result["ollama_available"] is True
            assert result["model_available"] is True
