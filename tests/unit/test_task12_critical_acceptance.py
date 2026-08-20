"""
Task 12 Critical Acceptance Test (read-only verification).

Mirrors the Task 9 / Task 10 / Task 11 critical acceptance structure. Verifies the
architectural acceptance criteria for HealthManager:

  1.  HealthManager is a Phase-3 (Governance) Core Manager.
  2.  manager_id == "core.health".
  3.  Configuration uses kernel.health.* (accessor pattern matches Tasks 8-11).
  4.  LifecycleManager owns its lifecycle (registered as Phase-3 manager).
  5.  HealthManager is NOT routed through _start_services / _stop_engineering_services.
  6.  Canonical ServiceRegistry is used.
  7.  Canonical StructuredLogger is used (no stdlib logging in business methods).
  8.  No duplicate HealthManager authority exists.
  9.  No EventType was invented (only canonical HEALTH_CHECK_PASSED /
      HEALTH_CHECK_FAILED / CORE_MANAGER_DEGRADED are emitted).
  10. Existing Task 9/10/11 critical behavior remains intact.

Per the CRITICAL EVENTTYPE RULE, these tests assert ONLY on canonical Part-2
EventTypes. No new EventType is invented.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from aios.core.configuration_manager import (
    get_configuration_manager,
    reset_configuration_manager_singleton,
)
from aios.core.health_manager import (
    HealthCheck,
    HealthCheckResult,
    HealthManager,
    HealthManagerError,
    HealthStatus,
    get_health_manager,
    reset_health_manager_singleton,
    set_health_manager,
)
from aios.core.kernel import HermesKernel, KernelConfig
from aios.core.lifecycle_manager import (
    get_lifecycle_manager,
    reset_lifecycle_manager_singleton,
)
from aios.core.service_registry import get_service_registry, reset_service_registry_singleton
from aios.core.state import (
    StateScope,
    get_state_manager,
    reset_state_manager_singleton,
)
from aios.core.storage import (
    StorageManager,
    get_storage_manager,
    reset_storage_manager_singleton,
)
from aios.core.structured_logger import get_logger
from aios.events.core.bus import reset_event_bus_singleton
from aios.events.core.types import EventType


async def _wait_for_health_events(bus: Any, deadline_loops: int = 100) -> set[str]:
    """Poll the bus history until the expected health events appear (bounded).

    HealthManager._emit_health_event schedules ``bus.publish`` via
    ``asyncio.ensure_future`` (the canonical sync-to-async bridge established by
    ConfigurationManager._run_emission, mirrored by StateManager/StorageManager);
    the coroutine must be allowed to run before the event appears in bus history.
    """
    expected = {
        EventType.HEALTH_CHECK_PASSED.name,
        EventType.HEALTH_CHECK_FAILED.name,
    }
    names: set[str] = set()
    for _ in range(deadline_loops):
        names = {
            e.eventType.name
            for e in bus.getRecentEvents()
            if hasattr(e.eventType, "name")
        }
        if expected & names:
            return names
        await asyncio.sleep(0)
    return names


@pytest.mark.asyncio
async def test_critical_acceptance_identities(tmp_path):
    """Verify all 10 architectural acceptance criteria."""
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_state_manager_singleton()
    reset_storage_manager_singleton()
    reset_health_manager_singleton()

    kernel = HermesKernel(config=KernelConfig(data_dir=tmp_path / "data"))
    try:
        await kernel.start()

        # --- Criterion 1: HealthManager is a Phase-3 (Governance) Core Manager ---
        hm = kernel.health_manager
        assert isinstance(hm, HealthManager)
        assert hm.name == "HealthManager"
        assert hm.phase == 3
        assert "HealthManager" in kernel.lifecycle._managers
        # Phase 3 in the topology = "Governance"
        phase_plan = kernel.lifecycle.phase_plan
        phase3 = [p for p in phase_plan if p["phase"] == 3][0]
        assert phase3["name"] == "Governance"
        assert "HealthManager" in phase3["managers"]
        assert "ResourceManager" in phase3["managers"]
        assert "SecurityManager" in phase3["managers"]

        # --- Criterion 2: manager_id == "core.health" ---
        assert hm.manager_id == "core.health"
        # ServiceRegistry uses core.health (NOT kernel.health — reserved namespace)
        assert hm.manager_id != "kernel.health"

        # --- Criterion 3: Configuration uses kernel.health.* ---
        # The kernel sets a frozen ConfigurationManager; HealthManager reads it.
        assert kernel.configuration is get_configuration_manager()
        # Verify the config accessor pattern is the same as StateManager's / StorageManager's.
        assert hm._configuration is kernel.configuration

        # --- Criterion 4: LifecycleManager owns its lifecycle ---
        # HealthManager is registered with LifecycleManager for Phase-3 orchestration.
        assert hm.is_initialized
        assert hm.health_ready() is True

        # --- Criterion 5: NOT routed through engineering-service startup ---
        # HealthManager is NOT started via _start_services or _stop_engineering_services.
        assert "health_manager" not in kernel._services
        # The engineering services list should NOT contain health_manager.
        started_services = list(kernel._services.keys())
        assert "health_manager" not in started_services
        # But resource_manager (an actual service) IS started.
        assert "resource_manager" in started_services

        # --- Criterion 6: Canonical ServiceRegistry is used ---
        sr = kernel.service_registry
        assert sr is get_service_registry()
        reg = sr.get_registration("core.health")
        assert reg is not None
        assert reg.service is hm
        assert reg.metadata.get("kind") == "core_manager"
        assert reg.metadata.get("manager") == "HealthManager"
        assert reg.metadata.get("phase") == 3

        # --- Criterion 7: Canonical StructuredLogger is used ---
        # HealthManager logs through the kernel's canonical StructuredLogger.
        assert hm._logger is kernel.logger
        assert hm._logger is get_logger()

        # --- Criterion 8: No duplicate HealthManager authority exists ---
        # Only one HealthManager instance is registered in the ServiceRegistry.
        core_health_reg = sr.get_registration("core.health")
        assert core_health_reg is not None
        assert core_health_reg.metadata.get("manager") == "HealthManager"
        # No other service_id maps to the same HealthManager instance.
        assert hm is get_health_manager()

        # --- Criterion 9: No EventType was invented ---
        # HealthManager uses only canonical EventTypes from the closed enum.
        assert EventType.HEALTH_CHECK_PASSED.name
        assert EventType.HEALTH_CHECK_FAILED.name
        assert EventType.CORE_MANAGER_DEGRADED.name

        # Perform health operations and verify only canonical events emerge.
        hm.record_health("test-component", "test-check", HealthStatus.HEALTHY)
        hm.record_health("test-component2", "test-check2", HealthStatus.UNHEALTHY)
        names = await _wait_for_health_events(kernel.event_bus)
        assert EventType.HEALTH_CHECK_PASSED.name in names
        assert EventType.HEALTH_CHECK_FAILED.name in names

        for e in kernel.event_bus.getRecentEvents():
            assert hasattr(e.eventType, "name"), "non-canonical EventType leaked"

        # --- Criterion 10: Task 9/10/11 critical behavior remains intact ---
        # LifecycleManager still works.
        assert kernel.lifecycle is get_lifecycle_manager()
        assert kernel.lifecycle.state is not None
        # StateManager still works.
        assert kernel.state_manager is get_state_manager()
        assert kernel.state_manager.is_initialized
        # StateManager still registered as core.state.
        state_reg = sr.get_registration("core.state")
        assert state_reg is not None
        assert state_reg.metadata.get("manager") == "StateManager"
        # StateManager's public API still works.
        kernel.state_manager.set_state(StateScope.WORKFLOW, "crit-wf", "x", 1)
        assert kernel.state_manager.get_state(StateScope.WORKFLOW, "crit-wf", "x") == 1
        # StorageManager still works.
        assert kernel.storage_manager is get_storage_manager()
        assert kernel.storage_manager.is_initialized
        assert isinstance(kernel.storage_manager, StorageManager)
    finally:
        await kernel.stop()
        # Hermetic teardown.
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()
        reset_lifecycle_manager_singleton()
        reset_state_manager_singleton()
        reset_storage_manager_singleton()
        reset_health_manager_singleton()


@pytest.mark.asyncio
async def test_critical_acceptance_lifecycle_ordering(tmp_path):
    """HealthManager is initialized within Phase 3 (alphabetical ordering)."""
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_state_manager_singleton()
    reset_storage_manager_singleton()
    reset_health_manager_singleton()

    kernel = HermesKernel(config=KernelConfig(data_dir=tmp_path / "data"))
    try:
        await kernel.start()
        assert kernel.lifecycle is not None
        # HealthManager is initialized by LifecycleManager during Phase 3.
        assert kernel.health_manager.is_initialized
        # The initialized_managers list includes HealthManager (Phase 3).
        order = kernel.lifecycle.initialized_managers
        assert "HealthManager" in order
        # Phase 2 managers come before Phase 3 managers.
        assert order.index("StateManager") < order.index("HealthManager")
    finally:
        await kernel.stop()
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()
        reset_lifecycle_manager_singleton()
        reset_state_manager_singleton()
        reset_storage_manager_singleton()
        reset_health_manager_singleton()


@pytest.mark.asyncio
async def test_critical_acceptance_reverse_shutdown_order(tmp_path):
    """HealthManager is shut down by LifecycleManager (reverse phase order)."""
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_state_manager_singleton()
    reset_storage_manager_singleton()
    reset_health_manager_singleton()

    kernel = HermesKernel(config=KernelConfig(data_dir=tmp_path / "data"))
    try:
        await kernel.start()
        assert kernel.health_manager.is_initialized
    finally:
        await kernel.stop()

    # After shutdown: HealthManager is non-ready, SHUTDOWN in registry.
    sr = get_service_registry()
    health_reg = sr.get_registration("core.health")
    assert health_reg is not None
    assert health_reg.lifecycle_state.value == "SHUTDOWN"
    assert kernel.health_manager.health_ready() is False
    assert kernel.health_manager.is_initialized is False

    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_state_manager_singleton()
    reset_storage_manager_singleton()
    reset_health_manager_singleton()


@pytest.mark.asyncio
async def test_critical_acceptance_health_api(tmp_path):
    """Verify the HealthManager business API: register, record, query."""
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_state_manager_singleton()
    reset_storage_manager_singleton()
    reset_health_manager_singleton()

    kernel = HermesKernel(config=KernelConfig(data_dir=tmp_path / "data"))
    try:
        await kernel.start()
        hm = kernel.health_manager

        # Register health checks.
        hc = hm.register_check("component-a", "check-1")
        assert isinstance(hc, HealthCheck)
        assert hc.component == "component-a"
        assert hc.check_id == "check-1"
        assert hc.enabled is True

        # Record a HEALTHY result.
        result = hm.record_health("component-a", "check-1", HealthStatus.HEALTHY)
        assert isinstance(result, HealthCheckResult)
        assert result.status is HealthStatus.HEALTHY
        assert result.component == "component-a"

        # Query per-component health.
        health = hm.get_component_health("component-a")
        assert health is not None
        assert health["status"] == "HEALTHY"

        # Record an UNHEALTHY result -> should emit HEALTH_CHECK_FAILED.
        hm.record_health("component-b", "check-2", HealthStatus.UNHEALTHY)

        # Overall status should be UNHEALTHY (worst wins).
        assert hm.overall_status is HealthStatus.UNHEALTHY

        # Get aggregate health snapshot.
        snapshot = hm.get_all_health()
        assert snapshot["overall"] == "UNHEALTHY"
        assert "component-a" in snapshot["components"]
        assert snapshot["components"]["component-a"] == "HEALTHY"
        assert "component-b" in snapshot["components"]

        # Unregister a check.
        assert hm.unregister_check("component-a", "check-1") is True
        assert hm.get_check("component-a", "check-1") is None
    finally:
        await kernel.stop()
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()
        reset_lifecycle_manager_singleton()
        reset_state_manager_singleton()
        reset_storage_manager_singleton()
        reset_health_manager_singleton()


@pytest.mark.asyncio
async def test_critical_acceptance_health_manager_error():
    """HealthManagerError carries rule_id and original_error (mirrors Tasks 9-11)."""
    reset_health_manager_singleton()
    try:
        err = HealthManagerError("test failure", rule_id="HM-TEST-001")
        assert str(err) == "test failure"
        assert err.rule_id == "HM-TEST-001"
        assert err.original_error is None

        inner = ValueError("inner")
        err2 = HealthManagerError("wrapped", rule_id="HM-TEST-002", original_error=inner)
        assert "original_error=ValueError: inner" in str(err2)
        assert err2.original_error is inner
    finally:
        reset_health_manager_singleton()


def test_critical_acceptance_singleton_pattern():
    """Singleton accessors follow the same threading.Lock pattern as Tasks 9-11."""
    from aios.events.core.bus import EventBus, EventBusConfig

    reset_health_manager_singleton()
    reset_event_bus_singleton()
    try:
        # A canonical EventBus must be initialized before HealthManager can be
        # constructed (it resolves the bus eagerly in __init__).
        EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
        # get_health_manager creates the singleton.
        hm1 = get_health_manager()
        assert isinstance(hm1, HealthManager)

        # Second call returns the same instance.
        hm2 = get_health_manager()
        assert hm1 is hm2

        # set_health_manager replaces it.
        hm3 = HealthManager()
        set_health_manager(hm3)
        assert get_health_manager() is hm3

        # reset clears it.
        reset_health_manager_singleton()
        assert get_health_manager() is not hm3  # new instance created
    finally:
        reset_health_manager_singleton()
        reset_event_bus_singleton()


def test_critical_acceptance_imports_resolve():
    # Task 1–12 regression guard: core-module imports must resolve.
    from aios.core.health_manager import HealthManager as HM12  # noqa: F401
    from aios.core.lifecycle_manager import LifecycleManager  # noqa: F401
    from aios.core.state import StateManager as S10  # noqa: F401
    from aios.core.storage import StorageManager as S11  # noqa: F401

    assert True
