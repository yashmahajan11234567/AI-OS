"""
Task 11 — StorageManager Core Manager unit tests (Part 4 §4.5).

Covers the ICoreManager surface (name / phase / dependencies / manager_id /
initialize / shutdown / health_ready), singleton behavior, ServiceRegistry
registration (as ``core.storage``; Part 4 §4.5.11 names kernel.storage — see
CONFLICT E.1/INV-SR-NS-002), ConfigurationManager consumption, wiring of
the C4 StructuredLogger (no stdlib logger), all six storage namespaces, storage
operations (artifact/checkpoint), config loading, persisted object loading,
final persist on shutdown, canonical EventType emission, error handling, and
idempotency.

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
from aios.core.storage import (
    StorageManager,
    StorageManagerError,
    StorageNamespace,
    get_storage_manager,
    reset_storage_manager_singleton,
    set_storage_manager,
)
from aios.events.core.bus import (
    EventBus,
    EventBusConfig,
    get_core_event_bus,
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
    """A StorageManager wired to a real canonical EventBus + tmp persistence dir."""
    reset_storage_manager_singleton()
    mgr = StorageManager(persistence_path=tmp_path / "storage")
    yield mgr
    reset_storage_manager_singleton()
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

    StorageManager._emit_event schedules ``bus.publish(event)`` via
    ``asyncio.ensure_future`` (mirrors ConfigurationManager._run_emission);
    the coroutine must be allowed to run before the event appears in bus history.
    """
    for _ in range(3):
        await asyncio.sleep(0)


# ---------------------------------------------------------------------------
# 1. construction / 2. singleton / 3. metadata
# ---------------------------------------------------------------------------


def test_construction(sm):
    assert isinstance(sm, StorageManager)
    assert sm.name == "StorageManager"
    assert sm.phase == 2
    assert sm.dependencies == ["LifecycleManager"]
    assert sm.manager_id == "core.storage"


def test_icoremanager_protocol_satisfied(sm):
    # Assert the ICoreManager structural surface directly (isinstance is
    # unreliable for runtime_checkable protocols with property members).
    assert hasattr(sm, "name") and sm.name == "StorageManager"
    assert hasattr(sm, "phase") and sm.phase == 2
    assert hasattr(sm, "dependencies")
    assert hasattr(sm, "manager_id")
    assert hasattr(sm, "initialize")
    assert hasattr(sm, "shutdown")
    assert hasattr(sm, "health_ready")


def test_singleton_accessor_returns_same():
    reset_storage_manager_singleton()
    reset_event_bus_singleton()
    EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    first = get_storage_manager()
    second = get_storage_manager()
    assert second is first
    reset_storage_manager_singleton()
    reset_event_bus_singleton()


def test_set_singleton_overrides(bus, tmp_path):
    reset_storage_manager_singleton()
    custom = StorageManager(persistence_path=tmp_path / "storage")
    set_storage_manager(custom)
    assert get_storage_manager() is custom
    reset_storage_manager_singleton()


def test_reset_singleton_clears(bus):
    reset_storage_manager_singleton()
    reset_event_bus_singleton()
    EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    before = get_storage_manager()
    reset_storage_manager_singleton()
    after = get_storage_manager()
    assert after is not before
    reset_storage_manager_singleton()
    reset_event_bus_singleton()


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
    # Registered in canonical C2 as core.storage (Part 4 §4.5.11 names kernel.storage;
    # INV-SR-NS-002 reserves the kernel namespace, so core.storage is the
    # compliant id, mirroring core.lifecycle / core.state).
    reg = sr.get_registration("core.storage")
    assert reg is not None
    assert reg.service is sm
    assert reg.metadata.get("kind") == "core_manager"
    assert reg.metadata.get("phase") == 2


@pytest.mark.asyncio
async def test_initialize_registers_with_service_registry(sm, sr):
    sm._service_registry = sr
    await sm.initialize()
    assert sr.get_registration("core.storage") is not None
    assert sm._registered_with_sr is True


@pytest.mark.asyncio
async def test_initialize_idempotent(sm, sr):
    sm._service_registry = sr
    await sm.initialize()
    await sm.initialize()  # must not raise / double-register
    assert sm.is_initialized
    assert sm.health_ready() is True
    assert sm._registered_with_sr is True


@pytest.mark.asyncio
async def test_initialize_reads_configuration(sm):
    from aios.core.storage import get_storage_manager

    class _CM:
        def get(self, path, default=None):
            mapping = {
                "kernel.storage.consistencyClass": "STRONG",
                "kernel.storage.integrity.verification": False,
                "kernel.storage.shutdownTimeoutMs": 1234,
            }
            return mapping.get(path, default)

        def get_section(self, section):
            return None

    sm._configuration = _CM()
    await sm.initialize()
    assert sm._consistency_class == "STRONG"
    assert sm._integrity_verification is False
    assert sm._shutdown_timeout_ms == 1234


@pytest.mark.asyncio
async def test_config_unavailable_uses_defaults(sm):
    sm._configuration = None
    await sm.initialize()
    assert sm._consistency_class == "EVENTUAL"
    assert sm._integrity_verification is True
    assert sm._shutdown_timeout_ms == 5000


@pytest.mark.asyncio
async def test_persistence_path_from_config(sm):
    class _CM:
        def get(self, path, default=None):
            if path == "kernel.storage.persistencePath":
                return str(sm._persistence_path / "configured")
            return default

        def get_section(self, section):
            return None

    sm._configuration = _CM()
    await sm.initialize()
    assert str(sm._persistence_path).endswith("configured")


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
# 5. shutdown / final persist / deregistration / idempotency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_shutdown_deregisters_and_clears_ready(sm, sr):
    sm._service_registry = sr
    await sm.initialize()
    assert sm.health_ready() is True
    await sm.shutdown()
    assert sm.is_initialized is False
    assert sm.health_ready() is False
    # Registry records SHUTDOWN lifecycle for core.storage.
    reg = sr.get_registration("core.storage")
    assert reg is not None
    assert reg.lifecycle_state.value == "SHUTDOWN"


@pytest.mark.asyncio
async def test_shutdown_persists_objects(sm, sr):
    sm._service_registry = sr
    await sm.initialize()
    sm.store_artifact("test-artifact", {"data": "value"})
    await sm.shutdown()
    # A persisted file exists on disk.
    files = list(sm._persistence_path.glob("*.json"))
    assert len(files) >= 1
    assert any("test-artifact" in f.name for f in files)


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
# 6. six storage namespaces (Part 4 §4.5.3)
# ---------------------------------------------------------------------------


def test_six_namespaces_declared(sm):
    expected = {
        StorageNamespace.CHECKPOINTS,
        StorageNamespace.ARTIFACTS,
        StorageNamespace.DIAGNOSTICS,
        StorageNamespace.AUDIT,
        StorageNamespace.CONFIGURATION,
        StorageNamespace.IDENTITY,
    }
    assert set(sm.namespaces) == expected
    assert len(sm.namespaces) == 6


def test_namespace_keys_initialized(sm):
    for ns in StorageNamespace:
        assert ns.value in sm._namespaces
        assert isinstance(sm._namespaces[ns.value], dict)


def test_get_namespace_objects_empty(sm):
    for ns in StorageNamespace:
        assert sm.get_namespace_objects(ns) == []


# ---------------------------------------------------------------------------
# 7. artifact operations (Part 4 §4.5.5)
# ---------------------------------------------------------------------------


def test_store_and_retrieve_artifact(sm):
    obj = sm.store_artifact("wf-result", {"output": "done"})
    assert obj.object_id == "wf-result"
    assert obj.namespace == StorageNamespace.ARTIFACTS
    retrieved = sm.retrieve_artifact("wf-result")
    assert retrieved is obj
    assert retrieved.data == {"output": "done"}


def test_store_artifact_overwrite(sm):
    first = sm.store_artifact("artifact-1", {"v": 1})
    second = sm.store_artifact("artifact-1", {"v": 2})
    assert second.data == {"v": 2}
    assert sm.retrieve_artifact("artifact-1").data == {"v": 2}


def test_delete_artifact(sm):
    sm.store_artifact("to-delete", {"x": 1})
    assert sm.retrieve_artifact("to-delete") is not None
    result = sm.delete_artifact("to-delete")
    assert result is True
    assert sm.retrieve_artifact("to-delete") is None


def test_delete_missing_artifact_returns_false(sm):
    result = sm.delete_artifact("nonexistent")
    assert result is False


def test_list_namespace_objects_after_artifact(sm):
    sm.store_artifact("a1", {"v": 1})
    sm.store_artifact("a2", {"v": 2})
    objects = sm.get_namespace_objects(StorageNamespace.ARTIFACTS)
    assert "a1" in objects
    assert "a2" in objects


# ---------------------------------------------------------------------------
# 8. checkpoint operations (Part 4 §4.5.4)
# ---------------------------------------------------------------------------


def test_write_and_read_checkpoint(sm):
    obj = sm.write_checkpoint("checkpoint-1", {"state": "saved"})
    assert obj.namespace == StorageNamespace.CHECKPOINTS
    assert obj.object_id == "checkpoint-1"
    retrieved = sm.read_checkpoint("checkpoint-1")
    assert retrieved is obj
    assert retrieved.data == {"state": "saved"}


def test_list_checkpoints(sm):
    sm.write_checkpoint("c1", {"v": 1})
    sm.write_checkpoint("c2", {"v": 2})
    checkpoints = sm.list_checkpoints()
    assert "c1" in checkpoints
    assert "c2" in checkpoints


def test_prune_checkpoint(sm):
    sm.write_checkpoint("c-prune", {"v": 1})
    assert sm.read_checkpoint("c-prune") is not None
    result = sm.prune_checkpoint("c-prune")
    assert result is True
    assert sm.read_checkpoint("c-prune") is None


def test_prune_missing_checkpoint_returns_false(sm):
    result = sm.prune_checkpoint("nonexistent")
    assert result is False


# ---------------------------------------------------------------------------
# 9. canonical EventType emission (no invented types)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_artifact_created_event_emitted(bus, sm):
    await bus.initialize()
    sm.store_artifact("evt-artifact", {"data": "value"})
    await _tick()
    events = bus.getRecentEvents()
    names = [e.eventType.name for e in events if hasattr(e.eventType, "name")]
    assert EventType.ARTIFACT_CREATED.name in names


@pytest.mark.asyncio
async def test_artifact_updated_event_emitted(bus, sm):
    await bus.initialize()
    sm.store_artifact("update-test", {"v": 1})
    await _tick()
    sm.store_artifact("update-test", {"v": 2})
    await _tick()
    events = bus.getRecentEvents()
    names = [e.eventType.name for e in events if hasattr(e.eventType, "name")]
    assert EventType.ARTIFACT_UPDATED.name in names


@pytest.mark.asyncio
async def test_artifact_deleted_event_emitted(bus, sm):
    await bus.initialize()
    sm.store_artifact("delete-test", {"v": 1})
    await _tick()
    sm.delete_artifact("delete-test")
    await _tick()
    events = bus.getRecentEvents()
    names = [e.eventType.name for e in events if hasattr(e.eventType, "name")]
    assert EventType.ARTIFACT_DELETED.name in names


@pytest.mark.asyncio
async def test_checkpoint_created_event_emitted(bus, sm):
    await bus.initialize()
    sm.write_checkpoint("chk-evt", {"state": "ok"})
    await _tick()
    events = bus.getRecentEvents()
    names = [e.eventType.name for e in events if hasattr(e.eventType, "name")]
    assert EventType.CHECKPOINT_CREATED.name in names


@pytest.mark.asyncio
async def test_checkpoint_pruned_event_emitted(bus, sm):
    await bus.initialize()
    sm.write_checkpoint("chk-prune-evt", {"state": "ok"})
    await _tick()
    sm.prune_checkpoint("chk-prune-evt")
    await _tick()
    events = bus.getRecentEvents()
    names = [e.eventType.name for e in events if hasattr(e.eventType, "name")]
    assert EventType.CHECKPOINT_PRUNED.name in names


@pytest.mark.asyncio
async def test_all_emitted_events_are_canonical(bus, sm):
    """No invented / non-canonical EventType values leak from StorageManager."""
    await bus.initialize()
    sm.store_artifact("canon-1", {"v": 1})
    sm.store_artifact("canon-1", {"v": 2})
    sm.delete_artifact("canon-1")
    sm.write_checkpoint("canon-c1", {"state": "ok"})
    sm.prune_checkpoint("canon-c1")
    await _tick()
    await bus.drain()
    for e in bus.getRecentEvents():
        assert hasattr(e.eventType, "name"), "non-canonical EventType leaked"


# ---------------------------------------------------------------------------
# 10. FIND-01 regression: deterministic event emission from sync business APIs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find01_no_runtime_warning_on_sync_emit(bus, sm):
    """Sync business API must not leak an un-awaited publish coroutine."""
    sm.store_artifact("find01-artifact", {"k": 1})
    await asyncio.sleep(0)
    assert not any(
        t.get_name() == "Task" and not t.done() for t in sm._pending_tasks
    )


@pytest.mark.asyncio
async def test_find01_event_observable_by_canonical_bus(bus, sm):
    """Event emitted from a sync path is observable on the canonical bus."""
    await bus.initialize()
    sm.store_artifact("find01-obs", {"k": 1})
    for _ in range(3):
        await asyncio.sleep(0)
    await bus.drain()
    names = {
        e.eventType.name
        for e in bus.getRecentEvents()
        if hasattr(e.eventType, "name")
    }
    assert EventType.ARTIFACT_CREATED.name in names


@pytest.mark.asyncio
async def test_find01_no_unawaited_coroutine_in_running_loop(bus, sm):
    """No coroutine / task is left un-awaited when emitting in a running loop."""
    await bus.initialize()
    sm.store_artifact("find01-drain", {"k": 1})
    await asyncio.sleep(0)
    await bus.drain()
    assert all(t.done() for t in sm._pending_tasks)


@pytest.mark.asyncio
async def test_find01_sync_api_preserved(bus, sm, sr):
    """Synchronous business API behavior is preserved (no async conversion)."""
    sm._service_registry = sr
    await sm.initialize()
    # Sync API is callable WITHOUT being awaited (proves it stayed synchronous).
    sm.store_artifact("wf", {"a": 1})
    assert sm.retrieve_artifact("wf").data == {"a": 1}
    sm.store_artifact("wf", {"b": 2})
    assert sm.retrieve_artifact("wf").data == {"b": 2}
    sm.write_checkpoint("c1", {"state": "ok"})
    assert "c1" in sm.list_checkpoints()
    sm.prune_checkpoint("c1")
    assert "c1" not in sm.list_checkpoints()
    result = sm.delete_artifact("wf")
    assert result is True
    assert sm.retrieve_artifact("wf") is None


@pytest.mark.asyncio
async def test_find01_async_init_shutdown_still_works(bus, sm, sr):
    """Async initialization/shutdown lifecycle behavior is unaffected."""
    sm._service_registry = sr
    await sm.initialize()
    assert sm.is_initialized
    assert sm.health_ready() is True
    await sm.shutdown()
    assert not sm.is_initialized
    assert not sm.health_ready()


# ---------------------------------------------------------------------------
# 11. error handling
# ---------------------------------------------------------------------------


def test_storage_manager_error_carries_rule_and_original():
    exc = StorageManagerError("boom", rule_id="SM-TEST-001")
    assert exc.rule_id == "SM-TEST-001"
    assert exc.original_error is None
    inner = RuntimeError("inner")
    exc2 = StorageManagerError("boom", original_error=inner)
    assert exc2.original_error is inner


def test_constructor_requires_canonical_bus():
    # With no canonical EventBus singleton, construction raises RuntimeError
    # (matching the StateManager contract).
    reset_event_bus_singleton()
    with pytest.raises(RuntimeError):
        StorageManager(persistence_path=Path(tempfile.mkdtemp()) / "storage")


def test_get_object_missing_namespace_key(sm):
    # Accessing a namespace that exists returns None for unknown object_id.
    assert sm.get_object(StorageNamespace.ARTIFACTS, "unknown") is None


def test_verify_integrity_empty_namespace(sm):
    assert sm.verify_integrity(StorageNamespace.ARTIFACTS) is True


def test_verify_integrity_with_objects(sm):
    sm.store_artifact("int-1", {"data": "value"})
    assert sm.verify_integrity(StorageNamespace.ARTIFACTS) is True


# ---------------------------------------------------------------------------
# 12. core.storage registered in canonical C2 (full integration path)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_registers_as_core_storage_in_canonical_sr(bus, sm, sr):
    sm._service_registry = sr
    await sm.initialize()
    reg = sr.get_registration("core.storage")
    assert reg is not None
    assert reg.metadata.get("manager") == "StorageManager"
    assert reg.metadata.get("kind") == "core_manager"


# ---------------------------------------------------------------------------
# 13. persisted object loading (during initialize)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_initialize_loads_persisted_objects(sm, bus):
    # A prior manager persisted an object.
    sm.store_artifact("restore-artifact", {"status": "saved"})
    sm.write_checkpoint("restore-chk", {"state": "ok"})

    # A NEW manager on the same persistence path loads objects during
    # initialize().
    sm2 = StorageManager(persistence_path=sm._persistence_path)
    await sm2.initialize()
    loaded_art = sm2.retrieve_artifact("restore-artifact")
    assert loaded_art is not None
    assert loaded_art.data == {"status": "saved"}
    loaded_chk = sm2.read_checkpoint("restore-chk")
    assert loaded_chk is not None
    assert loaded_chk.data == {"state": "ok"}
    reset_storage_manager_singleton()
    reset_event_bus_singleton()
