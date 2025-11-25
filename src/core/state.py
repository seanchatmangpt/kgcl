"""State Management for Tests

Provides state machines and state tracking for complex test scenarios.
"""

from typing import TypeVar, Generic, Callable, Any, Dict, Optional, Set
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

S = TypeVar("S", bound="State")
T = TypeVar("T")


class State(Enum):
    """Base state enumeration"""
    pass


@dataclass
class StateTransition(Generic[S]):
    """Represents a transition between states"""
    from_state: S
    to_state: S
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)


class StateManager(Generic[S]):
    """Manages state transitions and history

    Provides a simple state machine for test scenarios.

    Example:
        class OrderState(Enum):
            PENDING = "pending"
            CONFIRMED = "confirmed"
            SHIPPED = "shipped"
            DELIVERED = "delivered"

        @test
        def test_order_lifecycle():
            sm = StateManager(OrderState.PENDING)
            sm.transition_to(OrderState.CONFIRMED)
            sm.transition_to(OrderState.SHIPPED)
            assert sm.current_state() == OrderState.SHIPPED
            assert sm.history() == [
                OrderState.PENDING,
                OrderState.CONFIRMED,
                OrderState.SHIPPED,
            ]
    """

    def __init__(self, initial_state: S) -> None:
        self._current: S = initial_state
        self._history: list[S] = [initial_state]
        self._transitions: list[StateTransition[S]] = []
        self._validators: Dict[S, Callable[[S], bool]] = {}
        self._listeners: list[Callable[[S, S], None]] = []

    def current_state(self) -> S:
        """Get current state"""
        return self._current

    def transition_to(self, next_state: S, context: Optional[Dict[str, Any]] = None) -> bool:
        """Transition to next state

        Returns True if transition succeeded, False otherwise.
        """
        # Validate next state if validator exists
        if next_state in self._validators:
            if not self._validators[next_state](self._current):
                return False

        # Record transition
        transition = StateTransition(
            from_state=self._current,
            to_state=next_state,
            context=context or {}
        )
        self._transitions.append(transition)

        # Update current state
        old_state = self._current
        self._current = next_state
        self._history.append(next_state)

        # Notify listeners
        for listener in self._listeners:
            listener(old_state, next_state)

        return True

    def can_transition_to(self, next_state: S) -> bool:
        """Check if transition is valid"""
        if next_state in self._validators:
            return self._validators[next_state](self._current)
        return True

    def history(self) -> list[S]:
        """Get complete state history"""
        return self._history.copy()

    def transitions(self) -> list[StateTransition[S]]:
        """Get all transitions"""
        return self._transitions.copy()

    def add_validator(self, state: S, validator: Callable[[S], bool]) -> None:
        """Add validator for state transitions"""
        self._validators[state] = validator

    def add_listener(self, listener: Callable[[S, S], None]) -> None:
        """Add listener for state changes"""
        self._listeners.append(listener)

    def reset(self, initial_state: S) -> None:
        """Reset to initial state"""
        self._current = initial_state
        self._history = [initial_state]
        self._transitions = []

    def __repr__(self) -> str:
        return f"StateManager(current={self._current}, history_len={len(self._history)})"
