#!/usr/bin/env python3
"""
Mock Playwright MCP Server for AI-OS M8-T2 testing.

Provides a local mock Playwright MCP server that simulates browser tools
for testing the PlaywrightMCPAdapter without requiring a real browser.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
import uuid
from datetime import datetime
from typing import Any


class MockPlaywrightMCPServer:
    """Mock Playwright MCP server with deterministic browser tool responses."""

    def __init__(self):
        self._initialized = False
        self._sessions: dict[str, dict[str, Any]] = {}
        self._contexts: dict[str, dict[str, Any]] = {}
        self._pages: dict[str, dict[str, Any]] = {}
        self._request_counter = 0

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle incoming JSON-RPC request."""
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
                return self._error_response(request_id, -32601, f"Method not found: {method}")
        except Exception as e:
            return self._error_response(request_id, -32603, f"Internal error: {str(e)}")

    # ------------------------------------------------------------------
    # Initialize
    # ------------------------------------------------------------------

    async def _handle_initialize(self, request: dict[str, Any]) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "Mock Playwright MCP Server",
                    "version": "0.1.0",
                },
            },
        }

    # ------------------------------------------------------------------
    # Tool Discovery
    # ------------------------------------------------------------------

    async def _handle_tools_list(self, request: dict[str, Any]) -> dict[str, Any]:
        tools = [
            {
                "name": "browser_navigate",
                "description": "Navigate to a URL in the browser",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "headless": {"type": "boolean", "default": True},
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
                "name": "browser_type_text",
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
                "name": "browser_press_key",
                "description": "Press a keyboard key",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string"},
                        "session_id": {"type": "string"},
                    },
                    "required": ["key", "session_id"],
                },
            },
            {
                "name": "browser_snapshot",
                "description": "Get accessibility snapshot of the page",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "selector": {"type": "string"},
                    },
                    "required": ["session_id"],
                },
            },
            {
                "name": "browser_take_screenshot",
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
                "name": "browser_new_context",
                "description": "Create a new isolated browser context",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "headless": {"type": "boolean", "default": True},
                    },
                    "required": [],
                },
            },
            {
                "name": "browser_close_context",
                "description": "Close a browser context and all its pages",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "context_id": {"type": "string"},
                    },
                    "required": ["context_id"],
                },
            },
            {
                "name": "browser_close",
                "description": "Close the browser",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "get_playwright_version",
                "description": "Get Playwright version",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {"tools": tools},
        }

    # ------------------------------------------------------------------
    # Tool Dispatch
    # ------------------------------------------------------------------

    async def _handle_tool_call(self, request: dict[str, Any]) -> dict[str, Any]:
        params = request.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        request_id = request.get("id")

        try:
            handler = getattr(self, f"_tool_{tool_name}", None)
            if handler is None:
                return self._error_response(request_id, -32601, f"Unknown tool: {tool_name}")
            result = await handler(arguments)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result,
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"success": False, "error": str(e)},
            }

    # ------------------------------------------------------------------
    # Tool Implementations
    # ------------------------------------------------------------------

    async def _tool_browser_navigate(self, args: dict[str, Any]) -> dict[str, Any]:
        url = args.get("url", "")
        headless = args.get("headless", True)

        # Generate deterministic session ID if not provided
        if "session_id" not in args:
            args["session_id"] = str(uuid.uuid4())

        session_id = args["session_id"]
        if session_id not in self._sessions:
            self._sessions[session_id] = {"url": "", "title": "", "history": []}

        self._sessions[session_id]["url"] = url
        self._sessions[session_id]["title"] = f"Page: {url}"
        self._sessions[session_id]["history"].append({
            "action": "navigate",
            "url": url,
            "timestamp": datetime.utcnow().isoformat(),
        })

        return {
            "success": True,
            "session_id": session_id,
            "url": url,
            "title": f"Page: {url}",
            "status": "loaded",
            "load_state": "networkidle",
        }

    async def _tool_browser_click(self, args: dict[str, Any]) -> dict[str, Any]:
        selector = args.get("selector", "")
        session_id = args.get("session_id", "")

        if session_id not in self._sessions:
            self._sessions[session_id] = {"url": "", "title": "", "history": []}

        self._sessions[session_id]["history"].append({
            "action": "click",
            "selector": selector,
            "timestamp": datetime.utcnow().isoformat(),
        })

        return {
            "success": True,
            "session_id": session_id,
            "selector": selector,
            "clicked": True,
        }

    async def _tool_browser_type_text(self, args: dict[str, Any]) -> dict[str, Any]:
        selector = args.get("selector", "")
        text = args.get("text", "")
        session_id = args.get("session_id", "")

        if session_id not in self._sessions:
            self._sessions[session_id] = {"url": "", "title": "", "history": []}

        self._sessions[session_id]["history"].append({
            "action": "type",
            "selector": selector,
            "text": text,
            "timestamp": datetime.utcnow().isoformat(),
        })

        return {
            "success": True,
            "session_id": session_id,
            "selector": selector,
            "typed": True,
            "text": text,
        }

    async def _tool_browser_press_key(self, args: dict[str, Any]) -> dict[str, Any]:
        key = args.get("key", "")
        session_id = args.get("session_id", "")

        if session_id not in self._sessions:
            self._sessions[session_id] = {"url": "", "title": "", "history": []}

        self._sessions[session_id]["history"].append({
            "action": "press_key",
            "key": key,
            "timestamp": datetime.utcnow().isoformat(),
        })

        return {"success": True, "key": key}

    async def _tool_browser_snapshot(self, args: dict[str, Any]) -> dict[str, Any]:
        session_id = args.get("session_id", "")
        selector = args.get("selector")

        if session_id not in self._sessions:
            self._sessions[session_id] = {"url": "", "title": "", "history": []}

        snapshot = {
            "role": "document",
            "name": "",
            "children": [
                {"role": "heading", "name": "Mock Page Title", "level": 1},
                {"role": "link", "name": "Example Link", "url": "https://example.com/link"},
            ],
        }

        return {"success": True, "snapshot": snapshot}

    async def _tool_browser_take_screenshot(self, args: dict[str, Any]) -> dict[str, Any]:
        session_id = args.get("session_id", "")
        full_page = args.get("full_page", False)

        if session_id not in self._sessions:
            self._sessions[session_id] = {"url": "", "title": "", "history": []}

        return {
            "success": True,
            "screenshot": "iVBORw0KGgoAAAANSUhEUg==",  # Minimal valid PNG base64
            "format": "png",
            "full_page": full_page,
            "width": 1280,
            "height": 720,
        }

    async def _tool_browser_new_context(self, args: dict[str, Any]) -> dict[str, Any]:
        context_id = str(uuid.uuid4())
        self._contexts[context_id] = {
            "id": context_id,
            "created_at": datetime.utcnow().isoformat(),
            "pages": [],
            "cookies": [],
            "storage": {},
        }
        return {
            "success": True,
            "context_id": context_id,
            "created": True,
        }

    async def _tool_browser_close_context(self, args: dict[str, Any]) -> dict[str, Any]:
        context_id = args.get("context_id", "")
        if context_id in self._contexts:
            del self._contexts[context_id]
            return {"success": True, "context_id": context_id, "closed": True}
        return {"success": False, "error": f"Context {context_id} not found"}

    async def _tool_browser_close(self, args: dict[str, Any]) -> dict[str, Any]:
        self._sessions.clear()
        self._contexts.clear()
        self._pages.clear()
        return {"success": True, "closed": True}

    async def _tool_get_playwright_version(self, args: dict[str, Any]) -> dict[str, Any]:
        return {"success": True, "version": "1.40.0", "browser": "chromium"}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _error_response(self, request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }


async def main():
    """Main entry point for MCP server."""
    server = MockPlaywrightMCPServer()

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
