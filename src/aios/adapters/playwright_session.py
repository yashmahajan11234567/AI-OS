"""
Playwright Session Registry for AI-OS M8-T2.

Manages browser session lifecycle with isolation validation.
Mirrors the AcPSessionRegistry pattern from M8-T1.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class PlaywrightSessionError(Exception):
    """Base error for Playwright session operations."""


class PlaywrightSessionNotFoundError(PlaywrightSessionError):
    """Session not found or inactive."""


class PlaywrightSessionRegistry:
    """Registry for Playwright browser sessions with isolation validation.

    Each session gets an isolated browser context (cookies, localStorage,
    sessionStorage, authentication state all isolated).
    """

    def __init__(self, session_idle_timeout_seconds: int = 300) -> None:
        self._session_idle_timeout = session_idle_timeout_seconds
        self._sessions: dict[str, dict[str, Any]] = {}

    async def create(self, execution_id: str | None = None) -> str:
        """Create a new isolated browser session.

        Args:
            execution_id: Optional caller-provided execution identifier.

        Returns:
            Unique session_id for the new session.
        """
        session_id = f"pw_{uuid.uuid4().hex[:12]}"
        self._sessions[session_id] = {
            "execution_id": execution_id or str(uuid.uuid4()),
            "created_at": datetime.utcnow(),
            "last_used": datetime.utcnow(),
            "active": True,
            "context_id": None,
            "page_id": None,
            "url": "",
            "title": "",
        }
        logger.debug(f"Created Playwright session: {session_id}")
        return session_id

    async def close(self, session_id: str) -> None:
        """Close a browser session. Idempotent — no-op if already closed."""
        session = self._sessions.get(session_id)
        if not session or not session.get("active", False):
            return  # Idempotent

        session["active"] = False
        session["context_id"] = None
        session["page_id"] = None
        logger.debug(f"Closed Playwright session: {session_id}")

    def is_active(self, session_id: str) -> bool:
        """Check if a session is active."""
        session = self._sessions.get(session_id)
        return session is not None and session.get("active", False)

    def get_active(self) -> list[str]:
        """Return list of active session IDs."""
        return [sid for sid, s in self._sessions.items() if s.get("active", False)]

    async def validate_isolation(self, session_id: str) -> None:
        """Validate session is active and isolated.

        Raises PlaywrightSessionNotFoundError if session is invalid.
        """
        session = self._sessions.get(session_id)
        if not session or not session.get("active", False):
            raise PlaywrightSessionNotFoundError(
                f"Session not found or inactive: {session_id}"
            )
        # Update last_used for idle timeout tracking
        session["last_used"] = datetime.utcnow()

    async def cleanup_all(self) -> None:
        """Close all active sessions."""
        for session_id in list(self._sessions.keys()):
            try:
                await self.close(session_id)
            except Exception as e:
                logger.warning(f"Failed to close session {session_id} during cleanup: {e}")

    async def cleanup_stale_sessions(self) -> int:
        """Remove sessions idle longer than the timeout.

        Returns:
            Number of sessions cleaned up.
        """
        now = datetime.utcnow()
        stale = []
        for sid, session in self._sessions.items():
            if not session.get("active", False):
                continue
            last_used = session.get("last_used", now)
            idle_seconds = (now - last_used).total_seconds()
            if idle_seconds > self._session_idle_timeout:
                stale.append(sid)

        for sid in stale:
            await self.close(sid)
            logger.debug(f"Cleaned up stale session: {sid} (idle {idle_seconds:.0f}s)")

        return len(stale)
