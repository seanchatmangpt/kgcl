"""Typed CLI configuration store."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CliConfig:
    """Immutable CLI configuration snapshot."""

    data: dict[str, Any]

    def get(self, key: str, default: Any | None = None) -> Any | None:
        """Retrieve nested config values using dot paths."""
        current: Any = self.data
        for part in key.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current


class CliConfigStore:
    """Responsible for loading and persisting CLI configuration."""

    def __init__(self, config_dir: Path) -> None:
        self._config_dir = config_dir
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._config_file = self._config_dir / "config.json"

    def load(self) -> CliConfig:
        """Load config from disk (empty if missing)."""
        if self._config_file.exists():
            raw = json.loads(self._config_file.read_text(encoding="utf-8"))
        else:
            raw = {}
        return CliConfig(raw)

    def save(self, config: CliConfig) -> None:
        """Persist configuration to disk."""
        self._config_file.write_text(json.dumps(config.data, indent=2, sort_keys=True), encoding="utf-8")
