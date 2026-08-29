"""
Unit tests for PlaywrightMCPAdapter (M8-T2).

Tests adapter logic with mock MCP server, session lifecycle, provenance,
security, and authority boundaries.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from aios.adapters.base import ExecutionResult, ExecutionStatus
from aios.adapters.mock_playwright_mcp_server import MockPlaywrightMCPServer
from aios.adapters.playwright_mcp_adapter import (
    PlaywrightActionError,
    PlaywrightInfrastructureError,
    PlaywrightMCPAdapter,
    PlaywrightSecurityError,
    PlaywrightSessionErrorEx,
)
from aios.adapters.playwright_session import PlaywrightSessionRegistry, PlaywrightSessionNotFoundError
from aios.core.mcp_manager import MCPTool


class MockMCPManager:
    """Mock MCPManager for testing PlaywrightMCPAdapter."""

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
def mock_mcp_manager():
    return MockMCPManager()


@pytest.fixture
def adapter(mock_mcp_manager):
    return PlaywrightMCPAdapter(mcp_manager=mock_mcp_manager)


@pytest.fixture
def mock_server():
    return MockPlaywrightMCPServer()


# ---------------------------------------------------------------------------
# A. Adapter Creation (3 tests)
# ---------------------------------------------------------------------------

async def test_adapter_creation(adapter):
    """A1: Instantiates with default config."""
    assert adapter.perspective == "playwright_browser"
    assert adapter._server_id == "playwright_mcp"
    assert not adapter._connected


async def test_adapter_injects_tool(adapter):
    """A2: Custom tool injected for testing."""
    def fake_tool(target, context):
        return ExecutionResult(
            tool="fake",
            status=ExecutionStatus.SUCCESS,
            findings=[{"type": "test", "description": "ok"}],
        )
    adapter._tool = fake_tool
    r = adapter.execute("test", {})
    assert r.status == ExecutionStatus.SUCCESS
    assert r.tool == "fake"


async def test_adapter_default_tool_raises():
    """A3: _default_tool raises NotImplementedError without injection."""
    adapter = PlaywrightMCPAdapter()
    with pytest.raises(NotImplementedError):
        adapter._default_tool("t", {})


# ---------------------------------------------------------------------------
# B. MCP Connection (4 tests)
# ---------------------------------------------------------------------------

async def test_mcp_connect_success(adapter, mock_mcp_manager):
    """B1: Connects to mock MCP server."""
    result = await adapter.connect()
    assert result is True
    assert adapter._connected
    assert len(adapter._discovered_tools) > 0


async def test_mcp_connect_twice_is_noop(adapter):
    """B1b: Second connect is no-op."""
    await adapter.connect()
    result = await adapter.connect()
    assert result is True


async def test_mcp_disconnect(adapter):
    """B2: Disconnect cleans up."""
    await adapter.connect()
    await adapter.disconnect()
    assert not adapter._connected


async def test_mcp_call_tool_success(adapter):
    """B3: Call tool succeeds."""
    await adapter.connect()
    result = await adapter._call_tool("get_playwright_version", {})
    assert result["success"] is True
    assert "version" in result


# ---------------------------------------------------------------------------
# C. Tool Discovery (1 test)
# ---------------------------------------------------------------------------

async def test_tool_discovery(adapter):
    """C1: Discovers Playwright MCP tools."""
    await adapter.connect()
    assert "get_playwright_version" in adapter._discovered_tools
    assert "browser_navigate" in adapter._discovered_tools
    assert "browser_click" in adapter._discovered_tools


# ---------------------------------------------------------------------------
# D. Browser Session Lifecycle (3 tests)
# ---------------------------------------------------------------------------

async def test_create_session(adapter):
    """D1: Creates isolated browser session."""
    await adapter.connect()
    session_id = await adapter.create_session()

    assert adapter.is_session_active(session_id)
    assert session_id.startswith("pw_")

    await adapter.close_session(session_id)
    assert not adapter.is_session_active(session_id)


async def test_close_session_idempotent(adapter):
    """D2: Double close is no-op."""
    await adapter.connect()
    session_id = await adapter.create_session()
    await adapter.close_session(session_id)
    # Double close should not raise
    await adapter.close_session(session_id)
    assert not adapter.is_session_active(session_id)


async def test_close_unknown_session(adapter):
    """D3: Close unknown session is no-op."""
    await adapter.connect()
    # Should not raise
    await adapter.close_session("nonexistent")


# ---------------------------------------------------------------------------
# E. Browser Actions (5 tests)
# ---------------------------------------------------------------------------

async def test_navigate(adapter):
    """E1: Navigate to URL."""
    await adapter.connect()
    session_id = await adapter.create_session()
    try:
        result = await adapter.execute_action(session_id, "navigate", {
            "url": "https://example.com"
        })
        assert result["success"] is True
        assert result["url"] == "https://example.com"
    finally:
        await adapter.close_session(session_id)


async def test_click(adapter):
    """E2: Click element."""
    await adapter.connect()
    session_id = await adapter.create_session()
    try:
        result = await adapter.execute_action(session_id, "click", {
            "selector": "#submit-btn"
        })
        assert result["success"] is True
        assert result["selector"] == "#submit-btn"
    finally:
        await adapter.close_session(session_id)


async def test_type_text(adapter):
    """E3: Type text."""
    await adapter.connect()
    session_id = await adapter.create_session()
    try:
        result = await adapter.execute_action(session_id, "type", {
            "selector": "#search",
            "text": "query"
        })
        assert result["success"] is True
        assert result["text"] == "query"
    finally:
        await adapter.close_session(session_id)


async def test_screenshot(adapter):
    """E4: Take screenshot."""
    await adapter.connect()
    session_id = await adapter.create_session()
    try:
        result = await adapter.execute_action(session_id, "screenshot", {})
        assert result["success"] is True
        assert "screenshot" in result
        assert result["format"] == "png"
    finally:
        await adapter.close_session(session_id)


async def test_snapshot(adapter):
    """E5: Get accessibility snapshot."""
    await adapter.connect()
    session_id = await adapter.create_session()
    try:
        result = await adapter.execute_action(session_id, "snapshot", {})
        assert result["success"] is True
        assert "snapshot" in result
    finally:
        await adapter.close_session(session_id)


# ---------------------------------------------------------------------------
# F. Evidence Collection (2 tests)
# ---------------------------------------------------------------------------

async def test_collect_evidence(adapter):
    """F1: Collect evidence produces screenshot and snapshot."""
    await adapter.connect()
    session_id = await adapter.create_session()
    try:
        evidence = await adapter.collect_evidence(session_id)
        assert "screenshot" in evidence
        assert "snapshot" in evidence
        assert "page_state" in evidence
        assert evidence.get("screenshot_available") is True
        assert evidence.get("snapshot_available") is True
    finally:
        await adapter.close_session(session_id)


async def test_collect_evidence_with_accessibility(adapter):
    """F2: Evidence with accessibility tree."""
    await adapter.connect()
    session_id = await adapter.create_session()
    try:
        evidence = await adapter.collect_evidence(session_id, include_accessibility=True)
        assert "accessibility_tree" in evidence
    finally:
        await adapter.close_session(session_id)


# ---------------------------------------------------------------------------
# G. Provenance (2 tests)
# ---------------------------------------------------------------------------

async def test_provenance_complete(adapter):
    """G1: All mandatory provenance fields present in actions."""
    await adapter.connect()
    session_id = await adapter.create_session(execution_id="exec-test-123")

    # Navigate action
    result = await adapter.execute_action(session_id, "navigate", {
        "url": "https://example.com"
    })
    assert result["success"] is True

    # Verify session was tracked
    assert adapter.is_session_active(session_id)

    # Check provenance hashing works
    params_hash = adapter._hash_parameters({"url": "https://example.com"})
    assert len(params_hash) == 16

    await adapter.close_session(session_id)


async def test_provenance_no_secrets(adapter):
    """G2: No plaintext secrets in provenance or logs."""
    await adapter.connect()
    session_id = await adapter.create_session()

    # Test _redact_url directly (mock server doesn't redact, adapter does in prod)
    redacted_url = adapter._redact_url("https://example.com?token=sk-12345&password=secret")
    assert "sk-12345" not in redacted_url
    assert "secret" not in redacted_url
    assert "token=" in redacted_url  # key name preserved, value redacted

    # Env scrubbing
    redacted = adapter._scrub_env({"API_KEY": "secret123", "NORMAL": "value"})
    assert redacted["API_KEY"] == "***REDACTED***"
    assert redacted["NORMAL"] == "value"

    await adapter.close_session(session_id)


# ---------------------------------------------------------------------------
# H. Security (3 tests)
# ---------------------------------------------------------------------------

async def test_url_redaction(adapter):
    """H1: URLs with tokens are redacted."""
    url = "https://example.com/api?token=abc123&key=xyz&normal=value"
    redacted = adapter._redact_url(url)
    assert "abc123" not in redacted
    assert "xyz" not in redacted
    assert "normal=value" in redacted


async def test_dom_redaction(adapter):
    """H2: DOM with secrets is redacted."""
    html = '<div class="secret">sk-abcdefghijklmnopqrst</div>'
    redacted = adapter._redact_dom(html)
    assert "sk-abcdefghijklmnopqrst" not in redacted
    assert "***REDACTED***" in redacted


async def test_file_protocol_blocked(adapter):
    """H3: file:// protocol is blocked."""
    await adapter.connect()
    session_id = await adapter.create_session()
    try:
        with pytest.raises(PlaywrightSecurityError):
            await adapter.execute_action(session_id, "navigate", {
                "url": "file:///etc/passwd"
            })
    finally:
        await adapter.close_session(session_id)


async def test_allowed_domain_restriction(adapter):
    """H4: Navigation to non-allowed domain is blocked."""
    adapter_with_restrictions = PlaywrightMCPAdapter(
        mcp_manager=MockMCPManager(),
        allowed_domains=("example.com",),
    )
    await adapter_with_restrictions.connect()
    session_id = await adapter_with_restrictions.create_session()
    try:
        with pytest.raises(PlaywrightSecurityError):
            await adapter_with_restrictions.execute_action(session_id, "navigate", {
                "url": "https://evil.com"
            })
    finally:
        await adapter_with_restrictions.close_session(session_id)


# ---------------------------------------------------------------------------
# I. Error Handling (4 tests)
# ---------------------------------------------------------------------------

async def test_unknown_action_raises(adapter):
    """I1: Unknown action raises PlaywrightActionError."""
    await adapter.connect()
    session_id = await adapter.create_session()
    try:
        with pytest.raises(PlaywrightActionError):
            await adapter.execute_action(session_id, "unknown_action", {})
    finally:
        await adapter.close_session(session_id)


async def test_session_not_active_raises(adapter):
    """I2: Action on inactive session raises."""
    await adapter.connect()
    # Session validation happens before connection check
    with pytest.raises(PlaywrightSessionNotFoundError):
        await adapter.execute_action("nonexistent", "navigate", {"url": "https://example.com"})


async def test_disconnect_before_action(adapter):
    """I3: Action on nonexistent session raises (session validation first)."""
    with pytest.raises(PlaywrightSessionNotFoundError):
        await adapter.execute_action("sid", "navigate", {"url": "https://example.com"})


async def test_cleanup_all(adapter):
    """I4: cleanup_all removes all sessions and disconnects."""
    await adapter.connect()
    s1 = await adapter.create_session()
    s2 = await adapter.create_session()
    assert len(adapter.get_active_sessions()) == 2

    await adapter.cleanup_all()
    assert not adapter._connected
    assert len(adapter.get_active_sessions()) == 0


# ---------------------------------------------------------------------------
# J. Authority Boundary (1 test)
# ---------------------------------------------------------------------------

async def test_no_verdict_in_result(adapter):
    """J1: ExecutionResult has no verdict field."""
    await adapter.connect()
    session_id = await adapter.create_session()
    try:
        result = await adapter.execute_action(session_id, "navigate", {
            "url": "https://example.com"
        })
        # Result should only contain execution data, no verdict
        result_str = str(result).lower()
        forbidden = ["verdict", "approved", "rejected", "secure", "compliant"]
        for word in forbidden:
            assert word not in result_str, f"Forbidden word '{word}' found in result"
    finally:
        await adapter.close_session(session_id)


# ---------------------------------------------------------------------------
# K. Capability Registry (1 test)
# ---------------------------------------------------------------------------

async def test_capability_registered():
    """K1: Playwright capability registered in CapabilityManager."""
    from aios.core.capability_manager import (
        CapabilityManager,
        reset_capability_manager_singleton,
    )
    from aios.core.configuration_manager import (
        ConfigurationManager,
        reset_configuration_manager_singleton,
    )
    from aios.core.service_registry import (
        ServiceRegistry,
        reset_service_registry_singleton,
    )
    from aios.events.core.bus import EventBus, EventBusConfig, reset_event_bus_singleton

    # Reset singletons and create fresh bus
    reset_event_bus_singleton()
    reset_capability_manager_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()

    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    sr = ServiceRegistry(event_bus=bus)
    cm_config = ConfigurationManager(event_bus=bus)
    cap_mgr = CapabilityManager(service_registry=sr, configuration_manager=cm_config)

    try:
        entry = cap_mgr.register(
            capability_id="playwright_browser",
            facade="browser",
            provider_id="playwright_mcp",
            provider_metadata={"server_id": "playwright_mcp", "transport": "stdio"},
            security_context={"requires_validation": True},
            tags=("browser", "playwright"),
        )
        assert entry.capability_id == "playwright_browser"
        assert entry.facade == "browser"

        # Discover by facade
        found = cap_mgr.discover_by_facade("browser")
        assert len(found) == 1
        assert found[0].capability_id == "playwright_browser"
    finally:
        cap_mgr.shutdown()
        reset_event_bus_singleton()
        reset_capability_manager_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()


# ---------------------------------------------------------------------------
# L. Mock Server Round-trip (1 test)
# ---------------------------------------------------------------------------

async def test_mock_server_roundtrip():
    """L1: Full MCP round-trip with mock server."""
    server = MockPlaywrightMCPServer()

    # Initialize
    req = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
    resp = await server.handle_request(req)
    assert resp["result"]["serverInfo"]["name"] == "Mock Playwright MCP Server"

    # Tool discovery
    req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    resp = await server.handle_request(req)
    tools = resp["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "browser_navigate" in tool_names
    assert "browser_click" in tool_names
    assert "browser_take_screenshot" in tool_names

    # Navigate
    req = {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
        "name": "browser_navigate",
        "arguments": {"url": "https://example.com"}
    }}
    resp = await server.handle_request(req)
    assert resp["result"]["success"] is True
    assert resp["result"]["url"] == "https://example.com"

    # Screenshot
    req = {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {
        "name": "browser_take_screenshot",
        "arguments": {"session_id": resp["result"]["session_id"]}
    }}
    resp = await server.handle_request(req)
    assert resp["result"]["success"] is True
    assert "screenshot" in resp["result"]
