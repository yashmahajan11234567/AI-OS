"""
M8-T4 — ObsidianAdapter unit tests.

Tests cover:
- Adapter creation (3 tests)
- MCP connection (3 tests)
- Filesystem fallback (3 tests)
- Note operations (6 tests)
- Dual-path (MCP + filesystem) (3 tests)
- Provenance (3 tests)
- Advisory/C14 marking (2 tests)
- Security (4 tests)

Total: ~27 tests
"""

from __future__ import annotations

import asyncio
import tempfile
import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from aios.adapters.obsidian_adapter import (
    ObsidianAdapter,
    ObsidianError,
    ObsidianUnavailableError,
    ObsidianTimeoutError,
    ObsidianValidationError,
    ObsidianSecurityError,
    ObsidianVaultNotFoundError,
    MalformedObsidianResponseError,
    Note,
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
def temp_vault():
    """Create a temporary Obsidian vault for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir)
        # Create some test notes
        (vault_path / "note1.md").write_text(
            "---\ntitle: Note 1\ntags: [tag1, tag2]\n---\n\nContent of note 1"
        )
        (vault_path / "note2.md").write_text(
            "---\ntitle: Note 2\ntags: [tag2, tag3]\n---\n\nContent of note 2"
        )
        subdir = vault_path / "subdir"
        subdir.mkdir()
        (subdir / "note3.md").write_text(
            "---\ntitle: Note 3\ntags: [tag3]\n---\n\nContent of note 3"
        )
        yield vault_path


@pytest.fixture
def adapter(mock_mcp_manager):
    """Create an ObsidianAdapter with mocked MCPManager (no vault)."""
    return ObsidianAdapter(
        mcp_manager=mock_mcp_manager,
        server_id="obsidian",
        vault_path=None,
        timeout_seconds=30,
    )


@pytest.fixture
def adapter_with_vault(temp_vault):
    """Create an ObsidianAdapter with filesystem vault."""
    return ObsidianAdapter(
        mcp_manager=None,
        server_id="obsidian",
        vault_path=str(temp_vault),
        timeout_seconds=30,
    )


@pytest.fixture
def adapter_no_paths():
    """Create an ObsidianAdapter without MCP or vault (for negative tests)."""
    return ObsidianAdapter(
        mcp_manager=None,
        server_id="obsidian",
        vault_path=None,
        timeout_seconds=30,
    )


# ===========================================================================
# A. Adapter Creation (3 tests)
# ===========================================================================


def test_adapter_creation_defaults(adapter):
    """Adapter instantiates with default config."""
    assert adapter.perspective == "obsidian_knowledge"
    assert adapter._server_id == "obsidian"
    assert adapter._timeout_seconds == 30
    assert adapter._connected is False  # MCP path
    assert adapter._tools_discovered is False
    assert adapter._version_counter == 0


def test_adapter_injects_mcp_and_vault(mock_mcp_manager, temp_vault):
    """Custom MCPManager and vault_path injected for testing."""
    adapter = ObsidianAdapter(
        mcp_manager=mock_mcp_manager,
        vault_path=str(temp_vault)
    )
    assert adapter._mcp_manager is mock_mcp_manager
    assert adapter._vault_path == temp_vault


def test_adapter_default_tool_raises_without_paths(adapter_no_paths):
    """_default_tool raises NotImplementedError without MCP or vault."""
    with pytest.raises(NotImplementedError):
        adapter_no_paths._default_tool("target", {})


# ===========================================================================
# B. MCP Connection (3 tests)
# ===========================================================================


@pytest.mark.asyncio
async def test_connect_success(adapter, mock_mcp_manager):
    """Connects to mock Obsidian server via MCP."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={"success": True, "result": {"tools": {}}}
    )

    result = await adapter.connect()

    assert result is True
    assert adapter._connected is True
    assert adapter._tools_discovered is True
    mock_mcp_manager.connect.assert_called_once_with("obsidian")


@pytest.mark.asyncio
async def test_connect_mcp_not_available(adapter_no_paths):
    """Missing MCPManager and no vault -> returns False, doesn't crash."""
    result = await adapter_no_paths.connect()

    assert result is False
    assert adapter_no_paths._connected is False


@pytest.mark.asyncio
async def test_disconnect(adapter, mock_mcp_manager):
    """Disconnect cleans up MCP connection."""
    # First connect
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={"success": True, "result": {"tools": {}}}
    )
    await adapter.connect()

    # Then disconnect
    await adapter.disconnect()

    assert adapter._connected is False
    assert adapter._tools_discovered is False
    mock_mcp_manager.disconnect.assert_called_once_with("obsidian")


# ===========================================================================
# C. Filesystem Fallback (3 tests)
# ===========================================================================


@pytest.mark.asyncio
async def test_fallback_search_notes(adapter_with_vault, temp_vault):
    """Filesystem fallback works for search_notes."""
    result = await adapter_with_vault.search_notes("note 1")

    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["retrieval_path"] == "filesystem_fallback"
    assert result.metrics["notes_returned"] >= 1


@pytest.mark.asyncio
async def test_fallback_get_note(adapter_with_vault, temp_vault):
    """Filesystem fallback works for get_note."""
    result = await adapter_with_vault.get_note("note1.md")

    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["found"] is True
    assert result.metrics["retrieval_path"] == "filesystem_fallback"


@pytest.mark.asyncio
async def test_fallback_list_notes(adapter_with_vault, temp_vault):
    """Filesystem fallback works for list_notes."""
    result = await adapter_with_vault.list_notes(".")

    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["retrieval_path"] == "filesystem_fallback"
    assert result.metrics["notes_returned"] >= 3


# ===========================================================================
# D. Note Operations (6 tests)
# ===========================================================================


@pytest.mark.asyncio
async def test_search_notes_via_mcp(adapter, mock_mcp_manager):
    """search_notes works via MCP path."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={
            "success": True,
            "result": {
                "notes": [
                    {"path": "note1.md", "title": "Note 1", "tags": ["tag1"]},
                ]
            },
        }
    )
    await adapter.connect()

    result = await adapter.search_notes("test")

    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["retrieval_path"] == "mcp"
    assert result.metrics["notes_returned"] == 1


@pytest.mark.asyncio
async def test_search_notes_via_mcp_then_fallback(adapter_with_vault):
    """MCP path tried first, then filesystem fallback."""
    # Mock failing MCP
    mock_mcp = MagicMock()
    mock_mcp.connect = AsyncMock(return_value=True)
    mock_mcp.call_tool = AsyncMock(side_effect=Exception("MCP down"))
    mock_mcp.disconnect = AsyncMock(return_value=None)

    adapter = ObsidianAdapter(
        mcp_manager=mock_mcp,
        server_id="obsidian",
        vault_path=str(adapter_with_vault._vault_path),
        timeout_seconds=30,
    )
    await adapter.connect()

    result = await adapter.search_notes("note")

    # Should fall back to filesystem
    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["retrieval_path"] == "filesystem_fallback"


@pytest.mark.asyncio
async def test_get_note_mcp_path(adapter, mock_mcp_manager):
    """get_note works via MCP."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={"success": True, "result": {"path": "note1.md", "title": "Note 1"}}
    )
    await adapter.connect()

    result = await adapter.get_note("note1.md")

    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["found"] is True
    assert result.metrics["retrieval_path"] == "mcp"


@pytest.mark.asyncio
async def test_list_notes_via_mcp(adapter, mock_mcp_manager):
    """list_notes works via MCP."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={
            "success": True,
            "result": {"notes": [{"path": "note1.md", "title": "Note 1"}]}
        }
    )
    await adapter.connect()

    result = await adapter.list_notes(".")

    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["retrieval_path"] == "mcp"


@pytest.mark.asyncio
async def test_read_note_via_mcp(adapter, mock_mcp_manager):
    """read_note works via MCP."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={"success": True, "result": {"path": "note1.md", "content": "body"}}
    )
    await adapter.connect()

    result = await adapter.read_note("note1.md")

    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["retrieval_path"] == "mcp"


@pytest.mark.asyncio
async def test_no_path_available_error(adapter_no_paths):
    """Returns ERROR when neither MCP nor vault configured."""
    result = await adapter_no_paths.search_notes("test")

    assert result.status == ExecutionStatus.ERROR
    findings = result.findings
    assert any(f.get("type") == "unavailable" for f in findings)


# ===========================================================================
# E. Dual-Path Tests (3 tests)
# ===========================================================================


@pytest.mark.asyncio
async def test_mcp_priority_over_fallback(adapter_with_vault):
    """MCP path takes priority when available."""
    mock_mcp = MagicMock()
    mock_mcp.connect = AsyncMock(return_value=True)
    mock_mcp.call_tool = AsyncMock(
        return_value={"success": True, "result": {"notes": [{"source": "mcp", "title": "MCP Note"}]}}
    )
    mock_mcp.disconnect = AsyncMock(return_value=None)

    adapter = ObsidianAdapter(
        mcp_manager=mock_mcp,
        server_id="obsidian",
        vault_path=str(adapter_with_vault._vault_path),
        timeout_seconds=30,
    )
    await adapter.connect()

    result = await adapter.search_notes("test")

    # Should use MCP, not fallback
    assert result.metrics["retrieval_path"] == "mcp"
    assert result.raw["notes"][0]["source"] == "mcp"


@pytest.mark.asyncio
async def test_mcp_failure_triggers_fallback(adapter_with_vault):
    """MCP failure gracefully falls back to filesystem."""
    mock_mcp = MagicMock()
    mock_mcp.connect = AsyncMock(return_value=True)
    mock_mcp.call_tool = AsyncMock(side_effect=ObsidianUnavailableError("MCP down"))
    mock_mcp.disconnect = AsyncMock(return_value=None)

    adapter = ObsidianAdapter(
        mcp_manager=mock_mcp,
        server_id="obsidian",
        vault_path=str(adapter_with_vault._vault_path),
        timeout_seconds=30,
    )
    await adapter.connect()

    result = await adapter.search_notes("note")

    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["retrieval_path"] == "filesystem_fallback"


@pytest.mark.asyncio
async def test_both_unavailable(adapter_no_paths):
    """Both paths unavailable returns ERROR."""
    result = await adapter_no_paths.get_note("note.md")

    assert result.status == ExecutionStatus.ERROR
    assert any(f.get("type") == "unavailable" for f in result.findings)


# ===========================================================================
# F. Provenance (3 tests)
# ===========================================================================


@pytest.mark.asyncio
async def test_provenance_fields_present_mcp(adapter, mock_mcp_manager):
    """MCP result includes all required provenance fields."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={"success": True, "result": {"path": "note1.md", "title": "Note 1", "content": "body", "frontmatter": {}, "tags": []}}
    )
    await adapter.connect()

    result = await adapter.get_note("note1.md")

    prov = result.raw["provenance"]
    required_fields = [
        "source", "adapter", "operation", "correlation_id",
        "execution_id", "task_id", "timestamp", "request_id",
        "version", "authority", "advisory", "trust_level",
        "retrieval_path",
    ]
    for field in required_fields:
        assert field in prov, f"Missing provenance field: {field}"


@pytest.mark.asyncio
async def test_provenance_fields_present_filesystem(adapter_with_vault):
    """Filesystem result includes all required provenance fields."""
    result = await adapter_with_vault.get_note("note1.md")

    prov = result.raw["provenance"]
    required_fields = [
        "source", "adapter", "operation", "correlation_id",
        "execution_id", "task_id", "timestamp", "request_id",
        "version", "authority", "advisory", "trust_level",
        "retrieval_path",
    ]
    for field in required_fields:
        assert field in prov, f"Missing provenance field: {field}"


@pytest.mark.asyncio
async def test_provenance_values_correct(adapter_with_vault):
    """Provenance fields have correct values for filesystem."""
    result = await adapter_with_vault.get_note("note1.md")

    prov = result.raw["provenance"]
    assert prov["source"] == "obsidian"
    assert prov["adapter"] == "obsidian_adapter"
    assert prov["operation"] == "read_note"
    assert prov["authority"] == "contextual"
    assert prov["advisory"] is True
    assert prov["trust_level"] == "trusted_contextual"
    assert prov["retrieval_path"] == "filesystem"


# ===========================================================================
# G. Advisory/C14 Marking (2 tests)
# ===========================================================================


@pytest.mark.asyncio
async def test_results_marked_advisory_mcp(adapter, mock_mcp_manager):
    """MCP retrieved data marked advisory per C14."""
    mock_mcp_manager.call_tool = AsyncMock(
        return_value={"success": True, "result": {"notes": [{"path": "p1.md"}]}}
    )
    await adapter.connect()

    result = await adapter.search_notes("test")

    for note in result.raw["notes"]:
        assert note["provenance"]["advisory"] is True
        assert note["provenance"]["authority"] == "contextual"
        assert note["provenance"]["trust_level"] == "trusted_contextual"


@pytest.mark.asyncio
async def test_results_marked_advisory_filesystem(adapter_with_vault):
    """Filesystem retrieved data marked advisory per C14."""
    result = await adapter_with_vault.search_notes("note")

    for note in result.raw["notes"]:
        assert note["provenance"]["advisory"] is True
        assert note["provenance"]["authority"] == "contextual"
        assert note["provenance"]["trust_level"] == "trusted_contextual"


# ===========================================================================
# H. Security (4 tests)
# ===========================================================================


@pytest.mark.asyncio
async def test_path_traversal_blocked_direct(adapter_with_vault):
    """Path traversal attempts raise ObsidianSecurityError via _validate_path."""
    with pytest.raises(ObsidianSecurityError, match="traversal"):
        adapter_with_vault._validate_path("../../etc/passwd")


@pytest.mark.asyncio
async def test_obsidian_dir_blocked_direct(adapter_with_vault):
    """Access to .obsidian directory raises ObsidianSecurityError."""
    with pytest.raises(ObsidianSecurityError, match=".obsidian"):
        adapter_with_vault._validate_path(".obsidian/config.json")


@pytest.mark.asyncio
async def test_rejects_sensitive_content_direct(adapter_with_vault):
    """_validate_content rejects sensitive property keys."""
    with pytest.raises(ObsidianSecurityError, match="Sensitive property"):
        adapter_with_vault._validate_content({"password": "secret123"})

    with pytest.raises(ObsidianSecurityError, match="secret detected"):
        adapter_with_vault._validate_content({"note": "key is sk-abcdefghijklmnopqrstuvwx"})


@pytest.mark.asyncio
async def test_vault_not_found_error(temp_vault):
    """Returns ERROR when vault doesn't exist."""
    bad_adapter = ObsidianAdapter(
        mcp_manager=None,
        server_id="obsidian",
        vault_path="/nonexistent/path",
        timeout_seconds=30,
    )

    result = await bad_adapter.search_notes("test")

    assert result.status == ExecutionStatus.ERROR
    assert any(f.get("type") == "unavailable" for f in result.findings)


# ===========================================================================
# I. Frontmatter Parsing (2 tests)
# ===========================================================================


@pytest.mark.asyncio
async def test_frontmatter_parsed(adapter_with_vault):
    """Frontmatter is correctly parsed from notes."""
    result = await adapter_with_vault.get_note("note1.md")

    assert result.status == ExecutionStatus.SUCCESS
    assert result.raw["frontmatter"]["title"] == "Note 1"
    assert "tag1" in result.raw["tags"]
    assert "tag2" in result.raw["tags"]


@pytest.mark.asyncio
async def test_note_without_frontmatter(adapter_with_vault):
    """Notes without frontmatter are handled."""
    (adapter_with_vault._vault_path / "no_frontmatter.md").write_text("Just content")

    result = await adapter_with_vault.get_note("no_frontmatter.md")

    assert result.status == ExecutionStatus.SUCCESS
    assert result.raw["title"] == "no_frontmatter"
    assert result.raw["frontmatter"] == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])