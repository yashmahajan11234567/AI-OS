#!/usr/bin/env python3
"""
Mock Claude-Mem MCP Server for AI-OS M8-T4 testing.

Provides a local mock Claude-Mem server that implements the MCP protocol
for testing the ClaudeMemAdapter without requiring an external service.
"""

import json
import sys
from datetime import datetime, timedelta
from typing import Any


class MockClaudeMemServer:
    """Mock Claude-Mem MCP server with memory operations."""

    def __init__(self):
        self._memories: list[dict[str, Any]] = []
        self._initialized = False

    def handle_request(self, request: dict[str, Any]) -> dict[str, Any] | None:
        """Handle incoming MCP request. Returns None for notifications (no response)."""
        method = request.get("method", "")
        request_id = request.get("id")

        # Notifications don't have an id and don't expect a response
        is_notification = request_id is None

        try:
            if method == "initialize":
                return self._handle_initialize(request)
            elif method == "tools/list":
                return self._handle_tools_list(request)
            elif method == "tools/call":
                return self._handle_tool_call(request)
            elif method == "notifications/initialized":
                self._initialized = True
                # Notifications don't get a response
                return None
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

    def _handle_initialize(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle initialize request."""
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                },
                "serverInfo": {
                    "name": "Mock Claude-Mem Server",
                    "version": "0.1.0",
                },
            },
        }

    def _handle_tools_list(self, request: dict[str, Any]) -> dict[str, Any]:
        """List available tools."""
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "tools": [
                    {
                        "name": "retrieve_context",
                        "description": "Retrieve contextual memories matching a query",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "limit": {"type": "integer", "default": 10},
                                "tags": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["query"],
                        },
                    },
                    {
                        "name": "retrieve_recent",
                        "description": "Retrieve recent memories within a time window",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "hours": {"type": "integer", "default": 24},
                                "limit": {"type": "integer", "default": 20},
                            },
                        },
                    },
                    {
                        "name": "retrieve_by_tag",
                        "description": "Retrieve memories by tag",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "tag": {"type": "string"},
                                "limit": {"type": "integer", "default": 10},
                            },
                            "required": ["tag"],
                        },
                    },
                ],
            },
        }

    def _handle_tool_call(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle tool call."""
        params = request.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        request_id = request.get("id")

        try:
            if tool_name == "retrieve_context":
                result = self._retrieve_context(arguments)
            elif tool_name == "retrieve_recent":
                result = self._retrieve_recent(arguments)
            elif tool_name == "retrieve_by_tag":
                result = self._retrieve_by_tag(arguments)
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

    def _retrieve_context(self, args: dict[str, Any]) -> dict[str, Any]:
        """Retrieve contextual memories matching a query."""
        query = args.get("query", "").lower()
        limit = args.get("limit", 10)
        tags = args.get("tags", [])

        results = []
        for memory in self._memories:
            # Filter by tags if specified
            if tags and not any(t in memory.get("tags", []) for t in tags):
                continue

            # Simple text search in content and metadata
            content = memory.get("content", "").lower()
            metadata_str = json.dumps(memory.get("metadata", {})).lower()

            if query in content or query in metadata_str:
                results.append(memory.copy())
                if len(results) >= limit:
                    break

        return {"memories": results}

    def _retrieve_recent(self, args: dict[str, Any]) -> dict[str, Any]:
        """Retrieve recent memories within a time window."""
        hours = args.get("hours", 24)
        limit = args.get("limit", 20)

        cutoff = datetime.utcnow() - timedelta(hours=hours)

        results = []
        for memory in self._memories:
            created_str = memory.get("created_at", "")
            try:
                created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                if created >= cutoff:
                    results.append(memory.copy())
                    if len(results) >= limit:
                        break
            except (ValueError, AttributeError):
                continue

        # Sort by most recent first
        results.sort(key=lambda m: m.get("created_at", ""), reverse=True)
        return {"memories": results}

    def _retrieve_by_tag(self, args: dict[str, Any]) -> dict[str, Any]:
        """Retrieve memories by tag."""
        tag = args.get("tag", "")
        limit = args.get("limit", 10)

        results = []
        for memory in self._memories:
            if tag in memory.get("tags", []):
                results.append(memory.copy())
                if len(results) >= limit:
                    break

        # Sort by most recent first
        results.sort(key=lambda m: m.get("created_at", ""), reverse=True)
        return {"memories": results}


def main():
    """Main entry point for MCP server - synchronous stdio loop."""
    server = MockClaudeMemServer()

    # Simple synchronous read/write loop - works on all platforms including Windows
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
            response = server.handle_request(request)
            # Notifications return None - don't send a response
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError:
            # Ignore invalid JSON lines
            continue
        except Exception as e:
            # Send error response for any other errors
            error_response = {
                "jsonrpc": "2.0",
                "id": request.get("id") if isinstance(request, dict) else None,
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
            }
            sys.stdout.write(json.dumps(error_response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()