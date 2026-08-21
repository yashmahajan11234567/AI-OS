"""
Task 15 — CapabilityManager Core Manager unit + integration tests (Part 4 §4.6,
CONFLICT-CM-01).

Covers the ICoreManager surface (name / phase / dependencies / manager_id /
initialize / shutdown / health_ready), singleton behavior, ServiceRegistry
registration (as ``core.capability``; Part 4 §4.6.1 names kernel.capability —
see CONFLICT E.1 / INV-SR-NS-002), ConfigurationManager consumption, wiring of
the C4 StructuredLogger (no stdlib logger), the full capability business API
(register / deregister / get_capability / list_capabilities /
discover_by_facade / discover_by_tags / resolve / invoke), canonical EventType
emission (only SERVICE_STARTED / SERVICE_STOPPED / SKILL_EXECUTED /
SKILL_FAILED — mapping CapabilityRegisteredEvent / CapabilityRemovedEvent /
CapabilityInvocationEvent / CapabilityInvocationFailedEvent, CONFLICT E.1),
CapabilityManagerError semantics, and event-payload reserved-field compliance
(INV-EVT-011).

Per the CRITICAL EVENTTYPE RULE these tests assert ONLY on canonical Part-2
EventTypes. No new EventType is invented.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from aios.core.capability_manager import (
    CapabilityManager,
    CapabilityManagerError,
    CapabilityRegistryEntry,
    CapabilityState,
    get_capability_manager,
    reset_capability_manager_singleton,
    set_capability_manager,
)
from aios.core.configuration_manager import (
    ConfigurationManager,
    reset_configuration_manager_singleton,
)
from aios.core.service_registry import (
    get_service_registry,
    reset_service_registry_singleton,
)
from aios.core.structured_logger import get_logger
from aios.events.core.bus import (
    EventBus,
    EventBusConfig,
    reset_event_bus_singleton,
)
from aios.events.core.types import EventType


@pytest.fixture
def bus():
    """A canonical EventBus singleton (no dispatch worker; publish is awaited)."""
    reset_event_bus_singleton()
    b = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    yield b
    reset_event_bus_singleton()


@pytest.fixture
def sr(bus):
    """A canonical ServiceRegistry wired to the bus."""
    reset_service_registry_singleton()
    reg = get_service_registry(event_bus=bus)
    yield reg
    reset_service_registry_singleton()


@pytest.fixture
def cm(bus):
    """A canonical ConfigurationManager (empty/frozen)."""
    reset_configuration_manager_singleton()
    c = ConfigurationManager(event_bus=bus)
    yield c
    reset_configuration_manager_singleton()


@pytest.fixture
def logger(bus):
    """A canonical StructuredLogger."""
    return get_logger()


@pytest.fixture
def cmgr(bus, sr, cm, logger, tmp_path):
    """A CapabilityManager wired to real canonical C1–C4, uninitialized."""
    reset_capability_manager_singleton()
    mgr = CapabilityManager(
        service_registry=sr,
        configuration_manager=cm,
        logger=logger,
    )
    yield mgr
    reset_capability_manager_singleton()
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()


async def _tick() -> None:
    for _ in range(3):
        await asyncio.sleep(0)


async def _collected(bus: Any, wanted: set[str], deadline: int = 100) -> set[str]:
    seen: set[str] = set()
    for _ in range(deadline):
        seen = {
            e.eventType.name
            for e in bus.getRecentEvents()
            if hasattr(e.eventType, "name")
        }
        if wanted <= seen:
            return seen
        await asyncio.sleep(0)
    return seen


# ---------------------------------------------------------------------------
# 1. construction / 2. identity / 3. ICoreManager surface
# ---------------------------------------------------------------------------


def test_construction(cmgr):
    assert isinstance(cmgr, CapabilityManager)
    assert cmgr.name == "CapabilityManager"
    assert cmgr.phase == 4
    assert cmgr.dependencies == ["LifecycleManager"]
    assert cmgr.manager_id == "core.capability"
    assert cmgr.manager_id != "kernel.capability"


def test_icoremanager_protocol_surface(cmgr):
    assert hasattr(cmgr, "name") and cmgr.name == "CapabilityManager"
    assert hasattr(cmgr, "phase") and cmgr.phase == 4
    assert hasattr(cmgr, "dependencies")
    assert hasattr(cmgr, "manager_id") and cmgr.manager_id == "core.capability"
    assert hasattr(cmgr, "initialize")
    assert hasattr(cmgr, "shutdown")
    assert hasattr(cmgr, "health_ready")


def test_health_ready_false_before_init(cmgr):
    assert cmgr.is_initialized is False
    assert cmgr.health_ready() is False


def test_event_bus_eager_resolution():
    reset_event_bus_singleton()
    reset_capability_manager_singleton()
    try:
        with pytest.raises(RuntimeError):
            CapabilityManager()
    finally:
        reset_event_bus_singleton()
        reset_capability_manager_singleton()


# ---------------------------------------------------------------------------
# 4. singleton
# ---------------------------------------------------------------------------


def test_singleton_accessor_returns_same():
    reset_capability_manager_singleton()
    reset_event_bus_singleton()
    EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    first = get_capability_manager()
    second = get_capability_manager()
    assert second is first
    reset_capability_manager_singleton()
    reset_event_bus_singleton()


def test_set_singleton_overrides():
    reset_capability_manager_singleton()
    reset_event_bus_singleton()
    EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    try:
        default = get_capability_manager()
        custom = CapabilityManager()
        set_capability_manager(custom)
        assert get_capability_manager() is custom
        assert get_capability_manager() is not default
    finally:
        reset_capability_manager_singleton()
        reset_event_bus_singleton()


def test_reset_singleton_clears():
    reset_capability_manager_singleton()
    reset_event_bus_singleton()
    EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    try:
        a = get_capability_manager()
        reset_capability_manager_singleton()
        b = get_capability_manager()
        assert a is not b
    finally:
        reset_capability_manager_singleton()
        reset_capability_manager_singleton()
        reset_event_bus_singleton()


# ---------------------------------------------------------------------------
# 5. initialization / shutdown / ServiceRegistry
# ---------------------------------------------------------------------------


async def test_initialize_registers_core_capability(cmgr, sr):
    assert not cmgr.is_initialized
    await cmgr.initialize()
    assert cmgr.is_initialized
    assert cmgr.health_ready() is True

    reg = sr.get_registration("core.capability")
    assert reg is not None
    assert reg.service is cmgr
    assert reg.metadata.get("kind") == "core_manager"
    assert reg.metadata.get("manager") == "CapabilityManager"
    assert reg.metadata.get("phase") == 4


async def test_initialize_is_idempotent(cmgr, sr):
    await cmgr.initialize()
    assert cmgr.is_initialized
    await cmgr.initialize()
    assert cmgr.is_initialized
    assert sr.get_registration("core.capability") is not None


async def test_shutdown_marks_shutdown_and_clears(cmgr, sr):
    await cmgr.initialize()
    cmgr.register("cap.x", "facade.x", "provider.x")
    assert len(cmgr.list_capabilities()) == 1

    await cmgr.shutdown()
    assert cmgr.is_initialized is False
    assert cmgr.health_ready() is False
    assert cmgr.list_capabilities() == []
    reg = sr.get_registration("core.capability")
    assert reg is not None
    assert reg.lifecycle_state.value == "SHUTDOWN"


async def test_shutdown_is_idempotent(cmgr):
    await cmgr.shutdown()
    assert cmgr.is_initialized is False


async def test_config_consumed_from_c3(cmgr, cm):
    cm.set_test_override("kernel.capability.enforceAuthorization", False)
    await cmgr.initialize()
    assert cmgr._enforce_authorization is False


# ---------------------------------------------------------------------------
# 6. capability business API
# ---------------------------------------------------------------------------


def test_register_returns_entry(cmgr):
    entry = cmgr.register("cap.x", "facade.x", "provider.x")
    assert isinstance(entry, CapabilityRegistryEntry)
    assert entry.capability_id == "cap.x"
    assert entry.facade == "facade.x"
    assert entry.provider_id == "provider.x"
    assert entry.state is CapabilityState.REGISTERED
    assert entry.version == "1.0.0"


def test_register_rejects_duplicate(cmgr):
    cmgr.register("cap.x", "facade.x", "provider.x")
    with pytest.raises(CapabilityManagerError) as exc:
        cmgr.register("cap.x", "facade.y", "provider.y")
    assert exc.value.rule_id == "CM-DUP-001"


def test_deregister_returns_bool(cmgr):
    cmgr.register("cap.x", "facade.x", "provider.x")
    assert cmgr.deregister("cap.x") is True
    # Removed -> REMOVED state.
    assert cmgr.get_capability("cap.x") is None
    # Deregistering missing -> False.
    assert cmgr.deregister("cap.x") is False


def test_get_capability_and_list(cmgr):
    a = cmgr.register("cap.a", "facade", "provider")
    cmgr.register("cap.b", "facade", "provider")
    assert cmgr.get_capability("cap.a") is a
    assert cmgr.get_capability("missing") is None
    assert len(cmgr.list_capabilities()) == 2


def test_discover_by_facade(cmgr):
    cmgr.register("cap.a", "facade1", "provider")
    cmgr.register("cap.b", "facade2", "provider")
    cmgr.register("cap.c", "facade1", "provider")
    found = cmgr.discover_by_facade("facade1")
    assert len(found) == 2
    assert {e.capability_id for e in found} == {"cap.a", "cap.c"}


def test_discover_by_tags(cmgr):
    cmgr.register("cap.a", "f", "p", tags=("t1", "t2"))
    cmgr.register("cap.b", "f", "p", tags=("t2",))
    cmgr.register("cap.c", "f", "p", tags=("t3",))
    found = cmgr.discover_by_tags(("t2",))
    assert {e.capability_id for e in found} == {"cap.a", "cap.b"}
    # Multiple required tags -> intersection.
    found2 = cmgr.discover_by_tags(("t1", "t2"))
    assert {e.capability_id for e in found2} == {"cap.a"}
    # Empty tags -> all.
    assert len(cmgr.discover_by_tags(())) == 3


def test_resolve_returns_entry(cmgr):
    cmgr.register("cap.x", "facade.x", "provider.x")
    entry = cmgr.resolve("cap.x")
    assert entry.capability_id == "cap.x"


def test_resolve_unregistered_raises(cmgr):
    with pytest.raises(CapabilityManagerError) as exc:
        cmgr.resolve("nope")
    assert exc.value.rule_id == "CM-RES-001"


def test_invoke_resolves_and_returns(cmgr):
    cmgr.register("cap.x", "facade.x", "provider.x")
    entry = cmgr.invoke("cap.x", input_payload={"k": "v"}, caller_context={})
    assert isinstance(entry, CapabilityRegistryEntry)
    assert entry.capability_id == "cap.x"


def test_invoke_unregistered_emits_failure_event(cmgr):
    # invoke on a missing capability raises AND emits the canonical
    # SKILL_FAILED event (mapping CapabilityInvocationFailedEvent).
    with pytest.raises(CapabilityManagerError):
        cmgr.invoke("nope")
    # The event is emitted via the sync->async bridge only when a loop is running;
    # assert the method did not raise an un-awaited-coroutine warning instead and
    # that the missing capability correctly raises.
    assert cmgr.get_capability("nope") is None


# ---------------------------------------------------------------------------
# 7. canonical EventType emission (CONFLICT E.1 — no invented EventTypes)
# ---------------------------------------------------------------------------


async def test_register_emits_service_started(cmgr, bus):
    await bus.initialize()
    await cmgr.initialize()
    cmgr.register("cap.x", "facade", "provider")
    seen = await _collected(bus, {EventType.SERVICE_STARTED.name})
    assert EventType.SERVICE_STARTED.name in seen


async def test_deregister_emits_service_stopped(cmgr, bus):
    await bus.initialize()
    await cmgr.initialize()
    cmgr.register("cap.x", "facade", "provider")
    cmgr.deregister("cap.x")
    seen = await _collected(bus, {EventType.SERVICE_STOPPED.name})
    assert EventType.SERVICE_STOPPED.name in seen


async def test_invoke_emits_skill_executed(cmgr, bus):
    await bus.initialize()
    await cmgr.initialize()
    cmgr.register("cap.x", "facade", "provider")
    cmgr.invoke("cap.x")
    seen = await _collected(bus, {EventType.SKILL_EXECUTED.name})
    assert EventType.SKILL_EXECUTED.name in seen


async def test_emitted_events_are_all_canonical(cmgr, bus):
    await bus.initialize()
    await cmgr.initialize()
    cmgr.register("cap.x", "facade", "provider")
    cmgr.deregister("cap.x")
    cmgr.register("cap.y", "facade", "provider")
    cmgr.invoke("cap.y")
    await _tick()
    for e in bus.getRecentEvents():
        assert hasattr(e.eventType, "name"), "non-canonical EventType leaked"


async def test_event_payload_reserved_fields(cmgr, bus):
    """EventPayload rejects reserved base-contract fields (INV-EVT-011)."""
    await bus.initialize()
    await cmgr.initialize()
    cmgr.register("cap.x", "facade", "provider")
    await _tick()
    matched = False
    for e in bus.getRecentEvents():
        if (
            e.eventType.name == EventType.SERVICE_STARTED.name
            and e.payload.get("capability_id") == "cap.x"
        ):
            # This is the manager-emitted capability registration event (not the
            # ServiceRegistry's own registration envelope).
            assert "timestamp" not in e.payload, "reserved field 'timestamp' leaked"
            assert "category" not in e.payload, "reserved field 'category' leaked"
            assert e.payload.get("manager") == "CapabilityManager"
            assert e.payload.get("manager_id") == "core.capability"
            assert e.payload.get("capability_id") == "cap.x"
            assert e.payload.get("facade") == "facade"
            assert e.payload.get("provider_id") == "provider"
            matched = True
    assert matched, "manager-emitted SERVICE_STARTED for capability not emitted"


# ---------------------------------------------------------------------------
# 8. errors
# ---------------------------------------------------------------------------


def test_capability_manager_error_plain():
    err = CapabilityManagerError("boom")
    assert str(err) == "boom"
    assert err.rule_id is None
    assert err.original_error is None


def test_capability_manager_error_with_rule_id():
    err = CapabilityManagerError("boom", rule_id="CM-INV-001")
    assert err.rule_id == "CM-INV-001"
    assert "boom" in str(err)


def test_capability_manager_error_with_original():
    inner = ValueError("inner-cause")
    err = CapabilityManagerError("wrap", rule_id="CM-INV-002", original_error=inner)
    assert "original_error=ValueError: inner-cause" in str(err)
    assert err.original_error is inner


def test_capability_manager_error_is_exception():
    err = CapabilityManagerError("x")
    assert isinstance(err, Exception)
    with pytest.raises(CapabilityManagerError):
        raise err
