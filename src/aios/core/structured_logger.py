"""
StructuredLogger — Core Component C4 (Part 3 §3.6 / Part 0 Principle 12).

The single, process-wide structured logging abstraction for AI-OS. It provides:

* Structured (canonical JSON) log emission (§3.6.3).
* Mandatory correlationId / causationId enrichment (§3.6.4).
* Seven log levels: TRACE, DEBUG, INFO, WARN, ERROR, CRITICAL, AUDIT (§3.6.5).
* Immutable, JSON-serializable log entries (INV-SL-FMT-003 / INV-SL-STR-003).
* A pluggable sink architecture (§3.6.10) with built-in ConsoleSink,
  FileSink, EventBusSink, AuditSink, NullSink.
* Tamper-evident, append-only audit logging via a dedicated AuditSink (§3.6.6).
* Performance-optimized buffering with backpressure (§3.6.7 / §3.6.8).
* Sink failure handling: retry with backoff (max 3), DEGRADED isolation,
  automatic recovery (§3.6.11 / §3.6.12).
* Execution-local correlation context (contextvars, §3.6.4).
* A bound logger (bind(...fields) -> BoundLogger).
* The ICoreComponent surface (name / phase / dependencies / initialize /
  shutdown / healthCheck) following the EventBus / ServiceRegistry /
  ConfigurationManager patterns.

No ICoreComponent ABC exists in the repository; this module implements the
established Core Component surface directly, matching the Task 5/6/7 pattern.

No new EventTypes are created (EventBus rule). StructuredLogger publishes only
``CoreComponentInitialized`` and ``CoreComponentShutdown`` from the closed enum.
"""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum, IntEnum
from typing import Any

from aios.core.sinks import (
    AuditSink,
    BaseSink,
    ConsoleSink,
    EventBusSink,
    FileSink,
    NullSink,
    RotationConfig,
    Sink,
    SinkHealth,
)
from dataclasses import dataclass
from aios.events.core.event import Event
from aios.events.core.serialization import compute_checksum
from aios.events.core.types import EventType, SemanticVersion

logger = logging.getLogger("aios.core.structured_logger")


@dataclass
class StructuredLoggerConfig:
    """Configuration for StructuredLogger (test compatibility)."""
    level: str = "INFO"
    buffer_capacity: int = 10_000
    flush_interval: float = 0.1
    max_retries: int = 3
    backoff_base: float = 0.01


# ---------------------------------------------------------------------------
# Constants (Part 3 §3.6)
# ---------------------------------------------------------------------------

_COMPONENT_NAME = "StructuredLogger"
_COMPONENT_VERSION = SemanticVersion(0, 4, 0)
_PHASE = 3
_DEPENDENCIES = ["EventBus", "ServiceRegistry", "ConfigurationManager"]

_CORE_COMPONENT_INITIALIZED = EventType.CORE_COMPONENT_INITIALIZED
_CORE_COMPONENT_SHUTDOWN = EventType.CORE_COMPONENT_SHUTDOWN

# Default minimum level per §3.6.5 (INV-SL-LVL-003): INFO production / DEBUG dev.
_DEFAULT_LEVEL = "INFO"

# Ring-buffer default capacity (§3.6.8): 10,000 entries.
_DEFAULT_BUFFER_CAPACITY = 10_000
_DEFAULT_FLUSH_INTERVAL = 0.1  # 100ms (§3.6.8)
_DEFAULT_MAX_RETRIES = 3  # §3.6.11
_DEFAULT_BACKOFF_BASE = 0.01  # 10ms base backoff


class LogLevel(IntEnum):
    """Canonical log levels (§3.6.5)."""

    TRACE = 0
    DEBUG = 1
    INFO = 2
    WARN = 3
    ERROR = 4
    CRITICAL = 5
    AUDIT = 6


# Severity ordering for filtering: AUDIT is never dropped (INV-SL-LVL-002),
# but for buffer drop-priority we treat CRITICAL/AUDIT as highest protection.
_DROP_PRIORITY: dict[LogLevel, int] = {
    LogLevel.TRACE: 0,
    LogLevel.DEBUG: 1,
    LogLevel.INFO: 2,
    LogLevel.WARN: 3,
    LogLevel.ERROR: 4,
    LogLevel.AUDIT: 6,
    LogLevel.CRITICAL: 6,
}
# Never drop these under backpressure (INV-SL-PERF-003 / INV-SL-STR-006).
_NON_DROPPABLE = frozenset({LogLevel.CRITICAL, LogLevel.AUDIT})


# ---------------------------------------------------------------------------
# LogEntry — immutable, JSON-serializable (§3.6.3 / INV-SL-FMT-001..004)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LogEntry:
    """An immutable structured log entry. Carries a SHA-256 checksum.

    ``frozen=True`` enforces immutability after construction (INV-SL-STR-003).
    All fields are JSON-serializable; circular references are prohibited
    (INV-SL-FMT-003).
    """

    timestamp: str
    timestamp_monotonic: int
    log_id: str
    level: str
    level_value: int
    category: str
    correlation_id: str | None
    causation_id: str | None
    source: str
    logger_name: str
    message: str
    fields: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None
    checksum: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialization-safe dict (no private attributes exposed)."""
        return {
            "timestamp": self.timestamp,
            "timestampMonotonic": self.timestamp_monotonic,
            "logId": self.log_id,
            "level": self.level,
            "levelValue": self.level_value,
            "category": self.category,
            "correlationId": self.correlation_id,
            "causationId": self.causation_id,
            "source": self.source,
            "loggerName": self.logger_name,
            "message": self.message,
            "fields": self.fields,
            "error": self.error,
            "checksum": self.checksum,
        }

    def to_json(self) -> str:
        """Canonical JSON serialization (RFC 8785 ordering via sort_keys)."""
        return json.dumps(self.to_dict(), default=str, sort_keys=True)

    @property
    def json_safe(self) -> bool:
        """Best-effort JSON serializability check (INV-SL-FMT-003)."""
        try:
            self.to_json()
            return True
        except (TypeError, ValueError):
            return False


# ---------------------------------------------------------------------------
# Correlation context (§3.6.4) — execution-local via contextvars
# ---------------------------------------------------------------------------

@dataclass
class CorrelationContext:
    """Execution-local correlation context (§3.6.4)."""

    correlation_id: str | None = None
    causation_id: str | None = None
    component: str | None = None


_correlation_ctx: ContextVar[CorrelationContext | None] = ContextVar(
    "aios_logger_correlation", default=None
)


def get_correlation_context() -> CorrelationContext | None:
    """Read the current correlation context (§3.6.4)."""
    return _correlation_ctx.get()


def set_correlation_context(ctx: CorrelationContext | None) -> Any:
    """Set the correlation context; returns the token for cleanup."""
    return _correlation_ctx.set(ctx)


def clear_correlation_context(token: Any | None = None) -> None:
    """Clear the correlation context (§3.6.4 INV-SL-CORR-002)."""
    if token is not None:
        _correlation_ctx.reset(token)
    else:
        _correlation_ctx.set(None)


def with_correlation(
    correlation_id: str | None,
    causation_id: str | None,
    fn: Callable[[], Any],
    component: str | None = None,
) -> Any:
    """Execute ``fn`` with a correlation context, then auto-clear (§3.6.4)."""
    ctx = CorrelationContext(
        correlation_id=correlation_id,
        causation_id=causation_id,
        component=component,
    )
    token = set_correlation_context(ctx)
    try:
        return fn()
    finally:
        clear_correlation_context(token)


# ---------------------------------------------------------------------------
# Fatal-error hook (§3.6.11 — Core Component internal error is FATAL)
# ---------------------------------------------------------------------------

FatalHandler = Callable[[str, BaseException | None], None]


def _default_fatal_handler(message: str, exc: BaseException | None) -> None:
    logger.critical("StructuredLogger FATAL: %s", message, exc_info=exc)


# ---------------------------------------------------------------------------
# StructuredLogger — Core Component C4
# ---------------------------------------------------------------------------


class StructuredLogger:
    """Core Component C4 — StructuredLogger (Part 3 §3.6)."""

    def __init__(
        self,
        name: str = _COMPONENT_NAME,
        event_bus: Any | None = None,
        service_registry: Any | None = None,
        configuration_manager: Any | None = None,
    ) -> None:
        # INV-SL-STR-001: exactly one instance per process.
        global _INSTANCE
        with _INSTANCE_LOCK:
            if _INSTANCE is not None and _INSTANCE is not self:
                raise RuntimeError(
                    "Only one StructuredLogger instance is permitted per process "
                    "(INV-SL-STR-001). A second construction is rejected."
                )
            _INSTANCE = self

        self._name = name
        self._event_bus = event_bus
        self._service_registry = service_registry
        self._configuration_manager = configuration_manager
        self._kernel: Any = None

        # Lifecycle state machine (§LIFECYCLE): UNINITIALIZED -> INITIALIZING
        # -> RUNNING -> SHUTTING_DOWN -> SHUTDOWN.
        self._state = LoggerState.UNINITIALIZED

        # Sinks (pluggable). Registered but inactive until RUNNING.
        self._sinks: list[BaseSink] = []
        self._sinks_lock = threading.RLock()
        self._audit_sink: AuditSink | None = None

        # Buffering (§3.6.8): a single queue; worker drains to sinks.
        self._buffer: queue.Queue[LogEntry] = queue.Queue(
            maxsize=_DEFAULT_BUFFER_CAPACITY
        )
        self._buffer_capacity = _DEFAULT_BUFFER_CAPACITY
        self._flush_interval = _DEFAULT_FLUSH_INTERVAL
        self._overflow_count = 0
        self._dropped_count = 0

        # Worker (background thread) drains the buffer (§3.6.7 async pipeline).
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._overflow_event = threading.Event()  # set on buffer overflow

        # Level filter (applied at frontend, INV-SL-LVL-001).
        self._min_level = LogLevel[_DEFAULT_LEVEL]

        # Monotonic sequence for timestampMonotonic.
        self._mono = 0
        self._mono_lock = threading.Lock()

        # Fatal handler (kernel may override; §3.6.11 FATAL).
        self._fatal_handler: FatalHandler = _default_fatal_handler

        self._identity = _make_logger_identity()

    # --- ICoreComponent: identity / phase / dependencies -----------------

    @property
    def name(self) -> str:
        """Core Component name (ICoreComponent)."""
        return _COMPONENT_NAME

    @property
    def phase(self) -> int:
        """Initialization phase (Part 3 §3.6: Phase 3, last Core Component)."""
        return _PHASE

    @property
    def dependencies(self) -> list[str]:
        """Core Component dependencies (§3.6 / §3.7.2)."""
        return list(_DEPENDENCIES)

    @property
    def state(self) -> LoggerState:
        """Current lifecycle state of the component itself."""
        return self._state

    @property
    def event_bus(self) -> Any | None:
        """The injected EventBus (read-only accessor)."""
        return self._event_bus

    @property
    def audit_sink(self) -> AuditSink | None:
        """The dedicated audit sink, if configured (INV-SL-AUD-002)."""
        return self._audit_sink

    @property
    def sinks(self) -> list[BaseSink]:
        """Registered sinks (read-only snapshot)."""
        with self._sinks_lock:
            return list(self._sinks)

    @property
    def overflow_count(self) -> int:
        """Total buffer overflow events (INV-SL-BUF-002)."""
        return self._overflow_count

    @property
    def dropped_count(self) -> int:
        """Total entries dropped under backpressure (INV-SL-PERF-002)."""
        return self._dropped_count

    # --- ICoreComponent: initialize --------------------------------------

    async def initialize(self, kernel: Any = None) -> LoggerState:
        """Initialize StructuredLogger (Phase 3, §3.7.3).

        Resolves dependencies via DI (constructor) or the ``kernel`` argument
        (CC-IR-002), reads logging configuration (ConfigurationManager, already
        frozen), configures sinks, prepares buffers, starts the worker, and
        publishes ``CoreComponentInitialized`` (CONF-SL-003).
        """
        if self._state in (LoggerState.INITIALIZING, LoggerState.RUNNING):
            return self._state

        self._state = LoggerState.INITIALIZING
        if self._event_bus is None and kernel is not None:
            self._event_bus = getattr(kernel, "event_bus", None)
        if self._service_registry is None and kernel is not None:
            self._service_registry = getattr(kernel, "service_registry", None)
        if self._configuration_manager is None and kernel is not None:
            self._configuration_manager = getattr(kernel, "configuration", None)
        if self._event_bus is None:
            logger.warning(
                "StructuredLogger initialized without an EventBus; log-bridge and "
                "lifecycle events will be deferred until a bus is attached."
            )
        self._kernel = kernel

        # Release unnecessary mutable reference to ConfigurationManager after
        # reading config (dependency rule: do not retain unless needed).
        self._configure_from_config()

        # Build default sinks unless the kernel provided explicit ones.
        if not self._sinks:
            self._configure_default_sinks()

        # Start worker + transition to RUNNING.
        self._start_worker()
        self._state = LoggerState.RUNNING

        await self._emit_async(
            _CORE_COMPONENT_INITIALIZED,
            {
                "name": _COMPONENT_NAME,
                "component": _COMPONENT_NAME,
                "state": "RUNNING",
            },
        )
        return self._state

    def _configure_from_config(self) -> None:
        """Read logging configuration from the (frozen) ConfigurationManager."""
        cm = self._configuration_manager
        if cm is None or not hasattr(cm, "get"):
            return
        try:
            level = cm.get("logging.level", default=_DEFAULT_LEVEL)
            if isinstance(level, str) and level.upper() in LogLevel.__members__:
                self._min_level = LogLevel[level.upper()]
            cap = cm.get("logging.bufferCapacity", default=_DEFAULT_BUFFER_CAPACITY)
            if isinstance(cap, int) and cap > 0:
                # Rebuild queue at new capacity (only valid pre-RUNNING).
                if self._state is LoggerState.INITIALIZING:
                    self._buffer_capacity = cap
        except Exception:  # noqa: BLE001
            # Configuration read failure is non-fatal for logging setup.
            pass
        finally:
            # Drop the retained CM reference per dependency rule.
            self._configuration_manager = None

    def _configure_default_sinks(self) -> None:
        """Configure built-in sinks when none are supplied (§3.6.10)."""
        # Operational sinks: console + file + eventbus (INV-SL-SNK-001).
        self.register_sink(ConsoleSink(name="console", fmt="json", level=0))
        import tempfile

        tmp_dir = tempfile.gettempdir()
        from pathlib import Path

        log_path = Path(tmp_dir) / "aios" / "logs" / "aios.log"
        self.register_sink(
            FileSink(log_path, name="file", rotation=RotationConfig(), level=0)
        )
        if self._event_bus is not None:
            self.register_sink(
                EventBusSink(self._event_bus, name="eventbus", level=LogLevel.WARN)
            )
        # Dedicated audit sink (INV-SL-SNK-002 / INV-SL-AUD-002).
        audit_path = Path(tmp_dir) / "aios" / "audit" / "audit.log"
        audit = AuditSink(audit_path, name="audit")
        self._audit_sink = audit
        self.register_sink(audit)

    # --- ICoreComponent: shutdown ----------------------------------------

    async def shutdown(self) -> LoggerState:
        """Shutdown StructuredLogger (Phase S3, first Core Component, §3.7.4).

        Stops accepting new logs, flushes buffers, closes sinks, publishes
        ``CoreComponentShutdown``, and reaches SHUTDOWN.
        """
        if self._state is LoggerState.SHUTDOWN:
            return self._state
        self._state = LoggerState.SHUTTING_DOWN

        # Stop accepting new logs (buffer putter checks state).
        self._stop_event.set()

        # Flush outstanding buffers (INV-SL-BUF-003).
        self._flush_all()
        self._stop_worker()

        # Close sinks.
        with self._sinks_lock:
            sinks_snapshot = list(self._sinks)
        for sink in sinks_snapshot:
            try:
                sink.close()
            except Exception:  # noqa: BLE001
                logger.debug("Sink %s close failed during shutdown", sink.name)

        await self._emit_async(
            _CORE_COMPONENT_SHUTDOWN,
            {
                "name": _COMPONENT_NAME,
                "component": _COMPONENT_NAME,
                "state": "SHUTDOWN",
            },
        )
        self._state = LoggerState.SHUTDOWN
        return self._state

    # --- ICoreComponent: healthCheck (sync) ------------------------------

    def healthCheck(self) -> dict[str, Any]:
        """Core Component health check (sync, mirrors EventBus pattern)."""
        with self._sinks_lock:
            total = len(self._sinks)
            degraded = sum(1 for s in self._sinks if not s.is_healthy)
        healthy = self._state in (LoggerState.RUNNING, LoggerState.INITIALIZING)
        return {
            "healthy": healthy and degraded == 0,
            "state": self._state,
            "name": _COMPONENT_NAME,
            "sinks": total,
            "sinksDegraded": degraded,
            "overflowCount": self._overflow_count,
            "droppedCount": self._dropped_count,
        }

    # --- fatal handler registration (kernel, §3.6.11) --------------------

    def set_fatal_handler(self, handler: FatalHandler) -> None:
        """Register a kernel-provided fatal-error handler (§3.6.11 FATAL)."""
        self._fatal_handler = handler

    # --- sink registration (§3.6.10 / §3.6.13) ---------------------------

    def register_sink(self, sink: BaseSink) -> None:
        """Register a sink (built-in or custom, INV-SL-SNK-004)."""
        with self._sinks_lock:
            if any(s.name == sink.name for s in self._sinks):
                raise ValueError(f"Sink '{sink.name}' is already registered")
            self._sinks.append(sink)
        # If an EventBusSink is registered and no bus bound yet, try to bind.
        if (
            isinstance(sink, EventBusSink)
            and sink.event_bus is None
            and self._event_bus is not None
        ):
            sink.set_event_bus(self._event_bus)

    def unregister_sink(self, name: str) -> None:
        """Remove a registered sink by name."""
        with self._sinks_lock:
            self._sinks = [s for s in self._sinks if s.name != name]

    # --- public logging API (§PUBLIC LOGGING API) ------------------------

    def log(self, level: LogLevel | int | str, message: str, **fields: Any) -> None:
        """Emit a structured log entry at the given level."""
        lvl = self._coerce_level(level)
        if lvl < self._min_level:
            return  # INV-SL-LVL-001: filter at frontend
        self._emit(lvl, message, fields)

    def debug(self, message: str, **fields: Any) -> None:
        self.log(LogLevel.DEBUG, message, **fields)

    def info(self, message: str, **fields: Any) -> None:
        self.log(LogLevel.INFO, message, **fields)

    def warning(self, message: str, **fields: Any) -> None:
        self.log(LogLevel.WARN, message, **fields)

    def error(self, message: str, **fields: Any) -> None:
        self.log(LogLevel.ERROR, message, **fields)

    def critical(self, message: str, **fields: Any) -> None:
        self.log(LogLevel.CRITICAL, message, **fields)

    def audit(self, message: str, **fields: Any) -> None:
        """Emit an AUDIT entry (never filtered, never dropped, §3.6.5/§3.6.6)."""
        self._emit(LogLevel.AUDIT, message, fields, category="AUDIT")

    # --- context (§3.6.4) -----------------------------------------------

    def set_context(self, correlation_id: str | None, causation_id: str | None = None) -> Any:
        """Set the correlation context; returns a reset token (INV-SL-CORR-002)."""
        return set_correlation_context(
            CorrelationContext(correlation_id=correlation_id, causation_id=causation_id)
        )

    def clear_context(self, token: Any | None = None) -> None:
        """Clear the correlation context (auto-cleanup support)."""
        clear_correlation_context(token)

    def bind(self, **fields: Any) -> BoundLogger:
        """Create a bound logger with pre-bound fields (§13)."""
        return BoundLogger(self, fields)

    # --- entry construction + buffering ----------------------------------

    def _coerce_level(self, level: LogLevel | int | str) -> LogLevel:
        if isinstance(level, LogLevel):
            return level
        if isinstance(level, int):
            try:
                return LogLevel(level)
            except ValueError:
                # Clamp to nearest valid level.
                return LogLevel(max(0, min(6, level)))
        if isinstance(level, str):
            return LogLevel[level.upper()]
        raise TypeError(f"Unsupported level type: {type(level).__name__}")

    def _build_entry(
        self,
        level: LogLevel,
        message: str,
        fields: dict[str, Any],
        category: str = "SYSTEM",
    ) -> LogEntry:
        ctx = get_correlation_context()
        corr = ctx.correlation_id if ctx else None
        caus = ctx.causation_id if ctx else None
        with self._mono_lock:
            self._mono += 1
            mono = self._mono
        entry = LogEntry(
            timestamp=datetime.now(UTC).isoformat(),
            timestamp_monotonic=mono,
            log_id=str(uuid.uuid4()),
            level=level.name,
            level_value=int(level),
            category=category,
            correlation_id=corr,
            causation_id=caus,
            source="aios",
            logger_name=_COMPONENT_NAME,
            message=message,
            fields=dict(fields),
        )
        # Checksum of canonical JSON (INV-SL-FMT-004).
        checksum = compute_checksum(entry.to_dict())
        # dataclasses frozen: build a new instance with the checksum.
        return LogEntry(
            timestamp=entry.timestamp,
            timestamp_monotonic=entry.timestamp_monotonic,
            log_id=entry.log_id,
            level=entry.level,
            level_value=entry.level_value,
            category=entry.category,
            correlation_id=entry.correlation_id,
            causation_id=entry.causation_id,
            source=entry.source,
            logger_name=entry.logger_name,
            message=entry.message,
            fields=entry.fields,
            error=entry.error,
            checksum=checksum,
        )

    def _emit(
        self,
        level: LogLevel,
        message: str,
        fields: dict[str, Any],
        category: str = "SYSTEM",
    ) -> None:
        # Stop accepting new logs during shutdown (§LIFECYCLE).
        if self._state in (LoggerState.SHUTTING_DOWN, LoggerState.SHUTDOWN):
            return
        try:
            entry = self._build_entry(level, message, fields, category)
        except Exception as exc:  # noqa: BLE001
            # Internal logger error is FATAL (INV-SL-FH-001).
            self._fatal_handler("failed to build log entry", exc)
            return

        # Backpressure: drop lowest-priority entries on a full buffer, but
        # NEVER drop CRITICAL/AUDIT (INV-SL-PERF-003 / INV-SL-STR-006).
        try:
            self._buffer.put_nowait(entry)
        except queue.Full:
            self._overflow_event.set()
            self._overflow_count += 1
            if level in _NON_DROPPABLE:
                # Reserve capacity: make room by dropping the lowest-priority
                # buffered entry, then enqueue the critical/audit entry.
                self._evict_lowest_priority()
                try:
                    self._buffer.put_nowait(entry)
                except queue.Full:
                    # Even after eviction, still full — last resort: direct drain.
                    self._drain_to_sinks([entry])
            else:
                self._dropped_count += 1

    def _evict_lowest_priority(self) -> None:
        """Drop the lowest-priority buffered entry to make room (INV-SL-PERF-002)."""
        try:
            # Drain and re-enqueue all but the lowest-priority non-protected entry.
            drained: list[LogEntry] = []
            victim_index = -1
            victim_priority = 99
            while not self._buffer.empty():
                drained.append(self._buffer.get_nowait())
            for i, e in enumerate(drained):
                if LogLevel(e.level_value) in _NON_DROPPABLE:
                    continue
                p = _DROP_PRIORITY.get(LogLevel(e.level_value), 0)
                if p < victim_priority:
                    victim_priority = p
                    victim_index = i
            for i, e in enumerate(drained):
                if i == victim_index:
                    self._dropped_count += 1
                    continue
                try:
                    self._buffer.put_nowait(e)
                except queue.Full:
                    self._dropped_count += 1
        except Exception:  # noqa: BLE001
            pass

    # --- worker (§3.6.7 async pipeline) ----------------------------------

    def _start_worker(self) -> None:
        self._stop_event.clear()
        self._worker = threading.Thread(
            target=self._worker_loop, name="StructuredLogger-worker", daemon=True
        )
        self._worker.start()

    def _stop_worker(self) -> None:
        if self._worker is not None:
            self._worker.join(timeout=self._flush_interval * 5 + 1.0)
            self._worker = None

    def _worker_loop(self) -> None:
        batch: list[LogEntry] = []
        last_flush = time.monotonic()
        while not self._stop_event.is_set() or not self._buffer.empty():
            try:
                entry = self._buffer.get(timeout=self._flush_interval)
                batch.append(entry)
            except queue.Empty:
                entry = None
            now = time.monotonic()
            if (batch and (now - last_flush) >= self._flush_interval) or (
                len(batch) >= 256
            ):
                self._drain_to_sinks(batch)
                batch = []
                last_flush = now
        # Final drain of any remaining batch.
        if batch:
            self._drain_to_sinks(batch)

    def _flush_all(self) -> None:
        """Synchronously drain all buffered entries (INV-SL-BUF-003)."""
        batch: list[LogEntry] = []
        while not self._buffer.empty():
            try:
                batch.append(self._buffer.get_nowait())
            except queue.Empty:
                break
        if batch:
            self._drain_to_sinks(batch)

    def flush(self) -> None:
        """Public flush: drain the buffer to all sinks immediately."""
        self._flush_all()

    def _drain_to_sinks(self, entries: list[LogEntry]) -> None:
        """Route entries to sinks with per-sink retry + DEGRADED isolation."""
        # Split audit entries: they go ONLY to the AuditSink (CONF-SL-006).
        audit_entries = [e for e in entries if e.level == "AUDIT"]
        operational_entries = [e for e in entries if e.level != "AUDIT"]
        with self._sinks_lock:
            sinks = list(self._sinks)
        for sink in sinks:
            if sink is self._audit_sink:
                if not audit_entries:
                    continue
                target = audit_entries
            else:
                if not operational_entries:
                    continue
                target = operational_entries
            serialized = [e.to_dict() for e in target]
            self._write_to_sink_with_retry(sink, serialized)

    def _write_to_sink_with_retry(self, sink: BaseSink, entries: list[dict[str, Any]]) -> None:
        """Write to a sink with bounded retry + backoff, DEGRADED, recovery."""
        attempts = 0
        last_exc: Exception | None = None
        while attempts < _DEFAULT_MAX_RETRIES:
            try:
                sink.write(entries)
                # Successful write clears DEGRADED (INV-SL-REC-001).
                if not sink.is_healthy:
                    sink.mark_healthy()
                return
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                attempts += 1
                if attempts < _DEFAULT_MAX_RETRIES:
                    # Backoff before retry.
                    time.sleep(_DEFAULT_BACKOFF_BASE * (2 ** (attempts - 1)))
        # Persistent failure: mark DEGRADED, continue other sinks (§3.6.11).
        sink.mark_degraded()
        sink.handle_error(last_exc or RuntimeError("sink write failed"))

    # --- event emission (CORE_COMPONENT_INITIALIZED / SHUTDOWN) ----------

    def _make_event(self, event_type: EventType, payload: dict[str, Any]) -> Event:
        """Build a canonical Event for the canonical EventBus (C1, Task 5)."""
        import uuid
        return Event(
            eventType=event_type,
            source=self._identity,
            correlationId=uuid.uuid4(),
            payload=payload,
        )

    async def _emit_async(self, event_type: EventType, payload: dict[str, Any]) -> None:
        """Emit a canonical event via the canonical EventBus."""
        bus = self._event_bus
        if bus is None:
            return
        try:
            event = self._make_event(event_type, payload)
            result = bus.publish(event)
            if hasattr(result, "__await__"):
                await result
        except Exception as exc:  # noqa: BLE001
            logger.debug("Event emission of %s failed: %s", event_type.name, exc)


# ---------------------------------------------------------------------------
# Logger lifecycle state (§LIFECYCLE)
# ---------------------------------------------------------------------------


class LoggerState(str, Enum):
    """Lifecycle states for StructuredLogger (UNINITIALIZED→...→SHUTDOWN)."""

    UNINITIALIZED = "UNINITIALIZED"
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    SHUTDOWN = "SHUTDOWN"


# ---------------------------------------------------------------------------
# BoundLogger (§13)
# ---------------------------------------------------------------------------


class BoundLogger:
    """A logger with pre-bound structured fields (§13)."""

    def __init__(self, logger: StructuredLogger, fields: dict[str, Any]) -> None:
        self._logger = logger
        self._fields = dict(fields)

    def bind(self, **fields: Any) -> BoundLogger:
        """Further bind additional fields (returns a new BoundLogger)."""
        merged = dict(self._fields)
        merged.update(fields)
        return BoundLogger(self._logger, merged)

    def _emit(self, level: LogLevel | int | str, message: str, **fields: Any) -> None:
        merged = dict(self._fields)
        merged.update(fields)
        self._logger.log(level, message, **merged)

    def debug(self, message: str, **fields: Any) -> None:
        self._emit(LogLevel.DEBUG, message, **fields)

    def info(self, message: str, **fields: Any) -> None:
        self._emit(LogLevel.INFO, message, **fields)

    def warning(self, message: str, **fields: Any) -> None:
        self._emit(LogLevel.WARN, message, **fields)

    def error(self, message: str, **fields: Any) -> None:
        self._emit(LogLevel.ERROR, message, **fields)

    def critical(self, message: str, **fields: Any) -> None:
        self._emit(LogLevel.CRITICAL, message, **fields)

    def audit(self, message: str, **fields: Any) -> None:
        merged = dict(self._fields)
        merged.update(fields)
        self._logger.audit(message, **merged)


# ---------------------------------------------------------------------------
# Legacy aliases (preserve the pre-existing public contract from logger.py)
# ---------------------------------------------------------------------------


class LogContext:
    """Backwards-compatible correlation context holder (legacy alias)."""

    def __init__(
        self,
        correlation_id: str | None = None,
        service: str = "unknown",
        operation: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.correlation_id = correlation_id
        self.service = service
        self.operation = operation
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "service": self.service,
            "operation": self.operation,
            **self.metadata,
        }


class JsonFormatter(logging.Formatter):
    """JSON formatter for stdlib logging compatibility (legacy alias)."""

    def format(self, record: logging.LogRecord) -> str:
        import json as _json

        log_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName", "relativeCreated",
                "thread", "threadName", "exc_info", "exc_text", "stack_info",
            }:
                log_data[key] = value
        return _json.dumps(log_data, default=str)


# ---------------------------------------------------------------------------
# Singleton accessor (kernel-owned construction)
# ---------------------------------------------------------------------------


_INSTANCE: StructuredLogger | None = None
_INSTANCE_LOCK = threading.RLock()


def get_logger(name: str = _COMPONENT_NAME) -> StructuredLogger:
    """Get (or create) the global StructuredLogger singleton.

    The kernel owns construction; this accessor returns the kernel-owned
    instance when one exists, otherwise constructs a default singleton. Tests
    should prefer explicit construction + ``set_logger`` for isolation.
    """
    global _INSTANCE
    if _INSTANCE is None:
        with _INSTANCE_LOCK:
            if _INSTANCE is None:
                _INSTANCE = StructuredLogger(name)
    return _INSTANCE


def set_logger(logger_instance: StructuredLogger) -> None:
    """Set the global StructuredLogger singleton (kernel-owned construction)."""
    global _INSTANCE
    with _INSTANCE_LOCK:
        _INSTANCE = logger_instance


# Alias for test compatibility
set_structured_logger = set_logger
get_structured_logger = get_logger


def reset_structured_logger_singleton() -> None:
    """Reset the process-wide StructuredLogger singleton (tests only)."""
    global _INSTANCE
    with _INSTANCE_LOCK:
        _INSTANCE = None


# ---------------------------------------------------------------------------
# Component identity helper
# ---------------------------------------------------------------------------


def _make_logger_identity() -> Any:
    from aios.events.core.identity import ComponentIdentity, ComponentType

    return ComponentIdentity(
        component_type=ComponentType.CORE_COMPONENT,
        component_name=_COMPONENT_NAME,
        version=_COMPONENT_VERSION,
    )


__all__ = [
    "StructuredLogger",
    "StructuredLoggerConfig",
    "BoundLogger",
    "LogContext",
    "LogEntry",
    "JsonFormatter",
    "LogLevel",
    "LoggerState",
    "CorrelationContext",
    "get_logger",
    "get_structured_logger",
    "set_logger",
    "set_structured_logger",
    "reset_structured_logger_singleton",
    "get_correlation_context",
    "set_correlation_context",
    "clear_correlation_context",
    "with_correlation",
    # Re-exported sinks for convenience.
    "ConsoleSink",
    "FileSink",
    "EventBusSink",
    "AuditSink",
    "NullSink",
    "Sink",
    "SinkHealth",
    "RotationConfig",
]
