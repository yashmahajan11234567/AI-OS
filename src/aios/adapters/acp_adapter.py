"""
ACP Adapter for AI-OS M8-T1.

Provides ACP stdio transport layer for hermes-agent.
Deferred import of `acp` SDK - not at module scope.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# S1 (Terminal 2): route ACP subprocess execution through the canonical
# SecurityManager gate before spawning hermes-agent. Reuse the same gate the
# MCPManager uses (C18 gate-before-connect) so ACP has no privileged bypass path.
from aios.core.security_manager import get_security_manager
# S4 (Terminal 2): central secret redaction for subprocess failure reporting.
from aios.security.secrets import redact_text

logger = logging.getLogger(__name__)


@dataclass
class ProtocolError(Exception):
    """Base protocol error."""
    message: str

    def __str__(self) -> str:
        return self.message


class ProtocolUnavailableError(ProtocolError):
    """ACP SDK or hermes-agent not available."""
    pass


class TransportConnectionError(ProtocolError):
    """Failed to connect to ACP subprocess."""
    pass


class SessionCreationTimeout(ProtocolError):
    """Session creation exceeded timeout."""
    pass


class SessionNotFoundError(ProtocolError):
    """Session not found."""
    pass


class ExecutionTimeout(ProtocolError):
    """Execution exceeded timeout."""
    pass


class ExecutionCancelled(ProtocolError):
    """Execution was cancelled."""
    pass


class MalformedResponseError(ProtocolError):
    """Malformed ACP response."""
    pass


class TransportDisconnectError(ProtocolError):
    """Transport disconnected unexpectedly."""
    pass


class CleanupTimeout(ProtocolError):
    """Cleanup exceeded timeout."""
    pass


class DuplicateExecutionError(ProtocolError):
    """Duplicate execution detected."""
    pass


class SecretLeakDetectedError(ProtocolError):
    """Secret detected in parameters/provenance."""
    pass


@dataclass
class AcPSession:
    """ACP session metadata."""
    session_id: str
    cwd: str
    created_at: datetime
    active: bool = True
    pending_execution: bool = False


class AcPAdapter:
    """ACP stdio transport adapter for hermes-agent."""

    # Environment variable patterns to scrub
    SCRUB_PATTERNS = (
        re.compile(r"(.*_)?(api[_-]?key)(_.*)?$", re.IGNORECASE),
        re.compile(r"(.*_)?secret(_.*)?$", re.IGNORECASE),
        re.compile(r"(.*_)?token(_.*)?$", re.IGNORECASE),
        re.compile(r"(.*_)?password(_.*)?$", re.IGNORECASE),
        re.compile(r"(.*_)?credential(_.*)?$", re.IGNORECASE),
    )

    def __init__(
        self,
        cwd: str,
        timeout_seconds: int = 30,
        allowed_root: str | None = None,
        env_scrub_patterns: tuple[str, ...] | None = None,
    ) -> None:
        """Initialize ACP adapter.

        Args:
            cwd: Working directory for hermes-agent subprocess (path to hermes-agent repo)
            timeout_seconds: Connection/operation timeout
            allowed_root: If set, restrict cwd to be underneath this path
            env_scrub_patterns: Additional regex patterns for env var scrubbing
        """
        self._cwd = os.path.abspath(cwd) if cwd else os.getcwd()
        self._timeout_seconds = timeout_seconds
        self._allowed_root = os.path.abspath(allowed_root) if allowed_root else None
        self._scrub_patterns = list(self.SCRUB_PATTERNS)
        if env_scrub_patterns:
            for pattern in env_scrub_patterns:
                self._scrub_patterns.append(re.compile(pattern))

        self._process: asyncio.subprocess.Process | None = None
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._initialized = False
        self._sessions: dict[str, AcPSession] = {}
        self._pending_requests: dict[int, asyncio.Future] = {}
        self._request_counter = 0
        self._background_tasks: set[asyncio.Task] = set()

    def _validate_cwd(self) -> None:
        """Validate cwd is within allowed_root if set."""
        if self._allowed_root:
            try:
                cwd_rel = os.path.relpath(self._cwd, self._allowed_root)
                if cwd_rel.startswith("..") or os.path.isabs(cwd_rel):
                    raise ValueError(f"cwd {self._cwd} is not under allowed_root {self._allowed_root}")
            except ValueError:
                raise ValueError(f"cwd {self._cwd} is not under allowed_root {self._allowed_root}")

    def _scrub_env(self, env: dict[str, str] | None = None) -> dict[str, str]:
        """Scrub sensitive environment variables (S4 — central util)."""
        from aios.security.secrets import redact_env

        # Reuse the canonical redaction util. Local patterns are appended for
        # ACP-specific caller-supplied env names that may carry secrets.
        base = redact_env(env)
        if env is None:
            return base
        # Apply ACP-specific additional patterns to any non-secret-key values.
        extra = {}
        for key, value in base.items():
            should_scrub = False
            for pattern in self._scrub_patterns:
                if pattern.match(key):
                    should_scrub = True
                    break
            extra[key] = "***REDACTED***" if should_scrub else value
        return extra

    def _hash_parameters(self, params: dict[str, Any]) -> str:
        """Create SHA-256 hash of parameters for provenance (no secrets)."""
        # Sort keys for deterministic hash
        import json
        serialized = json.dumps(params, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    async def _get_acp_module(self):
        """Deferred import of acp SDK. Raises ProtocolUnavailableError if not available."""
        try:
            import acp
            return acp
        except ModuleNotFoundError:
            raise ProtocolUnavailableError("ACP SDK (acp) not installed")

    async def connect(self) -> bool:
        """Launch hermes-agent subprocess and complete ACP initialize handshake."""
        self._validate_cwd()

        # Check if hermes-agent entry point exists
        acp_entry = os.path.join(self._cwd, "acp_adapter", "entry.py")
        if not os.path.exists(acp_entry):
            # Check alternative locations
            alt_paths = [
                os.path.join(self._cwd, "hermes_agent", "acp_adapter", "entry.py"),
                os.path.join(self._cwd, "src", "hermes_agent", "acp_adapter", "entry.py"),
            ]
            found = False
            for alt in alt_paths:
                if os.path.exists(alt):
                    acp_entry = alt
                    found = True
                    break
            if not found:
                raise ProtocolUnavailableError(
                    f"hermes-agent ACP entry point not found in {self._cwd}. "
                    "Expected acp_adapter/entry.py or hermes_agent/acp_adapter/entry.py"
                )

        # Build subprocess command
        python_exe = shutil.which("python") or shutil.which("python3")
        if not python_exe:
            raise TransportConnectionError("Python interpreter not found")

        # S1 (Terminal 2): Gate-before-connect. ACP launches an external
        # subprocess, so it MUST route through the same canonical
        # SecurityManager.validate_mcp_server_before_connect gate that the
        # MCPManager uses (C18). There is no privileged/bypass path. Fail closed.
        command = [python_exe, "-m", "acp_adapter.entry"]
        try:
            from aios.core.mcp_manager import MCPServerConfig, MCPTransport

            server_config = MCPServerConfig(
                server_id="hermes_agent_acp",
                name="Hermes Agent ACP (subprocess)",
                transport=MCPTransport.STDIO,
                command=command,
                url=None,
                env={},
                headers={},
                timeout_seconds=self._timeout_seconds,
                auto_reconnect=False,
                max_retries=0,
                metadata={"cwd": self._cwd, "entry": acp_entry},
            )
            security_manager = get_security_manager()
            validation_result = security_manager.validate_mcp_server_before_connect(server_config)
            if not validation_result.passed:
                violation_summaries = "; ".join(
                    f"{v.severity}:{v.description}" for v in validation_result.violations
                    if v.severity in ("high", "critical")
                )
                raise TransportConnectionError(
                    f"ACP subprocess blocked by SecurityManager gate "
                    f"(hermes_agent_acp): {violation_summaries}"
                )
        except ImportError:
            # mcp_manager unavailable in an exceptional test environment — the
            # gate cannot run, so fail closed (never silently launch).
            raise TransportConnectionError(
                "ACP subprocess blocked: SecurityManager/MCP gate unavailable"
            )

        env = self._scrub_env()
        env["PYTHONPATH"] = self._cwd + (os.pathsep + env.get("PYTHONPATH", "")) if env.get("PYTHONPATH") else self._cwd

        logger.debug(f"Starting ACP subprocess: {python_exe} -m acp_adapter.entry from {self._cwd}")

        try:
            self._process = await asyncio.create_subprocess_exec(
                python_exe, "-m", "acp_adapter.entry",
                cwd=self._cwd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
        except Exception as e:
            raise TransportConnectionError(f"Failed to start ACP subprocess: {e}")

        # Set up reader/writer
        self._reader = self._process.stdout
        self._writer = self._process.stdin

        # Start stderr reader task
        stderr_task = asyncio.create_task(self._read_stderr())
        self._background_tasks.add(stderr_task)
        stderr_task.add_done_callback(self._background_tasks.discard)

        # Start response reader task
        response_task = asyncio.create_task(self._read_responses())
        self._background_tasks.add(response_task)
        response_task.add_done_callback(self._background_tasks.discard)

        # Wait for process to be ready (brief pause)
        await asyncio.sleep(0.5)

        # Check if process is still alive
        if self._process.returncode is not None:
            stderr_output = ""
            if self._process.stderr:
                stderr_data = await self._process.stderr.read()
                stderr_output = stderr_data.decode() if stderr_data else ""
            raise TransportConnectionError(
                f"ACP subprocess exited immediately with code "
                f"{self._process.returncode}: {redact_text(stderr_output)}"
            )

        # Send initialize handshake
        try:
            await self._send_request("initialize", {"protocolVersion": 1})
            response = await asyncio.wait_for(
                self._wait_for_response(1), timeout=self._timeout_seconds
            )
            if "error" in response:
                raise TransportConnectionError(f"ACP initialize failed: {response['error']}")

            self._initialized = True
            logger.info("ACP connection established")
            return True

        except asyncio.TimeoutError:
            await self.disconnect()
            raise SessionCreationTimeout(f"ACP initialize handshake timed out after {self._timeout_seconds}s")
        except Exception as e:
            await self.disconnect()
            if isinstance(e, ProtocolError):
                raise
            raise TransportConnectionError(f"ACP connection failed: {e}")

    async def _read_stderr(self) -> None:
        """Read stderr from subprocess for debugging."""
        if not self._process or not self._process.stderr:
            return
        try:
            while True:
                line = await self._process.stderr.readline()
                if not line:
                    break
                logger.debug(f"ACP stderr: {line.decode().strip()}")
        except Exception:
            pass  # Ignore stderr read errors

    async def _read_responses(self) -> None:
        """Read JSON-RPC responses from subprocess stdout."""
        if not self._reader:
            return

        while True:
            try:
                line = await self._reader.readline()
                if not line:
                    # EOF - process terminated
                    logger.warning("ACP subprocess stdout closed")
                    if self._process and self._process.returncode is not None:
                        logger.warning(f"ACP subprocess exited with code {self._process.returncode}")
                    # Mark all pending requests as failed
                    for future in self._pending_requests.values():
                        if not future.done():
                            future.set_exception(TransportDisconnectError("ACP subprocess terminated"))
                    self._pending_requests.clear()
                    break

                line = line.decode().strip()
                if not line:
                    continue

                response = json.loads(line)
                request_id = response.get("id")
                if request_id in self._pending_requests:
                    future = self._pending_requests.pop(request_id)
                    if not future.done():
                        future.set_result(response)
                else:
                    # Notification or unexpected response
                    logger.debug(f"ACP unsolicited response: {response}")

            except json.JSONDecodeError as e:
                logger.warning(f"ACP response JSON decode error: {e}")
            except Exception as e:
                logger.error(f"ACP response reader error: {e}")

    async def _send_request(self, method: str, params: dict[str, Any] | None = None) -> int:
        """Send JSON-RPC request and return request ID."""
        if not self._writer:
            raise TransportConnectionError("Not connected")

        self._request_counter += 1
        request_id = self._request_counter
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params is not None:
            request["params"] = params

        try:
            self._writer.write((json.dumps(request) + "\n").encode())
            await self._writer.drain()
        except Exception as e:
            raise TransportConnectionError(f"Failed to send request: {e}")

        return request_id

    async def _wait_for_response(self, request_id: int, timeout: float | None = None) -> dict[str, Any]:
        """Wait for response to a request."""
        future = asyncio.Future()
        self._pending_requests[request_id] = future
        try:
            if timeout:
                return await asyncio.wait_for(future, timeout=timeout)
            return await future
        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise
        except Exception:
            self._pending_requests.pop(request_id, None)
            raise

    async def disconnect(self) -> None:
        """Terminate ACP subprocess."""
        # Close all sessions
        await self.cleanup_all()

        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()

        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
            except Exception:
                pass
        self._process = None
        self._reader = None
        self._writer = None
        self._initialized = False
        logger.info("ACP disconnected")

    def is_connected(self) -> bool:
        """Check if adapter is connected and initialized."""
        return (
            self._initialized
            and self._process is not None
            and self._process.returncode is None
        )

    async def new_session(self, cwd: str | None = None, timeout: float | None = None) -> str:
        """Create new ACP session. Returns session_id (UUID)."""
        if not self.is_connected():
            raise TransportConnectionError("Not connected to ACP server")

        session_cwd = cwd or self._cwd
        effective_timeout = timeout or self._timeout_seconds

        request_id = await self._send_request("session/new", {"cwd": session_cwd})
        try:
            response = await asyncio.wait_for(
                self._wait_for_response(request_id), timeout=effective_timeout
            )
        except asyncio.TimeoutError:
            raise SessionCreationTimeout(f"Session creation timed out after {effective_timeout}s")

        if "error" in response:
            error_msg = response["error"].get("message", "Unknown error")
            raise SessionCreationTimeout(f"Session creation failed: {error_msg}")

        session_id = response.get("result", {}).get("sessionId")
        if not session_id:
            raise MalformedResponseError("Session creation response missing sessionId")

        session = AcPSession(
            session_id=session_id,
            cwd=session_cwd,
            created_at=datetime.utcnow(),
            active=True,
        )
        self._sessions[session_id] = session
        logger.debug(f"Created ACP session: {session_id}")
        return session_id

    async def prompt(
        self,
        session_id: str,
        text: str,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Send prompt to session, return raw ACP response dict."""
        if not self.is_connected():
            raise TransportConnectionError("Not connected to ACP server")

        session = self._sessions.get(session_id)
        if not session:
            raise SessionNotFoundError(f"Session not found: {session_id}")
        if not session.active:
            raise SessionNotFoundError(f"Session {session_id} is not active")

        # Prevent duplicate execution (SECURITY-CRITICAL)
        if session.pending_execution:
            raise DuplicateExecutionError(
                f"Session {session_id} already has a pending execution"
            )

        session.pending_execution = True
        effective_timeout = timeout or self._timeout_seconds

        try:
            request_id = await self._send_request(
                "session/prompt",
                {"sessionId": session_id, "prompt": text, "timeout": int(effective_timeout * 1000)}
            )
            response = await asyncio.wait_for(
                self._wait_for_response(request_id), timeout=effective_timeout
            )
        except asyncio.TimeoutError:
            # On timeout, mark session for potential cleanup but don't remove
            session.pending_execution = False
            raise ExecutionTimeout(f"Prompt execution timed out after {effective_timeout}s")
        except Exception:
            session.pending_execution = False
            raise
        finally:
            session.pending_execution = False

        if "error" in response:
            error_msg = response["error"].get("message", "Unknown error")
            if "cancel" in error_msg.lower():
                raise ExecutionCancelled(f"Execution cancelled: {error_msg}")
            raise MalformedResponseError(f"Prompt failed: {error_msg}")

        result = response.get("result", {})
        if not result:
            raise MalformedResponseError("Prompt response missing result")

        return result

    async def cancel(self, session_id: str) -> None:
        """Cancel in-flight prompt for session."""
        if not self.is_connected():
            raise TransportConnectionError("Not connected to ACP server")

        session = self._sessions.get(session_id)
        if not session:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        request_id = await self._send_request("session/cancel", {"sessionId": session_id})
        try:
            response = await asyncio.wait_for(
                self._wait_for_response(request_id), timeout=10.0
            )
            if "error" in response:
                logger.warning(f"ACP cancel failed: {response['error']}")
        except Exception as e:
            logger.warning(f"ACP cancel request failed: {e}")

        session.pending_execution = False

    async def close_session(self, session_id: str) -> None:
        """Close ACP session."""
        if not self.is_connected():
            return  # Idempotent - already disconnected

        session = self._sessions.get(session_id)
        if not session:
            logger.warning(f"Close session called for unknown session: {session_id}")
            return  # Idempotent - double close is no-op

        if not session.active:
            return  # Idempotent - already closed

        try:
            request_id = await self._send_request("session/close", {"sessionId": session_id})
            response = await asyncio.wait_for(
                self._wait_for_response(request_id), timeout=10.0
            )
            if "error" in response:
                logger.warning(f"ACP close session failed: {response['error']}")
        except Exception as e:
            logger.warning(f"ACP close session request failed: {e}")

        session.active = False
        del self._sessions[session_id]
        logger.debug(f"Closed ACP session: {session_id}")

    async def cleanup_all(self) -> None:
        """Close all active sessions."""
        session_ids = list(self._sessions.keys())
        for session_id in session_ids:
            try:
                await self.close_session(session_id)
            except Exception as e:
                logger.warning(f"Failed to close session {session_id} during cleanup: {e}")