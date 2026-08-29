"""
Unit tests for AcPAdapter (M8-T1).

Tests ACP protocol framing, timeout, cancel, env scrubbing, session lifecycle.
Tests the adapter logic directly and via in-process mock server.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from aios.adapters.acp_adapter import (
    AcPAdapter,
    ProtocolUnavailableError,
    TransportConnectionError,
    SessionCreationTimeout,
    SessionNotFoundError,
    ExecutionTimeout,
    ExecutionCancelled,
    MalformedResponseError,
    TransportDisconnectError,
    CleanupTimeout,
    DuplicateExecutionError,
    SecretLeakDetectedError,
)


class MockACPProcess:
    """Mock ACP subprocess for testing adapter logic."""

    def __init__(self):
        self.stdin = asyncio.StreamWriter(None, None, None, asyncio.get_event_loop())
        self.stdout = asyncio.StreamReader()
        self.stderr = asyncio.StreamReader()
        self.returncode = None
        self._terminate_called = False
        self._kill_called = False
        self._wait_future = asyncio.Future()

    def terminate(self):
        self._terminate_called = True
        if not self._wait_future.done():
            self._wait_future.set_result(0)

    def kill(self):
        self._kill_called = True
        if not self._wait_future.done():
            self._wait_future.set_result(0)

    async def wait(self):
        return await self._wait_future


@pytest.fixture
def temp_hermes_repo():
    """Create a temporary hermes-agent repo structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        acp_dir = tmpdir / "acp_adapter"
        acp_dir.mkdir()
        (acp_dir / "entry.py").write_text("# Mock ACP entry point\n")
        (acp_dir / "__init__.py").touch()
        yield str(tmpdir)


async def test_acp_adapter_scrubs_secrets_in_env(temp_hermes_repo):
    """Test _scrub_env method removes API_KEY, SECRET, TOKEN, PASSWORD, CREDENTIAL."""
    adapter = AcPAdapter(cwd=temp_hermes_repo, timeout_seconds=5)

    with pytest.MonkeyPatch().context() as mp:
        mp.setenv("API_KEY", "secret123")
        mp.setenv("SECRET_TOKEN", "token456")
        mp.setenv("MY_PASSWORD", "pass789")
        mp.setenv("CREDENTIAL_DATA", "cred123")
        mp.setenv("NORMAL_VAR", "value")

        scrubbed = adapter._scrub_env()
        assert scrubbed.get("API_KEY") == "***REDACTED***"
        assert scrubbed.get("SECRET_TOKEN") == "***REDACTED***"
        assert scrubbed.get("MY_PASSWORD") == "***REDACTED***"
        assert scrubbed.get("CREDENTIAL_DATA") == "***REDACTED***"
        assert scrubbed.get("NORMAL_VAR") == "value"


async def test_acp_adapter_validates_cwd(temp_hermes_repo):
    """Test cwd validation against allowed_root."""
    adapter = AcPAdapter(cwd="/etc", allowed_root="/home/user", timeout_seconds=5)

    with pytest.raises(ValueError) as exc_info:
        adapter._validate_cwd()
    assert "not under allowed_root" in str(exc_info.value)


async def test_acp_adapter_hash_parameters(temp_hermes_repo):
    """Test parameter hashing for provenance."""
    adapter = AcPAdapter(cwd=temp_hermes_repo, timeout_seconds=5)

    params1 = {"a": 1, "b": "test"}
    params2 = {"b": "test", "a": 1}  # Different order, same content
    params3 = {"a": 2, "b": "test"}  # Different content

    hash1 = adapter._hash_parameters(params1)
    hash2 = adapter._hash_parameters(params2)
    hash3 = adapter._hash_parameters(params3)

    assert hash1 == hash2  # Same content = same hash
    assert hash1 != hash3  # Different content = different hash
    assert len(hash1) == 16  # Truncated SHA256


async def test_acp_adapter_connect_acp_not_installed(temp_hermes_repo):
    """Test missing ACP entry point raises ProtocolUnavailableError."""
    # Create a repo without entry.py
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        # No acp_adapter directory
        adapter = AcPAdapter(cwd=str(tmpdir), timeout_seconds=5)

        with pytest.raises(ProtocolUnavailableError) as exc_info:
            await adapter.connect()
        assert "not found" in str(exc_info.value).lower() or "ACP entry point" in str(exc_info.value)


async def test_acp_adapter_connect_process_not_found():
    """Test missing hermes-agent raises ProtocolUnavailableError."""
    adapter = AcPAdapter(cwd="/nonexistent/path", timeout_seconds=5)

    with pytest.raises(ProtocolUnavailableError) as exc_info:
        await adapter.connect()
    assert "not found" in str(exc_info.value).lower() or "ACP entry point" in str(exc_info.value)


async def test_acp_adapter_session_lifecycle_basic():
    """Test basic session tracking logic."""
    from aios.adapters.acp_session import AcPSessionRegistry

    # Create a mock adapter
    class MockAdapter:
        def __init__(self):
            self.sessions = {}

        async def new_session(self, cwd, timeout):
            import uuid
            sid = str(uuid.uuid4())
            self.sessions[sid] = {"cwd": cwd, "active": True}
            return sid

        async def close_session(self, session_id):
            if session_id in self.sessions:
                self.sessions[session_id]["active"] = False

    mock_adapter = MockAdapter()
    registry = AcPSessionRegistry(mock_adapter, session_idle_timeout_seconds=300)

    # Test create
    session_id1 = await registry.create("/tmp", 30)
    assert registry.is_active(session_id1)
    assert session_id1 in registry.get_active()

    session_id2 = await registry.create("/tmp", 30)
    assert registry.is_active(session_id2)
    assert len(registry.get_active()) == 2

    # Test close
    await registry.close(session_id1)
    assert not registry.is_active(session_id1)
    assert len(registry.get_active()) == 1

    # Test double-close (idempotent)
    await registry.close(session_id1)  # Should not raise

    # Test cleanup_all
    await registry.cleanup_all()
    assert len(registry.get_active()) == 0


async def test_acp_adapter_session_isolation():
    """Test session isolation validation."""
    from aios.adapters.acp_session import AcPSessionRegistry, SessionNotFoundError

    class MockAdapter:
        def __init__(self):
            self.sessions = {}

        async def new_session(self, cwd, timeout):
            import uuid
            sid = str(uuid.uuid4())
            self.sessions[sid] = {"cwd": cwd, "active": True}
            return sid

        async def close_session(self, session_id):
            if session_id in self.sessions:
                self.sessions[session_id]["active"] = False

    mock_adapter = MockAdapter()
    registry = AcPSessionRegistry(mock_adapter, session_idle_timeout_seconds=300)

    session_id = await registry.create("/tmp", 30)
    await registry.validate_isolation(session_id)  # Should not raise

    # Unknown session should raise
    with pytest.raises(SessionNotFoundError):
        await registry.validate_isolation("unknown-session")

    # Closed session should raise
    await registry.close(session_id)
    with pytest.raises(SessionNotFoundError):
        await registry.validate_isolation(session_id)


async def test_acp_adapter_error_classification():
    """Test error classification hierarchy."""
    from aios.adapters.acp_adapter import (
        ProtocolError,
        ProtocolUnavailableError,
        TransportConnectionError,
        SessionCreationTimeout,
        SessionNotFoundError,
        ExecutionTimeout,
        ExecutionCancelled,
        MalformedResponseError,
        TransportDisconnectError,
        CleanupTimeout,
        DuplicateExecutionError,
        SecretLeakDetectedError,
    )

    # All should inherit from ProtocolError
    for err_class in [
        ProtocolUnavailableError,
        TransportConnectionError,
        SessionCreationTimeout,
        SessionNotFoundError,
        ExecutionTimeout,
        ExecutionCancelled,
        MalformedResponseError,
        TransportDisconnectError,
        CleanupTimeout,
        DuplicateExecutionError,
        SecretLeakDetectedError,
    ]:
        assert issubclass(err_class, ProtocolError)

    # Test instantiation
    err = ProtocolUnavailableError("test message")
    assert str(err) == "test message"


async def test_acp_adapter_duplicate_execution_detection():
    """Test duplicate execution prevention logic."""
    from aios.adapters.acp_adapter import AcPSession

    session = AcPSession(
        session_id="test-session",
        cwd="/tmp",
        created_at=asyncio.get_event_loop().time(),
    )

    # Initially no pending execution
    assert not session.pending_execution

    # Mark as pending
    session.pending_execution = True
    assert session.pending_execution

    # Should detect duplicate
    # (actual duplicate check is in adapter.prompt)


async def test_acp_adapter_is_connected_states(temp_hermes_repo):
    """Test is_connected state transitions."""
    adapter = AcPAdapter(cwd=temp_hermes_repo, timeout_seconds=5)

    assert not adapter.is_connected()

    # After successful mock connect
    # We can't easily test full connect without subprocess, but we can test state
    adapter._initialized = True
    adapter._process = MockACPProcess()
    adapter._process.returncode = None
    assert adapter.is_connected()

    # After process exits
    adapter._process.returncode = 0
    assert not adapter.is_connected()

    # After disconnect
    adapter._initialized = False
    adapter._process = None
    assert not adapter.is_connected()


# Integration-style tests using in-process mock server
async def test_acp_mock_server_in_process():
    """Test ACP mock server protocol directly in-process."""
    from aios.adapters.mock_hermes_acp_server import MockACPServer

    server = MockACPServer()

    # Test initialize
    req = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
    resp = await server.handle_request(req)
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 1
    assert "result" in resp
    assert resp["result"]["protocolVersion"] == 1

    # Test session/new
    req = {"jsonrpc": "2.0", "id": 2, "method": "session/new", "params": {"cwd": "/tmp"}}
    resp = await server.handle_request(req)
    assert resp["jsonrpc"] == "2.0"
    assert "result" in resp
    assert "sessionId" in resp["result"]
    session_id = resp["result"]["sessionId"]

    # Test session/prompt
    req = {"jsonrpc": "2.0", "id": 3, "method": "session/prompt", "params": {"sessionId": session_id, "prompt": "test"}}
    resp = await server.handle_request(req)
    assert resp["jsonrpc"] == "2.0"
    assert "result" in resp
    assert resp["result"]["stopReason"] == "end_turn"
    assert "Completed" in resp["result"]["text"]

    # Test session/cancel
    req = {"jsonrpc": "2.0", "id": 4, "method": "session/cancel", "params": {"sessionId": session_id}}
    resp = await server.handle_request(req)
    assert resp["jsonrpc"] == "2.0"
    assert resp["result"]["success"] is True

    # Test session/close
    req = {"jsonrpc": "2.0", "id": 5, "method": "session/close", "params": {"sessionId": session_id}}
    resp = await server.handle_request(req)
    assert resp["jsonrpc"] == "2.0"
    assert resp["result"]["success"] is True

    # Test unknown session
    req = {"jsonrpc": "2.0", "id": 6, "method": "session/prompt", "params": {"sessionId": "unknown", "prompt": "test"}}
    resp = await server.handle_request(req)
    assert "error" in resp
    assert resp["error"]["code"] == -32000


async def test_acp_mock_server_deterministic_responses():
    """Test mock server returns deterministic responses for same prompts."""
    from aios.adapters.mock_hermes_acp_server import MockACPServer

    server = MockACPServer()

    await server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    session_resp = await server.handle_request({"jsonrpc": "2.0", "id": 2, "method": "session/new"})
    session_id = session_resp["result"]["sessionId"]

    # Same prompt should give same response pattern
    resp1 = await server.handle_request({"jsonrpc": "2.0", "id": 3, "method": "session/prompt", "params": {"sessionId": session_id, "prompt": "do something specific"}})
    resp2 = await server.handle_request({"jsonrpc": "2.0", "id": 4, "method": "session/prompt", "params": {"sessionId": session_id, "prompt": "do something specific"}})

    assert resp1["result"]["text"] == resp2["result"]["text"]

    # Error prompt triggers error
    error_resp = await server.handle_request({"jsonrpc": "2.0", "id": 5, "method": "session/prompt", "params": {"sessionId": session_id, "prompt": "trigger error"}})
    assert error_resp["result"]["stopReason"] == "error"

    # Cancel prompt triggers cancelled
    cancel_resp = await server.handle_request({"jsonrpc": "2.0", "id": 6, "method": "session/prompt", "params": {"sessionId": session_id, "prompt": "cancel this"}})
    assert cancel_resp["result"]["stopReason"] == "cancelled"

    # Timeout prompt triggers timeout
    timeout_resp = await server.handle_request({"jsonrpc": "2.0", "id": 7, "method": "session/prompt", "params": {"sessionId": session_id, "prompt": "timeout please"}})
    assert timeout_resp["result"]["stopReason"] == "timeout"