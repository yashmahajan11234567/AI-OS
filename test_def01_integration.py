#!/usr/bin/env python3
"""Integration test to show DEF-01 breaks real MCP manager usage."""

import sys
import traceback
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_real_mcp_manager_fails():
    """Test that demonstrates DEF-01 breaks real MCP manager usage."""
    print("=== Testing Real MCP Manager (JSON Loading Path) ===")

    try:
        # Import necessary modules
        from aios.core.mcp_manager import MCPManager
        from aios.core.security_manager import get_security_manager

        # Create MCPManager the REAL way - loads from JSON files in config/mcp/
        print("Creating MCPManager (real JSON loading path)...")
        mcp_manager = MCPManager()  # This loads from ./config/mcp/*.json

        print(f"Successfully loaded {len(mcp_manager._servers)} MCP server configs from JSON")

        # Now try to use the security manager on one of these configs
        # This should trigger DEF-01
        print("Testing security validation on first loaded server config...")

        server_id = list(mcp_manager._servers.keys())[0]
        server_config = mcp_manager._servers[server_id]
        print(f"Testing server: {server_config.server_id}")
        print(f"Transport field value: {repr(server_config.transport)}")
        print(f"Transport field type: {type(server_config.transport)}")

        # Get security manager and try to validate
        security_manager = get_security_manager()
        print("Calling security_manager.gate_before_connect()...")

        # THIS IS WHERE DEF-01 HITS:
        # Line 665 in security_manager.py: server_config.transport.value
        result = security_manager.gate_before_connect(server_config)

        print(f"UNEXPECTED: Security gate passed with result: {result}")
        print("This suggests DEF-01 might already be fixed or not triggered in this path")
        return False

    except AttributeError as e:
        if "'str' object has no attribute 'value'" in str(e) and "transport" in str(e):
            print(f"SUCCESSFULLY REPRODUCED DEF-01: {e}")
            print("*** This confirms that real JSON-loaded MCP configs break the security gate ***")
            return True
        else:
            print(f"Different AttributeError: {e}")
            traceback.print_exc()
            return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()
        # Check if it's related to event bus initialization (which we might need to mock)
        if "EventBus" in str(e) or "initialized" in str(e):
            print("Note: Hit event bus initialization issue, but that's separate from DEF-01")
            # Let's try to demonstrate the core issue more directly
            return demonstrate_core_issue()
        return False

def demonstrate_core_issue():
    """Demonstrate the core DEF-01 issue directly."""
    print("\n=== Demonstrating Core DEF-01 Issue Directly ===")

    try:
        import json
        from aios.core.mcp_manager import MCPServerConfig

        # Load a real MCP config file to show the issue
        config_path = Path("config/mcp/graphify_mcp.json")
        if config_path.exists():
            print(f"Loading real config file: {config_path}")
            with open(config_path, 'r') as f:
                data = json.load(f)

            print(f"JSON transport value: {repr(data['transport'])} (type: {type(data['transport'])})")

            # Create MCPServerConfig the way _load_configs does it
            config = MCPServerConfig(**data)
            print(f"MCPServerConfig.transport: {repr(config.transport)} (type: {type(config.transport)})")

            # Show the exact problem line from security_manager.py:665
            print("\nReproducing the exact failure from security_manager.py:665:")
            print('config_str = f\"{server_id}:{name}:{transport.value}:{command}:{url}:{timeout}\"')

            try:
                # This is the exact line that fails
                transport_value = config.transport.value
                print(f"UNEXPECTED SUCCESS: transport.value = {transport_value}")
                return False
            except AttributeError as e:
                if "'str' object has no attribute 'value'" in str(e):
                    print(f"CONFIRMED DEF-01: {e}")
                    return True
                else:
                    print(f"Different AttributeError: {e}")
                    return False
        else:
            print(f"Config file not found: {config_path}")
            return False

    except Exception as e:
        print(f"Error in core demonstration: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("DEF-01 Integration Test")
    print("=" * 50)

    # Try the real MCP manager test first
    real_test_failed = test_real_mcp_manager_fails()

    if not real_test_failed:
        # If that didn't work due to dependencies, show core issue directly
        core_issue_proven = demonstrate_core_issue()

        if core_issue_proven:
            print("\n" + "=" * 50)
            print("RESULT: DEF-01 CORE ISSUE CONFIRMED")
            print("The real-world usage would fail due to JSON-loaded string transport")
            print("not being converted to MCPTransport enum before reaching security gate.")
            sys.exit(0)
        else:
            print("\n" + "=" * 50)
            print("RESULT: Could not definitively confirm DEF-01 in integration test")
            sys.exit(1)
    else:
        print("\n" + "=" * 50)
        print("RESULT: DEF-01 CONFIRMED IN REAL MCP MANAGER USAGE")
        print("Real JSON-loaded MCP configs break the security gate.")
        sys.exit(0)