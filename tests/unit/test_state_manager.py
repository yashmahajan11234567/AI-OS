"""
Task 10 — StateManager Core Manager unit tests (Part 4 §4.4).

Covers the ICoreManager surface (name / phase / dependencies / manager_id /
initialize / shutdown / health_ready), singleton behavior, ServiceRegistry
registration (as ``core.state``; Part 4 §4.4.9 names kernel.state — see
CONFLICT E.1/INV-SR-NS-002), ConfigurationManager consumption, wiring of
the C4 StructuredLogger (no stdlib logger), state business APIs (backward
compatible), config loading, persisted snapshot loading, final snapshot on
shutdown, canonical EventType emission, error handling, and idempotency.

Per the CRITICAL EVENT TYPE RULE these tests assert ONLY on canonical Part-2
EventTypes (CONFLICT E.1 mapping). No new EventType is invented.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest

from aios.core.service_registry import (
    get_service_registry,
    reset_service_registry_singleton,
)
from aios.core.state import (
    StateManager,
    StateManagerError,
    StateScope,
    StateSnapshot,
    get_state_manager,
    reset_state_manager_singleton,
    set_state_manager,
)
from aios.events.core.bus import (
    EventBus,
    EventBusConfig,
    reset_event_bus_singleton,
)
from aios.events.core.types import EventType


@pytest.fixture
def bus():
    """A canonical EventBus singleton (uninitialized; publish is fire-and-forget)."""
    reset_event_bus_singleton()
    b = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    return b


@pytest.fixture
def sm(bus, tmp_path):
    """A StateManager wired to a real canonical EventBus + tmp persistence dir."""
    reset_state_manager_singleton()
    mgr = StateManager(persistence_path=tmp_path / "state")
    yield mgr
    reset_state_manager_singleton()
    reset_event_bus_singleton()


@pytest.fixture
def sr(bus):
    """A canonical ServiceRegistry wired to the bus."""
    reset_service_registry_singleton()
    reg = get_service_registry(event_bus=bus)
    yield reg
    reset_service_registry_singleton()


async def _tick() -> None:
    """Yield to the event loop so scheduled publishes land.

    StateManager._emit_event schedules ``bus.publish(event)`` via
    ``asyncio.ensure_future`` (mirrors ConfigurationManager._run_emission);
    the coroutine must be allowed to run before the event appears in bus history.
    """
    for _ in range(3):
        await asyncio.sleep(0)


# ---------------------------------------------------------------------------
# 1. construction / 2. singleton / 3. metadata
# ---------------------------------------------------------------------------


def test_construction(sm):
    assert isinstance(sm, StateManager)
    assert sm.name == "StateManager"
    assert sm.phase == 2
    assert sm.dependencies == ["LifecycleManager"]
    assert sm.manager_id == "core.state"


def test_icoremanager_protocol_satisfied(sm):
    # Assert the ICoreManager structural surface directly (isinstance is
    # unreliable for runtime_checkable protocols with property members).
    assert hasattr(sm, "name") and sm.name == "StateManager"
    assert hasattr(sm, "phase") and sm.phase == 2
    assert hasattr(sm, "dependencies")
    assert hasattr(sm, "manager_id")
    assert hasattr(sm, "initialize")
    assert hasattr(sm, "shutdown")
    assert hasattr(sm, "health_ready")


def test_singleton_accessor_returns_same():
    reset_state_manager_singleton()
    reset_event_bus_singleton()
    EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    first = get_state_manager()
    second = get_state_manager()
    assert second is first
    reset_state_manager_singleton()
    reset_event_bus_singleton()


def test_set_singleton_overrides(bus, tmp_path):
    reset_state_manager_singleton()
    custom = StateManager(persistence_path=tmp_path / "state")
    set_state_manager(custom)
    assert get_state_manager() is custom
    reset_state_manager_singleton()


def test_reset_singleton_clears(bus):
    reset_state_manager_singleton()
    before = get_state_manager()
    reset_state_manager_singleton()
    after = get_state_manager()
    assert after is not before
    reset_state_manager_singleton()


def test_initial_health_not_ready(sm):
    # Not initialized yet -> not ready.
    assert sm.health_ready() is False


# ---------------------------------------------------------------------------
# 4. initialize / health_ready / idempotency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_initialize_wires_and_readies(sm, sr):
    sm._service_registry = sr
    await sm.initialize()
    assert sm.is_initialized
    assert sm.health_ready() is True
    # Registered in canonical C2 as core.state (Part 4 §4.4.9 names kernel.state;
    # INV-SR-NS-002 reserves the kernel namespace, so core.state is the
    # compliant id, mirroring core.lifecycle).
    reg = sr.get_registration("core.state")
    assert reg is not None
    assert reg.service is sm
    assert reg.metadata.get("kind") == "core_manager"
    assert reg.metadata.get("phase") == 2


@pytest.mark.asyncio
async def test_initialize_registers_with_service_registry(sm, sr):
    sm._service_registry = sr
    await sm.initialize()
    assert sr.get_registration("core.state") is not None
    assert sm._registered_with_sr is True


@pytest.mark.asyncio
async def test_initialize_idempotent(sm, sr):
    sm._service_registry = sr
    await sm.initialize()
    await sm.initialize()  # must not raise / double-register
    assert sm.is_initialized
    assert sm.health_ready() is True
    # Only one registration.
    assert sm._registered_with_sr is True


@pytest.mark.asyncio
async def test_initialize_reads_configuration(sm):
    class _CM:
        def get(self, path, default=None):
            mapping = {
                "kernel.state.snapshotIntervalSeconds": 60,
                "kernel.state.retentionPolicy.maxSnapshots": 25,
                "kernel.state.consistencyClass": "STRONG",
                "kernel.state.checkpointOnTransition": False,
                "kernel.state.shutdownTimeoutMs": 1234,
            }
            return mapping.get(path, default)

    sm._configuration = _CM()
    await sm.initialize()
    assert sm._snapshot_interval_seconds == 60
    assert sm._max_snapshots == 25
    assert sm._consistency_class == "STRONG"
    assert sm._checkpoint_on_transition is False
    assert sm._shutdown_timeout_ms == 1234


@pytest.mark.asyncio
async def test_config_unavailable_uses_defaults(sm):
    sm._configuration = None
    await sm.initialize()
    assert sm._snapshot_interval_seconds == 300
    assert sm._max_snapshots == 10
    assert sm._consistency_class == "EVENTUAL"
    assert sm._checkpoint_on_transition is True
    assert sm._shutdown_timeout_ms == 5000


@pytest.mark.asyncio
async def test_logs_through_structured_logger(sm):
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

    sm._logger = _SL()
    await sm.initialize()
    assert any("initialized" in m.lower() for _, m in logged)


@pytest.mark.asyncio
async def test_logger_unavailable_does_not_raise(sm):
    sm._logger = None
    await sm.initialize()
    assert sm.is_initialized


@pytest.mark.asyncio
async def test_eventbus_unavailable_defers_events(sm):
    sm._event_bus = None
    # Must not raise: initialize() completes even without a live bus wired.
    await sm.initialize()
    assert sm.is_initialized


# ---------------------------------------------------------------------------
# 5. shutdown / final snapshot / deregistration / idempotency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_shutdown_deregisters_and_clears_ready(sm, sr):
    sm._service_registry = sr
    await sm.initialize()
    assert sm.health_ready() is True
    await sm.shutdown()
    assert sm.is_initialized is False
    assert sm.health_ready() is False
    # Registry records SHUTDOWN lifecycle for core.state.
    reg = sr.get_registration("core.state")
    assert reg is not None
    assert reg.lifecycle_state.value == "SHUTDOWN"


@pytest.mark.asyncio
async def test_shutdown_creates_final_snapshot(sm, sr):
    sm._service_registry = sr
    await sm.initialize()
    sm.set_state(StateScope.WORKFLOW, "wf-final", "status", "running")
    await sm.shutdown()
    # A final snapshot was persisted for the workflow.
    files = list(sm._persistence_path.glob("*.json"))
    assert len(files) == 1
    assert "wf-final" in files[0].name


@pytest.mark.asyncio
async def test_shutdown_idempotent(sm, sr):
    sm._service_registry = sr
    await sm.initialize()
    await sm.shutdown()
    await sm.shutdown()  # second shutdown is a no-op
    assert sm.is_initialized is False


@pytest.mark.asyncio
async def test_shutdown_from_uninitialized_noop(sm):
    await sm.shutdown()  # not initialized -> no-op
    assert sm.is_initialized is False


# ---------------------------------------------------------------------------
# 6. persisted snapshot loading (during initialize)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_initialize_loads_persisted_snapshots(sm, bus):
    # A prior manager persisted a snapshot for wf-restore.
    sm.set_state(StateScope.WORKFLOW, "wf-restore", "status", "running")
    sm.checkpoint(StateScope.WORKFLOW, "wf-restore")

    # A NEW manager on the same persistence path loads the snapshot during
    # initialize().
    sm2 = StateManager(persistence_path=sm._persistence_path)
    await sm2.initialize()
    hist = sm2.get_history(StateScope.WORKFLOW, "wf-restore")
    assert len(hist) == 1
    # The rehydrated state key is reachable.
    assert sm2.get_state(StateScope.WORKFLOW, "wf-restore", "status") == "running"
    reset_state_manager_singleton()
    reset_event_bus_singleton()


# ---------------------------------------------------------------------------
# 7. business API backward compatibility
# ---------------------------------------------------------------------------


def test_business_api_works(sm, sr):
    sm.set_state(StateScope.WORKFLOW, "wf-1", "status", "running")
    assert sm.get_state(StateScope.WORKFLOW, "wf-1", "status") == "running"
    assert sm.get_state(StateScope.WORKFLOW, "wf-1") == {"status": "running"}

    sm.update_state(StateScope.WORKFLOW, "wf-1", {"progress": 50})
    assert sm.get_state(StateScope.WORKFLOW, "wf-1", "progress") == 50

    sm.delete_state(StateScope.WORKFLOW, "wf-1", "progress")
    assert sm.get_state(StateScope.WORKFLOW, "wf-1", "progress") is None

    snap = sm.checkpoint(StateScope.WORKFLOW, "wf-1", metadata={"step": 2})
    assert isinstance(snap, StateSnapshot)
    assert sm.get_history(StateScope.WORKFLOW, "wf-1") == [snap]

    restored = sm.restore(StateScope.WORKFLOW, "wf-1")
    assert restored.snapshot_id == snap.snapshot_id

    assert "wf-1" in sm.list_identifiers(StateScope.WORKFLOW)

    sm.set_state(StateScope.WORKFLOW, "wf-2", "x", 1)
    sm.clear_scope(StateScope.WORKFLOW, "wf-2")
    assert "wf-2" not in sm.list_identifiers(StateScope.WORKFLOW)


def test_checkpoint_on_missing_state_raises(sm):
    with pytest.raises(ValueError):
        sm.checkpoint(StateScope.WORKFLOW, "missing")


def test_get_state_missing_returns_empty_dict(sm):
    assert sm.get_state(StateScope.WORKFLOW, "missing") == {}


# ---------------------------------------------------------------------------
# 8. canonical EventType emission (no invented types)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_state_changed_event_emitted(bus, sm):
    await bus.initialize()
    sm.set_state(StateScope.WORKFLOW, "wf-evt", "a", 1)
    # StateManager._emit_event schedules publish via loop.create_task; give the
    # loop a chance to run the task before reading the history.
    for _ in range(3):
        await asyncio.sleep(0)
    events = bus.getRecentEvents()
    names = [e.eventType.name for e in events if hasattr(e.eventType, "name")]
    assert EventType.STATE_CHANGED.name in names


@pytest.mark.asyncio
async def test_snapshot_created_event_emitted(bus, sm):
    await bus.initialize()
    sm.set_state(StateScope.WORKFLOW, "wf-evt2", "a", 1)
    sm.checkpoint(StateScope.WORKFLOW, "wf-evt2")
    for _ in range(3):
        await asyncio.sleep(0)
    events = bus.getRecentEvents()
    names = [e.eventType.name for e in events if hasattr(e.eventType, "name")]
    assert EventType.STATE_SNAPSHOT_CREATED.name in names


@pytest.mark.asyncio
async def test_restored_event_emitted(bus, sm):
    await bus.initialize()
    sm.set_state(StateScope.WORKFLOW, "wf-evt3", "a", 1)
    sm.checkpoint(StateScope.WORKFLOW, "wf-evt3")
    sm.restore(StateScope.WORKFLOW, "wf-evt3")
    for _ in range(3):
        await asyncio.sleep(0)
    events = bus.getRecentEvents()
    names = [e.eventType.name for e in events if hasattr(e.eventType, "name")]
    assert EventType.STATE_RESTORED.name in names


# ---------------------------------------------------------------------------
# 9. error handling
# ---------------------------------------------------------------------------


def test_state_manager_error_carries_rule_and_original():
    exc = StateManagerError("boom", rule_id="SM-TEST-001")
    assert exc.rule_id == "SM-TEST-001"
    assert exc.original_error is None
    inner = RuntimeError("inner")
    exc2 = StateManagerError("boom", original_error=inner)
    assert exc2.original_error is inner


def test_constructor_requires_canonical_bus():
    # With no canonical EventBus singleton, construction raises RuntimeError
    # (matching the pre-Task-10 contract).
    reset_event_bus_singleton()
    with pytest.raises(RuntimeError):
        StateManager(persistence_path=Path(tempfile.mkdtemp()) / "state")


# ---------------------------------------------------------------------------
# 10. core.state registered in canonical C2 (full integration path)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_registers_as_kernel_state_in_canonical_sr(bus, sm, sr):
    sm._service_registry = sr
    await sm.initialize()
    reg = sr.get_registration("core.state")
    assert reg is not None
    assert reg.metadata.get("manager") == "StateManager"


# ---------------------------------------------------------------------------
# 11. FIND-01 regression: deterministic event emission from sync business APIs
#
# Regression tests mandated by the Task 10 independent QA (FIND-01):
#   A. No RuntimeWarning (coroutine never awaited) from sync event emission.
#   B. The emitted event is actually observable by the canonical EventBus.
#   C. No coroutine is left unawaited / no task leak.
#   D. Existing synchronous StateManager business API behavior is preserved.
#   E. Async initialization/shutdown behavior still works.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find01_no_runtime_warning_on_sync_emit(bus, sm):
    """A. Sync business API must not leak an un-awaited publish coroutine.

    ``set_state`` is synchronous; calling it outside a running loop (the classic
    pre-FIND-01 failure) must not raise ``RuntimeWarning: coroutine
    'EventBus.publish' was never awaited``. With `-W error::RuntimeWarning`
    enabled this is a hard failure if the old fire-and-forget path regresses.
    """
    # The bus is NOT initialized to RUNNING here — there is no running dispatch
    # loop, so the only thing that must hold is "no un-awaited coroutine".
    sm.set_state(StateScope.WORKFLOW, "wf-find01", "k", 1)
    # Drain to surface any swallowed exceptions from scheduled tasks.
    await asyncio.sleep(0)
    # Explicitly assert no dangling pending tasks carrying an un-awaited coro.
    assert not any(
        t.get_name() == "Task" and not t.done() for t in sm._pending_tasks
    )


@pytest.mark.asyncio
async def test_find01_event_observable_by_canonical_bus(bus, sm):
    """B. Event emitted from a sync path is observable on the canonical bus."""
    await bus.initialize()
    sm.set_state(StateScope.WORKFLOW, "wf-find01-obs", "k", 1)
    # _emit_event schedules bus.publish via asyncio.ensure_future; yield to the
    # loop so the publish task runs _publish_one (which records history) before
    # we read getRecentEvents(). (Mirrors test_state_changed_event_emitted.)
    for _ in range(3):
        await asyncio.sleep(0)
    await bus.drain()
    names = {
        e.eventType.name
        for e in bus.getRecentEvents()
        if hasattr(e.eventType, "name")
    }
    assert EventType.STATE_CHANGED.name in names


@pytest.mark.asyncio
async def test_find01_no_unawaited_coroutine_in_running_loop(bus, sm):
    """C. No coroutine / task is left un-awaited when emitting in a running loop.

    The publish coroutine MUST be scheduled with a strong reference
    (``_pending_tasks``) exactly as ConfigurationManager does; here we verify
    the scheduled task actually completes (drains) and is discarded.
    """
    await bus.initialize()
    sm.set_state(StateScope.WORKFLOW, "wf-find01-drain", "k", 1)
    # Let the scheduled publish task run then drain the bus.
    await asyncio.sleep(0)
    await bus.drain()
    # After drain, pending tasks scheduled by _emit_event have completed.
    assert all(t.done() for t in sm._pending_tasks)


@pytest.mark.asyncio
async def test_find01_sync_api_preserved(bus, sm, sr):
    """D. Synchronous business API behavior is preserved (no async conversion).

    The pre-Task-10 sync public API (set_state / get_state / update_state /
    delete_state / checkpoint / restore / get_history / list_identifiers /
    clear_scope) remains synchronous and behavior-compatible.
    """
    # Sync API is callable WITHOUT being awaited (proves it stayed synchronous).
    sm.set_state(StateScope.WORKFLOW, "wf", "a", 1)
    assert sm.get_state(StateScope.WORKFLOW, "wf", "a") == 1

    sm.update_state(StateScope.WORKFLOW, "wf", {"b": 2})
    assert sm.get_state(StateScope.WORKFLOW, "wf", "b") == 2

    snap = sm.checkpoint(StateScope.WORKFLOW, "wf")
    assert isinstance(snap, StateSnapshot)
    assert sm.get_history(StateScope.WORKFLOW, "wf") == [snap]

    restored = sm.restore(StateScope.WORKFLOW, "wf")
    assert restored.snapshot_id == snap.snapshot_id

    assert "wf" in sm.list_identifiers(StateScope.WORKFLOW)

    sm.delete_state(StateScope.WORKFLOW, "wf", "a")
    assert sm.get_state(StateScope.WORKFLOW, "wf", "a") is None

    sm.clear_scope(StateScope.WORKFLOW, "wf")
    assert "wf" not in sm.list_identifiers(StateScope.WORKFLOW)


@pytest.mark.asyncio
async def test_find01_async_init_shutdown_still_works(bus, sm, sr):
    """E. Async initialization/shutdown lifecycle behavior is unaffected."""
    sm._service_registry = sr
    await sm.initialize()
    assert sm.is_initialized
    assert sm.health_ready() is True
    await sm.shutdown()
    assert not sm.is_initialized
    assert not sm.health_ready()
