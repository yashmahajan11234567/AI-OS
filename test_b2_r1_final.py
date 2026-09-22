#!/usr/bin/env python3
"""
Final test to verify B2-R1 StateManager methods work correctly.
"""

import tempfile
from pathlib import Path
from aios.core.state import StateManager
from aios.events.core.bus import EventBus, EventBusConfig


def test_state_manager_methods_exist():
    """Test that the new StateManager methods exist."""
    # Setup EventBus like in the existing tests
    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))

    with tempfile.TemporaryDirectory() as tmp_dir:
        sm = StateManager(
            persistence_path=Path(tmp_dir) / "state",
            service_registry=None,  # Will be set in initialize
            configuration_manager=None,  # Will be set in initialize
            logger=None  # Will be set in initialize
        )
        # Manually set the event bus since we can't fully initialize
        sm._event_bus = bus

        # Test that methods exist
        assert hasattr(sm, 'get_git_context')
        assert hasattr(sm, 'get_state_history')

        # Test that methods are callable
        git_context = sm.get_git_context()
        state_history = sm.get_state_history()

        # Test return types
        assert isinstance(git_context, dict)
        assert isinstance(state_history, list)

        print("[PASS] StateManager methods exist and return correct types")


def test_git_context_structure():
    """Test Git context has expected structure."""
    # Setup EventBus like in the existing tests
    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))

    with tempfile.TemporaryDirectory() as tmp_dir:
        sm = StateManager(
            persistence_path=Path(tmp_dir) / "state",
            service_registry=None,
            configuration_manager=None,
            logger=None
        )
        # Manually set the event bus since we can't fully initialize
        sm._event_bus = bus

        git_context = sm.get_git_context()

        # Check required fields exist
        required_fields = ["source", "authority", "advisory", "data", "provenance"]
        for field in required_fields:
            assert field in git_context, f"Missing field: {field}"

        # Check data fields
        data_fields = ["repository_path", "branch", "commit", "working_tree_clean"]
        for field in data_fields:
            assert field in git_context["data"], f"Missing data field: {field}"

        # Check provenance fields
        prov_fields = ["source", "extracted_at", "authority"]
        for field in prov_fields:
            assert field in git_context["provenance"], f"Missing provenance field: {field}"

        print("[PASS] Git context has correct structure")


def test_state_history_structure():
    """Test state history returns proper structure."""
    # Setup EventBus like in the existing tests
    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))

    with tempfile.TemporaryDirectory() as tmp_dir:
        sm = StateManager(
            persistence_path=Path(tmp_dir) / "state",
            service_registry=None,
            configuration_manager=None,
            logger=None
        )
        # Manually set the event bus since we can't fully initialize
        sm._event_bus = bus

        # Add some state and create history
        sm.set_state("global", "test_key", "test_value", "initial")
        snapshot = sm.checkpoint("global", "test_key")

        # Get history
        history = sm.get_state_history(limit=5)

        # Should have at least one entry
        assert len(history) >= 1

        # Check structure of history entries
        if history:
            entry = history[0]
            required_fields = ["snapshot_id", "scope", "identifier", "state",
                             "metadata", "timestamp", "version"]
            for field in required_fields:
                assert field in entry, f"Missing history field: {field}"

        print("[PASS] State history has correct structure")


def test_get_state_history_empty():
    """Test get_state_history() returns empty list when no history exists."""
    # Setup EventBus like in the existing tests
    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))

    with tempfile.TemporaryDirectory() as tmp_dir:
        sm = StateManager(
            persistence_path=Path(tmp_dir) / "state",
            service_registry=None,
            configuration_manager=None,
            logger=None
        )
        # Manually set the event bus since we can't fully initialize
        sm._event_bus = bus

        history = sm.get_state_history()
        assert isinstance(history, list)
        assert len(history) == 0

        print("[PASS] get_state_history returns empty list when no history")


def test_get_state_history_respects_limit():
    """Test that get_state_history() respects the limit parameter."""
    # Setup EventBus like in the existing tests
    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))

    with tempfile.TemporaryDirectory() as tmp_dir:
        sm = StateManager(
            persistence_path=Path(tmp_dir) / "state",
            service_registry=None,
            configuration_manager=None,
            logger=None
        )
        # Manually set the event bus since we can't fully initialize
        sm._event_bus = bus

        # Create some state history
        sm.set_state("global", "global_state", "key1", "value1")
        sm.checkpoint("global", "global_state")

        # Add more checkpoints
        sm.set_state("global", "global_state", "key2", "value2")
        sm.checkpoint("global", "global_state")

        sm.set_state("global", "global_state", "key3", "value3")
        sm.checkpoint("global", "global_state")

        # Get history with limit
        history = sm.get_state_history(limit=2)

        # Should return at most 2 entries
        assert len(history) <= 2
        assert isinstance(history, list)

        # Verify structure of returned items
        if history:
            assert isinstance(history[0], dict)
            assert "snapshot_id" in history[0]
            assert "timestamp" in history[0]
            assert "state" in history[0]

        print("[PASS] get_state_history respects limit parameter")


if __name__ == "__main__":
    test_state_manager_methods_exist()
    test_git_context_structure()
    test_state_history_structure()
    test_get_state_history_empty()
    test_get_state_history_respects_limit()
    print("\n[PASS] All B2-R1 tests passed!")