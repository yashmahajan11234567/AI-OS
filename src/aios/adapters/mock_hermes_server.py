#!/usr/bin/env python3
"""
Mock Hermes Agent External MCP Server for AI-OS M5-GATE-REALIZE testing.

Provides a local mock Hermes server that implements the MCP protocol
for testing the HermesBridge without requiring an external service.
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Any


class MockHermesServer:
    """Mock Hermes Agent External MCP server with browser/worker capabilities."""

    def __init__(self):
        self._initialized = False
        self._sessions: dict[str, dict[str, Any]] = {}

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
                    "name": "Mock Hermes Agent External Server",
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
                        "name": "browser_navigate",
                        "description": "Navigate to a URL in the browser",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "url": {"type": "string"},
                                "session_id": {"type": "string"},
                            },
                            "required": ["url"],
                        },
                    },
                    {
                        "name": "browser_click",
                        "description": "Click an element on the page",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "selector": {"type": "string"},
                                "session_id": {"type": "string"},
                            },
                            "required": ["selector", "session_id"],
                        },
                    },
                    {
                        "name": "browser_type",
                        "description": "Type text into an element",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "selector": {"type": "string"},
                                "text": {"type": "string"},
                                "session_id": {"type": "string"},
                            },
                            "required": ["selector", "text", "session_id"],
                        },
                    },
                    {
                        "name": "browser_extract",
                        "description": "Extract content from the page",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "selector": {"type": "string"},
                                "attribute": {"type": "string", "default": "textContent"},
                                "session_id": {"type": "string"},
                            },
                            "required": ["session_id"],
                        },
                    },
                    {
                        "name": "browser_screenshot",
                        "description": "Take a screenshot of the page",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "session_id": {"type": "string"},
                                "full_page": {"type": "boolean", "default": False},
                            },
                            "required": ["session_id"],
                        },
                    },
                    {
                        "name": "worker_execute",
                        "description": "Execute a task on the worker",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "task": {"type": "string"},
                                "context": {"type": "object"},
                            },
                            "required": ["task"],
                        },
                    },
                    {
                        "name": "create_session",
                        "description": "Create a new isolated worker session",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "session_id": {"type": "string"},
                                "environment": {"type": "object", "default": {}},
                            },
                            "required": ["session_id"],
                        },
                    },
                    {
                        "name": "close_session",
                        "description": "Close an existing worker session",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "session_id": {"type": "string"},
                            },
                            "required": ["session_id"],
                        },
                    },
                    {
                        "name": "execute_task",
                        "description": "Execute a structured task on a worker session",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "session_id": {"type": "string"},
                                "task_type": {"type": "string"},
                                "description": {"type": "string"},
                                "parameters": {"type": "object"},
                            },
                            "required": ["session_id", "task_type", "description", "parameters"],
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
            if tool_name == "browser_navigate":
                result = await self._browser_navigate(arguments)
            elif tool_name == "browser_click":
                result = await self._browser_click(arguments)
            elif tool_name == "browser_type":
                result = await self._browser_type(arguments)
            elif tool_name == "browser_extract":
                result = await self._browser_extract(arguments)
            elif tool_name == "browser_screenshot":
                result = await self._browser_screenshot(arguments)
            elif tool_name == "worker_execute":
                result = await self._worker_execute(arguments)
            elif tool_name == "create_session":
                result = await self._create_session(arguments)
            elif tool_name == "close_session":
                result = await self._close_session(arguments)
            elif tool_name == "execute_task":
                result = await self._execute_task(arguments)
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

    async def _browser_navigate(self, args: dict[str, Any]) -> dict[str, Any]:
        """Mock browser navigate."""
        url = args.get("url", "")
        session_id = args.get("session_id", "default")

        if session_id not in self._sessions:
            self._sessions[session_id] = {"url": "", "history": []}

        self._sessions[session_id]["url"] = url
        self._sessions[session_id]["history"].append(
            {"action": "navigate", "url": url, "timestamp": datetime.utcnow().isoformat()}
        )

        return {
            "session_id": session_id,
            "url": url,
            "title": f"Mock Page: {url}",
            "status": "loaded",
        }

    async def _browser_click(self, args: dict[str, Any]) -> dict[str, Any]:
        """Mock browser click."""
        selector = args.get("selector", "")
        session_id = args.get("session_id", "default")

        if session_id not in self._sessions:
            self._sessions[session_id] = {"url": "", "history": []}

        self._sessions[session_id]["history"].append(
            {"action": "click", "selector": selector, "timestamp": datetime.utcnow().isoformat()}
        )

        return {
            "session_id": session_id,
            "selector": selector,
            "clicked": True,
        }

    async def _browser_type(self, args: dict[str, Any]) -> dict[str, Any]:
        """Mock browser type."""
        selector = args.get("selector", "")
        text = args.get("text", "")
        session_id = args.get("session_id", "default")

        if session_id not in self._sessions:
            self._sessions[session_id] = {"url": "", "history": []}

        self._sessions[session_id]["history"].append(
            {"action": "type", "selector": selector, "text": text, "timestamp": datetime.utcnow().isoformat()}
        )

        return {
            "session_id": session_id,
            "selector": selector,
            "typed": True,
            "text": text,
        }

    async def _browser_extract(self, args: dict[str, Any]) -> dict[str, Any]:
        """Mock browser extract."""
        selector = args.get("selector", "body")
        attribute = args.get("attribute", "textContent")
        session_id = args.get("session_id", "default")

        if session_id not in self._sessions:
            self._sessions[session_id] = {"url": "", "history": []}

        content_map = {
            "textContent": f"Mock page content extracted from {selector}",
            "innerHTML": f"<div class='{selector}'>Mock HTML content</div>",
            "href": "https://example.com/link",
        }

        self._sessions[session_id]["history"].append(
            {"action": "extract", "selector": selector, "timestamp": datetime.utcnow().isoformat()}
        )

        return {
            "session_id": session_id,
            "selector": selector,
            "attribute": attribute,
            "value": content_map.get(attribute, f"Mock {attribute} value"),
        }

    async def _browser_screenshot(self, args: dict[str, Any]) -> dict[str, Any]:
        """Mock browser screenshot."""
        session_id = args.get("session_id", "default")
        full_page = args.get("full_page", False)

        if session_id not in self._sessions:
            self._sessions[session_id] = {"url": "", "history": []}

        return {
            "session_id": session_id,
            "screenshot": "base64_mock_screenshot_data",
            "full_page": full_page,
            "format": "png",
        }

    async def _worker_execute(self, args: dict[str, Any]) -> dict[str, Any]:
        """Mock worker execute."""
        task = args.get("task", "")
        context = args.get("context", {})

        return {
            "task": task,
            "result": f"Worker completed task: {task}",
            "status": "completed",
            "output": {"summary": f"Mock worker output for: {task}"},
        }

    async def _create_session(self, args: dict[str, Any]) -> dict[str, Any]:
        """Mock create session."""
        session_id = args.get("session_id", "")
        environment = args.get("environment", {})

        if session_id not in self._sessions:
            self._sessions[session_id] = {"url": "", "history": [], "environment": environment}

        self._sessions[session_id]["history"].append(
            {"action": "create_session", "environment": environment, "timestamp": datetime.utcnow().isoformat()}
        )

        return {
            "success": True,
            "session_id": session_id,
            "environment": environment,
        }

    async def _close_session(self, args: dict[str, Any]) -> dict[str, Any]:
        """Mock close session."""
        session_id = args.get("session_id", "")

        if session_id in self._sessions:
            self._sessions[session_id]["history"].append(
                {"action": "close_session", "timestamp": datetime.utcnow().isoformat()}
            )
            return {"success": True, "session_id": session_id}
        else:
            return {"success": False, "error": f"Session {session_id} not found"}

    async def _execute_task(self, args: dict[str, Any]) -> dict[str, Any]:
        """Mock execute structured task."""
        session_id = args.get("session_id", "")
        task_type = args.get("task_type", "")
        description = args.get("description", "")
        parameters = args.get("parameters", {})

        if session_id not in self._sessions:
            self._sessions[session_id] = {"url": "", "history": []}

        self._sessions[session_id]["history"].append(
            {"action": "execute_task", "task_type": task_type, "description": description,
             "parameters": parameters, "timestamp": datetime.utcnow().isoformat()}
        )

        return {
            "success": True,
            "session_id": session_id,
            "task_type": task_type,
            "description": description,
            "result": f"Executed {task_type}: {description}",
            "output": {"summary": f"Mock execution result for {task_type}"},
        }


async def main():
    """Main entry point for MCP server."""
    server = MockHermesServer()

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