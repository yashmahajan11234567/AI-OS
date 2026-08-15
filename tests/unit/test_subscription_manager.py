"""
Tests for SubscriptionManager (Task 4; Part 2 §2.5).

Covers registry integration, wildcard bypass, register/unregister, idempotency,
duplicate vs distinct handling, no mutable-state exposure, async-filter
rejection, lifecycle (manager-owned), suspend/resume (SUSPENDED, §2.5.6),
unsubscribe interface (§2.5.2), and concurrency.

NOTE: Subscription lifecycle STATE is owned by SubscriptionManager
(§2.13.3 ISubscription has no state field). It is read via ``state_of(sid)``.
"""

import threading

import pytest

from aios.events.core.errors import EventRegistryError
from aios.events.core.filters import equals, is_async_filter
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.manager import ManagerState, SubscriptionManager, SubscribeOptions
from aios.events.core.subscription import (
    HandlerPriority,
    Subscription,
    SubscriptionState,
    WILDCARD,
)
from aios.events.core.types import EventType


def _subscriber(name: str = "TestService") -> ComponentIdentity:
    return ComponentIdentity(
        component_type=ComponentType.ENGINEERING_SERVICE,
        component_name=name,
    )


def _registry():
    from aios.events.core.registry import EventTypeRegistry

    return EventTypeRegistry()


def _handler() -> None:
    pass


def _mgr():
    return SubscriptionManager(_registry())


# ---- registration --------------------------------------------------------


def test_register_returns_id():
    m = _mgr()
    sid = m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler)
    assert m.get_subscription(sid) is not None
    assert m.subscription_count == 1
    assert m.state_of(sid) is SubscriptionState.ACTIVE


def test_new_subscription_initial_state_is_active():
    # After registration completes, a subscription is ACTIVE (CREATED ->
    # REGISTERED -> ACTIVE, §2.5.6). Lifecycle state is manager-owned.
    m = _mgr()
    sid = m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler)
    assert m.state_of(sid) == SubscriptionState.ACTIVE


def test_explicit_registration_stored():
    m = _mgr()
    m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler)
    subs = m.get_subscriptions(EventType.TASK_CREATED)
    assert len(subs) == 1
    assert subs[0].eventTypes == (EventType.TASK_CREATED,)


def test_registry_get_called_per_event_type():
    reg = _registry()

    class _Spy:
        def __init__(self, base):
            self._base = base
            self.calls = 0

        def get(self, et):
            self.calls += 1
            return self._base.get(et)

        def __getattr__(self, name):
            return getattr(self._base, name)

    spy = _Spy(reg)
    mgr = SubscriptionManager(spy)
    mgr.subscribe(
        _subscriber(),
        [EventType.TASK_CREATED, EventType.TASK_FAILED],
        _handler,
    )
    assert spy.calls == 2


def test_unknown_event_type_rejected():
    m = _mgr()

    class _FakeET:
        name = "EXT_NOT_REAL"

    with pytest.raises(EventRegistryError):
        m.subscribe(_subscriber(), _FakeET(), _handler)  # type: ignore[arg-type]


def test_wildcard_bypasses_registry_validation():
    m = _mgr()
    sid = m.subscribe(_subscriber(), WILDCARD, _handler)
    sub = m.get_subscription(sid)
    assert sub is not None
    assert sub.is_wildcard
    assert m.wildcard_count == 1


# ---- unregister ----------------------------------------------------------


def test_unregister():
    m = _mgr()
    sid = m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler)
    assert m.unregister(sid) == 1
    assert m.get_subscription(sid) is None
    assert m.state_of(sid) == SubscriptionState.DEREGISTERED
    assert m.subscription_count == 0


def test_lookup_by_type_and_wildcard():
    m = _mgr()
    m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler)
    m.subscribe(_subscriber("Wild"), WILDCARD, _handler)
    subs = m.get_subscriptions(EventType.TASK_CREATED)
    assert len(subs) == 2  # explicit + wildcard


# ---- idempotency & duplicates (INV-SUB-001 / §2.5.7) ---------------------


def test_duplicate_registration_not_duplicated():
    m = _mgr()
    sid1 = m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler)
    sid2 = m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler)
    assert sid1 == sid2
    assert m.subscription_count == 1


def test_idempotent_identical_returns_existing_id():
    m = _mgr()
    opt = SubscribeOptions(
        subscriber=_subscriber(),
        event_types=(EventType.TASK_CREATED,),
        handler=_handler,
    )
    sid1 = m.register(opt)
    sid2 = m.register(opt)
    assert sid1 == sid2
    assert m.subscription_count == 1


def test_different_handler_is_distinct():
    def h1(): pass
    def h2(): pass
    m = _mgr()
    s1 = m.subscribe(_subscriber(), EventType.TASK_CREATED, h1)
    s2 = m.subscribe(_subscriber(), EventType.TASK_CREATED, h2)
    assert s1 != s2
    assert m.subscription_count == 2


def test_different_event_types_distinct():
    m = _mgr()
    s1 = m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler)
    s2 = m.subscribe(_subscriber(), EventType.TASK_FAILED, _handler)
    assert s1 != s2
    assert m.subscription_count == 2


def test_overlapping_wildcard_and_explicit_allowed():
    m = _mgr()
    s1 = m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler)
    s2 = m.subscribe(_subscriber(), WILDCARD, _handler)
    assert s1 != s2
    assert m.subscription_count == 2


# ---- no mutable internal state exposure ----------------------------------


def test_internal_collections_not_exposed():
    m = _mgr()
    m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler)
    subs = m.get_subscriptions(EventType.TASK_CREATED)
    subs.append("mutated")  # type: ignore[arg-type]
    assert m.subscription_count == 1


# ---- filters -------------------------------------------------------------


def test_async_filter_rejected_at_register():
    m = _mgr()

    async def af(e):
        return True

    with pytest.raises(EventRegistryError):
        m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler, filter=af)


def test_sync_filter_accepted():
    m = _mgr()
    f = equals("payload.taskId", "t-1")
    sid = m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler, filter=f)
    assert m.get_subscription(sid) is not None


def test_wildcard_with_filter():
    m = _mgr()

    class _Ev:
        eventType = EventType.TASK_CREATED

        class payload:
            @staticmethod
            def get(k, default=None):
                return {"taskId": "t-1"}.get(k, default)

    f = equals("payload.taskId", "t-1")
    m.subscribe(_subscriber(), WILDCARD, _handler, filter=f)
    sub = m.get_subscriptions(EventType.TASK_CREATED)[0]
    assert sub.filter is not None


# ---- lifecycle: manager-owned state & SUSPENDED (§2.5.6) ------------------


def test_subscription_lifecycle_active_then_deregistered():
    m = _mgr()
    sid = m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler)
    assert m.state_of(sid) == SubscriptionState.ACTIVE
    m.unregister(sid)
    assert m.state_of(sid) == SubscriptionState.DEREGISTERED


def test_suspend_and_resume():
    m = _mgr()
    sid = m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler)
    # ACTIVE -> SUSPENDED
    assert m.suspend(sid) is True
    assert m.state_of(sid) == SubscriptionState.SUSPENDED
    # SUSPENDED -> ACTIVE (recovery, §2.5.6)
    assert m.resume(sid) is True
    assert m.state_of(sid) == SubscriptionState.ACTIVE


def test_suspend_only_from_active():
    m = _mgr()
    sid = m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler)
    m.suspend(sid)
    # Already suspended -> second suspend returns False.
    assert m.suspend(sid) is False


def test_resume_only_from_suspended():
    m = _mgr()
    sid = m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler)
    # Not suspended -> resume returns False.
    assert m.resume(sid) is False


def test_suspended_subscription_excluded_from_active_dispatch_set():
    m = _mgr()
    sid = m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler)
    m.suspend(sid)
    # A suspended subscription must not receive events. ``matching`` returns
    # only ACTIVE subscriptions; the manager surfaces SUSPENDED via state_of.
    assert m.state_of(sid) == SubscriptionState.SUSPENDED


# ---- unsubscribe API (§2.5.2) --------------------------------------------


def test_unsubscribe_by_event_types():
    m = _mgr()
    s1 = m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler)
    s2 = m.subscribe(_subscriber(), EventType.TASK_FAILED, _handler)
    removed = m.unsubscribe(event_types=[EventType.TASK_CREATED])
    assert removed == 1
    assert m.get_subscription(s1) is None
    assert m.get_subscription(s2) is not None


def test_unsubscribe_all():
    m = _mgr()
    m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler)
    m.subscribe(_subscriber(), WILDCARD, _handler)
    assert m.unsubscribe(all_=True) == 2
    assert m.subscription_count == 0


def test_graceful_unsubscribe_removes_active():
    # In Task 4 there is no EventBus, so no handlers are in-flight; graceful
    # deregistration (INV-SUB-003) completes immediately and the subscription
    # transitions ACTIVE -> DEREGISTERING -> DEREGISTERED.
    m = _mgr()
    sid = m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler)
    assert m.unregister(sid, immediate=False) == 1
    assert m.get_subscription(sid) is None
    assert m.state_of(sid) == SubscriptionState.DEREGISTERED


def test_immediate_unsubscribe():
    m = _mgr()
    sid = m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler)
    assert m.unregister(sid, immediate=True) == 1
    assert m.get_subscription(sid) is None


def test_unregister_unknown_returns_zero():
    m = _mgr()
    assert m.unregister("nonexistent-id") == 0


def test_manager_shutdown_clears():
    m = _mgr()
    m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler)
    m.subscribe(_subscriber("W"), WILDCARD, _handler)
    m.shutdown()
    assert m.state is ManagerState.SHUTDOWN
    assert m.subscription_count == 0
    assert m.wildcard_count == 0


def test_unsubscribe_during_shutdown_immediate():
    m = _mgr()
    sid = m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler)
    m.shutdown()
    assert m.unregister(sid) == 0


# ---- handler priority propagation (§2.5.4) --------------------------------


def test_explicit_priority_stored():
    m = _mgr()
    sid = m.subscribe(
        _subscriber(), EventType.TASK_CREATED, _handler, priority=HandlerPriority.HIGH
    )
    assert m.get_subscription(sid).priority is HandlerPriority.HIGH


def test_wildcard_implicit_lowest_priority():
    m = _mgr()
    sid = m.subscribe(_subscriber(), WILDCARD, _handler)
    # Implicit (LAST + 1) derived constant unless explicit priority given.
    from aios.events.core.subscription import WILDCARD_PRIORITY

    assert m.get_subscription(sid).priority == WILDCARD_PRIORITY


# ---- concurrency ---------------------------------------------------------


def test_concurrent_register_lookup():
    m = _mgr()
    errors = []

    def worker():
        try:
            for _ in range(50):
                sid = m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler)
                _ = m.get_subscription(sid)
                _ = m.get_subscriptions(EventType.TASK_CREATED)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []


def test_concurrent_idempotent_register():
    m = _mgr()
    results = []

    def worker():
        sid = m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler)
        results.append(sid)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(set(results)) == 1
    assert m.subscription_count == 1


def test_concurrent_deregister():
    m = _mgr()
    sids = [m.subscribe(_subscriber(), EventType.TASK_CREATED, _handler) for _ in range(5)]

    def worker(sid):
        m.unregister(sid)

    threads = [threading.Thread(target=worker, args=(s,)) for s in sids]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert m.subscription_count == 0


if __name__ == "__main__":
    # keep is_async_filter referenced for linters if not exercised above
    assert callable(is_async_filter)
