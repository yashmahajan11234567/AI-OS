#!/usr/bin/env python3
"""
Mock Notion MCP Server for AI-OS M8-T4 testing.

Provides a local mock Notion server that implements the MCP protocol
for testing the NotionAdapter without requiring an external service.
"""

import json
import sys
from datetime import datetime
from typing import Any


class MockNotionServer:
    """Mock Notion MCP server with basic planning operations."""

    def __init__(self):
        self._pages: dict[str, dict[str, Any]] = {}
        self._databases: dict[str, dict[str, Any]] = {}
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
                    "name": "Mock Notion Server",
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
                        "name": "search_pages",
                        "description": "Search Notion pages by query",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "parent": {"type": "string", "description": "Optional parent page/database ID"},
                                "limit": {"type": "integer", "default": 50},
                            },
                            "required": ["query"],
                        },
                    },
                    {
                        "name": "get_page",
                        "description": "Get a Notion page by ID",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "page_id": {"type": "string"},
                            },
                            "required": ["page_id"],
                        },
                    },
                    {
                        "name": "create_page",
                        "description": "Create a new Notion page",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "parent_id": {"type": "string", "description": "Parent page or database ID"},
                                "content": {"type": "object", "description": "Page content blocks"},
                                "properties": {"type": "object", "description": "Database properties if parent is a database"},
                            },
                            "required": ["title", "parent_id"],
                        },
                    },
                    {
                        "name": "update_page",
                        "description": "Update an existing Notion page",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "page_id": {"type": "string"},
                                "content": {"type": "object"},
                                "properties": {"type": "object"},
                            },
                            "required": ["page_id"],
                        },
                    },
                    {
                        "name": "query_database",
                        "description": "Query a Notion database",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "database_id": {"type": "string"},
                                "filter": {"type": "object", "description": "Notion filter object"},
                                "sorts": {"type": "array", "items": {"type": "object"}},
                                "limit": {"type": "integer", "default": 50},
                            },
                            "required": ["database_id"],
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
            if tool_name == "search_pages":
                result = self._search_pages(arguments)
            elif tool_name == "get_page":
                result = self._get_page(arguments)
            elif tool_name == "create_page":
                result = self._create_page(arguments)
            elif tool_name == "update_page":
                result = self._update_page(arguments)
            elif tool_name == "query_database":
                result = self._query_database(arguments)
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

    def _search_pages(self, args: dict[str, Any]) -> dict[str, Any]:
        """Search Notion pages by query."""
        query = args.get("query", "").lower()
        limit = args.get("limit", 50)
        parent = args.get("parent")

        results = []
        for page_id, page in self._pages.items():
            if parent and page.get("parent_id") != parent:
                continue
            # Simple text search in title and content
            title = page.get("title", "").lower()
            content_str = json.dumps(page.get("content", {})).lower()
            if query in title or query in content_str:
                results.append({
                    "id": page_id,
                    "title": page.get("title", ""),
                    "parent_id": page.get("parent_id"),
                    "created_time": page.get("created_time"),
                    "last_edited_time": page.get("last_edited_time"),
                })
                if len(results) >= limit:
                    break

        return {"pages": results}

    def _get_page(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get a Notion page by ID."""
        page_id = args["page_id"]
        page = self._pages.get(page_id)
        if not page:
            raise ValueError(f"Page not found: {page_id}")
        return page

    def _create_page(self, args: dict[str, Any]) -> dict[str, Any]:
        """Create a new Notion page."""
        title = args["title"]
        parent_id = args["parent_id"]
        content = args.get("content", {})
        properties = args.get("properties", {})

        page_id = f"page_{len(self._pages) + 1}"
        now = datetime.utcnow().isoformat()

        page = {
            "id": page_id,
            "title": title,
            "parent_id": parent_id,
            "content": content,
            "properties": properties,
            "created_time": now,
            "last_edited_time": now,
        }

        self._pages[page_id] = page
        return {"page_id": page_id, "created": True}

    def _update_page(self, args: dict[str, Any]) -> dict[str, Any]:
        """Update an existing Notion page."""
        page_id = args["page_id"]
        if page_id not in self._pages:
            raise ValueError(f"Page not found: {page_id}")

        page = self._pages[page_id]
        if "content" in args:
            page["content"].update(args["content"])
        if "properties" in args:
            page["properties"].update(args["properties"])
        page["last_edited_time"] = datetime.utcnow().isoformat()

        return {"page_id": page_id, "updated": True}

    def _query_database(self, args: dict[str, Any]) -> dict[str, Any]:
        """Query a Notion database."""
        database_id = args["database_id"]
        filter_obj = args.get("filter")
        sorts = args.get("sorts", [])
        limit = args.get("limit", 50)

        # For mock, we treat the database as a parent of pages
        results = []
        for page_id, page in self._pages.items():
            if page.get("parent_id") == database_id:
                # Simple filter matching (mock implementation)
                match = True
                if filter_obj:
                    # Very simplified filter - just check property exists
                    for key in filter_obj.get("property", ""):
                        if key not in page.get("properties", {}):
                            match = False
                            break
                if match:
                    results.append({
                        "id": page_id,
                        "properties": page.get("properties", {}),
                    })
                    if len(results) >= limit:
                        break

        return {"results": results, "has_more": False}


def main():
    """Main entry point for MCP server - synchronous stdio loop."""
    server = MockNotionServer()

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