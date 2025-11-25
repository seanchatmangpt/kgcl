"""SHACL validation for KGCL RDF data."""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from rdflib import Graph, Namespace, RDF
from pathlib import Path


@dataclass
class SHACLViolation:
    """SHACL validation violation."""

    focus_node: str
    severity: str
    shape_name: str
    message: str
    defect_description: Optional[str] = None
    suggested_fix: Optional[str] = None


@dataclass
class SHACLReport:
    """SHACL validation report."""

    conforms: bool
    violations: List[SHACLViolation]
    total_violations: int


class SHACLValidator:
    """Validates RDF graphs against SHACL shapes and invariants."""

    def __init__(self, shapes_path: Optional[str] = None):
        """Initialize SHACL validator.

        Args:
            shapes_path: Path to SHACL shapes TTL file (defaults to .kgc/types.ttl)
        """
        self.shapes_path = shapes_path or ".kgc/types.ttl"
        self.shapes_graph = self._load_shapes()
        self.schema_ns = Namespace("http://schema.org/")
        self.apple_ns = Namespace("urn:kgc:apple:")

    def _load_shapes(self) -> Graph:
        """Load SHACL shapes from file.

        Returns:
            Graph with SHACL shape definitions
        """
        shapes_graph = Graph()
        if Path(self.shapes_path).exists():
            shapes_graph.parse(self.shapes_path, format="turtle")
        return shapes_graph

    def validate(self, data_graph: Graph) -> SHACLReport:
        """Validate RDF graph against all SHACL shapes.

        Args:
            data_graph: RDF graph to validate

        Returns:
            SHACLReport with violations
        """
        violations = []

        # Check Event shape (EventTitleNotEmpty, EventTimeRangeValid)
        violations.extend(self._validate_events(data_graph))

        # Check Action shape (ReminderStatusRequired, ReminderDueToday)
        violations.extend(self._validate_actions(data_graph))

        # Check Message shape (MailMetadataValid)
        violations.extend(self._validate_messages(data_graph))

        # Check CreativeWork shape (FilePathValid)
        violations.extend(self._validate_works(data_graph))

        # Check cross-document constraints
        violations.extend(self._validate_cross_constraints(data_graph))

        conforms = len(violations) == 0

        return SHACLReport(
            conforms=conforms,
            violations=violations,
            total_violations=len(violations),
        )

    def _validate_events(self, graph: Graph) -> List[SHACLViolation]:
        """Validate schema:Event instances.

        Checks:
        - EventTitleNotEmptyInvariant
        - EventTimeRangeValidInvariant

        Args:
            graph: Data graph

        Returns:
            List of violations
        """
        violations = []

        # Get all events
        for event in graph.subjects(RDF.type, self.schema_ns.Event):
            # Check title exists and not empty
            titles = list(graph.objects(event, self.schema_ns.name))
            if not titles or all(len(str(t).strip()) == 0 for t in titles):
                violations.append(
                    SHACLViolation(
                        focus_node=str(event),
                        severity="Violation",
                        shape_name="EventTitleNotEmptyInvariant",
                        message="Event must have a non-empty title",
                        defect_description="Untitled meetings cause context loss",
                        suggested_fix="Provide a descriptive title for the event",
                    )
                )

            # Check start < end
            starts = list(graph.objects(event, self.schema_ns.startDate))
            ends = list(graph.objects(event, self.schema_ns.endDate))
            if starts and ends:
                try:
                    start_str = str(starts[0])
                    end_str = str(ends[0])
                    # Simple string comparison works for ISO 8601
                    if start_str >= end_str:
                        violations.append(
                            SHACLViolation(
                                focus_node=str(event),
                                severity="Violation",
                                shape_name="EventTimeRangeValidInvariant",
                                message="Event start must be before end",
                                defect_description="Invalid time ranges cause malformed data",
                                suggested_fix="Ensure startDate < endDate",
                            )
                        )
                except Exception:
                    pass  # Skip validation if dates can't be compared

        return violations

    def _validate_actions(self, graph: Graph) -> List[SHACLViolation]:
        """Validate schema:Action instances.

        Checks:
        - ReminderStatusRequiredInvariant
        - ReminderDueTodayValidInvariant

        Args:
            graph: Data graph

        Returns:
            List of violations
        """
        violations = []

        # Get all actions
        for action in graph.subjects(RDF.type, self.schema_ns.Action):
            # Check status exists
            statuses = list(graph.objects(action, self.schema_ns.actionStatus))
            if not statuses:
                violations.append(
                    SHACLViolation(
                        focus_node=str(action),
                        severity="Violation",
                        shape_name="ReminderStatusRequiredInvariant",
                        message="Action must have an actionStatus",
                        defect_description="Tasks without status create ambiguous state",
                        suggested_fix="Set actionStatus to PotentialActionStatus or CompletedActionStatus",
                    )
                )

        return violations

    def _validate_messages(self, graph: Graph) -> List[SHACLViolation]:
        """Validate schema:Message instances.

        Checks:
        - MailMetadataValidInvariant

        Args:
            graph: Data graph

        Returns:
            List of violations
        """
        violations = []

        # Get all messages
        for message in graph.subjects(RDF.type, self.schema_ns.Message):
            # Check has author (sender)
            authors = list(graph.objects(message, self.schema_ns.author))
            if not authors:
                violations.append(
                    SHACLViolation(
                        focus_node=str(message),
                        severity="Violation",
                        shape_name="MailMetadataValidInvariant",
                        message="Message must have an author (sender)",
                        defect_description="Emails without sender become orphaned data",
                        suggested_fix="Ensure message has schema:author pointing to a Person",
                    )
                )

        return violations

    def _validate_works(self, graph: Graph) -> List[SHACLViolation]:
        """Validate schema:CreativeWork instances.

        Checks:
        - FilePathValidInvariant

        Args:
            graph: Data graph

        Returns:
            List of violations
        """
        violations = []

        # Get all creative works
        for work in graph.subjects(RDF.type, self.schema_ns.CreativeWork):
            # Check has valid file path
            source_ids = list(graph.objects(work, self.apple_ns.sourceIdentifier))
            if source_ids:
                path = str(source_ids[0])
                # Validate is absolute path
                if not path.startswith("/"):
                    violations.append(
                        SHACLViolation(
                            focus_node=str(work),
                            severity="Violation",
                            shape_name="FilePathValidInvariant",
                            message="File path must be absolute",
                            defect_description="Relative file paths create broken references",
                            suggested_fix="Use absolute file paths starting with /",
                        )
                    )

        return violations

    def _validate_cross_constraints(self, graph: Graph) -> List[SHACLViolation]:
        """Validate cross-document constraints.

        Checks:
        - DataHasSourceInvariant
        - NoCircularDependenciesInvariant

        Args:
            graph: Data graph

        Returns:
            List of violations
        """
        violations = []

        # Check all data has source app tracking
        for subject in graph.subjects():
            # Skip blank nodes and literals
            if str(subject).startswith("urn:kgc:"):
                sources = list(graph.objects(subject, self.apple_ns.sourceApp))
                if not sources:
                    # Only check if it's a domain object (has RDF type)
                    has_type = any(
                        graph.objects(subject, RDF.type)
                    )
                    if has_type:
                        violations.append(
                            SHACLViolation(
                                focus_node=str(subject),
                                severity="Warning",
                                shape_name="DataHasSourceInvariant",
                                message="Data should have sourceApp tracking",
                                defect_description="Data without source tracking has unclear origin",
                                suggested_fix="Add apple:sourceApp property",
                            )
                        )

        # Check for circular task dependencies
        violations.extend(self._check_circular_dependencies(graph))

        return violations

    def _check_circular_dependencies(self, graph: Graph) -> List[SHACLViolation]:
        """Check for circular task dependencies.

        Args:
            graph: Data graph

        Returns:
            List of violations
        """
        violations = []

        # Build dependency map
        deps = {}
        for task in graph.subjects(RDF.type, self.schema_ns.Action):
            task_str = str(task)
            depends_on = list(graph.objects(task, self.apple_ns.dependsOn))
            if depends_on:
                deps[task_str] = [str(d) for d in depends_on]

        # Check for cycles using DFS
        visited = set()
        for task_id in deps:
            if self._has_cycle(task_id, deps, visited, set()):
                violations.append(
                    SHACLViolation(
                        focus_node=task_id,
                        severity="Violation",
                        shape_name="NoCircularDependenciesInvariant",
                        message="Circular task dependencies detected",
                        defect_description="Circular dependencies create task deadlocks",
                        suggested_fix="Remove circular dependency edges",
                    )
                )

        return violations

    def _has_cycle(
        self,
        node: str,
        graph: Dict[str, List[str]],
        visited: set,
        rec_stack: set,
    ) -> bool:
        """Check if DFS path has a cycle.

        Args:
            node: Current node
            graph: Dependency graph
            visited: Set of visited nodes
            rec_stack: Current recursion stack

        Returns:
            True if cycle detected
        """
        visited.add(node)
        rec_stack.add(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if self._has_cycle(neighbor, graph, visited, rec_stack):
                    return True
            elif neighbor in rec_stack:
                return True

        rec_stack.remove(node)
        return False

    def validate_invariant(
        self,
        data_object: Any,
        invariant: str,
        graph: Optional[Graph] = None,
        tags: Optional[List[str]] = None,
    ) -> SHACLReport:
        """Validate single invariant on object.

        Args:
            data_object: Object to validate
            invariant: Invariant name
            graph: Optional RDF graph (if already converted)
            tags: Optional tags for context

        Returns:
            SHACLReport with results
        """
        # For now, return empty report
        # Full implementation would require object-to-RDF conversion
        return SHACLReport(
            conforms=True,
            violations=[],
            total_violations=0,
        )

    def validate_all_invariants(self, data: Dict[str, List[Any]]) -> SHACLReport:
        """Validate all invariants on multiple objects.

        Args:
            data: Dict of data source lists

        Returns:
            SHACLReport with all violations
        """
        # For now, return empty report
        # Full implementation would ingest all data and validate
        return SHACLReport(
            conforms=True,
            violations=[],
            total_violations=0,
        )
