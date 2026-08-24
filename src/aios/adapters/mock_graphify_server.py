#!/usr/bin/env python3
"""
Mock Graphify MCP Server for AI-OS M5-GATE-REALIZE testing.

Provides a local mock Graphify server that implements the MCP protocol
for testing the GraphifyBackend without requiring an external service.
"""

import json
import sys
from datetime import datetime
from typing import Any


class MockGraphifyServer:
    """Mock Graphify MCP server with basic graph operations."""

    def __init__(self):
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: list[dict[str, Any]] = []
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
                    "name": "Mock Graphify Server",
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
                        "name": "add_node",
                        "description": "Add a node to the knowledge graph",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "node_id": {"type": "string"},
                                "label": {"type": "string"},
                                "properties": {"type": "object"},
                            },
                            "required": ["node_id", "label"],
                        },
                    },
                    {
                        "name": "get_node",
                        "description": "Get a node from the knowledge graph",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "node_id": {"type": "string"},
                            },
                            "required": ["node_id"],
                        },
                    },
                    {
                        "name": "update_node",
                        "description": "Update a node in the knowledge graph",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "node_id": {"type": "string"},
                                "properties": {"type": "object"},
                            },
                            "required": ["node_id"],
                        },
                    },
                    {
                        "name": "delete_node",
                        "description": "Delete a node from the knowledge graph",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "node_id": {"type": "string"},
                            },
                            "required": ["node_id"],
                        },
                    },
                    {
                        "name": "query_graph",
                        "description": "Query the knowledge graph",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                            },
                            "required": ["query"],
                        },
                    },
                    {
                        "name": "shortest_path",
                        "description": "Find shortest path between nodes",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "from_node": {"type": "string"},
                                "to_node": {"type": "string"},
                                "max_depth": {"type": "integer", "default": 10},
                            },
                            "required": ["from_node", "to_node"],
                        },
                    },
                    {
                        "name": "add_edge",
                        "description": "Add an edge between nodes",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "from_node": {"type": "string"},
                                "to_node": {"type": "string"},
                                "relationship": {"type": "string"},
                                "properties": {"type": "object"},
                            },
                            "required": ["from_node", "to_node", "relationship"],
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
            if tool_name == "add_node":
                result = self._add_node(arguments)
            elif tool_name == "get_node":
                result = self._get_node(arguments)
            elif tool_name == "update_node":
                result = self._update_node(arguments)
            elif tool_name == "delete_node":
                result = self._delete_node(arguments)
            elif tool_name == "query_graph":
                result = self._query_graph(arguments)
            elif tool_name == "shortest_path":
                result = self._shortest_path(arguments)
            elif tool_name == "add_edge":
                result = self._add_edge(arguments)
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

    def _add_node(self, args: dict[str, Any]) -> dict[str, Any]:
        """Add a node."""
        node_id = args["node_id"]
        self._nodes[node_id] = {
            "id": node_id,
            "label": args.get("label", node_id),
            "properties": args.get("properties", {}),
        }
        return {"node_id": node_id, "created": True}

    def _get_node(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get a node."""
        node_id = args["node_id"]
        node = self._nodes.get(node_id)
        if not node:
            raise ValueError(f"Node not found: {node_id}")
        return node

    def _update_node(self, args: dict[str, Any]) -> dict[str, Any]:
        """Update a node."""
        node_id = args["node_id"]
        if node_id not in self._nodes:
            raise ValueError(f"Node not found: {node_id}")
        self._nodes[node_id]["properties"].update(args.get("properties", {}))
        return {"node_id": node_id, "updated": True}

    def _delete_node(self, args: dict[str, Any]) -> dict[str, Any]:
        """Delete a node."""
        node_id = args["node_id"]
        if node_id in self._nodes:
            del self._nodes[node_id]
            # Also remove connected edges
            self._edges = [e for e in self._edges if e["from_node"] != node_id and e["to_node"] != node_id]
        return {"node_id": node_id, "deleted": True}

    def _query_graph(self, args: dict[str, Any]) -> dict[str, Any]:
        """Query the graph (simplified)."""
        # Simple implementation - return all nodes for now
        return {
            "nodes": list(self._nodes.values()),
            "edges": self._edges,
        }

    def _shortest_path(self, args: dict[str, Any]) -> dict[str, Any]:
        """Find shortest path (simplified BFS)."""
        from_node = args["from_node"]
        to_node = args["to_node"]
        max_depth = args.get("max_depth", 10)

        # Simple BFS
        if from_node not in self._nodes or to_node not in self._nodes:
            return {"path": [], "found": False}

        visited = {from_node}
        queue = [(from_node, [from_node])]
        depth = 0

        while queue and depth < max_depth:
            current, path = queue.pop(0)
            if current == to_node:
                return {"path": path, "found": True}

            # Find neighbors
            for edge in self._edges:
                if edge["from_node"] == current and edge["to_node"] not in visited:
                    visited.add(edge["to_node"])
                    queue.append((edge["to_node"], path + [edge["to_node"]]))
                elif edge["to_node"] == current and edge["from_node"] not in visited:
                    visited.add(edge["from_node"])
                    queue.append((edge["from_node"], path + [edge["from_node"]]))

            depth += 1

        return {"path": [], "found": False}

    def _add_edge(self, args: dict[str, Any]) -> dict[str, Any]:
        """Add an edge."""
        edge = {
            "from_node": args["from_node"],
            "to_node": args["to_node"],
            "relationship": args["relationship"],
            "properties": args.get("properties", {}),
        }
        self._edges.append(edge)
        return {"edge": edge, "created": True}


def main():
    """Main entry point for MCP server - synchronous stdio loop."""
    server = MockGraphifyServer()

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