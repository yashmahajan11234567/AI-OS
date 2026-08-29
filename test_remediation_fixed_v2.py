#!/usr/bin/env python3
"""Test that the DEF-01 remediation is working correctly - corrected version."""

import sys
import traceback
from pathlib import Path
import json

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_remediation_fix():
    """Test that the remediation fixes DEF-01 by coercing JSON string to enum."""
    print("=== Testing DEF-01 Remediation Fix ===")
    print("Verifying that JSON-loaded transport string is properly coerced to MCPTransport enum")

    try:
        # Import necessary modules
        from aios.core.mcp_manager import MCPServerConfig, MCPTransport, coerce_transport
        from aios.core.security_manager import SecurityManager

        # Create a stock-shaped JSON configuration (as would be loaded from config/mcp/*.json)
        stock_json_config = {
            "server_id": "test_mcp",
            "name": "Test MCP Server",
            "transport": "stdio",  # This was the problematic string from JSON
            "command": ["python", "-m", "test"],
            "url": None,
            "env": {}
        }

        print(f"1. Input JSON config transport value: {repr(stock_json_config['transport'])}")
        print(f"   Type: {type(stock_json_config['transport'])}")

        # Test the coerce_transport function directly
        print("\n2. Testing coerce_transport function:")
        coerced = coerce_transport(stock_json_config["transport"])
        print(f"   coerce_transport('stdio') = {repr(coerced)}")
        print(f"   Type: {type(coerced)}")
        print(f"   Is MCPTransport.STDIO? {coerced == MCPTransport.STDIO}")

        # Test that MCPServerConfig.__post_init__ works correctly
        print("\n3. Testing MCPServerConfig creation (this triggers __post_init__):")
        config = MCPServerConfig(**stock_json_config)
        print(f"   MCPServerConfig.transport: {repr(config.transport)}")
        print(f"   Type: {type(config.transport)}")
        print(f"   Is MCPTransport.STDIO? {config.transport == MCPTransport.STDIO}")

        # The key test: Is it NO LONGER a string? (This was the bug)
        is_still_string = isinstance(config.transport, str)
        print(f"   Is it still a string? {is_still_string} (should be False after fix)")

        # Test the exact failure point in SecurityManager - should now work
        print("\n4. Testing SecurityManager.validate_mcp_server_config() (should now work):")

        # Handle EventBus dependency
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

            # Test the exact line that used to fail (now line 665 in validate_mcp_server_config)
            print("\n5. Testing the former failure point from security_manager.py:665:")
            print('   Line in validate_mcp_server_config: config_str = f\"{server_id}:{name}:{transport.value}:{command}:{url}:{timeout}\"')

            try:
                # This should now work because config.transport is an MCPTransport enum
                transport_value = config.transport.value
                print(f"   SUCCESS: transport.value = {repr(transport_value)} (type: {type(transport_value)})")
                print(f"   This confirms the transport is now properly an enum!")

                # Test the actual validation method
                print("\n6. Testing security_manager.validate_mcp_server_config() method:")
                result = security_manager.validate_mcp_server_config(config)
                print(f"   SUCCESS: validate_mcp_server_config returned: {result}")
                print(f"   Passed: {result.passed}")
                print("   REMediation VERIFIED: DEF-01 is fixed!")

                return True  # Remediation working correctly

            except AttributeError as e:
                error_msg = str(e)
                if "'str' object has no attribute 'value'" in error_msg:
                    print(f"   FAILURE: DEF-01 still present: {error_msg}")
                    return False  # Remediation not working
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

def test_stock_json_loading_via_mcp_manager():
    """Test the actual stock JSON loading path via MCPManager."""
    print("\n\n=== Testing Stock JSON Loading via MCPManager ===")

    try:
        from aios.core.mcp_manager import MCPManager
        import tempfile
        import os
        import shutil

        # Create a temporary directory with stock JSON config
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "mcp"
            config_dir.mkdir()

            # Create a stock-shaped JSON config file (exactly as would exist in config/mcp/)
            stock_config = {
                "server_id": "graphify",
                "name": "Graphify",
                "transport": "stdio",
                "command": ["python", "-m", "aios.adapters.mock_graphify_server"],
                "url": None,
                "env": {}
            }

            config_file = config_dir / "graphify_mcp.json"
            with open(config_file, 'w') as f:
                json.dump(stock_config, f, indent=2)

            print(f"1. Created stock JSON config: {config_file}")
            print(f"   Content transport value: {repr(stock_config['transport'])}")

            # Test the actual MCPManager loading from JSON (this is the production path)
            print("\n2. Testing MCPManager loading from stock JSON config:")
            mcp_manager = MCPManager(config_dir=config_dir)

            print(f"   Loaded {len(mcp_manager._servers)} server configs")

            if len(mcp_manager._servers) > 0:
                server_id = list(mcp_manager._servers.keys())[0]
                server_config = mcp_manager._servers[server_id]
                print(f"   Loaded server: {server_config.server_id}")
                print(f"   MCPServerConfig.transport: {repr(server_config.transport)}")
                print(f"   Type: {type(server_config.transport)}")
                print(f"   Is MCPTransport.STDIO? {server_config.transport == MCPTransport.STDIO}")
                print(f"   Is it still a string? {isinstance(server_config.transport, str)} (should be False)")

                # Critical test: Can we now validate this without AttributeError?
                print("\n3. Testing SecurityManager validation on loaded config:")

                import aios.core.security_manager as sec_mod
                from aios.events.core.bus import get_core_event_bus

                original_get_bus = sec_mod.get_core_event_bus
                class MockEventBus: pass
                sec_mod.get_core_event_bus = lambda: MockEventBus()

                try:
                    security_manager = SecurityManager()
                    result = security_manager.validate_mcp_server_config(server_config)
                    print(f"   SUCCESS: Validation passed = {result.passed}")
                    print("   STOCK JSON LOADING PATH VERIFIED: DEF-01 is fixed!")
                    return True
                except AttributeError as e:
                    if "'str' object has no attribute 'value'" in str(e):
                        print(f"   FAILURE: DEF-01 still present in stock path: {e}")
                        return False
                    else:
                        print(f"   Different AttributeError: {e}")
                        return False
                finally:
                    sec_mod.get_core_event_bus = original_get_bus
            else:
                print("   ERROR: No servers loaded")
                return False

    except Exception as e:
        print(f"Unexpected error during stock JSON loading test: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("PHASE 2: Inspecting the Remediation (CORRECTED)")
    print("=" * 50)

    # Test the core fix
    remediation_works = test_remediation_fix()

    # Test the actual stock JSON loading path
    stock_path_works = test_stock_json_loading_via_mcp_manager()

    print("\n" + "=" * 50)
    print("PHASE 2 RESULTS:")
    print(f"  Core remediation fix works: {'YES' if remediation_works else 'NO'}")
    print(f"  Stock JSON loading path works: {'YES' if stock_path_works else 'NO'}")

    if remediation_works and stock_path_works:
        print("\n  CONCLUSION: Remediation is working correctly - DEF-01 is fixed")
        sys.exit(0)
    else:
        print("\n  CONCLUSION: Remediation has issues - DEF-01 may not be properly fixed")
        sys.exit(1)