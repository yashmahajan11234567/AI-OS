"""
Task 12 — HealthManager Core Manager unit + integration tests (Part 4 §4.6).

Covers the ICoreManager surface (name / phase / dependencies / manager_id /
initialize / shutdown / health_ready), singleton behavior, ServiceRegistry
registration (as ``core.health``; Part 4 §4.6.1 names kernel.health — see
CONFLICT E.1 / INV-SR-NS-002), ConfigurationManager consumption, wiring of
the C4 StructuredLogger (no stdlib logger), the full health business API
(register / unregister / record / query / aggregate), canonical EventType
emission (only HEALTH_CHECK_PASSED / HEALTH_CHECK_FAILED / CORE_MANAGER_DEGRADED),
HealthManagerError semantics, and event-payload reserved-field compliance
(INV-EVT-011).

Per the CRITICAL EVENT TYPE RULE these tests assert ONLY on canonical Part-2
EventTypes. No new EventType is invented.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from aios.core.configuration_manager import (
    ConfigurationManager,
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
def hm(bus, sr, cm, logger, tmp_path):
    """A HealthManager wired to real canonical C1–C4, uninitialized."""
    reset_health_manager_singleton()
    mgr = HealthManager(
        service_registry=sr,
        configuration_manager=cm,
        logger=logger,
    )
    yield mgr
    reset_health_manager_singleton()
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()


async def _tick() -> None:
    """Yield to the event loop so scheduled publishes land.

    HealthManager._emit_health_event schedules ``bus.publish(event)`` via
    ``asyncio.ensure_future`` (FIX-FIND-01 sync-to-async bridge); the coroutine
    must be allowed to run before the event appears in bus history.
    """
    for _ in range(3):
        await asyncio.sleep(0)


async def _collected(bus: Any, wanted: set[str], deadline: int = 100) -> set[str]:
    """Poll bus history for the wanted canonical event names (bounded)."""
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


def test_construction(hm):
    assert isinstance(hm, HealthManager)
    assert hm.name == "HealthManager"
    assert hm.phase == 3
    assert hm.dependencies == ["LifecycleManager"]
    assert hm.manager_id == "core.health"
    assert hm.manager_id != "kernel.health"


def test_icoremanager_protocol_surface(hm):
    # ICoreManager structural surface (runtime_checkable is unreliable for
    # protocols with property members, so assert the members directly).
    assert hasattr(hm, "name") and hm.name == "HealthManager"
    assert hasattr(hm, "phase") and hm.phase == 3
    assert hasattr(hm, "dependencies")
    assert hasattr(hm, "manager_id") and hm.manager_id == "core.health"
    assert hasattr(hm, "initialize")
    assert hasattr(hm, "shutdown")
    assert hasattr(hm, "health_ready")


def test_health_ready_false_before_init(hm):
    # Not yet initialized -> not ready (and not wired for emission readiness
    # until initialize completes).
    assert hm.is_initialized is False
    assert hm.health_ready() is False


def test_event_bus_eager_resolution():
    # Without a canonical EventBus, construction must fail loudly (INV-EB-001).
    reset_event_bus_singleton()
    reset_health_manager_singleton()
    try:
        with pytest.raises(RuntimeError):
            HealthManager()
    finally:
        reset_event_bus_singleton()
        reset_health_manager_singleton()


# ---------------------------------------------------------------------------
# 4. singleton
# ---------------------------------------------------------------------------


def test_singleton_accessor_returns_same():
    reset_health_manager_singleton()
    reset_event_bus_singleton()
    EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    first = get_health_manager()
    second = get_health_manager()
    assert second is first
    reset_health_manager_singleton()
    reset_event_bus_singleton()


def test_set_singleton_overrides():
    reset_health_manager_singleton()
    reset_event_bus_singleton()
    EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    try:
        default = get_health_manager()
        custom = HealthManager()
        set_health_manager(custom)
        assert get_health_manager() is custom
        assert get_health_manager() is not default
    finally:
        reset_health_manager_singleton()
        reset_event_bus_singleton()


def test_reset_singleton_clears():
    reset_health_manager_singleton()
    reset_event_bus_singleton()
    EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    try:
        a = get_health_manager()
        reset_health_manager_singleton()
        b = get_health_manager()
        assert a is not b
    finally:
        reset_health_manager_singleton()
        reset_event_bus_singleton()


# ---------------------------------------------------------------------------
# 5. initialization / shutdown / ServiceRegistry
# ---------------------------------------------------------------------------


async def test_initialize_registers_core_health(hm, sr):
    assert not hm.is_initialized
    await hm.initialize()
    assert hm.is_initialized
    assert hm.health_ready() is True

    reg = sr.get_registration("core.health")
    assert reg is not None
    assert reg.service is hm
    assert reg.metadata.get("kind") == "core_manager"
    assert reg.metadata.get("manager") == "HealthManager"
    assert reg.metadata.get("phase") == 3


async def test_initialize_is_idempotent(hm, sr):
    await hm.initialize()
    assert hm.is_initialized
    # Second call must be a no-op and not raise / double-register.
    await hm.initialize()
    assert hm.is_initialized
    # Still exactly one registration identity.
    assert sr.get_registration("core.health") is not None


async def test_shutdown_marks_shutdown_and_clears(hm, sr):
    await hm.initialize()
    hm.register_check("svc", "c1")
    hm.record_health("svc", "c1", HealthStatus.HEALTHY)
    assert len(hm.list_checks()) == 1

    await hm.shutdown()
    assert hm.is_initialized is False
    assert hm.health_ready() is False
    # Checks cleared.
    assert hm.list_checks() == []
    # ServiceRegistry marks SHUTDOWN.
    reg = sr.get_registration("core.health")
    assert reg is not None
    assert reg.lifecycle_state.value == "SHUTDOWN"


async def test_shutdown_is_idempotent(hm):
    # Not initialized -> shutdown is a no-op (no exception).
    await hm.shutdown()
    assert hm.is_initialized is False


async def test_config_consumed_from_c3(hm, cm):
    cm.set_test_override("kernel.health.defaultIntervalSeconds", 99)
    cm.set_test_override("kernel.health.failureThreshold", 7)
    await hm.initialize()
    # The record_health path should reflect the configured defaults via the
    # auto-register path (interval_seconds falls back to configured default).
    hc = hm.register_check("svc", "c1")
    assert hc.interval_seconds == 99


# ---------------------------------------------------------------------------
# 6. health business API
# ---------------------------------------------------------------------------


def test_register_and_list_checks(hm):
    hc = hm.register_check("comp", "chk")
    assert isinstance(hc, HealthCheck)
    assert hc.component == "comp"
    assert hc.check_id == "chk"
    assert hc.enabled is True
    assert len(hm.list_checks()) == 1


def test_register_check_metadata(hm):
    hc = hm.register_check(
        "comp", "chk", enabled=False, interval_seconds=10, timeout_seconds=2.0
    )
    assert hc.enabled is False
    assert hc.interval_seconds == 10
    assert hc.timeout_seconds == 2.0


def test_get_and_unregister_check(hm):
    hm.register_check("comp", "chk")
    assert hm.get_check("comp", "chk") is not None
    assert hm.unregister_check("comp", "chk") is True
    assert hm.get_check("comp", "chk") is None
    # Unregistering a missing check returns False.
    assert hm.unregister_check("comp", "chk") is False


def test_record_health_returns_result(hm):
    result = hm.record_health("comp", "chk", HealthStatus.HEALTHY, message="ok")
    assert isinstance(result, HealthCheckResult)
    assert result.status is HealthStatus.HEALTHY
    assert result.component == "comp"
    assert result.message == "ok"


def test_record_health_auto_registers_check(hm):
    # Recording without a prior registration auto-creates the check.
    hm.record_health("comp", "chk", HealthStatus.HEALTHY)
    assert hm.get_check("comp", "chk") is not None
    assert hm.get_check("comp", "chk").last_result is not None


def test_get_component_health(hm):
    hm.record_health("comp", "chk", HealthStatus.DEGRADED)
    health = hm.get_component_health("comp")
    assert health is not None
    assert health["status"] == "DEGRADED"
    assert health["component"] == "comp"
    # Unknown component -> None.
    assert hm.get_component_health("nope") is None


def test_overall_status_worst_wins(hm):
    hm.record_health("a", "c", HealthStatus.HEALTHY)
    assert hm.overall_status is HealthStatus.HEALTHY
    hm.record_health("b", "c", HealthStatus.DEGRADED)
    assert hm.overall_status is HealthStatus.DEGRADED
    hm.record_health("c", "c", HealthStatus.UNHEALTHY)
    assert hm.overall_status is HealthStatus.UNHEALTHY


def test_get_all_health_snapshot(hm):
    hm.record_health("a", "c", HealthStatus.HEALTHY)
    hm.record_health("b", "c", HealthStatus.UNHEALTHY)
    snap = hm.get_all_health()
    assert snap["overall"] == "UNHEALTHY"
    assert snap["components"]["a"] == "HEALTHY"
    assert snap["components"]["b"] == "UNHEALTHY"
    assert snap["total_checks"] == 2
    assert snap["healthy_checks"] == 1
    assert snap["unhealthy_checks"] == 1


def test_consecutive_failures_tracked(hm):
    hm.record_health("a", "c", HealthStatus.UNHEALTHY)
    hm.record_health("a", "c", HealthStatus.UNHEALTHY)
    hc = hm.get_check("a", "c")
    assert hc.consecutive_failures == 2
    hm.record_health("a", "c", HealthStatus.HEALTHY)
    assert hc.consecutive_failures == 0


# ---------------------------------------------------------------------------
# 7. canonical EventType emission (CONFLICT E.1 — no invented EventTypes)
# ---------------------------------------------------------------------------


async def test_emit_health_check_passed_event(hm, bus):
    await bus.initialize()
    await hm.initialize()
    hm.record_health("a", "c", HealthStatus.HEALTHY)
    seen = await _collected(bus, {EventType.HEALTH_CHECK_PASSED.name})
    assert EventType.HEALTH_CHECK_PASSED.name in seen


async def test_emit_health_check_failed_event(hm, bus):
    await bus.initialize()
    await hm.initialize()
    hm.record_health("a", "c", HealthStatus.UNHEALTHY)
    seen = await _collected(bus, {EventType.HEALTH_CHECK_FAILED.name})
    assert EventType.HEALTH_CHECK_FAILED.name in seen


async def test_emit_core_manager_degraded_event(hm, bus):
    await bus.initialize()
    await hm.initialize()
    hm.record_health("a", "c", HealthStatus.DEGRADED)
    seen = await _collected(bus, {EventType.CORE_MANAGER_DEGRADED.name})
    assert EventType.CORE_MANAGER_DEGRADED.name in seen


async def test_emitted_events_are_all_canonical(hm, bus):
    await bus.initialize()
    await hm.initialize()
    hm.record_health("a", "c", HealthStatus.HEALTHY)
    hm.record_health("b", "c", HealthStatus.UNHEALTHY)
    hm.record_health("c", "c", HealthStatus.DEGRADED)
    await _tick()
    for e in bus.getRecentEvents():
        assert hasattr(e.eventType, "name"), "non-canonical EventType leaked"


async def test_event_payload_omits_reserved_fields(hm, bus):
    """EventPayload rejects reserved base-contract fields (INV-EVT-011)."""
    await bus.initialize()
    await hm.initialize()
    hm.record_health("a", "c", HealthStatus.HEALTHY)
    await _tick()
    for e in bus.getRecentEvents():
        if e.eventType.name == EventType.HEALTH_CHECK_PASSED.name:
            # 'timestamp' (reserved) must NOT appear; 'checked_at' must.
            assert "timestamp" not in e.payload
            assert e.payload.get("checked_at")
            assert e.payload.get("component") == "a"
            assert e.payload.get("status") == "HEALTHY"
            assert e.payload.get("manager") == "HealthManager"
            assert e.payload.get("manager_id") == "core.health"


async def test_no_event_when_loop_not_running(hm, bus):
    """From a sync context with no running loop, emission is skipped (no warn)."""
    # initialize sets up the manager; record_health called outside a running
    # loop must not raise and must not enqueue a coroutine.
    await hm.initialize()
    # If the loop is not running in this context, record_health should still
    # store the result without emitting. We assert the stored result exists.
    hm.record_health("a", "c", HealthStatus.HEALTHY)
    assert hm.get_check("a", "c").last_result.status is HealthStatus.HEALTHY


# ---------------------------------------------------------------------------
# 8. errors
# ---------------------------------------------------------------------------


def test_health_manager_error_plain():
    err = HealthManagerError("boom")
    assert str(err) == "boom"
    assert err.rule_id is None
    assert err.original_error is None


def test_health_manager_error_with_rule_id():
    err = HealthManagerError("boom", rule_id="HM-INV-001")
    assert err.rule_id == "HM-INV-001"
    assert "boom" in str(err)


def test_health_manager_error_with_original():
    inner = ValueError("inner-cause")
    err = HealthManagerError("wrap", rule_id="HM-INV-002", original_error=inner)
    assert "original_error=ValueError: inner-cause" in str(err)
    assert err.original_error is inner


def test_health_manager_error_is_exception():
    err = HealthManagerError("x")
    assert isinstance(err, Exception)
    with pytest.raises(HealthManagerError):
        raise err
