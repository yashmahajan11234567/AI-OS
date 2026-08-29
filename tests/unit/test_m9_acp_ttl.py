"""M9-N7 — ACP session-TTL hardening tests (spec §11.7, §32.8, §34).

The registry gains an ABSOLUTE max-lifetime TTL alongside the existing idle
timeout. Coverage:

  * TTL disabled (0) → M8 behavior preserved exactly (no expiry, ever)
  * over-TTL session is reaped by cleanup_stale_sessions()
  * continuously-active session (fresh last_used) is STILL reaped by TTL
  * validate_isolation() fails closed at use time with SessionExpiredError
  * idle timeout still works independently of the TTL
  * HermesBridge passes session_ttl_seconds through to its registry
  * observation-only boundary intact: HermesObservation.trust_level stays
    "untrusted" and bridge output is unchanged by TTL hardening
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from aios.adapters.acp_session import (
    AcPSessionRegistry,
    SessionExpiredError,
    SessionNotFoundError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class MockACPAdapter:
    """Minimal duck-typed AcPAdapter double."""

    def __init__(self):
        self.closed: list[str] = []

    async def new_session(self, cwd="", timeout=30):
        return f"acp_{len(self.closed) + len(getattr(self, 'sessions', [])) or 1}"

    async def close_session(self, session_id):
        self.closed.append(session_id)


def make_registry(ttl_seconds: int, idle_seconds: int = 300) -> tuple:
    """(registry, adapter) with a seeded active session."""
    adapter = MockACPAdapter()
    registry = AcPSessionRegistry(
        adapter,
        session_idle_timeout_seconds=idle_seconds,
        session_ttl_seconds=ttl_seconds,
    )
    return registry, adapter


async def seed_session(registry: AcPSessionRegistry, *, age_seconds: float = 0.0,
                       idle_seconds: float = 0.0) -> str:
    """Insert an active session with controlled created_at / last_used."""
    now = datetime.utcnow()
    sid = "acp_seeded"
    registry._sessions[sid] = {
        "cwd": ".",
        "created_at": now - timedelta(seconds=age_seconds),
        "last_used": now - timedelta(seconds=idle_seconds),
        "timeout_seconds": 30,
        "active": True,
    }
    return sid


# ---------------------------------------------------------------------------
# TTL semantics
# ---------------------------------------------------------------------------


class TestTtlDisabledPreservesM8Behavior:
    async def test_zero_ttl_never_expires(self):
        """ttl=0 (default): no absolute cap — old sessions stay valid."""
        registry, _adapter = make_registry(ttl_seconds=0)
        await seed_session(registry, age_seconds=10_000_000)

        assert registry.session_ttl_seconds == 0
        cleaned = await registry.cleanup_stale_sessions()
        assert cleaned == 0
        assert registry.is_active("acp_seeded")

    async def test_negative_ttl_coerced_to_zero(self):
        registry, _adapter = make_registry(ttl_seconds=-50)
        assert registry.session_ttl_seconds == 0


class TestTtlEnforcement:
    async def test_expired_session_reaped_by_cleanup(self):
        registry, adapter = make_registry(ttl_seconds=100)
        await seed_session(registry, age_seconds=150)

        cleaned = await registry.cleanup_stale_sessions()

        assert cleaned == 1
        assert "acp_seeded" in adapter.closed
        assert not registry.is_active("acp_seeded")

    async def test_active_but_old_session_still_reaped(self):
        """The hardening point: continuous activity does NOT defeat the cap."""
        registry, _adapter = make_registry(ttl_seconds=100)
        # Fresh last_used (0s idle) but ancient created_at.
        await seed_session(registry, age_seconds=500, idle_seconds=0)

        cleaned = await registry.cleanup_stale_sessions()

        assert cleaned == 1

    async def test_young_session_survives(self):
        registry, _adapter = make_registry(ttl_seconds=3600)
        await seed_session(registry, age_seconds=10)

        cleaned = await registry.cleanup_stale_sessions()
        assert cleaned == 0
        assert registry.is_active("acp_seeded")

    async def test_idle_timeout_independent_of_ttl(self):
        """Idle path still fires when TTL is disabled (M8 behavior)."""
        registry, adapter = make_registry(ttl_seconds=0, idle_seconds=60)
        await seed_session(registry, idle_seconds=120)

        cleaned = await registry.cleanup_stale_sessions()
        assert cleaned == 1
        assert "acp_seeded" in adapter.closed


class TestUseTimeFailClosed:
    async def test_validate_isolation_rejects_expired(self):
        """Over-TTL use is rejected at validation time, before cleanup runs."""
        registry, _adapter = make_registry(ttl_seconds=100)
        await seed_session(registry, age_seconds=999)

        with pytest.raises(SessionExpiredError):
            await registry.validate_isolation("acp_seeded")
        # The session was NOT silently removed by validation — cleanup owns that.
        assert registry.is_active("acp_seeded")

    async def test_validate_isolation_allows_fresh(self):
        registry, _adapter = make_registry(ttl_seconds=3600)
        await seed_session(registry, age_seconds=5)

        await registry.validate_isolation("acp_seeded")  # no raise

    async def test_unknown_session_still_session_not_found(self):
        registry, _adapter = make_registry(ttl_seconds=100)

        with pytest.raises(SessionNotFoundError):
            await registry.validate_isolation("acp_missing")


# ---------------------------------------------------------------------------
# Bridge wiring + observation boundary
# ---------------------------------------------------------------------------


class TestBridgeWiring:
    async def test_bridge_passes_ttl_to_registry(self, monkeypatch, tmp_path):
        """_get_acp_adapter wires session_ttl_seconds into the registry."""
        from aios.adapters import hermes_bridge as hb
        from aios.adapters.acp_session import AcPSessionRegistry

        created = {}

        class _StubAdapter(MockACPAdapter):
            async def connect(self):
                return True

        def _fake_adapter(*args, **kwargs):
            stub = _StubAdapter()
            created["adapter"] = stub
            return stub

        monkeypatch.setattr(
            "aios.adapters.acp_adapter.AcPAdapter", _fake_adapter
        )

        bridge = hb.HermesBridge(
            mcp_manager=object(),
            protocol="acp",
            cwd=str(tmp_path),  # non-empty so ACP path proceeds
            fallback_to_mcp=False,
            session_ttl_seconds=1234,
        )
        adapter = await bridge._get_acp_adapter()

        assert adapter is created["adapter"]
        assert isinstance(bridge._acp_registry, AcPSessionRegistry)
        assert bridge._acp_registry.session_ttl_seconds == 1234

    def test_bridge_default_ttl_is_zero_m8_preserved(self):
        from aios.adapters.hermes_bridge import HermesBridge

        bridge = HermesBridge(mcp_manager=object(), protocol="mcp")
        assert bridge._session_ttl_seconds == 0

    async def test_observation_boundary_unchanged_by_ttl(self):
        """Spec §11.7: hardening must not touch the observation-only boundary."""
        from aios.adapters.hermes_bridge import HermesBridge, HermesObservation

        assert HermesObservation.trust_level == "untrusted"

        bridge = HermesBridge(mcp_manager=object(), protocol="mcp",
                              server_id="hermes_agent_ext")
        task = type(
            "T", (),
            {"task_id": "t1", "task_type": "browser", "description": "d",
             "parameters": {}, "session_id": "", "provenance": {}},
        )()
        obs = await bridge.execute_task(task)
        # Whatever the outcome, provenance/trust contract is fixed.
        assert obs.trust_level == "untrusted"
