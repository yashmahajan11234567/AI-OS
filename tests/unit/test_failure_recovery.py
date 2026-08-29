"""
M13 — Failure Recovery Manager unit tests (M13_FAILURE_RECOVERY_SPEC.md).

Verifies bounded, AI-OS-authoritative recovery for external (bounded) resources:
  * Classification routes failures to the correct M13 category.
  * Recovery is bounded (retry budget + capped backoff) — no recovery loops.
  * Local fallback recovers; exhausted retries degrade gracefully to AI-OS-local
    operation (external resource unavailable).
  * No local fallback escalates to the AI-OS self-loop decision (not a gateway).
  * Security gate-before-continue is fail-closed (external violation -> blocked).
  * Every recovery action carries aios_owned provenance (no external authority).
  * Recovery outcomes are emitted on the canonical EventBus (RECOVERY_ACTION_*).
  * The live kernel constructs a FailureRecoveryManager accessible via property.
"""

from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from aios.core.failure_recovery import (
    FailureRecoveryManager,
    FailureCategory,
    RecoveryOutcome,
)
from aios.events.core.types import EventType


@pytest.fixture
def manager():
    return FailureRecoveryManager(max_retries=3, backoff_base_seconds=0.0)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


class TestClassification:
    def test_hint_overrides(self, manager):
        assert manager.classify("x", category_hint=FailureCategory.SELF_LOOP) == (
            FailureCategory.SELF_LOOP
        )

    def test_infers_persistence(self, manager):
        assert manager.classify("supabase_adapter") == FailureCategory.PERSISTENCE
        assert manager.classify("obsidian_git_adapter") == FailureCategory.PERSISTENCE

    def test_infers_integration(self, manager):
        assert manager.classify("n8n_adapter") == FailureCategory.INTEGRATION
        assert manager.classify("playwright_mcp_adapter") == FailureCategory.INTEGRATION

    def test_infers_dashboard(self, manager):
        assert manager.classify("dashboard_service") == FailureCategory.DASHBOARD

    def test_infers_self_loop(self, manager):
        assert manager.classify("self_loop_engine") == FailureCategory.SELF_LOOP

    def test_defaults_bounded_execution(self, manager):
        assert manager.classify("unknown_component") == FailureCategory.BOUNDED_EXECUTION


# ---------------------------------------------------------------------------
# Recovery outcomes
# ---------------------------------------------------------------------------


class TestRecoveryOutcomes:
    @pytest.mark.asyncio
    async def test_local_fallback_recovers(self, manager):
        calls = {"n": 0}

        def fb():
            calls["n"] += 1
            return {"status": "success", "ok": True}

        rec = await manager.recover("supabase_adapter", local_fallback=fb)
        assert rec.outcome == RecoveryOutcome.RECOVERED.value
        assert rec.attempts == 1
        assert calls["n"] == 1
        assert rec.provenance["authority"] == "aios_owned"

    @pytest.mark.asyncio
    async def test_retries_then_recovers(self, manager):
        calls = {"n": 0}

        def fb():
            calls["n"] += 1
            if calls["n"] < 2:
                return {"status": "failure"}
            return {"status": "success"}

        rec = await manager.recover("n8n_adapter", local_fallback=fb)
        assert rec.outcome == RecoveryOutcome.RECOVERED.value
        assert rec.attempts == 2

    @pytest.mark.asyncio
    async def test_degraded_when_fallback_exhausted(self, manager):
        def fb():
            return {"status": "error"}

        rec = await manager.recover("obsidian_git_adapter", local_fallback=fb)
        assert rec.outcome == RecoveryOutcome.DEGRADED.value
        assert rec.attempts == manager._max_retries

    @pytest.mark.asyncio
    async def test_escalated_when_no_fallback(self, manager):
        rec = await manager.recover("n8n_adapter")
        assert rec.outcome == RecoveryOutcome.ESCALATED.value
        assert rec.attempts == 0

    @pytest.mark.asyncio
    async def test_bounded_retry_count(self, manager):
        calls = {"n": 0}

        def fb():
            calls["n"] += 1
            return None  # failure sentinel

        rec = await manager.recover("supabase_adapter", local_fallback=fb)
        # Bounded: exactly max_retries attempts, never more.
        assert calls["n"] == manager._max_retries
        assert rec.outcome in (
            RecoveryOutcome.DEGRADED.value,
            RecoveryOutcome.ESCALATED.value,
        )


# ---------------------------------------------------------------------------
# Security gate (fail-closed)
# ---------------------------------------------------------------------------


class TestSecurityGate:
    @pytest.mark.asyncio
    async def test_deny_blocks_recovery(self, manager):
        sec = MagicMock()
        sec.authorize.return_value = MagicMock(value="deny")
        manager.set_security_manager(sec)
        rec = await manager.recover(
            "supabase_adapter",
            local_fallback=lambda: {"status": "success"},
            security_action="supabase_recover",
            security_resource="supabase://db",
        )
        assert rec.outcome == RecoveryOutcome.FAILED.value
        assert "SecurityManager denied" in rec.detail

    @pytest.mark.asyncio
    async def test_allow_continues_recovery(self, manager):
        sec = MagicMock()
        sec.authorize.return_value = MagicMock(value="allow")
        manager.set_security_manager(sec)
        rec = await manager.recover(
            "supabase_adapter",
            local_fallback=lambda: {"status": "success"},
            security_action="supabase_recover",
        )
        assert rec.outcome == RecoveryOutcome.RECOVERED.value


# ---------------------------------------------------------------------------
# Provenance + audit events
# ---------------------------------------------------------------------------


class TestProvenanceAndAudit:
    @pytest.mark.asyncio
    async def test_provenance_aios_owned(self, manager):
        rec = await manager.recover("n8n_adapter", local_fallback=lambda: True)
        assert rec.provenance["authority"] == "aios_owned"
        assert rec.provenance["semantic_owner"] == "aios_kernel"

    @pytest.mark.asyncio
    async def test_emits_recovery_event(self, manager):
        captured = []

        class _Bus:
            def publish(self, event):
                captured.append(event)

        manager._event_bus = _Bus()
        rec = await manager.recover("supabase_adapter", local_fallback=lambda: True)
        assert captured, "expected a RECOVERY_ACTION_* event"
        assert captured[0].eventType in (
            EventType.RECOVERY_ACTION_COMPLETED,
            EventType.RECOVERY_ACTION_DISPATCHED,
            EventType.RECOVERY_ACTION_FAILED,
        )

    @pytest.mark.asyncio
    async def test_record_lookup(self, manager):
        rec = await manager.recover("n8n_adapter", local_fallback=lambda: True)
        assert manager.get_record(rec.recovery_id) is rec
        assert rec in manager.list_records()


# ---------------------------------------------------------------------------
# Live kernel wiring
# ---------------------------------------------------------------------------


def _reset_all_singletons():
    from aios.core.capability_manager import reset_capability_manager_singleton
    from aios.core.configuration_manager import reset_configuration_manager_singleton
    from aios.core.health_manager import reset_health_manager_singleton
    from aios.core.lifecycle_manager import reset_lifecycle_manager_singleton
    from aios.core.observability_manager import reset_observability_manager_singleton
    from aios.core.resource_manager import reset_resource_manager_singleton
    from aios.core.security_manager import reset_security_manager_singleton
    from aios.core.service_registry import reset_service_registry_singleton
    from aios.core.state import reset_state_manager_singleton
    from aios.core.storage import reset_storage_manager_singleton
    from aios.core.structured_logger import reset_structured_logger_singleton
    from aios.core.workflow import reset_workflow_manager_singleton
    from aios.events.core.bus import reset_event_bus_singleton

    for fn in (
        reset_observability_manager_singleton,
        reset_capability_manager_singleton,
        reset_security_manager_singleton,
        reset_health_manager_singleton,
        reset_resource_manager_singleton,
        reset_workflow_manager_singleton,
        reset_storage_manager_singleton,
        reset_state_manager_singleton,
        reset_lifecycle_manager_singleton,
        reset_structured_logger_singleton,
        reset_configuration_manager_singleton,
        reset_service_registry_singleton,
        reset_event_bus_singleton,
    ):
        fn()


@pytest.mark.asyncio
async def test_kernel_constructs_failure_recovery_manager():
    from aios.core.kernel import HermesKernel, KernelConfig

    _reset_all_singletons()
    temp_dir = Path(tempfile.mkdtemp())
    kernel = HermesKernel(config=KernelConfig(data_dir=temp_dir))
    try:
        await kernel.start()
        assert kernel.failure_recovery_manager is not None
        # It is wired to the kernel SecurityManager (gate-before-continue).
        assert kernel.failure_recovery_manager._security_manager is kernel.security_manager
        # And reuses the canonical EventBus for RECOVERY_ACTION_* audit events.
        assert kernel.failure_recovery_manager._event_bus is kernel.event_bus
    finally:
        await kernel.stop()
        _reset_all_singletons()
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
