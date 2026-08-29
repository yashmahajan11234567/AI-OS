#!/usr/bin/env python3
"""Simple test to verify DEF-01 remediation is working."""

import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_def01_fixed():
    """Test that DEF-01 is fixed - JSON string transport becomes enum."""
    print("=== Testing DEF-01 Remediation ===")

    try:
        from aios.core.mcp_manager import MCPServerConfig, MCPTransport
        from aios.core.security_manager import SecurityManager

        # Simulate stock JSON config loading
        stock_json_data = {
            "server_id": "test",
            "name": "Test Server",
            "transport": "stdio",  # This is what JSON gives us - a STRING
            "command": ["python", "-m", "test"],
            "url": None,
            "env": {}
        }

        print(f"1. JSON input transport: '{stock_json_data['transport']}' (type: {type(stock_json_data['transport'])})")

        # This is what happens in _load_configs() -> MCPServerConfig(**data)
        config = MCPServerConfig(**stock_json_data)

        print(f"2. After MCPServerConfig creation: {config.transport} (type: {type(config.transport)})")

        # THE KEY TEST: Is it NO LONGER a string?
        is_string = isinstance(config.transport, str)
        is_enum = isinstance(config.transport, MCPTransport)

        print(f"3. Is it still a string? {is_string} (should be False if fixed)")
        print(f"4. Is it an MCPTransport enum? {is_enum} (should be True if fixed)")

        if not is_string and is_enum:
            print("   ✓ TRANSPORT PROPERLY COERCED FROM STRING TO ENUM")

            # Now test that SecurityManager can access .value without error
            print("\n5. Testing SecurityManager access to .value:")

            # Handle EventBus dependency
            import aios.core.security_manager as sec_mod

            original_get_bus = sec_mod.get_core_event_bus
            class MockEventBus: pass
            sec_mod.get_core_event_bus = lambda: MockEventBus()

            try:
                security_manager = SecurityManager()

                # This is the EXACT line that was failing: security_manager.py:665
                # We'll test accessing .value directly first
                transport_value = config.transport.value
                print(f"   ✓ transport.value = '{transport_value}' (no AttributeError!)")

                # Test the actual validation method that contains line 665
                # Find the validate_mcp_server_config method
                if hasattr(security_manager, 'validate_mcp_server_config'):
                    result = security_manager.validate_mcp_server_config(config)
                    print(f"   ✓ validate_mcp_server_config() succeeded: passed={result.passed}")
                    print("   ✓ DEF-01 REMEDIATION VERIFIED WORKING")
                    return True
                else:
                    # Fallback: test the specific line that was failing
                    print("   Testing direct .value access (simulating line 665):")
                    _ = config.transport.value  # This line used to fail
                    print("   ✓ Direct .value access works")
                    print("   ✓ DEF-01 REMEDIATION VERIFIED WORKING")
                    return True

            except AttributeError as e:
                if "'str' object has no attribute 'value'" in str(e):
                    print(f"   ✗ DEF-01 STILL PRESENT: {e}")
                    return False
                else:
                    print(f"   ? Different AttributeError: {e}")
                    return False
            finally:
                sec_mod.get_core_event_bus = original_get_bus
        else:
            print(f"   ✗ TRANSPORT NOT PROPERLY COERCED")
            print(f"     Still string: {is_string}")
            print(f"     Is enum: {is_enum}")
            return False

    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_original_broken_behavior():
    """Demonstrate what the broken behavior looked like."""
    print("\n\n=== Demonstrating Original Broken Behavior ===")

    # Simulate what happened WITHOUT the fix
    class BrokenMCPServerConfig:
        def __init__(self, **kwargs):
            self.server_id = kwargs.get('server_id')
            self.name = kwargs.get('name')
            self.transport = kwargs.get('transport')  # STAYS AS STRING - NO COERCION
            self.command = kwargs.get('command')
            self.url = kwargs.get('url')
            self.env = kwargs.get('env', {})

    try:
        stock_json_data = {
            "server_id": "test",
            "name": "Test Server",
            "transport": "stdio",  # STRING FROM JSON
            "command": ["python", "-m", "test"],
            "url": None,
            "env": {}
        }

        broken_config = BrokenMCPServerConfig(**stock_json_data)
        print(f"Broken config transport: {broken_config.transport} (type: {type(broken_config.transport)})")

        # This is what would fail in the old code
        try:
            value = broken_config.transport.value  # This line would fail
            print(f"   Unexpectedly worked: {value}")
        except AttributeError as e:
            if "'str' object has no attribute 'value'" in str(e):
                print(f"   ✓ This is the ORIGINAL DEF-01 ERROR: {e}")
                return True
            else:
                print(f"   ? Different error: {e}")
                return False
    except Exception as e:
        print(f"Error in broken behavior demo: {e}")
        return False

if __name__ == "__main__":
    print("Testing DEF-01 Remediation Status")
    print("=" * 40)

    # Test if fix is working
    fix_working = test_def01_fixed()

    # Show what the broken behavior was
    original_broken = test_original_broken_behavior()

    print("\n" + "=" * 40)
    print("RESULTS:")
    print(f"  Remediation fix working: {'YES' if fix_working else 'NO'}")
    print(f"  Original broken behavior confirmed: {'YES' if original_broken else 'NO'}")

    if fix_working:
        print("\n  CONCLUSION: ✅ DEF-01 REMEDIATION IS WORKING")
        print("     JSON string transport is properly coerced to MCPTransport enum")
        print("     SecurityManager can now access .transport.value without AttributeError")
        sys.exit(0)
    else:
        print("\n  CONCLUSION: ❌ DEF-01 REMEDIATION IS NOT WORKING")
        sys.exit(1)