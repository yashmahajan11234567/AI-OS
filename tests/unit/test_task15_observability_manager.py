"""
Task 15 — ObservabilityManager Core Manager unit + integration tests (Part 4 §4.9).

Covers the ICoreManager surface (name / phase / dependencies / manager_id /
initialize / shutdown / health_ready), singleton behavior, ServiceRegistry
registration (as ``core.observability``; Part 4 §4.9 names kernel.observability
— see CONFLICT E.1 / INV-SR-NS-002), ConfigurationManager consumption, wiring of
the C4 StructuredLogger (no stdlib logger, no second logging system), the full
observability business API (record_metric / start_span / end_span /
get_metrics / get_spans), canonical EventType emission (only METRIC_EMITTED /
TRACE_SPAN_STARTED / TRACE_SPAN_ENDED — Part 4 §4.9.11 names like
MetricRegisteredEvent / TraceSampledEvent have no canonical equivalent and are
omitted, not invented), ObservabilityManagerError semantics, and event-payload
reserved-field compliance (INV-EVT-011).

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
from aios.core.observability_manager import (
    MetricRecord,
    MetricType,
    ObservabilityManager,
    ObservabilityManagerError,
    SpanRecord,
    get_observability_manager,
    reset_observability_manager_singleton,
    set_observability_manager,
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
def om(bus, sr, cm, logger, tmp_path):
    """An ObservabilityManager wired to real canonical C1–C4, uninitialized."""
    reset_observability_manager_singleton()
    mgr = ObservabilityManager(
        service_registry=sr,
        configuration_manager=cm,
        logger=logger,
    )
    yield mgr
    reset_observability_manager_singleton()
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


def test_construction(om):
    assert isinstance(om, ObservabilityManager)
    assert om.name == "ObservabilityManager"
    assert om.phase == 5
    assert om.dependencies == ["LifecycleManager"]
    assert om.manager_id == "core.observability"
    assert om.manager_id != "kernel.observability"


def test_icoremanager_protocol_surface(om):
    assert hasattr(om, "name") and om.name == "ObservabilityManager"
    assert hasattr(om, "phase") and om.phase == 5
    assert hasattr(om, "dependencies")
    assert hasattr(om, "manager_id") and om.manager_id == "core.observability"
    assert hasattr(om, "initialize")
    assert hasattr(om, "shutdown")
    assert hasattr(om, "health_ready")


def test_health_ready_false_before_init(om):
    assert om.is_initialized is False
    assert om.health_ready() is False


def test_event_bus_eager_resolution():
    reset_event_bus_singleton()
    reset_observability_manager_singleton()
    try:
        with pytest.raises(RuntimeError):
            ObservabilityManager()
    finally:
        reset_event_bus_singleton()
        reset_observability_manager_singleton()


# ---------------------------------------------------------------------------
# 4. singleton
# ---------------------------------------------------------------------------


def test_singleton_accessor_returns_same():
    reset_observability_manager_singleton()
    reset_event_bus_singleton()
    EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    first = get_observability_manager()
    second = get_observability_manager()
    assert second is first
    reset_observability_manager_singleton()
    reset_event_bus_singleton()


def test_set_singleton_overrides():
    reset_observability_manager_singleton()
    reset_event_bus_singleton()
    EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    try:
        default = get_observability_manager()
        custom = ObservabilityManager()
        set_observability_manager(custom)
        assert get_observability_manager() is custom
        assert get_observability_manager() is not default
    finally:
        reset_observability_manager_singleton()
        reset_event_bus_singleton()


def test_reset_singleton_clears():
    reset_observability_manager_singleton()
    reset_event_bus_singleton()
    EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    try:
        a = get_observability_manager()
        reset_observability_manager_singleton()
        b = get_observability_manager()
        assert a is not b
    finally:
        reset_observability_manager_singleton()
        reset_event_bus_singleton()


# ---------------------------------------------------------------------------
# 5. initialization / shutdown / ServiceRegistry
# ---------------------------------------------------------------------------


async def test_initialize_registers_core_observability(om, sr):
    assert not om.is_initialized
    await om.initialize()
    assert om.is_initialized
    assert om.health_ready() is True

    reg = sr.get_registration("core.observability")
    assert reg is not None
    assert reg.service is om
    assert reg.metadata.get("kind") == "core_manager"
    assert reg.metadata.get("manager") == "ObservabilityManager"
    assert reg.metadata.get("phase") == 5


async def test_initialize_is_idempotent(om, sr):
    await om.initialize()
    assert om.is_initialized
    await om.initialize()
    assert om.is_initialized
    assert sr.get_registration("core.observability") is not None


async def test_shutdown_marks_shutdown_and_clears(om, sr):
    await om.initialize()
    om.record_metric("m1", MetricType.COUNTER, 1.0)
    om.start_span("s1")
    assert len(om.get_metrics()) == 1
    assert len(om.get_spans()) == 1

    await om.shutdown()
    assert om.is_initialized is False
    assert om.health_ready() is False
    assert om.get_metrics() == []
    assert om.get_spans() == []
    reg = sr.get_registration("core.observability")
    assert reg is not None
    assert reg.lifecycle_state.value == "SHUTDOWN"


async def test_shutdown_is_idempotent(om):
    await om.shutdown()
    assert om.is_initialized is False


async def test_config_consumed_from_c3(om, cm):
    cm.set_test_override("kernel.observability.metricsEnabled", False)
    cm.set_test_override("kernel.observability.tracingEnabled", False)
    await om.initialize()
    assert om._metrics_enabled is False
    assert om._tracing_enabled is False


# ---------------------------------------------------------------------------
# 6. observability business API (metrics & tracing; NO second logging system)
# ---------------------------------------------------------------------------


def test_record_metric_returns_record(om):
    rec = om.record_metric("requests", MetricType.COUNTER, 5.0, unit="req")
    assert isinstance(rec, MetricRecord)
    assert rec.name == "requests"
    assert rec.metric_type is MetricType.COUNTER
    assert rec.value == 5.0
    assert rec.unit == "req"
    assert rec.labels == {}
    assert rec in om.get_metrics()


def test_record_metric_with_labels(om):
    om.record_metric(
        "latency", MetricType.HISTOGRAM, 0.12,
        unit="s", labels={"status": "200"},
    )
    metrics = om.get_metrics()
    assert len(metrics) == 1
    assert metrics[0].labels == {"status": "200"}


def test_get_metrics_snapshot(om):
    om.record_metric("a", MetricType.COUNTER, 1.0)
    om.record_metric("b", MetricType.GAUGE, 2.0)
    snap = om.get_metrics()
    assert len(snap) == 2
    snap.clear()  # snapshot semantics
    assert len(om.get_metrics()) == 2


def test_start_span_returns_record(om):
    span = om.start_span("op", attributes={"k": "v"})
    assert isinstance(span, SpanRecord)
    assert span.name == "op"
    assert span.span_id
    assert span.trace_id
    assert span.attributes == {"k": "v"}
    assert span in om.get_spans()


def test_end_span_removes_and_returns(om):
    span = om.start_span("op")
    assert span.span_id in {s.span_id for s in om.get_spans()}
    assert om.end_span(span.span_id) is True
    assert span.span_id not in {s.span_id for s in om.get_spans()}
    # Ending a missing span -> False.
    assert om.end_span("gone") is False


def test_end_span_unknown_returns_false(om):
    assert om.end_span("nope") is False


# ---------------------------------------------------------------------------
# 7. canonical EventType emission (CONFLICT E.1 — no invented EventTypes)
# ---------------------------------------------------------------------------


async def test_record_metric_emits_metric_emitted(om, bus):
    await bus.initialize()
    await om.initialize()
    om.record_metric("requests", MetricType.COUNTER, 1.0)
    seen = await _collected(bus, {EventType.METRIC_EMITTED.name})
    assert EventType.METRIC_EMITTED.name in seen


async def test_start_span_emits_trace_span_started(om, bus):
    await bus.initialize()
    await om.initialize()
    om.start_span("op")
    seen = await _collected(bus, {EventType.TRACE_SPAN_STARTED.name})
    assert EventType.TRACE_SPAN_STARTED.name in seen


async def test_end_span_emits_trace_span_ended(om, bus):
    await bus.initialize()
    await om.initialize()
    span = om.start_span("op")
    om.end_span(span.span_id)
    seen = await _collected(bus, {EventType.TRACE_SPAN_ENDED.name})
    assert EventType.TRACE_SPAN_ENDED.name in seen


async def test_emitted_events_are_all_canonical(om, bus):
    await bus.initialize()
    await om.initialize()
    om.record_metric("m", MetricType.COUNTER, 1.0)
    span = om.start_span("s")
    om.end_span(span.span_id)
    await _tick()
    for e in bus.getRecentEvents():
        assert hasattr(e.eventType, "name"), "non-canonical EventType leaked"


async def test_event_payload_reserved_fields(om, bus):
    """EventPayload rejects reserved base-contract fields (INV-EVT-011)."""
    await bus.initialize()
    await om.initialize()
    om.record_metric("m", MetricType.COUNTER, 3.0, unit="req", labels={"l": "v"})
    await _tick()
    matched = False
    for e in bus.getRecentEvents():
        if e.eventType.name == EventType.METRIC_EMITTED.name:
            assert "timestamp" not in e.payload, "reserved field 'timestamp' leaked"
            assert e.payload.get("manager") == "ObservabilityManager"
            assert e.payload.get("manager_id") == "core.observability"
            assert e.payload.get("metric") == "m"
            assert e.payload.get("metric_type") == "COUNTER"
            assert e.payload.get("value") == 3.0
            assert e.payload.get("unit") == "req"
            assert e.payload.get("labels") == {"l": "v"}
            matched = True
    assert matched, "METRIC_EMITTED event not emitted"


# ---------------------------------------------------------------------------
# 8. no second logging system / no RuntimeWarning
# ---------------------------------------------------------------------------


def test_no_stdlib_logging_in_business_path(om):
    """ObservabilityManager does NOT create a logging system.

    It must not instantiate a stdlib ``logging.Logger``; it only records metrics
    and trace spans and surfaces them on the canonical EventBus (C4 remains the
    single authoritative structured-logging component — CONFLICT-CC-01).
    """
    import logging as _stdlib_logging

    assert not isinstance(getattr(om, "_logger", None), _stdlib_logging.Logger)
    # No stdlib logger attribute is owned by the manager.
    assert not hasattr(om, "_log") or om.__dict__.get("_log") is None


async def test_no_unawaited_coroutine_warning(om, bus):
    """record_metric/start_span/end_span must not leave un-awaited coroutines."""
    import warnings as _warnings

    await bus.initialize()
    await om.initialize()
    with _warnings.catch_warnings(record=True) as caught:
        _warnings.simplefilter("always")
        om.record_metric("m", MetricType.COUNTER, 1.0)
        span = om.start_span("s")
        om.end_span(span.span_id)
        await asyncio.sleep(0)
    for w in caught:
        msg = str(w.message).lower()
        if "coroutine" in msg and issubclass(w.category, RuntimeWarning):
            pytest.fail(f"RuntimeWarning about un-awaited coroutine: {w.message}")


# ---------------------------------------------------------------------------
# 9. errors
# ---------------------------------------------------------------------------


def test_observability_manager_error_plain():
    err = ObservabilityManagerError("boom")
    assert str(err) == "boom"
    assert err.rule_id is None
    assert err.original_error is None


def test_observability_manager_error_with_rule_id():
    err = ObservabilityManagerError("boom", rule_id="OM-INV-001")
    assert err.rule_id == "OM-INV-001"
    assert "boom" in str(err)


def test_observability_manager_error_with_original():
    inner = ValueError("inner-cause")
    err = ObservabilityManagerError("wrap", rule_id="OM-INV-002", original_error=inner)
    assert "original_error=ValueError: inner-cause" in str(err)
    assert err.original_error is inner


def test_observability_manager_error_is_exception():
    err = ObservabilityManagerError("x")
    assert isinstance(err, Exception)
    with pytest.raises(ObservabilityManagerError):
        raise err
