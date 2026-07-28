"""MCP Service.

Engineering Service wrapping the Kernel's MCPManager behind an event-driven
facade. Manages MCP server connections and tool orchestration; exposes
connect/disconnect/call_tool and emits MCPServerConnected/MCPServerDisconnected/
MCPToolCalled/MCPToolResult.
"""

from __future__ import annotations

import logging
from typing import Any

from aios.core.mcp_manager import MCPManager, get_mcp_manager
from aios.events.base import Event
from aios.events.types import (
    MCPServerConnected,
    MCPServerDisconnected,
    MCPToolCalled,
    MCPToolResult,
)
from aios.services.base import BaseService

logger = logging.getLogger(__name__)


class MCPService(BaseService):
    """Event-driven facade over the Kernel MCPManager."""

    name = "mcp"
    version = "1.0.0"
    description = "MCP server/client management, tool orchestration"
    depends_on: list[str] = []

    def __init__(self, *args, manager: MCPManager | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._manager = manager or get_mcp_manager()

    @property
    def manager(self) -> MCPManager:
        return self._manager

    async def on_start(self) -> None:
        # No inbound events to handle by default; capability-driven via API.
        pass

    async def connect(self, server_id: str) -> bool:
        ok = await self._manager.connect(server_id)
        return ok

    async def connect_all(self) -> dict[str, bool]:
        return await self._manager.connect_all()

    async def disconnect(self, server_id: str) -> bool:
        return await self._manager.disconnect(server_id)

    async def disconnect_all(self) -> None:
        await self._manager.disconnect_all()

    async def call_tool(
        self, server_id: str, tool_name: str, arguments: dict[str, Any], call_id: str | None = None
    ) -> dict[str, Any]:
        return await self._manager.call_tool(server_id, tool_name, arguments, call_id)

    def list_servers(self):
        return self._manager.list_servers()

    def list_tools(self, server_id: str | None = None):
        return self._manager.list_tools(server_id)

    def get_stats(self) -> dict[str, Any]:
        base = super().get_stats()
        base["manager"] = self._manager.get_stats()
        return base


__all__ = ["MCPService"]
