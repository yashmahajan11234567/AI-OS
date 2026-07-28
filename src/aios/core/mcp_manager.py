"""
MCP Manager for AI-OS Hermes Kernel.

Manages Model Context Protocol (MCP) server connections and tool orchestration.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from aios.events.bus import get_event_bus
from aios.events.types import (
    MCPServerConnected,
    MCPServerDisconnected,
    MCPToolCalled,
    MCPToolResult,
)

logger = logging.getLogger(__name__)


class MCPTransport(str, Enum):
    """MCP transport types."""

    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"
    WEBSOCKET = "websocket"


@dataclass
class MCPServerConfig:
    """MCP server configuration."""

    server_id: str
    name: str
    transport: MCPTransport = MCPTransport.STDIO
    command: list[str] | None = None  # For stdio
    url: str | None = None  # For HTTP/SSE/WebSocket
    env: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 30
    auto_reconnect: bool = True
    max_retries: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPTool:
    """MCP tool definition."""

    name: str
    description: str
    input_schema: dict[str, Any]
    server_id: str


@dataclass
class MCPServerStatus:
    """MCP server connection status."""

    server_id: str
    connected: bool = False
    transport: MCPTransport = MCPTransport.STDIO
    tools: list[MCPTool] = field(default_factory=list)
    last_connected: datetime | None = None
    last_error: str | None = None
    retry_count: int = 0


class MCPManager:
    """
    Manages MCP server connections and tool orchestration.

    Features:
    - Multiple transport support (stdio, HTTP, SSE, WebSocket)
    - Automatic connection management
    - Tool discovery and caching
    - Tool execution with retries
    - Health monitoring
    """

    def __init__(
        self,
        config_dir: Path | None = None,
    ):
        """
        Initialize the MCP Manager.

        Args:
            config_dir: Directory containing MCP server configs
        """
        self._config_dir = config_dir or Path("./config/mcp")
        self._config_dir.mkdir(parents=True, exist_ok=True)

        self._servers: dict[str, MCPServerConfig] = {}
        self._status: dict[str, MCPServerStatus] = {}
        self._processes: dict[str, asyncio.subprocess.Process] = {}
        self._tools_cache: dict[str, list[MCPTool]] = {}
        self._event_bus = get_event_bus()

        # Load configs
        self._load_configs()

    def _load_configs(self) -> None:
        """Load MCP server configurations."""
        for config_file in self._config_dir.glob("*.json"):
            try:
                data = json.loads(config_file.read_text())
                config = MCPServerConfig(**data)
                self._servers[config.server_id] = config
                self._status[config.server_id] = MCPServerStatus(
                    server_id=config.server_id,
                    transport=config.transport,
                )
                logger.info(f"Loaded MCP server config: {config.server_id}")
            except Exception as e:
                logger.warning(f"Failed to load MCP config {config_file}: {e}")

    def add_server(self, config: MCPServerConfig) -> None:
        """Add an MCP server configuration."""
        self._servers[config.server_id] = config
        self._status[config.server_id] = MCPServerStatus(
            server_id=config.server_id,
            transport=config.transport,
        )
        self._save_config(config)

    def remove_server(self, server_id: str) -> bool:
        """Remove an MCP server configuration."""
        if server_id in self._servers:
            # Disconnect if connected
            if self._status[server_id].connected:
                asyncio.create_task(self.disconnect(server_id))

            del self._servers[server_id]
            del self._status[server_id]
            self._tools_cache.pop(server_id, None)

            # Delete config file
            config_file = self._config_dir / f"{server_id}.json"
            if config_file.exists():
                config_file.unlink()

            return True
        return False

    def _save_config(self, config: MCPServerConfig) -> None:
        """Save server config to file."""
        config_file = self._config_dir / f"{config.server_id}.json"
        data = {
            "server_id": config.server_id,
            "name": config.name,
            "transport": config.transport.value,
            "command": config.command,
            "url": config.url,
            "env": config.env,
            "headers": config.headers,
            "timeout_seconds": config.timeout_seconds,
            "auto_reconnect": config.auto_reconnect,
            "max_retries": config.max_retries,
            "metadata": config.metadata,
        }
        config_file.write_text(json.dumps(data, indent=2))

    async def connect(self, server_id: str) -> bool:
        """
        Connect to an MCP server.

        Args:
            server_id: Server identifier

        Returns:
            True if connected successfully
        """
        config = self._servers.get(server_id)
        if not config:
            logger.error(f"Server {server_id} not configured")
            return False

        status = self._status[server_id]
        if status.connected:
            logger.info(f"Server {server_id} already connected")
            return True

        try:
            if config.transport == MCPTransport.STDIO:
                await self._connect_stdio(config, status)
            elif config.transport == MCPTransport.HTTP:
                await self._connect_http(config, status)
            elif config.transport == MCPTransport.SSE:
                await self._connect_sse(config, status)
            elif config.transport == MCPTransport.WEBSOCKET:
                await self._connect_websocket(config, status)

            # Discover tools
            tools = await self._discover_tools(server_id)
            status.tools = tools
            self._tools_cache[server_id] = tools

            status.connected = True
            status.last_connected = datetime.utcnow()
            status.last_error = None
            status.retry_count = 0

            self._event_bus.publish(
                MCPServerConnected(
                    source_service="mcp_manager",
                    correlation_id=server_id,
                    payload={
                        "server_id": server_id,
                        "name": config.name,
                        "transport": config.transport.value,
                        "tools": [t.name for t in tools],
                    },
                )
            )

            logger.info(f"Connected to MCP server: {server_id}")
            return True

        except Exception as e:
            status.last_error = str(e)
            status.retry_count += 1
            logger.error(f"Failed to connect to {server_id}: {e}")
            return False

    async def _connect_stdio(
        self, config: MCPServerConfig, status: MCPServerStatus
    ) -> None:
        """Connect via stdio transport."""
        if not config.command:
            raise ValueError("STDIO transport requires command")

        process = await asyncio.create_subprocess_exec(
            *config.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=config.env,
        )
        self._processes[config.server_id] = process

    async def _connect_http(
        self, config: MCPServerConfig, status: MCPServerStatus
    ) -> None:
        """Connect via HTTP transport."""
        import aiohttp

        if not config.url:
            raise ValueError("HTTP transport requires URL")

        session = aiohttp.ClientSession(
            headers=config.headers,
            timeout=aiohttp.ClientTimeout(total=config.timeout_seconds),
        )
        self._processes[config.server_id] = session

    async def _connect_sse(
        self, config: MCPServerConfig, status: MCPServerStatus
    ) -> None:
        """Connect via SSE transport."""
        # Similar to HTTP but with SSE client
        await self._connect_http(config, status)

    async def _connect_websocket(
        self, config: MCPServerConfig, status: MCPServerStatus
    ) -> None:
        """Connect via WebSocket transport."""
        import websockets

        if not config.url:
            raise ValueError("WebSocket transport requires URL")

        websocket = await websockets.connect(
            config.url, extra_headers=config.headers
        )
        self._processes[config.server_id] = websocket

    async def disconnect(self, server_id: str) -> bool:
        """
        Disconnect from an MCP server.

        Args:
            server_id: Server identifier

        Returns:
            True if disconnected
        """
        if server_id not in self._servers:
            return False

        process = self._processes.pop(server_id, None)
        if process:
            try:
                if hasattr(process, "terminate"):
                    process.terminate()
                    await process.wait()
                elif hasattr(process, "close"):
                    await process.close()
            except Exception as e:
                logger.warning(f"Error closing connection to {server_id}: {e}")

        status = self._status[server_id]
        status.connected = False
        status.tools = []

        self._event_bus.publish(
            MCPServerDisconnected(
                source_service="mcp_manager",
                correlation_id=server_id,
                payload={"server_id": server_id, "reason": "manual_disconnect"},
            )
        )

        logger.info(f"Disconnected from MCP server: {server_id}")
        return True

    async def _discover_tools(self, server_id: str) -> list[MCPTool]:
        """Discover tools from an MCP server (placeholder)."""
        # In real implementation, this would call the MCP server's tools/list
        # For now, return mock tools based on server config
        config = self._servers.get(server_id)
        if not config:
            return []

        # Mock tools for demo
        return [
            MCPTool(
                name=f"{config.name}_tool",
                description=f"Tool from {config.name}",
                input_schema={"type": "object", "properties": {}},
                server_id=server_id,
            )
        ]

    async def call_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        call_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Call an MCP tool.

        Args:
            server_id: Server identifier
            tool_name: Tool name
            arguments: Tool arguments
            call_id: Optional call ID for tracking

        Returns:
            Tool result
        """
        call_id = call_id or f"call_{datetime.utcnow().timestamp()}"
        status = self._status.get(server_id)

        if not status or not status.connected:
            raise RuntimeError(f"Server {server_id} not connected")

        # Verify tool exists
        tool = next((t for t in status.tools if t.name == tool_name), None)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found on server {server_id}")

        self._event_bus.publish(
            MCPToolCalled(
                source_service="mcp_manager",
                correlation_id=call_id,
                payload={
                    "call_id": call_id,
                    "server_id": server_id,
                    "tool_name": tool_name,
                    "arguments": arguments,
                },
            )
        )

        try:
            # Placeholder for actual tool call
            # In real implementation, this would send via the appropriate transport
            await asyncio.sleep(0.1)

            result = {"success": True, "result": f"Mock result from {tool_name}"}

            self._event_bus.publish(
                MCPToolResult(
                    source_service="mcp_manager",
                    correlation_id=call_id,
                    payload={
                        "call_id": call_id,
                        "success": True,
                        "result": result,
                        "error": None,
                    },
                )
            )

            return result

        except Exception as e:
            error_result = {"success": False, "error": str(e)}

            self._event_bus.publish(
                MCPToolResult(
                    source_service="mcp_manager",
                    correlation_id=call_id,
                    payload={
                        "call_id": call_id,
                        "success": False,
                        "result": {},
                        "error": str(e),
                    },
                )
            )

            raise

    def get_server_status(self, server_id: str) -> MCPServerStatus | None:
        """Get server connection status."""
        return self._status.get(server_id)

    def list_servers(self) -> list[MCPServerConfig]:
        """List all configured servers."""
        return list(self._servers.values())

    def list_tools(self, server_id: str | None = None) -> list[MCPTool]:
        """List available tools."""
        if server_id:
            return self._tools_cache.get(server_id, [])
        tools = []
        for server_tools in self._tools_cache.values():
            tools.extend(server_tools)
        return tools

    async def connect_all(self) -> dict[str, bool]:
        """Connect to all configured servers."""
        results = {}
        for server_id in self._servers:
            results[server_id] = await self.connect(server_id)
        return results

    async def disconnect_all(self) -> None:
        """Disconnect from all servers."""
        for server_id in list(self._servers.keys()):
            await self.disconnect(server_id)

    def get_stats(self) -> dict[str, Any]:
        """Get MCP manager statistics."""
        connected = sum(1 for s in self._status.values() if s.connected)
        total_tools = sum(len(t) for t in self._tools_cache.values())
        return {
            "configured_servers": len(self._servers),
            "connected_servers": connected,
            "total_tools": total_tools,
            "servers": {
                sid: {
                    "connected": status.connected,
                    "tools": len(status.tools),
                    "last_error": status.last_error,
                }
                for sid, status in self._status.items()
            },
        }


# Global MCP manager
_global_mcp_manager: MCPManager | None = None


def get_mcp_manager(config_dir: Path | None = None) -> MCPManager:
    """Get or create the global MCP manager."""
    global _global_mcp_manager
    if _global_mcp_manager is None:
        _global_mcp_manager = MCPManager(config_dir)
    return _global_mcp_manager


def set_mcp_manager(manager: MCPManager) -> None:
    """Set the global MCP manager."""
    global _global_mcp_manager
    _global_mcp_manager = manager


__all__ = [
    "MCPManager",
    "MCPServerConfig",
    "MCPTool",
    "MCPServerStatus",
    "MCPTransport",
    "get_mcp_manager",
    "set_mcp_manager",
]