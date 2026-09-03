"""
MCP Capability Abstraction Layer for AI-OS Hermes Kernel.

Provides a generic abstraction for MCP (Model Context Protocol) capabilities that
allows AI-OS to consume MCP servers directly without requiring Claude Code
or plugin-specific infrastructure.

Architecture:
CapabilityManager
 ↓
MCP Capability (this layer)
 ↓
MCPManager
 ↓
MCP Server
 ↓
tool call
 ↓
result
 ↓
Provenance
 ↓
Verification
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from aios.core.mcp_manager import MCPManager, MCPTool
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion
# Avoid circular import - define minimal versions locally
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

# Local definitions to avoid circular import with capability_manager
@dataclass
class LocalCapabilityRegistryEntry:
    """Minimal CapabilityRegistryEntry for MCP capability conversion."""
    capability_id: str
    facade: str
    provider_id: str
    provider_metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    state: Any = None  # Will be set to actual CapabilityState later
    security_context: Dict[str, Any] = field(default_factory=dict)
    resource_profile: Dict[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = field(default_factory=tuple)
    trust_level: str = "untrusted"
    authority_classification: str = "advisory"
    adapter_binding: Dict[str, Any] = field(default_factory=dict)
    operations: tuple[str, ...] = field(default_factory=tuple)
    health_status: str = "unknown"
    availability: str = "unavailable"
    enabled: bool = True
    discovered_from: str = ""
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the entry to a JSON-safe dict."""
        return {
            "capability_id": self.capability_id,
            "facade": self.facade,
            "provider_id": self.provider_id,
            "provider_metadata": self.provider_metadata,
            "version": self.version,
            "state": self.state.value if hasattr(self.state, 'value') else str(self.state),
            "security_context": self.security_context,
            "resource_profile": self.resource_profile,
            "tags": list(self.tags),
            "trust_level": self.trust_level,
            "authority_classification": self.authority_classification,
            "adapter_binding": self.adapter_binding,
            "operations": list(self.operations),
            "health_status": self.health_status,
            "availability": self.availability,
            "enabled": self.enabled,
            "discovered_from": self.discovered_from,
            "dependencies": list(self.dependencies),
            "last_error": self.last_error,
        }

# Local enum definitions to avoid circular import
class LocalCapabilityState(str, Enum):
    REGISTERED = "REGISTERED"
    DISABLED = "DISABLED"
    DEPRECATED = "DEPRECATED"
    REMOVED = "REMOVED"

class LocalTrustLevel(str, Enum):
    BUILTIN = "builtin"
    TRUSTED = "trusted"
    TRUSTED_CONTEXTUAL = "trusted_contextual"
    UNTRUSTED = "untrusted"

class LocalAuthorityClassification(str, Enum):
    AUTHORITATIVE = "authoritative"
    CONTEXTUAL = "contextual"
    ADVISORY = "advisory"
    ADVISORY_ONLY = "advisory_only"

class LocalCapabilityAvailability(str, Enum):
    AVAILABLE = "available"
    DEGRADED = "degraded"
    ERROR = "error"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"
    UNKNOWN = "unknown"
from aios.core.structured_logger import StructuredLogger
from aios.core.configuration_manager import ConfigurationManager
from aios.core.service_registry import ServiceRegistry, ServiceType


logger = logging.getLogger(__name__)


class MCPCapabilityTransport(str, Enum):
    """MCP transport types mirrored from MCPManager for capability layer."""
    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"
    WEBSOCKET = "websocket"


@dataclass
class MCPCapabilityConfig:
    """Configuration for an MCP capability."""
    capability_id: str
    name: str
    transport: MCPCapabilityTransport = MCPCapabilityTransport.STDIO
    command: Optional[List[str]] = None  # For stdio
    url: Optional[str] = None  # For HTTP/SSE/WebSocket
    env: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 30
    auto_reconnect: bool = True
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)
    trust_level: str = LocalTrustLevel.UNTRUSTED.value
    authority_classification: str = LocalAuthorityClassification.ADVISORY.value
    discovered_from: str = "mcp_capability_layer"


@dataclass
class MCPCapabilityStatus:
    """Runtime status of an MCP capability."""
    capability_id: str
    connected: bool = False
    transport: MCPCapabilityTransport = MCPCapabilityTransport.STDIO
    tools: List[MCPTool] = field(default_factory=list)
    last_connected: Optional[Any] = None  # datetime
    last_error: Optional[str] = None
    retry_count: int = 0


class MCPCapability:
    """
    MCP Capability Abstraction Layer.

    Represents an MCP server as a capability that can be managed by CapabilityManager.
    Provides generic tool discovery and invocation using actual MCP tool names.

    This layer sits between CapabilityManager and MCPManager:
    CapabilityManager → MCPCapability → MCPManager → MCP Server
    """

    def __init__(
        self,
        config: MCPCapabilityConfig,
        mcp_manager: Optional[MCPManager] = None,
        config_manager: Optional[ConfigurationManager] = None,
        service_registry: Optional[ServiceRegistry] = None,
        structured_logger: Optional[StructuredLogger] = None,
    ):
        """
        Initialize the MCP Capability.

        Args:
            config: MCPCapabilityConfig instance
            mcp_manager: MCPManager instance (will create global if None)
            config_manager: ConfigurationManager instance
            service_registry: ServiceRegistry instance
            structured_logger: StructuredLogger instance
        """
        self.config = config
        self._mcp_manager = mcp_manager or MCPManager()
        self._config_manager = config_manager
        self._service_registry = service_registry
        self._logger = structured_logger
        self._status = MCPCapabilityStatus(capability_id=config.capability_id)

        # Component identity for event emission
        self._identity = ComponentIdentity(
            component_type=ComponentType.ENGINEERING_SERVICE,
            component_name="MCPCapability",
            version=SemanticVersion.parse("0.1.0"),
        )

        # Event bus for canonical events
        self._event_bus = get_core_event_bus()

        # Tool cache for performance
        self._tool_cache: Dict[str, MCPTool] = {}

    async def initialize(self) -> bool:
        """
        Initialize the MCP capability by connecting to the MCP server
        and discovering available tools.

        Returns:
            True if initialized successfully, False otherwise
        """
        try:
            # Convert config to MCPServerConfig
            from aios.core.mcp_manager import MCPServerConfig, MCPTransport

            mcp_config = MCPServerConfig(
                server_id=self.config.capability_id,
                name=self.config.name,
                transport=MCPTransport(self.config.transport.value),
                command=self.config.command,
                url=self.config.url,
                env=self.config.env,
                headers=self.config.headers,
                timeout_seconds=self.config.timeout_seconds,
                auto_reconnect=self.config.auto_reconnect,
                max_retries=self.config.max_retries,
                metadata=self.config.metadata,
            )

            # Connect to MCP server (this includes SecurityManager gate-before-connect)
            connected = await self._mcp_manager.connect(self.config.capability_id)
            if not connected:
                logger.error(f"Failed to connect to MCP server {self.config.capability_id}")
                return False

            # Update status
            self._status.connected = True
            self._status.transport = self.config.transport

            # Discover and cache tools
            await self._discover_and_cache_tools()

            logger.info(f"MCP capability {self.config.capability_id} initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize MCP capability {self.config.capability_id}: {e}")
            self._status.last_error = str(e)
            self._status.retry_count += 1
            return False

    async def shutdown(self) -> None:
        """Shutdown the MCP capability by disconnecting from the MCP server."""
        try:
            await self._mcp_manager.disconnect(self.config.capability_id)
            self._status.connected = False
            self._status.tools = []
            self._tool_cache.clear()
            logger.info(f"MCP capability {self.config.capability_id} shutdown")
        except Exception as e:
            logger.warning(f"Error shutting down MCP capability {self.config.capability_id}: {e}")

    async def _discover_and_cache_tools(self) -> None:
        """Discover tools from the MCP server and cache them for performance."""
        try:
            # Get tools from MCPManager
            tools = await self._mcp_manager.list_tools(self.config.capability_id)

            # Update status and cache
            self._status.tools = tools
            self._tool_cache = {tool.name: tool for tool in tools}

            # Emit tools discovered event
            if self._event_bus:
                self._emit_event(
                    EventType.SERVICE_STARTED,  # Mapping for tool discovery
                    {
                        "capability_id": self.config.capability_id,
                        "tools": [tool.name for tool in tools],
                        "transport": self.config.transport.value,
                    },
                    self.config.capability_id,
                )

            logger.debug(f"Discovered {len(tools)} tools for MCP capability {self.config.capability_id}")

        except Exception as e:
            logger.warning(f"Failed to discover tools for MCP capability {self.config.capability_id}: {e}")
            self._status.last_error = str(e)

    def get_tool(self, tool_name: str) -> Optional[MCPTool]:
        """
        Get a tool by its actual name from the MCP server.

        Args:
            tool_name: The actual tool name as discovered by tools/list

        Returns:
            MCPTool instance if found, None otherwise
        """
        return self._tool_cache.get(tool_name)

    def list_tools(self) -> List[MCPTool]:
        """
        List all available tools from the MCP server.

        Returns:
            List of MCPTool instances
        """
        return list(self._tool_cache.values())

    def get_tool_names(self) -> List[str]:
        """
        Get the names of all available tools.

        Returns:
            List of tool name strings
        """
        return list(self._tool_cache.keys())

    async def invoke_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        call_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Invoke an MCP tool by its actual name.

        This is the core generic invocation method that operates on the MCP protocol
        level without requiring semantic mappings.

        Args:
            tool_name: The actual tool name as discovered by tools/list
            arguments: Tool arguments according to the tool's inputSchema
            call_id: Optional call ID for tracking

        Returns:
            Tool result dictionary

        Raises:
            ValueError: If the tool is not found on the MCP server
            RuntimeError: If the MCP server is not connected
        """
        if not self._status.connected:
            raise RuntimeError(f"MCP capability {self.config.capability_id} is not connected")

        # Verify tool exists
        tool = self.get_tool(tool_name)
        if not tool:
            available_tools = ", ".join(self.get_tool_names())
            raise ValueError(
                f"Tool '{tool_name}' not found on MCP capability {self.config.capability_id}. "
                f"Available tools: {available_tools}"
            )

        # Provenance metadata
        provenance = {
            "capability_id": self.config.capability_id,
            "provider": self.config.name,
            "transport": self.config.transport.value if hasattr(self.config.transport, 'value') else str(self.config.transport),
            "tool_name": tool_name,
            "timestamp": self._get_timestamp(),
            "environment": "ai_os_mcp_capability",
            "interaction": "tool_invoke",
            "source": "mcp_capability_layer",
            "call_id": call_id or f"call_{self._get_timestamp()}",
            "authority": self.config.authority_classification,
            "trust_level": self.config.trust_level,
        }

        # Emit tool invocation event
        self._emit_event(
            EventType.SKILL_EXECUTED,  # Mapping for capability invocation
            {
                "capability_id": self.config.capability_id,
                "tool_name": tool_name,
                "arguments": arguments,
                "provenance": provenance,
            },
            provenance["call_id"],
        )

        try:
            # Call the tool via MCPManager
            result = await self._mcp_manager.call_tool(
                self.config.capability_id,
                tool_name,
                arguments,
                call_id
            )

            # Add provenance to result
            if isinstance(result, dict):
                result["provenance"] = provenance

            # Emit success event
            self._emit_event(
                EventType.SKILL_EXECUTED,  # Success uses same event type in current architecture
                {
                    "capability_id": self.config.capability_id,
                    "tool_name": tool_name,
                    "success": True,
                    "result": result,
                    "provenance": provenance,
                },
                provenance["call_id"],
            )

            return result

        except Exception as e:
            # Emit failure event
            error_result = {
                "success": False,
                "error": str(e),
                "provenance": provenance
            }

            self._emit_event(
                EventType.SKILL_FAILED,  # Mapping for capability invocation failure
                {
                    "capability_id": self.config.capability_id,
                    "tool_name": tool_name,
                    "success": False,
                    "error": str(e),
                    "provenance": provenance,
                },
                provenance["call_id"],
            )

            raise

    def get_status(self) -> MCPCapabilityStatus:
        """
        Get the current status of the MCP capability.

        Returns:
            MCPCapabilityStatus instance
        """
        return self._status

    def is_connected(self) -> bool:
        """
        Check if the MCP capability is connected.

        Returns:
            True if connected, False otherwise
        """
        return self._status.connected

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat()

    def _emit_event(self, event_type: EventType, payload: Dict[str, Any], correlation_id: str) -> None:
        """Emit a canonical event via the canonical EventBus."""
        if self._event_bus is None:
            return

        try:
            import uuid
            corr_uuid = uuid.UUID(correlation_id) if correlation_id else uuid.uuid4()
        except ValueError:
            # Not a valid UUID, generate a deterministic one from the string
            import uuid
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

    def to_capability_registry_entry(self) -> Any:
        """
        Convert this MCP capability to a CapabilityRegistryEntry for registration
        with CapabilityManager.

        Returns:
            CapabilityRegistryEntry instance
        """
        # Import locally to avoid circular import
        from aios.core.capability_manager import (
            CapabilityRegistryEntry,
            CapabilityState,
            TrustLevel,
            AuthorityClassification,
            CapabilityAvailability,
        )

        return CapabilityRegistryEntry(
            capability_id=self.config.capability_id,
            facade=self.config.name,  # Using name as facade for MCP capabilities
            provider_id=self.config.capability_id,
            provider_metadata={
                "transport": self.config.transport.value,
                "command": self.config.command,
                "url": self.config.url,
                "metadata": self.config.metadata,
            },
            version="1.0.0",
            state=CapabilityState.REGISTERED if self._status.connected else CapabilityState.DISABLED,
            security_context={},  # Security handled by SecurityManager gate-before-connect
            resource_profile={},
            tags=("mcp", "capability"),
            trust_level=self.config.trust_level,
            authority_classification=self.config.authority_classification,
            adapter_binding={},  # No specific adapter binding for generic MCP capability
            operations=tuple(self.get_tool_names()),  # All discovered tools as operations
            health_status="healthy" if self._status.connected else "unhealthy",
            availability=CapabilityAvailability.AVAILABLE if self._status.connected else CapabilityAvailability.UNAVAILABLE,
            enabled=self._status.connected,
            discovered_from=self.config.discovered_from,
            dependencies=(),  # MCP capabilities typically have no dependencies
            last_error=self._status.last_error,
        )


# Global MCP capability manager for tracking multiple MCP capabilities
class MCPCapabilityManager:
    """
    Manager for multiple MCP capabilities.

    Provides a registry interface for MCP capabilities that can be
    integrated with CapabilityManager.
    """

    def __init__(self):
        self._capabilities: Dict[str, MCPCapability] = {}
        self._logger = logger

    def register_capability(self, config: MCPCapabilityConfig) -> MCPCapability:
        """
        Register and initialize an MCP capability.

        Args:
            config: MCPCapabilityConfig instance

        Returns:
            Initialized MCPCapability instance
        """
        if config.capability_id in self._capabilities:
            logger.warning(f"MCP capability {config.capability_id} already registered")
            return self._capabilities[config.capability_id]

        capability = MCPCapability(config)
        self._capabilities[config.capability_id] = capability
        logger.info(f"Registered MCP capability: {config.capability_id}")
        return capability

    def get_capability(self, capability_id: str) -> Optional[MCPCapability]:
        """
        Get an MCP capability by ID.

        Args:
            capability_id: Capability identifier

        Returns:
            MCPCapability instance if found, None otherwise
        """
        return self._capabilities.get(capability_id)

    def list_capabilities(self) -> List[MCPCapability]:
        """
        List all registered MCP capabilities.

        Returns:
            List of MCPCapability instances
        """
        return list(self._capabilities.values())

    async def initialize_all(self) -> Dict[str, bool]:
        """
        Initialize all registered MCP capabilities.

        Returns:
            Dictionary mapping capability_id to initialization success
        """
        results = {}
        for capability_id, capability in self._capabilities.items():
            try:
                results[capability_id] = await capability.initialize()
            except Exception as e:
                logger.error(f"Failed to initialize MCP capability {capability_id}: {e}")
                results[capability_id] = False
        return results

    async def shutdown_all(self) -> None:
        """Shutdown all registered MCP capabilities."""
        for capability_id, capability in self._capabilities.items():
            try:
                await capability.shutdown()
            except Exception as e:
                logger.warning(f"Error shutting down MCP capability {capability_id}: {e}")


# Global MCP capability manager instance
_global_mcp_capability_manager: Optional[MCPCapabilityManager] = None


def get_mcp_capability_manager() -> MCPCapabilityManager:
    """Get or create the global MCP capability manager."""
    global _global_mcp_capability_manager
    if _global_mcp_capability_manager is None:
        _global_mcp_capability_manager = MCPCapabilityManager()
    return _global_mcp_capability_manager


def set_mcp_capability_manager(manager: MCPCapabilityManager) -> None:
    """Set the global MCP capability manager."""
    global _global_mcp_capability_manager
    _global_mcp_capability_manager = manager