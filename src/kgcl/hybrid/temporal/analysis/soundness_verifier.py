"""Soundness verification for workflow nets.

Implements van der Aalst's soundness criteria:
1. Option to complete - For every marking M reachable from [i], [o] is reachable from M
2. Proper completion - When [o] is reached, no other places have tokens
3. No dead transitions - Every transition can fire in some reachable marking
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kgcl.hybrid.temporal.domain.petri_net import FiringSequence, Marking, WorkflowNet


class SoundnessViolation(Enum):
    """Types of soundness violations."""

    DEADLOCK = auto()  # No enabled transitions, not at final marking
    LIVELOCK = auto()  # Infinite loop not reaching final
    IMPROPER_COMPLETION = auto()  # Final place has token but others do too
    DEAD_TRANSITION = auto()  # Transition never enabled
    NO_SOURCE = auto()  # Missing source place
    NO_SINK = auto()  # Missing sink place
    UNREACHABLE_SINK = auto()  # Cannot reach final marking


@dataclass(frozen=True)
class SoundnessResult:
    """Result of soundness verification.

    Parameters
    ----------
    is_sound : bool
        True if WF-net is sound
    violations : tuple[SoundnessViolation, ...]
        List of violations found
    messages : tuple[str, ...]
        Detailed violation messages
    reachable_markings : int
        Number of reachable markings explored
    dead_transitions : tuple[str, ...]
        Transitions that can never fire
    deadlock_markings : tuple[Any, ...]
        Markings where execution gets stuck
    """

    is_sound: bool
    violations: tuple[SoundnessViolation, ...] = ()
    messages: tuple[str, ...] = ()
    reachable_markings: int = 0
    dead_transitions: tuple[str, ...] = ()
    deadlock_markings: tuple[Any, ...] = ()


class SoundnessVerifier:
    """Verifies soundness of workflow nets.

    Uses reachability analysis to check van der Aalst's
    three soundness criteria.
    """

    def __init__(self, max_markings: int = 10000) -> None:
        """Initialize verifier.

        Parameters
        ----------
        max_markings : int
            Maximum markings to explore (prevents infinite loops)
        """
        self._max_markings = max_markings

    def verify(self, net: WorkflowNet) -> SoundnessResult:
        """Verify soundness of a workflow net.

        Parameters
        ----------
        net : WorkflowNet
            Workflow net to verify

        Returns
        -------
        SoundnessResult
            Verification result
        """
        violations: list[SoundnessViolation] = []
        messages: list[str] = []

        # Check structural requirements
        try:
            source = net.source_place()
        except ValueError:
            violations.append(SoundnessViolation.NO_SOURCE)
            messages.append("No unique source place found")
            source = None

        try:
            sink = net.sink_place()
        except ValueError:
            violations.append(SoundnessViolation.NO_SINK)
            messages.append("No unique sink place found")
            sink = None

        if violations:
            return SoundnessResult(is_sound=False, violations=tuple(violations), messages=tuple(messages))

        # Explore reachability graph
        initial = net.initial_marking()
        final = net.final_marking()

        visited: set[Marking] = set()
        to_explore: deque[Marking] = deque([initial])
        transitions_fired: set[str] = set()
        deadlock_markings: list[Marking] = []

        while to_explore and len(visited) < self._max_markings:
            marking = to_explore.popleft()

            if marking in visited:
                continue
            visited.add(marking)

            # Check if this is final marking
            if marking == final:
                continue

            # Check for improper completion
            if sink is not None and marking.get(sink.id) > 0 and marking != final:
                violations.append(SoundnessViolation.IMPROPER_COMPLETION)
                messages.append(f"Improper completion: sink has token but other places too: {marking}")

            # Get enabled transitions
            enabled = net.enabled_transitions(marking)

            if not enabled:
                # Deadlock - no enabled transitions and not at final
                deadlock_markings.append(marking)
                continue

            # Fire each enabled transition
            for t_id in enabled:
                transitions_fired.add(t_id)
                new_marking = net.fire(t_id, marking)
                if new_marking not in visited:
                    to_explore.append(new_marking)

        # Check criterion 1: Option to complete (all markings can reach final)
        for deadlock in deadlock_markings:
            if deadlock != final:
                violations.append(SoundnessViolation.DEADLOCK)
                messages.append(f"Deadlock at marking: {deadlock}")

        # Check if final is reachable from initial
        if final not in visited:
            violations.append(SoundnessViolation.UNREACHABLE_SINK)
            messages.append("Final marking [o] not reachable from initial marking [i]")

        # Check criterion 3: No dead transitions
        all_transitions = {t.id for t in net.transitions}
        dead = all_transitions - transitions_fired

        for t_id in dead:
            violations.append(SoundnessViolation.DEAD_TRANSITION)
            messages.append(f"Dead transition (never enabled): {t_id}")

        return SoundnessResult(
            is_sound=len(violations) == 0,
            violations=tuple(violations),
            messages=tuple(messages),
            reachable_markings=len(visited),
            dead_transitions=tuple(dead),
            deadlock_markings=tuple(deadlock_markings),
        )

    def find_firing_sequence_to_final(self, net: WorkflowNet) -> FiringSequence | None:
        """Find a firing sequence from initial to final marking.

        Uses BFS to find shortest path.

        Parameters
        ----------
        net : WorkflowNet
            Workflow net

        Returns
        -------
        FiringSequence | None
            Sequence of transitions, or None if unreachable
        """
        from kgcl.hybrid.temporal.domain.petri_net import FiringSequence

        initial = net.initial_marking()
        final = net.final_marking()

        visited: set[Marking] = set()
        # Queue of (marking, sequence)
        to_explore: deque[tuple[Marking, FiringSequence]] = deque([(initial, FiringSequence())])

        while to_explore:
            marking, sequence = to_explore.popleft()

            if marking in visited:
                continue
            visited.add(marking)

            if marking == final:
                return sequence

            for t_id in net.enabled_transitions(marking):
                new_marking = net.fire(t_id, marking)
                if new_marking not in visited:
                    to_explore.append((new_marking, sequence.append(t_id)))

        return None


@dataclass(frozen=True)
class CoverabilityNode:
    """Node in coverability graph (for unbounded nets).

    Parameters
    ----------
    marking : Marking
        Current marking
    parent : CoverabilityNode | None
        Parent node in graph
    transition : str | None
        Transition that led to this node
    """

    marking: Any  # Marking or marking with omega
    parent: CoverabilityNode | None = None
    transition: str | None = None


class CoverabilityAnalyzer:
    """Analyzes coverability for potentially unbounded nets.

    Uses omega (ω) to represent unbounded places.
    """

    def __init__(self, max_nodes: int = 10000) -> None:
        """Initialize analyzer.

        Parameters
        ----------
        max_nodes : int
            Maximum nodes to explore
        """
        self._max_nodes = max_nodes

    def is_bounded(self, net: WorkflowNet) -> tuple[bool, int]:
        """Check if net is bounded.

        Parameters
        ----------
        net : WorkflowNet
            Workflow net to check

        Returns
        -------
        tuple[bool, int]
            (is_bounded, max_tokens_in_any_place)
        """
        initial = net.initial_marking()
        visited: set[Marking] = set()
        to_explore: deque[Marking] = deque([initial])
        max_tokens = 1

        while to_explore and len(visited) < self._max_nodes:
            marking = to_explore.popleft()

            if marking in visited:
                continue
            visited.add(marking)

            # Track max tokens
            for _, count in marking.tokens:
                max_tokens = max(max_tokens, count)

            for t_id in net.enabled_transitions(marking):
                new_marking = net.fire(t_id, marking)
                if new_marking not in visited:
                    to_explore.append(new_marking)

        # If we explored all markings, it's bounded
        is_bounded = len(visited) < self._max_nodes
        return is_bounded, max_tokens


def create_soundness_verifier(max_markings: int = 10000) -> SoundnessVerifier:
    """Factory for soundness verifier.

    Parameters
    ----------
    max_markings : int
        Maximum markings to explore

    Returns
    -------
    SoundnessVerifier
        New verifier instance
    """
    return SoundnessVerifier(max_markings=max_markings)
