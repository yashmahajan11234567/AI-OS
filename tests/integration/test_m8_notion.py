"""
Integration tests for M8-T4 Notion Planning Integration.

Full-flow tests with mock Notion MCP server (in-process).
Tests real protocol round-trips, C14 advisory marking, provenance,
security validation, and graceful degradation.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from aios.adapters.notion_adapter import (
    NotionAdapter,
    NotionUnavailableError,
)
from aios.adapters.mock_notion_server import MockNotionServer
from aios.adapters.base import ExecutionStatus


class MockMCPManager:
    """Mock MCPManager using in-process MockNotionServer."""

    def __init__(self):
        self._servers = {}
        self._server = MockNotionServer()

    async def connect(self, server_id):
        self._servers[server_id] = {"connected": True}
        return True

    def get_server_status(self, server_id):
        status = self._servers.get(server_id)
        if status:
            return type('Status', (), {'connected': status['connected']})()
        return None

    async def call_tool(self, server_id, tool_name, args, call_id=None):
        if tool_name == "tools/list":
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }
        else:
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": args}
            }
        response = self._server.handle_request(request)
        if response is None:
            return {"success": True, "result": {}}
        if "error" in response:
            raise Exception(response["error"]["message"])
        return response.get("result", {"success": True, "result": {}})

    async def disconnect(self, server_id):
        self._servers[server_id] = {"connected": False}


@pytest.fixture
def mock_mcp_manager():
    return MockMCPManager()


# ===========================================================================
# Mock Server Protocol Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_notion_mock_server_initialize():
    """Test Notion MCP server initialize handshake."""
    server = MockNotionServer()
    req = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
    resp = server.handle_request(req)

    assert "result" in resp
    assert resp["result"]["protocolVersion"] == "2024-11-05"
    assert resp["result"]["serverInfo"]["name"] == "Mock Notion Server"
    assert "tools" in resp["result"]["capabilities"]


@pytest.mark.asyncio
async def test_notion_mock_server_tools_list():
    """Test tools/list returns all 5 Notion tools."""
    server = MockNotionServer()
    req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    resp = server.handle_request(req)

    assert "result" in resp
    tools = {t["name"] for t in resp["result"]["tools"]}
    expected = {"search_pages", "get_page", "create_page", "update_page", "query_database"}
    assert tools == expected


# ===========================================================================
# Full Flow Tests (Adapter + Mock Server)
# ===========================================================================


@pytest.mark.asyncio
async def test_notion_full_page_lifecycle(mock_mcp_manager):
    """Full page lifecycle: create -> get -> search -> update."""
    adapter = NotionAdapter(mcp_manager=mock_mcp_manager)
    await adapter.connect()

    # 1. Create a page
    create_result = await adapter.create_page(
        "Test Plan", "parent1", {"blocks": [{"type": "paragraph"}]}, {"status": "draft"}
    )
    assert create_result.status == ExecutionStatus.SUCCESS
    page_id = create_result.metrics["page_id"]
    assert page_id.startswith("page_")

    # 2. Get the page back
    get_result = await adapter.get_page(page_id)
    assert get_result.status == ExecutionStatus.SUCCESS
    assert get_result.metrics["found"] is True
    assert get_result.raw["title"] == "Test Plan"

    # 3. Search for it
    search_result = await adapter.search_pages("Test Plan")
    assert search_result.status == ExecutionStatus.SUCCESS
    assert search_result.metrics["pages_returned"] == 1

    # 4. Update the page
    update_result = await adapter.update_page(page_id, {"blocks": [{"type": "h1"}]})
    assert update_result.status == ExecutionStatus.SUCCESS

    await adapter.disconnect()


@pytest.mark.asyncio
async def test_notion_get_missing_page(mock_mcp_manager):
    """get_page for missing page returns found=False without crashing."""
    adapter = NotionAdapter(mcp_manager=mock_mcp_manager)
    await adapter.connect()

    result = await adapter.get_page("nonexistent_page")

    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["found"] is False
    assert result.raw == {}


@pytest.mark.asyncio
async def test_notion_search_empty_vault(mock_mcp_manager):
    """search_pages on empty vault returns empty results gracefully."""
    adapter = NotionAdapter(mcp_manager=mock_mcp_manager)
    await adapter.connect()

    result = await adapter.search_pages("anything")

    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["pages_returned"] == 0
    assert result.raw["pages"] == []


@pytest.mark.asyncio
async def test_notion_query_database_flow(mock_mcp_manager):
    """query_database returns pages parented under database."""
    adapter = NotionAdapter(mcp_manager=mock_mcp_manager)
    await adapter.connect()

    # Create two pages in a "database"
    await adapter.create_page("Task A", "db_tasks", {}, {"status": "open"})
    await adapter.create_page("Task B", "db_tasks", {}, {"status": "done"})

    result = await adapter.query_database("db_tasks")

    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["pages_returned"] == 2
    assert result.raw["has_more"] is False

    await adapter.disconnect()


# ===========================================================================
# C14 Advisory Marking / Provenance Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_notion_c14_advisory_on_retrieval(mock_mcp_manager):
    """Retrieved pages carry advisory=True per C14."""
    adapter = NotionAdapter(mcp_manager=mock_mcp_manager)
    await adapter.connect()

    await adapter.create_page("C14 Test", "parent1", {}, {})
    search_result = await adapter.search_pages("C14")

    assert search_result.status == ExecutionStatus.SUCCESS
    for page in search_result.raw["pages"]:
        prov = page.get("provenance", {})
        assert prov.get("advisory") is True
        assert prov.get("authority") == "contextual"
        assert prov.get("trust_level") == "untrusted"
        assert prov.get("source") == "notion"

    await adapter.disconnect()


@pytest.mark.asyncio
async def test_notion_provenance_fields_complete(mock_mcp_manager):
    """Every operation result carries complete provenance fields."""
    adapter = NotionAdapter(mcp_manager=mock_mcp_manager)
    await adapter.connect()

    create_result = await adapter.create_page("Prov Test", "p1", {}, {})
    marked_raw = create_result.raw
    prov = marked_raw["provenance"]

    required_fields = [
        "source", "adapter", "operation", "correlation_id",
        "execution_id", "task_id", "timestamp", "request_id",
        "version", "authority", "advisory", "trust_level",
    ]
    for field in required_fields:
        assert field in prov, f"Missing provenance field: {field}"

    assert prov["adapter"] == "notion_adapter"
    assert prov["operation"] == "create_page"

    await adapter.disconnect()


@pytest.mark.asyncio
async def test_notion_no_secrets_in_provenance(mock_mcp_manager):
    """Provenance never contains secret-looking values."""
    import re

    adapter = NotionAdapter(mcp_manager=mock_mcp_manager)
    await adapter.connect()

    await adapter.create_page("Sec Test", "p1", {}, {})
    result = await adapter.search_pages("Sec")

    raw_str = str(result.raw)
    secret_patterns = [
        r"sk[-_][a-zA-Z0-9]{20,}",
        r"Bearer\s+[a-zA-Z0-9._-]+",
        r"(?i)password\s*[:=]\s*\S+",
    ]
    for pattern in secret_patterns:
        assert not re.search(pattern, raw_str), f"Secret pattern leaked: {pattern}"


# ===========================================================================
# Security Validation Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_notion_sensitive_property_rejected_end_to_end(mock_mcp_manager):
    """Sensitive property keys rejected before any external call."""
    adapter = NotionAdapter(mcp_manager=mock_mcp_manager)
    await adapter.connect()

    from aios.adapters.notion_adapter import NotionSecurityError

    with pytest.raises(NotionSecurityError):
        await adapter.create_page("Evil", "p1", {}, {"api_key": "sk-1234567890abcdef1234"})

    # Verify nothing was created on the server side
    search_result = await adapter.search_pages("Evil")
    assert search_result.metrics["pages_returned"] == 0


@pytest.mark.asyncio
async def test_notion_oversized_property_rejected_end_to_end(mock_mcp_manager):
    """Oversized content rejected before any external call."""
    adapter = NotionAdapter(mcp_manager=mock_mcp_manager)
    await adapter.connect()

    from aios.adapters.notion_adapter import NotionValidationError

    large_content = {"data": "x" * 20000}
    with pytest.raises(NotionValidationError):
        await adapter.create_page("Big", "p1", large_content, {})


# ===========================================================================
# Graceful Degradation Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_notion_unavailable_returns_error_result(mock_mcp_manager):
    """Server failure yields ERROR ExecutionResult, not an exception."""
    adapter = NotionAdapter(mcp_manager=mock_mcp_manager)
    await adapter.connect()

    # Break the underlying server to simulate failure
    mock_mcp_manager._server._pages = None

    result = await adapter.search_pages("anything")

    assert result.status == ExecutionStatus.ERROR
    assert len(result.findings) >= 1
    assert result.findings[0]["severity"] == "error"


@pytest.mark.asyncio
async def test_notion_not_connected_returns_unavailable():
    """Operations without connection raise NotImplementedError via _default_tool."""
    adapter = NotionAdapter(mcp_manager=None)

    assert await adapter.connect() is False
    assert adapter.is_connected() is False

    with pytest.raises(NotImplementedError):
        adapter._default_tool("target", {})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
