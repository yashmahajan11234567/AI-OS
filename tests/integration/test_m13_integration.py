"""
M13 — Integration Acceptance Tests (kernel level).

Exercises the live HermesKernel to validate the M13 acceptance categories from
``M13_TEST_AND_ACCEPTANCE_SPEC.md`` end-to-end (no real external systems; mock mode
only, per the safe-default contract):

  1. Authority preservation — AI-OS stays the sole authority; bounded resources
     stay on T2 and never claim AUTHORITATIVE.
  2. Bounded-resource compliance — every M13 adapter is wired and T2/bounded.
  3. Integration pattern compliance — adapters are external resources, not peers.
  4. Security compliance — gate-before-connect is enforced (SecurityManager wired).
  5. Failure recovery compliance — FailureRecoveryManager recovers/degrades/escalates
     under AI-OS authority and emits RECOVERY_ACTION_* events.
  6. Learning & provenance — recovery actions carry aios_owned provenance.
  7. Default-safe — kernel boots in mock mode with zero terminal-contract violations.

All assertions run without network access. Real mode is exercised separately and
gated by AIOS_REAL_INTEGRATION_ENABLED=1 (see tests/unit/test_m13_real_mode_gating.py).
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

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
from aios.events.core.types import EventType


async def _reset_all_singletons():
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


@pytest.fixture
async def booted_kernel():
    await _reset_all_singletons()
    temp_dir = Path(tempfile.mkdtemp())
    from aios.core.kernel import HermesKernel, KernelConfig

    kernel = HermesKernel(config=KernelConfig(data_dir=temp_dir))
    await kernel.start()
    try:
        yield kernel
    finally:
        await kernel.stop()
        await _reset_all_singletons()
        shutil.rmtree(temp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 1-3. Authority preservation + bounded-resource + integration pattern
# ---------------------------------------------------------------------------


class TestM13AuthorityPreservation:
    @pytest.mark.asyncio
    async def test_no_terminal_violations(self, booted_kernel):
        # Authority preservation: no bounded resource claimed AI-OS authority.
        assert booted_kernel.terminal_contract_violations == []

    @pytest.mark.asyncio
    async def test_adapters_bounded_on_t2(self, booted_kernel):
        for adapter in (
            booted_kernel.supabase_adapter,
            booted_kernel.n8n_adapter,
            booted_kernel.obsidian_git_adapter,
        ):
            assert adapter is not None
            assert adapter.terminal == "T2"
            assert adapter.authority_level == "bounded_resource"
            assert adapter.is_mock_mode is True  # default-safe mode

    @pytest.mark.asyncio
    async def test_capabilities_registered(self, booted_kernel):
        reg = booted_kernel.capability_manager
        for cap in (
            "supabase_persistence",
            "n8n_execution",
            "obsidian_git_knowledge",
        ):
            assert reg.get_capability(cap) is not None


# ---------------------------------------------------------------------------
# 4. Security compliance — gate-before-connect wiring
# ---------------------------------------------------------------------------


class TestM13SecurityCompliance:
    @pytest.mark.asyncio
    async def test_security_manager_wired_to_adapters(self, booted_kernel):
        # External adapters consult the kernel SecurityManager (gate-before-connect).
        assert booted_kernel.supabase_adapter._security_manager is booted_kernel.security_manager
        assert booted_kernel.n8n_adapter._security_manager is booted_kernel.security_manager
        assert booted_kernel.obsidian_git_adapter._security_manager is booted_kernel.security_manager

    @pytest.mark.asyncio
    async def test_failure_recovery_security_gated(self, booted_kernel):
        frm = booted_kernel.failure_recovery_manager
        assert frm is not None
        # Recovery reuses the kernel SecurityManager — no external authority.
        assert frm._security_manager is booted_kernel.security_manager
        assert frm._event_bus is booted_kernel.event_bus


# ---------------------------------------------------------------------------
# 5-6. Failure recovery + provenance (live kernel)
# ---------------------------------------------------------------------------


class TestM13FailureRecovery:
    @pytest.mark.asyncio
    async def test_recover_emits_canonical_event(self, booted_kernel):
        captured = []

        class _Bus:
            def publish(self, event):
                captured.append(event)

        frm = booted_kernel.failure_recovery_manager
        frm._event_bus = _Bus()

        rec = await frm.recover(
            "supabase_adapter",
            local_fallback=lambda: {"status": "success"},
        )
        assert rec.outcome == "recovered"
        assert rec.provenance["authority"] == "aios_owned"
        assert captured, "expected RECOVERY_ACTION_* event on canonical bus"
        assert captured[0].eventType in (
            EventType.RECOVERY_ACTION_COMPLETED,
            EventType.RECOVERY_ACTION_DISPATCHED,
            EventType.RECOVERY_ACTION_FAILED,
        )

    @pytest.mark.asyncio
    async def test_degraded_when_external_unavailable(self, booted_kernel):
        frm = booted_kernel.failure_recovery_manager

        def always_fail():
            return {"status": "failure"}

        rec = await frm.recover("n8n_adapter", local_fallback=always_fail)
        # External resource unavailable -> AI-OS degrades to local operation,
        # never elevating the external system.
        assert rec.outcome == "degraded"
        assert rec.provenance["authority"] == "aios_owned"


# ---------------------------------------------------------------------------
# 7. Default-safe boot
# ---------------------------------------------------------------------------


class TestM13DefaultSafe:
    @pytest.mark.asyncio
    async def test_kernel_boots_operational_mock_mode(self, booted_kernel):
        assert booted_kernel.running is True
        # Zero authority violations and all adapters in mock mode: the safe default.
        assert booted_kernel.terminal_contract_violations == []
        assert booted_kernel.failure_recovery_manager is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
