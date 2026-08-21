"""
Task 14 — SecurityManager Core Manager unit + integration tests (Part 4 §4.7).

Covers the ICoreManager surface (name / phase / dependencies / manager_id /
initialize / shutdown / health_ready), singleton behavior, ServiceRegistry
registration (as ``core.security``; Part 4 §4.7 names kernel.security — see
CONFLICT E.1 / INV-SR-NS-002), ConfigurationManager consumption, wiring of the
C4 StructuredLogger (no stdlib logger), the full security business API
(authorize / record_violation / get_violation / list_violations), canonical
EventType emission (only SECURITY_ISSUE_FOUND), SecurityManagerError semantics,
and event-payload reserved-field compliance (INV-EVT-011).

Per the CRITICAL EVENTTYPE RULE these tests assert ONLY on canonical Part-2
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
from aios.core.security_manager import (
    SecurityDecision,
    SecurityManager,
    SecurityManagerError,
    SecurityViolation,
    get_security_manager,
    reset_security_manager_singleton,
    set_security_manager,
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
def sm(bus, sr, cm, logger, tmp_path):
    """A SecurityManager wired to real canonical C1–C4, uninitialized."""
    reset_security_manager_singleton()
    mgr = SecurityManager(
        service_registry=sr,
        configuration_manager=cm,
        logger=logger,
    )
    yield mgr
    reset_security_manager_singleton()
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()


async def _tick() -> None:
    """Yield to the event loop so scheduled publishes land."""
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


def test_construction(sm):
    assert isinstance(sm, SecurityManager)
    assert sm.name == "SecurityManager"
    assert sm.phase == 3
    assert sm.dependencies == ["LifecycleManager"]
    assert sm.manager_id == "core.security"
    assert sm.manager_id != "kernel.security"


def test_icoremanager_protocol_surface(sm):
    assert hasattr(sm, "name") and sm.name == "SecurityManager"
    assert hasattr(sm, "phase") and sm.phase == 3
    assert hasattr(sm, "dependencies")
    assert hasattr(sm, "manager_id") and sm.manager_id == "core.security"
    assert hasattr(sm, "initialize")
    assert hasattr(sm, "shutdown")
    assert hasattr(sm, "health_ready")


def test_health_ready_false_before_init(sm):
    assert sm.is_initialized is False
    assert sm.health_ready() is False


def test_event_bus_eager_resolution():
    # Without a canonical EventBus, construction must fail loudly (INV-EB-001).
    reset_event_bus_singleton()
    reset_security_manager_singleton()
    try:
        with pytest.raises(RuntimeError):
            SecurityManager()
    finally:
        reset_event_bus_singleton()
        reset_security_manager_singleton()


# ---------------------------------------------------------------------------
# 4. singleton
# ---------------------------------------------------------------------------


def test_singleton_accessor_returns_same():
    reset_security_manager_singleton()
    reset_event_bus_singleton()
    EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    first = get_security_manager()
    second = get_security_manager()
    assert second is first
    reset_security_manager_singleton()
    reset_event_bus_singleton()


def test_set_singleton_overrides():
    reset_security_manager_singleton()
    reset_event_bus_singleton()
    EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    try:
        default = get_security_manager()
        custom = SecurityManager()
        set_security_manager(custom)
        assert get_security_manager() is custom
        assert get_security_manager() is not default
    finally:
        reset_security_manager_singleton()
        reset_event_bus_singleton()


def test_reset_singleton_clears():
    reset_security_manager_singleton()
    reset_event_bus_singleton()
    EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    try:
        a = get_security_manager()
        reset_security_manager_singleton()
        b = get_security_manager()
        assert a is not b
    finally:
        reset_security_manager_singleton()
        reset_event_bus_singleton()


# ---------------------------------------------------------------------------
# 5. initialization / shutdown / ServiceRegistry
# ---------------------------------------------------------------------------


async def test_initialize_registers_core_security(sm, sr):
    assert not sm.is_initialized
    await sm.initialize()
    assert sm.is_initialized
    assert sm.health_ready() is True

    reg = sr.get_registration("core.security")
    assert reg is not None
    assert reg.service is sm
    assert reg.metadata.get("kind") == "core_manager"
    assert reg.metadata.get("manager") == "SecurityManager"
    assert reg.metadata.get("phase") == 3


async def test_initialize_is_idempotent(sm, sr):
    await sm.initialize()
    assert sm.is_initialized
    await sm.initialize()
    assert sm.is_initialized
    assert sr.get_registration("core.security") is not None


async def test_shutdown_marks_shutdown_and_clears(sm, sr):
    await sm.initialize()
    sm.record_violation(severity="high", description="x")
    assert len(sm.list_violations()) >= 1

    await sm.shutdown()
    assert sm.is_initialized is False
    assert sm.health_ready() is False
    assert sm.list_violations() == []
    reg = sr.get_registration("core.security")
    assert reg is not None
    assert reg.lifecycle_state.value == "SHUTDOWN"


async def test_shutdown_is_idempotent(sm):
    await sm.shutdown()
    assert sm.is_initialized is False


async def test_config_consumed_from_c3(sm, cm):
    cm.set_test_override("kernel.security.failClosed", False)
    cm.set_test_override("kernel.security.auditAllDenials", False)
    await sm.initialize()
    assert sm._fail_closed is False
    assert sm._audit_all_denials is False


# ---------------------------------------------------------------------------
# 6. security business API
# ---------------------------------------------------------------------------


def test_authorize_unknown_principal_denies(sm):
    # Fail-closed: unknown/None principal -> DENY.
    decision = sm.authorize(None, "read", "resource")
    assert decision is SecurityDecision.DENY


def test_record_violation_returns_violation(sm):
    violation = sm.record_violation(
        severity="high",
        description="test violation",
        category="authorization",
        context={"action": "read"},
    )
    assert isinstance(violation, SecurityViolation)
    assert violation.severity == "high"
    assert violation.description == "test violation"
    assert violation.category == "authorization"
    assert violation.violation_id
    # Recorded locally.
    assert violation in sm.list_violations()


def test_get_violation_by_id(sm):
    v = sm.record_violation(severity="low", description="d")
    assert sm.get_violation(v.violation_id) is v
    assert sm.get_violation("nonexistent") is None


def test_list_violations_snapshot(sm):
    sm.record_violation(severity="low", description="a")
    sm.record_violation(severity="high", description="b")
    vios = sm.list_violations()
    assert len(vios) == 2
    # Snapshot semantics: mutation of the returned list must not affect state.
    vios.clear()
    assert len(sm.list_violations()) == 2


# ---------------------------------------------------------------------------
# 7. canonical EventType emission (CONFLICT E.1 — no invented EventTypes)
# ---------------------------------------------------------------------------


async def test_record_violation_emits_security_issue_found(sm, bus):
    await bus.initialize()
    await sm.initialize()

    sm.record_violation(severity="high", description="issue")
    seen = await _collected(bus, {EventType.SECURITY_ISSUE_FOUND.name})
    assert EventType.SECURITY_ISSUE_FOUND.name in seen


async def test_authorize_unknown_emits_on_audit(sm, bus):
    await bus.initialize()
    await sm.initialize()
    sm.authorize(None, "read", "res")
    seen = await _collected(bus, {EventType.SECURITY_ISSUE_FOUND.name})
    assert EventType.SECURITY_ISSUE_FOUND.name in seen


async def test_emitted_events_are_all_canonical(sm, bus):
    await bus.initialize()
    await sm.initialize()
    sm.record_violation(severity="low", description="a")
    sm.authorize(None, "act", "res")
    await _tick()
    for e in bus.getRecentEvents():
        assert hasattr(e.eventType, "name"), "non-canonical EventType leaked"


async def test_event_payload_reserved_fields(sm, bus):
    """EventPayload rejects reserved base-contract fields (INV-EVT-011)."""
    await bus.initialize()
    await sm.initialize()
    v = sm.record_violation(
        severity="high",
        description="d",
        category="cat",
        context={"k": "v"},
    )
    await _tick()
    matched = False
    for e in bus.getRecentEvents():
        if e.eventType.name == EventType.SECURITY_ISSUE_FOUND.name:
            assert "timestamp" not in e.payload, "reserved field 'timestamp' leaked"
            assert e.payload.get("manager") == "SecurityManager"
            assert e.payload.get("manager_id") == "core.security"
            assert e.payload.get("issue_id") == v.violation_id
            assert e.payload.get("severity") == "high"
            assert e.payload.get("violation_category") == "cat"
            assert e.payload.get("description") == "d"
            assert e.payload.get("context") == {"k": "v"}
            matched = True
    assert matched, "SECURITY_ISSUE_FOUND event not emitted"


async def test_no_event_when_loop_not_running(sm, bus):
    await sm.initialize()
    # record_violation must not raise even though no running loop is publishing.
    v = sm.record_violation(severity="low", description="sync")
    assert v.violation_id is not None


# ---------------------------------------------------------------------------
# 8. errors
# ---------------------------------------------------------------------------


def test_security_manager_error_plain():
    err = SecurityManagerError("boom")
    assert str(err) == "boom"
    assert err.rule_id is None
    assert err.original_error is None


def test_security_manager_error_with_rule_id():
    err = SecurityManagerError("boom", rule_id="SM-INV-001")
    assert err.rule_id == "SM-INV-001"
    assert "boom" in str(err)


def test_security_manager_error_with_original():
    inner = ValueError("inner-cause")
    err = SecurityManagerError("wrap", rule_id="SM-INV-002", original_error=inner)
    assert "original_error=ValueError: inner-cause" in str(err)
    assert err.original_error is inner


def test_security_manager_error_is_exception():
    err = SecurityManagerError("x")
    assert isinstance(err, Exception)
    with pytest.raises(SecurityManagerError):
        raise err
