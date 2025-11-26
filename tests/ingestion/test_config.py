"""Tests for ingestion configuration."""

import tempfile
from pathlib import Path

import pytest

from kgcl.ingestion.config import (
    CollectorConfig,
    FeatureConfig,
    FilterConfig,
    IngestionConfig,
    RDFConfig,
    ServiceConfig,
    ValidationConfig,
)


class TestCollectorConfig:
    """Tests for CollectorConfig."""

    def test_default_config(self):
        """Test default collector configuration."""
        config = CollectorConfig()

        assert config.flush_interval_seconds == 60
        assert config.batch_size == 100
        assert config.output_format == "jsonl"
        assert config.enable_recovery is True

    def test_custom_config(self):
        """Test custom collector configuration."""
        config = CollectorConfig(
            flush_interval_seconds=30, batch_size=50, output_format="json"
        )

        assert config.flush_interval_seconds == 30
        assert config.batch_size == 50

    def test_invalid_batch_size(self):
        """Test that invalid batch size is rejected."""
        with pytest.raises(ValueError):
            CollectorConfig(batch_size=0)


class TestFilterConfig:
    """Tests for FilterConfig."""

    def test_default_filters(self):
        """Test default filter configuration."""
        config = FilterConfig()

        assert "com.apple.Spotlight" in config.excluded_apps
        assert "localhost" in config.excluded_domains
        assert config.min_duration_seconds == 1.0

    def test_custom_exclusions(self):
        """Test custom exclusion lists."""
        config = FilterConfig(
            excluded_apps=["com.test.app"], excluded_domains=["test.local"]
        )

        assert config.excluded_apps == ["com.test.app"]
        assert config.excluded_domains == ["test.local"]

    def test_privacy_mode(self):
        """Test privacy mode flag."""
        config = FilterConfig(privacy_mode=True)
        assert config.privacy_mode is True


class TestFeatureConfig:
    """Tests for FeatureConfig."""

    def test_default_features(self):
        """Test default feature configuration."""
        config = FeatureConfig()

        assert "app_usage_time" in config.enabled_features
        assert "1h" in config.aggregation_windows
        assert config.incremental_updates is True

    def test_custom_features(self):
        """Test custom feature configuration."""
        config = FeatureConfig(
            enabled_features=["custom_feature"], aggregation_windows=["30m", "2h"]
        )

        assert config.enabled_features == ["custom_feature"]
        assert "30m" in config.aggregation_windows


class TestRDFConfig:
    """Tests for RDFConfig."""

    def test_default_rdf_config(self):
        """Test default RDF configuration."""
        config = RDFConfig()

        assert config.base_namespace == "http://kgcl.example.org/"
        assert config.auto_namespace_assignment is True
        assert config.normalize_timestamps is True

    def test_custom_namespace(self):
        """Test custom namespace configuration."""
        config = RDFConfig(base_namespace="http://custom.example.com/")

        assert config.base_namespace == "http://custom.example.com/"


class TestValidationConfig:
    """Tests for ValidationConfig."""

    def test_default_validation(self):
        """Test default validation configuration."""
        config = ValidationConfig()

        assert config.enable_validation is True
        assert config.strict_mode is False
        assert config.validation_report_format == "turtle"

    def test_strict_mode(self):
        """Test strict validation mode."""
        config = ValidationConfig(strict_mode=True)
        assert config.strict_mode is True


class TestServiceConfig:
    """Tests for ServiceConfig."""

    def test_default_service_config(self):
        """Test default service configuration."""
        config = ServiceConfig()

        assert config.enable_http_api is True
        assert config.api_host == "127.0.0.1"
        assert config.api_port == 8080
        assert config.enable_hooks is True

    def test_custom_api_settings(self):
        """Test custom API settings."""
        config = ServiceConfig(api_host="0.0.0.0", api_port=9000)

        assert config.api_host == "0.0.0.0"
        assert config.api_port == 9000

    def test_invalid_port(self):
        """Test that invalid port is rejected."""
        with pytest.raises(ValueError):
            ServiceConfig(api_port=100)


class TestIngestionConfig:
    """Tests for complete IngestionConfig."""

    def test_default_config(self):
        """Test default complete configuration."""
        config = IngestionConfig.default()

        assert config.collector.batch_size == 100
        assert config.filter.privacy_mode is False
        assert config.feature.incremental_updates is True
        assert config.service.enable_http_api is True

    def test_nested_config(self):
        """Test nested configuration."""
        config = IngestionConfig(
            collector=CollectorConfig(batch_size=50),
            filter=FilterConfig(privacy_mode=True),
        )

        assert config.collector.batch_size == 50
        assert config.filter.privacy_mode is True

    def test_yaml_roundtrip(self):
        """Test saving and loading YAML configuration."""
        config = IngestionConfig(
            collector=CollectorConfig(batch_size=75),
            filter=FilterConfig(min_duration_seconds=2.0),
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            temp_path = Path(f.name)

        try:
            # Save to YAML
            config.to_yaml(temp_path)

            # Load back
            loaded = IngestionConfig.from_yaml(temp_path)

            assert loaded.collector.batch_size == 75
            assert loaded.filter.min_duration_seconds == 2.0

        finally:
            temp_path.unlink()

    def test_get_nested_value(self):
        """Test getting nested configuration value."""
        config = IngestionConfig.default()

        value = config.get("collector.batch_size")
        assert value == 100

        value = config.get("filter.privacy_mode")
        assert value is False

    def test_get_with_default(self):
        """Test getting value with default."""
        config = IngestionConfig.default()

        value = config.get("nonexistent.key", "default_value")
        assert value == "default_value"

    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            IngestionConfig.from_yaml("/nonexistent/config.yaml")

    def test_export_creates_directory(self):
        """Test that export creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nested" / "config.yaml"

            config = IngestionConfig.default()
            config.to_yaml(config_path)

            assert config_path.exists()
            assert config_path.parent.exists()
