"""
Hermes Bridge for AI-OS M8-T1.

AI-OS-side bridge to hermes-agent(EXT) via MCP/ACP.
- Provides MCP fallback connection
- Supports ACP upgrade (preferred)
- Isolates worker session
- Attaches complete provenance
- Returns observations ONLY

hermes-agent(EXT) MUST NOT:
- Issue AI-OS verdicts
- Become decision authority
- Bypass SecurityManager
- Modify kernel policy
- Approve/reject implementation
- Become a second orchestrator
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from aios.core.mcp_manager import get_mcp_manager

logger = logging.getLogger(__name__)


@dataclass
class HermesTask:
    """Task to delegate to Hermes worker."""

    task_id: str
    task_type: str  # "browser", "navigation", "extraction", "screenshot", etc.
    description: str
    parameters: dict[str, Any]
    session_id: str
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass
class HermesObservation:
    """Observation returned from Hermes worker (NOT a verdict)."""

    task_id: str
    success: bool
    data: dict[str, Any]
    error: str | None
    timestamp: datetime
    session_id: str
    provenance: dict[str, Any]
    trust_level: str = "untrusted"  # Always untrusted - AI-OS decides


# Custom exceptions for error classification
class ProtocolError(Exception):
    """Base protocol error."""
    pass


class ProtocolUnavailableError(ProtocolError):
    """Requested protocol unavailable."""
    pass


class TransportConnectionError(ProtocolError):
    """Transport connection failed."""
    pass


class SessionCreationTimeout(ProtocolError):
    """Session creation timed out."""
    pass


class SessionNotFoundError(ProtocolError):
    """Session not found."""
    pass


class ExecutionTimeout(ProtocolError):
    """Execution timed out."""
    pass


class ExecutionCancelled(ProtocolError):
    """Execution was cancelled."""
    pass


class MalformedResponseError(ProtocolError):
    """Malformed response received."""
    pass


class TransportDisconnectError(ProtocolError):
    """Transport disconnected."""
    pass


class DuplicateExecutionError(ProtocolError):
    """Duplicate execution detected."""
    pass


class SecretLeakDetectedError(ProtocolError):
    """Secret detected in parameters."""
    pass


class HermesBridge:
    """AI-OS-side HermesBridge for hermes-agent(EXT) integration.

    Supports both ACP (preferred) and MCP (fallback) protocols.
    Isolates the worker session and attaches provenance.
    Returns observations only - hermes-agent(EXT) has no decision authority.
    """

    # Environment variable patterns to scrub from provenance and subprocess env
    SCRUB_PATTERNS = (
        re.compile(r"(.*_)?(api[_-]?key)(_.*)?$", re.IGNORECASE),
        re.compile(r"(.*_)?secret(_.*)?$", re.IGNORECASE),
        re.compile(r"(.*_)?token(_.*)?$", re.IGNORECASE),
        re.compile(r"(.*_)?password(_.*)?$", re.IGNORECASE),
        re.compile(r"(.*_)?credential(_.*)?$", re.IGNORECASE),
    )

    def __init__(
        self,
        mcp_manager=None,
        server_id: str = "hermes_agent_ext",
        protocol: str = "acp",
        fallback_to_mcp: bool = True,
        acp_adapter=None,
        cwd: str = "",
        timeout_seconds: int = 30,
        retry_attempts: int = 3,
        allowed_root: str = "",
        session_idle_timeout_seconds: int = 300,
        session_ttl_seconds: int = 0,
    ) -> None:
        """Initialize Hermes bridge.

        Args:
            mcp_manager: MCPManager instance (uses global if None)
            server_id: MCP server identifier for hermes-agent(EXT)
            protocol: Protocol to use - "acp" (preferred) or "mcp"
            fallback_to_mcp: If ACP unavailable, fall back to MCP
            acp_adapter: Optional AcPAdapter for testing (injected)
            cwd: Working directory for hermes-agent (path to hermes-agent repo)
            timeout_seconds: Connection/operation timeout
            retry_attempts: Max retry attempts for transient errors
            allowed_root: If set, restrict subprocess cwd to underneath this path
            session_idle_timeout_seconds: Session idle timeout for ACP
            session_ttl_seconds: Absolute max session lifetime for ACP
                (M9-N7 hardening; 0 = disabled, M8 default preserved)
        """
        self._mcp_manager = mcp_manager or get_mcp_manager()
        self._server_id = server_id
        self._protocol = protocol.lower()
        self._fallback_to_mcp = fallback_to_mcp
        self._acp_adapter = acp_adapter
        self._cwd = cwd
        self._timeout_seconds = timeout_seconds
        self._retry_attempts = retry_attempts
        self._allowed_root = allowed_root or None
        self._session_idle_timeout_seconds = session_idle_timeout_seconds
        self._session_ttl_seconds = max(0, int(session_ttl_seconds))

        # Session tracking
        self._active_sessions: dict[str, dict[str, Any]] = {}
        self._acp_registry = None

        # Validate protocol
        if self._protocol not in ("acp", "mcp"):
            raise ValueError(f"Unsupported protocol: {protocol}. Must be 'acp' or 'mcp'")

    async def _get_acp_adapter(self):
        """Get or create ACP adapter (lazy initialization)."""
        if self._acp_adapter is not None:
            return self._acp_adapter

        # Deferred import - don't import acp at module scope
        try:
            from aios.adapters.acp_adapter import AcPAdapter, ProtocolUnavailableError as AcpProtocolUnavailableError
        except ImportError:
            raise ProtocolUnavailableError("ACP adapter module not available")

        if not self._cwd:
            raise ProtocolUnavailableError("ACP requires cwd parameter (path to hermes-agent repo)")

        self._acp_adapter = AcPAdapter(
            cwd=self._cwd,
            timeout_seconds=self._timeout_seconds,
            allowed_root=self._allowed_root,
        )

        # Try to connect
        try:
            await self._acp_adapter.connect()
        except AcpProtocolUnavailableError:
            raise ProtocolUnavailableError("ACP SDK or hermes-agent not available")

        # Initialize session registry
        from aios.adapters.acp_session import AcPSessionRegistry
        self._acp_registry = AcPSessionRegistry(
            self._acp_adapter,
            session_idle_timeout_seconds=self._session_idle_timeout_seconds,
            session_ttl_seconds=self._session_ttl_seconds,  # M9-N7
        )

        return self._acp_adapter

    async def _ensure_mcp_connected(self) -> bool:
        """Ensure connection to hermes-agent(EXT) MCP server."""
        status = self._mcp_manager.get_server_status(self._server_id)
        if not status or not status.connected:
            return await self._mcp_manager.connect(self._server_id)
        return True

    def _create_provenance(
        self,
        task: HermesTask,
        protocol: str,
        adapter: str,
        execution_id: str,
        correlation_id: str,
        exit_status: str,
        errors: list[str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create complete provenance metadata for an observation."""
        # Hash parameters for safe provenance (no secrets)
        params_hash = self._hash_parameters(task.parameters)

        provenance = {
            "task_id": task.task_id,
            "execution_id": execution_id,
            "session_id": task.session_id,
            "correlation_id": correlation_id,
            "protocol": protocol,  # "acp" | "mcp" | "acp_fallback"
            "adapter": adapter,    # "acp_adapter" | "mcp_manager"
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_metadata": {
                "task_type": task.task_type,
                "description": task.description[:200] if len(task.description) > 200 else task.description,
                "parameters_hash": params_hash,
            },
            "target": {"server_id": self._server_id},
            "exit_status": exit_status,  # "completed" | "cancelled" | "error" | "timeout"
            "errors": errors or [],
            "environment": "ai_os_hermes_bridge",
        }

        if extra:
            # Merge extra but don't override core fields
            for k, v in extra.items():
                if k not in provenance:
                    provenance[k] = v

        return provenance

    def _hash_parameters(self, params: dict[str, Any]) -> str:
        """Create SHA-256 hash of parameters for provenance (no secrets)."""
        serialized = json.dumps(params, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    def _scrub_env(self, env: dict[str, str] | None = None) -> dict[str, str]:
        """Scrub sensitive environment variables."""
        source_env = env or dict(os.environ)
        scrubbed = {}
        for key, value in source_env.items():
            should_scrub = False
            for pattern in self.SCRUB_PATTERNS:
                if pattern.match(key):
                    should_scrub = True
                    break
            if not should_scrub:
                scrubbed[key] = value
            else:
                scrubbed[key] = "***REDACTED***"
        return scrubbed

    async def create_worker_session(self, environment: dict[str, Any] | None = None) -> str:
        """Create an isolated worker session.

        Returns the SERVER-GENERATED session ID (not locally generated).
        This fixes DEF-001 where local and remote session IDs could diverge.

        Implements ACP-first / MCP-fallback policy:
        - protocol="acp" + fallback=True  → Try ACP, fallback to MCP on failure (provenance="acp_fallback")
        - protocol="acp" + fallback=False → Try ACP, raise on failure
        - protocol="mcp"                  → Use MCP directly (provenance="mcp")

        Args:
            environment: Optional environment configuration for the session

        Returns:
            Session ID as returned by the remote side
        """
        if self._protocol == "acp":
            try:
                session_id = await self._create_acp_session(environment)
                self._active_sessions[session_id]["protocol"] = "acp"
                self._active_sessions[session_id]["provenance_protocol"] = "acp"
                return session_id
            except ProtocolUnavailableError as e:
                if self._fallback_to_mcp:
                    logger.warning(f"ACP unavailable, falling back to MCP: {e}")
                    session_id = await self._create_mcp_session(environment)
                    self._active_sessions[session_id]["protocol"] = "mcp"
                    self._active_sessions[session_id]["provenance_protocol"] = "acp_fallback"
                    return session_id
                raise
        else:
            session_id = await self._create_mcp_session(environment)
            self._active_sessions[session_id]["protocol"] = "mcp"
            self._active_sessions[session_id]["provenance_protocol"] = "mcp"
            return session_id

    async def _create_acp_session(self, environment: dict[str, Any] | None = None) -> str:
        """Create ACP session via adapter."""
        adapter = await self._get_acp_adapter()
        registry = self._acp_registry

        # Determine cwd from environment or default
        cwd = self._cwd
        if environment and "cwd" in environment:
            cwd = environment["cwd"]

        session_id = await registry.create(cwd=cwd, timeout_seconds=self._timeout_seconds)

        self._active_sessions[session_id] = {
            "created_at": datetime.now(timezone.utc),
            "environment": environment or {},
            "protocol": "acp",
        }

        logger.debug(f"Created ACP session: {session_id}")
        return session_id

    async def _create_mcp_session(self, environment: dict[str, Any] | None = None) -> str:
        """Create MCP session via MCP manager."""
        if not await self._ensure_mcp_connected():
            raise TransportConnectionError("MCP server not connected")

        # For MCP, we still generate ID locally but the server should echo it back
        # We'll use the returned session ID from the server if available
        local_session_id = f"hermes_{uuid.uuid4().hex[:12]}"

        result = await self._mcp_manager.call_tool(
            self._server_id,
            "create_session",
            {
                "session_id": local_session_id,
                "environment": environment or {},
            },
        )

        # Use server-returned session ID if available, otherwise use local
        returned_session_id = result.get("session_id", local_session_id)

        self._active_sessions[returned_session_id] = {
            "created_at": datetime.now(timezone.utc),
            "environment": environment or {},
            "protocol": "mcp",
        }

        logger.debug(f"Created MCP session: {returned_session_id}")
        return returned_session_id

    async def close_worker_session(self, session_id: str) -> bool:
        """Close an isolated worker session.

        Args:
            session_id: Session ID to close (must be the one returned from create_worker_session)

        Returns:
            True if session was closed
        """
        if session_id not in self._active_sessions:
            logger.warning(f"Attempt to close unknown session: {session_id}")
            return False

        session_info = self._active_sessions[session_id]
        protocol = session_info.get("protocol", "mcp")

        success = False
        if protocol == "acp" and self._acp_registry:
            try:
                await self._acp_registry.close(session_id)
                success = True
            except Exception as e:
                logger.warning(f"ACP session close failed: {e}")
                success = False
        else:
            # MCP path
            try:
                result = await self._mcp_manager.call_tool(
                    self._server_id,
                    "close_session",
                    {"session_id": session_id},
                )
                success = result.get("success", False)
            except Exception as e:
                logger.warning(f"MCP session close failed: {e}")
                success = False

        self._active_sessions.pop(session_id, None)
        return success

    async def execute_task(self, task: HermesTask) -> HermesObservation:
        """Execute a task via hermes-agent(EXT) worker.

        Returns an OBSERVATION, not a verdict. hermes-agent(EXT) executes;
        AI-OS decides.

        Args:
            task: HermesTask to execute

        Returns:
            HermesObservation (untrusted, provenance attached)
        """
        # Validate session exists and is active
        if task.session_id not in self._active_sessions:
            return HermesObservation(
                task_id=task.task_id,
                success=False,
                data={},
                error=f"Session not found: {task.session_id}",
                timestamp=datetime.now(timezone.utc),
                session_id=task.session_id,
                provenance=self._create_provenance(
                    task, "unknown", "unknown", "error-exec", "error-corr",
                    "error", ["session_not_found"]
                ),
            )

        session_info = self._active_sessions[task.session_id]
        protocol = session_info.get("protocol", "mcp")

        # Generate execution ID and correlation ID for this call
        execution_id = str(uuid.uuid4())
        correlation_id = str(uuid.uuid4())

        # Determine actual protocol for provenance from session info
        provenance_protocol = session_info.get("provenance_protocol", protocol)
        # For acp_fallback, we're using MCP under the hood, so adapter is mcp_manager
        if provenance_protocol == "acp_fallback":
            adapter_name = "mcp_manager"
        elif provenance_protocol == "acp":
            adapter_name = "acp_adapter"
        else:
            adapter_name = "mcp_manager"

        try:
            if protocol == "acp":
                observation = await self._execute_acp_task(task, execution_id, correlation_id, provenance_protocol)
            else:
                observation = await self._execute_mcp_task(task, execution_id, correlation_id, provenance_protocol)

            # Ensure trust_level is always untrusted
            observation.trust_level = "untrusted"
            return observation

        except SessionNotFoundError:
            return HermesObservation(
                task_id=task.task_id,
                success=False,
                data={},
                error="Session not found",
                timestamp=datetime.now(timezone.utc),
                session_id=task.session_id,
                provenance=self._create_provenance(
                    task, provenance_protocol, adapter_name, execution_id, correlation_id,
                    "error", ["session_not_found"]
                ),
            )
        except ExecutionTimeout:
            return HermesObservation(
                task_id=task.task_id,
                success=False,
                data={},
                error="Execution timeout",
                timestamp=datetime.now(timezone.utc),
                session_id=task.session_id,
                provenance=self._create_provenance(
                    task, provenance_protocol, adapter_name, execution_id, correlation_id,
                    "timeout", ["execution_timeout"]
                ),
            )
        except ExecutionCancelled:
            return HermesObservation(
                task_id=task.task_id,
                success=False,
                data={},
                error="Execution cancelled",
                timestamp=datetime.now(timezone.utc),
                session_id=task.session_id,
                provenance=self._create_provenance(
                    task, provenance_protocol, adapter_name, execution_id, correlation_id,
                    "cancelled", ["execution_cancelled"]
                ),
            )
        except MalformedResponseError as e:
            return HermesObservation(
                task_id=task.task_id,
                success=False,
                data={},
                error=f"Malformed response: {e}",
                timestamp=datetime.now(timezone.utc),
                session_id=task.session_id,
                provenance=self._create_provenance(
                    task, actual_protocol, adapter_name, execution_id, correlation_id,
                    "error", ["malformed_response"]
                ),
            )
        except Exception as e:
            # Generic error handling
            return HermesObservation(
                task_id=task.task_id,
                success=False,
                data={},
                error=str(e),
                timestamp=datetime.now(timezone.utc),
                session_id=task.session_id,
                provenance=self._create_provenance(
                    task, actual_protocol, adapter_name, execution_id, correlation_id,
                    "error", [type(e).__name__]
                ),
            )

    async def _execute_acp_task(
        self,
        task: HermesTask,
        execution_id: str,
        correlation_id: str,
        provenance_protocol: str,
    ) -> HermesObservation:
        """Execute task via ACP adapter."""
        adapter = await self._get_acp_adapter()
        registry = self._acp_registry

        # Validate session
        await registry.validate_isolation(task.session_id)

        # Build prompt text from task
        prompt_text = self._task_to_prompt(task)

        # Execute with retry logic
        last_error = None
        for attempt in range(self._retry_attempts):
            try:
                response = await adapter.prompt(
                    session_id=task.session_id,
                    text=prompt_text,
                    timeout=self._timeout_seconds,
                )
                break
            except ExecutionTimeout:
                last_error = "timeout"
                if attempt < self._retry_attempts - 1:
                    logger.warning(f"ACP execution timeout, retry {attempt + 1}/{self._retry_attempts}")
                    continue
                raise
            except (TransportDisconnectError, TransportConnectionError) as e:
                last_error = str(e)
                if attempt < self._retry_attempts - 1:
                    logger.warning(f"ACP transport error, retry {attempt + 1}/{self._retry_attempts}: {e}")
                    # Try to reconnect
                    try:
                        await adapter.connect()
                        continue
                    except Exception:
                        pass
                raise
        else:
            # All retries exhausted
            raise ExecutionTimeout(f"All retry attempts failed: {last_error}")

        # Normalize ACP response to HermesObservation
        return self._normalize_acp_response(
            response, task, execution_id, correlation_id, provenance_protocol
        )

    async def _execute_mcp_task(
        self,
        task: HermesTask,
        execution_id: str,
        correlation_id: str,
        provenance_protocol: str,
    ) -> HermesObservation:
        """Execute task via MCP manager."""
        if not await self._ensure_mcp_connected():
            raise TransportConnectionError("MCP server not connected")

        try:
            result = await self._mcp_manager.call_tool(
                self._server_id,
                "execute_task",
                {
                    "session_id": task.session_id,
                    "task_type": task.task_type,
                    "description": task.description,
                    "parameters": task.parameters,
                },
            )
        except Exception as e:
            raise TransportConnectionError(f"MCP call failed: {e}")

        return self._normalize_mcp_response(
            result, task, execution_id, correlation_id, provenance_protocol
        )

    def _task_to_prompt(self, task: HermesTask) -> str:
        """Convert HermesTask to ACP prompt text."""
        # Structured prompt for hermes-agent ACP
        prompt = f"Task: {task.description}\n"
        prompt += f"Type: {task.task_type}\n"
        if task.parameters:
            prompt += f"Parameters: {json.dumps(task.parameters, default=str)}\n"
        return prompt

    def _normalize_acp_response(
        self,
        response: dict[str, Any],
        task: HermesTask,
        execution_id: str,
        correlation_id: str,
        provenance_protocol: str,
    ) -> HermesObservation:
        """Normalize ACP response to HermesObservation."""
        stop_reason = response.get("stopReason", "error")
        text = response.get("text", "")

        # Determine success based on stop_reason (not heuristic text matching)
        if stop_reason == "end_turn":
            success = True
            error = None
            exit_status = "completed"
        elif stop_reason == "cancelled":
            success = False
            error = "Execution cancelled"
            exit_status = "cancelled"
        elif stop_reason == "timeout":
            success = False
            error = "Execution timeout"
            exit_status = "timeout"
        elif stop_reason == "error":
            success = False
            error = text or "ACP execution error"
            exit_status = "error"
        else:
            # Unknown stop reason - treat as error
            success = False
            error = f"Unknown stop reason: {stop_reason}"
            exit_status = "error"

        # Parse response data
        data = {}
        if text:
            data["output"] = text
        if "result" in response:
            data["result"] = response["result"]
        if "artifacts" in response:
            data["artifacts"] = response["artifacts"]

        # For acp_fallback, we're using MCP under the hood, so adapter is mcp_manager
        if provenance_protocol == "acp_fallback":
            adapter_name = "mcp_manager"
        elif provenance_protocol == "acp":
            adapter_name = "acp_adapter"
        else:
            adapter_name = "mcp_manager"

        provenance = self._create_provenance(
            task, provenance_protocol, adapter_name, execution_id, correlation_id,
            exit_status,
        )

        return HermesObservation(
            task_id=task.task_id,
            success=success,
            data=data,
            error=error,
            timestamp=datetime.now(timezone.utc),
            session_id=task.session_id,
            provenance=provenance,
        )

    def _normalize_mcp_response(
        self,
        result: dict[str, Any],
        task: HermesTask,
        execution_id: str,
        correlation_id: str,
        provenance_protocol: str,
    ) -> HermesObservation:
        """Normalize MCP response to HermesObservation."""
        success = result.get("success", False)
        data = result.get("result", {})
        error = result.get("error")

        exit_status = "completed" if success else "error"

        # For acp_fallback, we're using MCP under the hood, so adapter is mcp_manager
        if provenance_protocol == "acp_fallback":
            adapter_name = "mcp_manager"
        elif provenance_protocol == "acp":
            adapter_name = "acp_adapter"
        else:
            adapter_name = "mcp_manager"

        provenance = self._create_provenance(
            task, provenance_protocol, adapter_name, execution_id, correlation_id,
            exit_status,
            errors=[error] if error else [],
        )

        return HermesObservation(
            task_id=task.task_id,
            success=success,
            data=data,
            error=error,
            timestamp=datetime.now(timezone.utc),
            session_id=task.session_id,
            provenance=provenance,
        )

    async def navigate(self, session_id: str, url: str) -> HermesObservation:
        """Navigate to a URL in the browser session."""
        task = HermesTask(
            task_id=f"nav_{uuid.uuid4().hex[:8]}",
            task_type="navigation",
            description=f"Navigate to {url}",
            parameters={"url": url},
            session_id=session_id,
        )
        return await self.execute_task(task)

    async def click(self, session_id: str, selector: str) -> HermesObservation:
        """Click an element."""
        task = HermesTask(
            task_id=f"click_{uuid.uuid4().hex[:8]}",
            task_type="click",
            description=f"Click element {selector}",
            parameters={"selector": selector},
            session_id=session_id,
        )
        return await self.execute_task(task)

    async def type_text(self, session_id: str, selector: str, text: str) -> HermesObservation:
        """Type text into an element."""
        task = HermesTask(
            task_id=f"type_{uuid.uuid4().hex[:8]}",
            task_type="type",
            description=f"Type into {selector}",
            parameters={"selector": selector, "text": text},
            session_id=session_id,
        )
        return await self.execute_task(task)

    async def screenshot(self, session_id: str, full_page: bool = False) -> HermesObservation:
        """Take a screenshot."""
        task = HermesTask(
            task_id=f"screenshot_{uuid.uuid4().hex[:8]}",
            task_type="screenshot",
            description="Take screenshot",
            parameters={"full_page": full_page},
            session_id=session_id,
        )
        return await self.execute_task(task)

    async def extract_content(self, session_id: str, selector: str | None = None) -> HermesObservation:
        """Extract page content."""
        task = HermesTask(
            task_id=f"extract_{uuid.uuid4().hex[:8]}",
            task_type="extraction",
            description="Extract page content",
            parameters={"selector": selector},
            session_id=session_id,
        )
        return await self.execute_task(task)

    async def wait_for(self, session_id: str, condition: str, timeout: int = 30) -> HermesObservation:
        """Wait for a condition."""
        task = HermesTask(
            task_id=f"wait_{uuid.uuid4().hex[:8]}",
            task_type="wait",
            description=f"Wait for {condition}",
            parameters={"condition": condition, "timeout": timeout},
            session_id=session_id,
        )
        return await self.execute_task(task)

    def is_session_active(self, session_id: str) -> bool:
        """Check if a worker session is active."""
        return session_id in self._active_sessions

    def get_active_sessions(self) -> list[str]:
        """Get list of active session IDs."""
        return list(self._active_sessions.keys())

    async def cleanup_all(self) -> None:
        """Close all active sessions."""
        session_ids = list(self._active_sessions.keys())
        for session_id in session_ids:
            try:
                await self.close_worker_session(session_id)
            except Exception as e:
                logger.warning(f"Failed to close session {session_id}: {e}")


def get_hermes_bridge(
    mcp_manager=None,
    server_id: str = "hermes_agent_ext",
    protocol: str = "acp",
    fallback_to_mcp: bool = True,
    acp_adapter=None,
    cwd: str = "",
    timeout_seconds: int = 30,
    retry_attempts: int = 3,
    allowed_root: str = "",
    session_idle_timeout_seconds: int = 300,
) -> HermesBridge:
    """Get or create HermesBridge instance."""
    return HermesBridge(
        mcp_manager=mcp_manager,
        server_id=server_id,
        protocol=protocol,
        fallback_to_mcp=fallback_to_mcp,
        acp_adapter=acp_adapter,
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        retry_attempts=retry_attempts,
        allowed_root=allowed_root,
        session_idle_timeout_seconds=session_idle_timeout_seconds,
    )