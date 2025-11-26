"""Ingestion service with HTTP API and transaction batching.

Provides the main ingestion interface for KGCL events.
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kgcl.ingestion.collectors.batch import BatchCollector
from kgcl.ingestion.config import IngestionConfig
from kgcl.ingestion.converters import RDFConverter
from kgcl.ingestion.materializer import FeatureMaterializer
from kgcl.ingestion.models import AppEvent, BrowserVisit, CalendarBlock, EventBatch

logger = logging.getLogger(__name__)


class IngestionHook:
    """Hook for pre/post ingestion processing."""

    def __init__(self, name: str, handler: Callable[[list[AppEvent | BrowserVisit | CalendarBlock]], Any]) -> None:
        """Initialize hook.

        Parameters
        ----------
        name : str
            Hook name
        handler : Callable
            Hook handler function
        """
        self.name = name
        self.handler = handler

    async def execute(self, events: list[AppEvent | BrowserVisit | CalendarBlock]) -> Any:
        """Execute hook handler.

        Parameters
        ----------
        events : list[AppEvent | BrowserVisit | CalendarBlock]
            Events to process

        Returns
        -------
        Any
            Hook result
        """
        if asyncio.iscoroutinefunction(self.handler):
            return await self.handler(events)
        return self.handler(events)


class IngestionService:
    """Main ingestion service.

    Features:
    - HTTP API for event ingestion
    - Transaction batching for performance
    - Pre/post ingestion hooks
    - RDF conversion integration
    - Feature materialization
    - SHACL validation
    """

    def __init__(self, config: IngestionConfig | None = None) -> None:
        """Initialize ingestion service.

        Parameters
        ----------
        config : IngestionConfig, optional
            Service configuration, uses defaults if None
        """
        self.config = config or IngestionConfig.default()

        # Initialize components
        self.collector = BatchCollector(self.config.collector)
        self.rdf_converter = RDFConverter(self.config.rdf)
        self.materializer = FeatureMaterializer(self.config.feature)

        # Hooks
        self._pre_hooks: list[IngestionHook] = []
        self._post_hooks: list[IngestionHook] = []

        # Statistics
        self._stats = {
            "total_events": 0,
            "total_batches": 0,
            "failed_events": 0,
            "validation_errors": 0,
            "last_ingestion": None,
        }

    def ingest_event(self, event: AppEvent | BrowserVisit | CalendarBlock) -> dict[str, Any]:
        """Ingest single event.

        Parameters
        ----------
        event : AppEvent | BrowserVisit | CalendarBlock
            Event to ingest

        Returns
        -------
        dict[str, Any]
            Ingestion result
        """
        return asyncio.run(self.ingest_event_async(event))

    async def ingest_event_async(self, event: AppEvent | BrowserVisit | CalendarBlock) -> dict[str, Any]:
        """Ingest single event asynchronously.

        Parameters
        ----------
        event : AppEvent | BrowserVisit | CalendarBlock
            Event to ingest

        Returns
        -------
        dict[str, Any]
            Ingestion result with status and metadata
        """
        try:
            # Execute pre-hooks
            if self.config.service.enable_hooks:
                await self._execute_hooks(self._pre_hooks, [event])

            # Apply filters
            if self._should_filter_event(event):
                return {"status": "filtered", "event_id": event.event_id, "reason": "Event filtered by configuration"}

            # Add to collector
            self.collector.add_event(event)

            # Execute post-hooks
            if self.config.service.enable_hooks:
                await self._execute_hooks(self._post_hooks, [event])

            # Update stats
            self._stats["total_events"] += 1
            self._stats["last_ingestion"] = datetime.now(UTC).replace(tzinfo=None).isoformat()

            return {"status": "success", "event_id": event.event_id, "event_type": type(event).__name__}

        except Exception as e:
            self._stats["failed_events"] += 1
            return {"status": "error", "event_id": event.event_id, "error": str(e)}

    def ingest_batch(self, batch: EventBatch | list[AppEvent | BrowserVisit | CalendarBlock]) -> dict[str, Any]:
        """Ingest batch of events.

        Parameters
        ----------
        batch : EventBatch | list[AppEvent | BrowserVisit | CalendarBlock]
            Batch or list of events

        Returns
        -------
        dict[str, Any]
            Batch ingestion result
        """
        return asyncio.run(self.ingest_batch_async(batch))

    async def ingest_batch_async(
        self, batch: EventBatch | list[AppEvent | BrowserVisit | CalendarBlock]
    ) -> dict[str, Any]:
        """Ingest batch of events asynchronously.

        Parameters
        ----------
        batch : EventBatch | list[AppEvent | BrowserVisit | CalendarBlock]
            Batch or list of events

        Returns
        -------
        dict[str, Any]
            Batch ingestion result
        """
        # Extract events from batch
        if isinstance(batch, EventBatch):
            events = batch.events
            batch_id = batch.batch_id
        else:
            events = batch
            batch_id = f"batch_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"

        try:
            # Execute pre-hooks
            if self.config.service.enable_hooks:
                await self._execute_hooks(self._pre_hooks, events)

            # Filter events
            filtered_events = [e for e in events if not self._should_filter_event(e)]

            # Process in transaction batches
            results = []
            batch_size = self.config.service.transaction_batch_size

            for i in range(0, len(filtered_events), batch_size):
                transaction_batch = filtered_events[i : i + batch_size]
                result = await self._process_transaction_batch(transaction_batch)
                results.append(result)

            # Execute post-hooks
            if self.config.service.enable_hooks:
                await self._execute_hooks(self._post_hooks, filtered_events)

            # Update stats
            self._stats["total_events"] += len(filtered_events)
            self._stats["total_batches"] += 1
            self._stats["last_ingestion"] = datetime.now(UTC).replace(tzinfo=None).isoformat()

            return {
                "status": "success",
                "batch_id": batch_id,
                "total_events": len(events),
                "processed_events": len(filtered_events),
                "filtered_events": len(events) - len(filtered_events),
                "transactions": len(results),
            }

        except Exception as e:
            self._stats["failed_events"] += len(events)
            return {"status": "error", "batch_id": batch_id, "error": str(e)}

    async def _process_transaction_batch(self, events: list[AppEvent | BrowserVisit | CalendarBlock]) -> dict[str, Any]:
        """Process events in a transaction.

        Parameters
        ----------
        events : list[AppEvent | BrowserVisit | CalendarBlock]
            Events to process

        Returns
        -------
        dict[str, Any]
            Transaction result
        """
        # Add to collector
        self.collector.add_events(events)

        # Convert to RDF if needed
        rdf_graph = None
        if self.config.rdf.base_namespace:
            rdf_graph = self.rdf_converter.convert_batch(events)

        # Materialize features if enabled
        features = []
        if self.config.feature.enabled_features:
            from datetime import timedelta

            now = datetime.now(UTC).replace(tzinfo=None)
            window_start = now.replace(minute=0, second=0, microsecond=0)
            window_end = window_start + timedelta(hours=1)
            features = self.materializer.materialize(events, window_start, window_end)

        return {
            "event_count": len(events),
            "rdf_triples": len(rdf_graph) if rdf_graph else 0,
            "features_computed": len(features),
        }

    def _should_filter_event(self, event: AppEvent | BrowserVisit | CalendarBlock) -> bool:
        """Check if event should be filtered.

        Parameters
        ----------
        event : AppEvent | BrowserVisit | CalendarBlock
            Event to check

        Returns
        -------
        bool
            True if event should be filtered
        """
        # Filter by app name
        if isinstance(event, AppEvent):
            if event.app_name in self.config.filter.excluded_apps:
                return True
            if event.duration_seconds is not None and event.duration_seconds < self.config.filter.min_duration_seconds:
                return True

        # Filter by domain
        if isinstance(event, BrowserVisit):
            if event.domain in self.config.filter.excluded_domains:
                return True
            if event.duration_seconds is not None and event.duration_seconds < self.config.filter.min_duration_seconds:
                return True

        return False

    async def _execute_hooks(
        self, hooks: list[IngestionHook], events: list[AppEvent | BrowserVisit | CalendarBlock]
    ) -> None:
        """Execute list of hooks.

        Parameters
        ----------
        hooks : list[IngestionHook]
            Hooks to execute
        events : list[AppEvent | BrowserVisit | CalendarBlock]
            Events to pass to hooks
        """
        for hook in hooks:
            try:
                await hook.execute(events)
            except Exception as e:
                # Log error but don't fail ingestion
                logger.error(
                    "Hook execution failed",
                    extra={"hook_name": hook.name, "error": str(e), "event_count": len(events)},
                    exc_info=True,
                )

    def register_pre_hook(
        self, name: str, handler: Callable[[list[AppEvent | BrowserVisit | CalendarBlock]], Any]
    ) -> None:
        """Register pre-ingestion hook.

        Parameters
        ----------
        name : str
            Hook name
        handler : Callable
            Hook handler function
        """
        self._pre_hooks.append(IngestionHook(name, handler))

    def register_post_hook(
        self, name: str, handler: Callable[[list[AppEvent | BrowserVisit | CalendarBlock]], Any]
    ) -> None:
        """Register post-ingestion hook.

        Parameters
        ----------
        name : str
            Hook name
        handler : Callable
            Hook handler function
        """
        self._post_hooks.append(IngestionHook(name, handler))

    def flush(self) -> dict[str, Any]:
        """Flush collector and get statistics.

        Returns
        -------
        dict[str, Any]
            Flush result
        """
        flushed = self.collector.flush()
        return {
            "events_flushed": flushed,
            "collector_stats": self.collector.get_stats(),
            "service_stats": self.get_stats(),
        }

    def get_stats(self) -> dict[str, Any]:
        """Get service statistics.

        Returns
        -------
        dict[str, Any]
            Service statistics
        """
        return {
            **self._stats,
            "collector": self.collector.get_stats(),
            "materializer": self.materializer.get_cache_stats(),
        }

    def export_config(self, path: Path | str) -> None:
        """Export current configuration to file.

        Parameters
        ----------
        path : Path | str
            Output path
        """
        self.config.to_yaml(path)

    @classmethod
    def from_config_file(cls, path: Path | str) -> "IngestionService":
        """Create service from configuration file.

        Parameters
        ----------
        path : Path | str
            Configuration file path

        Returns
        -------
        IngestionService
            Configured service instance
        """
        config = IngestionConfig.from_yaml(path)
        return cls(config)

    def start(self) -> None:
        """Start ingestion service."""
        self.collector.start()

    def stop(self) -> None:
        """Stop ingestion service."""
        self.collector.stop()

    def to_http_handler(self) -> Callable:
        """Create HTTP request handler.

        Returns
        -------
        Callable
            HTTP handler function

        Note
        ----
        This is a basic implementation. In production, use a proper
        framework like FastAPI or Flask.
        """

        async def handler(request_data: dict[str, Any]) -> dict[str, Any]:
            """Handle HTTP ingestion request.

            Parameters
            ----------
            request_data : dict[str, Any]
                Request payload

            Returns
            -------
            dict[str, Any]
                Response data
            """
            endpoint = request_data.get("endpoint", "/ingest")
            payload = request_data.get("payload", {})

            if endpoint == "/ingest/event":
                # Single event ingestion
                event_type = payload.get("event_type")
                event_data = payload.get("data")

                if event_type == "AppEvent":
                    event = AppEvent(**event_data)
                elif event_type == "BrowserVisit":
                    event = BrowserVisit(**event_data)
                elif event_type == "CalendarBlock":
                    event = CalendarBlock(**event_data)
                else:
                    return {"status": "error", "message": "Unknown event type"}

                return await self.ingest_event_async(event)

            if endpoint == "/ingest/batch":
                # Batch ingestion
                events = []
                for event_item in payload.get("events", []):
                    event_type = event_item.get("event_type")
                    event_data = event_item.get("data")

                    if event_type == "AppEvent":
                        events.append(AppEvent(**event_data))
                    elif event_type == "BrowserVisit":
                        events.append(BrowserVisit(**event_data))
                    elif event_type == "CalendarBlock":
                        events.append(CalendarBlock(**event_data))

                return await self.ingest_batch_async(events)

            if endpoint == "/stats":
                return {"status": "success", "stats": self.get_stats()}

            if endpoint == "/flush":
                return {"status": "success", **self.flush()}

            return {"status": "error", "message": "Unknown endpoint"}

        return handler
