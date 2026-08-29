#!/usr/bin/env python3
"""Test that the DEF-01 remediation is working correctly."""

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
        print(f"   Is it still a string? {isinstance(config.transport, str)}")

        # Test the exact failure point in SecurityManager - should now work
        print("\n4. Testing SecurityManager.gate_before_connect() (should now work):")

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

            # This is the EXACT line that used to fail in security_manager.py:665
            print("\n5. Testing the former failure point from security_manager.py:665:")
            print('   Line: config_str = f\"{server_id}:{name}:{transport.value}:{command}:{url}:{timeout}\"')

            try:
                # This should now work because config.transport is an MCPTransport enum
                transport_value = config.transport.value
                server_id_val = config.server_id
                name_val = config.name
                command_val = str(config.command) if config.command else "None"
                url_val = str(config.url) if config.url else "None"
                timeout_val = config.timeout_seconds

                config_str = f"{server_id_val}:{name_val}:{transport_value}:{command_val}:{url_val}:{timeout_val}"
                print(f"   SUCCESS: Generated config_str = {config_str}")
                print(f"   transport.value = {repr(transport_value)} (type: {type(transport_value)})")

                # Test the actual security gate method
                print("\n6. Testing security_manager.gate_before_connect() method:")
                result = security_manager.gate_before_connect(config)
                print(f"   SUCCESS: gate_before_connect returned: {result}")
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

def test_all_valid_transports():
    """Test that all valid transport strings are handled correctly."""
    print("\n\n=== Testing All Valid Transport Strings ===")

    try:
        from aios.core.mcp_manager import MCPServerConfig, MCPTransport, coerce_transport

        valid_transports = ["stdio", "http", "sse", "websocket"]
        all_passed = True

        for transport_str in valid_transports:
            print(f"\nTesting transport: {transport_str}")

            # Test direct coercion
            coerced = coerce_transport(transport_str)
            expected = MCPTransport(transport_str)
            if coerced == expected:
                print(f"   ✓ coerce_transport('{transport_str}') = {repr(coerced)}")
            else:
                print(f"   ✗ coerce_transport('{transport_str}') = {repr(coerced)}, expected {repr(expected)}")
                all_passed = False

            # Test through MCPServerConfig
            config_data = {
                "server_id": f"test_{transport_str}",
                "name": f"Test {transport_str.upper()}",
                "transport": transport_str,
                "command": ["python", "-m", "test"] if transport_str == "stdio" else None,
                "url": "http://test.com" if transport_str in ["http", "sse", "websocket"] else None,
                "env": {}
            }

            # Remove None values for clean config
            config_data = {k: v for k, v in config_data.items() if v is not None}

            config = MCPServerConfig(**config_data)
            if config.transport == expected:
                print(f"   ✓ MCPServerConfig.transport = {repr(config.transport)}")
            else:
                print(f"   ✗ MCPServerConfig.transport = {repr(config.transport)}, expected {repr(expected)}")
                all_passed = False

        return all_passed

    except Exception as e:
        print(f"Error testing valid transports: {e}")
        traceback.print_exc()
        return False

def test_invalid_transports():
    """Test that invalid transport values fail deterministically."""
    print("\n\n=== Testing Invalid Transport Values (Should Fail) ===")

    try:
        from aios.core.mcp_manager import coerce_transport

        invalid_transports = ["invalid", "UNKNOWN", "", "STDIO", "Http", 123, None]
        all_passed = True

        for invalid_transport in invalid_transports:
            print(f"\nTesting invalid transport: {repr(invalid_transport)}")

            try:
                result = coerce_transport(invalid_transport)
                print(f"   ✗ coerce_transport({repr(invalid_transport)}) = {repr(result)} - SHOULD HAVE FAILED!")
                all_passed = False
            except ValueError as e:
                print(f"   ✓ Correctly raised ValueError: {str(e)[:60]}...")
            except Exception as e:
                print(f"   ? Raised {type(e).__name__}: {e}")
                # This might be okay depending on the type

        return all_passed

    except Exception as e:
        print(f"Error testing invalid transports: {e}")
        traceback.print_exc()
        return False

def test_enum_passthrough():
    """Test that existing MCPTransport enum instances pass through unchanged."""
    print("\n\n=== Testing MCPTransport Enum Passthrough ===")

    try:
        from aios.core.mcp_manager import MCPServerConfig, MCPTransport, coerce_transport

        all_passed = True

        for transport_enum in MCPTransport:
            print(f"\nTesting enum passthrough: {transport_enum}")

            # Test direct coercion (should return same enum)
            result = coerce_transport(transport_enum)
            if result is transport_enum:
                print(f"   ✓ coerce_transport({transport_enum}) is same object: {result is transport_enum}")
            else:
                print(f"   ✗ coerce_transport({transport_enum}) = {repr(result)} - should be same object")
                all_passed = False

            # Test through MCPServerConfig with enum input
            config_data = {
                "server_id": f"test_{transport_enum.value}",
                "name": f"Test {transport_enum.value.upper()}",
                "transport": transport_enum,  # Pass enum directly
                "env": {}
            }

            # Add appropriate command/url based on transport type
            if transport_enum == MCPTransport.STDIO:
                config_data["command"] = ["python", "-m", "test"]
            elif transport_enum in [MCPTransport.HTTP, MCPTransport.SSE, MCPTransport.WEBSOCKET]:
                config_data["url"] = "http://test.com"

            config = MCPServerConfig(**config_data)
            if config.transport is transport_enum:
                print(f"   ✓ MCPServerConfig.transport is same enum object: {config.transport is transport_enum}")
            else:
                print(f"   ✗ MCPServerConfig.transport = {repr(config.transport)} - should be {repr(transport_enum)}")
                all_passed = False

        return all_passed

    except Exception as e:
        print(f"Error testing enum passthrough: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("PHASE 2: Inspecting the Remediation")
    print("=" * 50)

    # Test the core fix
    remediation_works = test_remediation_fix()

    # Test all required properties
    valid_transports_work = test_all_valid_transports()
    invalid_transports_fail = test_invalid_transports()
    enum_passthrough_works = test_enum_passthrough()

    print("\n" + "=" * 50)
    print("PHASE 2 RESULTS:")
    print(f"  Core remediation fix works: {'YES' if remediation_works else 'NO'}")
    print(f"  All valid transports handled: {'YES' if valid_transports_work else 'NO'}")
    print(f"  Invalid transports fail deterministically: {'YES' if invalid_transports_fail else 'NO'}")
    print(f"  MCPTransport enum passthrough works: {'YES' if enum_passthrough_works else 'NO'}")

    all_checks_pass = remediation_works and valid_transports_work and invalid_transports_fail and enum_passthrough_works

    if all_checks_pass:
        print("\n  CONCLUSION: All remediation checks PASSED - DEF-01 appears to be properly fixed")
        sys.exit(0)
    else:
        print("\n  CONCLUSION: Some remediation checks FAILED -DEF-01 may not be properly fixed")
        sys.exit(1)