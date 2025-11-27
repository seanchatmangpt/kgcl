"""TickExecutor - Execute a single tick of physics application.

This module implements the core tick execution logic: export state,
apply rules via reasoner, and import results back to store.

Examples
--------
>>> from kgcl.hybrid.adapters import OxigraphAdapter, EYEAdapter, WCP43RulesAdapter
>>> store = OxigraphAdapter()
>>> reasoner = EYEAdapter()
>>> rules = WCP43RulesAdapter()
>>> executor = TickExecutor(store, reasoner, rules)
"""

from __future__ import annotations

import logging
import time

import pyoxigraph as ox

from kgcl.hybrid.domain.exceptions import ReasonerError
from kgcl.hybrid.domain.physics_result import PhysicsResult
from kgcl.hybrid.ports.reasoner_port import Reasoner
from kgcl.hybrid.ports.rules_port import RulesProvider
from kgcl.hybrid.ports.store_port import RDFStore

logger = logging.getLogger(__name__)


class TickExecutor:
    """Execute a single tick of physics application.

    Implements the core feedback loop:
    1. Export state from store (Matter at T0)
    2. Apply rules via reasoner (Physics as Force)
    3. Import results back to store (Matter at T1)

    Parameters
    ----------
    store : RDFStore
        The RDF store for state storage.
    reasoner : Reasoner
        The N3 reasoner for applying rules.
    rules_provider : RulesProvider
        Provider for physics rules.

    Examples
    --------
    >>> from kgcl.hybrid.adapters import OxigraphAdapter, EYEAdapter, WCP43RulesAdapter
    >>> store = OxigraphAdapter()
    >>> reasoner = EYEAdapter(skip_availability_check=True)
    >>> rules = WCP43RulesAdapter()
    >>> executor = TickExecutor(store, reasoner, rules)
    """

    def __init__(self, store: RDFStore, reasoner: Reasoner, rules_provider: RulesProvider) -> None:
        """Initialize TickExecutor.

        Parameters
        ----------
        store : RDFStore
            The RDF store for state.
        reasoner : Reasoner
            The N3 reasoner.
        rules_provider : RulesProvider
            Provider for physics rules.
        """
        self._store = store
        self._reasoner = reasoner
        self._rules = rules_provider
        self._rules_cache: str | None = None
        logger.info("TickExecutor initialized")

    def execute_tick(self, tick_number: int) -> PhysicsResult:
        """Execute one tick of physics application.

        This is the core Feedback Loop:
        1. Export State (T0) from store
        2. Apply Logic (Rules) via reasoner
        3. Ingest Delta back into store (T1)

        Parameters
        ----------
        tick_number : int
            Sequential tick identifier.

        Returns
        -------
        PhysicsResult
            Result with timing and delta metrics.

        Raises
        ------
        ReasonerError
            If reasoning fails.

        Examples
        --------
        >>> from kgcl.hybrid.adapters import OxigraphAdapter, EYEAdapter, WCP43RulesAdapter
        >>> store = OxigraphAdapter()
        >>> _ = store.load_turtle('''
        ...     @prefix kgc: <https://kgc.org/ns/> .
        ...     @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        ...     <urn:task:A> kgc:status "Completed" ;
        ...         yawl:flowsInto <urn:flow:1> .
        ...     <urn:flow:1> yawl:nextElementRef <urn:task:B> .
        ...     <urn:task:B> a yawl:Task .
        ... ''')
        >>> reasoner = EYEAdapter()
        >>> if reasoner.is_available():
        ...     rules = WCP43RulesAdapter()
        ...     executor = TickExecutor(store, reasoner, rules)
        ...     result = executor.execute_tick(1)
        ...     result.tick_number == 1
        True
        """
        start_time = time.perf_counter()

        # 1. EXPORT (Materialize State)
        triples_before = self._store.triple_count()
        current_state = self._get_state()

        # 2. Get rules (cached)
        rules = self._get_rules()

        # 3. REASON (Apply Force)
        logger.info(f"Tick {tick_number}: Invoking reasoner...")
        result = self._reasoner.reason(current_state, rules)

        if not result.success:
            error_msg = result.error or "Unknown reasoning error"
            logger.error(f"Tick {tick_number}: Reasoning failed: {error_msg}")
            raise ReasonerError(error_msg)

        # 4. INGEST (Evolution)
        # Load the deductions back into the store
        # Note: Reasoner outputs FULL state + New Deductions
        # Store handles merge (idempotent adds)
        self._load_deductions(result.output)

        triples_after = self._store.triple_count()
        delta = triples_after - triples_before

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(f"Tick {tick_number}: Physics applied in {duration_ms:.2f}ms, delta={delta}")

        return PhysicsResult(
            tick_number=tick_number,
            duration_ms=duration_ms,
            triples_before=triples_before,
            triples_after=triples_after,
            delta=delta,
        )

    def _get_state(self) -> str:
        """Export current state from store.

        Returns
        -------
        str
            Current state as serialized RDF.
        """
        # Try to get TriG format if available (better for EYE)
        if hasattr(self._store, "dump_trig"):
            trig_method = self._store.dump_trig
            return str(trig_method())
        return self._store.dump()

    def _get_rules(self) -> str:
        """Get physics rules (cached).

        Returns
        -------
        str
            N3 physics rules.
        """
        if self._rules_cache is None:
            self._rules_cache = self._rules.get_rules()
        return self._rules_cache

    def _load_deductions(self, output: str) -> None:
        """Load reasoner output back into store.

        Parameters
        ----------
        output : str
            N3 output from reasoner.
        """
        # Load as N3 format (reasoner output)
        if hasattr(self._store, "load_raw"):
            load_raw_method = self._store.load_raw
            load_raw_method(output.encode("utf-8"), ox.RdfFormat.N3)
        else:
            self._store.load_n3(output)
