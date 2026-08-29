#!/usr/bin/env python3
"""Simple reproduction of DEF-01: Production MCP connection crashes on stock boot."""

import sys
import traceback
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_def01_reproduction():
    """Reproduce DEF-01 by demonstrating the transport enum issue."""
    print("=== DEF-01 Reproduction Test ===")
    print("Testing MCP transport enum issue...")

    try:
        # Test 1: Show that JSON loading produces string transport, not enum
        import json
        from aios.core.mcp_manager import MCPServerConfig, MCPTransport

        # Simulate what happens in _load_configs when reading JSON
        sample_config_json = '''{
            "server_id": "test",
            "name": "Test Server",
            "transport": "stdio",
            "command": ["python", "-m", "test"],
            "url": null,
            "env": {}
        }'''

        print("1. Testing JSON loading behavior...")
        data = json.loads(sample_config_json)
        print(f"   JSON transport value: {data['transport']} (type: {type(data['transport'])})")

        # This is what happens in _load_configs - direct instantiation
        config = MCPServerConfig(**data)
        print(f"   Config transport value: {config.transport} (type: {type(config.transport)})")

        # Test 2: Show that this causes the security gate to fail
        print("\n2. Testing security gate access...")
        from aios.core.security_manager import SecurityManager

        # Create a security manager (we'll mock the event bus dependency)
        import asyncio
        from aios.events.core.bus import CoreEventBus
        from aios.events.core.identity import ComponentIdentity, ComponentType
        from aios.events.core.types import EventType, SemanticVersion

        # Mock the event bus to avoid initialization issues
        class MockEventBus:
            pass

        # Temporarily patch the get_core_event_bus function
        import aios.core.security_manager as sec_mod
        original_get_bus = sec_mod.get_core_event_bus
        sec_mod.get_core_event_bus = lambda: MockEventBus()

        try:
            security_manager = SecurityManager()

            # This is the exact line that fails in security_manager.py:665
            print(f"   Attempting to access: config.transport.value")
            print(f"   config.transport = {config.transport}")
            print(f"   type(config.transport) = {type(config.transport)}")

            # This should fail
            transport_value = config.transport.value
            print(f"   SUCCESS: transport.value = {transport_value}")

        except AttributeError as e:
            if "'str' object has no attribute 'value'" in str(e):
                print(f"   SUCCESSFULLY REPRODUCED DEF-01: {e}")
                return True
            else:
                print(f"   Different AttributeError: {e}")
                return False
        finally:
            # Restore original function
            sec_mod.get_core_event_bus = original_get_bus

    except Exception as e:
        print(f"Unexpected error during setup: {e}")
        traceback.print_exc()
        return False

    return False

if __name__ == "__main__":
    reproduced = test_def01_reproduction()
    if reproduced:
        print("\n=== RESULT: DEF-01 CONFIRMED ===")
        sys.exit(0)
    else:
        print("\n=== RESULT: DEF-01 NOT REPRODUCED ===")
        sys.exit(1)