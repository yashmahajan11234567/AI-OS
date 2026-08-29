#!/usr/bin/env python3
"""
Mock Hermes ACP Server for AI-OS M8-T1 testing.

Provides a minimal ACP-compliant stdio JSON-RPC server for testing
the ACP adapter without requiring hermes-agent installation.
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from typing import Any


class MockACPServer:
    """Mock ACP server implementing minimal ACP protocol over stdio."""

    def __init__(self):
        self._initialized = False
        self._sessions: dict[str, dict[str, Any]] = {}
        self._current_session: str | None = None

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any] | None:
        """Handle incoming ACP JSON-RPC request."""
        method = request.get("method", "")
        request_id = request.get("id")

        # Notifications don't have responses
        is_notification = "id" not in request

        try:
            if method == "initialize":
                return await self._handle_initialize(request)
            elif method == "session/new":
                return await self._handle_new_session(request)
            elif method == "session/prompt":
                return await self._handle_prompt(request)
            elif method == "session/cancel":
                return await self._handle_cancel(request)
            elif method == "session/close":
                return await self._handle_close_session(request)
            elif method == "notifications/initialized":
                self._initialized = True
                return None  # No response for notifications
            else:
                if not is_notification:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32601, "message": f"Method not found: {method}"},
                    }
        except Exception as e:
            if not is_notification:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
                }
        return None

    async def _handle_initialize(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle ACP initialize handshake."""
        request_id = request.get("id")
        self._initialized = True
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": 1,
                "capabilities": {
                    "session": {"new": True, "prompt": True, "cancel": True, "close": True}
                },
                "serverInfo": {
                    "name": "Mock Hermes ACP Server",
                    "version": "0.1.0",
                },
            },
        }

    async def _handle_new_session(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle session/new - create new ACP session."""
        request_id = request.get("id")
        params = request.get("params", {})
        cwd = params.get("cwd", "")

        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {
            "cwd": cwd,
            "created_at": datetime.utcnow().isoformat(),
            "history": [],
            "active": True,
        }
        self._current_session = session_id

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"sessionId": session_id},
        }

    async def _handle_prompt(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle session/prompt - execute a prompt in a session."""
        request_id = request.get("id")
        params = request.get("params", {})
        session_id = params.get("sessionId", self._current_session)
        prompt_text = params.get("prompt", "")
        timeout = params.get("timeout", 30000)  # timeout in ms

        if session_id not in self._sessions:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32000, "message": f"Session not found: {session_id}"},
            }

        session = self._sessions[session_id]
        if not session["active"]:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32000, "message": f"Session {session_id} is not active"},
            }

        # Simulate processing - deterministic response based on prompt
        session["history"].append(
            {
                "action": "prompt",
                "prompt": prompt_text[:200],
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Determine response based on prompt content (deterministic for testing)
        if "error" in prompt_text.lower():
            stop_reason = "error"
            text = "Error occurred during execution"
        elif "cancel" in prompt_text.lower():
            stop_reason = "cancelled"
            text = "Execution cancelled"
        elif "timeout" in prompt_text.lower():
            stop_reason = "timeout"
            text = "Execution timed out"
        else:
            stop_reason = "end_turn"
            text = f"Completed: {prompt_text[:100]}"

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "stopReason": stop_reason,
                "text": text,
                "sessionId": session_id,
            },
        }

    async def _handle_cancel(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle session/cancel - cancel in-flight prompt."""
        request_id = request.get("id")
        params = request.get("params", {})
        session_id = params.get("sessionId", self._current_session)

        if session_id not in self._sessions:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32000, "message": f"Session not found: {session_id}"},
            }

        session = self._sessions[session_id]
        session["history"].append(
            {"action": "cancel", "timestamp": datetime.utcnow().isoformat()}
        )

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"success": True, "sessionId": session_id},
        }

    async def _handle_close_session(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle session/close - close an ACP session."""
        request_id = request.get("id")
        params = request.get("params", {})
        session_id = params.get("sessionId", self._current_session)

        if session_id not in self._sessions:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32000, "message": f"Session not found: {session_id}"},
            }

        session = self._sessions[session_id]
        session["active"] = False
        session["history"].append(
            {"action": "close", "timestamp": datetime.utcnow().isoformat()}
        )

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"success": True, "sessionId": session_id},
        }


async def main():
    """Main entry point for ACP mock server."""
    # Check if ACP mock is enabled
    if not os.environ.get("HERMES_MOCK_ACP", "").lower() in ("1", "true", "yes"):
        print("HERMES_MOCK_ACP not set, exiting", file=sys.stderr)
        sys.exit(1)

    server = MockACPServer()

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
            if response is not None:
                writer.write(json.dumps(response) + "\n")
                writer.flush()
        except json.JSONDecodeError:
            continue


if __name__ == "__main__":
    asyncio.run(main())