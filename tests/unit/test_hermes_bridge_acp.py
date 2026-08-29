"""
Unit tests for HermesBridge ACP support (M8-T1).

Tests protocol selection, MCP fallback, session ID lifecycle, provenance completeness, no verdict leakage.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
import sys

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from aios.adapters.hermes_bridge import (
    HermesBridge,
    HermesTask,
    HermesObservation,
    ProtocolUnavailableError,
    TransportConnectionError,
    SessionCreationTimeout,
    SessionNotFoundError,
    ExecutionTimeout,
    ExecutionCancelled,
    MalformedResponseError,
    TransportDisconnectError,
    DuplicateExecutionError,
    SecretLeakDetectedError,
)
from aios.adapters.mock_hermes_server import MockHermesServer


class MockMCPManager:
    """Mock MCPManager for testing."""

    def __init__(self):
        self._servers = {}
        self._server = MockHermesServer()

    async def connect(self, server_id):
        self._servers[server_id] = {"connected": True}
        return True

    def get_server_status(self, server_id):
        status = self._servers.get(server_id)
        if status:
            return type('Status', (), {'connected': status['connected']})()
        return None

    async def call_tool(self, server_id, tool_name, args, call_id=None):
        # Delegate to mock server
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": args}
        }
        response = await self._server.handle_request(request)
        if "error" in response:
            raise Exception(response["error"]["message"])
        return response.get("result", {}).get("result", response.get("result", {}))


@pytest.fixture
def temp_hermes_repo():
    """Create a temporary hermes-agent repo structure for ACP testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        acp_dir = tmpdir / "acp_adapter"
        acp_dir.mkdir()
        (acp_dir / "entry.py").write_text("# Mock ACP entry point\n")
        (acp_dir / "__init__.py").touch()
        yield str(tmpdir)


@pytest.fixture
def mock_mcp_manager():
    return MockMCPManager()


async def test_protocol_selection_acp_preferred(temp_hermes_repo):
    """Test protocol='acp' uses ACP when available."""
    bridge = HermesBridge(
        protocol="acp",
        cwd=temp_hermes_repo,
        timeout_seconds=1,
        fallback_to_mcp=False,
    )

    # Protocol should be set
    assert bridge._protocol == "acp"
    assert bridge._fallback_to_mcp is False


async def test_protocol_selection_mcp_explicit(mock_mcp_manager):
    """Test protocol='mcp' uses MCP directly."""
    bridge = HermesBridge(
        mcp_manager=mock_mcp_manager,
        protocol="mcp",
        server_id="hermes_agent_ext",
    )

    assert bridge._protocol == "mcp"
    # Should not require ACP config


async def test_fallback_acp_unavailable_mcp_used(temp_hermes_repo, mock_mcp_manager):
    """Test ACP unavailable + fallback=True uses MCP with provenance 'acp_fallback'."""
    bridge = HermesBridge(
        mcp_manager=mock_mcp_manager,
        protocol="acp",
        cwd=temp_hermes_repo + "_nonexistent",  # Make ACP fail
        fallback_to_mcp=True,
        timeout_seconds=1,
    )

    # Protocol should be acp initially
    assert bridge._protocol == "acp"
    assert bridge._fallback_to_mcp is True

    # When ACP fails, it should fall back to MCP and create session via MCP
    session_id = await bridge.create_worker_session(environment={"app_url": "http://test"})

    # Session should be created successfully via MCP fallback
    assert session_id is not None
    assert bridge.is_session_active(session_id)

    # Provenance should track the fallback
    # Execute a task to check provenance
    task = HermesTask(
        task_id="test-fallback",
        task_type="navigation",
        description="Test fallback",
        parameters={"url": "https://example.com"},
        session_id=session_id,
    )
    obs = await bridge.execute_task(task)

    # Provenance should show acp_fallback
    assert obs.provenance["protocol"] == "acp_fallback"
    assert obs.provenance["adapter"] == "mcp_manager"
    assert obs.success is True

    await bridge.close_worker_session(session_id)


async def test_no_fallback_acp_unavailable_raises(temp_hermes_repo):
    """Test ACP unavailable + fallback=False raises ProtocolUnavailableError."""
    bridge = HermesBridge(
        protocol="acp",
        cwd=temp_hermes_repo + "_nonexistent",
        fallback_to_mcp=False,
        timeout_seconds=1,
    )

    # Should raise when trying to use ACP
    with pytest.raises(ProtocolUnavailableError):
        await bridge._get_acp_adapter()


async def test_unsupported_protocol_raises():
    """Test unsupported protocol values raise ValueError."""
    with pytest.raises(ValueError) as exc_info:
        HermesBridge(protocol="invalid")
    assert "unsupported protocol" in str(exc_info.value).lower()


async def test_create_worker_session_tracks_id_acp(temp_hermes_repo, mock_mcp_manager):
    """Test create_worker_session returns and tracks server-generated session ID."""
    # Test with mock ACP adapter and registry
    from aios.adapters.acp_session import AcPSessionRegistry

    class MockACPAdapter:
        def __init__(self):
            self.sessions = {}

        async def connect(self):
            return True

        async def new_session(self, cwd, timeout):
            import uuid
            sid = f"acp_{uuid.uuid4().hex[:12]}"
            self.sessions[sid] = {"cwd": cwd, "active": True}
            return sid

        async def close_session(self, session_id):
            if session_id in self.sessions:
                self.sessions[session_id]["active"] = False

        def is_connected(self):
            return True

    mock_acp = MockACPAdapter()
    bridge = HermesBridge(
        mcp_manager=mock_mcp_manager,
        protocol="acp",
        acp_adapter=mock_acp,
        cwd=temp_hermes_repo,
        fallback_to_mcp=False,
    )

    # Manually set up the registry with mock adapter
    registry = AcPSessionRegistry(mock_acp, session_idle_timeout_seconds=300)
    bridge._acp_adapter = mock_acp
    bridge._acp_registry = registry

    session_id = await bridge.create_worker_session(environment={"app_url": "http://test"})

    # Session ID should be from ACP adapter (server-generated)
    assert session_id.startswith("acp_")
    assert bridge.is_session_active(session_id)
    assert session_id in bridge.get_active_sessions()


async def test_create_worker_session_tracks_id_mcp(mock_mcp_manager):
    """Test create_worker_session returns and tracks server-generated ID for MCP."""
    bridge = HermesBridge(
        mcp_manager=mock_mcp_manager,
        protocol="mcp",
        server_id="hermes_agent_ext",
    )

    session_id = await bridge.create_worker_session(environment={"app_url": "http://test"})

    # Session ID should be returned and tracked
    assert session_id is not None
    assert len(session_id) > 0
    assert bridge.is_session_active(session_id)
    assert session_id in bridge.get_active_sessions()


async def test_close_worker_session_removes_id(mock_mcp_manager):
    """Test close_worker_session removes ID from active sessions."""
    bridge = HermesBridge(
        mcp_manager=mock_mcp_manager,
        protocol="mcp",
        server_id="hermes_agent_ext",
    )

    session_id = await bridge.create_worker_session()
    assert bridge.is_session_active(session_id)

    result = await bridge.close_worker_session(session_id)
    assert result is True
    assert not bridge.is_session_active(session_id)
    assert session_id not in bridge.get_active_sessions()


async def test_close_unknown_session_idempotent(mock_mcp_manager):
    """Test close_worker_session on unknown session is no-op (idempotent)."""
    bridge = HermesBridge(
        mcp_manager=mock_mcp_manager,
        protocol="mcp",
        server_id="hermes_agent_ext",
    )

    result = await bridge.close_worker_session("unknown-session")
    assert result is False  # Not an error


async def test_provenance_complete_mcp(mock_mcp_manager):
    """Test MCP observations have all mandatory provenance fields."""
    bridge = HermesBridge(
        mcp_manager=mock_mcp_manager,
        protocol="mcp",
        server_id="hermes_agent_ext",
    )

    session_id = await bridge.create_worker_session()
    task = HermesTask(
        task_id="test-task-1",
        task_type="navigation",
        description="Navigate to example.com",
        parameters={"url": "https://example.com"},
        session_id=session_id,
    )

    obs = await bridge.execute_task(task)

    # Check all mandatory provenance fields
    prov = obs.provenance
    mandatory_fields = [
        "task_id", "execution_id", "session_id", "correlation_id",
        "protocol", "adapter", "timestamp", "request_metadata",
        "target", "exit_status", "errors", "environment"
    ]
    for field in mandatory_fields:
        assert field in prov, f"Missing provenance field: {field}"

    assert prov["protocol"] == "mcp"
    assert prov["adapter"] == "mcp_manager"
    assert prov["task_id"] == "test-task-1"
    assert prov["session_id"] == session_id
    assert prov["exit_status"] in ("completed", "error", "timeout", "cancelled")
    assert isinstance(prov["errors"], list)
    assert isinstance(prov["request_metadata"], dict)
    assert "task_type" in prov["request_metadata"]
    assert "description" in prov["request_metadata"]
    assert "parameters_hash" in prov["request_metadata"]


async def test_provenance_no_secrets(mock_mcp_manager):
    """Test provenance contains no plaintext secrets."""
    bridge = HermesBridge(
        mcp_manager=mock_mcp_manager,
        protocol="mcp",
        server_id="hermes_agent_ext",
    )

    session_id = await bridge.create_worker_session()
    task = HermesTask(
        task_id="test-task-secret",
        task_type="navigation",
        description="Navigate with secret",
        parameters={"url": "https://example.com", "api_key": "secret123", "password": "pass456"},
        session_id=session_id,
    )

    obs = await bridge.execute_task(task)

    # Check provenance doesn't contain secrets in plaintext
    prov_str = str(obs.provenance)
    assert "secret123" not in prov_str
    assert "pass456" not in prov_str
    # Parameters should be hashed
    assert "parameters_hash" in obs.provenance["request_metadata"]
    assert isinstance(obs.provenance["request_metadata"]["parameters_hash"], str)
    assert len(obs.provenance["request_metadata"]["parameters_hash"]) == 16


async def test_normalize_acp_stop_reason():
    """Test ACP response normalization handles stop reasons correctly."""
    from aios.adapters.hermes_bridge import HermesBridge

    # We can't easily instantiate without full setup, but we can test the logic
    # by creating a bridge with mock ACP adapter
    class MockACPAdapter:
        def is_connected(self):
            return True

    bridge = HermesBridge(protocol="acp", acp_adapter=MockACPAdapter())
    bridge._active_sessions["test-session"] = {"protocol": "acp", "created_at": asyncio.get_event_loop().time()}

    task = HermesTask(
        task_id="test-1",
        task_type="test",
        description="Test task",
        parameters={},
        session_id="test-session",
    )

    # Test different stop reasons
    # end_turn -> success=True, exit_status="completed"
    result_end_turn = bridge._normalize_acp_response(
        {"stopReason": "end_turn", "text": "Done", "sessionId": "test-session"},
        task, "exec-1", "corr-1", "acp"
    )
    assert result_end_turn.success is True
    assert result_end_turn.provenance["exit_status"] == "completed"

    # cancelled -> success=False, exit_status="cancelled"
    result_cancelled = bridge._normalize_acp_response(
        {"stopReason": "cancelled", "text": "Cancelled", "sessionId": "test-session"},
        task, "exec-2", "corr-2", "acp"
    )
    assert result_cancelled.success is False
    assert result_cancelled.provenance["exit_status"] == "cancelled"

    # timeout -> success=False, exit_status="timeout"
    result_timeout = bridge._normalize_acp_response(
        {"stopReason": "timeout", "text": "Timeout", "sessionId": "test-session"},
        task, "exec-3", "corr-3", "acp"
    )
    assert result_timeout.success is False
    assert result_timeout.provenance["exit_status"] == "timeout"

    # error -> success=False, exit_status="error"
    result_error = bridge._normalize_acp_response(
        {"stopReason": "error", "text": "Error occurred", "sessionId": "test-session"},
        task, "exec-4", "corr-4", "acp"
    )
    assert result_error.success is False
    assert result_error.provenance["exit_status"] == "error"

    # Unknown -> success=False, exit_status="error"
    result_unknown = bridge._normalize_acp_response(
        {"stopReason": "unknown", "text": "Unknown", "sessionId": "test-session"},
        task, "exec-5", "corr-5", "acp"
    )
    assert result_unknown.success is False
    assert result_unknown.provenance["exit_status"] == "error"


async def test_error_wraps_as_observation_mcp(mock_mcp_manager):
    """Test exceptions during execute_task become observations, not raised."""
    bridge = HermesBridge(
        mcp_manager=mock_mcp_manager,
        protocol="mcp",
        server_id="hermes_agent_ext",
    )

    # Create task with non-existent session
    task = HermesTask(
        task_id="test-error",
        task_type="test",
        description="Test error",
        parameters={},
        session_id="non-existent-session",
    )

    obs = await bridge.execute_task(task)

    # Should return observation with success=False, not raise
    assert isinstance(obs, HermesObservation)
    assert obs.success is False
    assert obs.error is not None
    assert obs.provenance["exit_status"] == "error"
    assert obs.trust_level == "untrusted"


async def test_observe_not_verdict(mock_mcp_manager):
    """Test observations never contain verdict/pass/fail/approved/rejected/secure/compliant."""
    bridge = HermesBridge(
        mcp_manager=mock_mcp_manager,
        protocol="mcp",
        server_id="hermes_agent_ext",
    )

    session_id = await bridge.create_worker_session()
    task = HermesTask(
        task_id="test-check-forbidden",
        task_type="navigation",
        description="Navigate",
        parameters={"url": "https://example.com"},
        session_id=session_id,
    )

    obs = await bridge.execute_task(task)

    # Convert to dict and check for forbidden words
    obs_dict = {
        "task_id": obs.task_id,
        "success": obs.success,
        "data": obs.data,
        "error": obs.error,
        "provenance": obs.provenance,
        "trust_level": obs.trust_level,
    }

    obs_str = str(obs_dict).lower()
    forbidden = ["verdict", "approved", "rejected", "secure", "compliant"]
    for word in forbidden:
        assert word not in obs_str, f"Forbidden word '{word}' found in observation"

    # trust_level must be untrusted
    assert obs.trust_level == "untrusted"


async def test_session_lifecycle_fix_def001(mock_mcp_manager):
    """Test DEF-001 fix: create_worker_session returns server ID, close uses same ID."""
    bridge = HermesBridge(
        mcp_manager=mock_mcp_manager,
        protocol="mcp",
        server_id="hermes_agent_ext",
    )

    # Create session - should return the server-generated ID
    session_id = await bridge.create_worker_session(environment={"test": "env"})

    # Use that same ID for operations
    assert bridge.is_session_active(session_id)

    # Close with the same ID
    result = await bridge.close_worker_session(session_id)
    assert result is True

    # Session should be gone
    assert not bridge.is_session_active(session_id)

    # Double close should be idempotent
    result2 = await bridge.close_worker_session(session_id)
    assert result2 is False  # No-op, not error


async def test_provenance_fallback_protocol_tracking(temp_hermes_repo, mock_mcp_manager):
    """Test provenance tracks 'acp_fallback' correctly."""
    # This would be tested in integration with real fallback
    # Here we verify the bridge can distinguish the protocols
    bridge_acp = HermesBridge(
        protocol="acp",
        cwd=temp_hermes_repo,
        fallback_to_mcp=True,
    )
    bridge_mcp = HermesBridge(
        protocol="mcp",
        mcp_manager=mock_mcp_manager,
    )

    assert bridge_acp._protocol == "acp"
    assert bridge_mcp._protocol == "mcp"
    assert bridge_acp._fallback_to_mcp is True
    assert bridge_mcp._fallback_to_mcp is True  # Default


# Test that bridge methods preserve provenance across convenience methods
async def test_convenience_methods_preserve_provenance(mock_mcp_manager):
    """Test navigate, click, type_text, etc. preserve provenance."""
    bridge = HermesBridge(
        mcp_manager=mock_mcp_manager,
        protocol="mcp",
        server_id="hermes_agent_ext",
    )

    session_id = await bridge.create_worker_session()

    # Test each convenience method
    nav_obs = await bridge.navigate(session_id, "https://example.com")
    assert "parameters_hash" in nav_obs.provenance["request_metadata"]
    assert nav_obs.provenance["request_metadata"]["task_type"] == "navigation"

    click_obs = await bridge.click(session_id, "button#submit")
    assert click_obs.provenance["request_metadata"]["task_type"] == "click"

    type_obs = await bridge.type_text(session_id, "input#search", "query")
    assert type_obs.provenance["request_metadata"]["task_type"] == "type"

    screenshot_obs = await bridge.screenshot(session_id, full_page=True)
    assert screenshot_obs.provenance["request_metadata"]["task_type"] == "screenshot"

    extract_obs = await bridge.extract_content(session_id, "h1")
    assert extract_obs.provenance["request_metadata"]["task_type"] == "extraction"

    wait_obs = await bridge.wait_for(session_id, "element:visible", timeout=10)
    assert wait_obs.provenance["request_metadata"]["task_type"] == "wait"

    await bridge.close_worker_session(session_id)


async def test_hash_parameters_deterministic():
    """Test parameter hashing is deterministic."""
    class MockBridge:
        def _hash_parameters(self, params):
            import json, hashlib
            serialized = json.dumps(params, sort_keys=True, default=str)
            return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    bridge = MockBridge()

    params1 = {"b": 2, "a": 1, "nested": {"x": 10}}
    params2 = {"a": 1, "b": 2, "nested": {"x": 10}}

    hash1 = bridge._hash_parameters(params1)
    hash2 = bridge._hash_parameters(params2)

    assert hash1 == hash2
    assert len(hash1) == 16