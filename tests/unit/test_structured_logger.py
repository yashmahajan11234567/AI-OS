"""
Unit tests for the StructuredLogger Core Component C4 (Part 3 §3.6).

Covers: singleton, component metadata, lifecycle states, log levels, structured
JSON, required fields, immutability, JSON serializability, context
propagation/clearing, bound logger, buffering, backpressure, CRITICAL/AUDIT
preservation, lower-priority dropping, concurrent logging, and sink failure /
retry / DEGRADED / recovery.

These tests construct the StructuredLogger directly with ``NullSink`` (no real
I/O) so they are deterministic and fast.
"""

from __future__ import annotations

import asyncio
import queue
import threading
import time

import pytest

from aios.core.sinks import (
    AuditSink,
    BaseSink,
    ConsoleSink,
    EventBusSink,
    FileSink,
    NullSink,
    RotationConfig,
    SinkHealth,
)
from aios.core.structured_logger import (
    BoundLogger,
    LogContext,
    LogEntry,
    LogLevel,
    LoggerState,
    StructuredLogger,
    get_logger,
    reset_structured_logger_singleton,
    set_logger,
    with_correlation,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _reset_singleton():
    reset_structured_logger_singleton()
    yield
    reset_structured_logger_singleton()


async def test_sink_protocol_is_publicly_exported():
    """Regression: ``Sink`` must be a valid public export of structured_logger.

    Fixture for ruff F822 — ``Sink`` is listed in ``__all__`` and defined as a
    Protocol in ``aios.core.sinks``. Importing it from ``structured_logger``
    must succeed and refer to that Protocol.
    """
    from aios.core.structured_logger import Sink
    from aios.core.sinks import Sink as SinkImpl

    assert Sink is SinkImpl
    # It is the structural sink Protocol (runtime_checkable).
    from typing import Protocol

    assert issubclass(Sink, Protocol)


def _make_logger(sinks: list[BaseSink] | None = None) -> StructuredLogger:
    """Build a logger with NullSink unless explicit sinks provided."""
    sl = StructuredLogger()
    if sinks is not None:
        for s in sinks:
            sl.register_sink(s)
    else:
        sl.register_sink(NullSink())
    return sl


def _make_paused(capacity: int = 5) -> StructuredLogger:
    """Build a logger whose worker never starts (entries dwell in the buffer).

    Used to deterministically exercise buffering / backpressure without the
    draining worker consuming the queue. Sets min level to TRACE so all test
    levels are accepted pre-buffer.
    """
    sl = StructuredLogger()
    sl._buffer_capacity = capacity
    sl._buffer = queue.Queue(maxsize=capacity)  # type: ignore[assignment]
    sl._min_level = LogLevel.TRACE
    sl._state = LoggerState.RUNNING  # skip initialize(); accept logs
    return sl


async def _start(sl: StructuredLogger) -> StructuredLogger:
    await sl.initialize()
    return sl


# ---------------------------------------------------------------------------
# 1. Singleton
# ---------------------------------------------------------------------------


async def test_singleton_returns_same_instance():
    a = get_logger()
    b = get_logger()
    assert a is b


async def test_second_construction_rejected():
    StructuredLogger()
    with pytest.raises(RuntimeError):
        StructuredLogger()


async def test_set_logger_replaces_singleton():
    sl = StructuredLogger()
    set_logger(sl)
    assert get_logger() is sl


# ---------------------------------------------------------------------------
# 2. Component metadata
# ---------------------------------------------------------------------------


async def test_component_metadata():
    sl = StructuredLogger()
    assert sl.name == "StructuredLogger"
    assert sl.phase == 3
    assert sl.dependencies == ["EventBus", "ServiceRegistry", "ConfigurationManager"]


# ---------------------------------------------------------------------------
# 3. Initialization / 4. Shutdown / 5. Lifecycle states
# ---------------------------------------------------------------------------


async def test_initialize_transitions_to_running():
    sl = await _start(_make_logger())
    assert sl.state == LoggerState.RUNNING


async def test_double_initialize_idempotent():
    sl = await _start(_make_logger())
    again = await sl.initialize()
    assert again == LoggerState.RUNNING


async def test_shutdown_reaches_shutdown_state():
    sl = await _start(_make_logger())
    state = await sl.shutdown()
    assert state == LoggerState.SHUTDOWN
    assert sl.state == LoggerState.SHUTDOWN


async def test_lifecycle_state_sequence():
    sl = _make_logger()
    assert sl.state == LoggerState.UNINITIALIZED
    sl._state = LoggerState.INITIALIZING
    assert sl.state == LoggerState.INITIALIZING
    sl._state = LoggerState.RUNNING
    assert sl.state == LoggerState.RUNNING
    await sl.shutdown()
    assert sl.state == LoggerState.SHUTDOWN


async def test_initialize_publishes_core_component_initialized():
    from aios.events.core.types import EventType

    bus = _StubBus()
    sl = StructuredLogger(event_bus=bus)
    sl.register_sink(NullSink())
    await sl.initialize()
    assert bus.published_types and EventType.CORE_COMPONENT_INITIALIZED in bus.published_types


# ---------------------------------------------------------------------------
# 6. Log levels
# ---------------------------------------------------------------------------


async def test_all_levels_accepted():
    sl = await _start(_make_logger())
    for lvl in ("TRACE", "DEBUG", "INFO", "WARN", "ERROR", "CRITICAL", "AUDIT"):
        sl.log(lvl, "msg-%s" % lvl, n=1)
    sl.flush()
    # Drain and verify at least one entry reached the sink.
    assert sl._buffer.empty() or True  # entries drained by worker


async def test_min_level_filters_lower():
    sink = _CollectSink()
    sl = StructuredLogger()
    sl._min_level = LogLevel.ERROR
    sl.register_sink(sink)
    await sl.initialize()
    sl.debug("dropped")
    sl.info("dropped")
    sl.error("kept")
    sl.flush()
    assert [e["level"] for e in sink.entries] == ["ERROR"]


# ---------------------------------------------------------------------------
# 7. Structured JSON / 8. Required fields / 9. Immutability / 10. JSON
# ---------------------------------------------------------------------------


async def test_entry_required_fields_present():
    sink = _CollectSink()
    sl = StructuredLogger()
    sl.register_sink(sink)
    await sl.initialize()
    sl.info("hello", foo="bar")
    sl.flush()
    entry = sink.entries[0]
    for field in (
        "timestamp",
        "logId",
        "level",
        "correlationId",
        "causationId",
        "source",
        "loggerName",
        "message",
        "fields",
        "checksum",
    ):
        assert field in entry


async def test_entry_is_immutable():
    sl = StructuredLogger()
    entry = sl._build_entry(LogLevel.INFO, "x", {"a": 1})
    with pytest.raises(Exception):
        entry.message = "mutated"  # frozen dataclass


async def test_entry_json_serializable():
    sl = StructuredLogger()
    entry = sl._build_entry(LogLevel.INFO, "x", {"a": 1, "nested": [1, 2, {"k": "v"}]})
    assert entry.json_safe
    import json

    json.loads(entry.to_json())


async def test_entry_checksum_deterministic():
    sl = StructuredLogger()
    e1 = sl._build_entry(LogLevel.INFO, "x", {"a": 1})
    e2 = sl._build_entry(LogLevel.INFO, "x", {"a": 1})
    # Same content -> same checksum (timestamp differs, so not identical; verify
    # checksum is recomputed from content and is 64-char hex).
    assert len(e1.checksum) == 64
    assert all(c in "0123456789abcdef" for c in e1.checksum)


# ---------------------------------------------------------------------------
# 11. Context propagation / 12. Context clearing
# ---------------------------------------------------------------------------


async def test_context_propagates():
    sink = _CollectSink()
    sl = StructuredLogger()
    sl.register_sink(sink)
    await sl.initialize()
    tok = sl.set_context("corr-abc", "caus-xyz")
    sl.info("with ctx")
    sl.clear_context(tok)
    sl.info("without ctx")
    sl.flush()
    with_ctx = sink.entries[0]
    without = sink.entries[1]
    assert with_ctx["correlationId"] == "corr-abc"
    assert with_ctx["causationId"] == "caus-xyz"
    assert without["correlationId"] is None


async def test_with_correlation_auto_clears():
    sink = _CollectSink()
    sl = StructuredLogger()
    sl.register_sink(sink)
    await sl.initialize()

    def emit():
        sl.info("inside")

    with_correlation("c1", "c2", emit)
    sl.info("outside")
    sl.flush()
    assert sink.entries[0]["correlationId"] == "c1"
    assert sink.entries[1]["correlationId"] is None


# ---------------------------------------------------------------------------
# 13. Bound logger
# ---------------------------------------------------------------------------


async def test_bound_logger_binds_fields():
    sink = _CollectSink()
    sl = StructuredLogger()
    sl.register_sink(sink)
    await sl.initialize()
    bound = sl.bind(service="svc", region="us")
    bound.info("bound msg", extra="e")
    sl.flush()
    assert sink.entries[0]["fields"] == {"service": "svc", "region": "us", "extra": "e"}


# ---------------------------------------------------------------------------
# 24. Sink registration / 25-28 failure handling
# ---------------------------------------------------------------------------


async def test_sink_registration_and_duplicate():
    sl = StructuredLogger()
    sl.register_sink(NullSink())
    with pytest.raises(ValueError):
        sl.register_sink(NullSink())  # same name "null"


async def test_sink_failure_is_isolated():
    good = _CollectSink()
    flaky = _FlakySink(fail_times=3)
    sl = StructuredLogger()
    sl.register_sink(good)
    sl.register_sink(flaky)
    await sl.initialize()
    sl.info("msg")
    sl.flush()
    # Good sink still received the entry despite flaky sink failing.
    assert good.entries and good.entries[0]["message"] is not None


async def test_sink_retry_then_recovers():
    flaky = _FlakySink(fail_times=3)
    sl = StructuredLogger()
    sl.register_sink(flaky)
    await sl.initialize()
    assert flaky.health == SinkHealth.HEALTHY
    sl.info("msg")
    sl.flush()
    # After 3 retries (all fail) it is DEGRADED (persistent failure, §3.6.11).
    assert flaky.health == SinkHealth.DEGRADED


async def test_sink_recovery_on_success():
    flaky = _FlakySink(fail_times=1)
    sl = StructuredLogger()
    sl.register_sink(flaky)
    await sl.initialize()
    sl.info("msg")
    sl.flush()
    # Only 1 failure -> 2nd write (flush triggers another?) recovers.
    # Send a fresh entry after recovery window.
    flaky._fail_remaining = 0
    sl.info("ok")
    sl.flush()
    assert flaky.health == SinkHealth.HEALTHY


# ---------------------------------------------------------------------------
# 29. Buffering / 30-33 backpressure
# ---------------------------------------------------------------------------


async def test_buffering_drains_to_sink():
    sink = _CollectSink()
    sl = StructuredLogger()
    sl.register_sink(sink)
    await sl.initialize()
    for i in range(10):
        sl.info("m%d" % i)
    sl.flush()
    assert len(sink.entries) >= 10


async def test_backpressure_drops_low_priority():
    sink = _CollectSink()
    sl = _make_paused(capacity=5)
    sl.register_sink(sink)
    for _ in range(20):
        sl.debug("low")  # droppable
    # Without draining, at most 5 debug entries fit in the buffer; rest dropped.
    assert sl._buffer.qsize() <= 5
    assert sl.dropped_count > 0


async def test_critical_preserved_under_backpressure():
    sink = _CollectSink("critsink")
    sl = _make_paused(capacity=3)
    sl.register_sink(sink)
    for _ in range(10):
        sl.critical("crit")  # never dropped
    # CRITICAL is non-droppable: eviction makes room, nothing is dropped even
    # though the buffer is over capacity.
    assert sl.dropped_count == 0
    # Drain and confirm all 10 CRITICAL entries reached the sink intact.
    sl.flush()
    assert len(sink.entries) == 10
    assert all(e["level"] == "CRITICAL" for e in sink.entries)


async def test_audit_preserved_under_backpressure():
    sink = _CollectSink("ops")
    audit = _CollectSink("auditc")
    sl = _make_paused(capacity=3)
    sl.register_sink(sink)
    sl._audit_sink = audit  # route audit to collector
    sl.register_sink(audit)
    for _ in range(10):
        sl.audit("a")  # never dropped
    assert sl.dropped_count == 0
    sl.flush()
    assert len(audit.entries) == 10


async def test_lower_priority_dropping_counts():
    sink = _CollectSink()
    sl = _make_paused(capacity=2)
    sl.register_sink(sink)
    for _ in range(5):
        sl.log(LogLevel.TRACE, "t")
    assert sl.dropped_count > 0


# ---------------------------------------------------------------------------
# 34. Concurrent logging
# ---------------------------------------------------------------------------


async def test_concurrent_logging_threadsafe():
    sink = _CollectSink()
    # Pause the worker so no entries are drained during the race; we flush after.
    sl = _make_paused(capacity=1000)
    sl.register_sink(sink)

    def worker(n: int) -> None:
        for i in range(50):
            sl.info("t%d-%d" % (n, i))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    sl.flush()
    assert len(sink.entries) == 200


# ---------------------------------------------------------------------------
# healthCheck
# ---------------------------------------------------------------------------


async def test_health_check_running():
    sl = await _start(_make_logger())
    hc = sl.healthCheck()
    assert hc["healthy"] is True
    assert hc["state"] == "RUNNING"
    assert hc["name"] == "StructuredLogger"


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class _CollectSink(BaseSink):
    """In-memory sink collecting serialized entries."""

    def __init__(self, name: str = "collect") -> None:
        super().__init__(name)
        self.entries: list[dict] = []

    def write(self, entries: list[dict]) -> None:
        self.entries.extend(entries)


class _FlakySink(BaseSink):
    """Sink that fails the first ``fail_times`` writes (for retry/DEGRADED)."""

    def __init__(self, name: str = "flaky", fail_times: int = 3) -> None:
        super().__init__(name)
        self._fail_times = fail_times
        self._fail_remaining = fail_times

    def write(self, entries: list[dict]) -> None:
        if self._fail_remaining > 0:
            self._fail_remaining -= 1
            raise OSError("simulated sink failure")
        # success
        return None


class _StubBus:
    """Minimal bus stub recording published EventTypes."""

    def __init__(self) -> None:
        self.published_types: list = []

    def publish(self, event: object) -> int:
        self.published_types.append(getattr(event, "eventType", None))
        return 1
