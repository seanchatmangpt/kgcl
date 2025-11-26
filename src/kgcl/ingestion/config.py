"""Configuration management for KGCL ingestion system.

Provides YAML-based configuration with validation and defaults.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class CollectorConfig(BaseModel):
    """Configuration for event collectors."""

    flush_interval_seconds: int = Field(
        default=60, ge=1, description="Time between batch flushes"
    )
    batch_size: int = Field(default=100, ge=1, description="Maximum events per batch")
    output_format: str = Field(
        default="jsonl",
        pattern="^(jsonl|json|parquet)$",
        description="Output file format",
    )
    output_directory: Path = Field(
        default=Path.home() / ".kgcl" / "events", description="Directory for event logs"
    )
    enable_recovery: bool = Field(
        default=True, description="Enable recovery from corrupted logs"
    )
    max_retry_attempts: int = Field(
        default=3, ge=0, description="Maximum retry attempts for failed operations"
    )


class FilterConfig(BaseModel):
    """Configuration for event filtering."""

    excluded_apps: list[str] = Field(
        default_factory=lambda: [
            "com.apple.Spotlight",
            "com.apple.loginwindow",
            "com.apple.systemuiserver",
        ],
        description="Application bundle IDs to exclude",
    )
    excluded_domains: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "0.0.0.0"],
        description="Web domains to exclude",
    )
    min_duration_seconds: float = Field(
        default=1.0, ge=0, description="Minimum event duration to record"
    )
    privacy_mode: bool = Field(
        default=False, description="Enable privacy mode (redact sensitive data)"
    )


class FeatureConfig(BaseModel):
    """Configuration for feature materialization."""

    enabled_features: list[str] = Field(
        default_factory=lambda: [
            "app_usage_time",
            "browser_domain_visits",
            "meeting_count",
            "context_switches",
        ],
        description="Enabled feature templates",
    )
    aggregation_windows: list[str] = Field(
        default_factory=lambda: ["1h", "1d", "1w"],
        description="Time windows for aggregation",
    )
    incremental_updates: bool = Field(
        default=True, description="Enable incremental feature updates"
    )
    cache_size: int = Field(default=1000, ge=0, description="Feature cache size")


class RDFConfig(BaseModel):
    """Configuration for RDF conversion."""

    base_namespace: str = Field(
        default="http://kgcl.example.org/", description="Base RDF namespace URI"
    )
    auto_namespace_assignment: bool = Field(
        default=True, description="Automatically assign namespaces to entities"
    )
    normalize_timestamps: bool = Field(
        default=True, description="Normalize all timestamps to UTC"
    )
    property_cleanup: bool = Field(
        default=True, description="Clean and normalize property names"
    )
    include_schema_version: bool = Field(
        default=True, description="Include schema version in RDF output"
    )


class ValidationConfig(BaseModel):
    """Configuration for SHACL validation."""

    enable_validation: bool = Field(default=True, description="Enable SHACL validation")
    shapes_directory: Path | None = Field(
        default=None, description="Directory containing SHACL shapes"
    )
    strict_mode: bool = Field(
        default=False, description="Fail ingestion on validation errors"
    )
    validation_report_format: str = Field(
        default="turtle",
        pattern="^(turtle|json-ld|nt|xml)$",
        description="Validation report format",
    )


class ServiceConfig(BaseModel):
    """Configuration for ingestion service."""

    enable_http_api: bool = Field(default=True, description="Enable HTTP ingestion API")
    api_host: str = Field(default="127.0.0.1", description="API server host")
    api_port: int = Field(
        default=8080, ge=1024, le=65535, description="API server port"
    )
    transaction_batch_size: int = Field(
        default=50, ge=1, description="Events per transaction"
    )
    enable_hooks: bool = Field(
        default=True, description="Enable pre/post ingestion hooks"
    )
    max_concurrent_requests: int = Field(
        default=10, ge=1, description="Maximum concurrent API requests"
    )


class IngestionConfig(BaseModel):
    """Complete ingestion system configuration."""

    collector: CollectorConfig = Field(default_factory=CollectorConfig)
    filter: FilterConfig = Field(default_factory=FilterConfig)
    feature: FeatureConfig = Field(default_factory=FeatureConfig)
    rdf: RDFConfig = Field(default_factory=RDFConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    service: ServiceConfig = Field(default_factory=ServiceConfig)

    @classmethod
    def from_yaml(cls, path: Path | str) -> "IngestionConfig":
        """Load configuration from YAML file.

        Parameters
        ----------
        path : Path | str
            Path to YAML configuration file

        Returns
        -------
        IngestionConfig
            Loaded and validated configuration

        Raises
        ------
        FileNotFoundError
            If configuration file doesn't exist
        ValueError
            If configuration is invalid
        """
        config_path = Path(path)
        if not config_path.exists():
            msg = f"Configuration file not found: {config_path}"
            raise FileNotFoundError(msg)

        with config_path.open("r") as f:
            data = yaml.safe_load(f)

        return cls(**data)

    def to_yaml(self, path: Path | str) -> None:
        """Save configuration to YAML file.

        Parameters
        ----------
        path : Path | str
            Output path for YAML configuration
        """
        config_path = Path(path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with config_path.open("w") as f:
            yaml.dump(
                self.model_dump(mode="json"),
                f,
                default_flow_style=False,
                sort_keys=False,
            )

    @classmethod
    def default(cls) -> "IngestionConfig":
        """Create default configuration.

        Returns
        -------
        IngestionConfig
            Default configuration instance
        """
        return cls()

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated path.

        Parameters
        ----------
        key_path : str
            Dot-separated configuration key path (e.g., 'collector.batch_size')
        default : Any, optional
            Default value if key not found

        Returns
        -------
        Any
            Configuration value or default
        """
        parts = key_path.split(".")
        current = self.model_dump()

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default

        return current
