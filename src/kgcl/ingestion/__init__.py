"""KGCL Event Ingestion System.

This module provides a complete event collection and ingestion pipeline for:
- Application usage tracking
- Browser visit monitoring
- Calendar event collection
- Feature materialization
- RDF conversion
"""

from kgcl.ingestion.config import IngestionConfig
from kgcl.ingestion.models import AppEvent, BrowserVisit, CalendarBlock, EventBatch
from kgcl.ingestion.service import IngestionService

__all__ = ["AppEvent", "BrowserVisit", "CalendarBlock", "EventBatch", "IngestionConfig", "IngestionService"]
