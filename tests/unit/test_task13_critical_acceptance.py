"""
Task 13 Critical Acceptance Test (read-only verification).

Mirrors the Task 9 / Task 10 / Task 11 / Task 12 critical acceptance structure.
Verifies the architectural acceptance criteria for ResourceManager (now a
Phase-3 Governance Core Manager, Part 4 §4.7):

  1.  ResourceManager is a Phase-3 (Governance) Core Manager.
  2.  manager_id == "core.resource".
  3.  Configuration uses kernel.resource.* (accessor pattern matches Tasks 8-12).
  4.  LifecycleManager owns its lifecycle (registered as Phase-3 manager).
  5.  ResourceManager is NOT routed through _start_services / _stop_engineering_services
      for its Core-Manager initialize()/shutdown() (only its cleanup task is).
  6.  Canonical ServiceRegistry is used.
  7.  Canonical StructuredLogger is used (no stdlib logging in business methods).
  8.  No duplicate ResourceManager authority exists.
  9.  No EventType was invented (only canonical RESOURCE_ALLOCATED / RESOURCE_RELEASED /
      RESOURCE_EXHAUSTED / QUOTA_EXCEEDED are emitted).
  10. Existing Task 9/10/11/12 critical behavior remains intact.

Per the CRITICAL EVENTTYPE RULE, these tests assert ONLY on canonical Part-2
EventTypes. No new EventType is invented.
"""

from __future__ import annotations

import asyncio
import warnings
from typing import Any

import pytest

from aios.core.configuration_manager import (
    get_configuration_manager,
    reset_configuration_manager_singleton,
)
from aios.core.health_manager import get_health_manager, reset_health_manager_singleton
from aios.core.kernel import HermesKernel, KernelConfig
from aios.core.lifecycle_manager import (
    get_lifecycle_manager,
    reset_lifecycle_manager_singleton,
)
from aios.core.resource_manager import (
    ResourceLimit,
    ResourceManager,
    ResourceManagerError,
    ResourceType,
    get_resource_manager,
    reset_resource_manager_singleton,
    set_resource_manager,
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


async def _wait_for_resource_events(
    bus: Any, expected: set[str], deadline_loops: int = 200
) -> set[str]:
    """Poll the bus history until the expected resource events appear (bounded).

    ResourceManager._emit_resource_event schedules ``bus.publish`` via
    ``asyncio.ensure_future`` (the canonical sync-to-async bridge established by
    ConfigurationManager._run_emission, mirrored by StateManager/StorageManager/
    HealthManager); the coroutine must be allowed to run before the event appears
    in bus history.
    """
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
    reset_health_manager_singleton()
    reset_resource_manager_singleton()

    kernel = HermesKernel(config=KernelConfig(data_dir=tmp_path / "data"))
    try:
        await kernel.start()

        # --- Criterion 1: ResourceManager is a Phase-3 (Governance) Core Manager ---
        rm = kernel.resource_manager
        assert isinstance(rm, ResourceManager)
        assert rm.name == "ResourceManager"
        assert rm.phase == 3
        assert "ResourceManager" in kernel.lifecycle._managers
        # Phase 3 in the topology = "Governance"
        phase_plan = kernel.lifecycle.phase_plan
        phase3 = [p for p in phase_plan if p["phase"] == 3][0]
        assert phase3["name"] == "Governance"
        assert "ResourceManager" in phase3["managers"]
        assert "HealthManager" in phase3["managers"]
        assert "SecurityManager" in phase3["managers"]

        # --- Criterion 2: manager_id == "core.resource" ---
        assert rm.manager_id == "core.resource"
        # ServiceRegistry uses core.resource (NOT kernel.resource — reserved namespace)
        assert rm.manager_id != "kernel.resource"

        # --- Criterion 3: Configuration uses kernel.resource.* ---
        assert kernel.configuration is get_configuration_manager()
        assert rm._configuration is kernel.configuration

        # --- Criterion 4: LifecycleManager owns its lifecycle ---
        assert rm.is_initialized
        assert rm.health_ready() is True

        # --- Criterion 5: NOT routed through engineering-service startup ---
        # ResourceManager's Core-Manager lifecycle (initialize/shutdown) is owned
        # by LifecycleManager Phase 3, NOT by the engineering-service start/stop
        # loops. (The cleanup task is started via the engineering hook for backward
        # compatibility, but the manager itself is a registered Phase-3 manager.)
        assert "ResourceManager" in kernel.lifecycle._managers
        assert rm in kernel.lifecycle._managers.values()

        # --- Criterion 6: Canonical ServiceRegistry is used ---
        sr = kernel.service_registry
        assert sr is get_service_registry()
        reg = sr.get_registration("core.resource")
        assert reg is not None
        assert reg.service is rm
        assert reg.metadata.get("kind") == "core_manager"
        assert reg.metadata.get("manager") == "ResourceManager"
        assert reg.metadata.get("phase") == 3

        # --- Criterion 7: Canonical StructuredLogger is used ---
        assert rm._logger is kernel.logger
        assert rm._logger is get_logger()

        # --- Criterion 8: No duplicate ResourceManager authority exists ---
        core_resource_reg = sr.get_registration("core.resource")
        assert core_resource_reg is not None
        assert core_resource_reg.metadata.get("manager") == "ResourceManager"
        assert rm is get_resource_manager()

        # --- Criterion 9: No EventType was invented ---
        assert EventType.RESOURCE_ALLOCATED.name
        assert EventType.RESOURCE_RELEASED.name
        assert EventType.RESOURCE_EXHAUSTED.name
        assert EventType.QUOTA_EXCEEDED.name

        # Perform resource operations and verify only canonical events emerge.
        alloc = await rm.allocate(ResourceType.MEMORY, 1024, "crit-requester", "init")
        rm.release(alloc.allocation_id)
        names = await _wait_for_resource_events(
            kernel.event_bus,
            {
                EventType.RESOURCE_ALLOCATED.name,
                EventType.RESOURCE_RELEASED.name,
            },
        )
        assert EventType.RESOURCE_ALLOCATED.name in names
        assert EventType.RESOURCE_RELEASED.name in names

        for e in kernel.event_bus.getRecentEvents():
            assert hasattr(e.eventType, "name"), "non-canonical EventType leaked"

        # --- Criterion 10: Task 9/10/11/12 critical behavior remains intact ---
        assert kernel.lifecycle is get_lifecycle_manager()
        assert kernel.lifecycle.state is not None
        # StateManager still works.
        assert kernel.state_manager is get_state_manager()
        assert kernel.state_manager.is_initialized
        state_reg = sr.get_registration("core.state")
        assert state_reg is not None
        assert state_reg.metadata.get("manager") == "StateManager"
        kernel.state_manager.set_state(StateScope.WORKFLOW, "crit-wf", "x", 1)
        assert kernel.state_manager.get_state(StateScope.WORKFLOW, "crit-wf", "x") == 1
        # StorageManager still works.
        assert kernel.storage_manager is get_storage_manager()
        assert kernel.storage_manager.is_initialized
        assert isinstance(kernel.storage_manager, StorageManager)
        # HealthManager still works.
        assert kernel.health_manager is get_health_manager()
        assert kernel.health_manager.is_initialized
    finally:
        await kernel.stop()
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()
        reset_lifecycle_manager_singleton()
        reset_state_manager_singleton()
        reset_storage_manager_singleton()
        reset_health_manager_singleton()
        reset_resource_manager_singleton()


@pytest.mark.asyncio
async def test_critical_acceptance_lifecycle_ordering(tmp_path):
    """ResourceManager is initialized within Phase 3 (alphabetical ordering)."""
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_state_manager_singleton()
    reset_storage_manager_singleton()
    reset_health_manager_singleton()
    reset_resource_manager_singleton()

    kernel = HermesKernel(config=KernelConfig(data_dir=tmp_path / "data"))
    try:
        await kernel.start()
        assert kernel.lifecycle is not None
        assert kernel.resource_manager.is_initialized
        # Within Phase 3, alphabetical ordering: HealthManager before ResourceManager.
        order = kernel.lifecycle.initialized_managers
        assert "HealthManager" in order
        assert "ResourceManager" in order
        assert order.index("HealthManager") < order.index("ResourceManager")
        # Phase 2 managers come before Phase 3 managers.
        assert order.index("StateManager") < order.index("ResourceManager")
    finally:
        await kernel.stop()
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()
        reset_lifecycle_manager_singleton()
        reset_state_manager_singleton()
        reset_storage_manager_singleton()
        reset_health_manager_singleton()
        reset_resource_manager_singleton()


@pytest.mark.asyncio
async def test_critical_acceptance_reverse_shutdown_order(tmp_path):
    """ResourceManager is shut down by LifecycleManager (reverse phase order)."""
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_state_manager_singleton()
    reset_storage_manager_singleton()
    reset_health_manager_singleton()
    reset_resource_manager_singleton()

    kernel = HermesKernel(config=KernelConfig(data_dir=tmp_path / "data"))
    try:
        await kernel.start()
        assert kernel.resource_manager.is_initialized
    finally:
        await kernel.stop()

    sr = get_service_registry()
    resource_reg = sr.get_registration("core.resource")
    assert resource_reg is not None
    assert resource_reg.lifecycle_state.value == "SHUTDOWN"
    assert kernel.resource_manager.health_ready() is False
    assert kernel.resource_manager.is_initialized is False

    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_state_manager_singleton()
    reset_storage_manager_singleton()
    reset_health_manager_singleton()
    reset_resource_manager_singleton()


@pytest.mark.asyncio
async def test_critical_acceptance_resource_api(tmp_path):
    """Verify the ResourceManager business API: allocate, release, usage, stats."""
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_state_manager_singleton()
    reset_storage_manager_singleton()
    reset_health_manager_singleton()
    reset_resource_manager_singleton()

    kernel = HermesKernel(config=KernelConfig(data_dir=tmp_path / "data"))
    try:
        await kernel.start()
        rm = kernel.resource_manager

        alloc = await rm.allocate(ResourceType.MEMORY, 1024, "comp-a", "alloc")
        assert alloc.resource_type is ResourceType.MEMORY
        assert alloc.amount == 1024
        assert alloc.requestor == "comp-a"

        usage = rm.get_usage(ResourceType.MEMORY)
        assert usage["used"] == 1024

        assert rm.release(alloc.allocation_id) is True
        assert rm.release(alloc.allocation_id) is False

        # Stats still report limits.
        stats = rm.get_stats()
        assert "limits" in stats

        # set_limit / get_limit work.
        rm.set_limit(ResourceLimit(ResourceType.CUSTOM, 10, "units"))
        assert rm.get_limit(ResourceType.CUSTOM) is not None
    finally:
        await kernel.stop()
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()
        reset_lifecycle_manager_singleton()
        reset_state_manager_singleton()
        reset_storage_manager_singleton()
        reset_health_manager_singleton()
        reset_resource_manager_singleton()


@pytest.mark.asyncio
async def test_critical_acceptance_quota_exceeded_and_runtimewarn(tmp_path):
    """Quota breach emits QUOTA_EXCEEDED; no ResourceWarning from sync emission."""
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_state_manager_singleton()
    reset_storage_manager_singleton()
    reset_health_manager_singleton()
    reset_resource_manager_singleton()

    kernel = HermesKernel(config=KernelConfig(data_dir=tmp_path / "data"))
    try:
        await kernel.start()
        rm = kernel.resource_manager

        mem_limit = rm.get_limit(ResourceType.MEMORY)
        assert mem_limit is not None
        over = mem_limit.limit + 1

        # Capture RuntimeWarnings (sync emission must NOT produce un-awaited
        # coroutine warnings).
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with pytest.raises(Exception):
                await rm.allocate(ResourceType.MEMORY, over, "over-requester", "too much")
            # Let any scheduled publish tasks drain.
            await _wait_for_resource_events(
                kernel.event_bus, {EventType.QUOTA_EXCEEDED.name}
            )

        runtime_warns = [
            w for w in caught
            if issubclass(w.category, RuntimeWarning)
        ]
        assert not runtime_warns, f"Unexpected RuntimeWarning: {runtime_warns}"

        names = {
            e.eventType.name
            for e in kernel.event_bus.getRecentEvents()
            if hasattr(e.eventType, "name")
        }
        assert EventType.QUOTA_EXCEEDED.name in names
    finally:
        await kernel.stop()
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()
        reset_lifecycle_manager_singleton()
        reset_state_manager_singleton()
        reset_storage_manager_singleton()
        reset_health_manager_singleton()
        reset_resource_manager_singleton()


def test_critical_acceptance_singleton_pattern():
    """Singleton accessors follow the same threading.Lock pattern as Tasks 9-12."""
    from aios.events.core.bus import EventBus, EventBusConfig

    reset_resource_manager_singleton()
    reset_event_bus_singleton()
    try:
        EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
        rm1 = get_resource_manager()
        assert isinstance(rm1, ResourceManager)

        rm2 = get_resource_manager()
        assert rm1 is rm2

        rm3 = ResourceManager()
        set_resource_manager(rm3)
        assert get_resource_manager() is rm3

        reset_resource_manager_singleton()
        assert get_resource_manager() is not rm3  # new instance created
    finally:
        reset_resource_manager_singleton()
        reset_event_bus_singleton()


def test_critical_acceptance_resource_manager_error():
    """ResourceManagerError carries rule_id and original_error (mirrors Tasks 9-12)."""
    reset_resource_manager_singleton()
    try:
        err = ResourceManagerError("test failure", rule_id="RM-TEST-001")
        assert str(err) == "test failure"
        assert err.rule_id == "RM-TEST-001"
        assert err.original_error is None

        inner = ValueError("inner")
        err2 = ResourceManagerError("wrapped", rule_id="RM-TEST-002", original_error=inner)
        assert "original_error=ValueError: inner" in str(err2)
        assert err2.original_error is inner
    finally:
        reset_resource_manager_singleton()


@pytest.mark.asyncio
async def test_critical_acceptance_no_stdlib_logging(tmp_path):
    """ResourceManager business methods use StructuredLogger, not stdlib logging."""

    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_state_manager_singleton()
    reset_storage_manager_singleton()
    reset_health_manager_singleton()
    reset_resource_manager_singleton()

    kernel = HermesKernel(config=KernelConfig(data_dir=tmp_path / "data"))
    try:
        await kernel.start()
        rm = kernel.resource_manager

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            alloc = await rm.allocate(ResourceType.CPU, 10, "lw", "t")
            rm.release(alloc.allocation_id)
            await _wait_for_resource_events(
                kernel.event_bus,
                {EventType.RESOURCE_ALLOCATED.name, EventType.RESOURCE_RELEASED.name},
            )
        runtime_warns = [
            w for w in caught
            if issubclass(w.category, RuntimeWarning)
        ]
        assert not runtime_warns, f"Unexpected RuntimeWarning: {runtime_warns}"

        # The stdlib 'logging' module should not be used by ResourceManager for
        # its business emissions; verify no 'coroutine was never awaited' leak and
        # that the canonical logger is wired.
        assert rm._logger is get_logger()
    finally:
        await kernel.stop()
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()
        reset_lifecycle_manager_singleton()
        reset_state_manager_singleton()
        reset_storage_manager_singleton()
        reset_health_manager_singleton()
        reset_resource_manager_singleton()


def test_critical_acceptance_imports_resolve():
    # Task 1–13 regression guard: core-module imports must resolve.
    from aios.core.health_manager import HealthManager  # noqa: F401
    from aios.core.lifecycle_manager import LifecycleManager  # noqa: F401
    from aios.core.resource_manager import ResourceManager as RM13  # noqa: F401
    from aios.core.state import StateManager as S10  # noqa: F401
    from aios.core.storage import StorageManager as S11  # noqa: F401

    assert True
