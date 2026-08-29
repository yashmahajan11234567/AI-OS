#!/usr/bin/env python3
"""Debug what's really happening with transport field."""

import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "sys"))
sys.path.insert(0, str(Path(__file__).parent / "src"))

def debug_transport():
    """Debug the transport field type."""
    print("=== Debugging Transport Field ===")

    try:
        from aios.core.mcp_manager import MCPServerConfig, MCPTransport

        # Test data exactly as JSON would provide
        stock_json_data = {
            "server_id": "test",
            "name": "Test Server",
            "transport": "stdio",  # This is a STRING from JSON
            "command": ["python", "-m", "test"],
            "url": None,
            "env": {}
        }

        print(f"Input transport: {repr(stock_json_data['transport'])}")
        print(f"Input transport type: {type(stock_json_data['transport'])}")
        print(f"isinstance(input_transport, str): {isinstance(stock_json_data['transport'], str)}")

        # Create the MCPServerConfig (this should trigger __post_init__)
        config = MCPServerConfig(**stock_json_data)

        print(f"\nAfter MCPServerConfig creation:")
        print(f"  config.transport = {repr(config.transport)}")
        print(f"  type(config.transport) = {type(config.transport)}")
        print(f"  isinstance(config.transport, str) = {isinstance(config.transport, str)}")
        print(f"  isinstance(config.transport, MCPTransport) = {isinstance(config.transport, MCPTransport)}")

        # Let's also check what the raw __dict__ shows
        print(f"\nConfig __dict__ transport: {repr(config.__dict__.get('transport', 'NOT FOUND'))}")

        # Test direct access to .value
        try:
            value = config.transport.value
            print(f"\n  config.transport.value = {repr(value)} (SUCCESS!)")
        except AttributeError as e:
            print(f"\n  config.transport.value FAILED: {e}")

        return not isinstance(config.transport, str) and isinstance(config.transport, MCPTransport)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = debug_transport()
    print(f"\nResult: Transport properly fixed = {result}")