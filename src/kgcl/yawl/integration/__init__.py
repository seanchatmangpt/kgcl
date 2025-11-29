"""YAWL integration module for vendor connectivity.

This module provides adapters to connect Python YAWL clients with:
- vendors/yawl-v5.2: Java YAWL example specifications
- vendors/unrdf: RDF knowledge graph library
- vendors/yawlui-v5.2: Modern YAWL web UI
- kgcl.hybrid: Hybrid Engine tick controller
"""

from kgcl.yawl.integration.hybrid_adapter import WorkflowStateChange, YAWLHybridAdapter, YAWLTickReceipt
from kgcl.yawl.integration.rdf_bridge import RDFTriple, YAWLRDFBridge
from kgcl.yawl.integration.unrdf_adapter import ProvenanceRecord, UNRDFAdapter, UNRDFHookEvent, YAWLEvent, YAWLEventType
from kgcl.yawl.integration.vendor_loader import VendorSpec, VendorSpecLoader

__all__ = [
    "ProvenanceRecord",
    "RDFTriple",
    "UNRDFAdapter",
    "UNRDFHookEvent",
    "VendorSpec",
    "VendorSpecLoader",
    "WorkflowStateChange",
    "YAWLEvent",
    "YAWLEventType",
    "YAWLHybridAdapter",
    "YAWLRDFBridge",
    "YAWLTickReceipt",
]
