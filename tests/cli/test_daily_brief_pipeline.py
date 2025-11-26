"""Unit tests for daily brief pipeline helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from kgcl.cli.daily_brief_pipeline import (
    DailyBriefEventBatch,
    DailyBriefFeatureBuilder,
    EventLogLoader,
    generate_daily_brief,
)
from kgcl.signatures.daily_brief import DailyBriefInput


@pytest.fixture
def synthetic_batch(tmp_path_factory: pytest.TempPathFactory) -> DailyBriefEventBatch:
    """Provide a synthetic batch from an empty log directory."""
    loader = EventLogLoader(base_path=tmp_path_factory.mktemp("events"))
    start = datetime(2024, 11, 24, tzinfo=UTC)
    end = start + timedelta(days=1)
    return loader.load(start, end)


def test_event_loader_generates_synthetic_when_logs_missing(
    synthetic_batch: DailyBriefEventBatch,
) -> None:
    """Loader should generate deterministic synthetic events when logs are absent."""
    assert synthetic_batch.synthetic
    assert synthetic_batch.event_count > 0
    assert synthetic_batch.start_date.date().isoformat() >= "2024-11-24"


def test_feature_builder_produces_daily_brief_input(
    synthetic_batch: DailyBriefEventBatch,
) -> None:
    """Feature builder should convert events into a fully-typed DailyBriefInput."""
    builder = DailyBriefFeatureBuilder()
    feature_set = builder.build(synthetic_batch)

    assert isinstance(feature_set.input_data, DailyBriefInput)
    assert feature_set.metadata["event_count"] == synthetic_batch.event_count
    assert feature_set.input_data.time_in_app > 0
    assert feature_set.input_data.meeting_count >= 1


def test_generate_daily_brief_returns_markdown_payload(
    synthetic_batch: DailyBriefEventBatch,
) -> None:
    """Pipeline should yield structured outputs and metadata."""
    builder = DailyBriefFeatureBuilder()
    feature_set = builder.build(synthetic_batch)
    result = generate_daily_brief(feature_set, model="fallback")

    payload = result.to_dict()
    assert payload["metadata"]["model"] == "fallback"
    assert "summary" in payload["brief"]
    markdown = result.to_markdown()
    assert markdown.startswith("# Daily Brief")
