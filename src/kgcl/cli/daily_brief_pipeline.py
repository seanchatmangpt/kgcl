"""Daily brief ingestion and feature pipeline helpers."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from typing import TYPE_CHECKING, Any, ClassVar
from uuid import uuid4

from kgcl.hooks.security import ErrorSanitizer
from kgcl.ingestion.config import FeatureConfig, IngestionConfig
from kgcl.ingestion.materializer import FeatureMaterializer
from kgcl.ingestion.models import AppEvent, BrowserVisit, CalendarBlock
from kgcl.signatures.daily_brief import (
    DailyBriefInput,
    DailyBriefModule,
    DailyBriefOutput,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

logger = logging.getLogger(__name__)

EventRecord = AppEvent | BrowserVisit | CalendarBlock


@dataclass(frozen=True)
class DailyBriefEventBatch:
    """Collection of events used to build a daily brief."""

    events: list[EventRecord]
    start_date: datetime
    end_date: datetime
    source_files: tuple[Path, ...] = field(default_factory=tuple)
    synthetic: bool = False

    @property
    def duration_days(self) -> float:
        """Return covered duration in fractional days."""
        delta = self.end_date - self.start_date
        return max(delta.total_seconds() / 86_400, 0.0)

    @property
    def event_count(self) -> int:
        """Return total number of events."""
        return len(self.events)


@dataclass(frozen=True)
class DailyBriefFeatureSet:
    """Materialized features prepared for DSPy generation."""

    input_data: DailyBriefInput
    metadata: dict[str, Any]


@dataclass(frozen=True)
class DailyBriefResult:
    """Generated daily brief artifacts."""

    output: DailyBriefOutput
    metadata: dict[str, Any]

    def to_markdown(self) -> str:
        """Render result as markdown string."""
        highlights = (
            "\n".join(f"- {item}" for item in self.output.highlights)
            or "- No highlights captured"
        )
        patterns = (
            "\n".join(f"- {item}" for item in self.output.patterns)
            or "- No dominant patterns detected"
        )
        recommendations = (
            "\n".join(f"- {item}" for item in self.output.recommendations)
            or "- Maintain current routines; no recommendations generated"
        )

        metadata_lines = [
            f"- Date range: {self.metadata['window']['start']} → {self.metadata['window']['end']}",
            f"- Events analyzed: {self.metadata['event_count']}",
            f"- Synthetic data: {self.metadata['synthetic_data']}",
            f"- LLM enabled: {self.metadata['llm_enabled']}",
            f"- Model: {self.metadata['model']}",
        ]
        metadata_section = "\n".join(metadata_lines)

        top_apps = self.metadata.get("top_apps", [])
        top_domains = self.metadata.get("top_domains", [])
        app_lines = (
            "\n".join(f"- {item['name']}: {item['hours']:.2f}h" for item in top_apps)
            or "- None"
        )
        domain_lines = (
            "\n".join(
                f"- {item['domain']}: {item['visits']} visits" for item in top_domains
            )
            or "- None"
        )

        return "\n".join(
            [
                f"# Daily Brief ({self.metadata['window']['label']})",
                "",
                "## Summary",
                self.output.summary,
                "",
                "## Highlights",
                highlights,
                "",
                "## Patterns",
                patterns,
                "",
                "## Recommendations",
                recommendations,
                "",
                "## Productivity",
                f"- Score: {self.output.productivity_score}/100",
                f"- Focus quality: {self.output.wellbeing_indicators.get('focus_quality', 'unknown')}",
                "",
                "## Metadata",
                metadata_section,
                "",
                "### Top Applications",
                app_lines,
                "",
                "### Top Domains",
                domain_lines,
            ]
        )

    def to_rows(self) -> list[dict[str, str]]:
        """Render result as flat rows for table/CSV output."""
        rows: list[dict[str, str]] = [
            {"section": "Summary", "value": self.output.summary},
            {
                "section": "Productivity Score",
                "value": str(self.output.productivity_score),
            },
        ]
        rows.extend(
            {"section": "Highlight", "value": item} for item in self.output.highlights
        )
        rows.extend(
            {"section": "Pattern", "value": item} for item in self.output.patterns
        )
        rows.extend(
            {"section": "Recommendation", "value": item}
            for item in self.output.recommendations
        )
        for key, value in self.metadata.items():
            if key == "window":
                rows.append(
                    {"section": "Window", "value": f"{value['start']} → {value['end']}"}
                )
            elif key in {"top_apps", "top_domains"}:
                continue
            else:
                rows.append(
                    {"section": key.replace("_", " ").title(), "value": str(value)}
                )
        return rows

    def to_dict(self) -> dict[str, Any]:
        """Render result as structured dictionary suitable for JSON."""
        return {"metadata": self.metadata, "brief": self.output.model_dump()}


class EventLogLoader:
    """Load App/Browser/Calendar events from BatchCollector logs."""

    EVENT_TYPE_MAP: ClassVar[dict[str, type[EventRecord]]] = {
        "AppEvent": AppEvent,
        "BrowserVisit": BrowserVisit,
        "CalendarBlock": CalendarBlock,
    }

    def __init__(
        self, base_path: Path | None = None, sanitizer: ErrorSanitizer | None = None
    ) -> None:
        config = IngestionConfig.default()
        self.base_path = base_path or config.collector.output_directory
        self.sanitizer = sanitizer or ErrorSanitizer()

    def load(self, start_date: datetime, end_date: datetime) -> DailyBriefEventBatch:
        """Load events between the provided dates."""
        normalized_start = self._normalize_timestamp(start_date)
        normalized_end = self._normalize_timestamp(end_date)

        events: list[EventRecord] = []
        source_files: list[Path] = []

        for file_path in self._candidate_files(normalized_start, normalized_end):
            if not file_path.exists():
                continue

            source_files.append(file_path)
            events.extend(self._read_file(file_path, normalized_start, normalized_end))

        if not events:
            synthetic = self._synthetic_events(normalized_start, normalized_end)
            logger.info(
                "No ingestion logs found in %s, generating %d synthetic events",
                self.base_path,
                len(synthetic),
            )
            return DailyBriefEventBatch(
                events=synthetic,
                start_date=normalized_start,
                end_date=normalized_end,
                source_files=tuple(source_files),
                synthetic=True,
            )

        events.sort(key=lambda event: event.timestamp)
        return DailyBriefEventBatch(
            events=events,
            start_date=normalized_start,
            end_date=normalized_end,
            source_files=tuple(source_files),
            synthetic=False,
        )

    def _candidate_files(
        self, start_date: datetime, end_date: datetime
    ) -> Iterable[Path]:
        """Yield JSONL files that may contain data for the window."""
        current = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        limit = end_date + timedelta(days=1)

        while current <= limit:
            filename = f"events_{current.strftime('%Y%m%d')}.jsonl"
            yield self.base_path / filename
            current += timedelta(days=1)

    def _read_file(
        self, file_path: Path, start_date: datetime, end_date: datetime
    ) -> list[EventRecord]:
        """Read events from a JSONL batch file."""
        results: list[EventRecord] = []

        try:
            with file_path.open("r") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    record = json.loads(line)
                    if record.get("type") != "event":
                        continue
                    event_type = record.get("event_type")
                    data = record.get("data", {})
                    model = self.EVENT_TYPE_MAP.get(event_type or "")
                    if model is None:
                        continue
                    event = model(**data)
                    if start_date <= event.timestamp <= end_date:
                        results.append(event)
        except Exception as exc:
            sanitized = self.sanitizer.sanitize(exc)
            message = f"Failed to read {file_path.name}: {sanitized.message}"
            raise RuntimeError(message) from exc

        return results

    def _synthetic_events(
        self, start_date: datetime, end_date: datetime
    ) -> list[EventRecord]:
        """Generate deterministic synthetic events as a fallback."""
        midpoint = start_date + (end_date - start_date) / 2
        focus_start = midpoint.replace(hour=9, minute=0, second=0, microsecond=0)
        focus_end = focus_start + timedelta(hours=2)
        meeting_start = midpoint.replace(hour=13, minute=0, second=0, microsecond=0)
        meeting_end = meeting_start + timedelta(hours=1)

        events: list[EventRecord] = [
            AppEvent(
                event_id=f"app_{uuid4().hex[:8]}",
                timestamp=focus_start,
                app_name="com.microsoft.VSCode",
                app_display_name="VS Code",
                window_title="kgcl/daily_brief.py",
                duration_seconds=120 * 60,
            ),
            AppEvent(
                event_id=f"app_{uuid4().hex[:8]}",
                timestamp=focus_end + timedelta(minutes=30),
                app_name="com.apple.Safari",
                app_display_name="Safari",
                window_title="UNRDF Docs",
                duration_seconds=45 * 60,
            ),
            BrowserVisit(
                event_id=f"browser_{uuid4().hex[:8]}",
                timestamp=focus_end,
                url="https://github.com/sac/kgcl",
                domain="github.com",
                title="KGCL Repository",
                browser_name="Safari",
                duration_seconds=300,
            ),
            CalendarBlock(
                event_id=f"cal_{uuid4().hex[:8]}",
                timestamp=meeting_start,
                end_time=meeting_end,
                title="Daily Planning",
                attendees=["kgcl@example.org"],
                location="Zoom",
            ),
        ]
        events.sort(key=lambda event: event.timestamp)
        return events

    @staticmethod
    def _normalize_timestamp(value: datetime) -> datetime:
        """Return naive UTC timestamp."""
        if value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)


class DailyBriefFeatureBuilder:
    """Build DailyBriefInput instances from ingested events."""

    BREAK_THRESHOLD_MINUTES = 30

    def __init__(self, feature_config: FeatureConfig | None = None) -> None:
        config = feature_config or IngestionConfig.default().feature
        self._materializer = FeatureMaterializer(config)

    def build(self, batch: DailyBriefEventBatch) -> DailyBriefFeatureSet:
        """Create feature set for the provided event batch."""
        materialized = self._materializer.materialize(
            batch.events, batch.start_date, batch.end_date
        )

        total_app_seconds, app_usage = self._aggregate_app_usage(batch.events)
        domain_visits, domain_counts = self._aggregate_domains(batch.events)
        meeting_count, meeting_hours = self._aggregate_meetings(batch.events)
        context_switches = self._count_context_switches(batch.events)
        break_intervals = self._count_breaks(batch.events)

        focus_hours = max(total_app_seconds / 3600 - meeting_hours, 0.0)

        brief_input = DailyBriefInput(
            time_in_app=round(total_app_seconds / 3600, 2),
            domain_visits=domain_visits,
            calendar_busy_hours=round(meeting_hours, 2),
            context_switches=context_switches,
            focus_time=round(focus_hours, 2),
            screen_time=round(total_app_seconds / 3600, 2),
            top_apps={
                name: round(seconds / 3600, 2) for name, seconds in app_usage.items()
            },
            top_domains=domain_counts,
            meeting_count=meeting_count,
            break_intervals=break_intervals,
        )

        metadata = {
            "event_count": batch.event_count,
            "synthetic_data": batch.synthetic,
            "window": {
                "start": batch.start_date.isoformat(),
                "end": batch.end_date.isoformat(),
                "label": f"{batch.start_date.date()} → {batch.end_date.date()}",
            },
            "top_apps": self._format_top_apps(app_usage),
            "top_domains": self._format_top_domains(domain_counts),
            "materialized_features": len(materialized),
            "source_files": [str(path) for path in batch.source_files],
        }

        return DailyBriefFeatureSet(input_data=brief_input, metadata=metadata)

    def _aggregate_app_usage(
        self, events: Sequence[EventRecord]
    ) -> tuple[float, dict[str, float]]:
        total_seconds = 0.0
        app_usage: dict[str, float] = {}

        for event in events:
            if isinstance(event, AppEvent) and event.duration_seconds:
                total_seconds += event.duration_seconds
                app_usage[event.app_display_name or event.app_name] = (
                    app_usage.get(event.app_display_name or event.app_name, 0.0)
                    + event.duration_seconds
                )

        return total_seconds, app_usage

    def _aggregate_domains(
        self, events: Sequence[EventRecord]
    ) -> tuple[int, dict[str, int]]:
        domain_counts: dict[str, int] = {}
        for event in events:
            if isinstance(event, BrowserVisit):
                domain_counts[event.domain] = domain_counts.get(event.domain, 0) + 1
        return sum(domain_counts.values()), domain_counts

    def _aggregate_meetings(self, events: Sequence[EventRecord]) -> tuple[int, float]:
        meeting_count = 0
        total_hours = 0.0
        for event in events:
            if isinstance(event, CalendarBlock):
                meeting_count += 1
                total_hours += (event.end_time - event.timestamp).total_seconds() / 3600
        return meeting_count, total_hours

    def _count_context_switches(self, events: Sequence[EventRecord]) -> int:
        app_events = sorted(
            (e for e in events if isinstance(e, AppEvent)),
            key=lambda evt: evt.timestamp,
        )
        switches = 0
        prev_app: str | None = None
        for event in app_events:
            if prev_app is not None and event.app_name != prev_app:
                switches += 1
            prev_app = event.app_name
        return switches

    def _count_breaks(self, events: Sequence[EventRecord]) -> int:
        sorted_events = sorted(events, key=lambda event: event.timestamp)
        breaks = 0
        for previous, current in pairwise(sorted_events):
            gap_minutes = (current.timestamp - previous.timestamp).total_seconds() / 60
            if gap_minutes >= self.BREAK_THRESHOLD_MINUTES:
                breaks += 1
        return breaks

    def _format_top_apps(self, app_usage: dict[str, float]) -> list[dict[str, Any]]:
        top = sorted(app_usage.items(), key=lambda item: item[1], reverse=True)[:5]
        return [
            {"name": name, "hours": round(seconds / 3600, 2)} for name, seconds in top
        ]

    def _format_top_domains(
        self, domain_counts: dict[str, int]
    ) -> list[dict[str, Any]]:
        top = sorted(domain_counts.items(), key=lambda item: item[1], reverse=True)[:5]
        return [{"domain": name, "visits": count} for name, count in top]


def generate_daily_brief(
    feature_set: DailyBriefFeatureSet, model: str
) -> DailyBriefResult:
    """Generate a daily brief result from the provided feature set."""
    use_llm = model.lower() not in {"fallback", "rule-based"}
    module = DailyBriefModule(use_llm=use_llm)
    output = module.generate(feature_set.input_data)

    metadata = {**feature_set.metadata, "model": model, "llm_enabled": module.use_llm}

    return DailyBriefResult(output=output, metadata=metadata)
