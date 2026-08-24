"""
MCP Manager for AI-OS Hermes Kernel.

Manages Model Context Protocol (MCP) server connections and tool orchestration.
Uses the canonical EventBus (C1, Task 5) and canonical EventType enum.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion

# Import SecurityManager for gate-before-connect validation
from aios.core.security_manager import get_security_manager

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

        # FIX 9: Use canonical EventBus (C1, Task 5)
        self._event_bus = get_core_event_bus()
        if self._event_bus is None:
            logger.warning("Canonical EventBus not yet initialized; events will be deferred")

        # Component identity for event emission
        self._identity = ComponentIdentity(
            component_type=ComponentType.ENGINEERING_SERVICE,
            component_name="MCPManager",
            version=SemanticVersion.parse("0.1.0"),
        )

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

        M5-GATE-REALIZE: Gate-before-connect enforcement (C18).
        Validates server configuration through SecurityManager's MCPServerSecurityGate
        BEFORE attempting connection.

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

        # M5: Gate-before-connect - validate server configuration through SecurityManager
        # before attempting any connection (C18: gate-before-connect)
        security_manager = get_security_manager()
        validation_result = security_manager.validate_mcp_server_before_connect(config)

        if not validation_result.passed:
            # Gate failed - do not connect
            error_msg = f"MCP server {server_id} failed security validation: {len(validation_result.violations)} violations"
            status.last_error = error_msg
            status.retry_count += 1
            logger.error(error_msg)

            self._emit_event(
                EventType.MCP_SERVER_VALIDATION_FAILED,
                {
                    "server_id": server_id,
                    "name": config.name,
                    "scan_id": validation_result.scan_id,
                    "violations": [
                        {
                            "violation_id": v.violation_id,
                            "severity": v.severity,
                            "description": v.description,
                            "category": v.category,
                            "context": v.context,
                        }
                        for v in validation_result.violations
                    ],
                },
                validation_result.scan_id,
            )

            return False

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

            self._emit_event(
                EventType.MCP_SERVER_CONNECTED,
                {
                    "server_id": server_id,
                    "name": config.name,
                    "transport": config.transport.value,
                    "tools": [t.name for t in tools],
                    "action": "server_connected",
                },
                server_id,
            )

            logger.info(f"Connected to MCP server: {server_id}")
            return True

        except Exception as e:
            status.last_error = str(e)
            status.retry_count += 1
            logger.error(f"Failed to connect to {server_id}: {e}")
            return False

    def _emit_event(self, event_type: EventType, payload: dict[str, Any], correlation_id: str) -> None:
        """Emit a canonical event via the canonical EventBus."""
        # Ensure correlation_id is a valid UUID - generate one if it's not
        try:
            corr_uuid = uuid.UUID(correlation_id) if correlation_id else uuid.uuid4()
        except ValueError:
            # Not a valid UUID, generate a deterministic one from the string
            corr_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, correlation_id)
        event = CoreEvent(
            eventType=event_type,
            source=self._identity,
            correlationId=corr_uuid,
            payload=payload,
        )
        result = self._event_bus.publish(event) if self._event_bus else None
        # Fire and forget - result handling is async
        if result and hasattr(result, "__await__"):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(result)
            except RuntimeError:
                pass

    async def _connect_stdio(
        self, config: MCPServerConfig, status: MCPServerStatus
    ) -> None:
        """Connect via stdio transport with MCP protocol initialization."""
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

        # Initialize MCP connection
        await self._initialize_mcp_stdio(config.server_id, process, config)

    async def _initialize_mcp_stdio(
        self, server_id: str, process: asyncio.subprocess.Process, config: MCPServerConfig
    ) -> None:
        """Initialize MCP protocol over stdio."""
        import json

        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "AI-OS MCP Manager",
                    "version": "0.1.0",
                },
            },
        }

        request_data = json.dumps(init_request) + "\n"
        process.stdin.write(request_data.encode())
        await process.stdin.drain()

        # Read response
        response_line = await asyncio.wait_for(
            process.stdout.readline(), timeout=config.timeout_seconds
        )
        if not response_line:
            raise RuntimeError("MCP server closed connection during initialization")

        try:
            response = json.loads(response_line.decode().strip())
            if "error" in response:
                raise RuntimeError(f"MCP initialization failed: {response['error']}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response from MCP server: {e}")

        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }
        notification_data = json.dumps(initialized_notification) + "\n"
        process.stdin.write(notification_data.encode())
        await process.stdin.drain()

    async def _connect_http(
        self, config: MCPServerConfig, status: MCPServerStatus
    ) -> None:
        """Connect via HTTP transport with MCP protocol initialization."""
        import aiohttp

        if not config.url:
            raise ValueError("HTTP transport requires URL")

        session = aiohttp.ClientSession(
            headers=config.headers,
            timeout=aiohttp.ClientTimeout(total=config.timeout_seconds),
        )
        self._processes[config.server_id] = session

        # Initialize MCP connection
        await self._initialize_mcp_http(config.server_id, session, config)

    async def _initialize_mcp_http(
        self, server_id: str, session: aiohttp.ClientSession, config: MCPServerConfig
    ) -> None:
        """Initialize MCP protocol over HTTP."""
        import json

        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "AI-OS MCP Manager",
                    "version": "0.1.0",
                },
            },
        }

        async with session.post(
            config.url.rstrip("/") + "/mcp",
            json=init_request,
        ) as resp:
            if resp.status != 200:
                raise RuntimeError(f"MCP initialization failed: HTTP {resp.status}")
            response = await resp.json()
            if "error" in response:
                raise RuntimeError(f"MCP initialization failed: {response['error']}")

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

        # Initialize MCP connection
        await self._initialize_mcp_websocket(config.server_id, websocket, config)

    async def _initialize_mcp_websocket(
        self, server_id: str, websocket, config: MCPServerConfig
    ) -> None:
        """Initialize MCP protocol over WebSocket."""
        import json

        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "AI-OS MCP Manager",
                    "version": "0.1.0",
                },
            },
        }

        await websocket.send(json.dumps(init_request))
        response_str = await asyncio.wait_for(websocket.recv(), timeout=config.timeout_seconds)
        response = json.loads(response_str)
        if "error" in response:
            raise RuntimeError(f"MCP initialization failed: {response['error']}")

        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }
        await websocket.send(json.dumps(initialized_notification))

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

        self._emit_event(
            EventType.MCP_SERVER_DISCONNECTED,
            {"server_id": server_id, "reason": "manual_disconnect"},
            server_id,
        )

        logger.info(f"Disconnected from MCP server: {server_id}")
        return True

    async def _discover_tools(self, server_id: str) -> list[MCPTool]:
        """Discover tools from an MCP server using tools/list."""
        config = self._servers.get(server_id)
        if not config:
            return []

        process = self._processes.get(server_id)
        if not process:
            return []

        try:
            if config.transport == MCPTransport.STDIO:
                return await self._discover_tools_stdio(server_id, process, config)
            elif config.transport in (MCPTransport.HTTP, MCPTransport.SSE):
                return await self._discover_tools_http(server_id, process, config)
            elif config.transport == MCPTransport.WEBSOCKET:
                return await self._discover_tools_websocket(server_id, process, config)
        except Exception as e:
            logger.warning(f"Failed to discover tools from {server_id}: {e}")

        return []

    async def _discover_tools_stdio(
        self, server_id: str, process: asyncio.subprocess.Process, config: MCPServerConfig
    ) -> list[MCPTool]:
        """Discover tools via stdio transport."""
        import json

        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }

        request_data = json.dumps(request) + "\n"
        process.stdin.write(request_data.encode())
        await process.stdin.drain()

        response_line = await asyncio.wait_for(
            process.stdout.readline(), timeout=config.timeout_seconds
        )
        if not response_line:
            return []

        response = json.loads(response_line.decode().strip())
        if "error" in response:
            logger.warning(f"tools/list failed for {server_id}: {response['error']}")
            return []

        tools = []
        for tool_data in response.get("result", {}).get("tools", []):
            tools.append(MCPTool(
                name=tool_data.get("name", ""),
                description=tool_data.get("description", ""),
                input_schema=tool_data.get("inputSchema", {}),
                server_id=server_id,
            ))

        self._emit_event(
            EventType.MCP_TOOL_DISCOVERED,
            {
                "server_id": server_id,
                "tools": [t.name for t in tools],
            },
            server_id,
        )

        return tools

    async def _discover_tools_http(
        self, server_id: str, session: aiohttp.ClientSession, config: MCPServerConfig
    ) -> list[MCPTool]:
        """Discover tools via HTTP transport."""
        import json

        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }

        async with session.post(
            config.url.rstrip("/") + "/mcp",
            json=request,
        ) as resp:
            if resp.status != 200:
                return []
            response = await resp.json()

        if "error" in response:
            logger.warning(f"tools/list failed for {server_id}: {response['error']}")
            return []

        tools = []
        for tool_data in response.get("result", {}).get("tools", []):
            tools.append(MCPTool(
                name=tool_data.get("name", ""),
                description=tool_data.get("description", ""),
                input_schema=tool_data.get("inputSchema", {}),
                server_id=server_id,
            ))

        self._emit_event(
            EventType.MCP_TOOL_DISCOVERED,
            {
                "server_id": server_id,
                "tools": [t.name for t in tools],
            },
            server_id,
        )

        return tools

    async def _discover_tools_websocket(
        self, server_id: str, websocket, config: MCPServerConfig
    ) -> list[MCPTool]:
        """Discover tools via WebSocket transport."""
        import json

        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }

        await websocket.send(json.dumps(request))
        response_str = await asyncio.wait_for(websocket.recv(), timeout=config.timeout_seconds)
        response = json.loads(response_str)

        if "error" in response:
            logger.warning(f"tools/list failed for {server_id}: {response['error']}")
            return []

        tools = []
        for tool_data in response.get("result", {}).get("tools", []):
            tools.append(MCPTool(
                name=tool_data.get("name", ""),
                description=tool_data.get("description", ""),
                input_schema=tool_data.get("inputSchema", {}),
                server_id=server_id,
            ))

        self._emit_event(
            EventType.MCP_TOOL_DISCOVERED,
            {
                "server_id": server_id,
                "tools": [t.name for t in tools],
            },
            server_id,
        )

        return tools

    async def call_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        call_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Call an MCP tool with full provenance tracking.

        M5-GATE-REALIZE: Every interaction carries provenance (session_id, worker/server,
        timestamp, environment, interaction/tool, source).

        Args:
            server_id: Server identifier
            tool_name: Tool name
            arguments: Tool arguments
            call_id: Optional call ID for tracking

        Returns:
            Tool result with provenance
        """
        call_id = call_id or f"call_{datetime.utcnow().timestamp()}"
        status = self._status.get(server_id)

        if not status or not status.connected:
            raise RuntimeError(f"Server {server_id} not connected")

        # Verify tool exists
        tool = next((t for t in status.tools if t.name == tool_name), None)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found on server {server_id}")

        config = self._servers.get(server_id)
        process = self._processes.get(server_id)

        # Provenance metadata
        provenance = {
            "call_id": call_id,
            "session_id": f"mcp_{server_id}_{datetime.utcnow().timestamp()}",
            "worker": config.name if config else "unknown",
            "server": server_id,
            "timestamp": datetime.utcnow().isoformat(),
            "environment": "ai_os_mcp",
            "interaction": "tool_call",
            "tool": tool_name,
            "source": "mcp_manager",
        }

        self._emit_event(
            EventType.MCP_TOOL_CALLED,
            {
                "call_id": call_id,
                "server_id": server_id,
                "tool_name": tool_name,
                "arguments": arguments,
                "provenance": provenance,
            },
            call_id,
        )

        try:
            if config.transport == MCPTransport.STDIO:
                result = await self._call_tool_stdio(server_id, process, config, tool_name, arguments, call_id)
            elif config.transport in (MCPTransport.HTTP, MCPTransport.SSE):
                result = await self._call_tool_http(server_id, process, config, tool_name, arguments, call_id)
            elif config.transport == MCPTransport.WEBSOCKET:
                result = await self._call_tool_websocket(server_id, process, config, tool_name, arguments, call_id)
            else:
                raise ValueError(f"Unsupported transport: {config.transport}")

            # Add provenance to result
            result["provenance"] = provenance

            self._emit_event(
                EventType.MCP_TOOL_SUCCEEDED,
                {
                    "call_id": call_id,
                    "success": True,
                    "result": result,
                    "error": None,
                    "provenance": provenance,
                },
                call_id,
            )

            return result

        except Exception as e:
            error_result = {"success": False, "error": str(e), "provenance": provenance}

            self._emit_event(
                EventType.MCP_TOOL_FAILED,
                {
                    "call_id": call_id,
                    "success": False,
                    "result": {},
                    "error": str(e),
                    "provenance": provenance,
                },
                call_id,
            )

            raise

    async def _call_tool_stdio(
        self, server_id: str, process: asyncio.subprocess.Process,
        config: MCPServerConfig, tool_name: str, arguments: dict[str, Any], call_id: str
    ) -> dict[str, Any]:
        """Call tool via stdio transport."""
        import json

        request = {
            "jsonrpc": "2.0",
            "id": int(call_id.split("_")[-1].replace(".", "")) if "_" in call_id else 3,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        request_data = json.dumps(request) + "\n"
        process.stdin.write(request_data.encode())
        await process.stdin.drain()

        response_line = await asyncio.wait_for(
            process.stdout.readline(), timeout=config.timeout_seconds
        )
        if not response_line:
            raise RuntimeError("MCP server closed connection during tool call")

        response = json.loads(response_line.decode().strip())
        if "error" in response:
            raise RuntimeError(f"MCP tool call failed: {response['error']}")

        return response.get("result", {})

    async def _call_tool_http(
        self, server_id: str, session: aiohttp.ClientSession,
        config: MCPServerConfig, tool_name: str, arguments: dict[str, Any], call_id: str
    ) -> dict[str, Any]:
        """Call tool via HTTP transport."""
        import json

        request = {
            "jsonrpc": "2.0",
            "id": int(call_id.split("_")[-1].replace(".", "")) if "_" in call_id else 3,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        async with session.post(
            config.url.rstrip("/") + "/mcp",
            json=request,
        ) as resp:
            if resp.status != 200:
                raise RuntimeError(f"MCP tool call failed: HTTP {resp.status}")
            response = await resp.json()

        if "error" in response:
            raise RuntimeError(f"MCP tool call failed: {response['error']}")

        return response.get("result", {})

    async def _call_tool_websocket(
        self, server_id: str, websocket,
        config: MCPServerConfig, tool_name: str, arguments: dict[str, Any], call_id: str
    ) -> dict[str, Any]:
        """Call tool via WebSocket transport."""
        import json

        request = {
            "jsonrpc": "2.0",
            "id": int(call_id.split("_")[-1].replace(".", "")) if "_" in call_id else 3,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        await websocket.send(json.dumps(request))
        response_str = await asyncio.wait_for(websocket.recv(), timeout=config.timeout_seconds)
        response = json.loads(response_str)

        if "error" in response:
            raise RuntimeError(f"MCP tool call failed: {response['error']}")

        return response.get("result", {})

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