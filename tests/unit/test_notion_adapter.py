"""
M8-T4 — NotionAdapter unit tests.

Tests cover:
- Adapter creation (3 tests)
- MCP connection (3 tests)
- Page operations (5 tests)
- Database operations (2 tests)
- Provenance (2 tests)
- Advisory/C14 marking (2 tests)
- Security (3 tests)
- Failure handling (2 tests)

Total: ~18 tests
"""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aios.adapters.notion_adapter import (
    NotionAdapter,
    NotionError,
    NotionUnavailableError,
    NotionTimeoutError,
    NotionValidationError,
    NotionSecurityError,
    MalformedNotionResponseError,
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
    """Create a NotionAdapter with mocked MCPManager."""
    return NotionAdapter(
        mcp_manager=mock_mcp_manager,
        server_id="notion",
        timeout_seconds=30,
    )


@pytest.fixture
def adapter_no_mcp():
    """Create a NotionAdapter without MCPManager (for negative tests)."""
    return NotionAdapter(
        mcp_manager=None,
        server_id="notion",
        timeout_seconds=30,
    )


# ===========================================================================
# A. Adapter Creation (3 tests)
# ===========================================================================


def test_adapter_creation_defaults(adapter):
    """Adapter instantiates with default config."""
    assert adapter.perspective == "notion_planning"
    assert adapter._server_id == "notion"
    assert adapter._timeout_seconds == 30
    assert adapter._connected is False
    assert adapter._tools_discovered is False
    assert adapter._version_counter == 0


def test_adapter_injects_mcp(mock_mcp_manager):
    """Custom MCPManager injected for testing."""
    adapter = NotionAdapter(mcp_manager=mock_mcp_manager)
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
    """Connects to mock Notion server."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={"success": True, "result": {"tools": {}}}
    )

    result = await adapter.connect()

    assert result is True
    assert adapter._connected is True
    assert adapter._tools_discovered is True
    mock_mcp_manager.connect.assert_called_once_with("notion")


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
    mock_mcp_manager.disconnect.assert_called_once_with("notion")


# ===========================================================================
# C. Page Operations (5 tests)
# ===========================================================================


@pytest.mark.asyncio
async def test_search_pages(adapter, mock_mcp_manager):
    """search_pages returns structured results."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={
            "success": True,
            "result": {
                "pages": [
                    {"id": "page1", "title": "Test Page 1", "parent_id": "parent1"},
                    {"id": "page2", "title": "Test Page 2", "parent_id": "parent2"},
                ]
            },
        }
    )
    await adapter.connect()

    result = await adapter.search_pages("test query")

    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["pages_returned"] == 2
    assert len(result.raw["pages"]) == 2
    assert "advisory" in result.raw["pages"][0]["provenance"]
    assert result.raw["pages"][0]["provenance"]["advisory"] is True


@pytest.mark.asyncio
async def test_search_pages_empty(adapter, mock_mcp_manager):
    """search_pages returns empty list when no matches."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={"success": True, "result": {"pages": []}}
    )
    await adapter.connect()

    result = await adapter.search_pages("nonexistent")

    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["pages_returned"] == 0
    assert result.raw["pages"] == []


@pytest.mark.asyncio
async def test_get_page_found(adapter, mock_mcp_manager):
    """get_page returns page when found."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={"success": True, "result": {"id": "page1", "title": "Test Page"}}
    )
    await adapter.connect()

    result = await adapter.get_page("page1")

    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["found"] is True
    assert result.raw["provenance"]["advisory"] is True


@pytest.mark.asyncio
async def test_get_page_not_found(adapter, mock_mcp_manager):
    """get_page returns SUCCESS with found=False when not found."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={"success": False, "not_found": True, "error": "Page not found"}
    )
    await adapter.connect()

    result = await adapter.get_page("nonexistent")

    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["found"] is False


@pytest.mark.asyncio
async def test_create_page(adapter, mock_mcp_manager):
    """create_page creates new page."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={"success": True, "result": {"page_id": "new_page1", "created": True}}
    )
    await adapter.connect()

    result = await adapter.create_page("New Page", "parent1", {"blocks": []}, {"status": "draft"})

    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["page_id"] == "new_page1"
    assert "advisory" in result.raw["provenance"]


@pytest.mark.asyncio
async def test_update_page(adapter, mock_mcp_manager):
    """update_page updates existing page."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={"success": True, "result": {"page_id": "page1", "updated": True}}
    )
    await adapter.connect()

    result = await adapter.update_page("page1", {"blocks": [{"type": "text"}]}, {"status": "done"})

    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["page_id"] == "page1"


# ===========================================================================
# D. Database Operations (2 tests)
# ===========================================================================


@pytest.mark.asyncio
async def test_query_database(adapter, mock_mcp_manager):
    """query_database returns filtered results."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={
            "success": True,
            "result": {
                "results": [
                    {"id": "page1", "properties": {"name": "Task 1"}},
                    {"id": "page2", "properties": {"name": "Task 2"}},
                ],
                "has_more": False,
            },
        }
    )
    await adapter.connect()

    result = await adapter.query_database("db1", {"property": "status", "value": "open"})

    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["pages_returned"] == 2
    assert result.raw["has_more"] is False


@pytest.mark.asyncio
async def test_query_database_empty(adapter, mock_mcp_manager):
    """query_database returns empty when no matches."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={"success": True, "result": {"results": [], "has_more": False}}
    )
    await adapter.connect()

    result = await adapter.query_database("db1", None)

    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["pages_returned"] == 0


# ===========================================================================
# E. Provenance (2 tests)
# ===========================================================================


@pytest.mark.asyncio
async def test_provenance_fields_present(adapter, mock_mcp_manager):
    """Every result includes all required provenance fields."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={"success": True, "result": {"id": "page1", "title": "Test"}}
    )
    await adapter.connect()

    result = await adapter.get_page("page1")

    prov = result.raw["provenance"]
    required_fields = [
        "source", "adapter", "operation", "correlation_id",
        "execution_id", "task_id", "timestamp", "request_id",
        "version", "authority", "advisory", "trust_level",
    ]
    for field in required_fields:
        assert field in prov, f"Missing provenance field: {field}"


@pytest.mark.asyncio
async def test_provenance_values_correct(adapter, mock_mcp_manager):
    """Provenance fields have correct values."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={"success": True, "result": {"id": "page1", "title": "Test"}}
    )
    await adapter.connect()

    result = await adapter.get_page("page1")

    prov = result.raw["provenance"]
    assert prov["source"] == "notion"
    assert prov["adapter"] == "notion_adapter"
    assert prov["operation"] == "get_page"
    assert prov["authority"] == "contextual"
    assert prov["advisory"] is True
    assert prov["trust_level"] == "untrusted"


# ===========================================================================
# F. Advisory/C14 Marking (2 tests)
# ===========================================================================


@pytest.mark.asyncio
async def test_results_marked_advisory(adapter, mock_mcp_manager):
    """All retrieved data marked advisory per C14."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={"success": True, "result": {"pages": [{"id": "p1"}]}}
    )
    await adapter.connect()

    result = await adapter.search_pages("test")

    for page in result.raw["pages"]:
        assert page["provenance"]["advisory"] is True
        assert page["provenance"]["authority"] == "contextual"
        assert page["provenance"]["trust_level"] == "untrusted"


@pytest.mark.asyncio
async def test_execute_action_dispatch(adapter, mock_mcp_manager):
    """execute dispatches to correct action handler."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={"success": True, "result": {"pages": []}}
    )
    await adapter.connect()

    # Test search_pages action
    result = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: adapter.execute("query", {"action": "search_pages", "limit": 10})
    )
    assert result.status == ExecutionStatus.SUCCESS

    # Test get_page action
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={"success": True, "result": {"id": "p1", "title": "Test"}}
    )
    result = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: adapter.execute("page1", {"action": "get_page"})
    )
    assert result.status == ExecutionStatus.SUCCESS


# ===========================================================================
# G. Security (3 tests)
# ===========================================================================


@pytest.mark.asyncio
async def test_rejects_sensitive_property_key(adapter, mock_mcp_manager):
    """Rejects sensitive property keys before external call."""
    mock_mcp_manager.call_tool = AsyncMock()
    await adapter.connect()

    with pytest.raises(NotionSecurityError):
        await adapter.create_page("Test", "parent", {"password": "secret"})


@pytest.mark.asyncio
async def test_rejects_secret_value_patterns(adapter, mock_mcp_manager):
    """Rejects values matching secret patterns."""
    mock_mcp_manager.call_tool = AsyncMock()
    await adapter.connect()

    with pytest.raises(NotionSecurityError):
        await adapter.create_page("Test", "parent", {"api_key": "sk-1234567890abcdef1234"})


@pytest.mark.asyncio
async def test_rejects_oversized_content(adapter, mock_mcp_manager):
    """Rejects content exceeding MAX_CONTENT_SIZE."""
    large_content = {"data": "x" * 20000}  # > 10KB
    mock_mcp_manager.call_tool = AsyncMock()
    await adapter.connect()

    with pytest.raises(NotionValidationError):
        await adapter.create_page("Test", "parent", large_content)


# ===========================================================================
# H. Failure Handling (2 tests)
# ===========================================================================


@pytest.mark.asyncio
async def test_timeout_error(adapter, mock_mcp_manager):
    """Returns ERROR ExecutionResult on timeout."""
    mock_mcp_manager.call_tool = AsyncMock(
        side_effect=asyncio.TimeoutError()
    )
    await adapter.connect()

    result = await adapter.search_pages("test")

    assert result.status == ExecutionStatus.ERROR
    assert "timed out" in str(result.findings).lower()


@pytest.mark.asyncio
async def test_malformed_response_error(adapter, mock_mcp_manager):
    """Returns ERROR on malformed response."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={"success": False, "error": "Internal server error"}
    )
    await adapter.connect()

    result = await adapter.search_pages("test")

    assert result.status == ExecutionStatus.ERROR


# ===========================================================================
# I. Capability Registry (1 test)
# ===========================================================================


def test_capability_registration_pattern():
    """Verify capability registration follows expected pattern."""
    # This test just verifies the class has the right structure
    # Actual registration is tested in integration tests
    assert hasattr(NotionAdapter, 'perspective')
    assert NotionAdapter.perspective == "notion_planning"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])