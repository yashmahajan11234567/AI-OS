"""
M8-T4 — Claude-Mem Contextual Memory Adapter.

Implements BaseExecutionAdapter for the Claude-Mem MCP server.
Provides contextual memory retrieval: context, recent, by_tag.
All results marked advisory per C14 - Claude-Mem is UNTRUSTED contextual memory.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from aios.adapters.base import BaseExecutionAdapter, ExecutionResult, ExecutionStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error Hierarchy
# ---------------------------------------------------------------------------


class ClaudeMemError(Exception):
    """Base error for Claude-Mem adapter."""

    pass


class ClaudeMemUnavailableError(ClaudeMemError):
    """Claude-Mem MCP server not reachable."""

    pass


class ClaudeMemTimeoutError(ClaudeMemError):
    """Operation exceeded timeout."""

    pass


class ClaudeMemValidationError(ClaudeMemError):
    """Invalid input for Claude-Mem operation."""

    pass


class ClaudeMemSecurityError(ClaudeMemError):
    """Security violation (sensitive data, prompt injection)."""

    pass


class MalformedClaudeMemResponseError(ClaudeMemError):
    """Malformed response from Claude-Mem MCP."""

    pass


# ---------------------------------------------------------------------------
# Security / Validation Constants
# ---------------------------------------------------------------------------

SENSITIVE_PROPERTY_KEYS = frozenset(
    [
        "password",
        "token",
        "secret",
        "api_key",
        "apikey",
        "authorization",
        "credential",
        "private_key",
        "access_token",
    ]
)

SECRET_VALUE_PATTERNS = [
    re.compile(r"sk[-_]?[a-zA-Z0-9]{20,}"),  # API keys
    re.compile(r"Bearer\s+[a-zA-Z0-9._-]+"),  # Bearer tokens
    re.compile(r"(?:password|passwd|pwd)\s*[:=]\s*\S+"),  # password assignments
]

MAX_QUERY_SIZE = 1024  # 1 KB for queries
MAX_RETRIEVAL_LIMIT = 20
MAX_CONTEXT_SIZE = 10240  # 10 KB per retrieved entry


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class MemoryEntry:
    """Claude-Mem memory entry."""

    id: str
    content: str
    tags: list[str]
    metadata: dict[str, Any]
    created_at: datetime
    provenance: dict[str, Any]


# ---------------------------------------------------------------------------
# Claude-Mem Adapter
# ---------------------------------------------------------------------------


class ClaudeMemAdapter(BaseExecutionAdapter):
    """
    Claude-Mem MCP adapter implementing BaseExecutionAdapter.

    Connects to Claude-Mem MCP server via MCPManager (stdio transport),
    provides contextual memory retrieval operations.

    All retrieved data is marked advisory per C14:
    - source=claude_mem
    - advisory=True
    - authority=contextual
    - trust_level=untrusted (remote service, memory entries could contain injected content)
    """

    perspective = "claude_mem_context"

    def __init__(
        self,
        mcp_manager: Any | None = None,
        server_id: str = "claude_mem",
        timeout_seconds: int = 30,
    ) -> None:
        """
        Initialize Claude-Mem adapter.

        Args:
            mcp_manager: MCPManager instance (deferred import).
                         If None, adapter operates in test/disconnected mode.
            server_id: MCP server identifier for Claude-Mem (default: "claude_mem").
            timeout_seconds: Default timeout for Claude-Mem operations.
        """
        super().__init__(tool=None)
        self._mcp_manager = mcp_manager
        self._server_id = server_id
        self._timeout_seconds = timeout_seconds
        self._connected = False
        self._version_counter = 0
        self._tools_discovered = False

    # -----------------------------------------------------------------------
    # BaseExecutionAdapter implementation
    # -----------------------------------------------------------------------

    def _default_tool(
        self, target: str, context: dict[str, Any]
    ) -> ExecutionResult:
        """Production execution path - raises if not connected (requires MCP)."""
        if not self._connected:
            raise NotImplementedError(
                f"{type(self).__name__} requires MCP connection; "
                "inject a test tool or call connect() first"
            )
        # Default tool is a pass-through to retrieve_context
        return asyncio.run(self.retrieve_context(target))

    def execute(
        self, target: str, context: dict[str, Any] | None = None
    ) -> ExecutionResult:
        """Execute Claude-Mem operation based on context action."""
        context = context or {}
        action = context.get("action", "retrieve_context")

        if action == "retrieve_context":
            return asyncio.run(
                self.retrieve_context(
                    target,
                    context.get("limit", 10),
                    context.get("tags"),
                )
            )
        elif action == "retrieve_recent":
            return asyncio.run(
                self.retrieve_recent(
                    context.get("hours", 24),
                    context.get("limit", 20),
                )
            )
        elif action == "retrieve_by_tag":
            return asyncio.run(
                self.retrieve_by_tag(
                    target,
                    context.get("limit", 10),
                )
            )
        else:
            return self._default_tool(target, context)

    # -----------------------------------------------------------------------
    # Connection Management
    # -----------------------------------------------------------------------

    async def connect(self) -> bool:
        """Connect to Claude-Mem MCP server via MCPManager."""
        if self._connected:
            return True

        if self._mcp_manager is None:
            logger.warning("ClaudeMemAdapter: No MCPManager provided; cannot connect")
            return False

        try:
            result = await self._mcp_manager.connect(self._server_id)
            if result:
                self._connected = True
                await self._discover_tools()
                logger.info(f"ClaudeMemAdapter connected to '{self._server_id}'")
            return result
        except Exception as e:
            logger.warning(f"Failed to connect to Claude-Mem server: {e}")
            raise ClaudeMemUnavailableError(f"Failed to connect: {e}") from e

    async def _discover_tools(self) -> None:
        """Discover available Claude-Mem tools via tools/list."""
        if self._tools_discovered:
            return

        try:
            tools_result = await asyncio.wait_for(
                self._mcp_manager.call_tool(self._server_id, "tools/list", {}),
                timeout=self._timeout_seconds,
            )
            if tools_result.get("success"):
                tools = tools_result.get("result", {})
                logger.debug(f"Claude-Mem tools discovered: {list(tools.keys())}")
                self._tools_discovered = True
            else:
                logger.warning("Claude-Mem tools discovery returned no result")
        except Exception as e:
            logger.warning(f"Failed to discover Claude-Mem tools: {e}")

    async def disconnect(self) -> None:
        """Disconnect from Claude-Mem MCP server."""
        if self._mcp_manager:
            try:
                await self._mcp_manager.disconnect(self._server_id)
            except Exception as e:
                logger.warning(f"Error disconnecting Claude-Mem: {e}")
        self._connected = False
        self._tools_discovered = False
        logger.debug("ClaudeMemAdapter disconnected")

    def is_connected(self) -> bool:
        """Check if adapter is connected to Claude-Mem."""
        return self._connected

    async def cleanup(self) -> None:
        """Clean up resources (alias for disconnect)."""
        await self.disconnect()

    # -----------------------------------------------------------------------
    # Version Counter
    # -----------------------------------------------------------------------

    def _next_version(self) -> int:
        """Generate monotonically increasing version counter."""
        self._version_counter += 1
        return self._version_counter

    # -----------------------------------------------------------------------
    # Provenance Tracking
    # -----------------------------------------------------------------------

    def _make_provenance(
        self,
        operation: str,
        execution_id: str | None = None,
        task_id: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Create provenance metadata for a Claude-Mem operation."""
        return {
            "source": "claude_mem",
            "adapter": "claude_mem_adapter",
            "operation": operation,
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "execution_id": execution_id,
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": str(uuid.uuid4()),
            "version": self._next_version(),
            "authority": "contextual",
            "advisory": True,
            "trust_level": "untrusted",
        }

    def _mark_advisory(
        self, metadata: dict[str, Any], operation: str | None = None
    ) -> dict[str, Any]:
        """Mark metadata as advisory/contextual per C14 with full provenance."""
        marked = dict(metadata)
        # Start from a full provenance base so externally-sourced results carry
        # the complete required field set, not just the C14 markers.
        provenance = self._make_provenance(operation or "external_read")
        # Existing caller-supplied provenance takes precedence over defaults.
        provenance.update(marked.get("provenance", {}))
        # Re-apply C14 constants so they cannot be overridden by external data.
        provenance.update(
            {
                "source": "claude_mem",
                "advisory": True,
                "authority": "contextual",
                "trust_level": "untrusted",
                "claude_mem_timestamp": datetime.utcnow().isoformat(),
            }
        )
        marked["provenance"] = provenance
        return marked

    def _error_result(self, operation: str, description: str) -> ExecutionResult:
        """Build a graceful ERROR ExecutionResult for failed operations."""
        return ExecutionResult(
            tool="claude_mem_adapter",
            status=ExecutionStatus.ERROR,
            findings=[
                {
                    "type": "claude_mem_error",
                    "severity": "error",
                    "description": description,
                    "provenance": self._make_provenance(operation),
                }
            ],
            metrics={"operation": operation},
            raw={},
        )

    # -----------------------------------------------------------------------
    # Security Validation
    # -----------------------------------------------------------------------

    def _validate_query(self, query: str) -> None:
        """Validate query string for size and injection patterns."""
        if len(query.encode("utf-8")) > MAX_QUERY_SIZE:
            raise ClaudeMemValidationError(
                f"Query exceeds max size ({MAX_QUERY_SIZE} bytes)"
            )

        # Check for potential prompt injection patterns
        injection_patterns = [
            r"ignore\s+(?:previous|above|all)\s+(?:instructions|prompts?)",
            r"system\s*:\s*",
            r"assistant\s*:\s*",
            r"<\|.*?\|>",
            r"```\s*(?:python|javascript|bash|shell)\s*\n",
        ]
        for pattern in injection_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                logger.warning(f"Potential prompt injection detected in query: {query[:100]}")
                # Don't reject - just log; content filtering happens on retrieval

    def _validate_content(self, content: str) -> None:
        """Validate retrieved content size."""
        if len(content.encode("utf-8")) > MAX_CONTEXT_SIZE:
            raise ClaudeMemValidationError(
                f"Content exceeds max size ({MAX_CONTEXT_SIZE} bytes)"
            )

    # -----------------------------------------------------------------------
    # MCP Tool Call Wrapper
    # -----------------------------------------------------------------------

    async def _call_tool(
        self, tool_name: str, arguments: dict[str, Any], operation: str
    ) -> dict[str, Any]:
        """Call a Claude-Mem MCP tool with error handling."""
        if not self._connected:
            raise ClaudeMemUnavailableError("Not connected to Claude-Mem server")

        try:
            result = await asyncio.wait_for(
                self._mcp_manager.call_tool(
                    self._server_id, tool_name, arguments
                ),
                timeout=self._timeout_seconds,
            )
        except asyncio.TimeoutError:
            raise ClaudeMemTimeoutError(
                f"Claude-Mem tool '{tool_name}' timed out after {self._timeout_seconds}s"
            ) from None
        except Exception as e:
            raise ClaudeMemTimeoutError(f"Claude-Mem tool '{tool_name}' failed: {e}") from e

        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            if "not found" in error_msg.lower():
                return {"success": False, "not_found": True, "error": error_msg}
            raise MalformedClaudeMemResponseError(
                f"Claude-Mem tool '{tool_name}' returned error: {error_msg}"
            )

        return result.get("result", {})

    # -----------------------------------------------------------------------
    # Memory Retrieval Operations
    # -----------------------------------------------------------------------

    async def retrieve_context(
        self, query: str, limit: int = 10, tags: list[str] | None = None
    ) -> ExecutionResult:
        """Retrieve contextual memories matching a query."""
        self._validate_query(query)
        limit = min(limit, MAX_RETRIEVAL_LIMIT)

        try:
            result = await self._call_tool(
                "retrieve_context",
                {"query": query, "limit": limit, "tags": tags or []},
                "retrieve_context",
            )
        except ClaudeMemTimeoutError as e:
            return self._error_result("retrieve_context", f"Claude-Mem retrieval timed out: {e}")
        except ClaudeMemValidationError:
            raise
        except ClaudeMemError as e:
            return self._error_result("retrieve_context", f"Claude-Mem retrieval failed: {e}")

        memories = result.get("memories", [])
        marked_memories = []

        for mem in memories:
            # Validate and sanitize content
            if "content" in mem:
                try:
                    self._validate_content(mem["content"])
                except ClaudeMemValidationError as e:
                    logger.warning(f"Dropping oversized memory entry: {e}")
                    continue
            marked_mem = self._mark_advisory(mem, operation="retrieve_context")
            marked_memories.append(marked_mem)

        return ExecutionResult(
            tool="claude_mem_adapter",
            status=ExecutionStatus.SUCCESS,
            findings=[],
            metrics={
                "query": query,
                "limit": limit,
                "memories_returned": len(marked_memories),
            },
            raw={"memories": marked_memories},
        )

    async def retrieve_recent(
        self, hours: int = 24, limit: int = 20
    ) -> ExecutionResult:
        """Retrieve recent memories within a time window."""
        limit = min(limit, MAX_RETRIEVAL_LIMIT)

        try:
            result = await self._call_tool(
                "retrieve_recent",
                {"hours": hours, "limit": limit},
                "retrieve_recent",
            )
        except ClaudeMemTimeoutError as e:
            return self._error_result("retrieve_recent", f"Claude-Mem retrieval timed out: {e}")
        except ClaudeMemError as e:
            return self._error_result("retrieve_recent", f"Claude-Mem retrieval failed: {e}")

        memories = result.get("memories", [])
        marked_memories = []

        for mem in memories:
            if "content" in mem:
                try:
                    self._validate_content(mem["content"])
                except ClaudeMemValidationError as e:
                    logger.warning(f"Dropping oversized memory entry: {e}")
                    continue
            marked_mem = self._mark_advisory(mem, operation="retrieve_recent")
            marked_memories.append(marked_mem)

        return ExecutionResult(
            tool="claude_mem_adapter",
            status=ExecutionStatus.SUCCESS,
            findings=[],
            metrics={
                "hours": hours,
                "limit": limit,
                "memories_returned": len(marked_memories),
            },
            raw={"memories": marked_memories},
        )

    async def retrieve_by_tag(
        self, tag: str, limit: int = 10
    ) -> ExecutionResult:
        """Retrieve memories by tag."""
        limit = min(limit, MAX_RETRIEVAL_LIMIT)

        try:
            result = await self._call_tool(
                "retrieve_by_tag",
                {"tag": tag, "limit": limit},
                "retrieve_by_tag",
            )
        except ClaudeMemTimeoutError as e:
            return self._error_result("retrieve_by_tag", f"Claude-Mem retrieval timed out: {e}")
        except ClaudeMemError as e:
            return self._error_result("retrieve_by_tag", f"Claude-Mem retrieval failed: {e}")

        memories = result.get("memories", [])
        marked_memories = []

        for mem in memories:
            if "content" in mem:
                try:
                    self._validate_content(mem["content"])
                except ClaudeMemValidationError as e:
                    logger.warning(f"Dropping oversized memory entry: {e}")
                    continue
            marked_mem = self._mark_advisory(mem, operation="retrieve_by_tag")
            marked_memories.append(marked_mem)

        return ExecutionResult(
            tool="claude_mem_adapter",
            status=ExecutionStatus.SUCCESS,
            findings=[],
            metrics={
                "tag": tag,
                "limit": limit,
                "memories_returned": len(marked_memories),
            },
            raw={"memories": marked_memories},
        )