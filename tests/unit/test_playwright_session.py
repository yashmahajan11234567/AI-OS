"""
Unit tests for PlaywrightSessionRegistry (M8-T2).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from aios.adapters.playwright_session import (
    PlaywrightSessionNotFoundError,
    PlaywrightSessionRegistry,
)


@pytest.mark.asyncio
async def test_session_create_and_active():
    """Test basic session creation and active state."""
    registry = PlaywrightSessionRegistry()
    session_id = await registry.create()

    assert registry.is_active(session_id)
    assert session_id in registry.get_active()
    assert session_id.startswith("pw_")


@pytest.mark.asyncio
async def test_session_close_idempotent():
    """Test session close is idempotent."""
    registry = PlaywrightSessionRegistry()
    session_id = await registry.create()

    assert registry.is_active(session_id)
    await registry.close(session_id)
    assert not registry.is_active(session_id)
    assert session_id not in registry.get_active()

    # Double close should be no-op
    await registry.close(session_id)
    assert not registry.is_active(session_id)


@pytest.mark.asyncio
async def test_session_validation():
    """Test session isolation validation."""
    registry = PlaywrightSessionRegistry()
    session_id = await registry.create()

    # Active session should validate
    await registry.validate_isolation(session_id)

    # Unknown session should raise
    with pytest.raises(PlaywrightSessionNotFoundError):
        await registry.validate_isolation("unknown-session")

    # Closed session should raise
    await registry.close(session_id)
    with pytest.raises(PlaywrightSessionNotFoundError):
        await registry.validate_isolation(session_id)


@pytest.mark.asyncio
async def test_cleanup_all():
    """Test cleanup_all removes all sessions."""
    registry = PlaywrightSessionRegistry()

    sessions = []
    for _ in range(5):
        sid = await registry.create()
        sessions.append(sid)

    assert len(registry.get_active()) == 5
    await registry.cleanup_all()
    assert len(registry.get_active()) == 0


@pytest.mark.asyncio
async def test_stale_session_cleanup():
    """Test stale session cleanup."""
    registry = PlaywrightSessionRegistry(session_idle_timeout_seconds=0)

    # Create sessions
    session_id = await registry.create()

    # Manually set last_used far in the past to guarantee staleness
    from datetime import datetime, timedelta
    registry._sessions[session_id]["last_used"] = datetime.utcnow() - timedelta(hours=1)

    cleaned = await registry.cleanup_stale_sessions()
    assert cleaned == 1
    assert not registry.is_active(session_id)


@pytest.mark.asyncio
async def test_multiple_sessions_isolated():
    """Test multiple sessions are isolated."""
    registry = PlaywrightSessionRegistry()

    s1 = await registry.create(execution_id="exec-1")
    s2 = await registry.create(execution_id="exec-2")

    assert s1 != s2
    assert registry.is_active(s1)
    assert registry.is_active(s2)
    assert len(registry.get_active()) == 2

    await registry.close(s1)
    assert not registry.is_active(s1)
    assert registry.is_active(s2)
    assert len(registry.get_active()) == 1

    await registry.cleanup_all()
    assert len(registry.get_active()) == 0
