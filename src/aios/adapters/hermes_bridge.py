"""
Hermes Bridge for AI-OS M5-GATE-REALIZE.

AI-OS-side bridge to hermes-agent(EXT) via MCP/ACP.
- Provides MCP fallback connection
- Supports ACP upgrade later
- Isolates worker session
- Attaches provenance
- Returns observations ONLY

hermes-agent(EXT) MUST NOT:
- Issue AI-OS verdicts
- Become decision authority
- Bypass SecurityManager
- Modify kernel policy
- Approve/reject implementation
- Become a second orchestrator

Real Hermes execution remains blocked until C11/license conditions are resolved.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from aios.core.mcp_manager import get_mcp_manager


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


class HermesBridge:
    """AI-OS-side HermesBridge for hermes-agent(EXT) integration.

    The external hermes-agent repository remains external/gitignored.
    This bridge connects through the approved MCP fallback.
    Provides an interface that can support ACP upgrade later.
    Isolates the worker session and attaches provenance.
    Returns observations only - hermes-agent(EXT) has no decision authority.
    """

    def __init__(
        self,
        mcp_manager=None,
        server_id: str = "hermes_agent_ext",
    ) -> None:
        """Initialize Hermes bridge.

        Args:
            mcp_manager: MCPManager instance (uses global if None)
            server_id: MCP server identifier for hermes-agent(EXT)
        """
        self._mcp_manager = mcp_manager or get_mcp_manager()
        self._server_id = server_id
        self._active_sessions: dict[str, dict[str, Any]] = {}

    async def _ensure_connected(self) -> bool:
        """Ensure connection to hermes-agent(EXT) MCP server."""
        status = self._mcp_manager.get_server_status(self._server_id)
        if not status or not status.connected:
            return await self._mcp_manager.connect(self._server_id)
        return True

    def _create_session_id(self) -> str:
        """Create unique session ID for isolation."""
        return f"hermes_{uuid.uuid4().hex[:12]}"

    def _create_provenance(self, task: HermesTask, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        """Create provenance metadata for an observation."""
        provenance = {
            "session_id": task.session_id,
            "worker": "hermes_agent_ext",
            "server": self._server_id,
            "timestamp": datetime.utcnow().isoformat(),
            "environment": "ai_os_hermes_bridge",
            "interaction": task.task_type,
            "source": "hermes_bridge",
            "task_id": task.task_id,
        }
        if extra:
            provenance.update(extra)
        return provenance

    async def create_worker_session(self, environment: dict[str, Any] | None = None) -> str:
        """Create an isolated worker session.

        Args:
            environment: Optional environment configuration for the session

        Returns:
            Session ID for the isolated session
        """
        if not await self._ensure_connected():
            raise RuntimeError("Hermes bridge server not connected")

        session_id = self._create_session_id()

        # Create session via MCP
        result = await self._mcp_manager.call_tool(
            self._server_id,
            "create_session",
            {
                "session_id": session_id,
                "environment": environment or {},
            },
        )

        self._active_sessions[session_id] = {
            "created_at": datetime.utcnow(),
            "environment": environment or {},
        }

        return session_id

    async def close_worker_session(self, session_id: str) -> bool:
        """Close an isolated worker session.

        Args:
            session_id: Session ID to close

        Returns:
            True if session was closed
        """
        result = await self._mcp_manager.call_tool(
            self._server_id,
            "close_session",
            {"session_id": session_id},
        )

        self._active_sessions.pop(session_id, None)
        return result.get("success", False)

    async def execute_task(self, task: HermesTask) -> HermesObservation:
        """Execute a task via hermes-agent(EXT) worker.

        Returns an OBSERVATION, not a verdict. hermes-agent(EXT) executes;
        AI-OS decides.

        Args:
            task: HermesTask to execute

        Returns:
            HermesObservation (untrusted, provenance attached)
        """
        if not await self._ensure_connected():
            raise RuntimeError("Hermes bridge server not connected")

        # Create provenance
        provenance = self._create_provenance(task)

        # Emit event
        call_id = f"hermes_{task.task_id}_{datetime.utcnow().timestamp()}"

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
                call_id=call_id,
            )

            # Build observation (NOT verdict)
            observation = HermesObservation(
                task_id=task.task_id,
                success=result.get("success", False),
                data=result.get("result", {}),
                error=result.get("error"),
                timestamp=datetime.utcnow(),
                session_id=task.session_id,
                provenance=provenance,
            )

            return observation

        except Exception as e:
            return HermesObservation(
                task_id=task.task_id,
                success=False,
                data={},
                error=str(e),
                timestamp=datetime.utcnow(),
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


def get_hermes_bridge(
    mcp_manager=None,
    server_id: str = "hermes_agent_ext",
) -> HermesBridge:
    """Get or create HermesBridge instance."""
    return HermesBridge(mcp_manager=mcp_manager, server_id=server_id)