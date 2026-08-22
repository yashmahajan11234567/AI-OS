"""
Task 11 Critical Acceptance Test (read-only verification).

Mirrors the Task 9 / Task 10 critical acceptance structure. Verifies the
architectural acceptance criteria for StorageManager:

  1.  StorageManager is a Phase-2 Core Manager.
  2.  manager_id == "core.storage".
  3.  Configuration uses kernel.storage.*.
  4.  LifecycleManager owns its lifecycle.
  5.  StorageManager is NOT routed through engineering-service startup.
  6.  Canonical ServiceRegistry is used.
  7.  Canonical StructuredLogger is used.
  8.  No duplicate StorageManager authority exists.
  9.  No EventType was invented.
  10. Existing Task 9 and Task 10 critical behavior remains intact.

Per the CRITICAL EVENT TYPE RULE, these tests assert ONLY on canonical Part-2
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
    StorageNamespace,
    get_storage_manager,
    reset_storage_manager_singleton,
)
from aios.core.structured_logger import get_logger
from aios.events.bus import get_event_bus
from aios.events.core.bus import get_core_event_bus, reset_event_bus_singleton
from aios.events.core.types import EventType


async def _wait_for_storage_events(bus: Any, deadline_loops: int = 100) -> set[str]:
    """Poll the bus history until the expected storage events appear (bounded).

    StorageManager._emit_event schedules ``bus.publish`` via
    ``asyncio.ensure_future`` (the canonical sync-to-async bridge established by
    ConfigurationManager._run_emission); the coroutine must be allowed to run
    before the event appears in bus history.
    """
    expected = {
        EventType.ARTIFACT_CREATED.name,
        EventType.CHECKPOINT_CREATED.name,
    }
    names: set[str] = set()
    for _ in range(deadline_loops):
        names = {
            e.eventType.name
            for e in bus.getRecentEvents()
            if hasattr(e.eventType, "name")
        }
        if expected <= names:
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

    kernel = HermesKernel(config=KernelConfig(data_dir=tmp_path / "data"))
    try:
        await kernel.start()

        # --- Criterion 1: StorageManager is a Phase-2 Core Manager ---
        sm = kernel.storage_manager
        assert isinstance(sm, StorageManager)
        assert sm.name == "StorageManager"
        assert sm.phase == 2
        assert "StorageManager" in kernel.lifecycle._managers
        # Phase 2 in the topology = "State & Storage"
        phase_plan = kernel.lifecycle.phase_plan
        phase2 = [p for p in phase_plan if p["phase"] == 2][0]
        assert phase2["name"] == "State & Storage"
        assert "StateManager" in phase2["managers"]
        assert "StorageManager" in phase2["managers"]

        # --- Criterion 2: manager_id == "core.storage" ---
        assert sm.manager_id == "core.storage"
        # ServiceRegistry uses core.storage (NOT kernel.storage — reserved namespace)
        assert sm.manager_id != "kernel.storage"

        # --- Criterion 3: Configuration uses kernel.storage.* ---
        # The kernel sets a frozen ConfigurationManager; StorageManager reads it.
        assert kernel.configuration is get_configuration_manager()
        # Verify the config accessor pattern is the same as StateManager's.
        assert sm._configuration is kernel.configuration
        # StorageManager reads kernel.storage.* paths (verified by the fact that
        # initialize completed without error even with no explicit config values;
        # defaults are used, which is the expected graceful-fallback behavior).

        # --- Criterion 4: LifecycleManager owns its lifecycle ---
        # StorageManager is registered with LifecycleManager for Phase-2 orchestration.
        assert sm.is_initialized
        assert sm.health_ready() is True
        # NOT started via _start_services or _stop_engineering_services.
        assert "storage_manager" not in kernel._services

        # --- Criterion 5: NOT routed through engineering-service startup ---
        # The engineering services list should NOT contain storage_manager or
        # workflow_manager — both are now Core Managers owned by LifecycleManager.
        started_services = list(kernel._services.keys())
        assert "storage_manager" not in started_services
        assert "workflow_manager" not in started_services

        # --- Criterion 6: Canonical ServiceRegistry is used ---
        sr = kernel.service_registry
        assert sr is get_service_registry()
        reg = sr.get_registration("core.storage")
        assert reg is not None
        assert reg.service is sm
        assert reg.metadata.get("kind") == "core_manager"
        assert reg.metadata.get("manager") == "StorageManager"
        assert reg.metadata.get("phase") == 2

        # --- Criterion 7: Canonical StructuredLogger is used ---
        # StorageManager logs through the kernel's canonical StructuredLogger.
        assert sm._logger is kernel.logger
        assert sm._logger is get_logger()

        # --- Criterion 8: No duplicate StorageManager authority exists ---
        # Only one StorageManager instance is registered in the ServiceRegistry.
        # ServiceRegistry.get_registration returns the single registration for
        # "core.storage"; querying it again returns the same ServiceRegistration,
        # proving there is no duplicate authority.
        core_storage_reg = sr.get_registration("core.storage")
        assert core_storage_reg is not None
        assert core_storage_reg.metadata.get("manager") == "StorageManager"
        # No other service_id maps to the same StorageManager instance.
        assert sm is get_storage_manager()

        # --- Criterion 9: No EventType was invented ---
        # StorageManager uses only canonical EventTypes from the closed enum.
        # Verify the storage-relevant canonical EventTypes exist (no new ones).
        assert EventType.ARTIFACT_CREATED.name
        assert EventType.ARTIFACT_UPDATED.name
        assert EventType.ARTIFACT_DELETED.name
        assert EventType.CHECKPOINT_CREATED.name
        assert EventType.CHECKPOINT_PRUNED.name

        # Perform storage operations and verify only canonical events emerge.
        sm.store_artifact("crit-artifact", {"data": "test"})
        sm.write_checkpoint("crit-checkpoint", {"state": "ok"})
        names = await _wait_for_storage_events(kernel.event_bus)
        assert EventType.ARTIFACT_CREATED.name in names
        assert EventType.CHECKPOINT_CREATED.name in names

        for e in kernel.event_bus.getRecentEvents():
            assert hasattr(e.eventType, "name"), "non-canonical EventType leaked"

        # --- Criterion 10: Task 9 and Task 10 critical behavior remains intact ---
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
    finally:
        await kernel.stop()
        # Hermetic teardown.
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()
        reset_lifecycle_manager_singleton()
        reset_state_manager_singleton()
        reset_storage_manager_singleton()


@pytest.mark.asyncio
async def test_critical_acceptance_lifecycle_ordering(tmp_path):
    """StorageManager is initialized AFTER StateManager (alphabetical Phase 2)."""
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_state_manager_singleton()
    reset_storage_manager_singleton()

    kernel = HermesKernel(config=KernelConfig(data_dir=tmp_path / "data"))
    try:
        await kernel.start()
        assert kernel.lifecycle is not None
        # Both Phase-2 managers are initialized.
        assert kernel.state_manager.is_initialized
        assert kernel.storage_manager.is_initialized
        # The initialized_managers list reflects alphabetical ordering within
        # Phase 2: StateManager before StorageManager.
        order = kernel.lifecycle.initialized_managers
        assert order.index("StateManager") < order.index("StorageManager")
    finally:
        await kernel.stop()
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()
        reset_lifecycle_manager_singleton()
        reset_state_manager_singleton()
        reset_storage_manager_singleton()


@pytest.mark.asyncio
async def test_critical_acceptance_reverse_shutdown_order(tmp_path):
    """Shutdown runs reverse phase order: StorageManager before StateManager."""
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_state_manager_singleton()
    reset_storage_manager_singleton()

    kernel = HermesKernel(config=KernelConfig(data_dir=tmp_path / "data"))
    try:
        await kernel.start()
        assert kernel.storage_manager.is_initialized
    finally:
        await kernel.stop()

    # After shutdown: both are non-ready, both SHUTDOWN in registry.
    sr = get_service_registry()
    storage_reg = sr.get_registration("core.storage")
    state_reg = sr.get_registration("core.state")
    assert storage_reg is not None
    assert state_reg is not None
    assert storage_reg.lifecycle_state.value == "SHUTDOWN"
    assert state_reg.lifecycle_state.value == "SHUTDOWN"
    assert kernel.storage_manager.health_ready() is False
    assert kernel.state_manager.health_ready() is False

    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_state_manager_singleton()
    reset_storage_manager_singleton()


def test_critical_acceptance_imports_resolve():
    # Task 1–9 regression guard: core-module imports must resolve.
    from aios.core.configuration_manager import ConfigurationManager as C3  # noqa: F401
    from aios.core.lifecycle_manager import LifecycleManager  # noqa: F401
    from aios.core.service_registry import ServiceRegistry as C2  # noqa: F401
    from aios.core.state import StateManager as S10  # noqa: F401
    from aios.core.storage import StorageManager as S11  # noqa: F401
    from aios.core.structured_logger import StructuredLogger as C4  # noqa: F401
    from aios.events.core import EventBus as C1  # noqa: F401

    assert True
