"""State Machine Testing

Provides state machine test models and runners.
"""

from typing import Any, Callable, Dict, List, Set, Optional, Tuple
from enum import Enum
from dataclasses import dataclass


@dataclass
class Transition:
    """State transition"""
    from_state: str
    to_state: str
    action: str
    precondition: Optional[Callable[[Any], bool]] = None
    postcondition: Optional[Callable[[Any], bool]] = None


class StateMachine:
    """Abstract state machine for testing

    Models system behavior through states and transitions.
    """

    def __init__(self, initial_state: str) -> None:
        self._current_state = initial_state
        self._transitions: Dict[str, List[Transition]] = {}
        self._history: List[str] = [initial_state]

    def add_transition(
        self,
        from_state: str,
        to_state: str,
        action: str,
        precondition: Optional[Callable[[Any], bool]] = None,
        postcondition: Optional[Callable[[Any], bool]] = None,
    ) -> None:
        """Add state transition"""
        if from_state not in self._transitions:
            self._transitions[from_state] = []

        transition = Transition(
            from_state=from_state,
            to_state=to_state,
            action=action,
            precondition=precondition,
            postcondition=postcondition,
        )
        self._transitions[from_state].append(transition)

    def current_state(self) -> str:
        """Get current state"""
        return self._current_state

    def valid_actions(self) -> List[str]:
        """Get valid actions from current state"""
        if self._current_state not in self._transitions:
            return []
        return [t.action for t in self._transitions[self._current_state]]

    def can_transition(self, action: str, context: Optional[Any] = None) -> bool:
        """Check if transition is valid"""
        if self._current_state not in self._transitions:
            return False

        for transition in self._transitions[self._current_state]:
            if transition.action == action:
                if transition.precondition is None:
                    return True
                return transition.precondition(context)

        return False

    def perform_action(self, action: str, context: Optional[Any] = None) -> bool:
        """Perform action and transition state

        Returns:
            True if transition succeeded
        """
        if self._current_state not in self._transitions:
            return False

        for transition in self._transitions[self._current_state]:
            if transition.action == action:
                # Check precondition
                if transition.precondition and not transition.precondition(context):
                    return False

                # Check postcondition
                if transition.postcondition and not transition.postcondition(context):
                    return False

                # Perform transition
                self._current_state = transition.to_state
                self._history.append(self._current_state)
                return True

        return False

    def history(self) -> List[str]:
        """Get state history"""
        return self._history.copy()

    def reset(self, initial_state: str) -> None:
        """Reset to initial state"""
        self._current_state = initial_state
        self._history = [initial_state]


@dataclass
class StateMachineTest:
    """Test for a state machine

    Example:
        test = StateMachineTest(
            name="order_workflow",
            initial_state="pending",
            expected_path=["pending", "confirmed", "shipped", "delivered"]
        )
    """
    name: str
    initial_state: str
    expected_path: Optional[List[str]] = None
    machine: Optional[StateMachine] = None
    passed: bool = False

    def __post_init__(self) -> None:
        if self.machine is None:
            self.machine = StateMachine(self.initial_state)

    def run(self, actions: List[Tuple[str, Optional[Any]]]) -> bool:
        """Run test with sequence of actions

        Args:
            actions: List of (action, context) tuples

        Returns:
            True if test passed
        """
        if self.machine is None:
            return False

        for action, context in actions:
            if not self.machine.perform_action(action, context):
                self.passed = False
                return False

        # Check if expected path matches if provided
        if self.expected_path:
            self.passed = self.machine.history() == self.expected_path
        else:
            self.passed = True

        return self.passed

    def __repr__(self) -> str:
        return (
            f"StateMachineTest({self.name!r}, "
            f"state={self.machine.current_state() if self.machine else 'None'}, "
            f"passed={self.passed})"
        )
