"""Blood-Brain Barrier (BBB) Ingress Layer.

This module implements the ingress layer that converts external data (JSON)
into validated RDF topology (QuadDelta) that can be processed by the Atman engine.

The BBB implements "Active Transport":
1. LIFT: Convert JSON payload to N-Triples (QuadDelta)
2. SCREEN: Run pyshacl.validate() against invariants.shacl.ttl
3. REJECT: If invalid, raise TopologyViolationError
4. PASS: Send validated QuadDelta to Atman

The metaphor is biological: just as the blood-brain barrier protects the brain
from harmful substances while allowing nutrients through, the BBB protects
the knowledge graph from invalid topology while allowing valid mutations.
"""

from kgcl.ingress.bbb import BBBIngress, TopologyViolationError, lift_json_to_quads, validate_topology

__all__ = ["BBBIngress", "TopologyViolationError", "lift_json_to_quads", "validate_topology"]
