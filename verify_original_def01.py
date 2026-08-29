#!/usr/bin/env python3
"""Verify the original DEF-01 failure still exists in the code before remediation check."""

import sys
import traceback
from pathlib import Path
import json

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_original_def01_failure():
    """Reproduce the original DEF-01 failure using stock-shaped JSON config."""
    print("=== Verifying Original DEF-01 Failure ===")
    print("Testing that JSON-loaded transport string causes AttributeError in SecurityManager")

    try:
        # Import necessary modules
        from aios.core.mcp_manager import MCPServerConfig
        from aios.core.security_manager import SecurityManager

        # Create a stock-shaped JSON configuration (as would be loaded from config/mcp/*.json)
        stock_json_config = {
            "server_id": "test_mcp",
            "name": "Test MCP Server",
            "transport": "stdio",  # This is the problematic string from JSON
            "command": ["python", "-m", "test"],
            "url": None,
            "env": {}
        }

        print(f"1. Stock JSON config transport value: {repr(stock_json_config['transport'])}")
        print(f"   Type: {type(stock_json_config['transport'])}")

        # This is exactly what happens in _load_configs() - direct instantiation from JSON data
        print("\n2. Creating MCPServerConfig from JSON data (simulating _load_configs)...")
        config = MCPServerConfig(**stock_json_config)
        print(f"   MCPServerConfig.transport: {repr(config.transport)}")
        print(f"   Type: {type(config.transport)}")
        print(f"   Is it still a string? {isinstance(config.transport, str)}")

        # Now test the exact failure point in SecurityManager
        print("\n3. Testing SecurityManager.gate_before_connect() (the failure point)...")

        # We need to handle the EventBus dependency issue
        import aios.core.security_manager as sec_mod
        from aios.events.core.bus import get_core_event_bus

        # Store original function
        original_get_bus = sec_mod.get_core_event_bus

        # Mock the event bus to avoid initialization issues
        class MockEventBus:
            pass

        sec_mod.get_core_event_bus = lambda: MockEventBus()

        try:
            security_manager = SecurityManager()
            print("   SecurityManager created successfully")

            # This is the EXACT line that fails in security_manager.py:665
            print("\n4. Reproducing the exact failure from security_manager.py:665:")
            print('   Line: config_str = f\"{server_id}:{name}:{transport.value}:{command}:{url}:{timeout}\"')

            try:
                # This should fail with AttributeError: 'str' object has no attribute 'value'
                transport_value = config.transport.value
                print(f"   UNEXPECTED: Success - transport.value = {transport_value}")
                print("   This would mean DEF-01 is already fixed!")
                return False  # DEF-01 not reproduced (unexpected)

            except AttributeError as e:
                error_msg = str(e)
                if "'str' object has no attribute 'value'" in error_msg and "transport" in error_msg:
                    print(f"   *** CONFIRMED ORIGINAL DEF-01 FAILURE: {error_msg} ***")
                    print("   Root cause: JSON-loaded string transport not converted to MCPTransport enum")
                    return True  # DEF-01 successfully reproduced
                else:
                    print(f"   Different AttributeError: {error_msg}")
                    return False

        finally:
            # Always restore the original function
            sec_mod.get_core_event_bus = original_get_bus

    except Exception as e:
        print(f"Unexpected error during testing: {e}")
        traceback.print_exc()
        return False

def show_expected_behavior():
    """Show what the behavior should be after proper fix."""
    print("\n\n=== Expected Behavior After Fix ===")

    try:
        from aios.core.mcp_manager import MCPServerConfig, MCPTransport

        print("After fix, JSON-loaded transport should become MCPTransport enum:")

        # Simulate what the fix should do
        stock_json_config = {
            "server_id": "test_mcp",
            "name": "Test MCP Server",
            "transport": "stdio",
            "command": ["python", "-m", "test"],
            "url": None,
            "env": {}
        }

        # Apply the fix manually to show expected behavior
        if "transport" in stock_json_config and isinstance(stock_json_config["transport"], str):
            stock_json_config["transport"] = MCPTransport(stock_json_config["transport"])

        print(f"   Fixed transport value: {repr(stock_json_config['transport'])}")
        print(f"   Type: {type(stock_json_config['transport'])}")
        print(f"   Is it MCPTransport.STDIO? {stock_json_config['transport'] == MCPTransport.STDIO}")

        config = MCPServerConfig(**stock_json_config)
        print(f"   MCPServerConfig.transport: {repr(config.transport)}")
        print(f"   Type: {type(config.transport)}")

        # This should now work
        try:
            transport_value = config.transport.value
            print(f"   SUCCESS: config.transport.value = {transport_value}")
            return True
        except AttributeError as e:
            print(f"   Still failing: {e}")
            return False

    except Exception as e:
        print(f"Error in expected behavior demo: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("PHASE 1: Establishing Previous DEF-01 Failure")
    print("=" * 50)

    # Test that we can reproduce the original failure
    original_failure_confirmed = test_original_def01_failure()
    expected_works = show_expected_behavior()

    print("\n" + "=" * 50)
    print("PHASE 1 RESULTS:")
    print(f"  Original DEF-01 failure confirmed: {'YES' if original_failure_confirmed else 'NO'}")
    print(f"  Expected fix behavior works: {'YES' if expected_works else 'NO'}")

    if original_failure_confirmed:
        print("\n  CONCLUSION: Original DEF-01 failure is verified and ready for remediation testing")
        sys.exit(0)
    else:
        print("\n  CONCLUSION: Could not verify original DEF-01 failure - may already be fixed")
        sys.exit(1)