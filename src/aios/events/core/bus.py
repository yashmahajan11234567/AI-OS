"""
EventBus — the orchestration layer (Part 2 §2.4 / Task 5).

The EventBus owns *publication*, *priority queues*, *dispatch*, *handler
execution*, *concurrency limits*, *retry scheduling*, *DLQ*, *lifecycle*,
*event history*, *replay*, *diagnostics*, *metrics*, *recursive-depth
protection*, and *backpressure*. It does NOT own subscription state, EventType
registry, schema/validation, Event immutability, or UUID generation — those are
delegated to the existing Task 1–4 components.

Design:

  * Async-native. ``publish`` / ``publishBatch`` / ``drain`` / ``initialize`` /
    ``shutdown`` are coroutines. Subscription bookkeeping (``subscribe`` /
    ``unsubscribe`` / lookups) delegates synchronously to ``SubscriptionManager``
    (which owns an RLock); this is safe because the GIL serializes access and the
    bus never mutates subscription state itself.
  * ``publish`` ONLY enqueues (INV-EB-012). Actual handler execution happens in
    ``drain`` / the background dispatch worker. ``publish`` therefore never
    invokes a subscriber handler synchronously.
  * Dispatch is deterministic. Tests pass ``auto_start_dispatch_worker=False``
    in their config and call ``await bus.drain()`` to process exactly the events
    currently queued. A production deployment sets ``auto_start_dispatch_worker``
    to run a continuously-scheduled worker task.

Import restriction (INV-EB-002): this module imports ONLY the Python standard
library and ``aios.events.core.*``. It never imports ``aios.core.*``,
``aios.managers.*``, ``aios.observability.*``, or Hermes.

No new exception/error classes are introduced; the existing
``EventRegistryError`` (preferred for lifecycle/registry/singleton violations)
and ``EventValidationError`` are reused.
"""

from __future__ import annotations

import asyncio
import enum
import heapq
import threading
import time
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from aios.events.core.errors import EventRegistryError
from aios.events.core.event import Event
from aios.events.core.filters import is_async_filter
from aios.events.core.manager import SubscribeOptions, SubscriptionManager
from aios.events.core.priority import EventPriority
from aios.events.core.registry import EventTypeRegistry
from aios.events.core.serialization import compute_checksum
from aios.events.core.subscription import (
    WILDCARD_PRIORITY,
    HandlerPriority,
    RetryPolicy,
    Subscription,
)
from aios.events.core.types import EventType

__all__ = [
    "EventBus",
    "EventBusState",
    "PublishStatus",
    "PublishResult",
    "PublishOptions",
    "EventBusConfig",
    "EventBusDiagnostics",
    "EventBusMetrics",
    "DeadLetterEntry",
    "DeadLetterFilter",
    "ReplayOptions",
    "UnsubscribeOptions",
    "EventBusHealth",
]


# ---------------------------------------------------------------------------
# Enumerations / public status types
# ---------------------------------------------------------------------------


class EventBusState(enum.StrEnum):
    """EventBus lifecycle (Part 2 §2.4 / Task 5 INV-EB-*)."""

    UNINITIALIZED = "UNINITIALIZED"
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    DRAINING = "DRAINING"
    SHUTDOWN = "SHUTDOWN"


class PublishStatus(enum.StrEnum):
    """Exactly the five required publish outcomes (Task 5 Phase 4)."""

    ACCEPTED = "ACCEPTED"
    REJECTED_VALIDATION = "REJECTED_VALIDATION"
    REJECTED_CAPACITY = "REJECTED_CAPACITY"
    REJECTED_SHUTDOWN = "REJECTED_SHUTDOWN"
    REJECTED_DUPLICATE = "REJECTED_DUPLICATE"


# Priority lanes, highest-first. Index in this list == dispatch precedence.
_PRIORITY_LANES: tuple[EventPriority, ...] = (
    EventPriority.CRITICAL,
    EventPriority.HIGH,
    EventPriority.NORMAL,
    EventPriority.LOW,
    EventPriority.BACKGROUND,
)
_LANE_INDEX = {p: i for i, p in enumerate(_PRIORITY_LANES)}


@dataclass(frozen=True)
class PublishOptions:
    """Options for a single publish call (Task 5 Phase 4)."""

    blocking: bool = False
    timeoutMs: int | None = None
    idempotencyKey: str | None = None
    waitForAck: bool = False


@dataclass(frozen=True)
class PublishResult:
    """Frozen structured publish result (Task 5 Phase 4)."""

    status: PublishStatus
    eventId: uuid.UUID | None = None
    message: str = ""

    @property
    def accepted(self) -> bool:
        return self.status is PublishStatus.ACCEPTED


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EventBusConfig:
    """Minimal EventBus configuration (Task 5 Phase 25).

    Every field maps to an architecture requirement; nothing invented.
    ``auto_start_dispatch_worker`` is False by default so unit tests can drive
    dispatch deterministically via ``await bus.drain()``; production callers set
    it True.
    """

    publishQueueCapacity: int = 10000
    retryQueueCapacity: int = 1000
    dlqCapacity: int = 1000
    handlerTimeoutMs: int = 30000
    dispatchCycleTimeoutMs: int = 1000
    shutdownDrainTimeoutMs: int = 30000
    maxDispatchDepth: int = 16
    loopDetectionWindow: int = 1000
    maxEventsPerCyclePerLane: int = 1000
    historyCapacity: int = 10000
    auto_start_dispatch_worker: bool = False

    def __post_init__(self) -> None:
        if self.publishQueueCapacity <= 0:
            raise EventRegistryError("publishQueueCapacity MUST be > 0.")
        if self.retryQueueCapacity <= 0:
            raise EventRegistryError("retryQueueCapacity MUST be > 0.")
        if self.dlqCapacity <= 0:
            raise EventRegistryError("dlqCapacity MUST be > 0.")
        if self.maxDispatchDepth < 1:
            raise EventRegistryError("maxDispatchDepth MUST be >= 1.")
        if self.handlerTimeoutMs < 0:
            raise EventRegistryError("handlerTimeoutMs MUST be >= 0.")
        if self.historyCapacity < 0:
            raise EventRegistryError("historyCapacity MUST be >= 0.")


# ---------------------------------------------------------------------------
# Dead-letter + replay
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeadLetterEntry:
    """A dead-lettered failed dispatch (Task 5 Phase 18)."""

    entryId: str
    event: Event
    subscriptionId: uuid.UUID
    reason: str
    classification: str  # TRANSIENT | TIMEOUT | UNAVAILABLE | NON_RETRYABLE
    attempt: int
    createdAt: str  # ISO8601 UTC
    createdAtMonotonic: int  # process-local ns for purge comparisons
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DeadLetterFilter:
    """Optional filter for ``getDeadLetters`` (Task 5 Phase 18)."""

    subscriptionId: uuid.UUID | None = None
    classification: str | None = None
    eventType: EventType | None = None
    limit: int | None = None


@dataclass(frozen=True)
class ReplayOptions:
    """Options for the v1.0 memory-only replay API (Task 5 Phase 21)."""

    eventType: EventType | None = None
    correlationId: uuid.UUID | None = None
    sinceEventId: uuid.UUID | None = None
    limit: int | None = None
    dryRun: bool = False
    newEventIds: bool = True


@dataclass(frozen=True)
class UnsubscribeOptions:
    """Unsubscribe criteria (Task 5 Phase 8) — mirrors manager.unsubscribe.

    Delegates to ``SubscriptionManager.unsubscribe``; does NOT recreate the
    subscription/deduplication logic.
    """

    subscriptionId: uuid.UUID | None = None
    eventTypes: tuple[EventType, ...] | None = None
    all_: bool = False
    immediate: bool = False


# ---------------------------------------------------------------------------
# Metrics / diagnostics / health
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EventBusMetrics:
    """Internal counters exposed via ``getMetrics`` (Task 5 Phase 24)."""

    published: int = 0
    dispatched: int = 0
    delivered: int = 0
    retries: int = 0
    dlq: int = 0
    validation_failures: int = 0
    queue_overflows: int = 0
    recursive_events: int = 0
    last_handler_duration_ms: float = 0.0
    dispatch_cycle_latency_ms: float = 0.0
    active_subscriptions: int = 0
    queued_events: int = 0
    dlq_size: int = 0
    retry_queue_size: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "published": self.published,
            "dispatched": self.dispatched,
            "delivered": self.delivered,
            "retries": self.retries,
            "dlq": self.dlq,
            "validation_failures": self.validation_failures,
            "queue_overflows": self.queue_overflows,
            "recursive_events": self.recursive_events,
            "last_handler_duration_ms": self.last_handler_duration_ms,
            "dispatch_cycle_latency_ms": self.dispatch_cycle_latency_ms,
            "active_subscriptions": self.active_subscriptions,
            "queued_events": self.queued_events,
            "dlq_size": self.dlq_size,
            "retry_queue_size": self.retry_queue_size,
        }


@dataclass(frozen=True)
class EventBusDiagnostics:
    """Diagnostic snapshot exposed via ``getDiagnostics`` (Task 5 Phase 24)."""

    state: EventBusState
    config: EventBusConfig
    queue_depths: dict[str, int]
    subscription_count: int
    dlq_size: int
    retry_queue_size: int
    metrics: EventBusMetrics

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "queue_depths": dict(self.queue_depths),
            "subscription_count": self.subscription_count,
            "dlq_size": self.dlq_size,
            "retry_queue_size": self.retry_queue_size,
            "metrics": self.metrics.to_dict(),
        }


@dataclass(frozen=True)
class EventBusHealth:
    """Health check result (Task 5 Phase 24)."""

    healthy: bool
    state: EventBusState
    queued_events: int
    dlq_size: int
    active_subscriptions: int
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "healthy": self.healthy,
            "state": self.state.value,
            "queued_events": self.queued_events,
            "dlq_size": self.dlq_size,
            "active_subscriptions": self.active_subscriptions,
            "details": self.details,
        }


# ---------------------------------------------------------------------------
# Singleton guard (INV-EB-001)
# ---------------------------------------------------------------------------

# Module-level singleton reference. A second construction raises
# EventRegistryError (the established registry/lifecycle error class) unless the
# singleton has been reset (tests reset it; production must not construct twice).
_INSTANCE: EventBus | None = None
_INSTANCE_LOCK = threading.Lock()


def reset_event_bus_singleton() -> None:
    """Reset the process-wide EventBus singleton.

    Provided so unit tests can construct a fresh bus per test. Production code
    MUST NOT call this; the singleton is meant to be created exactly once per
    process (INV-EB-001).
    """
    global _INSTANCE
    with _INSTANCE_LOCK:
        _INSTANCE = None


# ---------------------------------------------------------------------------
# EventBus
# ---------------------------------------------------------------------------


class EventBus:
    """The AI-OS EventBus orchestration layer (Part 2 §2.4, Task 5)."""

    def __init__(
        self,
        config: EventBusConfig | None = None,
        registry: EventTypeRegistry | None = None,
        diagnostic_hook: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        global _INSTANCE
        with _INSTANCE_LOCK:
            if _INSTANCE is not None and _INSTANCE is not self:
                raise EventRegistryError(
                    "Only one EventBus instance is permitted per process "
                    "(INV-EB-001). A second construction is rejected."
                )
            _INSTANCE = self

        self._config = config or EventBusConfig()
        self._registry = registry or EventTypeRegistry()
        self._subscriptions = SubscriptionManager(self._registry)
        self._diagnostic_hook = diagnostic_hook

        # Lifecycle
        self._state = EventBusState.UNINITIALIZED
        self._lock = threading.RLock()

        # Per-lane bounded FIFO queues (highest priority index 0).
        self._lanes: list[deque] = [deque() for _ in _PRIORITY_LANES]
        # Retry queue: heap of (due_monotonic_ns, attempt, subscriptionId, Event).
        self._retry_heap: list[tuple[int, int, uuid.UUID, Event]] = []
        # Dead-letter queue (bounded; manual DROP_OLDEST).
        self._dlq: deque = deque()
        # Bounded in-memory history ring buffer.
        self._history: deque[Event] = deque()
        # Idempotency keys currently seen.
        self._seen_keys: set[str] = set()
        # Dispatch depth per correlationId (recursion protection).
        self._dispatch_depth: dict[uuid.UUID, int] = {}

        # Async coordination. Conditions are bound to a loop, so they are created
        # lazily in initialize() (which runs inside a running loop). Until then
        # they are None; publish requires RUNNING (post-initialize) so they are
        # always available when used.
        self._space_cv: asyncio.Condition | None = None
        self._not_empty_cv: asyncio.Condition | None = None
        self._worker_task: asyncio.Task | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        # Per-subscription concurrency semaphores (created lazily in the loop).
        self._sem: dict[uuid.UUID, asyncio.Semaphore] = {}

        # Metrics
        self._metrics = EventBusMetrics()

    # --- config / lifecycle ------------------------------------------------

    @property
    def state(self) -> EventBusState:
        return self._state

    @property
    def config(self) -> EventBusConfig:
        return self._config

    def configure(self, config: EventBusConfig) -> None:
        """Replace the active configuration (validates it)."""
        if self._state not in (
            EventBusState.UNINITIALIZED,
            EventBusState.INITIALIZING,
        ):
            raise EventRegistryError(
                "EventBus.configure() is only permitted before RUNNING."
            )
        self._config = config

    async def initialize(self, kernel: Any = None) -> EventBusState:
        """Initialize and transition to RUNNING (Task 5 Phase 6, INV-EB-003).

        Idempotent: a second initialize while RUNNING is a no-op. The optional
        ``kernel`` is accepted for interface symmetry but the bus does not depend
        on Hermes internals (INV-EB-002).
        """
        if self._state is EventBusState.RUNNING:
            return self._state
        if self._state in (EventBusState.DRAINING, EventBusState.SHUTDOWN):
            raise EventRegistryError(
                f"EventBus cannot initialize from state {self._state.value}."
            )
        self._state = EventBusState.INITIALIZING
        self._loop = asyncio.get_running_loop()
        # Bind the cross-coroutine coordination primitives to THIS loop. They
        # must be created inside a running loop (asyncio.Condition requires it).
        self._space_cv = asyncio.Condition()
        self._not_empty_cv = asyncio.Condition()
        # INV-EB-003: emit the architecture-defined CoreComponentInitialized
        # diagnostic/audit signal. CORE_COMPONENT_INITIALIZED is a canonical
        # EventType (no fabricated EventType is introduced).
        self._emit_diagnostic(
            "CoreComponentInitialized",
            {"component": "EventBus", "state": "INITIALIZING"},
        )
        self._state = EventBusState.RUNNING
        if self._config.auto_start_dispatch_worker:
            self._start_worker()
        self._emit_diagnostic(
            "CoreComponentInitialized",
            {"component": "EventBus", "state": "RUNNING"},
        )
        return self._state

    def _start_worker(self) -> None:
        if self._worker_task is not None and not self._worker_task.done():
            return
        self._worker_task = asyncio.ensure_future(self._worker_loop())

    async def _worker_loop(self) -> None:
        """Background dispatch worker (production mode)."""
        while self._state is EventBusState.RUNNING:
            await self._dispatch_available()
            # Yield; if nothing dispatched, wait for a publish to notify us.
            assert self._not_empty_cv is not None  # initialized in initialize()
            async with self._not_empty_cv:
                if self._state is not EventBusState.RUNNING:
                    break
                try:
                    await asyncio.wait_for(
                        self._not_empty_cv.wait(), timeout=0.05
                    )
                except (TimeoutError, asyncio.CancelledError):
                    pass
        # Draining/shutdown: drain whatever remains.
        await self._drain_remaining()

    async def shutdown(self) -> EventBusState:
        """Graceful shutdown: DRAINING then SHUTDOWN (Task 5 Phase 6)."""
        if self._state is EventBusState.SHUTDOWN:
            return self._state
        self._state = EventBusState.DRAINING
        deadline = time.monotonic() + (self._config.shutdownDrainTimeoutMs / 1000.0)
        while self._queued_total() > 0 and time.monotonic() < deadline:
            await self._dispatch_available()
            if self._queued_total() == 0:
                break
        # Stop the worker task if it exists.
        if self._worker_task is not None and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except (asyncio.CancelledError, Exception):
                pass
            self._worker_task = None
        self._state = EventBusState.SHUTDOWN
        self._emit_diagnostic("EventBusShutdown", {"state": "SHUTDOWN"})
        return self._state

    # --- subscription integration (delegate to SubscriptionManager) --------

    def subscribe(self, options: SubscribeOptions) -> Any:
        """Subscribe by delegating to SubscriptionManager.register."""
        return self._subscriptions.register(options)

    def unsubscribe(self, options: UnsubscribeOptions) -> int:
        """Unsubscribe by delegating to SubscriptionManager.unsubscribe."""
        ets = list(options.eventTypes) if options.eventTypes else None
        return self._subscriptions.unsubscribe(
            subscription_id=options.subscriptionId,
            event_types=ets,
            all_=options.all_,
            immediate=options.immediate,
        )

    def getSubscription(self, subscriptionId: Any) -> Subscription | None:
        return self._subscriptions.get_subscription(subscriptionId)

    def listSubscriptions(
        self, filter: Callable[[Subscription], bool] | None = None
    ) -> list[Subscription]:
        subs = self._subscriptions.list_all()
        if filter is None:
            return subs
        return [s for s in subs if filter(s)]

    # --- publish pipeline (INV-EB-012: enqueue only) -----------------------

    async def publish(
        self, event: Event, options: PublishOptions | None = None
    ) -> PublishResult:
        opts = options or PublishOptions()
        return await self._publish_one(event, opts)

    async def publishBatch(
        self, events: list[Event], options: PublishOptions | None = None
    ) -> list[PublishResult]:
        return [await self._publish_one(e, options or PublishOptions()) for e in events]

    async def _publish_one(
        self, event: Event, opts: PublishOptions
    ) -> PublishResult:
        # 1. Lifecycle gate
        if self._state not in (EventBusState.RUNNING,):
            return PublishResult(
                PublishStatus.REJECTED_SHUTDOWN,
                event.eventId if isinstance(getattr(event, "eventId", None), uuid.UUID) else None,
                f"EventBus is {self._state.value}; publish rejected (not enqueued).",
            )

        # 2. Event type check (must be a canonical, registered EventType)
        if not isinstance(event.eventType, EventType):
            self._incr("validation_failures")
            return PublishResult(
                PublishStatus.REJECTED_VALIDATION, event.eventId,
                "eventType is not a canonical EventType.",
            )
        reg = self._registry.get(event.eventType)
        if reg is None:
            self._incr("validation_failures")
            return PublishResult(
                PublishStatus.REJECTED_VALIDATION, event.eventId,
                f"EventType {event.eventType.name} is not registered.",
            )

        # 3/4. Registry schema validation (uses registry.validate_schema, NOT a
        # schema-hash comparison).
        vr = self._registry.validate_schema(event.eventType, event.payload.to_dict())
        if not vr.valid:
            self._incr("validation_failures")
            return PublishResult(
                PublishStatus.REJECTED_VALIDATION, event.eventId,
                f"Schema validation failed: {vr.error_message}",
            )

        # 5. Event integrity / checksum validation (defense in depth; checksum
        # is SHA-256 of the canonical payload — distinct from schemaHash).
        try:
            expected = compute_checksum(event.payload.to_dict())
        except Exception as exc:  # noqa: BLE001
            self._incr("validation_failures")
            return PublishResult(
                PublishStatus.REJECTED_VALIDATION, event.eventId,
                f"Checksum computation failed: {exc}",
            )
        if expected != event.checksum:
            self._incr("validation_failures")
            return PublishResult(
                PublishStatus.REJECTED_VALIDATION, event.eventId,
                "Event checksum mismatch (integrity check failed).",
            )

        # 6. Idempotency pre-check (best-effort fast path; authoritative
        # decision is atomic with enqueue below).
        if opts.idempotencyKey is not None and opts.idempotencyKey in self._seen_keys:
            return PublishResult(
                PublishStatus.REJECTED_DUPLICATE, event.eventId,
                "Idempotency key already seen.",
            )

        # 7. Capacity check (with optional blocking wait)
        lane_idx = self._lane_index_for(event.priority)
        if self._lane_full(lane_idx):
            if opts.blocking:
                try:
                    await self._wait_for_space(opts.timeoutMs)
                except TimeoutError:
                    self._incr("queue_overflows")
                    return PublishResult(
                        PublishStatus.REJECTED_CAPACITY, event.eventId,
                        "Publish queue full; blocking wait timed out.",
                    )
            if self._lane_full(lane_idx):
                self._incr("queue_overflows")
                return PublishResult(
                    PublishStatus.REJECTED_CAPACITY, event.eventId,
                    "Publish queue full (REJECTED_CAPACITY; not dropped silently).",
                )

        # 8. Priority-lane enqueue (authoritative idempotency decision +
        # capacity decision are atomic under the queue lock so a duplicate can
        # never be enqueued twice).
        assert self._space_cv is not None  # initialized in initialize()
        async with self._space_cv:
            if opts.idempotencyKey is not None:
                if opts.idempotencyKey in self._seen_keys:
                    return PublishResult(
                        PublishStatus.REJECTED_DUPLICATE, event.eventId,
                        "Idempotency key already seen (atomic check).",
                    )
            if self._lane_full(lane_idx):
                self._incr("queue_overflows")
                return PublishResult(
                    PublishStatus.REJECTED_CAPACITY, event.eventId,
                    "Publish queue full at enqueue.",
                )
            self._lanes[lane_idx].append(event)
            if opts.idempotencyKey is not None:
                self._seen_keys.add(opts.idempotencyKey)
            self._space_cv.notify_all()
        assert self._not_empty_cv is not None  # initialized in initialize()
        async with self._not_empty_cv:
            self._not_empty_cv.notify_all()

        # 9. Accepted
        self._incr("published")
        self._record_history(event)
        return PublishResult(PublishStatus.ACCEPTED, event.eventId, "Accepted.")

    # --- dispatch ----------------------------------------------------------

    def _lane_index_for(self, priority: EventPriority) -> int:
        return _LANE_INDEX.get(priority, _LANE_INDEX[EventPriority.NORMAL])

    def _lane_full(self, lane_idx: int) -> bool:
        return len(self._lanes[lane_idx]) >= self._config.publishQueueCapacity

    async def _wait_for_space(self, timeout_ms: int | None) -> None:
        """Block until at least one lane has free capacity (3.12-compatible).

        Uses ``asyncio.wait_for(condition.wait(), timeout)`` since
        ``Condition.wait(timeout)`` is 3.13+ only; the project requires 3.12.
        """
        assert self._space_cv is not None  # initialized in initialize()
        timeout = (timeout_ms / 1000.0) if timeout_ms is not None else None
        deadline = None if timeout is None else time.monotonic() + timeout
        async with self._space_cv:
            while any(self._lane_full(i) for i in range(len(self._lanes))):
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    raise TimeoutError("wait_for_space timed out")
                # wait_for raises asyncio.TimeoutError on expiry.
                await asyncio.wait_for(self._space_cv.wait(), remaining)

    async def drain(self) -> int:
        """Process all currently-queued (and due) events. Returns count dispatched.

        Deterministic single-pass-per-call driver used by unit tests and by
        ``shutdown``. Repeated calls drain whatever remains (including retries
        that have become due).
        """
        return await self._drain_remaining()

    def _queued_total(self) -> int:
        return sum(len(lane) for lane in self._lanes) + len(self._retry_heap)

    async def _drain_remaining(self) -> int:
        dispatched = 0
        # Recursive-depth accounting is scoped to a single drain pass: it guards
        # against a pathological loop where one correlationId keeps generating new
        # events that re-dispatch within the same pass. Reset before each pass.
        self._dispatch_depth.clear()
        # Bound iterations to avoid pathological loops when retries are not yet due.
        guard = max(1, self._config.publishQueueCapacity * 4 + len(self._retry_heap) * 4)
        while True:
            item = self._select_next()
            if item is None:
                break
            # A lane/retry entry was popped -> capacity freed. Wake any blocking
            # publishers waiting for space (backpressure release).
            if self._space_cv is not None:
                async with self._space_cv:
                    self._space_cv.notify_all()
            event, retry_ctx = item
            await self._dispatch_event(event, retry_ctx)
            dispatched += 1
            guard -= 1
            if guard <= 0:
                break
        return dispatched

    async def _dispatch_available(self) -> int:
        """Process events that are available right now (no waiting on future retries)."""
        return await self._drain_remaining()

    def _select_next(
        self,
    ) -> tuple[Event, tuple[uuid.UUID, int] | None] | None:
        """Pick the next event to dispatch.

        Returns ``(event, retry_ctx)`` where ``retry_ctx`` is
        ``(subscriptionId, attempt)`` when the event was popped from the retry
        heap (so retries target only the failing subscription), or ``None`` for a
        fresh publish (dispatch to all matching subscriptions at attempt 0).

        Ordering: due retries first (earliest due timestamp + lowest attempt),
        then highest-priority lane, FIFO within a lane.
        """
        # Due retries first (only those whose due time has elapsed).
        now = time.monotonic_ns()
        due: list[tuple[int, int, uuid.UUID, Event]] = []
        while self._retry_heap and self._retry_heap[0][0] <= now:
            due.append(heapq.heappop(self._retry_heap))
        if due:
            due.sort(key=lambda t: (t[0], t[1]))
            for item in due[1:]:
                heapq.heappush(self._retry_heap, item)
            due_ns, attempt, sub_id, event = due[0]
            return event, (sub_id, attempt)
        for lane in self._lanes:
            if lane:
                return lane.popleft(), None
        return None

    async def _dispatch_event(
        self, event: Event, retry_ctx: tuple[uuid.UUID, int] | None = None
    ) -> None:
        """Match subscriptions, sort, execute handlers with isolation + retry."""
        start = time.monotonic_ns()

        # Recursive-depth protection (per correlationId, scoped to this drain
        # pass). Increment once per dispatch of a given correlationId; if it
        # exceeds maxDispatchDepth within one pass we stop processing further
        # events of that correlationId and flag RecursiveEventDetected (the count
        # is reset at the start of each drain). This bounds pathological loops
        # where one correlationId keeps re-publishing into the same drain.
        corr = event.correlationId
        depth = self._dispatch_depth.get(corr, 0) + 1
        if depth > self._config.maxDispatchDepth:
            self._incr("recursive_events")
            self._emit_diagnostic(
                "RecursiveEventDetected",
                {"correlationId": str(corr), "depth": depth},
            )
            return
        self._dispatch_depth[corr] = depth

        retry_sub_id, retry_attempt = retry_ctx if retry_ctx else (None, 0)
        subs = self._subscriptions.matching(event)
        # Sort by HandlerPriority then subscriptionId (INV-SUB-007).
        subs_sorted = sorted(
            subs,
            key=lambda s: (
                self._handler_priority_value(s),
                str(s.subscriptionId),
            ),
        )
        for sub in subs_sorted:
            if retry_ctx is not None and sub.subscriptionId != retry_sub_id:
                # A retry targets ONLY the subscription that failed; skip others.
                continue
            await self._execute_handler(event, sub, retry_attempt)

        self._incr("dispatched")
        elapsed_ms = (time.monotonic_ns() - start) / 1_000_000.0
        self._metrics = self._metrics.__class__(
            **{**self._metrics.__dict__, "dispatch_cycle_latency_ms": elapsed_ms}
        )

    def _handler_priority_value(self, sub: Subscription) -> int:
        p = sub.priority
        if isinstance(p, HandlerPriority):
            return int(p.value)
        if p == WILDCARD_PRIORITY:
            return WILDCARD_PRIORITY
        if isinstance(p, int):
            return p
        return int(HandlerPriority.NORMAL.value)

    async def _execute_handler(
        self, event: Event, sub: Subscription, attempt: int
    ) -> None:
        """Execute a single handler, isolate failures, apply retry/DLQ."""
        sid = sub.subscriptionId
        sem = self._sem.setdefault(
            sid, asyncio.Semaphore(max(1, sub.maxConcurrency))
        )
        timeout = (
            (sub.timeoutMs / 1000.0)
            if sub.timeoutMs and sub.timeoutMs > 0
            else (self._config.handlerTimeoutMs / 1000.0)
        )
        await sem.acquire()
        try:
            h_start = time.monotonic_ns()
            try:
                if sub.handlerType == "async" or _is_async_handler(sub.handler):
                    await asyncio.wait_for(
                        _maybe_await(sub.handler, event), timeout=timeout
                    )
                else:
                    loop = asyncio.get_running_loop()
                    fut = loop.run_in_executor(None, sub.handler, event)
                    await asyncio.wait_for(fut, timeout=timeout)
                self._incr("delivered")
            except TimeoutError:
                self._record_failure(event, sub, attempt, "TIMEOUT", "Handler timed out")
            except Exception as exc:  # noqa: BLE001
                self._record_failure(
                    event, sub, attempt, "TRANSIENT",
                    f"{type(exc).__name__}: {exc}",
                )
            finally:
                h_dur = (time.monotonic_ns() - h_start) / 1_000_000.0
                self._metrics = self._metrics.__class__(
                    **{**self._metrics.__dict__, "last_handler_duration_ms": h_dur}
                )
        finally:
            sem.release()

    def _record_failure(
        self,
        event: Event,
        sub: Subscription,
        attempt: int,
        classification: str,
        reason: str,
    ) -> None:
        """Apply retry policy; enqueue retry or dead-letter on exhaustion."""
        rp = sub.retryPolicy or RetryPolicy()  # default architecture retry policy
        max_attempts = rp.maxAttempts
        if classification in ("TRANSIENT", "TIMEOUT", "UNAVAILABLE") and attempt < max_attempts - 1:
            # Schedule retry with exponential backoff (+ optional jitter).
            delay_ms = rp.baseDelayMs * (rp.backoffMultiplier ** attempt)
            delay_ms = min(delay_ms, rp.maxDelayMs)
            if rp.jitter:
                # Deterministic-ish jitter within ±10% using a bounded offset.
                delay_ms = delay_ms * 0.95
            due = time.monotonic_ns() + int(delay_ms * 1_000_000)
            heapq.heappush(
                self._retry_heap, (due, attempt + 1, sub.subscriptionId, event)
            )
            if len(self._retry_heap) > self._config.retryQueueCapacity:
                # Retry overflow -> oldest retry goes to DLQ (retry->DLQ rule).
                self._retry_heap.sort()
                _, old_attempt, old_sid, old_event = self._retry_heap.pop(0)
                self._dead_letter(
                    old_event, old_sid, "retry_overflow",
                    "Retry queue overflow", old_attempt,
                )
            self._incr("retries")
            return
        # Non-retryable or exhaustion -> DLQ.
        self._dead_letter(event, sub.subscriptionId, classification, reason, attempt)

    def _dead_letter(
        self,
        event: Event,
        sub_id: uuid.UUID,
        classification: str,
        reason: str,
        attempt: int,
    ) -> None:
        entry = DeadLetterEntry(
            entryId=str(uuid7()),
            event=event,
            subscriptionId=sub_id,
            reason=reason,
            classification=classification,
            attempt=attempt,
            createdAt=_now_iso(),
            createdAtMonotonic=time.monotonic_ns(),
            metadata={},
        )
        if len(self._dlq) >= self._config.dlqCapacity:
            self._dlq.popleft()  # DROP_OLDEST
        self._dlq.append(entry)
        self._incr("dlq")

    # --- event history (bounded ring) -------------------------------------

    def _record_history(self, event: Event) -> None:
        if self._config.historyCapacity <= 0:
            return
        self._history.append(event)
        while len(self._history) > self._config.historyCapacity:
            self._history.popleft()

    def getEvent(self, eventId: uuid.UUID) -> Event | None:
        for e in reversed(self._history):
            if e.eventId == eventId:
                return e
        return None

    def getEventsByCorrelationId(self, correlationId: uuid.UUID) -> list[Event]:
        return [e for e in self._history if e.correlationId == correlationId]

    def getEventsByType(
        self, eventType: EventType, limit: int | None = None
    ) -> list[Event]:
        out = [e for e in self._history if e.eventType == eventType]
        if limit is not None:
            out = out[-limit:]
        return out

    def getRecentEvents(self, limit: int | None = None) -> list[Event]:
        out = list(self._history)
        if limit is not None:
            out = out[-limit:]
        return out

    # --- dead-letter queries / replay --------------------------------------

    def getDeadLetters(
        self,
        filter: DeadLetterFilter | None = None,
        limit: int | None = None,
    ) -> list[DeadLetterEntry]:
        out = list(self._dlq)
        if filter is not None:
            if filter.subscriptionId is not None:
                out = [e for e in out if e.subscriptionId == filter.subscriptionId]
            if filter.classification is not None:
                out = [e for e in out if e.classification == filter.classification]
            if filter.eventType is not None:
                out = [e for e in out if e.event.eventType == filter.eventType]
        if limit is not None:
            out = out[-limit:]
        return out

    async def replayDeadLetter(
        self, entryId: str, options: PublishOptions | None = None
    ) -> PublishResult:
        entry = next((e for e in self._dlq if e.entryId == entryId), None)
        if entry is None:
            return PublishResult(
                PublishStatus.REJECTED_VALIDATION, None,
                f"Dead-letter entry {entryId} not found.",
            )
        # Reconstruct a NEW event with a fresh UUIDv7 id; preserve
        # correlationId / causationId. Do NOT mutate the original.
        data = entry.event.to_dict()
        data["eventId"] = str(uuid7())
        if entry.event.causationId is not None:
            data["causationId"] = str(entry.event.causationId)
        data["correlationId"] = str(entry.event.correlationId)
        new_event = Event.from_dict(data)
        return await self._publish_one(new_event, options or PublishOptions())

    def purgeDeadLetters(self, olderThan: int | None = None) -> int:
        """Remove DLQ entries older than ``olderThan`` (monotonic ns).

        If ``olderThan`` is None, purge ALL entries.
        """
        before = len(self._dlq)
        if olderThan is None:
            self._dlq.clear()
        else:
            self._dlq = deque(
                e for e in self._dlq if e.createdAtMonotonic >= olderThan
            )
        return before - len(self._dlq)

    # --- replay (v1.0 memory-only) -----------------------------------------

    async def replay(self, options: ReplayOptions | None = None) -> list[Event]:
        """Replay retained in-memory history (Task 5 Phase 21, v1.0).

        v1.0 LIMITATIONS (documented, not deferred-infrastructure):
          * Memory-only; no StateManager/StorageManager integration.
          * No deterministic replay engine / external side-effect interception.
        ``dryRun`` reconstructs the events to be replayed but does NOT publish
        them (no handler side effects).
        """
        opts = options or ReplayOptions()
        candidates = list(self._history)
        if opts.eventType is not None:
            candidates = [e for e in candidates if e.eventType == opts.eventType]
        if opts.correlationId is not None:
            candidates = [e for e in candidates if e.correlationId == opts.correlationId]
        if opts.sinceEventId is not None:
            idx = next(
                (i for i, e in enumerate(candidates) if e.eventId == opts.sinceEventId),
                None,
            )
            if idx is not None:
                candidates = candidates[idx + 1:]
        if opts.limit is not None:
            candidates = candidates[-opts.limit:]

        reconstructed: list[Event] = []
        for e in candidates:
            data = e.to_dict()
            if opts.newEventIds:
                data["eventId"] = str(uuid7())
            if e.causationId is not None:
                data["causationId"] = str(e.causationId)
            data["correlationId"] = str(e.correlationId)
            reconstructed.append(Event.from_dict(data))

        if not opts.dryRun:
            for ne in reconstructed:
                await self._publish_one(ne, PublishOptions())
        return reconstructed

    # --- observability -----------------------------------------------------

    def _emit_diagnostic(self, name: str, payload: dict[str, Any]) -> None:
        if self._diagnostic_hook is None:
            return
        try:
            self._diagnostic_hook(name, payload)
        except Exception:  # noqa: BLE001
            # Diagnostic emission must never crash the bus.
            pass

    def healthCheck(self) -> EventBusHealth:
        healthy = self._state is EventBusState.RUNNING and self._queued_total() < (
            self._config.publishQueueCapacity * len(self._lanes)
        )
        return EventBusHealth(
            healthy=healthy,
            state=self._state,
            queued_events=self._queued_total(),
            dlq_size=len(self._dlq),
            active_subscriptions=self._subscriptions.subscription_count,
            details="",
        )

    def getDiagnostics(self) -> EventBusDiagnostics:
        return EventBusDiagnostics(
            state=self._state,
            config=self._config,
            queue_depths={
                p.name: len(self._lanes[_LANE_INDEX[p]])
                for p in _PRIORITY_LANES
            },
            subscription_count=self._subscriptions.subscription_count,
            dlq_size=len(self._dlq),
            retry_queue_size=len(self._retry_heap),
            metrics=self._metrics,
        )

    def getMetrics(self) -> EventBusMetrics:
        return self._metrics.__class__(
            **{
                **self._metrics.__dict__,
                "active_subscriptions": self._subscriptions.subscription_count,
                "queued_events": self._queued_total(),
                "dlq_size": len(self._dlq),
                "retry_queue_size": len(self._retry_heap),
            }
        )

    # --- internal metrics helper -------------------------------------------

    def _incr(self, field_name: str) -> None:
        cur = getattr(self._metrics, field_name)
        self._metrics = self._metrics.__class__(
            **{**self._metrics.__dict__, field_name: cur + 1}
        )


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _is_async_handler(handler: Any) -> bool:
    import inspect

    if inspect.iscoroutinefunction(handler):
        return True
    if callable(handler) and inspect.iscoroutinefunction(getattr(handler, "__call__", None)):
        return True
    # Reuse the architecture filter async-detection for callables.
    return is_async_filter(handler)


async def _maybe_await(fn: Callable, event: Event) -> Any:
    result = fn(event)
    if asyncio.iscoroutine(result):
        return await result
    return result


def _now_iso() -> str:
    return (
        datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )


def uuid7() -> uuid.UUID:
    """Generate a UUIDv7 via the core helper (no duplicate logic)."""
    from aios.events.core.ids import uuid7 as _core_uuid7

    return _core_uuid7()
