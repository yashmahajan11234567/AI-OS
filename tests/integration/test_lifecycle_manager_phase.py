"""
Task 9 — LifecycleManager integration tests (Part 4 §4.3 / Part 3 §3.7).

Verifies, in an integration context:

  * LifecycleManager initializes after Core Components C1–C4.
  * LifecycleManager uses the existing canonical EventBus (C1).
  * LifecycleManager uses the existing ServiceRegistry (C2).
  * LifecycleManager reads ConfigurationManager (C3).
  * LifecycleManager logs through StructuredLogger (C4).
  * Lifecycle events are observable.
  * Shutdown sequencing is deterministic (reverse phase order).
  * Kernel lifecycle state is exposed correctly.
  * No Task 1–8 regressions are introduced (imports resolve).

Only canonical Part-2 EventTypes are asserted (CONFLICT E.1 mapping). No new
EventType is invented.
"""

from __future__ import annotations

import asyncio

import pytest

from aios.core.configuration_manager import (
    ConfigurationManager,
    get_configuration_manager,
    reset_configuration_manager_singleton,
    set_configuration_manager,
)
from aios.core.lifecycle_manager import (
    LifecycleManager,
    LifecycleState,
    reset_lifecycle_manager_singleton,
)
from aios.core.service_registry import (
    ServiceRegistry,
    get_service_registry,
    reset_service_registry_singleton,
)
from aios.core.structured_logger import StructuredLogger, get_logger
from aios.events.core.bus import EventBus, EventBusConfig, reset_event_bus_singleton
from aios.events.core.types import EventType


@pytest.fixture
def core_stack():
    """Wire the four Core Components (C1–C4) for integration."""
    reset_lifecycle_manager_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    # The canonical EventBus is a process-wide singleton (INV-EB-001); reset it
    # so a single fresh instance can be constructed for this fixture.
    reset_event_bus_singleton()

    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    sr = get_service_registry(event_bus=bus)
    cm = get_configuration_manager(event_bus=bus)
    sl = get_logger()

    yield {
        "bus": bus,
        "service_registry": sr,
        "configuration": cm,
        "logger": sl,
    }

    reset_lifecycle_manager_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_event_bus_singleton()


@pytest.fixture
def integrated(core_stack):
    """A LifecycleManager fully wired to C1–C4."""
    lm = LifecycleManager(
        event_bus=core_stack["bus"],
        service_registry=core_stack["service_registry"],
        configuration_manager=core_stack["configuration"],
        logger=core_stack["logger"],
    )
    return lm


# ---------------------------------------------------------------------------
# C1–C4 present; LifecycleManager initializes after them
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_initializes_after_core_components(core_stack, integrated):
    assert integrated.state is LifecycleState.UNINITIALIZED
    # All four Core Components exist and are non-None.
    assert core_stack["bus"] is not None
    assert core_stack["service_registry"] is not None
    assert core_stack["configuration"] is not None
    assert core_stack["logger"] is not None
    state = await integrated.initialize()
    assert state is LifecycleState.OPERATIONAL


@pytest.mark.asyncio
async def test_uses_existing_eventbus(core_stack, integrated):
    await integrated.initialize()
    # Confirm the SAME canonical EventBus instance is wired through.
    assert integrated._event_bus is core_stack["bus"]


@pytest.mark.asyncio
async def test_uses_existing_service_registry(core_stack, integrated):
    await integrated.register_with_service_registry()
    assert integrated._service_registry is core_stack["service_registry"]
    reg = core_stack["service_registry"].get_registration("core.lifecycle")
    assert reg is not None
    assert reg.service is integrated


@pytest.mark.asyncio
async def test_reads_configuration_manager(core_stack, integrated):
    # ConfigurationManager accessor returns the same instance LifecycleManager holds.
    assert integrated._configuration is core_stack["configuration"]


@pytest.mark.asyncio
async def test_logs_through_structured_logger(core_stack, integrated):
    assert integrated._logger is core_stack["logger"]
    await integrated.initialize()  # should not raise; emits structured logs
    assert integrated.is_operational


# ---------------------------------------------------------------------------
# Observable events + ordering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lifecycle_events_observable(core_stack, integrated):
    await core_stack["bus"].initialize()
    await integrated.initialize()
    await integrated.shutdown()
    history = core_stack["bus"].getRecentEvents()
    names = [
        e.eventType.name if hasattr(e.eventType, "name") else str(e.eventType)
        for e in history
    ]
    # Canonical mapped lifecycle events are observable.
    assert EventType.KERNEL_INITIALIZATION_STARTED.name in names
    assert EventType.KERNEL_READY.name in names
    assert EventType.KERNEL_SHUTDOWN_STARTED.name in names
    assert EventType.KERNEL_TERMINATED.name in names


@pytest.mark.asyncio
async def test_phase_completion_event_emitted(core_stack, integrated):
    await core_stack["bus"].initialize()
    await integrated.initialize()
    history = core_stack["bus"].getRecentEvents()
    types = [
        e.eventType.name if hasattr(e.eventType, "name") else str(e.eventType)
        for e in history
    ]
    assert EventType.CORE_MANAGER_INITIALIZED.name in types


# ---------------------------------------------------------------------------
# Deterministic shutdown sequencing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_shutdown_deterministic_reverse_order(core_stack, integrated):
    calls: list[str] = []

    class _M:
        def __init__(self, name):
            self._name = name

        @property
        def name(self):
            return self._name

        @property
        def phase(self):
            # phase is informational; the declared topology drives ordering.
            return 1

        @property
        def dependencies(self):
            return []

        async def initialize(self):
            pass

        async def shutdown(self):
            calls.append(f"shutdown:{self._name}")

        def health_ready(self):
            return True

    # Declared topology names in different phases: StateManager (phase 2),
    # SecurityManager (phase 3). Use two distinct phase-2/phase-3 names.
    s = _M("StateManager")  # phase 2
    sec = _M("SecurityManager")  # phase 3
    integrated.register_manager(s)
    integrated.register_manager(sec)
    await integrated.initialize()
    await integrated.shutdown()
    # Reverse phase order: SecurityManager (phase 3) before StateManager (phase 2).
    assert calls.index("shutdown:SecurityManager") < calls.index("shutdown:StateManager")


@pytest.mark.asyncio
async def test_kernel_lifecycle_state_exposed(core_stack, integrated):
    await integrated.initialize()
    assert integrated.is_operational
    assert integrated.is_initialized
    assert not integrated.is_terminated
    await integrated.shutdown()
    assert integrated.is_terminated
    assert not integrated.is_operational


# ---------------------------------------------------------------------------
# No Task 1–8 regressions (imports resolve)
# ---------------------------------------------------------------------------


def test_core_component_imports_resolve():
    # These must import without error (regression guard).
    from aios.events.core import EventBus as C1  # noqa: F401
    from aios.core.service_registry import ServiceRegistry as C2  # noqa: F401
    from aios.core.configuration_manager import ConfigurationManager as C3  # noqa: F401
    from aios.core.structured_logger import StructuredLogger as C4  # noqa: F401
    from aios.core.lifecycle_manager import LifecycleManager  # noqa: F401
    assert True
