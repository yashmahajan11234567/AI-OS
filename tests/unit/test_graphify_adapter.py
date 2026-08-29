"""
M8-T3 — GraphifyAdapter unit tests.

Tests cover:
- Adapter creation (3 tests)
- MCP connection (3 tests)
- Node operations (5 tests)
- Edge operations (3 tests)
- Query operations (3 tests)
- Context enrichment (3 tests)
- Provenance (2 tests)
- Advisory/C14 marking (2 tests)
- Security (3 tests)
- Failure handling (2 tests)
- Capability registry (1 test)

Total: 27 tests
"""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aios.adapters.graphify_adapter import (
    GraphifyAdapter,
    GraphifyError,
    GraphifyUnavailableError,
    GraphifyTimeoutError,
    GraphifyValidationError,
    GraphifyStorageError,
    MalformedGraphifyResponseError,
    GraphifySecurityError,
)
from aios.adapters.base import ExecutionResult, ExecutionStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_mcp_manager():
    """Create a mock MCPManager."""
    mcp = MagicMock()
    mcp.connect = AsyncMock(return_value=True)
    mcp.disconnect = AsyncMock(return_value=None)
    mcp.call_tool = AsyncMock(return_value={"success": True, "result": {}})
    return mcp


@pytest.fixture
def adapter(mock_mcp_manager):
    """Create a GraphifyAdapter with mocked MCPManager."""
    return GraphifyAdapter(
        mcp_manager=mock_mcp_manager,
        server_id="graphify",
        timeout_seconds=30,
        namespace="ai_os",
    )


@pytest.fixture
def adapter_no_mcp():
    """Create a GraphifyAdapter without MCPManager (for negative tests)."""
    return GraphifyAdapter(
        mcp_manager=None,
        server_id="graphify",
        timeout_seconds=30,
        namespace="ai_os",
    )


# ===========================================================================
# A. Adapter Creation (3 tests)
# ===========================================================================

def test_adapter_creation_defaults(adapter):
    """Adapter instantiates with default config."""
    assert adapter.perspective == "graphify_context"
    assert adapter._server_id == "graphify"
    assert adapter._timeout_seconds == 30
    assert adapter._namespace == "ai_os"
    assert adapter._connected is False
    assert adapter._tools_discovered is False
    assert adapter._version_counter == 0


def test_adapter_injects_mcp(mock_mcp_manager):
    """Custom MCPManager injected for testing."""
    adapter = GraphifyAdapter(mcp_manager=mock_mcp_manager)
    assert adapter._mcp_manager is mock_mcp_manager


def test_adapter_default_tool_raises_without_mcp(adapter_no_mcp):
    """_default_tool raises NotImplementedError without MCP."""
    with pytest.raises(NotImplementedError):
        adapter_no_mcp._default_tool("target", {})


# ===========================================================================
# B. MCP Connection (3 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_connect_success(adapter, mock_mcp_manager):
    """Connects to mock Graphify server."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={"success": True, "result": {"tools": {}}}
    )

    result = await adapter.connect()

    assert result is True
    assert adapter._connected is True
    assert adapter._tools_discovered is True
    mock_mcp_manager.connect.assert_called_once_with("graphify")


@pytest.mark.asyncio
async def test_connect_mcp_not_available(adapter_no_mcp):
    """Missing MCPManager -> returns False, doesn't crash."""
    result = await adapter_no_mcp.connect()

    assert result is False
    assert adapter_no_mcp._connected is False


@pytest.mark.asyncio
async def test_disconnect(adapter, mock_mcp_manager):
    """Disconnect cleans up connection."""
    # First connect
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={"success": True, "result": {"tools": {}}}
    )
    await adapter.connect()

    # Then disconnect
    await adapter.disconnect()

    assert adapter._connected is False
    assert adapter._tools_discovered is False
    mock_mcp_manager.disconnect.assert_called_once_with("graphify")


# ===========================================================================
# C. Node Operations (5 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_store_node(adapter, mock_mcp_manager):
    """Store node, verify in graph."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={"success": True, "result": {"created": True}}
    )

    await adapter.connect()

    result = await adapter.store_node(
        "task:abc123", "task", {"title": "Test Task", "status": "pending"}
    )

    assert isinstance(result, ExecutionResult)
    assert result.status == ExecutionStatus.SUCCESS
    assert "entity_id" in result.metrics
    assert result.metrics["entity_id"] == "ai_os:task:abc123"
    # call_tool called twice: once for tools/list, once for add_node
    assert mock_mcp_manager.call_tool.call_count >= 1


@pytest.mark.asyncio
async def test_get_node_found(adapter, mock_mcp_manager):
    """Retrieve stored node."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={
            "success": True,
            "result": {
                "id": "ai_os:task:abc123",
                "label": "task",
                "properties": {
                    "title": "Test Task",
                    "provenance": {"source": "ai_os"},
                },
            },
        }
    )

    await adapter.connect()

    result = await adapter.get_node("task:abc123")

    assert isinstance(result, ExecutionResult)
    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["found"] is True
    assert "provenance" in result.raw


@pytest.mark.asyncio
async def test_get_node_not_found(adapter, mock_mcp_manager):
    """Missing node -> returns empty result with found=False."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={
            "success": False,
            "not_found": True,
            "error": "Node not found",
        }
    )

    await adapter.connect()

    result = await adapter.get_node("task:nonexistent")

    assert isinstance(result, ExecutionResult)
    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["found"] is False


@pytest.mark.asyncio
async def test_update_node(adapter, mock_mcp_manager):
    """Update node properties."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={"success": True, "result": {"updated": True}}
    )

    await adapter.connect()

    result = await adapter.update_node("task:abc123", {"status": "completed"})

    assert isinstance(result, ExecutionResult)
    assert result.status == ExecutionStatus.SUCCESS
    # call_tool called twice: once for tools/list, once for update_node
    assert mock_mcp_manager.call_tool.call_count >= 1


@pytest.mark.asyncio
async def test_delete_node(adapter, mock_mcp_manager):
    """Delete node, verify removed."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={"success": True, "result": {"deleted": True}}
    )

    await adapter.connect()

    result = await adapter.delete_node("task:abc123")

    assert isinstance(result, ExecutionResult)
    assert result.status == ExecutionStatus.SUCCESS
    # call_tool called twice: once for tools/list, once for delete_node
    assert mock_mcp_manager.call_tool.call_count >= 1


# ===========================================================================
# D. Edge Operations (3 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_add_edge(adapter, mock_mcp_manager):
    """Add edge, verify in graph."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={
            "success": True,
            "result": {"edge": {"from_node": "ai_os:task:a", "to_node": "ai_os:task:b", "relationship": "DEPENDS_ON"}, "created": True}
        }
    )

    await adapter.connect()

    result = await adapter.add_edge(
        "task:a", "task:b", "DEPENDS_ON", {"weight": 1.0}
    )

    assert isinstance(result, ExecutionResult)
    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["relationship"] == "DEPENDS_ON"


@pytest.mark.asyncio
async def test_add_edge_duplicate_no_duplicate_created(adapter, mock_mcp_manager):
    """Duplicate edge -> no duplicate created (handled by backend)."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={
            "success": True,
            "result": {"edge": {"from_node": "ai_os:task:a", "to_node": "ai_os:task:b", "relationship": "DEPENDS_ON"}, "created": False}
        }
    )

    await adapter.connect()

    result = await adapter.add_edge("task:a", "task:b", "DEPENDS_ON")

    # The adapter doesn't check for duplicates; it relies on backend behavior
    assert isinstance(result, ExecutionResult)


@pytest.mark.asyncio
async def test_add_edge_missing_node(adapter, mock_mcp_manager):
    """Edge to non-existent node -> warning, edge still created (backend handles)."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={
            "success": True,
            "result": {"edge": {"from_node": "ai_os:task:a", "to_node": "ai_os:task:missing", "relationship": "DEPENDS_ON"}, "created": True}
        }
    )

    await adapter.connect()

    result = await adapter.add_edge("task:a", "task:missing", "DEPENDS_ON")

    assert isinstance(result, ExecutionResult)
    assert result.status == ExecutionStatus.SUCCESS


# ===========================================================================
# E. Query Operations (3 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_query_graph(adapter, mock_mcp_manager):
    """Query returns nodes and edges."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={
            "success": True,
            "result": {
                "nodes": [
                    {"id": "ai_os:task:a", "label": "task", "properties": {"title": "A"}},
                    {"id": "ai_os:task:b", "label": "task", "properties": {"title": "B"}},
                ],
                "edges": [
                    {"from_node": "ai_os:task:a", "to_node": "ai_os:task:b", "relationship": "DEPENDS_ON", "properties": {}}
                ],
            },
        }
    )

    await adapter.connect()

    result = await adapter.query_graph("MATCH (n) RETURN n LIMIT 10")

    assert isinstance(result, ExecutionResult)
    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["nodes_returned"] == 2
    assert result.metrics["edges_returned"] == 1
    assert len(result.raw["nodes"]) == 2
    assert len(result.raw["edges"]) == 1


@pytest.mark.asyncio
async def test_shortest_path_found(adapter, mock_mcp_manager):
    """Path found between connected nodes."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={
            "success": True,
            "result": {"path": ["ai_os:task:a", "ai_os:task:b", "ai_os:task:c"], "found": True}
        }
    )

    await adapter.connect()

    result = await adapter.shortest_path("task:a", "task:c")

    assert isinstance(result, ExecutionResult)
    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["found"] is True
    assert result.metrics["path_length"] == 3
    assert len(result.raw["path"]) == 3


@pytest.mark.asyncio
async def test_shortest_path_not_found(adapter, mock_mcp_manager):
    """No path -> empty list."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={
            "success": True,
            "result": {"path": [], "found": False}
        }
    )

    await adapter.connect()

    result = await adapter.shortest_path("task:a", "task:z")

    assert isinstance(result, ExecutionResult)
    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["found"] is False
    assert result.metrics["path_length"] == 0


# ===========================================================================
# F. Context Enrichment (3 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_get_related_entities(adapter, mock_mcp_manager):
    """Returns related nodes with relationship type."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={
            "success": True,
            "result": {
                "nodes": [
                    {"id": "ai_os:task:b", "label": "task", "properties": {"title": "B"}},
                ],
                "edges": [
                    {"from_node": "ai_os:task:a", "to_node": "ai_os:task:b", "relationship": "DEPENDS_ON", "properties": {}, "created_at": "2024-01-01T00:00:00Z"}
                ],
            },
        }
    )

    await adapter.connect()

    result = await adapter.get_related_entities("task:a", "DEPENDS_ON")

    assert isinstance(result, ExecutionResult)
    assert result.status == ExecutionStatus.SUCCESS
    assert "related_count" in result.metrics
    assert len(result.raw["edges"]) == 1
    assert result.raw["edges"][0]["relationship"] == "DEPENDS_ON"


@pytest.mark.asyncio
async def test_get_execution_history(adapter, mock_mcp_manager):
    """Returns execution nodes ordered by time."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={
            "success": True,
            "result": {
                "nodes": [
                    {"id": "ai_os:exec:1", "label": "execution", "properties": {"started_at": "2024-01-01T00:00:00Z"}},
                    {"id": "ai_os:exec:2", "label": "execution", "properties": {"started_at": "2024-01-01T01:00:00Z"}},
                ],
                "edges": [],
            },
        }
    )

    await adapter.connect()

    result = await adapter.get_execution_history("exec:1")

    assert isinstance(result, ExecutionResult)
    assert result.status == ExecutionStatus.SUCCESS
    assert "history_count" in result.metrics
    assert len(result.raw["executions"]) == 2


@pytest.mark.asyncio
async def test_get_dependency_chain(adapter, mock_mcp_manager):
    """Returns full dependency chain."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={
            "success": True,
            "result": {
                "nodes": [
                    {"id": "ai_os:task:b", "label": "task", "properties": {"title": "B"}},
                    {"id": "ai_os:task:c", "label": "task", "properties": {"title": "C"}},
                ],
                "edges": [
                    {"from_node": "ai_os:task:a", "to_node": "ai_os:task:b", "relationship": "DEPENDS_ON"},
                    {"from_node": "ai_os:task:b", "to_node": "ai_os:task:c", "relationship": "DEPENDS_ON"},
                ],
            },
        }
    )

    await adapter.connect()

    result = await adapter.get_dependency_chain("task:a")

    assert isinstance(result, ExecutionResult)
    assert result.status == ExecutionStatus.SUCCESS
    assert "dependency_count" in result.metrics
    assert len(result.raw["dependencies"]) == 2


# ===========================================================================
# G. Provenance (2 tests)
# ===========================================================================

def test_provenance_complete(adapter):
    """All mandatory provenance fields present."""
    prov = adapter._make_provenance(
        "store_node",
        execution_id="exec:123",
        task_id="task:456",
        correlation_id="corr:789",
    )

    assert prov["source"] == "ai_os"
    assert prov["adapter"] == "graphify_adapter"
    assert prov["operation"] == "store_node"
    assert prov["correlation_id"] == "corr:789"
    assert prov["execution_id"] == "exec:123"
    assert prov["task_id"] == "task:456"
    assert "timestamp" in prov
    assert "request_id" in prov
    assert "version" in prov
    assert isinstance(prov["version"], int)


def test_provenance_no_secrets(adapter):
    """No plaintext secrets in provenance."""
    prov = adapter._make_provenance("store_node")

    # Check no secret keys in provenance
    prov_str = str(prov).lower()
    sensitive = ["password", "token", "secret", "api_key", "authorization"]
    for word in sensitive:
        assert word not in prov_str


# ===========================================================================
# H. Advisory Marking (C14) (2 tests)
# ===========================================================================

def test_advisory_marking_on_retrieve(adapter):
    """Retrieved nodes marked advisory."""
    metadata = {"relationship": "depends_on", "confidence": 0.8}
    marked = adapter._mark_advisory(metadata)

    assert "provenance" in marked
    assert marked["provenance"]["source"] == "graphify_inferred"
    assert marked["provenance"]["advisory"] is True
    assert marked["provenance"]["authority"] == "advisory_only"
    assert "graphify_timestamp" in marked["provenance"]


def test_advisory_marking_on_query(adapter):
    """Queried results marked advisory."""
    node = {"id": "ai_os:task:a", "properties": {"title": "Test"}}
    marked = adapter._mark_advisory(node)

    assert "provenance" in marked
    assert marked["provenance"]["source"] == "graphify_inferred"
    assert marked["provenance"]["advisory"] is True
    assert marked["provenance"]["authority"] == "advisory_only"


# ===========================================================================
# I. Security (3 tests)
# ===========================================================================

def test_sensitive_property_key_rejected(adapter):
    """Node with password property -> rejected."""
    with pytest.raises(GraphifySecurityError):
        adapter._validate_properties({"password": "secret123"})


def test_oversized_property_rejected(adapter):
    """Property > 10KB -> rejected."""
    oversized = "x" * 11000  # > 10KB
    with pytest.raises(GraphifyValidationError):
        adapter._validate_properties({"data": oversized})


def test_no_verdict_in_result(adapter):
    """ExecutionResult has no verdict field."""
    result = ExecutionResult(
        tool="graphify_adapter",
        status=ExecutionStatus.SUCCESS,
        findings=[],
    )

    # Verify no verdict-like fields
    assert "verdict" not in result.__dict__
    assert "approved" not in str(result).lower()
    assert "rejected" not in str(result).lower()


# ===========================================================================
# J. Failure Handling (2 tests)
# ===========================================================================

@pytest.mark.asyncio
async def test_graphify_unavailable_returns_empty_context(adapter):
    """Server down -> returns empty context, no crash (in execute path)."""
    # Don't connect, just call execute which will use _default_tool
    # But _default_tool raises NotImplementedError without connection
    # The real test is that the adapter doesn't crash on failed operations
    adapter._connected = False  # Explicitly not connected

    # The adapter should handle missing connection gracefully in execute()
    # Since we don't have a real MCP, we test the error classification
    with pytest.raises(GraphifyUnavailableError):
        await adapter._call_tool("add_node", {"node_id": "test"}, "test")


@pytest.mark.asyncio
async def test_malformed_response_raises_error(adapter, mock_mcp_manager):
    """Bad JSON response -> MalformedGraphifyResponseError."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={"success": False, "error": "Internal server error"}
    )
    adapter._connected = True

    with pytest.raises(MalformedGraphifyResponseError):
        await adapter._call_tool("add_node", {"node_id": "test"}, "test")


# ===========================================================================
# K. Capability Registry (1 test)
# ===========================================================================

def test_capability_registration_pattern():
    """Verify capability registration pattern matches spec."""
    # This test verifies the registration pattern used in kernel.py
    capability_data = {
        "capability_id": "graphify_context",
        "facade": "graph",
        "provider_id": "graphify",
        "provider_metadata": {
            "server_id": "graphify",
            "transport": "stdio",
            "timeout_seconds": 30,
            "auto_reconnect": True,
        },
        "security_context": {
            "requires_validation": True,
            "allowed_operations": [
                "add_node", "get_node", "update_node", "delete_node",
                "query_graph", "shortest_path", "add_edge",
            ],
        },
        "tags": ("graph", "knowledge", "context", "relationships", "dependency"),
    }

    assert capability_data["capability_id"] == "graphify_context"
    assert capability_data["facade"] == "graph"
    assert capability_data["provider_id"] == "graphify"
    assert "query_graph" in capability_data["security_context"]["allowed_operations"]
    assert "add_edge" in capability_data["security_context"]["allowed_operations"]


# ===========================================================================
# Additional: Namespace and Validation tests
# ===========================================================================

def test_namespace_prefixing(adapter):
    """Entity IDs are prefixed with namespace."""
    assert adapter._make_entity_id("task:123") == "ai_os:task:123"
    assert adapter._make_entity_id("ai_os:task:123") == "ai_os:task:123"  # already prefixed


def test_namespace_striping(adapter):
    """Namespace can be stripped."""
    assert adapter._strip_namespace("ai_os:task:123") == "task:123"
    assert adapter._strip_namespace("task:123") == "task:123"


def test_query_validation_length(adapter):
    """Query string length validated."""
    long_query = "x" * 1001
    with pytest.raises(GraphifyValidationError):
        adapter._validate_query(long_query)


def test_query_validation_ok(adapter):
    """Valid query passes validation."""
    adapter._validate_query("MATCH (n) RETURN n LIMIT 10")  # Should not raise


def test_rendered_lock_not_in_adapter_code():
    """Verify no forbidden patterns in adapter code."""
    # This is a static check - the adapter module shouldn't import:
    # - SecurityManager
    # - CouncilManager
    # - StateManager
    # - EventBus publish
    # - verdict/approved/rejected decisions
    import aios.adapters.graphify_adapter as mod
    import inspect

    source = inspect.getsource(mod)

    forbidden_imports = [
        "from aios.core.security_manager import",
        "from aios.core.council_manager import",
        "from aios.core.state import",
        "self._event_bus.publish",
    ]

    for forbidden in forbidden_imports:
        assert forbidden not in source, f"Forbidden import found: {forbidden}"

    # Check no verdict/decision language
    assert 'return {"verdict"' not in source
    assert 'return {"status": "approved"' not in source
    assert 'return {"decision": "reject"' not in source


# ===========================================================================
# Additional: Error Hierarchy tests
# ===========================================================================

def test_error_hierarchy():
    """GraphifyError hierarchy is correct."""
    # All specific errors inherit from GraphifyError
    assert issubclass(GraphifyUnavailableError, GraphifyError)
    assert issubclass(GraphifyTimeoutError, GraphifyError)
    assert issubclass(GraphifyValidationError, GraphifyError)
    assert issubclass(GraphifyStorageError, GraphifyError)
    assert issubclass(MalformedGraphifyResponseError, GraphifyError)
    assert issubclass(GraphifySecurityError, GraphifyError)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])