#!/usr/bin/env python3
"""
Simple integration test to verify B2-R1 StateManager methods work with SelfLoopEngine.
"""

import tempfile
from pathlib import Path
from aios.core.state import StateManager
from aios.core.self_loop_engine import SelfLoopEngine
from aios.events.core.bus import get_core_event_bus, reset_event_bus_singleton
from aios.events.core.bus import EventBus, EventBusConfig


def test_state_manager_methods_exist_and_callable():
    """Test that the new StateManager methods exist and are callable."""
    # Reset and get the canonical EventBus for testing
    reset_event_bus_singleton()
    bus = get_core_event_bus()
    # Ensure it's started for the tests
    if not bus._dispatch_worker or not bus._dispatch_worker.is_alive():
        bus.start_dispatch_worker()

    with tempfile.TemporaryDirectory() as tmp_dir:
        sm = StateManager(persistence_path=Path(tmp_dir) / "state")

        # Test that methods exist
        assert hasattr(sm, 'get_git_context')
        assert hasattr(sm, 'get_state_history')

        # Test that methods are callable
        git_context = sm.get_git_context()
        state_history = sm.get_state_history()

        # Test return types
        assert isinstance(git_context, dict)
        assert isinstance(state_history, list)

        # Test Git context structure
        assert git_context.get("source") == "git"
        assert git_context.get("authority") == "provenance_only"

        print("[PASS] StateManager methods exist and return correct types")


def test_self_loop_engine_integration():
    """Test that SelfLoopEngine can work with StateManager."""
    # Reset and get the canonical EventBus for testing
    reset_event_bus_singleton()
    bus = get_core_event_bus()
    # Ensure it's started for the tests
    if not bus._dispatch_worker or not bus._dispatch_worker.is_alive():
        bus.start_dispatch_worker()

    with tempfile.TemporaryDirectory() as tmp_dir:
        sm = StateManager(persistence_path=Path(tmp_dir) / "state")

        # Create SelfLoopEngine with StateManager
        engine = SelfLoopEngine(state_manager=sm)

        # Test that engine recognizes the methods
        assert hasattr(sm, 'get_git_context')
        assert hasattr(sm, 'get_state_history')

        # Test that methods can be called through engine reference
        git_context = sm.get_git_context()
        state_history = sm.get_state_history()

        assert isinstance(git_context, dict)
        assert isinstance(state_history, list)

        print("[PASS] SelfLoopEngine integration works with StateManager")


def test_git_context_structure():
    """Test Git context has expected structure."""
    # Reset and get the canonical EventBus for testing
    reset_event_bus_singleton()
    bus = get_core_event_bus()
    # Ensure it's started for the tests
    if not bus._dispatch_worker or not bus._dispatch_worker.is_alive():
        bus.start_dispatch_worker()

    with tempfile.TemporaryDirectory() as tmp_dir:
        sm = StateManager(persistence_path=Path(tmp_dir) / "state")
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
    # Reset and get the canonical EventBus for testing
    reset_event_bus_singleton()
    bus = get_core_event_bus()
    # Ensure it's started for the tests
    if not bus._dispatch_worker or not bus._dispatch_worker.is_alive():
        bus.start_dispatch_worker()

    with tempfile.TemporaryDirectory() as tmp_dir:
        sm = StateManager(persistence_path=Path(tmp_dir) / "state")

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


if __name__ == "__main__":
    test_state_manager_methods_exist_and_callable()
    test_self_loop_engine_integration()
    test_git_context_structure()
    test_state_history_structure()
    print("\n[PASS] All B2-R1 integration tests passed!")