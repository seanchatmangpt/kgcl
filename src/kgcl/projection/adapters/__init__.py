"""Projection adapters - Concrete implementations of ports.

This module contains adapters for:
- EventStoreAdapter: Wraps RDFEventStore for KGCLDaemon integration
- RDFLibAdapter: Wraps rdflib.Graph for testing
- FilesystemTemplateRegistry: Loads templates from filesystem

Examples
--------
>>> from kgcl.daemon.event_store import RDFEventStore
>>> from kgcl.projection.adapters import EventStoreAdapter
>>> store = RDFEventStore()
>>> adapter = EventStoreAdapter(store)
>>> adapter.graph_id
'event_store'
"""

from __future__ import annotations

from kgcl.projection.adapters.event_store_adapter import EventStoreAdapter
from kgcl.projection.adapters.filesystem_registry import FilesystemTemplateRegistry
from kgcl.projection.adapters.rdflib_adapter import RDFLibAdapter

__all__ = ["EventStoreAdapter", "FilesystemTemplateRegistry", "RDFLibAdapter"]
