#!/usr/bin/env python3
"""
Mock Agent-Reach MCP Server for AI-OS M5-GATE-REALIZE testing.

Provides a local mock Agent-Reach server that implements the MCP protocol
for testing the AgentReachAdapter without requiring an external service.
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Any


class MockAgentReachServer:
    """Mock Agent-Reach MCP server with basic web/social search."""

    def __init__(self):
        self._initialized = False

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle incoming MCP request."""
        method = request.get("method", "")
        request_id = request.get("id")

        try:
            if method == "initialize":
                return await self._handle_initialize(request)
            elif method == "tools/list":
                return await self._handle_tools_list(request)
            elif method == "tools/call":
                return await self._handle_tool_call(request)
            elif method == "notifications/initialized":
                self._initialized = True
                return {"jsonrpc": "2.0"}
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
            }

    async def _handle_initialize(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle initialize request."""
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "Mock Agent-Reach Server",
                    "version": "0.1.0",
                },
            },
        }

    async def _handle_tools_list(self, request: dict[str, Any]) -> dict[str, Any]:
        """List available tools."""
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "tools": [
                    {
                        "name": "web_search",
                        "description": "Search the web for content",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "max_results": {"type": "integer", "default": 10},
                                "sources": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["query"],
                        },
                    },
                    {
                        "name": "social_search",
                        "description": "Search social media for content",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "platform": {"type": "string"},
                                "max_results": {"type": "integer", "default": 10},
                            },
                            "required": ["query"],
                        },
                    },
                    {
                        "name": "news_search",
                        "description": "Search news for content",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "max_results": {"type": "integer", "default": 10},
                            },
                            "required": ["query"],
                        },
                    },
                ],
            },
        }

    async def _handle_tool_call(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle tool call."""
        params = request.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        request_id = request.get("id")

        try:
            if tool_name == "web_search":
                result = await self._web_search(arguments)
            elif tool_name == "social_search":
                result = await self._social_search(arguments)
            elif tool_name == "news_search":
                result = await self._news_search(arguments)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
                }

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"success": True, "result": result},
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"success": False, "error": str(e)},
            }

    async def _web_search(self, args: dict[str, Any]) -> dict[str, Any]:
        """Mock web search."""
        query = args.get("query", "")
        max_results = args.get("max_results", 10)

        # Return mock results
        results = [
            {
                "title": f"Result {i}: {query}",
                "snippet": f"This is a mock search result snippet for query '{query}' - result {i}",
                "url": f"https://example.com/result/{i}",
            }
            for i in range(1, min(max_results, 5) + 1)
        ]

        return {"results": results, "total": len(results), "query": query}

    async def _social_search(self, args: dict[str, Any]) -> dict[str, Any]:
        """Mock social media search."""
        query = args.get("query", "")
        platform = args.get("platform", "twitter")
        max_results = args.get("max_results", 10)

        results = [
            {
                "author": f"user{i}",
                "text": f"Mock social post about '{query}' from @user{i}",
                "url": f"https://{platform}.com/user{i}/status/{i}",
                "platform": platform,
            }
            for i in range(1, min(max_results, 5) + 1)
        ]

        return {"posts": results, "total": len(results), "query": query, "platform": platform}

    async def _news_search(self, args: dict[str, Any]) -> dict[str, Any]:
        """Mock news search."""
        query = args.get("query", "")
        max_results = args.get("max_results", 10)

        results = [
            {
                "title": f"News {i}: {query}",
                "description": f"Mock news article about '{query}' - article {i}",
                "url": f"https://news.example.com/article/{i}",
                "source": {"name": f"NewsSource{i}"},
            }
            for i in range(1, min(max_results, 5) + 1)
        ]

        return {"articles": results, "total": len(results), "query": query}


async def main():
    """Main entry point for MCP server."""
    server = MockAgentReachServer()

    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

    writer = sys.stdout

    while True:
        line = await reader.readline()
        if not line:
            break

        line = line.decode().strip()
        if not line:
            continue

        try:
            request = json.loads(line)
            response = await server.handle_request(request)
            writer.write(json.dumps(response) + "\n")
            writer.flush()
        except json.JSONDecodeError:
            continue


if __name__ == "__main__":
    asyncio.run(main())