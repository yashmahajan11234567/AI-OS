"""
ACP Session Registry for AI-OS M8-T1.

Manages ACP session lifecycle with isolation validation and cleanup.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from aios.adapters.acp_adapter import AcPAdapter, SessionNotFoundError

logger = logging.getLogger(__name__)


class SessionExpiredError(SessionNotFoundError):
    """Session exceeded its absolute max lifetime (M9-N7 TTL hardening).

    Subclasses :class:`SessionNotFoundError` so existing callers that treat
    expiry as "session gone" keep working unchanged.
    """

    pass


class AcPSessionRegistry:
    """Registry for ACP session lifecycle management."""

    def __init__(
        self,
        adapter: AcPAdapter,
        session_idle_timeout_seconds: int = 300,
        session_ttl_seconds: int = 0,
    ) -> None:
        """Initialize session registry.

        Args:
            adapter: AcPAdapter instance for session operations
            session_idle_timeout_seconds: Max idle time before session considered stale
            session_ttl_seconds: Absolute max lifetime for any session regardless
                of activity (M9-N7 hardening). 0 disables the absolute cap —
                only the idle timeout applies. Default 0 preserves M8 behavior.
        """
        self._adapter = adapter
        self._session_idle_timeout = session_idle_timeout_seconds
        self._session_ttl = max(0, int(session_ttl_seconds))
        self._sessions: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    @property
    def session_ttl_seconds(self) -> int:
        """Configured absolute session TTL (0 = disabled)."""
        return self._session_ttl

    def _is_expired(self, meta: dict[str, Any], now: datetime) -> bool:
        """Return True when the session exceeds the absolute TTL."""
        if self._session_ttl <= 0:
            return False
        created_at = meta.get("created_at")
        if created_at is None:
            return False
        age = (now - created_at).total_seconds()
        return age >= self._session_ttl

    async def create(self, cwd: str, timeout_seconds: int) -> str:
        """Create session, register, return session_id.

        Args:
            cwd: Working directory for the session
            timeout_seconds: Timeout for session creation

        Returns:
            Session ID (UUID string)
        """
        async with self._lock:
            session_id = await self._adapter.new_session(cwd=cwd, timeout=timeout_seconds)

            self._sessions[session_id] = {
                "cwd": cwd,
                "created_at": datetime.utcnow(),
                "last_used": datetime.utcnow(),
                "timeout_seconds": timeout_seconds,
                "active": True,
            }
            logger.debug(f"Registered ACP session: {session_id}")
            return session_id

    async def close(self, session_id: str) -> None:
        """Close session, unregister. Double-close is no-op.

        Args:
            session_id: Session ID to close
        """
        async with self._lock:
            session_meta = self._sessions.get(session_id)
            if not session_meta:
                logger.warning(f"Close called for unknown session: {session_id}")
                return  # Idempotent

            if not session_meta.get("active", False):
                logger.debug(f"Session {session_id} already inactive")
                return  # Idempotent

            try:
                await self._adapter.close_session(session_id)
            except Exception as e:
                logger.warning(f"Error closing ACP session {session_id}: {e}")
            finally:
                session_meta["active"] = False
                session_meta["closed_at"] = datetime.utcnow()
                del self._sessions[session_id]
                logger.debug(f"Unregistered ACP session: {session_id}")

    def is_active(self, session_id: str) -> bool:
        """Check if session is active."""
        session = self._sessions.get(session_id)
        return session is not None and session.get("active", False)

    def get_active(self) -> list[str]:
        """Get list of active session IDs."""
        return [
            sid for sid, meta in self._sessions.items()
            if meta.get("active", False)
        ]

    async def cleanup_all(self) -> None:
        """Close all active sessions."""
        async with self._lock:
            session_ids = list(self._sessions.keys())
            for session_id in session_ids:
                try:
                    await self._adapter.close_session(session_id)
                except Exception as e:
                    logger.warning(f"Failed to close session {session_id}: {e}")
            self._sessions.clear()

    async def validate_isolation(self, session_id: str) -> None:
        """Validate session isolation - ensure session belongs to this registry.

        M9-N7: additionally enforces the absolute TTL at use time (fail-closed)
        — an over-lifetime session is rejected even before cleanup runs.

        Args:
            session_id: Session ID to validate

        Raises:
            SessionNotFoundError: If session not found or not active
            SessionExpiredError: If session exceeded its absolute max lifetime
        """
        session = self._sessions.get(session_id)
        if not session or not session.get("active", False):
            raise SessionNotFoundError(f"Session not found or inactive: {session_id}")

        if self._is_expired(session, datetime.utcnow()):
            raise SessionExpiredError(
                f"Session {session_id} exceeded absolute lifetime "
                f"({self._session_ttl}s); use is rejected"
            )

        # Update last used timestamp
        session["last_used"] = datetime.utcnow()

    async def cleanup_stale_sessions(self) -> int:
        """Clean up sessions that exceeded idle timeout OR absolute TTL.

        M9-N7: a session is stale when EITHER bound is violated — long-lived
        but continuously-active sessions are reaped by the absolute cap.

        Returns:
            Number of sessions cleaned up
        """
        cleaned = 0
        now = datetime.utcnow()
        stale_sessions = []
        expired_sessions = []

        async with self._lock:
            for session_id, meta in self._sessions.items():
                if not meta.get("active", False):
                    continue
                if self._is_expired(meta, now):
                    expired_sessions.append(session_id)
                    continue
                last_used = meta.get("last_used", meta.get("created_at", now))
                if now - last_used > timedelta(seconds=self._session_idle_timeout):
                    stale_sessions.append(session_id)

            for session_id in expired_sessions + stale_sessions:
                reason = (
                    "absolute TTL exceeded"
                    if session_id in expired_sessions
                    else "idle timeout exceeded"
                )
                try:
                    await self._adapter.close_session(session_id)
                except Exception as e:
                    logger.warning(
                        f"Failed to close session {session_id} ({reason}): {e}"
                    )
                finally:
                    if session_id in self._sessions:
                        del self._sessions[session_id]
                        cleaned += 1

        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} stale ACP sessions")

        return cleaned
