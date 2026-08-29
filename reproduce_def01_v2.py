#!/usr/bin/env python3
"""Minimal reproduction of DEF-01: Production MCP connection crashes on stock boot."""

import sys
import traceback
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_def01_reproduction():
    """Reproduce DEF-01 by loading MCP configs the normal way and attempting security validation."""
    print("=== DEF-01 Reproduction Test ===")
    print("Testing stock boot MCP config loading...")

    try:
        # Initialize the kernel first to set up the event bus
        from aios.core.kernel import HermesKernel
        from aios.core.config import KernelConfig

        print("Initializing HermesKernel...")
        kernel = HermesKernel(KernelConfig())

        # Now the MCP manager should be initialized
        if kernel._mcp_manager is None:
            print("ERROR: MCP manager not initialized")
            return False

        print(f"MCP Manager initialized with {len(kernel._mcp_manager._servers)} server configs")

        # Try to validate one of the servers through SecurityManager (this should trigger DEF-01)
        print("Attempting security validation on first server...")
        server_id = list(kernel._mcp_manager._servers.keys())[0]
        server_config = kernel._mcp_manager._servers[server_id]
        print(f"Testing server: {server_config.server_id}")
        print(f"Transport type: {type(server_config.transport)}")
        print(f"Transport value: {server_config.transport}")

        # This is where the error occurs - in security_manager.py line 665
        from aios.core.security_manager import get_security_manager
        security_manager = get_security_manager()

        print("Calling security manager gate_before_connect...")
        # This should crash with AttributeError: 'str' object has no attribute 'value'
        result = security_manager.gate_before_connect(server_config)
        print(f"Security gate result: {result}")
        print("UNEXPECTED: No error occurred!")

    except AttributeError as e:
        if "transport" in str(e) and "'str' object has no attribute 'value'" in str(e):
            print(f"SUCCESSFULLY REPRODUCED DEF-01: {e}")
            print("\nFull traceback:")
            traceback.print_exc()
            return True
        else:
            print(f"Different AttributeError: {e}")
            traceback.print_exc()
            return False
    except Exception as e:
        print(f"Unexpected error: {e}")
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