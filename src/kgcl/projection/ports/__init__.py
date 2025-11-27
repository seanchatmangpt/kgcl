"""Projection ports - Abstract protocols for graph and template access.

This module re-exports the protocol interfaces that define boundaries
between the projection engine and external systems.
"""

from __future__ import annotations

from kgcl.projection.ports.graph_client import GraphClient, GraphRegistry
from kgcl.projection.ports.template_registry import BundleRegistry, InMemoryTemplateRegistry, TemplateRegistry

__all__ = ["BundleRegistry", "GraphClient", "GraphRegistry", "InMemoryTemplateRegistry", "TemplateRegistry"]
