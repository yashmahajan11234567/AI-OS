#!/usr/bin/env python3
"""Core reproduction of DEF-01: Show the transport enum issue."""

import sys
import traceback
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_def01_core_issue():
    """Demonstrate the core DEF-01 issue: JSON loading vs enum expectation."""
    print("=== DEF-01 Core Issue Demonstration ===")
    print("Showing that JSON loading produces string transport, not MCPTransport enum")

    try:
        import json
        from aios.core.mcp_manager import MCPServerConfig, MCPTransport

        # Simulate what happens in _load_configs when reading JSON files
        print("\n1. Loading MCP config from JSON (as done in _load_configs)...")
        sample_config_json = '''{
            "server_id": "graphify",
            "name": "Graphify",
            "transport": "stdio",
            "command": ["python", "-m", "aios.adapters.mock_graphify_server"],
            "url": null,
            "env": {}
        }'''

        data = json.loads(sample_config_json)
        print(f"   JSON data['transport']: {repr(data['transport'])}")
        print(f"   Type: {type(data['transport'])}")

        # This is exactly what happens in _load_configs line 131:
        # config = MCPServerConfig(**data)
        config = MCPServerConfig(**data)
        print(f"   MCPServerConfig.transport: {repr(config.transport)}")
        print(f"   Type: {type(config.transport)}")
        print(f"   Is it MCPTransport.STDIO? {config.transport == MCPTransport.STDIO}")
        print(f"   Is it equal to 'stdio'? {config.transport == 'stdio'}")

        # Show the problem: trying to access .value on a string
        print("\n2. Demonstrating the security gate failure...")
        print("   In security_manager.py line 665, code does:")
        print('   config_str = f\"{...}:{server_config.transport.value}:{...}\"')

        try:
            # This is the failing line
            transport_value = config.transport.value
            print(f"   SUCCESS: config.transport.value = {transport_value}")
            print("   UNEXPECTED: No error occurred!")
            return False
        except AttributeError as e:
            error_msg = str(e)
            print(f"   ERROR: {error_msg}")
            if "'str' object has no attribute 'value'" in error_msg:
                print("   *** CONFIRMED: This is exactly DEF-01 ***")
                return True
            else:
                print("   Different AttributeError")
                return False

    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()
        return False

def show_workaround():
    """Show how the conftest.py workaround avoids this issue."""
    print("\n\n3. Showing the conftest.py workaround...")

    try:
        from aios.core.mcp_manager import MCPServerConfig, MCPTransport

        # This is what conftest.py does - uses the enum directly
        print("   Creating MCPServerConfig with MCPTransport enum directly:")
        config = MCPServerConfig(
            server_id="graphify",
            name="Graphify",
            transport=MCPTransport.STDIO,  # <-- ENUM, not string
            command=["python", "-m", "aios.adapters.mock_graphify_server"],
            url=None,
            env={}
        )
        print(f"   MCPServerConfig.transport: {repr(config.transport)}")
        print(f"   Type: {type(config.transport)}")

        # This works fine
        try:
            transport_value = config.transport.value
            print(f"   SUCCESS: config.transport.value = {transport_value}")
            print("   *** This is why conftest.py bypasses the issue ***")
        except AttributeError as e:
            print(f"   Unexpected error: {e}")
            return False

        return True

    except Exception as e:
        print(f"Unexpected error in workaround demo: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("DEF-01 Root Cause Analysis")
    print("=" * 50)

    issue_reproduced = test_def01_core_issue()
    workaround_works = show_workaround()

    print("\n" + "=" * 50)
    print("SUMMARY:")
    print(f"  DEF-01 Issue Reproduced: {'YES' if issue_reproduced else 'NO'}")
    print(f"  Workaround Valid: {'YES' if workaround_works else 'NO'}")

    if issue_reproduced:
        print("\n  ROOT CAUSE: JSON loader does not convert string 'transport' to MCPTransport enum")
        print("  LOCATION: mcp_manager.py:_load_configs() line 131")
        print("  EFFECT: security_manager.py:665 tries to access .value on string -> AttributeError")
        print("\n  FIX NEEDED: Coerce transport field to MCPTransport enum in _load_configs")
        sys.exit(0)
    else:
        print("\n  Unable to reproduce the core issue")
        sys.exit(1)