"""
Integration tests for M8-T4 Obsidian Persistent Knowledge Integration.

Full-flow tests with mock Obsidian MCP server (in-process) plus a real
temporary filesystem vault for the fallback path. Tests dual-path routing,
protocol round-trips, C14 advisory marking, and path-traversal protection.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest

# Add src to path
sys_path = str(Path(__file__).parent.parent.parent / "src")
if sys_path not in __import__("sys").path:
    __import__("sys").path.insert(0, sys_path)

from aios.adapters.obsidian_adapter import (
    ObsidianAdapter,
    ObsidianSecurityError,
    ObsidianUnavailableError,
)
from aios.adapters.mock_obsidian_server import MockObsidianServer
from aios.adapters.base import ExecutionStatus


class MockMCPManager:
    """Mock MCPManager using in-process MockObsidianServer."""

    def __init__(self):
        self._servers = {}
        self._server = MockObsidianServer()

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
            request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        else:
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": args},
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


@pytest.fixture
def temp_vault():
    """Temporary filesystem vault with sample notes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault = Path(tmpdir)
        (vault / "arch.md").write_text(
            "---\ntitle: Architecture\ntags: [design, core]\n---\n\nKernel design notes"
        )
        (vault / "testing.md").write_text(
            "---\ntitle: Testing Guide\ntags: [qa]\n---\n\nHow to test the kernel"
        )
        sub = vault / "projects"
        sub.mkdir()
        (sub / "m8.md").write_text(
            "---\ntitle: M8 Plan\ntags: [planning]\n---\n\nExternal integrations milestone"
        )
        yield vault


def add_note_to_mock(server: MockObsidianServer, path: str, title: str, tags: list, content: str):
    """Helper to seed mock server notes."""
    server._notes[path] = {
        "path": path,
        "title": title,
        "tags": tags,
        "content": content,
        "created_at": "2026-08-25T00:00:00",
        "updated_at": "2026-08-25T00:00:00",
    }


# ===========================================================================
# Mock Server Protocol Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_obsidian_mock_server_initialize():
    """Test Obsidian MCP server initialize handshake."""
    server = MockObsidianServer()
    req = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
    resp = server.handle_request(req)

    assert "result" in resp
    assert resp["result"]["serverInfo"]["name"]
    assert "tools" in resp["result"]["capabilities"]


@pytest.mark.asyncio
async def test_obsidian_mock_server_tools_list():
    """Test tools/list returns all 4 Obsidian tools."""
    server = MockObsidianServer()
    req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    resp = server.handle_request(req)

    tools = {t["name"] for t in resp["result"]["tools"]}
    expected = {"search_notes", "get_note", "list_notes", "read_note"}
    assert tools == expected


# ===========================================================================
# Dual-Path Routing Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_obsidian_mcp_path_used_when_connected(mock_mcp_manager):
    """When connected via MCP, retrieval reports retrieval_path=mcp."""
    adapter = ObsidianAdapter(mcp_manager=mock_mcp_manager)
    await adapter.connect()

    result = await adapter.search_notes("anything")

    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["retrieval_path"] == "mcp"


@pytest.mark.asyncio
async def test_obsidian_fallback_used_without_mcp(temp_vault):
    """Without MCP, filesystem fallback serves requests."""
    adapter = ObsidianAdapter(mcp_manager=None, vault_path=str(temp_vault))

    result = await adapter.search_notes("architecture")

    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["retrieval_path"] == "filesystem_fallback"
    assert result.metrics["notes_returned"] == 1
    assert result.raw["notes"][0]["title"] == "Architecture"


@pytest.mark.asyncio
async def test_obsidian_mcp_failure_degrades_to_filesystem(mock_mcp_manager, temp_vault):
    """MCP failure degrades gracefully to filesystem fallback."""
    # Seed both paths with matching content
    add_note_to_mock(
        mock_mcp_manager._server, "arch.md", "Architecture", ["design"], "Kernel design"
    )

    adapter = ObsidianAdapter(
        mcp_manager=mock_mcp_manager, vault_path=str(temp_vault)
    )
    await adapter.connect()

    # Break the MCP path mid-session
    async def broken(*a, **kw):
        raise Exception("connection lost")

    mock_mcp_manager.call_tool = broken

    result = await adapter.search_notes("architecture")

    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["retrieval_path"] == "filesystem_fallback"


# ===========================================================================
# Full Flow Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_obsidian_full_flow_via_mcp(mock_mcp_manager):
    """Full note flow over MCP: seed -> search -> get -> read -> list."""
    adapter = ObsidianAdapter(mcp_manager=mock_mcp_manager)
    await adapter.connect()

    add_note_to_mock(
        adapter._mcp_manager._server,
        "notes/design.md",
        "Design Doc",
        ["design"],
        "System design content",
    )

    # Search
    search_result = await adapter.search_notes("design")
    assert search_result.status == ExecutionStatus.SUCCESS
    assert search_result.metrics["notes_returned"] == 1

    # Get
    get_result = await adapter.get_note("notes/design.md")
    assert get_result.status == ExecutionStatus.SUCCESS
    assert get_result.metrics["found"] is True

    # Read
    read_result = await adapter.read_note("notes/design.md")
    assert read_result.status == ExecutionStatus.SUCCESS

    # List
    list_result = await adapter.list_notes(".")
    assert list_result.status == ExecutionStatus.SUCCESS
    assert list_result.metrics["notes_returned"] >= 1


@pytest.mark.asyncio
async def test_obsidian_get_missing_note_no_crash(mock_mcp_manager):
    """get_note on missing note returns found=False without crashing."""
    adapter = ObsidianAdapter(mcp_manager=mock_mcp_manager)
    await adapter.connect()

    result = await adapter.get_note("does/not/exist.md")

    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["found"] is False


@pytest.mark.asyncio
async def test_obsidian_subdirectory_scoping(temp_vault):
    """Filesystem fallback respects directory scoping."""
    adapter = ObsidianAdapter(mcp_manager=None, vault_path=str(temp_vault))

    result = await adapter.list_notes("projects")

    assert result.status == ExecutionStatus.SUCCESS
    paths = [n["path"] for n in result.raw["notes"]]
    assert all(p.startswith("projects") for p in paths)


# ===========================================================================
# C14 Advisory / Provenance Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_obsidian_c14_advisory_both_paths(mock_mcp_manager, temp_vault):
    """Both retrieval paths mark results advisory per C14."""
    # MCP path
    add_note_to_mock(
        mock_mcp_manager._server, "c14.md", "C14 Note", [], "advisory content"
    )
    mcp_adapter = ObsidianAdapter(mcp_manager=mock_mcp_manager)
    await mcp_adapter.connect()
    mcp_result = await mcp_adapter.search_notes("c14")

    assert mcp_result.metrics["retrieval_path"] == "mcp"
    for note in mcp_result.raw["notes"]:
        prov = note.get("provenance", {})
        assert prov.get("advisory") is True
        assert prov.get("authority") == "contextual"
        assert prov.get("trust_level") == "trusted_contextual"

    # Filesystem path
    fs_adapter = ObsidianAdapter(mcp_manager=None, vault_path=str(temp_vault))
    fs_result = await fs_adapter.search_notes("kernel")

    assert fs_result.metrics["retrieval_path"] == "filesystem_fallback"
    for note in fs_result.raw["notes"]:
        prov = note.get("provenance", {})
        assert prov.get("advisory") is True
        assert prov.get("authority") == "contextual"


@pytest.mark.asyncio
async def test_obsidian_provenance_fields_complete(temp_vault):
    """Filesystem fallback results carry complete provenance fields."""
    adapter = ObsidianAdapter(mcp_manager=None, vault_path=str(temp_vault))

    result = await adapter.get_note("arch.md")

    prov = result.raw["provenance"]
    required_fields = [
        "source", "adapter", "operation", "correlation_id",
        "execution_id", "task_id", "timestamp", "request_id",
        "version", "authority", "advisory", "trust_level",
        "retrieval_path",
    ]
    for field in required_fields:
        assert field in prov, f"Missing provenance field: {field}"

    assert prov["source"] == "obsidian"
    assert prov["operation"] == "read_note"


# ===========================================================================
# Security Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_obsidian_path_traversal_blocked_end_to_end(temp_vault):
    """Path traversal blocked across both direct validation and operations."""
    adapter = ObsidianAdapter(mcp_manager=None, vault_path=str(temp_vault))

    # Direct validation raises
    with pytest.raises(ObsidianSecurityError):
        adapter._validate_path("../../outside/secret.txt")

    # Operation surfaces ERROR result rather than crashing
    result = await adapter.get_note("..\\..\\windows\\system32\\config")
    assert result.status == ExecutionStatus.ERROR


@pytest.mark.asyncio
async def test_obsidian_dot_obsidian_directory_protected(temp_vault):
    """.obsidian internal directory is inaccessible even if it exists."""
    obs_dir = temp_vault / ".obsidian"
    obs_dir.mkdir(exist_ok=True)
    (obs_dir / "workspace.json").write_text('{"fake": "config"}')

    adapter = ObsidianAdapter(mcp_manager=None, vault_path=str(temp_vault))

    with pytest.raises(ObsidianSecurityError):
        adapter._validate_path(".obsidian/workspace.json")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
