"""
Task 9 — LifecycleManager unit tests (Part 4 §4.3).

Covers the 26 required unit areas: construction, singleton, metadata, initial
state, valid/invalid transitions, thread-safe state access, initialize,
initialize idempotency/rejection, shutdown, shutdown idempotency, deterministic
phase ordering, dependency validation, phase completion, init failure, rollback,
rollback idempotency, rollback failure, degraded, recovery, event emission,
event ordering, ServiceRegistry registration, ConfigurationManager integration,
StructuredLogger integration, and unavailable-dependency behavior.

Per the CRITICAL EVENT TYPE RULE, these tests assert ONLY on the canonical
Part-2 EventTypes the LifecycleManager is permitted to emit (mapping from the
Part-4 PascalCase names documented as CONFLICT E.1). No new EventType is
invented.
"""

from __future__ import annotations

import asyncio

import pytest

from aios.core.lifecycle_manager import (
    ICoreManager,
    LifecycleManager,
    LifecycleManagerError,
    LifecycleState,
    get_lifecycle_manager,
    reset_lifecycle_manager_singleton,
    set_lifecycle_manager,
)
from aios.events.core.bus import EventBus, EventBusConfig, reset_event_bus_singleton
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def bus():
    reset_event_bus_singleton()
    b = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    return b


@pytest.fixture
def lm(bus):
    """A LifecycleManager wired to a real canonical EventBus but no registry/CM/SL."""
    reset_lifecycle_manager_singleton()
    mgr = LifecycleManager(event_bus=bus)
    yield mgr
    reset_lifecycle_manager_singleton()


class _FakeManager:
    """Minimal ICoreManager used to exercise orchestration without real managers."""

    def __init__(self, name: str, *, ready: bool = True, fail_init: bool = False,
                 fail_shutdown: bool = False, deps: list[str] | None = None):
        self._name = name
        self._ready = ready
        self.fail_init = fail_init
        self.fail_shutdown = fail_shutdown
        self._deps = deps or []
        self.initialized = False
        self.shutdown_called = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def phase(self) -> int:
        return 2

    @property
    def dependencies(self) -> list[str]:
        return list(self._deps)

    async def initialize(self) -> None:
        if self.fail_init:
            raise RuntimeError(f"{self._name} init failure")
        self.initialized = True

    async def shutdown(self) -> None:
        if self.fail_shutdown:
            raise RuntimeError(f"{self._name} shutdown failure")
        self.shutdown_called = True

    def health_ready(self) -> bool:
        return self._ready


# ---------------------------------------------------------------------------
# 1. construction / 3. metadata / 4. initial state
# ---------------------------------------------------------------------------


def test_construction(lm):
    assert isinstance(lm, LifecycleManager)
    assert lm.name == "LifecycleManager"
    assert lm.phase == 1
    assert lm.dependencies == [
        "EventBus", "ServiceRegistry", "ConfigurationManager", "StructuredLogger"
    ]
    assert lm.manager_id == "core.lifecycle"


def test_initial_state(lm):
    assert lm.state is LifecycleState.UNINITIALIZED


def test_icoremanager_protocol_satisfied(lm):
    # ICoreManager is a structural Protocol; verify LifecycleManager satisfies
    # the contract surface (name/phase/dependencies/initialize/shutdown/
    # health_ready). isinstance is unreliable for runtime_checkable protocols
    # with property members, so we assert the surface directly.
    assert hasattr(lm, "name") and lm.name == "LifecycleManager"
    assert hasattr(lm, "phase") and lm.phase == 1
    assert hasattr(lm, "dependencies")
    assert hasattr(lm, "initialize")
    assert hasattr(lm, "shutdown")
    assert hasattr(lm, "health_ready")


# ---------------------------------------------------------------------------
# 2. singleton behavior
# ---------------------------------------------------------------------------


def test_singleton_accessor_returns_same():
    reset_lifecycle_manager_singleton()
    first = get_lifecycle_manager()
    second = get_lifecycle_manager()
    assert second is first
    reset_lifecycle_manager_singleton()


def test_set_singleton_overrides():
    reset_lifecycle_manager_singleton()
    custom = LifecycleManager()
    set_lifecycle_manager(custom)
    assert get_lifecycle_manager() is custom
    reset_lifecycle_manager_singleton()


# ---------------------------------------------------------------------------
# 5. valid state transitions / 6. invalid transitions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_valid_transitions_via_api(lm):
    await lm.initialize()
    assert lm.state is LifecycleState.OPERATIONAL
    await lm.mark_degraded(["ResourceManager"])
    assert lm.state is LifecycleState.DEGRADED
    await lm.begin_recovery()
    assert lm.state is LifecycleState.RECOVERY_IN_PROGRESS
    await lm.complete_recovery(success=True)
    assert lm.state is LifecycleState.OPERATIONAL
    await lm.shutdown()
    assert lm.state is LifecycleState.TERMINATED


@pytest.mark.asyncio
async def test_invalid_transition_rejected(lm):
    # UNINITIALIZED -> OPERATIONAL is not allowed directly.
    with pytest.raises(LifecycleManagerError):
        await lm._transition(LifecycleState.OPERATIONAL)  # type: ignore[call]


@pytest.mark.asyncio
async def test_terminal_state_blocks_transitions(lm):
    await lm.initialize()
    await lm.shutdown()
    assert lm.state is LifecycleState.TERMINATED
    with pytest.raises(LifecycleManagerError):
        await lm._transition(LifecycleState.OPERATIONAL)  # type: ignore[call]


# ---------------------------------------------------------------------------
# 7. thread-safe state access
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_thread_safe_state_access(lm):
    results: list[LifecycleState] = []

    def reader() -> None:
        for _ in range(200):
            results.append(lm.state)

    await lm.initialize()
    threads = [__import__("threading").Thread(target=reader) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert all(s is LifecycleState.OPERATIONAL for s in results)


# ---------------------------------------------------------------------------
# 8. initialization / 9. idempotency / rejection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_initialize_transitions_to_operational(lm):
    assert await lm.initialize() is LifecycleState.OPERATIONAL
    assert lm.is_operational
    assert lm.is_initialized


@pytest.mark.asyncio
async def test_initialize_idempotent_rejects_double_init(lm):
    await lm.initialize()
    with pytest.raises(LifecycleManagerError) as exc:
        await lm.initialize()
    assert exc.value.rule_id == "LM-INIT-001"


@pytest.mark.asyncio
async def test_initialize_rejected_when_terminated(lm):
    await lm.initialize()
    await lm.shutdown()
    with pytest.raises(LifecycleManagerError) as exc:
        await lm.initialize()
    assert exc.value.rule_id == "LM-INIT-002"


# ---------------------------------------------------------------------------
# 10. shutdown / 11. idempotency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_shutdown_transitions_to_terminated(lm):
    await lm.initialize()
    assert await lm.shutdown() is LifecycleState.TERMINATED
    assert lm.is_terminated


@pytest.mark.asyncio
async def test_shutdown_idempotent(lm):
    await lm.initialize()
    await lm.shutdown()
    again = await lm.shutdown()
    assert again is LifecycleState.TERMINATED
    assert lm.state is LifecycleState.TERMINATED


@pytest.mark.asyncio
async def test_shutdown_from_uninitialized(lm):
    # No init yet: goes straight to TERMINATED.
    assert await lm.shutdown() is LifecycleState.TERMINATED


# ---------------------------------------------------------------------------
# 12. deterministic phase ordering
# ---------------------------------------------------------------------------


def test_phase_plan_declares_five_phases(lm):
    plan = lm.phase_plan
    assert [p["phase"] for p in plan] == [1, 2, 3, 4, 5]
    names = [p["name"] for p in plan]
    assert names == [
        "Foundation", "State & Storage", "Governance",
        "Execution", "Observability",
    ]


@pytest.mark.asyncio
async def test_initialize_deterministic_order_with_managers(lm):
    # Managers not in the declared topology must be rejected (LM-REG-001).
    with pytest.raises(LifecycleManagerError):
        lm.register_manager(_FakeManager("BetaManager"))
    with pytest.raises(LifecycleManagerError):
        lm.register_manager(_FakeManager("AlphaManager"))
    # Register two declared phase-3 managers; ensure alphabetical ordering.
    lm.register_manager(_FakeManager("ResourceManager"))  # phase 3
    lm.register_manager(_FakeManager("SecurityManager"))  # phase 3
    await lm.initialize()
    # Phase 3 execution order must be alphabetical ascending: ResourceManager (R)
    # before SecurityManager (S). LifecycleManager (self, phase 1) is also present.
    order = lm.initialized_managers
    assert order[0] == "LifecycleManager"  # Phase 1 Foundation first
    res_idx = order.index("ResourceManager")
    sec_idx = order.index("SecurityManager")
    assert res_idx < sec_idx


# ---------------------------------------------------------------------------
# 13. dependency validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dependency_validation_failure_rolls_back(lm):
    bad = _FakeManager("StorageManager", deps=["NonExistentManager"])
    lm.register_manager(bad)
    with pytest.raises(LifecycleManagerError):
        await lm.initialize()
    # Rollback completed -> UNINITIALIZED.
    assert lm.state is LifecycleState.UNINITIALIZED


def test_register_unknown_manager_rejected(lm):
    with pytest.raises(LifecycleManagerError) as exc:
        lm.register_manager(_FakeManager("GhostManager"))
    assert exc.value.rule_id == "LM-REG-001"


# ---------------------------------------------------------------------------
# 14. phase completion / 15. init failure / 16-18. rollback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_initialization_failure_triggers_rollback(lm):
    lm.register_manager(_FakeManager("StateManager", fail_init=True))
    with pytest.raises(LifecycleManagerError):
        await lm.initialize()
    assert lm.state is LifecycleState.UNINITIALIZED


@pytest.mark.asyncio
async def test_rollback_shuts_down_initialized_managers(lm):
    state = _FakeManager("StateManager")
    lm.register_manager(state)
    await lm.initialize()
    assert state.initialized
    await lm.rollback()
    assert state.shutdown_called
    assert lm.state is LifecycleState.UNINITIALIZED


@pytest.mark.asyncio
async def test_rollback_idempotent(lm):
    state = _FakeManager("StateManager")
    lm.register_manager(state)
    await lm.initialize()
    await lm.rollback()
    first = lm.state
    # Second rollback is a no-op (already UNINITIALIZED).
    again = await lm.rollback()
    assert again is first
    assert again is LifecycleState.UNINITIALIZED


@pytest.mark.asyncio
async def test_rollback_failure_distinguished_from_original(lm):
    state = _FakeManager("StateManager", fail_shutdown=True)
    lm.register_manager(state)
    await lm.initialize()
    # original init succeeded; now force a rollback whose shutdown fails.
    with pytest.raises(LifecycleManagerError) as exc:
        await lm.rollback()
    # Original error is None (init was fine); rollback error is recorded.
    assert exc.value.rollback_errors
    assert exc.value.original_error is None
    assert lm.state is LifecycleState.UNINITIALIZED


# ---------------------------------------------------------------------------
# 19. degraded / 20. recovery
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_degraded_transition(lm):
    await lm.initialize()
    await lm.mark_degraded(["HealthManager"])
    assert lm.state is LifecycleState.DEGRADED


@pytest.mark.asyncio
async def test_recovery_flow(lm):
    await lm.initialize()
    await lm.mark_degraded()
    await lm.begin_recovery()
    assert lm.state is LifecycleState.RECOVERY_IN_PROGRESS
    await lm.complete_recovery(success=True)
    assert lm.state is LifecycleState.OPERATIONAL


@pytest.mark.asyncio
async def test_begin_recovery_requires_degraded(lm):
    await lm.initialize()
    with pytest.raises(LifecycleManagerError) as exc:
        await lm.begin_recovery()
    assert exc.value.rule_id == "LM-REC-001"


# ---------------------------------------------------------------------------
# 21. event emission / 22. event ordering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_events_emitted_on_transitions(bus, lm):
    await bus.initialize()
    await lm.initialize()
    await lm.shutdown()
    history = bus.getRecentEvents()
    types = [
        e.eventType.name if hasattr(e.eventType, "name") else str(e.eventType)
        for e in history
    ]
    # Canonical mapped events must be present in order.
    assert EventType.KERNEL_INITIALIZATION_STARTED.name in types
    assert EventType.CORE_MANAGER_INITIALIZED.name in types
    assert EventType.KERNEL_READY.name in types
    assert EventType.KERNEL_SHUTDOWN_STARTED.name in types
    assert EventType.KERNEL_TERMINATED.name in types


@pytest.mark.asyncio
async def test_event_ordering_initialization_before_ready(bus, lm):
    await bus.initialize()
    await lm.initialize()
    history = bus.getRecentEvents()
    names = [
        e.eventType.name if hasattr(e.eventType, "name") else str(e.eventType)
        for e in history
    ]
    init_idx = names.index(EventType.KERNEL_INITIALIZATION_STARTED.name)
    ready_idx = names.index(EventType.KERNEL_READY.name)
    assert init_idx < ready_idx


# ---------------------------------------------------------------------------
# 23. ServiceRegistry registration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_registers_with_service_registry(lm, bus):
    from aios.core.service_registry import (
        ServiceRegistry,
        get_service_registry,
        reset_service_registry_singleton,
    )
    reset_service_registry_singleton()
    sr = ServiceRegistry(event_bus=bus)
    lm._service_registry = sr
    await lm.register_with_service_registry()
    reg = sr.get_registration("core.lifecycle")
    assert reg is not None
    assert reg.service is lm
    reset_service_registry_singleton()


@pytest.mark.asyncio
async def test_registration_skipped_when_no_registry(lm):
    lm._service_registry = None
    # Should not raise.
    await lm.register_with_service_registry()


# ---------------------------------------------------------------------------
# 24. ConfigurationManager integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reads_configuration_for_shutdown_timeout(lm):
    class _CM:
        def get(self, path, default=None):
            if path == "kernel.lifecycle.shutdownTimeoutMs":
                return 1234
            return default

    lm._configuration = _CM()
    # Re-read via fresh construction semantics: emulate by calling the reader.
    val = lm._read_config_int("kernel.lifecycle.shutdownTimeoutMs", 30000)
    assert val == 1234


@pytest.mark.asyncio
async def test_config_unavailable_uses_default(lm):
    lm._configuration = None
    assert lm._read_config_int("kernel.lifecycle.shutdownTimeoutMs", 30000) == 30000


# ---------------------------------------------------------------------------
# 25. StructuredLogger integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_logs_through_structured_logger(lm):
    logged: list[str] = []

    class _SL:
        def debug(self, message, **fields):
            logged.append(("debug", message))

        def info(self, message, **fields):
            logged.append(("info", message))

        def warning(self, message, **fields):
            logged.append(("warning", message))

        def error(self, message, **fields):
            logged.append(("error", message))

    lm._logger = _SL()
    await lm.initialize()
    assert any("OPERATIONAL" in m for _, m in logged)


@pytest.mark.asyncio
async def test_logger_unavailable_does_not_raise(lm):
    lm._logger = None
    # Should initialize without raising even though logger is None.
    await lm.initialize()
    assert lm.is_operational


# ---------------------------------------------------------------------------
# 26. unavailable dependency behavior
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_eventbus_unavailable_defers_events(lm):
    # No bus wired: initialize still succeeds (events no-op/deferred).
    lm._event_bus = None
    assert await lm.initialize() is LifecycleState.OPERATIONAL


def test_build_phase_topology_is_deterministic(lm):
    plan_a = lm.phase_plan
    plan_b = lm.phase_plan
    assert plan_a == plan_b
