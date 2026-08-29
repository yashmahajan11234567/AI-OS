#!/usr/bin/env python3
"""
Mock Obsidian MCP Server for AI-OS M8-T4 testing.

Provides a local mock Obsidian server that implements the MCP protocol
for testing the ObsidianAdapter without requiring an external service.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class MockObsidianServer:
    """Mock Obsidian MCP server with vault operations."""

    def __init__(self):
        self._notes: dict[str, dict[str, Any]] = {}
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
                    "name": "Mock Obsidian Server",
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
                        "name": "search_notes",
                        "description": "Search Obsidian notes by query",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "directory": {"type": "string", "description": "Optional directory to search in"},
                                "limit": {"type": "integer", "default": 50},
                            },
                            "required": ["query"],
                        },
                    },
                    {
                        "name": "get_note",
                        "description": "Get an Obsidian note by path",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                            },
                            "required": ["path"],
                        },
                    },
                    {
                        "name": "list_notes",
                        "description": "List notes in a directory",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "directory": {"type": "string", "default": "."},
                                "limit": {"type": "integer", "default": 100},
                            },
                        },
                    },
                    {
                        "name": "read_note",
                        "description": "Read an Obsidian note content with frontmatter",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                            },
                            "required": ["path"],
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
            if tool_name == "search_notes":
                result = self._search_notes(arguments)
            elif tool_name == "get_note":
                result = self._get_note(arguments)
            elif tool_name == "list_notes":
                result = self._list_notes(arguments)
            elif tool_name == "read_note":
                result = self._read_note(arguments)
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

    def _search_notes(self, args: dict[str, Any]) -> dict[str, Any]:
        """Search Obsidian notes by query."""
        query = args.get("query", "").lower()
        directory = args.get("directory", ".")
        limit = args.get("limit", 50)

        results = []
        for path, note in self._notes.items():
            # Check if note is in the specified directory
            note_dir = str(Path(path).parent)
            if directory != "." and not path.startswith(directory):
                continue

            # Simple text search in title, content, and tags
            title = note.get("title", "").lower()
            content = note.get("content", "").lower()
            tags = " ".join(note.get("tags", [])).lower()

            if query in title or query in content or query in tags:
                results.append({
                    "path": path,
                    "title": note.get("title", ""),
                    "tags": note.get("tags", []),
                    "created_at": note.get("created_at"),
                    "updated_at": note.get("updated_at"),
                })
                if len(results) >= limit:
                    break

        return {"notes": results}

    def _get_note(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get an Obsidian note by path."""
        path = args["path"]
        note = self._notes.get(path)
        if not note:
            raise ValueError(f"Note not found: {path}")
        return note

    def _list_notes(self, args: dict[str, Any]) -> dict[str, Any]:
        """List notes in a directory."""
        directory = args.get("directory", ".")
        limit = args.get("limit", 100)

        results = []
        for path, note in self._notes.items():
            note_dir = str(Path(path).parent)
            if directory == "." or path.startswith(directory):
                results.append({
                    "path": path,
                    "title": note.get("title", ""),
                    "tags": note.get("tags", []),
                    "created_at": note.get("created_at"),
                    "updated_at": note.get("updated_at"),
                })
                if len(results) >= limit:
                    break

        return {"notes": results}

    def _read_note(self, args: dict[str, Any]) -> dict[str, Any]:
        """Read an Obsidian note content with frontmatter."""
        path = args["path"]
        note = self._notes.get(path)
        if not note:
            raise ValueError(f"Note not found: {path}")
        return note


def main():
    """Main entry point for MCP server - synchronous stdio loop."""
    server = MockObsidianServer()

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