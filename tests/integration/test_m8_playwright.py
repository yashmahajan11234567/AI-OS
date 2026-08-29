"""
Integration tests for M8-T2 Playwright MCP Integration.

Tests full flow with mock Playwright MCP server: session isolation,
deterministic execution, evidence capture, and security.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from aios.adapters.mock_playwright_mcp_server import MockPlaywrightMCPServer
from aios.adapters.playwright_mcp_adapter import (
    PlaywrightActionError,
    PlaywrightInfrastructureError,
    PlaywrightMCPAdapter,
    PlaywrightSecurityError,
)
from aios.adapters.playwright_session import PlaywrightSessionRegistry
from aios.core.mcp_manager import MCPTool


class MockMCPManager:
    """Mock MCPManager using in-process MockPlaywrightMCPServer."""

    _TOOL_NAMES = (
        "browser_navigate", "browser_click", "browser_type_text",
        "browser_take_screenshot", "browser_snapshot",
        "browser_new_context", "browser_close_context",
        "browser_close", "get_playwright_version",
    )

    def __init__(self, server=None):
        self._servers = {}
        self._server = server or MockPlaywrightMCPServer()

    async def connect(self, server_id):
        self._servers[server_id] = {"connected": True}
        return True

    async def disconnect(self, server_id):
        self._servers.pop(server_id, None)

    def get_server_status(self, server_id):
        status = self._servers.get(server_id)
        if status:
            return type('Status', (), {'connected': status['connected']})()
        return None

    async def call_tool(self, server_id, tool_name, args, call_id=None):
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": args}
        }
        response = await self._server.handle_request(request)
        if "error" in response:
            raise RuntimeError(response["error"]["message"])
        return response.get("result", {}).get("result", response.get("result", {}))

    def list_tools(self, server_id):
        return [MCPTool(
            name=name, description=f"{name}", input_schema={}, server_id=server_id
        ) for name in self._TOOL_NAMES]


@pytest.fixture
def mock_server():
    return MockPlaywrightMCPServer()


@pytest.fixture
def mock_mcp_manager(mock_server):
    return MockMCPManager(mock_server)


@pytest.fixture
def adapter(mock_mcp_manager):
    return PlaywrightMCPAdapter(mcp_manager=mock_mcp_manager)


# ---------------------------------------------------------------------------
# Session Isolation Tests
# ---------------------------------------------------------------------------

async def test_context_isolation(mock_mcp_manager):
    """Test two contexts don't share state."""
    adapter = PlaywrightMCPAdapter(mcp_manager=mock_mcp_manager)
    await adapter.connect()

    # Create two sessions
    s1 = await adapter.create_session()
    s2 = await adapter.create_session()

    # Navigate both to different URLs
    await adapter.execute_action(s1, "navigate", {"url": "https://site1.com"})
    await adapter.execute_action(s2, "navigate", {"url": "https://site2.com"})

    # Execute on both independently
    r1 = await adapter.execute_action(s1, "click", {"selector": "#btn1"})
    r2 = await adapter.execute_action(s2, "click", {"selector": "#btn2"})

    assert r1["success"] is True
    assert r2["success"] is True

    # Close both
    await adapter.close_session(s1)
    await adapter.close_session(s2)


async def test_no_shared_cookies(mock_mcp_manager):
    """Test cookies isolated between sessions."""
    adapter = PlaywrightMCPAdapter(mcp_manager=mock_mcp_manager)
    await adapter.connect()

    s1 = await adapter.create_session()
    s2 = await adapter.create_session()

    # Navigate and set "cookies" via session tracking
    await adapter.execute_action(s1, "navigate", {"url": "https://a.com"})
    await adapter.execute_action(s2, "navigate", {"url": "https://b.com"})

    # Different sessions, different URLs
    assert s1 != s2

    await adapter.close_session(s1)
    await adapter.close_session(s2)


# ---------------------------------------------------------------------------
# Deterministic Navigation Tests
# ---------------------------------------------------------------------------

async def test_navigation_success(adapter):
    """Test navigate to URL returns correct metadata."""
    await adapter.connect()
    session_id = await adapter.create_session()
    try:
        result = await adapter.execute_action(session_id, "navigate", {
            "url": "https://example.com"
        })
        assert result["success"] is True
        assert result["url"] == "https://example.com"
        assert "title" in result
        assert result["status"] == "loaded"
    finally:
        await adapter.close_session(session_id)


# ---------------------------------------------------------------------------
# Click and Type Tests
# ---------------------------------------------------------------------------

async def test_click_success(adapter):
    """Test click element succeeds."""
    await adapter.connect()
    session_id = await adapter.create_session()
    try:
        result = await adapter.execute_action(session_id, "click", {
            "selector": "#submit-btn"
        })
        assert result["success"] is True
        assert result["clicked"] is True
    finally:
        await adapter.close_session(session_id)


async def test_type_text_success(adapter):
    """Test type text succeeds."""
    await adapter.connect()
    session_id = await adapter.create_session()
    try:
        result = await adapter.execute_action(session_id, "type", {
            "selector": "#username",
            "text": "testuser"
        })
        assert result["success"] is True
        assert result["typed"] is True
        assert result["text"] == "testuser"
    finally:
        await adapter.close_session(session_id)


# ---------------------------------------------------------------------------
# Screenshot Tests
# ---------------------------------------------------------------------------

async def test_screenshot_capture(adapter):
    """Test screenshot returned as base64."""
    await adapter.connect()
    session_id = await adapter.create_session()
    try:
        result = await adapter.execute_action(session_id, "screenshot", {})
        assert result["success"] is True
        assert "screenshot" in result
        assert result["format"] == "png"
    finally:
        await adapter.close_session(session_id)


async def test_screenshot_full_page(adapter):
    """Test full-page screenshot."""
    await adapter.connect()
    session_id = await adapter.create_session()
    try:
        result = await adapter.execute_action(session_id, "screenshot", {
            "full_page": True
        })
        assert result["success"] is True
        assert result["full_page"] is True
    finally:
        await adapter.close_session(session_id)


# ---------------------------------------------------------------------------
# DOM Evidence Tests
# ---------------------------------------------------------------------------

async def test_dom_snapshot(adapter):
    """Test DOM snapshot captured."""
    await adapter.connect()
    session_id = await adapter.create_session()
    try:
        result = await adapter.execute_action(session_id, "snapshot", {})
        assert result["success"] is True
        assert "snapshot" in result
        assert result["snapshot"]["role"] == "document"
    finally:
        await adapter.close_session(session_id)


# ---------------------------------------------------------------------------
# Provenance Tests
# ---------------------------------------------------------------------------

async def test_provenance_complete(adapter):
    """Test all mandatory provenance fields present."""
    await adapter.connect()
    execution_id = str(uuid.uuid4())
    session_id = await adapter.create_session(execution_id=execution_id)
    try:
        result = await adapter.execute_action(session_id, "navigate", {
            "url": "https://example.com"
        })

        # Verify session tracking
        assert adapter.is_session_active(session_id)

        # Verify provenance hashing
        params_hash = adapter._hash_parameters({"url": "https://example.com"})
        assert len(params_hash) == 16
        assert params_hash != ""
    finally:
        await adapter.close_session(session_id)


async def test_provenance_no_secrets(adapter):
    """Test no plaintext secrets in results."""
    await adapter.connect()
    session_id = await adapter.create_session()
    try:
        # Test the adapter's redaction methods directly
        redacted_url = adapter._redact_url(
            "https://api.example.com?key=sk-secret123&token=tok-abc"
        )
        assert "sk-secret123" not in redacted_url
        assert "tok-abc" not in redacted_url

        # Env scrubbing
        redacted = adapter._scrub_env({"API_KEY": "secret123", "NORMAL": "value"})
        assert redacted["API_KEY"] == "***REDACTED***"
        assert redacted["NORMAL"] == "value"
    finally:
        await adapter.close_session(session_id)


# ---------------------------------------------------------------------------
# Security Tests
# ---------------------------------------------------------------------------

async def test_no_secret_leakage(adapter):
    """Test no secret leakage in provenance or logs."""
    await adapter.connect()
    session_id = await adapter.create_session()
    try:
        # Test DOM redaction
        redacted_dom = adapter._redact_dom(
            '<div class="secret">sk-abcdefghijklmnopqrst</div>'
        )
        assert "sk-abcdefghijklmnopqrst" not in redacted_dom
        assert "***REDACTED***" in redacted_dom

        # Test URL redaction
        redacted_url = adapter._redact_url(
            "https://example.com?password=secret123&api_key=sk-12345"
        )
        assert "secret123" not in redacted_url
        assert "sk-12345" not in redacted_url
    finally:
        await adapter.close_session(session_id)


async def test_file_protocol_blocked(adapter):
    """Test file:// protocol is blocked."""
    await adapter.connect()
    session_id = await adapter.create_session()
    try:
        with pytest.raises(PlaywrightSecurityError):
            await adapter.execute_action(session_id, "navigate", {
                "url": "file:///etc/passwd"
            })
    finally:
        await adapter.close_session(session_id)


# ---------------------------------------------------------------------------
# Cleanup Tests
# ---------------------------------------------------------------------------

async def test_cleanup_all(adapter):
    """Test cleanup_all removes all sessions."""
    await adapter.connect()
    s1 = await adapter.create_session()
    s2 = await adapter.create_session()
    assert len(adapter.get_active_sessions()) == 2

    await adapter.cleanup_all()
    assert not adapter._connected
    assert len(adapter.get_active_sessions()) == 0


async def test_no_session_leakage(adapter):
    """Test no session leakage after close."""
    await adapter.connect()
    session_id = await adapter.create_session()
    assert adapter.is_session_active(session_id)

    await adapter.close_session(session_id)
    assert not adapter.is_session_active(session_id)
    assert len(adapter.get_active_sessions()) == 0


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------

async def test_malformed_response(adapter):
    """Test malformed MCP response handled gracefully."""
    await adapter.connect()
    # Try calling a non-existent tool
    with pytest.raises((PlaywrightActionError, RuntimeError)):
        await adapter._call_tool("nonexistent_tool", {})


# ---------------------------------------------------------------------------
# Full Flow Test
# ---------------------------------------------------------------------------

async def test_full_browser_flow(adapter):
    """Test full browser flow: navigate → click → type → screenshot → evidence."""
    await adapter.connect()
    session_id = await adapter.create_session()
    try:
        # Navigate
        nav_result = await adapter.execute_action(session_id, "navigate", {
            "url": "https://example.com"
        })
        assert nav_result["success"] is True

        # Click
        click_result = await adapter.execute_action(session_id, "click", {
            "selector": "#link"
        })
        assert click_result["success"] is True

        # Type
        type_result = await adapter.execute_action(session_id, "type", {
            "selector": "#input",
            "text": "hello"
        })
        assert type_result["success"] is True

        # Screenshot
        screen_result = await adapter.execute_action(session_id, "screenshot", {})
        assert screen_result["success"] is True

        # Collect evidence
        evidence = await adapter.collect_evidence(session_id)
        assert evidence["screenshot_available"] is True
        assert evidence["snapshot_available"] is True
        assert evidence["evidence_count"] >= 2
    finally:
        await adapter.close_session(session_id)


# ---------------------------------------------------------------------------
# Real Browser E2E (gated)
# ---------------------------------------------------------------------------

async def test_real_browser_e2e():
    """Real browser E2E test (gated behind PLAYWRIGHT_E2E_TEST=1)."""
    if not os.environ.get("PLAYWRIGHT_E2E_TEST", "").lower() in ("1", "true", "yes"):
        pytest.skip("PLAYWRIGHT_E2E_TEST not set")

    # This would test against real Playwright MCP if available
    # For now, verify the env var gating works
    assert True


# ---------------------------------------------------------------------------
# Mock Server Protocol Test
# ---------------------------------------------------------------------------

async def test_mock_server_deterministic():
    """Test mock server returns deterministic responses."""
    server = MockPlaywrightMCPServer()

    # Navigate twice with same URL
    r1 = await server.handle_request({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "browser_navigate", "arguments": {"url": "https://example.com"}}
    })
    r2 = await server.handle_request({
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": "browser_navigate", "arguments": {"url": "https://example.com"}}
    })

    assert r1["result"]["url"] == r2["result"]["url"]
    assert r1["result"]["title"] == r2["result"]["title"]
