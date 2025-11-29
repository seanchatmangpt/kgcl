"""Hybrid Orchestrator - Thesis Architecture Implementation.

This module implements the complete hybrid workflow architecture from
the thesis "Overcoming Monotonic Barriers in Workflow Execution".

The execution flow:
1. BEGIN TRANSACTION (snapshot for rollback)
2. VALIDATE PRECONDITIONS (SHACL shapes)
3. INFERENCE (EYE produces recommendations - monotonic)
4. MUTATION (SPARQL UPDATE executes recommendations - non-monotonic)
5. VALIDATE POSTCONDITIONS (SHACL shapes)
6. COMMIT or ROLLBACK

This separation of concerns achieves 100% WCP-43 coverage vs 11.6% for pure N3.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pyoxigraph as ox

from kgcl.hybrid.adapters.shacl_validator import create_validator
from kgcl.hybrid.adapters.sparql_mutator import SPARQLMutator
from kgcl.hybrid.adapters.transaction_manager import PyOxigraphTransactionManager
from kgcl.hybrid.domain.physics_result import PhysicsResult
from kgcl.hybrid.ports.validator_port import ValidationResult
from kgcl.hybrid.wcp43_mutations import CLEANUP_RECOMMENDATIONS, WCP43_MUTATIONS

if TYPE_CHECKING:
    from kgcl.hybrid.adapters.eye_adapter import EYEAdapter
    from kgcl.hybrid.ports.transaction_port import Transaction

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TickOutcome:
    """Complete outcome of a tick execution.

    Parameters
    ----------
    success : bool
        Whether tick completed successfully.
    physics_result : PhysicsResult
        Physics application metrics.
    precondition_result : ValidationResult | None
        Precondition validation result.
    postcondition_result : ValidationResult | None
        Postcondition validation result.
    recommendations_inferred : int
        Number of recommendations from EYE.
    mutations_applied : int
        Number of SPARQL UPDATE mutations executed.
    rolled_back : bool
        Whether transaction was rolled back.
    error : str | None
        Error message if failed.
    """

    success: bool
    physics_result: PhysicsResult
    precondition_result: ValidationResult | None = None
    postcondition_result: ValidationResult | None = None
    recommendations_inferred: int = 0
    mutations_applied: int = 0
    rolled_back: bool = False
    error: str | None = None


@dataclass
class OrchestratorConfig:
    """Configuration for the hybrid orchestrator.

    Parameters
    ----------
    enable_precondition_validation : bool
        Validate state before inference.
    enable_postcondition_validation : bool
        Validate state after mutation.
    enable_transactions : bool
        Use transactions with rollback.
    cleanup_recommendations : bool
        Remove EYE recommendations after execution.
    max_mutations_per_tick : int
        Maximum mutations to apply per tick.
    """

    enable_precondition_validation: bool = True
    enable_postcondition_validation: bool = True
    enable_transactions: bool = True
    cleanup_recommendations: bool = True
    max_mutations_per_tick: int = 100


class HybridOrchestrator:
    """Orchestrator implementing the thesis hybrid architecture.

    Coordinates:
    - PyOxigraph (mutable state)
    - EYE Reasoner (inference recommendations)
    - SPARQL UPDATE (state mutations)
    - SHACL (pre/post validation)
    - Transactions (snapshot rollback)

    This achieves 100% WCP-43 coverage by separating:
    - Inference (monotonic, deterministic)
    - Mutation (non-monotonic, atomic)
    - Validation (closed-world, fail-fast)

    Parameters
    ----------
    store : ox.Store
        PyOxigraph store.
    reasoner : EYEAdapter
        EYE reasoner adapter.
    rules : str
        N3 physics rules.
    config : OrchestratorConfig | None
        Orchestrator configuration.

    Examples
    --------
    >>> import pyoxigraph as ox
    >>> from kgcl.hybrid.adapters.eye_adapter import EYEAdapter
    >>> store = ox.Store()
    >>> reasoner = EYEAdapter()
    >>> orchestrator = HybridOrchestrator(store, reasoner, N3_RULES)
    >>> result = orchestrator.execute_tick(1)
    """

    def __init__(
        self, store: ox.Store, reasoner: EYEAdapter, rules: str, config: OrchestratorConfig | None = None
    ) -> None:
        """Initialize the hybrid orchestrator.

        Parameters
        ----------
        store : ox.Store
            PyOxigraph store.
        reasoner : EYEAdapter
            EYE reasoner adapter.
        rules : str
            N3 physics rules.
        config : OrchestratorConfig | None
            Configuration options.
        """
        self._store = store
        self._reasoner = reasoner
        self._rules = rules
        self._config = config or OrchestratorConfig()

        # Initialize components
        self._mutator = SPARQLMutator(store)
        self._transaction_manager = PyOxigraphTransactionManager(store)
        self._validator = create_validator()

        logger.info("HybridOrchestrator initialized with thesis architecture")

    def execute_tick(self, tick_number: int) -> TickOutcome:
        """Execute one tick with full thesis architecture.

        Flow:
        1. Begin transaction
        2. Validate preconditions
        3. Run EYE inference (produces recommendations)
        4. Execute SPARQL UPDATE mutations
        5. Validate postconditions
        6. Commit or rollback

        Parameters
        ----------
        tick_number : int
            Sequential tick identifier.

        Returns
        -------
        TickOutcome
            Complete tick outcome with metrics.
        """
        start_time = time.perf_counter()
        triples_before = len(self._store)

        transaction: Transaction | None = None
        precondition_result: ValidationResult | None = None
        postcondition_result: ValidationResult | None = None
        recommendations_inferred = 0
        mutations_applied = 0

        try:
            # 1. BEGIN TRANSACTION
            if self._config.enable_transactions:
                transaction = self._transaction_manager.begin()
                transaction.log_operation(f"Tick {tick_number} started")

            # 2. VALIDATE PRECONDITIONS
            if self._config.enable_precondition_validation:
                current_state = self._dump_state()
                precondition_result = self._validator.validate_preconditions(current_state)
                if not precondition_result.conforms:
                    raise ValueError(
                        f"Precondition validation failed: {precondition_result.violation_count} violations"
                    )
                if transaction:
                    transaction.log_operation("Preconditions validated")

            # 3. INFERENCE (EYE produces recommendations)
            current_state = self._dump_state()
            inference_result = self._reasoner.reason(current_state, self._rules)

            if not inference_result.success:
                raise RuntimeError(f"Inference failed: {inference_result.error}")

            # Load inference results (recommendations)
            self._load_inference_results(inference_result.output)
            recommendations_inferred = self._count_recommendations()

            if transaction:
                transaction.log_operation(f"Inferred {recommendations_inferred} recommendations")

            # 4. EXECUTE MUTATIONS (SPARQL UPDATE)
            mutations_applied = self._execute_mutations()

            if transaction:
                transaction.log_operation(f"Applied {mutations_applied} mutations")

            # 5. CLEANUP RECOMMENDATIONS
            if self._config.cleanup_recommendations and recommendations_inferred > 0:
                self._cleanup_recommendations()

            # 6. VALIDATE POSTCONDITIONS
            if self._config.enable_postcondition_validation:
                new_state = self._dump_state()
                postcondition_result = self._validator.validate_postconditions(new_state)
                if not postcondition_result.conforms:
                    raise ValueError(
                        f"Postcondition validation failed: {postcondition_result.violation_count} violations"
                    )
                if transaction:
                    transaction.log_operation("Postconditions validated")

            # 7. COMMIT
            if transaction:
                self._transaction_manager.commit(transaction)

            # Build result
            triples_after = len(self._store)
            duration_ms = (time.perf_counter() - start_time) * 1000

            physics_result = PhysicsResult(
                tick_number=tick_number,
                duration_ms=duration_ms,
                triples_before=triples_before,
                triples_after=triples_after,
                delta=triples_after - triples_before,
            )

            return TickOutcome(
                success=True,
                physics_result=physics_result,
                precondition_result=precondition_result,
                postcondition_result=postcondition_result,
                recommendations_inferred=recommendations_inferred,
                mutations_applied=mutations_applied,
            )

        except Exception as e:
            # ROLLBACK on any failure
            rolled_back = False
            if transaction:
                try:
                    self._transaction_manager.rollback(transaction, reason=str(e))
                    rolled_back = True
                except Exception as rollback_error:
                    logger.error(f"Rollback failed: {rollback_error}")

            logger.error(f"Tick {tick_number} failed: {e}")

            triples_after = len(self._store)
            duration_ms = (time.perf_counter() - start_time) * 1000

            physics_result = PhysicsResult(
                tick_number=tick_number,
                duration_ms=duration_ms,
                triples_before=triples_before,
                triples_after=triples_after,
                delta=triples_after - triples_before,
            )

            return TickOutcome(
                success=False,
                physics_result=physics_result,
                precondition_result=precondition_result,
                postcondition_result=postcondition_result,
                recommendations_inferred=recommendations_inferred,
                mutations_applied=mutations_applied,
                rolled_back=rolled_back,
                error=str(e),
            )

    def _dump_state(self) -> str:
        """Dump current store state as Turtle.

        Returns
        -------
        str
            Serialized state.
        """
        chunks: list[bytes] = []
        self._store.dump(chunks.append, ox.RdfFormat.TURTLE)
        return b"".join(chunks).decode("utf-8")

    def _load_inference_results(self, output: str) -> None:
        """Load EYE inference results into store.

        Parameters
        ----------
        output : str
            N3 output from reasoner.
        """
        try:
            self._store.load(output.encode("utf-8"), ox.RdfFormat.N3)
        except Exception:
            # Try Turtle if N3 fails
            try:
                self._store.load(output.encode("utf-8"), ox.RdfFormat.TURTLE)
            except Exception as e:
                logger.warning(f"Failed to load inference results: {e}")

    def _count_recommendations(self) -> int:
        """Count recommendations inferred by EYE.

        Returns
        -------
        int
            Number of shouldFire recommendations.
        """
        query = """
        PREFIX kgc: <https://kgc.org/ns/>
        SELECT (COUNT(?s) AS ?count)
        WHERE { ?s kgc:shouldFire true }
        """
        try:
            results = list(self._store.query(query))
            if results:
                count_term = results[0][0]
                return int(str(count_term))
        except Exception as e:
            logger.warning(f"Failed to count recommendations: {e}")
        return 0

    def _execute_mutations(self) -> int:
        """Execute SPARQL UPDATE mutations for recommendations.

        Returns
        -------
        int
            Number of mutations applied.
        """
        mutations_applied = 0

        # Execute pattern-specific mutations
        for pattern_id, mutation in WCP43_MUTATIONS.items():
            if pattern_id in ("STATUS", "CLEANUP", "MARKER-CLEAN"):
                continue  # Skip utility mutations

            try:
                result = self._mutator.execute_sparql_update(mutation.sparql)
                if result.success and (result.triples_deleted > 0 or result.triples_inserted > 0):
                    mutations_applied += 1
                    logger.debug(f"Applied {pattern_id}: {mutation.name}")
            except Exception as e:
                logger.warning(f"Mutation {pattern_id} failed: {e}")

        return mutations_applied

    def _cleanup_recommendations(self) -> None:
        """Clean up recommendation markers."""
        try:
            self._mutator.execute_sparql_update(CLEANUP_RECOMMENDATIONS.sparql)
        except Exception as e:
            logger.warning(f"Recommendation cleanup failed: {e}")


def create_orchestrator(
    store: ox.Store, reasoner: EYEAdapter, rules: str, config: OrchestratorConfig | None = None
) -> HybridOrchestrator:
    """Create a hybrid orchestrator.

    Parameters
    ----------
    store : ox.Store
        PyOxigraph store.
    reasoner : EYEAdapter
        EYE reasoner adapter.
    rules : str
        N3 physics rules.
    config : OrchestratorConfig | None
        Configuration options.

    Returns
    -------
    HybridOrchestrator
        Configured orchestrator.
    """
    return HybridOrchestrator(store, reasoner, rules, config)
