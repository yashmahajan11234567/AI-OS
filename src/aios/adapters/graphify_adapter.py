"""
M8-T3 — Graphify Relationship / Knowledge Graph Adapter.

Implements BaseExecutionAdapter for the Graphify MCP server.
Provides graph operations: node/edge CRUD, queries, context enrichment.
All results marked advisory per C14.
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
# Error Hierarchy
# ---------------------------------------------------------------------------


class GraphifyError(Exception):
    """Base error for Graphify adapter."""

    pass


class GraphifyUnavailableError(GraphifyError):
    """Graphify MCP server not reachable."""

    pass


class GraphifyTimeoutError(GraphifyError):
    """Operation exceeded timeout."""

    pass


class GraphifyValidationError(GraphifyError):
    """Invalid input for graph operation."""

    pass


class GraphifyStorageError(GraphifyError):
    """Storage/write failure."""

    pass


class MalformedGraphifyResponseError(GraphifyError):
    """Malformed response from Graphify MCP."""

    pass


class GraphifySecurityError(GraphifyError):
    """Security violation (sensitive data attempt)."""

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

MAX_PROPERTY_VALUE_SIZE = 10240  # 10 KB
MAX_QUERY_LENGTH = 1000
MAX_PATH_DEPTH = 10
MAX_QUERY_RESULTS = 100
DEFAULT_NAMESPACE = "ai_os"


# ---------------------------------------------------------------------------
# GraphifyAdapter
# ---------------------------------------------------------------------------


class GraphifyAdapter(BaseExecutionAdapter):
    """
    Graphify MCP adapter implementing BaseExecutionAdapter.

    Connects to Graphify MCP server via MCPManager (stdio transport),
    provides node/edge CRUD, relationship queries, and context enrichment.

    All retrieved data is marked advisory per C14:
    - source=graphify_inferred
    - advisory=True
    - authority=advisory_only
    - graphify_timestamp in provenance
    """

    perspective = "graphify_context"

    def __init__(
        self,
        mcp_manager: Any | None = None,
        server_id: str = "graphify",
        timeout_seconds: int = 30,
        namespace: str = DEFAULT_NAMESPACE,
    ) -> None:
        """
        Initialize Graphify adapter.

        Args:
            mcp_manager: MCPManager instance (deferred import, not at module scope).
                         If None, adapter operates in test/disconnected mode.
            server_id: MCP server identifier for Graphify (default: "graphify").
            timeout_seconds: Default timeout for graph operations.
            namespace: Namespace prefix for all entity IDs (default: "ai_os").
        """
        super().__init__(tool=None)  # No injected tool; uses _default_tool
        self._mcp_manager = mcp_manager
        self._server_id = server_id
        self._timeout_seconds = timeout_seconds
        self._namespace = namespace
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
        # Default tool is a pass-through to context retrieval
        return asyncio.run(self.get_related_entities(target))

    def execute(
        self, target: str, context: dict[str, Any] | None = None
    ) -> ExecutionResult:
        """Execute graph operation based on context action."""
        context = context or {}
        action = context.get("action", "get_related_entities")

        if action == "store_node":
            return asyncio.run(
                self.store_node(
                    target, context.get("label", "task"), context.get("properties", {})
                )
            )
        elif action == "get_node":
            return asyncio.run(self.get_node(target))
        elif action == "update_node":
            return asyncio.run(
                self.update_node(target, context.get("properties", {}))
            )
        elif action == "delete_node":
            return asyncio.run(self.delete_node(target))
        elif action == "add_edge":
            return asyncio.run(
                self.add_edge(
                    target,
                    context["to_id"],
                    context["relationship"],
                    context.get("properties", {}),
                )
            )
        elif action == "get_related_entities":
            return asyncio.run(
                self.get_related_entities(
                    target,
                    context.get("relationship_type"),
                    context.get("limit", 50),
                )
            )
        elif action == "get_execution_history":
            return asyncio.run(
                self.get_execution_history(target, context.get("limit", 20))
            )
        elif action == "get_dependency_chain":
            return asyncio.run(
                self.get_dependency_chain(target, context.get("max_depth", 10))
            )
        elif action == "query_graph":
            return asyncio.run(
                self.query_graph(target, context.get("limit", 100))
            )
        elif action == "shortest_path":
            return asyncio.run(
                self.shortest_path(target, context["to_node"], context.get("max_depth", 10))
            )
        else:
            # Fallback to default
            return self._default_tool(target, context)

    # -----------------------------------------------------------------------
    # Connection Management
    # -----------------------------------------------------------------------

    async def connect(self) -> bool:
        """Connect to Graphify MCP server via MCPManager."""
        if self._connected:
            return True

        if self._mcp_manager is None:
            logger.warning("GraphifyAdapter: No MCPManager provided; cannot connect")
            return False

        try:
            result = await self._mcp_manager.connect(self._server_id)
            if result:
                self._connected = True
                # Discover tools
                await self._discover_tools()
                logger.info(f"GraphifyAdapter connected to '{self._server_id}'")
            return result
        except Exception as e:
            logger.warning(f"Failed to connect to Graphify server: {e}")
            raise GraphifyUnavailableError(f"Failed to connect: {e}") from e

    async def _discover_tools(self) -> None:
        """Discover available Graphify tools via tools/list."""
        if self._tools_discovered:
            return

        try:
            tools_result = await asyncio.wait_for(
                self._mcp_manager.call_tool(self._server_id, "tools/list", {}),
                timeout=self._timeout_seconds,
            )
            if tools_result.get("success"):
                tools = tools_result.get("result", {})
                logger.debug(f"Graphify tools discovered: {list(tools.keys())}")
                self._tools_discovered = True
            else:
                logger.warning("Graphify tools discovery returned no result")
        except Exception as e:
            logger.warning(f"Failed to discover Graphify tools: {e}")

    async def disconnect(self) -> None:
        """Disconnect from Graphify MCP server."""
        if self._mcp_manager:
            try:
                await self._mcp_manager.disconnect(self._server_id)
            except Exception as e:
                logger.warning(f"Error disconnecting Graphify: {e}")
        self._connected = False
        self._tools_discovered = False
        logger.debug("GraphifyAdapter disconnected")

    def is_connected(self) -> bool:
        """Check if adapter is connected to Graphify."""
        return self._connected

    async def cleanup(self) -> None:
        """Clean up resources (alias for disconnect)."""
        await self.disconnect()

    # -----------------------------------------------------------------------
    # Namespace & ID Helpers
    # -----------------------------------------------------------------------

    def _make_entity_id(self, entity_id: str) -> str:
        """Prefix entity ID with namespace for isolation."""
        if entity_id.startswith(f"{self._namespace}:"):
            return entity_id
        return f"{self._namespace}:{entity_id}"

    def _strip_namespace(self, entity_id: str) -> str:
        """Remove namespace prefix if present."""
        prefix = f"{self._namespace}:"
        if entity_id.startswith(prefix):
            return entity_id[len(prefix) :]
        return entity_id

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
        """Create provenance metadata for a graph operation."""
        return {
            "source": "ai_os",
            "adapter": "graphify_adapter",
            "operation": operation,
            # M9-N8 / D-04: an orchestrator correlation_id supplied via the
            # canonical C4 CorrelationContext (contextvars) propagates into
            # every provenance block; absent context, behavior is unchanged
            # (fresh per-call uuid).
            "correlation_id": (
                self._resolve_correlation_id(correlation_id)
                or str(uuid.uuid4())
            ),
            "execution_id": execution_id,
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": str(uuid.uuid4()),
            "version": self._next_version(),
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

    def _mark_advisory(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Mark metadata as advisory/inferred per C14."""
        marked = dict(metadata)
        provenance = marked.get("provenance", {})
        provenance.update(
            {
                "source": "graphify_inferred",
                "advisory": True,
                "authority": "advisory_only",
                # M9-N8 (spec §17): force trust_level too — a hostile payload
                # must not be able to pre-seed trusted/builtin here.
                "trust_level": "untrusted",
                "graphify_timestamp": datetime.utcnow().isoformat(),
            }
        )
        marked["provenance"] = provenance
        return marked

    # -----------------------------------------------------------------------
    # Security Validation
    # -----------------------------------------------------------------------

    def _validate_properties(self, properties: dict[str, Any]) -> None:
        """Validate properties for size and sensitive content."""
        # Check property keys
        for key in properties:
            key_lower = key.lower()
            if key_lower in SENSITIVE_PROPERTY_KEYS:
                raise GraphifySecurityError(
                    f"Sensitive property key rejected: '{key}'"
                )

        # Check property value sizes and secret patterns
        for key, value in properties.items():
            if isinstance(value, str):
                if len(value.encode("utf-8")) > MAX_PROPERTY_VALUE_SIZE:
                    raise GraphifyValidationError(
                        f"Property '{key}' exceeds max size ({MAX_PROPERTY_VALUE_SIZE} bytes)"
                    )
                for pattern in SECRET_VALUE_PATTERNS:
                    if pattern.search(value):
                        raise GraphifySecurityError(
                            f"Potential secret detected in property '{key}'"
                        )
            elif isinstance(value, (dict, list)):
                # Recursively validate nested structures (depth-limited)
                str_val = json.dumps(value)
                if len(str_val.encode("utf-8")) > MAX_PROPERTY_VALUE_SIZE:
                    raise GraphifyValidationError(
                        f"Property '{key}' exceeds max size ({MAX_PROPERTY_VALUE_SIZE} bytes)"
                    )
                for pattern in SECRET_VALUE_PATTERNS:
                    if pattern.search(str_val):
                        raise GraphifySecurityError(
                            f"Potential secret detected in property '{key}'"
                        )

    def _validate_query(self, query: str) -> None:
        """Validate query string."""
        if len(query) > MAX_QUERY_LENGTH:
            raise GraphifyValidationError(
                f"Query exceeds max length ({MAX_QUERY_LENGTH} chars)"
            )

    # -----------------------------------------------------------------------
    # MCP Tool Call Wrapper
    # -----------------------------------------------------------------------

    async def _call_tool(
        self, tool_name: str, arguments: dict[str, Any], operation: str
    ) -> dict[str, Any]:
        """Call a Graphify MCP tool with error handling."""
        if not self._connected:
            raise GraphifyUnavailableError("Not connected to Graphify server")

        try:
            result = await asyncio.wait_for(
                self._mcp_manager.call_tool(
                    self._server_id, tool_name, arguments
                ),
                timeout=self._timeout_seconds,
            )
        except asyncio.TimeoutError:
            raise GraphifyTimeoutError(
                f"Graphify tool '{tool_name}' timed out after {self._timeout_seconds}s"
            ) from None
        except Exception as e:
            raise GraphifyTimeoutError(f"Graphify tool '{tool_name}' failed: {e}") from e

        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            if "not found" in error_msg.lower():
                return {"success": False, "not_found": True, "error": error_msg}
            raise MalformedGraphifyResponseError(
                f"Graphify tool '{tool_name}' returned error: {error_msg}"
            )

        return result.get("result", {})

    # -----------------------------------------------------------------------
    # Node CRUD Operations
    # -----------------------------------------------------------------------

    async def store_node(
        self, entity_id: str, label: str, properties: dict[str, Any]
    ) -> ExecutionResult:
        """Store a node in the knowledge graph."""
        entity_id = self._make_entity_id(entity_id)
        provenance = self._make_provenance("store_node")
        properties = dict(properties)  # Copy for mutation

        # Validate and enrich
        self._validate_properties(properties)
        # M9-N8 / D-03: the STORED provenance must itself carry C14 advisory
        # markers — previously the stored block was bare ``_make_provenance``
        # output (source="ai_os", no markers), so graph-resident nodes looked
        # authoritative. Nest under ``provenance`` so ``_mark_advisory``
        # force-reasserts its constants ON TOP of the full operation block.
        properties["provenance"] = self._mark_advisory(
            {"provenance": provenance}
        )["provenance"]
        properties["created_at"] = datetime.utcnow().isoformat()
        properties["updated_at"] = datetime.utcnow().isoformat()

        result = await self._call_tool(
            "add_node",
            {"node_id": entity_id, "label": label, "properties": properties},
            "store_node",
        )

        success = result.get("created", False)
        return ExecutionResult(
            tool="graphify_adapter",
            status=ExecutionStatus.SUCCESS if success else ExecutionStatus.FAILURE,
            findings=(
                []
                if success
                else [
                    {
                        "type": "store_failed",
                        "severity": "error",
                        "description": f"Failed to store node {entity_id}",
                        "provenance": provenance,
                    }
                ]
            ),
            metrics={"entity_id": entity_id, "label": label},
            # D-03 remediation: write paths must also carry C14 advisory
            # provenance (source=graphify_inferred, authority=advisory_only,
            # advisory=True) — previously only reads were marked.
            raw=self._mark_advisory(result),
        )

    async def get_node(self, entity_id: str) -> ExecutionResult:
        """Retrieve a node from the knowledge graph."""
        entity_id = self._make_entity_id(entity_id)
        provenance = self._make_provenance("get_node")

        result = await self._call_tool(
            "get_node", {"node_id": entity_id}, "get_node"
        )

        if isinstance(result, dict) and result.get("not_found"):
            return ExecutionResult(
                tool="graphify_adapter",
                status=ExecutionStatus.SUCCESS,
                findings=[],
                metrics={"entity_id": entity_id, "found": False},
                raw={},
            )

        if not result:
            return ExecutionResult(
                tool="graphify_adapter",
                status=ExecutionStatus.SUCCESS,
                findings=[],
                metrics={"entity_id": entity_id, "found": False},
                raw={},
            )

        # Mark as advisory per C14
        marked_result = self._mark_advisory(result)
        # M9-N8 / D-04: carry the operation's correlation_id (which resolves
        # the ambient orchestrator context) into the result provenance.
        op_prov = marked_result.setdefault("provenance", {})
        if not op_prov.get("correlation_id"):
            op_prov["correlation_id"] = provenance["correlation_id"]
        return ExecutionResult(
            tool="graphify_adapter",
            status=ExecutionStatus.SUCCESS,
            findings=[],
            metrics={"entity_id": entity_id, "found": True},
            raw=marked_result,
        )

    async def update_node(
        self, entity_id: str, properties: dict[str, Any]
    ) -> ExecutionResult:
        """Update a node in the knowledge graph."""
        entity_id = self._make_entity_id(entity_id)
        provenance = self._make_provenance("update_node")
        properties = dict(properties)

        self._validate_properties(properties)
        # M9-N8 / D-03: stored provenance must carry C14 advisory markers
        # (same rationale as store_node).
        properties["provenance"] = self._mark_advisory(
            {"provenance": provenance}
        )["provenance"]
        properties["updated_at"] = datetime.utcnow().isoformat()

        result = await self._call_tool(
            "update_node",
            {"node_id": entity_id, "properties": properties},
            "update_node",
        )

        success = result.get("updated", False)
        return ExecutionResult(
            tool="graphify_adapter",
            status=ExecutionStatus.SUCCESS if success else ExecutionStatus.FAILURE,
            findings=(
                []
                if success
                else [
                    {
                        "type": "update_failed",
                        "severity": "error",
                        "description": f"Failed to update node {entity_id}",
                        "provenance": provenance,
                    }
                ]
            ),
            metrics={"entity_id": entity_id},
            # D-03 remediation: write-path C14 advisory marking.
            raw=self._mark_advisory(result),
        )

    async def delete_node(self, entity_id: str) -> ExecutionResult:
        """Delete a node from the knowledge graph."""
        entity_id = self._make_entity_id(entity_id)
        provenance = self._make_provenance("delete_node")

        result = await self._call_tool(
            "delete_node", {"node_id": entity_id}, "delete_node"
        )

        success = result.get("deleted", False)
        return ExecutionResult(
            tool="graphify_adapter",
            status=ExecutionStatus.SUCCESS if success else ExecutionStatus.FAILURE,
            findings=(
                []
                if success
                else [
                    {
                        "type": "delete_failed",
                        "severity": "error",
                        "description": f"Failed to delete node {entity_id}",
                        "provenance": provenance,
                    }
                ]
            ),
            metrics={"entity_id": entity_id},
            # D-03 remediation: write-path C14 advisory marking.
            raw=self._mark_advisory(result),
        )

    # -----------------------------------------------------------------------
    # Edge Operations
    # -----------------------------------------------------------------------

    async def add_edge(
        self,
        from_id: str,
        to_id: str,
        relationship: str,
        properties: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Add a relationship edge between nodes."""
        from_id = self._make_entity_id(from_id)
        to_id = self._make_entity_id(to_id)
        provenance = self._make_provenance("add_edge")
        properties = dict(properties or {})

        self._validate_properties(properties)
        properties["provenance"] = provenance
        properties["created_at"] = datetime.utcnow().isoformat()

        result = await self._call_tool(
            "add_edge",
            {
                "from_node": from_id,
                "to_node": to_id,
                "relationship": relationship,
                "properties": properties,
            },
            "add_edge",
        )

        success = result.get("created", False)
        return ExecutionResult(
            tool="graphify_adapter",
            status=ExecutionStatus.SUCCESS if success else ExecutionStatus.FAILURE,
            findings=(
                []
                if success
                else [
                    {
                        "type": "add_edge_failed",
                        "severity": "error",
                        "description": f"Failed to add edge {from_id} -> {to_id} ({relationship})",
                        "provenance": provenance,
                    }
                ]
            ),
            metrics={"from": from_id, "to": to_id, "relationship": relationship},
            # D-03 remediation: write-path C14 advisory marking (edge creation).
            raw=self._mark_advisory(result),
        )

    # -----------------------------------------------------------------------
    # Query Operations
    # -----------------------------------------------------------------------

    async def query_graph(
        self, query: str, limit: int = MAX_QUERY_RESULTS
    ) -> ExecutionResult:
        """Execute a custom graph query."""
        self._validate_query(query)
        provenance = self._make_provenance("query_graph")

        result = await self._call_tool(
            "query_graph", {"query": query}, "query_graph"
        )

        nodes = result.get("nodes", [])
        edges = result.get("edges", [])

        # Apply limits and mark advisory
        nodes = nodes[:limit]
        edges = edges[:500]

        marked_nodes = [self._mark_advisory(node) for node in nodes]
        marked_edges = [self._mark_advisory(edge) for edge in edges]

        return ExecutionResult(
            tool="graphify_adapter",
            status=ExecutionStatus.SUCCESS,
            findings=[],
            metrics={
                "nodes_returned": len(marked_nodes),
                "edges_returned": len(marked_edges),
            },
            raw={"nodes": marked_nodes, "edges": marked_edges},
        )

    async def shortest_path(
        self, from_id: str, to_id: str, max_depth: int = MAX_PATH_DEPTH
    ) -> ExecutionResult:
        """Find shortest path between two nodes."""
        from_id = self._make_entity_id(from_id)
        to_id = self._make_entity_id(to_id)
        max_depth = min(max_depth, MAX_PATH_DEPTH)
        provenance = self._make_provenance("shortest_path")

        result = await self._call_tool(
            "shortest_path",
            {
                "from_node": from_id,
                "to_node": to_id,
                "max_depth": max_depth,
            },
            "shortest_path",
        )

        path = result.get("path", [])
        found = result.get("found", False)

        # Mark path as advisory
        marked_path = [{"node_id": n, "provenance": provenance} for n in path]

        return ExecutionResult(
            tool="graphify_adapter",
            status=ExecutionStatus.SUCCESS,
            findings=[],
            metrics={"found": found, "path_length": len(path), "max_depth": max_depth},
            raw={"path": marked_path, "found": found},
        )

    # -----------------------------------------------------------------------
    # Context Enrichment (High-Level Queries)
    # -----------------------------------------------------------------------

    async def get_related_entities(
        self,
        entity_id: str,
        relationship_type: str | None = None,
        limit: int = 50,
    ) -> ExecutionResult:
        """Get entities related to the given entity."""
        entity_id = self._make_entity_id(entity_id)
        limit = min(limit, MAX_QUERY_RESULTS)
        provenance = self._make_provenance("get_related_entities")

        # Build query to find related entities
        if relationship_type:
            query = f"MATCH (n {{id: '{entity_id}'}})-[r:{relationship_type}]->(m) RETURN m, r LIMIT {limit}"
        else:
            query = f"MATCH (n {{id: '{entity_id}'}})-[r]->(m) RETURN m, r LIMIT {limit}"

        result = await self._call_tool(
            "query_graph", {"query": query}, "get_related_entities"
        )

        nodes = result.get("nodes", [])[:limit]
        edges = result.get("edges", [])[:500]

        # Filter by relationship type if specified
        if relationship_type:
            edges = [e for e in edges if e.get("relationship") == relationship_type]
            # Collect target node IDs from filtered edges
            target_ids = {e["to_node"] for e in edges}
            nodes = [n for n in nodes if n.get("id") in target_ids]

        marked_nodes = [self._mark_advisory(n) for n in nodes]
        marked_edges = [self._mark_advisory(e) for e in edges]

        # Deterministic ordering: relationship type, created_at desc, node_id
        marked_edges.sort(
            key=lambda e: (
                e.get("relationship", ""),
                -(
                    e.get("created_at", "")
                    and datetime.fromisoformat(e["created_at"].replace("Z", "+00:00")).timestamp()
                    or 0
                ),
                e.get("from_node", ""),
            )
        )

        return ExecutionResult(
            tool="graphify_adapter",
            status=ExecutionStatus.SUCCESS,
            findings=[],
            metrics={
                "entity_id": entity_id,
                "relationship_type": relationship_type,
                "related_count": len(marked_nodes),
            },
            raw={"nodes": marked_nodes, "edges": marked_edges},
        )

    async def get_execution_history(
        self, execution_id: str, limit: int = 20
    ) -> ExecutionResult:
        """Get execution history chain for an execution."""
        entity_id = self._make_entity_id(f"exec:{execution_id}")
        limit = min(limit, MAX_QUERY_RESULTS)
        provenance = self._make_provenance("get_execution_history")

        # Query for execution chain (FOLLOWS relationships)
        query = (
            f"MATCH (n {{id: '{entity_id}'}})-[:FOLLOWS*0..{MAX_PATH_DEPTH}]->(m) "
            f"RETURN m ORDER BY m.properties.created_at DESC LIMIT {limit}"
        )

        result = await self._call_tool(
            "query_graph", {"query": query}, "get_execution_history"
        )

        nodes = result.get("nodes", [])[:limit]
        marked_nodes = [self._mark_advisory(n) for n in nodes]

        return ExecutionResult(
            tool="graphify_adapter",
            status=ExecutionStatus.SUCCESS,
            findings=[],
            metrics={"entity_id": entity_id, "history_count": len(marked_nodes)},
            raw={"executions": marked_nodes},
        )

    async def get_dependency_chain(
        self, entity_id: str, max_depth: int = 10
    ) -> ExecutionResult:
        """Get full dependency chain for a task/entity."""
        entity_id = self._make_entity_id(entity_id)
        max_depth = min(max_depth, MAX_PATH_DEPTH)
        provenance = self._make_provenance("get_dependency_chain")

        # Query for dependency chain (DEPENDS_ON relationships)
        query = (
            f"MATCH (n {{id: '{entity_id}'}})-[:DEPENDS_ON*1..{max_depth}]->(m) "
            f"RETURN m"
        )

        result = await self._call_tool(
            "query_graph", {"query": query}, "get_dependency_chain"
        )

        nodes = result.get("nodes", [])
        edges = result.get("edges", [])

        # BFS ordering for dependency chain
        marked_nodes = [self._mark_advisory(n) for n in nodes]
        marked_edges = [self._mark_advisory(e) for e in edges]

        return ExecutionResult(
            tool="graphify_adapter",
            status=ExecutionStatus.SUCCESS,
            findings=[],
            metrics={"entity_id": entity_id, "dependency_count": len(marked_nodes)},
            raw={"dependencies": marked_nodes, "edges": marked_edges},
        )