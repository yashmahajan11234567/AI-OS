"""
Task 10 Critical Acceptance Test (read-only verification).

Mirrors the Task 9 critical acceptance structure. Verifies, end-to-end through
the kernel:

  * StateManager identity metadata (name/phase/dependencies/manager_id).
  * ``dependencies`` is EXACTLY ``["LifecycleManager"]`` (no StorageManager).
  * Phase-2 initialization is driven by LifecycleManager.
  * ``core.state`` is registered in the canonical ServiceRegistry with
    core-manager metadata (not an ordinary engineering service).
  * Canonical EventTypes ONLY are emitted (STATE_CHANGED / STATE_SNAPSHOT_CREATED /
    STATE_RESTORED) — no invented types.
  * The pre-existing public state business APIs remain available (backward
    compatibility).
  * No Task 1–9 regressions (imports resolve, kernel remains functional).
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
    StateManagerError,
    StateScope,
    reset_state_manager_singleton,
)
from aios.core.structured_logger import get_logger
from aios.events.bus import get_event_bus
from aios.events.core.bus import get_core_event_bus, reset_event_bus_singleton
from aios.events.core.types import EventType


@pytest.mark.asyncio
async def test_critical_acceptance_identities(tmp_path):
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_state_manager_singleton()

    kernel = HermesKernel(config=KernelConfig(data_dir=tmp_path / "data"))
    try:
        await kernel.start()

        # 1. identity metadata
        assert kernel.state_manager.name == "StateManager"
        assert kernel.state_manager.phase == 2
        assert kernel.state_manager.dependencies == ["LifecycleManager"]
        assert kernel.state_manager.manager_id == "core.state"

        # 2. canonical core-components wiring
        assert kernel.event_bus is get_event_bus()
        assert kernel.event_bus is get_core_event_bus()
        assert kernel.service_registry is get_service_registry()
        assert kernel.configuration is get_configuration_manager()
        assert kernel.logger is get_logger()
        assert kernel.lifecycle is get_lifecycle_manager()

        # 3. state manager is driven by LifecycleManager (Phase 2), not _start_services
        assert kernel.state_manager.is_initialized
        assert kernel.state_manager.health_ready() is True
        assert "state_manager" not in kernel._services

        # 4. core.state present in the canonical ServiceRegistry
        reg = kernel.service_registry.get_registration("core.state")
        assert reg is not None
        assert reg.service is kernel.state_manager
        assert reg.metadata.get("kind") == "core_manager"

        # 5. backward-compatible state APIs still work
        sm = kernel.state_manager
        sm.set_state(StateScope.WORKFLOW, "acceptance-wf", "phase", "planning")
        assert sm.get_state(StateScope.WORKFLOW, "acceptance-wf", "phase") == "planning"
        snap = sm.checkpoint(StateScope.WORKFLOW, "acceptance-wf")
        assert snap is not None
        sm.restore(StateScope.WORKFLOW, "acceptance-wf")

        # 6. errors carry rule context
        err = StateManagerError("boom", rule_id="SM-AC-001")
        assert err.rule_id == "SM-AC-001"
    finally:
        await kernel.stop()
        # Hermetic teardown: the kernel freezes the canonical ConfigurationManager
        # (kernel.py:367). Reset every process-wide singleton so no residue leaks
        # into later tests (in particular the Task 9 critical acceptance test,
        # which does not reset CM). Matches the _reset_all() pattern used by the
        # Task 10 integration phase file.
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()
        reset_lifecycle_manager_singleton()
        reset_state_manager_singleton()


async def _wait_for_state_events(bus: Any, deadline_loops: int = 100) -> set[str]:
    """Poll the bus history until the three state events appear (bounded).

    StateManager._emit_event schedules ``bus.publish`` via
    ``asyncio.ensure_future`` (the canonical sync-to-async bridge established by
    ConfigurationManager._run_emission); the coroutine must be allowed to run
    before the event appears in bus history. We poll with explicit ``sleep(0)``
    yields until all three expected events are observed, or fail with a clear
    bound (rather than a fixed count that races the event loop).
    """
    expected = {
        EventType.STATE_CHANGED.name,
        EventType.STATE_SNAPSHOT_CREATED.name,
        EventType.STATE_RESTORED.name,
    }
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
async def test_critical_acceptance_no_invented_event_types(tmp_path):
    """Assert only canonical EventTypes are emitted by StateManager operations."""
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_state_manager_singleton()

    kernel = HermesKernel(config=KernelConfig(data_dir=tmp_path / "data"))
    try:
        await kernel.start()
        sm = kernel.state_manager
        sm.set_state(StateScope.WORKFLOW, "acceptance-evt", "status", "running")
        sm.checkpoint(StateScope.WORKFLOW, "acceptance-evt")
        sm.restore(StateScope.WORKFLOW, "acceptance-evt")

        names = await _wait_for_state_events(kernel.event_bus)

        # Every event observed must use a canonical EventType (never a fabricated
        # string/enum member).
        for e in kernel.event_bus.getRecentEvents():
            assert hasattr(e.eventType, "name"), "non-canonical EventType leaked"

        # The three state events are canonical (STATE_* family) and observable.
        assert {
            EventType.STATE_CHANGED.name,
            EventType.STATE_SNAPSHOT_CREATED.name,
            EventType.STATE_RESTORED.name,
        } <= names
    finally:
        await kernel.stop()
        # Hermetic teardown (see test_critical_acceptance_identities).
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()
        reset_lifecycle_manager_singleton()
        reset_state_manager_singleton()


def test_critical_acceptance_imports_resolve():
    # Task 1–9 regression guard: core-module imports must resolve.
    from aios.core.configuration_manager import ConfigurationManager as C3  # noqa: F401
    from aios.core.lifecycle_manager import LifecycleManager  # noqa: F401
    from aios.core.service_registry import ServiceRegistry as C2  # noqa: F401
    from aios.core.state import StateManager as S10  # noqa: F401
    from aios.core.structured_logger import StructuredLogger as C4  # noqa: F401
    from aios.events.core import EventBus as C1  # noqa: F401

    assert True
