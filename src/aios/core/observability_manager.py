"""
ObservabilityManager — the Phase-5 (Observability) Core Manager for AI-OS Hermes Kernel.

ObservabilityManager is the observability authority for the kernel. It implements
the ICoreManager Protocol (name / phase / dependencies / initialize / shutdown /
health_ready) so LifecycleManager (Task 9) can orchestrate it deterministically:

  * initialized by LifecycleManager during Phase 5 (Observability — deterministic
    per Part 4 §4.3.4; the only manager in its phase)
  * registers with the canonical ServiceRegistry (C2) as ``core.observability``
    (Part 4 §4.11 names the identity ``kernel.observability``; see the CONFLICT
    E.1 note below for the Part-3-vs-Part-4 resolution that maps it to
    ``core.observability``, using the same precedent Task 9/10/11/12/13/14
    established for ``core.lifecycle`` / ``core.state`` / ``core.storage`` /
    ``core.health`` / ``core.resource`` / ``core.security`` /
    ``core.capability``), using the same "core_manager" metadata envelope
  * reads ``kernel.observability.*`` configuration from the frozen
    ConfigurationManager (C3)
  * logs through the StructuredLogger Core Component (C4) — the stdlib logger is
    NOT used

CONFLICT E.1 (Task 15 mapping, same as Tasks 9–14): Part 4 §4.11.11 names events
like ``MetricRegisteredEvent`` / ``AlertFiringEvent`` / ``AlertResolvedEvent`` /
``DashboardRegisteredEvent`` / ``TraceSampledEvent`` that do NOT exist in the
closed canonical ``EventType`` enum (Part 2 §2.3.1, Task 2). ObservabilityManager
does NOT invent new EventTypes. The canonical mappings for the observability
domain are (verified against ``src/aios/events/core/types.py``):

  * Metric emitted     -> EventType.METRIC_EMITTED
  * Trace span started -> EventType.TRACE_SPAN_STARTED
  * Trace span ended   -> EventType.TRACE_SPAN_ENDED

If a conceptual observability event has no canonical EventType equivalent, that
event emission is omitted rather than invented.

NOTE ON ``core.observability`` SERVICE-ID (CONFLICT E.1, Part 3 §3.4.8 vs Part 4
§4.11): Part 4 §4.11 names ObservabilityManager's ServiceRegistry identity as
``kernel.observability``, but Part 3 §3.4.8 / INV-SR-NS-002 reserve the ``kernel``
namespace ("not in ServiceRegistry"; registration throws). This is the same
Part-3-vs-Part-4 contradiction Task 9 resolved for LifecycleManager (registering
as ``core.lifecycle``) and Task 10/11/12/13/14 resolved for the other Core
Managers. Per that precedent, the compliant, INV-SR-NS-002-respecting
ServiceRegistry identity is ``core.observability``. The configuration namespace
read from C3 remains ``kernel.observability.*`` (Part 4 §4.11 config schema),
which is independent of the ServiceRegistry id. Lifecycle ownership
(initialize/shutdown driven by LifecycleManager Phase 5) is unchanged.

PHASE DEPENDENCY RULE: ObservabilityManager is Phase 5. It declares ONLY
Phase-1 LifecycleManager as a formal dependency:

    dependencies = ["LifecycleManager"]

It does NOT declare WorkflowManager, SecurityManager, or HealthManager as formal
dependencies. WorkflowManager is a Phase-4 sibling that is NOT currently
registered with LifecycleManager; declaring it (or any not-yet-present manager)
as a dependency would be rejected by LifecycleManager's dependency validator
(LM-DEP-003) and would break kernel boot. The operational relationships
(tracing correlation, security authorization, SLO health metrics) are
event-driven (via canonical EventBus), not lifecycle dependency edges. C1–C4 are
always-satisfied base dependencies handled by LifecycleManager.

NO SECOND LOGGING SYSTEM: ObservabilityManager does NOT create a logging system.
StructuredLogger (C4) remains the single authoritative structured-logging
component (Part 1 §1.8.4, CONFLICT-CC-01). This manager only governs metrics and
tracing emission and records telemetry through the canonical EventBus.
"""

from __future__ import annotations

import asyncio
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Core Components (Tasks 1–8) — consumed, never re-implemented. Imports are
# deferred to module import time (same pattern as the other Core Managers); these
# modules do not import ``aios.core.observability_manager`` at module scope, so
# there is no circular-import risk.
from aios.core.configuration_manager import ConfigurationManager
from aios.core.service_registry import ServiceRegistry, ServiceType
from aios.core.structured_logger import StructuredLogger
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion

__all__ = [
    "ObservabilityManager",
    "MetricType",
    "MetricRecord",
    "SpanRecord",
    "ObservabilityManagerError",
    "get_observability_manager",
    "set_observability_manager",
    "reset_observability_manager_singleton",
]

# ---------------------------------------------------------------------------
# Constants / identity
# ---------------------------------------------------------------------------

_NAME = "ObservabilityManager"
# Part 4 §4.11 names ObservabilityManager's ServiceRegistry identity as
# ``kernel.observability``, but Part 3 §3.4.8 / INV-SR-NS-002 reserve the
# ``kernel`` namespace ("not in ServiceRegistry"; registration throws). This is
# the same Part-3-vs-Part-4 contradiction Task 9 resolved for LifecycleManager
# (registering as ``core.lifecycle``) and Task 10/11/12/13/14 resolved for the
# other Core Managers. We follow that precedent: the compliant,
# INV-SR-NS-002-respecting ServiceRegistry id is ``core.observability``. The
# configuration namespace read from C3 remains ``kernel.observability.*`` (Part 4
# §4.11 config schema), which is unaffected by the ServiceRegistry id.
_MANAGER_ID = "core.observability"
_PHASE = 5  # Phase 5 — "Observability"
_VERSION = SemanticVersion(1, 0, 0)
_COMPONENT_DEPENDENCIES = (
    "EventBus",
    "ServiceRegistry",
    "ConfigurationManager",
    "StructuredLogger",
)
# Task 15 requirement: ``dependencies`` MUST be EXACTLY ["LifecycleManager"].
# Per the architecture review (§5.4, same as Tasks 10–14):
#   * cross-phase managers (WorkflowManager, SecurityManager, HealthManager) are
#     NOT declared as dependencies — they would be rejected by LifecycleManager's
#     dependency validator (LM-DEP-003) and could break kernel boot
#     (WorkflowManager is not currently registered with LifecycleManager).
#     Deterministic phase ordering already guarantees correct sequencing, and the
#     operational relationships (tracing correlation, authorization, SLO metrics)
#     are event-driven (via canonical EventBus), not lifecycle dependency edges.
#   * C1–C4 are always-satisfied base dependencies handled by LifecycleManager,
#     so they are not repeated here.
_MANAGER_DEPENDENCIES = ("LifecycleManager",)

# Canonical event mapping (no invented EventTypes; see CONFLICT E.1 note).
_METRIC_EMITTED = EventType.METRIC_EMITTED
_TRACE_SPAN_STARTED = EventType.TRACE_SPAN_STARTED
_TRACE_SPAN_ENDED = EventType.TRACE_SPAN_ENDED


# ---------------------------------------------------------------------------
# Enumerations / value objects
# ---------------------------------------------------------------------------


class MetricType(str, Enum):  # noqa: UP042 -- matches sibling manager enums
    """OTel-style metric types (Part 4 §4.11.2)."""

    COUNTER = "COUNTER"
    GAUGE = "GAUGE"
    HISTOGRAM = "HISTOGRAM"
    SUMMARY = "SUMMARY"


@dataclass
class MetricRecord:
    """A recorded metric (Part 4 §4.11.2)."""

    name: str
    metric_type: MetricType
    value: float
    unit: str = ""
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class SpanRecord:
    """A trace span (Part 4 §4.11.4)."""

    span_id: str
    name: str
    trace_id: str
    attributes: dict[str, Any] = field(default_factory=dict)
    parent_span_id: str | None = None


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ObservabilityManagerError(Exception):
    """ObservabilityManager failure (Part 4 §4.11.12).

    Carries optional diagnostic context: ``rule_id`` (internal
    invariant/rule identifier) and ``original_error`` (the underlying error,
    when wrapping). Mirrors ``LifecycleManagerError`` / ``StateManagerError`` /
    ``StorageManagerError`` / ``HealthManagerError`` / ``ResourceManagerError`` /
    ``SecurityManagerError`` / ``CapabilityManagerError`` (Tasks 9/10/11/12/13/14/15).
    """

    def __init__(
        self,
        message: str,
        *,
        rule_id: str | None = None,
        original_error: BaseException | None = None,
    ) -> None:
        self.rule_id = rule_id
        self.original_error = original_error
        super().__init__(message)

    def __str__(self) -> str:
        base = super().__str__()
        if self.original_error is not None:
            base += (
                f" [original_error={type(self.original_error).__name__}:"
                f" {self.original_error}]"
            )
        return base


# ---------------------------------------------------------------------------
# ObservabilityManager
# ---------------------------------------------------------------------------


class ObservabilityManager:
    """Phase-5 (Observability) telemetry authority for the Hermes Kernel.

    Provides the kernel observability surface:
    - Metric recording (Counter / Gauge / Histogram / Summary) emitting the
      canonical ``METRIC_EMITTED`` event.
    - Trace span lifecycle (start / end) emitting the canonical
      ``TRACE_SPAN_STARTED`` / ``TRACE_SPAN_ENDED`` events.
    - ICoreManager Core-Manager lifecycle (Task 15 — orchestrated by
      LifecycleManager).

    Architecture contract (mirrors the sibling Core Managers):
    - Consumes the four Core Components (C1–C4) via DI.
    - Does NOT construct its own EventBus / ServiceRegistry /
      ConfigurationManager / StructuredLogger.
    - Does NOT create a second logging system — StructuredLogger (C4) remains
      the single authoritative structured-logging component (CONFLICT-CC-01).
    - Uses only canonical EventTypes (CONFLICT E.1).
    - Lifecycle is owned by LifecycleManager (NOT routed through
      _start_services / _stop_engineering_services in the kernel).
    """

    def __init__(
        self,
        *,
        service_registry: ServiceRegistry | None = None,
        configuration_manager: ConfigurationManager | None = None,
        logger: StructuredLogger | None = None,
    ) -> None:
        """
        Initialize the Observability Manager.

        C2/C3/C4 dependencies are injected (kernel wires the canonical instances).
        C1 (EventBus) is resolved eagerly from the canonical singleton so both the
        constructor contract (raise if the bus is not up) and the sync
        ``_emit_event`` bridge keep working unchanged.
        """
        # C2/C3/C4 — injected via DI (Task 15).
        self._service_registry = service_registry
        self._configuration: ConfigurationManager | None = configuration_manager
        self._logger: StructuredLogger | None = logger

        # C1 CANONICAL EventBus singleton (INV-EB-001). Resolved eagerly.
        self._event_bus = get_core_event_bus()
        if self._event_bus is None:
            raise RuntimeError(
                "Canonical EventBus not initialized. Start the kernel first."
            )

        # Strong references for sync-path publish tasks (FIX-FIND-01).
        self._pending_tasks: set[asyncio.Future[Any]] = set()

        # Component identity for event emission (CORE_MANAGER, Part 4 §4.11).
        self._identity = ComponentIdentity(
            component_type=ComponentType.CORE_MANAGER,
            component_name=_NAME,
            version=_VERSION,
        )

        # ICoreManager lifecycle state (Task 15).
        self._initialized = False
        self._registered_with_sr = False

        # Telemetry bookkeeping.
        self._metrics: list[MetricRecord] = []
        self._spans: dict[str, SpanRecord] = {}
        self._telemetry_lock = threading.RLock()

        # Configuration consumed from the FROZEN ConfigurationManager (C3).
        self._metrics_enabled = True
        self._tracing_enabled = True
        self._default_sampling_rate = 0.01  # Part 4 §4.11.4 default ~1%

    # ------------------------------------------------------------------
    # ICoreManager surface (Task 15 / Part 4 §4.2)
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Core Manager name."""
        return _NAME

    @property
    def phase(self) -> int:
        """Lifecycle phase (Phase 5 — Observability, Part 4 §4.2.3)."""
        return _PHASE

    @property
    def dependencies(self) -> list[str]:
        """Core Manager dependencies: Phase-1 LifecycleManager + C1–C4."""
        return list(_MANAGER_DEPENDENCIES)

    @property
    def manager_id(self) -> str:
        """ServiceRegistry identity (``core.observability``; Part 4 §4.11 names
        ``kernel.observability`` — see the CONFLICT E.1 note on INV-SR-NS-002)."""
        return _MANAGER_ID

    @property
    def is_initialized(self) -> bool:
        """True once initialize() completed successfully."""
        return self._initialized

    def health_ready(self) -> bool:
        """True only when correctly initialized and wired (C1 + initialized).

        Mirrors the sibling Core Managers' health_ready: ready by construction
        once the manager has completed its own initialization. Returns False
        before ``initialize()`` and after ``shutdown()``.
        """
        return self._initialized and self._event_bus is not None

    # ------------------------------------------------------------------
    # ICoreManager: initialization / shutdown
    # ------------------------------------------------------------------

    def _read_config_str(self, path: str, default: str) -> str:
        """Read a string config value from the frozen ConfigurationManager (C3)."""
        cm = self._configuration
        if cm is None or not hasattr(cm, "get"):
            return default
        try:
            val = cm.get(path, default=default)
            return str(val) if val is not None else default
        except Exception:  # noqa: BLE001
            return default

    def _read_config_int(self, path: str, default: int) -> int:
        """Read an int config value from the frozen ConfigurationManager (C3)."""
        cm = self._configuration
        if cm is None or not hasattr(cm, "get"):
            return default
        try:
            val = cm.get(path, default=default)
            return int(val) if isinstance(val, (int, float)) else default
        except Exception:  # noqa: BLE001
            return default

    def _read_config_float(self, path: str, default: float) -> float:
        """Read a float config value from the frozen ConfigurationManager (C3)."""
        cm = self._configuration
        if cm is None or not hasattr(cm, "get"):
            return default
        try:
            val = cm.get(path, default=default)
            return float(val) if isinstance(val, (int, float)) else default
        except Exception:  # noqa: BLE001
            return default

    def _read_config_bool(self, path: str, default: bool) -> bool:
        """Read a bool config value from the frozen ConfigurationManager (C3)."""
        cm = self._configuration
        if cm is None or not hasattr(cm, "get"):
            return default
        try:
            val = cm.get(path, default=default)
            if isinstance(val, str):
                return val.strip().lower() in ("1", "true", "yes", "on")
            return bool(val)
        except Exception:  # noqa: BLE001
            return default

    async def initialize(self) -> None:
        """Phase 5 initialization (called by LifecycleManager).

        Follows the Core Manager pattern: reads ``kernel.observability.*``
        configuration from the frozen C3, registers this manager with the
        canonical ServiceRegistry (C2) as ``core.observability``, and marks the
        manager initialized/ready.

        Idempotent and lifecycle-safe: a second initialize while already
        initialized is a no-op.
        """
        if self._initialized:
            self._log_debug("initialize() called while already initialized; no-op.")
            return

        # 1. Read configuration from the FROZEN ConfigurationManager (C3).
        self._metrics_enabled = self._read_config_bool(
            "kernel.observability.metricsEnabled", self._metrics_enabled
        )
        self._tracing_enabled = self._read_config_bool(
            "kernel.observability.tracingEnabled", self._tracing_enabled
        )
        self._default_sampling_rate = self._read_config_float(
            "kernel.observability.defaultSamplingRate", self._default_sampling_rate
        )

        # 2. Register with the canonical ServiceRegistry (C2) as ``core.observability``.
        await self.register_with_service_registry()

        # 3. Mark initialized/ready.
        self._initialized = True
        self._log_info(
            f"ObservabilityManager initialized (phase {self.phase}, "
            f"manager_id={_MANAGER_ID})."
        )

    async def shutdown(self) -> None:
        """Phase 5 (reverse) shutdown (called by LifecycleManager).

        Clears telemetry bookkeeping, marks ``core.observability`` SHUTDOWN in the
        canonical ServiceRegistry (C2), and clears the initialized flag.

        Idempotent and lifecycle-safe: a second shutdown is a no-op.
        """
        if not self._initialized:
            self._log_debug("shutdown() called while not initialized; no-op.")
            return

        # 1. Clear telemetry bookkeeping.
        with self._telemetry_lock:
            self._metrics.clear()
            self._spans.clear()

        # 2. Deregister / mark SHUTDOWN in C2 (non-fatal on failure).
        await self._deregister_from_service_registry()

        # 3. Clear initialized/ready flag.
        self._initialized = False
        self._log_info("ObservabilityManager shut down.")

    # ------------------------------------------------------------------
    # ServiceRegistry integration (mirror sibling Core Manager pattern)
    # ------------------------------------------------------------------

    async def register_with_service_registry(self) -> None:
        """Register ObservabilityManager with the ServiceRegistry (C2, Part 4 §4.11).

        Registered as ``core.observability`` with the same metadata envelope
        LifecycleManager uses (``core.lifecycle``) — ``kind: core_manager`` — so
        the registration is explicitly NOT classified as an ordinary engineering
        service.
        """
        sr = self._service_registry
        if sr is None:
            self._log_warning("ServiceRegistry unavailable; not registering ObservabilityManager.")
            return
        try:
            await sr.register(
                self,
                service_id=_MANAGER_ID,
                service_type=ServiceType.ENGINEERING,
                metadata={
                    "kind": "core_manager",
                    "manager": _NAME,
                    "phase": _PHASE,
                    "lifecycle_state": "INITIALIZED",
                },
            )
            self._registered_with_sr = True
            self._log_info(f"Registered with ServiceRegistry as '{_MANAGER_ID}'.")
        except Exception as exc:  # noqa: BLE001
            self._log_warning(f"ServiceRegistry registration failed: {exc}")

    async def _deregister_from_service_registry(self) -> None:
        """Mark ``core.observability`` SHUTDOWN in the canonical ServiceRegistry (C2)."""
        sr = self._service_registry
        if sr is None:
            self._log_debug("ServiceRegistry unavailable; nothing to deregister")
            return
        try:
            await sr.mark_service_shutdown(_MANAGER_ID)
            self._registered_with_sr = False
            self._log_info(f"Marked '{_MANAGER_ID}' SHUTDOWN in ServiceRegistry.")
        except Exception as exc:  # noqa: BLE001
            self._log_warning(
                f"ServiceRegistry shutdown-mark failed for '{_MANAGER_ID}': {exc}"
            )

    # ------------------------------------------------------------------
    # Business API — metrics & tracing (no second logging system)
    # ------------------------------------------------------------------

    def record_metric(
        self,
        name: str,
        metric_type: MetricType,
        value: float,
        *,
        unit: str = "",
        labels: dict[str, str] | None = None,
    ) -> MetricRecord:
        """Record a metric (Part 4 §4.11.2) and emit METRIC_EMITTED.

        Does NOT create a logging system; it records the metric in local
        bookkeeping and surfaces it on the canonical EventBus via the
        sync-to-async bridge. Only the canonical ``EventType.METRIC_EMITTED`` is
        emitted (CONFLICT E.1 — Part 4 §4.11.11 names like ``MetricRegisteredEvent``
        have no canonical equivalent and are omitted, not invented).
        """
        record = MetricRecord(
            name=name,
            metric_type=metric_type,
            value=value,
            unit=unit,
            labels=dict(labels or {}),
        )
        with self._telemetry_lock:
            self._metrics.append(record)

        if self._metrics_enabled:
            self._emit_event(
                _METRIC_EMITTED,
                {
                    "metric": name,
                    "metric_type": metric_type.value,
                    "value": value,
                    "unit": unit,
                    "labels": record.labels,
                },
            )
        self._log_debug(f"Recorded metric: {name}={value} {unit}")
        return record

    def get_metrics(self) -> list[MetricRecord]:
        """Snapshot of recorded metrics."""
        with self._telemetry_lock:
            return list(self._metrics)

    def start_span(
        self,
        name: str,
        *,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> SpanRecord:
        """Start a trace span (Part 4 §4.11.4) and emit TRACE_SPAN_STARTED.

        Returns the created SpanRecord. Only the canonical
        ``EventType.TRACE_SPAN_STARTED`` is emitted (CONFLICT E.1 — Part 4
        §4.11.11 names like ``TraceSampledEvent`` have no canonical equivalent and
        are omitted, not invented).
        """
        span = SpanRecord(
            span_id=str(uuid.uuid4()),
            name=name,
            trace_id=trace_id or str(uuid.uuid4()),
            attributes=dict(attributes or {}),
            parent_span_id=parent_span_id,
        )
        with self._telemetry_lock:
            self._spans[span.span_id] = span

        if self._tracing_enabled:
            self._emit_event(
                _TRACE_SPAN_STARTED,
                {
                    "span_id": span.span_id,
                    "name": span.name,
                    "trace_id": span.trace_id,
                    "parent_span_id": span.parent_span_id,
                    "attributes": span.attributes,
                },
            )
        self._log_debug(f"Started span: {name} ({span.span_id})")
        return span

    def end_span(self, span_id: str) -> bool:
        """End a trace span (Part 4 §4.11.4) and emit TRACE_SPAN_ENDED.

        Returns True if the span existed and was ended. Only the canonical
        ``EventType.TRACE_SPAN_ENDED`` is emitted (CONFLICT E.1 — Part 4 §4.11.11).
        """
        with self._telemetry_lock:
            span = self._spans.pop(span_id, None)
        if span is None:
            return False
        if self._tracing_enabled:
            self._emit_event(
                _TRACE_SPAN_ENDED,
                {
                    "span_id": span.span_id,
                    "name": span.name,
                    "trace_id": span.trace_id,
                    "parent_span_id": span.parent_span_id,
                },
            )
        self._log_debug(f"Ended span: {span.name} ({span_id})")
        return True

    def get_spans(self) -> list[SpanRecord]:
        """Snapshot of currently-open spans."""
        with self._telemetry_lock:
            return list(self._spans.values())

    # ------------------------------------------------------------------
    # Event emission (canonical EventTypes only; CONFLICT E.1)
    # ------------------------------------------------------------------

    def _emit_event(self, event_type: EventType, payload: dict[str, Any]) -> None:
        """Emit a canonical observability event via the canonical EventBus.

        The canonical ``EventBus.publish`` is async (returns a coroutine). From a
        synchronous business-API call site we cannot ``await`` it, so this method
        bridges to the async bus deterministically using the architecture-approved
        sync-to-async bridge (FIX-FIND-01) established by the sibling Core
        Managers:

        * If a loop is already running, the publish coroutine is scheduled via
          ``asyncio.ensure_future`` and kept alive with a strong reference in
          ``self._pending_tasks`` (with a ``done_callback`` discarding it on
          completion).
        * If no loop is running, the emission is skipped with a StructuredLogger
          debug note — avoiding the
          ``RuntimeWarning: coroutine 'EventBus.publish' was never awaited`` and
          never leaving a coroutine un-awaited.

        Only canonical EventTypes are emitted (CONFLICT E.1: Part 4 §4.11.11 names
        like ``MetricRegisteredEvent`` / ``TraceSampledEvent`` have no canonical
        equivalent and are omitted, not invented).
        """
        bus = self._event_bus
        if bus is None:
            return

        full_payload = {
            "manager": _NAME,
            "manager_id": _MANAGER_ID,
            **payload,
        }

        event = CoreEvent(
            eventType=event_type,
            source=self._identity,
            correlationId=uuid.uuid4(),
            payload=full_payload,
        )

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self._log_debug(
                f"Event {event_type.name} not dispatched (no running event loop).",
            )
            return
        if not loop.is_running():
            self._log_debug(
                f"Event {event_type.name} not dispatched (event loop not running).",
            )
            return

        coro = bus.publish(event)
        task = asyncio.ensure_future(coro, loop=loop)
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    # ------------------------------------------------------------------
    # StructuredLogger integration (C4, Task 15 — replaces stdlib logging)
    # ------------------------------------------------------------------

    def _log_debug(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.debug(message, manager=_NAME, **fields)

    def _log_info(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.info(message, manager=_NAME, **fields)

    def _log_warning(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.warning(message, manager=_NAME, **fields)

    def _log_error(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.error(message, manager=_NAME, **fields)


# ---------------------------------------------------------------------------
# Global ObservabilityManager singleton (INV — one per process)
# ---------------------------------------------------------------------------

_global_observability_manager: ObservabilityManager | None = None
_observability_singleton_lock = threading.Lock()


def get_observability_manager() -> ObservabilityManager:
    """Get or create the global ObservabilityManager singleton.

    Uses the same lock-guarded pattern as the other Core Managers (Tasks 9–14)
    and the C1–C4 singletons, so concurrent callers cannot double-construct.
    """
    global _global_observability_manager
    with _observability_singleton_lock:
        if _global_observability_manager is None:
            _global_observability_manager = ObservabilityManager()
        return _global_observability_manager


def set_observability_manager(manager: ObservabilityManager) -> None:
    """Set the global ObservabilityManager singleton."""
    global _global_observability_manager
    with _observability_singleton_lock:
        _global_observability_manager = manager


def reset_observability_manager_singleton() -> None:
    """Reset the process-wide ObservabilityManager singleton (tests only).

    Mirrors ``reset_lifecycle_manager_singleton`` and the other Core Manager
    reset accessors / C2–C4 resets.
    """
    global _global_observability_manager
    with _observability_singleton_lock:
        _global_observability_manager = None
