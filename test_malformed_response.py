#!/usr/bin/env python3
"""Test script to verify adapter responses to malformed MCP responses."""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from aios.adapters.notion_adapter import NotionAdapter
from aios.adapters.obsidian_adapter import ObsidianAdapter
from aios.adapters.graphify_adapter import GraphifyAdapter
from aios.adapters.claude_mem_adapter import ClaudeMemAdapter
from aios.core.mcp_manager import MCPManager
from unittest.mock import AsyncMock, Mock


async def test_adapter_malformed_response(adapter_class, adapter_name):
    """Test how an adapter handles malformed MCP responses."""
    print(f"\nTesting {adapter_name}...")

    # Create a mock MCP manager that returns malformed responses
    mock_mcp_manager = AsyncMock()
    mock_mcp_manager.call_tool.return_value = {
        "unexpected": True,
        "raw": "not-a-valid-result"
    }

    # Create adapter instance
    adapter = adapter_class(mcp_manager=mock_mcp_manager, server_id="test")
    adapter._connected = True  # Simulate connected state

    try:
        # Try to call an operation
        if adapter_name == "Notion":
            result = await adapter.search_pages("test")
        elif adapter_name == "Obsidian":
            result = await adapter.search_notes("test")
        elif adapter_name == "Graphify":
            result = await adapter.store_node("test1", "TestNode", {"property": "value"})
        elif adapter_name == "Claude-Mem":
            result = await adapter.retrieve_context("test")

        print(f"  Result status: {result.status}")
        if result.status == "success":
            print(f"  *** INCORRECT: Treated malformed response as SUCCESS")
            return False
        elif result.status == "error":
            print(f"  *** CORRECT: Treated malformed response as ERROR")
            return True
        else:
            print(f"  ??? UNEXPECTED: Got status {result.status}")
            return False

    except Exception as e:
        print(f"  !!! EXCEPTION: {e}")
        # Some adapters might raise exceptions instead of returning ERROR results
        # This is also acceptable behavior for malformed responses
        print(f"  *** ACCEPTABLE: Raised exception for malformed response")
        return True


async def main():
    """Run the test for all adapters."""
    print("Testing adapter responses to malformed MCP responses...")

    adapters = [
        (NotionAdapter, "Notion"),
        (ObsidianAdapter, "Obsidian"),
        (GraphifyAdapter, "Graphify"),
        (ClaudeMemAdapter, "Claude-Mem")
    ]

    results = []
    for adapter_class, adapter_name in adapters:
        try:
            result = await test_adapter_malformed_response(adapter_class, adapter_name)
            results.append((adapter_name, result))
        except Exception as e:
            print(f"  !!! FAILED to test {adapter_name}: {e}")
            results.append((adapter_name, False))

    print("\n" + "="*50)
    print("SUMMARY:")
    all_correct = True
    for adapter_name, correct in results:
        status = "PASS" if correct else "FAIL"
        print(f"  {adapter_name}: [{status}]")
        if not correct:
            all_correct = False

    if all_correct:
        print("\n*** All adapters handle malformed responses correctly!")
    else:
        print("\n!!! Some adapters have issues with malformed responses.")

    return all_correct


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)