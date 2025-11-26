"""Default service implementations for CLI commands."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rdflib import Graph

from kgcl.cli.core.config_store import CliConfig, CliConfigStore
from kgcl.cli.core.services import (
    ConfigService,
    DailyBriefRequest,
    DspyService,
    IngestionService,
    LinkmlValidator,
    SparqlService,
)
from kgcl.cli.daily_brief_pipeline import (
    DailyBriefEventBatch,
    DailyBriefFeatureBuilder,
    EventLogLoader,
    generate_daily_brief,
)
from kgcl.signatures.daily_brief import DailyBriefModule


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=None)


class DailyBriefIngestionService(IngestionService):
    """Load events/features for the daily brief pipeline."""

    def __init__(self, project_root: Path) -> None:
        self._loader = EventLogLoader()
        self._builder = DailyBriefFeatureBuilder()
        self._project_root = project_root

    def load_daily_brief(self, request: DailyBriefRequest) -> dict:
        start = _parse_dt(request.start_date)
        end = _parse_dt(request.end_date)
        batch: DailyBriefEventBatch = self._loader.load(start, end)
        feature_set = self._builder.build(batch)
        return {"batch": batch, "features": feature_set}


class DailyBriefDspyService(DspyService):
    """Default DSPy-backed daily brief generator."""

    def __init__(self) -> None:
        self._module = DailyBriefModule(use_llm=True)

    def generate_daily_brief(self, features: dict, model: str) -> dict:
        feature_set = features["features"]
        result = generate_daily_brief(feature_set, model)
        payload = {
            "markdown": result.to_markdown(),
            "dict": result.to_dict(),
            "table": result.to_rows(),
            "metadata": result.metadata,
        }
        return payload


@dataclass
class LocalDatasetSparqlService(SparqlService):
    """SPARQL service that queries local Turtle files via rdflib."""

    dataset_path: Path

    def query(
        self, query_text: str, *, limit: int | None = None
    ) -> list[dict[str, str]]:
        # Check if dataset exists, raise FileNotFoundError if not
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {self.dataset_path}")

        graph = Graph()
        graph.parse(self.dataset_path, format=self._guess_format())
        sparql = (
            query_text
            if not limit or "LIMIT" in query_text.upper()
            else f"{query_text}\nLIMIT {limit}"
        )
        results = graph.query(sparql)
        normalized: list[dict[str, str]] = []
        for binding in results.bindings:
            row: dict[str, str] = {}
            for var, value in binding.items():
                row[str(var)] = str(value)
            if row:
                normalized.append(row)
        return normalized

    def _guess_format(self) -> str:
        suffix = self.dataset_path.suffix.lower()
        return (
            "trig" if suffix in {".trig"} else "n3" if suffix in {".n3"} else "turtle"
        )


class JsonConfigService(ConfigService):
    """Config service backed by CliConfigStore."""

    def __init__(self, store: CliConfigStore) -> None:
        self._store = store
        self._snapshot = store.load()

    def snapshot(self) -> dict:
        return self._snapshot.data

    def update(self, new_config: dict) -> None:
        config = CliConfig(new_config)
        self._store.save(config)
        self._snapshot = config


class NoOpLinkmlValidator(LinkmlValidator):
    """Validator that enforces schema via SHACL when configured."""

    def __init__(self, shapes_path: Path | None = None) -> None:
        self._shapes_path = shapes_path

    def validate(self, payload: dict) -> None:
        if self._shapes_path and self._shapes_path.exists():
            # SHACL validation using pyshacl library
            try:
                from pyshacl import validate  # type: ignore[import-not-found]

                data_graph = Graph()
                data_graph.parse(data=json.dumps(payload), format="json-ld")
                shapes_graph = Graph()
                shapes_graph.parse(self._shapes_path, format="turtle")
                r = validate(
                    data_graph=data_graph, shacl_graph=shapes_graph, inference="rdfs"
                )
                conforms, _, results_text = r
                if not conforms:
                    raise ValueError(
                        f"Payload failed LinkML/SHACL validation: {results_text}"
                    )
            except ImportError:
                raise RuntimeError(
                    "pyshacl is required for LinkML validation but is not installed."
                ) from None
