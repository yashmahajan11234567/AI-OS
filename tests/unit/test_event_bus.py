"""
Task 5 — EventBus unit tests (Phase 26 coverage).

These tests exercise the architecture-aligned ``EventBus`` in
``src/aios/events/core/bus.py``. They drive dispatch deterministically by
passing ``auto_start_dispatch_worker=False`` (the default) and calling
``await bus.drain()`` rather than relying on a background worker, so ordering
and counts are reproducible.

All tests are coroutine tests (``pytestmark = pytest.mark.asyncio`` in
``conftest.py``); the declared ``pytest-asyncio`` plugin drives them without
any modification to ``pyproject.toml`` or Task 1–4 files.
"""

from __future__ import annotations

import asyncio

from aios.events.core import (
    ComponentIdentity,
    ComponentType,
    DeadLetterEntry,
    DeadLetterFilter,
    Event,
    EventBus,
    EventBusConfig,
    EventBusDiagnostics,
    EventBusHealth,
    EventBusMetrics,
    EventBusState,
    EventPriority,
    EventType,
    HandlerPriority,
    PublishOptions,
    PublishResult,
    PublishStatus,
    ReplayOptions,
    RetryPolicy,
    SubscribeOptions,
    UnsubscribeOptions,
    reset_event_bus_singleton,
)
from aios.events.core.errors import EventRegistryError
from aios.events.core.ids import uuid7
from aios.events.core.registry import EventTypeRegistry


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _source(name: str = "TestSvc") -> ComponentIdentity:
    return ComponentIdentity(
        component_type=ComponentType.ENGINEERING_SERVICE,
        component_name=name,
    )


def make_event(
    event_type: EventType = EventType.TASK_CREATED,
    priority: EventPriority = EventPriority.NORMAL,
    correlation_id=None,
    payload: dict | None = None,
) -> Event:
    return Event(
        eventType=event_type,
        source=_source(),
        priority=priority,
        correlationId=correlation_id,
        payload=payload if payload is not None else {"k": "v"},
    )


def new_bus(config: EventBusConfig | None = None, **kw) -> EventBus:
    return EventBus(config=config, **kw)


# ---------------------------------------------------------------------------
# public type / enum shape
# ---------------------------------------------------------------------------


def test_publish_status_has_exactly_five_values():
    assert {s.value for s in PublishStatus} == {
        "ACCEPTED",
        "REJECTED_VALIDATION",
        "REJECTED_CAPACITY",
        "REJECTED_SHUTDOWN",
        "REJECTED_DUPLICATE",
    }
    assert len(PublishStatus) == 5


def test_event_bus_state_shape():
    assert {s.value for s in EventBusState} == {
        "UNINITIALIZED",
        "INITIALIZING",
        "RUNNING",
        "DRAINING",
        "SHUTDOWN",
    }


def test_publish_result_and_options_frozen():
    r = PublishResult(PublishStatus.ACCEPTED)
    assert r.accepted is True
    assert r.status is PublishStatus.ACCEPTED
    assert r.eventId is None
    # frozen dataclasses cannot be mutated
    try:
        r.status = PublishStatus.REJECTED_CAPACITY  # type: ignore[misc]
        assert False, "PublishResult should be immutable"
    except (AttributeError, TypeError):
        pass
    o = PublishOptions(blocking=True, timeoutMs=5)
    assert o.blocking is True
    assert o.timeoutMs == 5


# ---------------------------------------------------------------------------
# singleton (INV-EB-001)
# ---------------------------------------------------------------------------


def test_singleton_rejects_second_construction():
    b1 = new_bus()
    try:
        new_bus()
        assert False, "second EventBus construction MUST be rejected"
    except EventRegistryError:
        pass
    # first instance still usable
    assert b1.state is EventBusState.UNINITIALIZED


# ---------------------------------------------------------------------------
# lifecycle (INV-EB-003)
# ---------------------------------------------------------------------------


async def test_lifecycle_uninitialized_to_running_to_shutdown():
    b = new_bus()
    assert b.state is EventBusState.UNINITIALIZED
    await b.initialize()
    assert b.state is EventBusState.RUNNING
    state = await b.shutdown()
    assert state is EventBusState.SHUTDOWN


async def test_initialize_is_idempotent_when_running():
    b = new_bus()
    await b.initialize()
    again = await b.initialize()
    assert again is EventBusState.RUNNING
    assert b.state is EventBusState.RUNNING


async def test_initialize_emits_core_component_initialized_diagnostic():
    seen = []
    b = new_bus(diagnostic_hook=lambda name, payload: seen.append(name))
    await b.initialize()
    assert "CoreComponentInitialized" in seen


async def test_diagnostic_hook_exceptions_do_not_crash_bus():
    def boom(name, payload):
        raise RuntimeError("hook boom")

    b = new_bus(diagnostic_hook=boom)
    # Must not raise despite the hook raising.
    await b.initialize()
    assert b.state is EventBusState.RUNNING


async def test_configure_only_allowed_before_running():
    b = new_bus()
    b.configure(EventBusConfig(publishQueueCapacity=5))
    await b.initialize()
    try:
        b.configure(EventBusConfig())
        assert False, "configure after RUNNING must be rejected"
    except EventRegistryError:
        pass


async def test_health_check_reflects_state():
    b = new_bus()
    h = b.healthCheck()
    assert h.healthy is False  # UNINITIALIZED
    await b.initialize()
    h = b.healthCheck()
    assert h.healthy is True
    assert isinstance(h, EventBusHealth)


# ---------------------------------------------------------------------------
# config validation (Phase 25)
# ---------------------------------------------------------------------------


def test_config_validation_rejects_bad_values():
    for kw in (
        {"publishQueueCapacity": 0},
        {"retryQueueCapacity": 0},
        {"dlqCapacity": 0},
        {"maxDispatchDepth": 0},
        {"handlerTimeoutMs": -1},
    ):
        try:
            EventBusConfig(**kw)
            assert False, f"config {kw} should be rejected"
        except EventRegistryError:
            pass


def test_config_defaults():
    c = EventBusConfig()
    assert c.publishQueueCapacity == 10000
    assert c.retryQueueCapacity == 1000
    assert c.dlqCapacity == 1000
    assert c.maxDispatchDepth == 16


# ---------------------------------------------------------------------------
# publish pipeline (INV-EB-012: enqueue only)
# ---------------------------------------------------------------------------


async def test_publish_requires_running_state():
    b = new_bus()
    res = await b.publish(make_event())
    assert res.status is PublishStatus.REJECTED_SHUTDOWN


async def test_publish_accepted_and_enqueues_only():
    b = new_bus()
    await b.initialize()
    calls = []
    b.subscribe(
        SubscribeOptions(
            subscriber=_source(),
            event_types=[EventType.TASK_CREATED],
            handler=lambda e: calls.append(e.eventId),
        )
    )
    res = await b.publish(make_event())
    assert res.status is PublishStatus.ACCEPTED
    assert res.eventId is not None
    # INV-EB-012: publish enqueues only; handler NOT invoked until drain.
    assert calls == []
    # History records the published event.
    assert len(b.getRecentEvents()) == 1
    # Now dispatch.
    await b.drain()
    assert len(calls) == 1


async def test_publish_validation_rejects_unregistered_event_type():
    # Custom registry without canonical auto-population => nothing registered.
    reg = EventTypeRegistry(auto_populate_canonical=False)
    b = new_bus(registry=reg)
    await b.initialize()
    res = await b.publish(make_event())
    assert res.status is PublishStatus.REJECTED_VALIDATION


async def test_publish_validation_checksum_mismatch(monkeypatch):
    b = new_bus()
    await b.initialize()
    # Force the integrity check to disagree with the event checksum.
    import aios.events.core.bus as bus_mod

    monkeypatch.setattr(bus_mod, "compute_checksum", lambda payload: "0" * 64)
    res = await b.publish(make_event())
    assert res.status is PublishStatus.REJECTED_VALIDATION


async def test_publish_idempotency_duplicate_key():
    b = new_bus()
    await b.initialize()
    r1 = await b.publish(make_event(), PublishOptions(idempotencyKey="k1"))
    assert r1.status is PublishStatus.ACCEPTED
    r2 = await b.publish(make_event(), PublishOptions(idempotencyKey="k1"))
    assert r2.status is PublishStatus.REJECTED_DUPLICATE
    r3 = await b.publish(make_event(), PublishOptions(idempotencyKey="k2"))
    assert r3.status is PublishStatus.ACCEPTED


async def test_publish_capacity_rejected_nonblocking():
    b = new_bus(EventBusConfig(publishQueueCapacity=1))
    await b.initialize()
    r1 = await b.publish(make_event())
    assert r1.accepted
    r2 = await b.publish(make_event())
    assert r2.status is PublishStatus.REJECTED_CAPACITY


async def test_publish_capacity_blocking_times_out():
    b = new_bus(EventBusConfig(publishQueueCapacity=1))
    await b.initialize()
    assert (await b.publish(make_event())).accepted
    r2 = await b.publish(make_event(), PublishOptions(blocking=True, timeoutMs=10))
    assert r2.status is PublishStatus.REJECTED_CAPACITY


async def test_publish_batch():
    b = new_bus()
    await b.initialize()
    results = await b.publishBatch([make_event(), make_event()])
    assert all(r.accepted for r in results)
    assert len(results) == 2


# ---------------------------------------------------------------------------
# priority lanes / dispatch ordering
# ---------------------------------------------------------------------------


async def test_priority_lane_ordering():
    b = new_bus()
    await b.initialize()
    order = []
    b.subscribe(
        SubscribeOptions(
            subscriber=_source(),
            event_types=[EventType.TASK_CREATED],
            handler=lambda e: order.append(e.priority),
        )
    )
    # Publish LOW first, then CRITICAL (same type, different event priority).
    await b.publish(make_event(priority=EventPriority.LOW))
    await b.publish(make_event(priority=EventPriority.CRITICAL))
    await b.drain()
    assert order[0] is EventPriority.CRITICAL
    assert order[1] is EventPriority.LOW


async def test_one_failure_does_not_block_others():
    b = new_bus()
    await b.initialize()
    good, bad = [], []

    def failing(e):
        bad.append(e.eventId)
        raise ValueError("boom")

    b.subscribe(
        SubscribeOptions(
            subscriber=_source("Good"),
            event_types=[EventType.TASK_CREATED],
            handler=lambda e: good.append(e.eventId),
        )
    )
    b.subscribe(
        SubscribeOptions(
            subscriber=_source("Bad"),
            event_types=[EventType.TASK_CREATED],
            handler=failing,
        )
    )
    res = await b.publish(make_event())
    assert res.accepted
    await b.drain()
    assert len(good) == 1  # successful handler still ran
    assert len(bad) == 1  # failing handler ran but isolated


# ---------------------------------------------------------------------------
# handler execution: sync + async, maxConcurrency, timeout
# ---------------------------------------------------------------------------


async def test_async_handler_invoked():
    b = new_bus()
    await b.initialize()
    called = []

    async def ah(e):
        called.append(e.eventId)

    b.subscribe(
        SubscribeOptions(
            subscriber=_source(),
            event_types=[EventType.TASK_CREATED],
            handler=ah,
            handler_type="async",
        )
    )
    await b.publish(make_event())
    await b.drain()
    assert len(called) == 1


async def test_async_handler_auto_detected_without_flag():
    b = new_bus()
    await b.initialize()
    called = []

    async def ah(e):
        called.append(e.eventId)

    # handler_type defaults to "sync" but bus must detect async via inspect.
    b.subscribe(
        SubscribeOptions(
            subscriber=_source(),
            event_types=[EventType.TASK_CREATED],
            handler=ah,
        )
    )
    await b.publish(make_event())
    await b.drain()
    assert len(called) == 1


async def test_max_concurrency_limit_respected():
    b = new_bus()
    await b.initialize()
    current = 0
    peak = 0
    lock = asyncio.Lock()

    async def ah(e):
        nonlocal current, peak
        async with lock:
            current += 1
            peak = max(peak, current)
        await asyncio.sleep(0.01)
        async with lock:
            current -= 1

    b.subscribe(
        SubscribeOptions(
            subscriber=_source(),
            event_types=[EventType.TASK_CREATED],
            handler=ah,
            handler_type="async",
            max_concurrency=2,
        )
    )
    for _ in range(6):
        await b.publish(make_event())
    await b.drain()
    assert peak <= 2
    assert peak >= 1


async def test_handler_timeout_classified_as_timeout():
    b = new_bus()
    await b.initialize()

    def slow(e):
        import time as _t

        _t.sleep(0.05)

    b.subscribe(
        SubscribeOptions(
            subscriber=_source(),
            event_types=[EventType.TASK_CREATED],
            handler=slow,
            timeout_ms=1,  # 1ms timeout vs 50ms work
            retry_policy=RetryPolicy(maxAttempts=1),  # immediate DLQ on fail
        )
    )
    await b.publish(make_event())
    await b.drain()
    dlq = b.getDeadLetters()
    assert len(dlq) == 1
    assert dlq[0].classification == "TIMEOUT"


# ---------------------------------------------------------------------------
# retry + DLQ
# ---------------------------------------------------------------------------


async def test_retry_then_dead_letter_on_exhaustion():
    b = new_bus()
    await b.initialize()
    attempts = []

    def always_fail(e):
        attempts.append(1)
        raise RuntimeError("nope")

    b.subscribe(
        SubscribeOptions(
            subscriber=_source(),
            event_types=[EventType.TASK_CREATED],
            handler=always_fail,
            # fast, deterministic retries; 3 total attempts then DLQ
            # Use baseDelayMs=20 to stay above Windows timer resolution (~15ms)
            retry_policy=RetryPolicy(
                maxAttempts=3, baseDelayMs=20, maxDelayMs=20, jitter=False
            ),
        )
    )
    await b.publish(make_event())
    await b.drain()
    # not yet exhausted (retry due in ~20ms)
    assert b.getMetrics().dlq == 0
    # Sleep sufficiently longer than the delay for deterministic behavior
    await asyncio.sleep(0.05)
    await b.drain()
    await asyncio.sleep(0.05)
    await b.drain()
    assert b.getMetrics().dlq == 1
    dlq = b.getDeadLetters()
    assert dlq[0].classification == "TRANSIENT"
    assert len(attempts) == 3  # exactly maxAttempts attempts


async def test_dlq_filter_and_capacity_drop_oldest():
    b = new_bus(EventBusConfig(dlqCapacity=3))
    await b.initialize()

    def always_fail(e):
        raise RuntimeError("x")

    b.subscribe(
        SubscribeOptions(
            subscriber=_source(),
            event_types=[EventType.TASK_CREATED],
            handler=always_fail,
            retry_policy=RetryPolicy(maxAttempts=1),  # immediate DLQ
        )
    )
    for _ in range(5):
        await b.publish(make_event())
    await b.drain()
    # Capacity 3 => oldest dropped, 3 remain.
    assert len(b.getDeadLetters()) == 3

    # Filter by classification.
    f = DeadLetterFilter(classification="TRANSIENT")
    assert len(b.getDeadLetters(filter=f)) == 3


async def test_dlq_replay_reconstructs_new_event():
    b = new_bus()
    await b.initialize()

    def always_fail(e):
        raise RuntimeError("x")

    b.subscribe(
        SubscribeOptions(
            subscriber=_source(),
            event_types=[EventType.TASK_CREATED],
            handler=always_fail,
            retry_policy=RetryPolicy(maxAttempts=1),
        )
    )
    ev = make_event()
    await b.publish(ev)
    await b.drain()
    entries = b.getDeadLetters()
    assert len(entries) == 1
    entry_id = entries[0].entryId
    before = len(b.getRecentEvents())
    res = await b.replayDeadLetter(entry_id)
    assert res.accepted
    after = b.getRecentEvents()
    assert len(after) == before + 1
    # The replayed event is NEW (different id) but preserves correlationId.
    replayed = after[-1]
    assert replayed.eventId != ev.eventId
    assert replayed.correlationId == ev.correlationId
    # Original event object is untouched (immutable by contract).
    assert ev.eventId != replayed.eventId


async def test_purge_dead_letters():
    b = new_bus()
    await b.initialize()

    def always_fail(e):
        raise RuntimeError("x")

    b.subscribe(
        SubscribeOptions(
            subscriber=_source(),
            event_types=[EventType.TASK_CREATED],
            handler=always_fail,
            retry_policy=RetryPolicy(maxAttempts=1),
        )
    )
    for _ in range(3):
        await b.publish(make_event())
    await b.drain()
    assert len(b.getDeadLetters()) == 3
    removed = b.purgeDeadLetters()
    assert removed == 3
    assert len(b.getDeadLetters()) == 0


async def test_retry_queue_overflow_goes_to_dlq():
    # retryQueueCapacity=1; first retry not due (large delay) stays in heap,
    # second failure must overflow the oldest retry into the DLQ.
    b = new_bus(EventBusConfig(retryQueueCapacity=1))
    await b.initialize()

    def always_fail(e):
        raise RuntimeError("x")

    rp = RetryPolicy(maxAttempts=3, baseDelayMs=10000, maxDelayMs=10000, jitter=False)
    sid_a = b.subscribe(
        SubscribeOptions(
            subscriber=_source("A"),
            event_types=[EventType.TASK_CREATED],
            handler=always_fail,
            retry_policy=rp,
        )
    )
    sid_b = b.subscribe(
        SubscribeOptions(
            subscriber=_source("B"),
            event_types=[EventType.TASK_FAILED],
            handler=always_fail,
            retry_policy=rp,
        )
    )
    await b.publish(make_event())  # A fails -> retry (not due)
    await b.drain()
    await b.publish(make_event(event_type=EventType.TASK_FAILED))  # B fails -> overflow
    await b.drain()
    dlq = b.getDeadLetters()
    assert len(dlq) >= 1
    # Overflow pulled the oldest pending retry into the DLQ (one of the two
    # subscriptions); exactly one retry remains in the bounded retry queue.
    assert dlq[0].subscriptionId in (sid_a, sid_b)
    assert b.getDiagnostics().retry_queue_size == 1


# ---------------------------------------------------------------------------
# subscription delegation
# ---------------------------------------------------------------------------


async def test_subscribe_and_lookup_delegates_to_manager():
    b = new_bus()
    await b.initialize()
    sid = b.subscribe(
        SubscribeOptions(
            subscriber=_source(), event_types=[EventType.TASK_CREATED],
            handler=lambda e: None,
        )
    )
    sub = b.getSubscription(sid)
    assert sub is not None
    assert sub.eventTypes == (EventType.TASK_CREATED,)
    assert len(b.listSubscriptions()) == 1


async def test_unsubscribe_by_id():
    b = new_bus()
    await b.initialize()
    sid = b.subscribe(
        SubscribeOptions(
            subscriber=_source(), event_types=[EventType.TASK_CREATED],
            handler=lambda e: None,
        )
    )
    removed = b.unsubscribe(UnsubscribeOptions(subscriptionId=sid))
    assert removed == 1
    assert b.getSubscription(sid) is None


async def test_unsubscribe_all():
    b = new_bus()
    await b.initialize()
    b.subscribe(
        SubscribeOptions(
            subscriber=_source(), event_types=[EventType.TASK_CREATED],
            handler=lambda e: None,
        )
    )
    b.subscribe(
        SubscribeOptions(
            subscriber=_source("W"), event_types=WILDCARD_TEST(),
            handler=lambda e: None,
        )
    )
    assert b.unsubscribe(UnsubscribeOptions(all_=True)) == 2


def WILDCARD_TEST() -> object:
    from aios.events.core.subscription import WILDCARD

    return WILDCARD


# ---------------------------------------------------------------------------
# event history
# ---------------------------------------------------------------------------


async def test_event_history_queries():
    b = new_bus()
    await b.initialize()
    ev = make_event()
    await b.publish(ev)
    assert b.getEvent(ev.eventId) is not None
    assert len(b.getEventsByCorrelationId(ev.correlationId)) == 1
    assert len(b.getEventsByType(EventType.TASK_CREATED)) == 1
    assert len(b.getRecentEvents()) == 1


async def test_history_capacity_bounded():
    b = new_bus(EventBusConfig(historyCapacity=5))
    await b.initialize()
    for i in range(10):
        await b.publish(make_event(payload={"i": i}))
    assert len(b.getRecentEvents()) == 5


# ---------------------------------------------------------------------------
# replay (v1.0 memory-only)
# ---------------------------------------------------------------------------


async def test_replay_dry_run_no_handlers():
    b = new_bus()
    await b.initialize()
    called = []
    b.subscribe(
        SubscribeOptions(
            subscriber=_source(),
            event_types=[EventType.TASK_CREATED],
            handler=lambda e: called.append(e.eventId),
        )
    )
    e1 = make_event()
    e2 = make_event()
    await b.publish(e1)
    await b.publish(e2)
    reconstructed = await b.replay(ReplayOptions(dryRun=True, newEventIds=True))
    assert len(reconstructed) == 2
    # dryRun never publishes, so handlers never run.
    assert called == []
    # reconstructed events have NEW ids but same correlationIds preserved.
    assert reconstructed[0].eventId != e1.eventId
    assert reconstructed[0].correlationId == e1.correlationId


async def test_replay_publishes_to_handlers():
    b = new_bus()
    await b.initialize()
    called = []
    b.subscribe(
        SubscribeOptions(
            subscriber=_source(),
            event_types=[EventType.TASK_CREATED],
            handler=lambda e: called.append(e.eventId),
        )
    )
    await b.publish(make_event())
    await b.replay(ReplayOptions(dryRun=False))
    # original publish (drained here) + replay re-publish each invoke handler.
    await b.drain()
    assert len(called) == 2


# ---------------------------------------------------------------------------
# recursive / loop protection
# ---------------------------------------------------------------------------


async def test_recursive_event_detection_per_correlation():
    b = new_bus(EventBusConfig(maxDispatchDepth=2, publishQueueCapacity=50))
    await b.initialize()
    corr = uuid7()
    calls = []

    async def republisher(e):
        calls.append(e.eventId)
        if len(calls) < 10:
            # Re-publish a fresh event with the SAME correlationId -> loop.
            await b.publish(make_event(correlation_id=corr))

    b.subscribe(
        SubscribeOptions(
            subscriber=_source(),
            event_types=[EventType.TASK_CREATED],
            handler=republisher,
            handler_type="async",
        )
    )
    await b.publish(make_event(correlation_id=corr))
    await b.drain()
    # Depth capped at 2; the 3rd dispatch of this correlationId is blocked.
    assert len(calls) == 2
    assert b.getMetrics().recursive_events >= 1


# ---------------------------------------------------------------------------
# observability / metrics / diagnostics
# ---------------------------------------------------------------------------


async def test_metrics_and_diagnostics_shapes():
    b = new_bus()
    await b.initialize()
    calls = []
    b.subscribe(
        SubscribeOptions(
            subscriber=_source(),
            event_types=[EventType.TASK_CREATED],
            handler=lambda e: calls.append(e.eventId),
        )
    )
    await b.publish(make_event())
    await b.drain()
    m = b.getMetrics()
    assert isinstance(m, EventBusMetrics)
    assert m.published == 1
    assert m.dispatched == 1
    assert m.delivered == 1
    d = b.getDiagnostics()
    assert isinstance(d, EventBusDiagnostics)
    assert set(d.queue_depths.keys()) == {
        "CRITICAL", "HIGH", "NORMAL", "LOW", "BACKGROUND"
    }
    assert d.subscription_count == 1


async def test_diagnostic_hook_receives_recursive_signal():
    seen = []
    b = new_bus(
        EventBusConfig(maxDispatchDepth=2, publishQueueCapacity=50),
        diagnostic_hook=lambda name, payload: seen.append(name),
    )
    await b.initialize()
    corr = uuid7()
    calls = []

    async def republisher(e):
        calls.append(e.eventId)
        if len(calls) < 10:
            await b.publish(make_event(correlation_id=corr))

    b.subscribe(
        SubscribeOptions(
            subscriber=_source(),
            event_types=[EventType.TASK_CREATED],
            handler=republisher,
            handler_type="async",
        )
    )
    await b.publish(make_event(correlation_id=corr))
    await b.drain()
    assert "RecursiveEventDetected" in seen


# ---------------------------------------------------------------------------
# shutdown completes only after drain (no fake completion)
# ---------------------------------------------------------------------------


async def test_shutdown_drains_queued_events():
    b = new_bus()
    await b.initialize()
    called = []
    b.subscribe(
        SubscribeOptions(
            subscriber=_source(),
            event_types=[EventType.TASK_CREATED],
            handler=lambda e: called.append(e.eventId),
        )
    )
    await b.publish(make_event())
    # Not yet drained; shutdown must drain before reporting SHUTDOWN.
    state = await b.shutdown()
    assert state is EventBusState.SHUTDOWN
    assert len(called) == 1  # queued event was drained during shutdown


async def test_publish_after_shutdown_rejected():
    b = new_bus()
    await b.initialize()
    await b.shutdown()
    res = await b.publish(make_event())
    assert res.status is PublishStatus.REJECTED_SHUTDOWN
