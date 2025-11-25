"""State machine testing example."""

from src.testing import StateMachine, StateMachineTest


def create_order_state_machine():
    """Create state machine for order workflow."""
    sm = StateMachine("pending")
    
    # Define transitions
    sm.add_transition("pending", "confirmed", "confirm")
    sm.add_transition("confirmed", "shipped", "ship")
    sm.add_transition("shipped", "delivered", "deliver")
    
    return sm


def test_order_workflow():
    """Test complete order workflow."""
    sm = create_order_state_machine()
    
    # Perform workflow
    assert sm.perform_action("confirm")
    assert sm.current_state() == "confirmed"
    
    assert sm.perform_action("ship")
    assert sm.current_state() == "shipped"
    
    assert sm.perform_action("deliver")
    assert sm.current_state() == "delivered"
    
    # Check history
    expected = ["pending", "confirmed", "shipped", "delivered"]
    assert sm.history() == expected
    
    print(f"✓ Order workflow: {' -> '.join(sm.history())}")


def test_invalid_transition():
    """Test invalid transitions are rejected."""
    sm = create_order_state_machine()
    
    # Try invalid action from pending state
    result = sm.perform_action("deliver")
    assert not result, "Should not allow invalid transition"
    assert sm.current_state() == "pending"
    
    print("✓ Invalid transition rejected")


def test_valid_actions():
    """Test getting valid actions from current state."""
    sm = create_order_state_machine()
    
    # Check valid actions from pending
    actions = sm.valid_actions()
    assert "confirm" in actions
    
    # Transition and check new valid actions
    sm.perform_action("confirm")
    actions = sm.valid_actions()
    assert "ship" in actions
    
    print(f"✓ Valid actions from confirmed state: {actions}")


if __name__ == "__main__":
    test_order_workflow()
    test_invalid_transition()
    test_valid_actions()
