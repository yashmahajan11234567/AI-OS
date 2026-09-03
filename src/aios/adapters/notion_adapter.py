"""
M8-T4 — Notion Planning / Project Tracking Adapter.

Implements BaseExecutionAdapter for the Notion MCP server.
Provides page/database operations: search, get, create, update, query.
All results marked advisory per C14 - Notion is UNTRUSTED contextual data.
"""

from __future__ import annotations

import asyncio
import hashlib
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
# Tool Mapping
# ---------------------------------------------------------------------------

# Maps AI-OS operation names to possible tool names (ordered by preference)
# First choice: official Notion MCP server tool names
# Second choice: legacy mock server tool names (for backward compatibility)
_TOOL_MAPPING = {
    "search_pages": ["notion-search", "search_pages"],
    "get_page": ["notion-fetch", "get_page"],
    "create_page": ["notion-create-pages", "create_page"],
    "update_page": ["notion-update-page", "update_page"],
    "query_database": ["notion-query-data-sources", "query_database"],
}

# Dynamic mapping of AI-OS operations to actual tool names provided by the connected server
# Populated during tool discovery in _discover_tools()
_actual_tool_mapping: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Error Hierarchy
# ---------------------------------------------------------------------------


class NotionError(Exception):
    """Base error for Notion adapter."""

    pass


class NotionUnavailableError(NotionError):
    """Notion MCP server not reachable."""

    pass


class NotionTimeoutError(NotionError):
    """Operation exceeded timeout."""

    pass


class NotionValidationError(NotionError):
    """Invalid input for Notion operation."""

    pass


class NotionSecurityError(NotionError):
    """Security violation (sensitive data attempt)."""

    pass


class MalformedNotionResponseError(NotionError):
    """Malformed response from Notion MCP."""

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

MAX_CONTENT_SIZE = 10240  # 10 KB
MAX_QUERY_LENGTH = 1000
MAX_SEARCH_RESULTS = 100


# ---------------------------------------------------------------------------
# Notion Adapter
# ---------------------------------------------------------------------------


class NotionAdapter(BaseExecutionAdapter):
    """
    Notion MCP adapter implementing BaseExecutionAdapter.

    Connects to Notion MCP server via MCPManager (stdio transport),
    provides page/database CRUD and search operations for planning.

    All retrieved data is marked advisory per C14:
    - source=notion
    - advisory=True
    - authority=contextual
    - trust_level=untrusted
    """

    perspective = "notion_planning"

    def __init__(
        self,
        mcp_manager: Any | None = None,
        server_id: str = "notion",
        timeout_seconds: int = 30,
    ) -> None:
        """
        Initialize Notion adapter.

        Args:
            mcp_manager: MCPManager instance (deferred import, not at module scope).
                         If None, adapter operates in test/disconnected mode.
            server_id: MCP server identifier for Notion (default: "notion").
            timeout_seconds: Default timeout for Notion operations.
        """
        super().__init__(tool=None)  # No injected tool; uses _default_tool
        self._mcp_manager = mcp_manager
        self._server_id = server_id
        self._timeout_seconds = timeout_seconds
        self._connected = False
        self._version_counter = 0
        self._tools_discovered = False
        # Mapping of AI-OS operations to actual tool names provided by server
        self._actual_tool_mapping: dict[str, str] = {}

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
        # Default tool is a pass-through to search_pages
        return asyncio.run(self.search_pages(target))

    def execute(
        self, target: str, context: dict[str, Any] | None = None
    ) -> ExecutionResult:
        """Execute Notion operation based on context action."""
        context = context or {}
        action = context.get("action", "search_pages")

        if action == "search_pages":
            return asyncio.run(
                self.search_pages(
                    target,
                    context.get("parent"),
                    context.get("limit", 50),
                )
            )
        elif action == "get_page":
            return asyncio.run(self.get_page(target))
        elif action == "create_page":
            return asyncio.run(
                self.create_page(
                    context.get("title", ""),
                    context.get("parent_id", ""),
                    context.get("content", {}),
                    context.get("properties", {}),
                )
            )
        elif action == "update_page":
            return asyncio.run(
                self.update_page(
                    target,
                    context.get("content", {}),
                    context.get("properties", {}),
                )
            )
        elif action == "query_database":
            return asyncio.run(
                self.query_database(
                    target,
                    context.get("filter"),
                    context.get("sorts"),
                    context.get("limit", 50),
                )
            )
        else:
            # Fallback to default
            return self._default_tool(target, context)

    # -----------------------------------------------------------------------
    # Connection Management
    # -----------------------------------------------------------------------

    async def connect(self) -> bool:
        """Connect to Notion MCP server via MCPManager."""
        if self._connected:
            return True

        if self._mcp_manager is None:
            logger.warning("NotionAdapter: No MCPManager provided; cannot connect")
            return False

        try:
            result = await self._mcp_manager.connect(self._server_id)
            if result:
                self._connected = True
                # Discover tools
                await self._discover_tools()
                logger.info(f"NotionAdapter connected to '{self._server_id}'")
            return result
        except Exception as e:
            logger.warning(f"Failed to connect to Notion server: {e}")
            raise NotionUnavailableError(f"Failed to connect: {e}") from e

    async def _discover_tools(self) -> None:
        """Discover available Notion tools via tools/list and map to AI-OS operations."""
        if self._tools_discovered:
            return

        try:
            tools_result = await asyncio.wait_for(
                self._mcp_manager.call_tool(self._server_id, "tools/list", {}),
                timeout=self._timeout_seconds,
            )
            if tools_result.get("success"):
                tools_dict = tools_result.get("result", {})
                # Extract the list of tools from the result
                tools_list = tools_dict.get("tools", []) if isinstance(tools_dict, dict) else []
                logger.debug(f"Notion tools discovered: {[t.get('name') for t in tools_list if isinstance(t, dict)]}")

                # Build mapping from AI-OS operations to actual tool names
                self._actual_tool_mapping = {}
                for ai_os_operation, possible_names in _TOOL_MAPPING.items():
                    # Find the first possible name that the server actually provides
                    for possible_name in possible_names:
                        if any(t.get("name") == possible_name for t in tools_list if isinstance(t, dict)):
                            self._actual_tool_mapping[ai_os_operation] = possible_name
                            break
                    # If no match found, use the first possible name as fallback
                    if ai_os_operation not in self._actual_tool_mapping:
                        self._actual_tool_mapping[ai_os_operation] = possible_names[0]

                self._tools_discovered = True
                logger.debug(f"Tool mapping: {self._actual_tool_mapping}")
            else:
                logger.warning("Notion tools discovery returned no result")
        except Exception as e:
            logger.warning(f"Failed to discover Notion tools: {e}")
            # Fallback to default mapping if discovery fails
            for ai_os_operation, possible_names in _TOOL_MAPPING.items():
                self._actual_tool_mapping[ai_os_operation] = possible_names[0]

    async def disconnect(self) -> None:
        """Disconnect from Notion MCP server."""
        if self._mcp_manager:
            try:
                await self._mcp_manager.disconnect(self._server_id)
            except Exception as e:
                logger.warning(f"Error disconnecting Notion: {e}")
        self._connected = False
        self._tools_discovered = False
        logger.debug("NotionAdapter disconnected")

    def is_connected(self) -> bool:
        """Check if adapter is connected to Notion."""
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
        """Create provenance metadata for a Notion operation."""
        return {
            "source": "notion",
            "adapter": "notion_adapter",
            "operation": operation,
            # M9-N8 / D-04: ambient orchestrator correlation propagates via
            # the canonical C4 CorrelationContext (see GraphifyAdapter).
            "correlation_id": (
                self._resolve_correlation_id(correlation_id)
                or str(uuid.uuid4())
            ),
            "execution_id": execution_id,
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": str(uuid.uuid4()),
            "version": self._next_version(),
            "authority": "contextual",
            "advisory": True,
            "trust_level": "untrusted",
        }

    @staticmethod
    def _resolve_correlation_id(explicit: str | None) -> str | None:
        """Explicit id wins; else read the ambient C4 CorrelationContext."""
        if explicit:
            return explicit
        try:
            from aios.core.structured_logger import get_correlation_context

            ctx = get_correlation_context()
            if ctx is not None and ctx.correlation_id:
                return str(ctx.correlation_id)
        except Exception:  # noqa: BLE001 — provenance must never fail on lookup
            pass
        return None

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
                "source": "notion",
                "advisory": True,
                "authority": "contextual",
                "trust_level": "untrusted",
                "notion_timestamp": datetime.utcnow().isoformat(),
            }
        )
        marked["provenance"] = provenance
        return marked

    def _error_result(
        self, operation: str, description: str
    ) -> ExecutionResult:
        """Build a graceful ERROR ExecutionResult for failed operations."""
        return ExecutionResult(
            tool="notion_adapter",
            status=ExecutionStatus.ERROR,
            findings=[
                {
                    "type": "notion_error",
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

    def _validate_content(self, content: dict[str, Any]) -> None:
        """Validate content for size and sensitive data."""
        # Check property keys
        for key in content:
            key_lower = key.lower()
            if key_lower in SENSITIVE_PROPERTY_KEYS:
                raise NotionSecurityError(
                    f"Sensitive property key rejected: '{key}'"
                )

        # Check value sizes and secret patterns
        str_content = json.dumps(content)
        if len(str_content.encode("utf-8")) > MAX_CONTENT_SIZE:
            raise NotionValidationError(
                f"Content exceeds max size ({MAX_CONTENT_SIZE} bytes)"
            )

        for pattern in SECRET_VALUE_PATTERNS:
            if pattern.search(str_content):
                raise NotionSecurityError(
                    f"Potential secret detected in content"
                )

    def _validate_query(self, query: str) -> None:
        """Validate query string."""
        if len(query) > MAX_QUERY_LENGTH:
            raise NotionValidationError(
                f"Query exceeds max length ({MAX_QUERY_LENGTH} chars)"
            )

    # -----------------------------------------------------------------------
    # MCP Tool Call Wrapper
    # -----------------------------------------------------------------------

    async def _call_tool(
        self, tool_name: str, arguments: dict[str, Any], operation: str
    ) -> dict[str, Any]:
        """Call a Notion MCP tool with error handling."""
        if not self._connected:
            raise NotionUnavailableError("Not connected to Notion server")

        try:
            result = await asyncio.wait_for(
                self._mcp_manager.call_tool(
                    self._server_id, tool_name, arguments
                ),
                timeout=self._timeout_seconds,
            )
        except asyncio.TimeoutError:
            raise NotionTimeoutError(
                f"Notion tool '{tool_name}' timed out after {self._timeout_seconds}s"
            ) from None
        except Exception as e:
            raise NotionTimeoutError(f"Notion tool '{tool_name}' failed: {e}") from e

        # Handle both mock server format and official server format
        # Mock server format: {"success": True, "result": actual_result}
        # Official server format: actual_result (with provenance added by MCPManager)
        if isinstance(result, dict) and result.get("success") is False:
            # Explicit failure from mock server
            error_msg = result.get("error", "Unknown error")
            if "not found" in error_msg.lower():
                return {"success": False, "not_found": True, "error": error_msg}
            raise MalformedNotionResponseError(
                f"Notion tool '{tool_name}' returned error: {error_msg}"
            )
        elif isinstance(result, dict) and result.get("success") is True:
            # Success from mock server - extract the actual result
            return result.get("result", {})
        else:
            # Missing or invalid success flag - treat as malformed response
            # This covers both official server format (which should have success added by MCPManager)
            # and truly malformed responses
            if isinstance(result, dict) and "success" not in result:
                # Explicitly malformed response - no success indicator at all
                raise MalformedNotionResponseError(
                    f"Notion tool '{tool_name}' returned malformed response (missing success indicator)"
                )
            # Official server format or other valid response - return as-is
            # (provenance already added by MCPManager)
            return result

    # -----------------------------------------------------------------------
    # Page Operations
    # -----------------------------------------------------------------------

    async def search_pages(
        self, query: str, parent: str | None = None, limit: int = 50
    ) -> ExecutionResult:
        """Search Notion pages by query."""
        self._validate_query(query)
        limit = min(limit, MAX_SEARCH_RESULTS)

        tool_name = self._actual_tool_mapping.get("search_pages", "search_pages")
        try:
            result = await self._call_tool(
                tool_name,
                {"query": query, "parent": parent, "limit": limit},
                "search_pages",
            )
        except NotionTimeoutError as e:
            return self._error_result("search_pages", f"Notion search timed out: {e}")
        except NotionError as e:
            return self._error_result("search_pages", f"Notion search failed: {e}")

        pages = result.get("pages", [])
        marked_pages = [
            self._mark_advisory(page, operation="search_pages") for page in pages
        ]

        return ExecutionResult(
            tool="notion_adapter",
            status=ExecutionStatus.SUCCESS,
            findings=[],
            metrics={"query": query, "pages_returned": len(marked_pages)},
            raw={"pages": marked_pages},
        )

    async def get_page(self, page_id: str) -> ExecutionResult:
        """Retrieve a Notion page by ID."""
        tool_name = self._actual_tool_mapping.get("get_page", "get_page")
        try:
            result = await self._call_tool(
                tool_name, {"page_id": page_id}, "get_page"
            )
        except NotionTimeoutError as e:
            return self._error_result("get_page", f"Notion get_page timed out: {e}")
        except NotionError as e:
            return self._error_result("get_page", f"Notion get_page failed: {e}")

        if isinstance(result, dict) and result.get("not_found"):
            return ExecutionResult(
                tool="notion_adapter",
                status=ExecutionStatus.SUCCESS,
                findings=[],
                metrics={"page_id": page_id, "found": False},
                raw={},
            )

        if not result:
            return ExecutionResult(
                tool="notion_adapter",
                status=ExecutionStatus.SUCCESS,
                findings=[],
                metrics={"page_id": page_id, "found": False},
                raw={},
            )

        # Mark as advisory per C14
        marked_result = self._mark_advisory(result, operation="get_page")
        return ExecutionResult(
            tool="notion_adapter",
            status=ExecutionStatus.SUCCESS,
            findings=[],
            metrics={"page_id": page_id, "found": True},
            raw=marked_result,
        )

    async def create_page(
        self,
        title: str,
        parent_id: str,
        content: dict[str, Any] | None = None,
        properties: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Create a new Notion page."""
        provenance = self._make_provenance("create_page")
        content = content or {}
        properties = properties or {}

        # Validate content and properties
        self._validate_content(content)
        self._validate_content(properties)

        tool_name = self._actual_tool_mapping.get("create_page", "create_page")
        try:
            result = await self._call_tool(
                tool_name,
                {
                    "title": title,
                    "parent_id": parent_id,
                    "content": content,
                    "properties": properties,
                },
                "create_page",
            )
        except NotionTimeoutError as e:
            return self._error_result("create_page", f"Notion create_page timed out: {e}")
        except NotionError as e:
            return self._error_result("create_page", f"Notion create_page failed: {e}")

        success = result.get("created", False)
        page_id = result.get("page_id", "")

        # Mark the externally-sourced result as advisory per C14
        marked_result = self._mark_advisory(result, operation="create_page")

        return ExecutionResult(
            tool="notion_adapter",
            status=ExecutionStatus.SUCCESS if success else ExecutionStatus.FAILURE,
            findings=(
                []
                if success
                else [
                    {
                        "type": "create_failed",
                        "severity": "error",
                        "description": f"Failed to create page '{title}'",
                        "provenance": marked_result["provenance"],
                    }
                ]
            ),
            metrics={"title": title, "parent_id": parent_id, "page_id": page_id},
            raw=marked_result,
        )

    async def update_page(
        self,
        page_id: str,
        content: dict[str, Any] | None = None,
        properties: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Update an existing Notion page."""
        provenance = self._make_provenance("update_page")
        content = content or {}
        properties = properties or {}

        # Validate content and properties
        self._validate_content(content)
        self._validate_content(properties)

        tool_name = self._actual_tool_mapping.get("update_page", "update_page")
        try:
            result = await self._call_tool(
                tool_name,
                {"page_id": page_id, "content": content, "properties": properties},
                "update_page",
            )
        except NotionTimeoutError as e:
            return self._error_result("update_page", f"Notion update_page timed out: {e}")
        except NotionError as e:
            return self._error_result("update_page", f"Notion update_page failed: {e}")

        success = result.get("updated", False)

        # Mark the externally-sourced result as advisory per C14
        marked_result = self._mark_advisory(result, operation="update_page")

        return ExecutionResult(
            tool="notion_adapter",
            status=ExecutionStatus.SUCCESS if success else ExecutionStatus.FAILURE,
            findings=(
                []
                if success
                else [
                    {
                        "type": "update_failed",
                        "severity": "error",
                        "description": f"Failed to update page {page_id}",
                        "provenance": marked_result["provenance"],
                    }
                ]
            ),
            metrics={"page_id": page_id},
            raw=marked_result,
        )

    async def query_database(
        self,
        database_id: str,
        filter_obj: dict[str, Any] | None = None,
        sorts: list[dict[str, Any]] | None = None,
        limit: int = 50,
    ) -> ExecutionResult:
        """Query a Notion database."""
        limit = min(limit, MAX_SEARCH_RESULTS)
        provenance = self._make_provenance("query_database")

        if filter_obj:
            self._validate_content(filter_obj)

        tool_name = self._actual_tool_mapping.get("query_database", "query_database")
        try:
            result = await self._call_tool(
                tool_name,
                {
                    "database_id": database_id,
                    "filter": filter_obj,
                    "sorts": sorts,
                    "limit": limit,
                },
                "query_database",
            )
        except NotionTimeoutError as e:
            return self._error_result(
                "query_database", f"Notion database query timed out: {e}"
            )
        except NotionError as e:
            return self._error_result(
                "query_database", f"Notion database query failed: {e}"
            )

        pages = result.get("results", [])
        marked_pages = [
            self._mark_advisory(page, operation="query_database") for page in pages
        ]

        return ExecutionResult(
            tool="notion_adapter",
            status=ExecutionStatus.SUCCESS,
            findings=[],
            metrics={
                "database_id": database_id,
                "pages_returned": len(marked_pages),
            },
            raw={"pages": marked_pages, "has_more": result.get("has_more", False)},
        )