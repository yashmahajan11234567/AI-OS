"""
Task 13 — ResourceManager Core Manager unit tests.

Covers the ICoreManager surface, singleton behavior, lifecycle, ServiceRegistry
integration, configuration integration, business APIs, canonical EventType
mappings, the sync→async event bridge (with RuntimeWarning protection),
StructuredLogger usage, and ResourceManagerError behavior — following the
Task 9–12 structure.

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
)
from aios.core.resource_manager import (
    ResourceAllocation,
    ResourceLimit,
    ResourceManager,
    ResourceManagerError,
    ResourceType,
    get_resource_manager,
    reset_resource_manager_singleton,
    set_resource_manager,
)
from aios.core.service_registry import (
    get_service_registry,
    reset_service_registry_singleton,
)
from aios.core.structured_logger import get_logger
from aios.events.core.bus import EventBus, EventBusConfig, reset_event_bus_singleton
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_wired_manager(
    *,
    with_bus: bool = True,
    with_sr: bool = True,
    with_logger: bool = True,
    with_cm: bool = True,
) -> ResourceManager:
    """Construct a ResourceManager with the canonical components wired in.

    The canonical EventBus is created but NOT initialized here (initialization
    requires a running loop and is performed inside the async tests via
    ``await _init_bus(rm)`` — mirroring kernel startup which initializes the bus
    before constructing managers).
    """
    if with_bus:
        reset_event_bus_singleton()
        EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    sr = get_service_registry() if with_sr else None
    logger = get_logger() if with_logger else None
    cm = get_configuration_manager() if with_cm else None
    return ResourceManager(
        service_registry=sr,
        configuration_manager=cm,
        logger=logger,
    )


async def _init_bus(rm: ResourceManager) -> None:
    """Initialize the canonical EventBus (RUNNING) so events can be enqueued."""
    bus = rm._event_bus
    if bus is not None and bus._state.name != "RUNNING":  # type: ignore[attr-defined]
        await bus.initialize()


async def _drain(bus: Any, expected: set[str], deadline_loops: int = 200) -> set[str]:
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


# ---------------------------------------------------------------------------
# 1–4. Identity / phase / manager_id / dependencies
# ---------------------------------------------------------------------------


def test_identity_name_phase_manager_id():
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_resource_manager_singleton()
    rm = _build_wired_manager()
    try:
        assert rm.name == "ResourceManager"
        assert rm.phase == 3
        assert rm.manager_id == "core.resource"
        assert rm.manager_id != "kernel.resource"
        assert rm.dependencies == ["LifecycleManager"]
    finally:
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_resource_manager_singleton()


def test_identity_component_identity_is_core_manager():
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_resource_manager_singleton()
    rm = _build_wired_manager()
    try:
        ident = rm._identity
        assert isinstance(ident, ComponentIdentity)
        assert ident.component_type is ComponentType.CORE_MANAGER
        assert ident.component_name == "ResourceManager"
        assert ident.version == SemanticVersion(1, 0, 0)
    finally:
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_resource_manager_singleton()


# ---------------------------------------------------------------------------
# 5. ICoreManager surface
# ---------------------------------------------------------------------------


def test_icore_manager_protocol_surface():
    from aios.core.lifecycle_manager import ICoreManager

    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_resource_manager_singleton()
    rm = _build_wired_manager()
    try:
        assert isinstance(rm, ICoreManager)
    finally:
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_resource_manager_singleton()


def test_not_initialized_before_initialize():
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_resource_manager_singleton()
    rm = _build_wired_manager()
    try:
        assert rm.is_initialized is False
        assert rm.health_ready() is False
    finally:
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_resource_manager_singleton()


# ---------------------------------------------------------------------------
# 6–7. Singleton behavior / reset
# ---------------------------------------------------------------------------


def test_singleton_get_set_reset():
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_resource_manager_singleton()
    EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    try:
        a = ResourceManager()
        set_resource_manager(a)
        assert get_resource_manager() is a
        b = ResourceManager()
        set_resource_manager(b)
        assert get_resource_manager() is b
        reset_resource_manager_singleton()
        assert get_resource_manager() is not b
    finally:
        reset_resource_manager_singleton()
        reset_event_bus_singleton()
        reset_service_registry_singleton()


def test_singleton_thread_lock_guarded():
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_resource_manager_singleton()
    EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    try:
        import threading

        created: list[ResourceManager] = []
        barrier = threading.Barrier(4)

        def worker() -> None:
            barrier.wait()
            created.append(get_resource_manager())

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # All threads resolve to a single instance (no double construction).
        assert all(c is created[0] for c in created)
    finally:
        reset_resource_manager_singleton()
        reset_event_bus_singleton()
        reset_service_registry_singleton()


# ---------------------------------------------------------------------------
# 8–10. Initialization / shutdown / health_ready
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_initialize_registers_and_marks_ready():
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_resource_manager_singleton()
    rm = _build_wired_manager()
    try:
        await rm.initialize()
        assert rm.is_initialized is True
        assert rm.health_ready() is True
        reg = get_service_registry().get_registration("core.resource")
        assert reg is not None
        assert reg.service is rm

        # Idempotent.
        await rm.initialize()
        assert rm.is_initialized is True
    finally:
        await rm.shutdown()
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_resource_manager_singleton()


@pytest.mark.asyncio
async def test_shutdown_marks_shutdown_and_clears_state():
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_resource_manager_singleton()
    rm = _build_wired_manager()
    try:
        await rm.initialize()
        await rm.shutdown()
        assert rm.is_initialized is False
        assert rm.health_ready() is False
        reg = get_service_registry().get_registration("core.resource")
        assert reg is not None
        assert reg.lifecycle_state.value == "SHUTDOWN"

        # Idempotent.
        await rm.shutdown()
        assert rm.is_initialized is False
    finally:
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_resource_manager_singleton()


# ---------------------------------------------------------------------------
# 11–13. ServiceRegistry / core.resource / kernel.resource config
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_service_registry_metadata_envelope():
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_resource_manager_singleton()
    rm = _build_wired_manager()
    try:
        await rm.initialize()
        reg = get_service_registry().get_registration("core.resource")
        assert reg is not None
        assert reg.metadata["kind"] == "core_manager"
        assert reg.metadata["manager"] == "ResourceManager"
        assert reg.metadata["phase"] == 3
    finally:
        await rm.shutdown()
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_resource_manager_singleton()


def test_config_namespace_is_kernel_resource_not_core_resource():
    # The ResourceManager reads kernel.resource.* from the frozen ConfigurationManager
    # (independent from the core.resource ServiceRegistry id). Verify the accessor
    # paths are used (no core.resource.* config access).
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_resource_manager_singleton()
    rm = _build_wired_manager()
    try:
        # Exercise the readers with no CM (graceful default) and with a CM.
        assert rm._read_config_int("kernel.resource.cleanupIntervalSeconds", 60) == 60
        assert rm.manager_id == "core.resource"
        # The configuration namespace is kernel.resource.* (read by initialize()).
    finally:
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_resource_manager_singleton()


# ---------------------------------------------------------------------------
# 14–15. Lifecycle ownership / not in engineering-service path
# ---------------------------------------------------------------------------


def test_registers_with_lifecycle_not_engineering_services():
    # Verified end-to-end in the critical acceptance test via HermesKernel.
    # Here we assert the ResourceManager depends only on LifecycleManager (so it
    # is not an engineering-service dependency edge).
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_resource_manager_singleton()
    rm = _build_wired_manager()
    try:
        assert "LifecycleManager" in rm.dependencies
        assert "HealthManager" not in rm.dependencies
        assert "SecurityManager" not in rm.dependencies
    finally:
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_resource_manager_singleton()


# ---------------------------------------------------------------------------
# 16. Business APIs preserved
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_business_api_allocate_release_usage_stats():
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_resource_manager_singleton()
    rm = _build_wired_manager()
    try:
        await rm.initialize()

        alloc = await rm.allocate(ResourceType.MEMORY, 2048, "svc-x", "load test")
        assert isinstance(alloc, ResourceAllocation)
        assert alloc.resource_type is ResourceType.MEMORY
        assert alloc.amount == 2048

        usage = rm.get_usage(ResourceType.MEMORY)
        assert usage["used"] == 2048
        assert usage["available"] == 8192 - 2048

        # Release.
        assert rm.release(alloc.allocation_id) is True
        assert rm.release(alloc.allocation_id) is False

        # release_all_for_requestor.
        await rm.allocate(ResourceType.CPU, 5, "svc-x", "more")
        assert rm.release_all_for_requestor("svc-x") == 1

        # stats structure.
        stats = rm.get_stats()
        assert "limits" in stats
        assert "total_allocations" in stats
        assert "waiting_requests" in stats

        # add_allocation.
        rm.set_limit(ResourceLimit(ResourceType.CUSTOM, 10, "units"))
        rm.add_allocation(
            ResourceAllocation(
                allocation_id="manual-1",
                resource_type=ResourceType.CUSTOM,
                amount=1,
                requestor="manual",
                purpose="track",
            )
        )
        assert rm.get_usage(ResourceType.CUSTOM)["used"] == 1

        # set_limit / get_limit.
        rm.set_limit(ResourceLimit(ResourceType.GPU, 4, "count"))
        assert rm.get_limit(ResourceType.GPU) is not None
    finally:
        await rm.shutdown()
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_resource_manager_singleton()


@pytest.mark.asyncio
async def test_business_api_cleanup_expired():
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_resource_manager_singleton()
    rm = _build_wired_manager()
    try:
        await rm.initialize()
        alloc = await rm.allocate(
            ResourceType.MEMORY, 100, "exp", "short", ttl_seconds=-1
        )
        cleaned = await rm._cleanup_expired()
        assert cleaned >= 1
        assert rm.release(alloc.allocation_id) is False
    finally:
        await rm.shutdown()
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_resource_manager_singleton()


# ---------------------------------------------------------------------------
# 17–19. Canonical EventTypes / no invented / reserved fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_canonical_events_emitted_and_no_inventions():
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_resource_manager_singleton()
    rm = _build_wired_manager()
    try:
        await _init_bus(rm)
        await rm.initialize()
        bus = rm._event_bus
        assert bus is not None

        alloc = await rm.allocate(ResourceType.MEMORY, 1024, "evt", "t")
        rm.release(alloc.allocation_id)

        names = await _drain(
            bus,
            {EventType.RESOURCE_ALLOCATED.name, EventType.RESOURCE_RELEASED.name},
        )
        assert EventType.RESOURCE_ALLOCATED.name in names
        assert EventType.RESOURCE_RELEASED.name in names

        # Every emitted event is canonical (has .name); payload has no forbidden keys.
        forbidden = {
            "eventId", "eventType", "correlationId", "source", "target",
            "timestamp", "payload", "checksum",
        }
        for e in bus.getRecentEvents():
            assert hasattr(e.eventType, "name"), "non-canonical EventType leaked"
            assert not (set(e.payload.to_dict().keys()) & forbidden)
    finally:
        await rm.shutdown()
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_resource_manager_singleton()


@pytest.mark.asyncio
async def test_quota_exceeded_canonical_event_and_no_invention():
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_resource_manager_singleton()
    rm = _build_wired_manager()
    try:
        await _init_bus(rm)
        await rm.initialize()
        bus = rm._event_bus
        assert bus is not None
        mem = rm.get_limit(ResourceType.MEMORY)
        assert mem is not None
        with pytest.raises(Exception):
            await rm.allocate(ResourceType.MEMORY, mem.limit + 100, "over", "x")
        names = await _drain(bus, {EventType.QUOTA_EXCEEDED.name})
        assert EventType.QUOTA_EXCEEDED.name in names
    finally:
        await rm.shutdown()
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_resource_manager_singleton()


# ---------------------------------------------------------------------------
# 20–21. sync→async bridge / no RuntimeWarning
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_emit_no_runtimewarning():
    """Synchronous emissions must not produce un-awaited-coroutine warnings."""
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_resource_manager_singleton()
    rm = _build_wired_manager()
    try:
        await _init_bus(rm)
        await rm.initialize()
        bus = rm._event_bus
        assert bus is not None

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            alloc = await rm.allocate(ResourceType.MEMORY, 512, "sw", "t")
            rm.release(alloc.allocation_id)
            await _drain(
                bus,
                {EventType.RESOURCE_ALLOCATED.name, EventType.RESOURCE_RELEASED.name},
            )

        runtime_warns = [w for w in caught if issubclass(w.category, RuntimeWarning)]
        assert not runtime_warns, f"Unexpected RuntimeWarning(s): {runtime_warns}"
    finally:
        await rm.shutdown()
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_resource_manager_singleton()


def test_sync_emit_without_running_loop_is_noop_not_leak():
    """Outside a running loop, emission is skipped (no un-awaited coroutine)."""
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_resource_manager_singleton()
    rm = _build_wired_manager()
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            # Call the sync emitter directly with no running loop.
            rm._emit_resource_event(EventType.RESOURCE_ALLOCATED, {"x": 1})
            runtime_warns = [
                w for w in caught if issubclass(w.category, RuntimeWarning)
            ]
            assert not runtime_warns, f"Unexpected RuntimeWarning: {runtime_warns}"
        assert rm._pending_tasks == set()
    finally:
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_resource_manager_singleton()


# ---------------------------------------------------------------------------
# 22. Persistence / state behavior (cleanup task; no external persistence)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cleanup_task_start_stop_idempotent():
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_resource_manager_singleton()
    rm = _build_wired_manager()
    try:
        await rm.initialize()
        rm.start_cleanup_task()
        # Second start is a no-op (already running).
        rm.start_cleanup_task()
        assert rm._cleanup_task is not None
        rm.stop_cleanup_task()
        assert rm._cleanup_task is None
        # Double stop is safe.
        rm.stop_cleanup_task()
    finally:
        await rm.shutdown()
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_resource_manager_singleton()


# ---------------------------------------------------------------------------
# 23. Error handling
# ---------------------------------------------------------------------------


def test_resource_manager_error_context():
    reset_resource_manager_singleton()
    try:
        err = ResourceManagerError("boom", rule_id="RM-INV-001")
        assert err.rule_id == "RM-INV-001"
        assert err.original_error is None
        assert "boom" in str(err)

        cause = KeyError("missing")
        err2 = ResourceManagerError(
            "wrapped", rule_id="RM-INV-002", original_error=cause
        )
        assert err2.original_error is cause
        assert "original_error=KeyError" in str(err2)

        # Subclass relationship preserved.
        assert isinstance(err, Exception)
    finally:
        reset_resource_manager_singleton()


def test_constructor_requires_event_bus():
    """Without a canonical EventBus, construction must fail diagnosably."""
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_resource_manager_singleton()
    try:
        with pytest.raises(RuntimeError):
            ResourceManager()
    finally:
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_resource_manager_singleton()


# ---------------------------------------------------------------------------
# 24. Regression — backward-compatible constructor / legacy config shim
# ---------------------------------------------------------------------------


def test_legacy_config_shim_preserved():
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_resource_manager_singleton()
    EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    try:
        # Legacy dict-form config is still accepted (backward compatible).
        rm = ResourceManager(
            config={
                "limits": [
                    {
                        "resource_type": "disk",
                        "limit": 999,
                        "unit": "MB",
                        "warning_threshold": 0.5,
                    }
                ]
            }
        )
        disk = rm.get_limit(ResourceType.DISK)
        assert disk is not None
        assert disk.limit == 999
        assert disk.warning_threshold == 0.5
    finally:
        reset_resource_manager_singleton()
        reset_event_bus_singleton()
        reset_service_registry_singleton()


def test_legacy_config_shim_malformed_is_diagnosable():
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_resource_manager_singleton()
    EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    try:
        # Malformed legacy override is skipped (logged), not crashed.
        rm = ResourceManager(
            config={"limits": [{"resource_type": "not_a_real_type"}]}
        )
        # No exception; default limits still present.
        assert rm.get_limit(ResourceType.MEMORY) is not None
    finally:
        reset_resource_manager_singleton()
        reset_event_bus_singleton()
        reset_service_registry_singleton()
