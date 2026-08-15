"""
Tests for the Subscription value object (Task 4; Part 2 §2.13.3, §2.5.4).

Covers construction, validation, UUIDv7 id, immutability, equality semantics,
handler-priority conformance (§2.5.4 / §2.14.2), eventTypes type safety &
deep immutability, metadata deep immutability, RetryPolicy conformance (§2.5.8),
wildcard flag, event-type matching, and idempotency identity keying
(INV-SUB-011).

Lifecycle *state* is intentionally NOT a field of Subscription (§2.13.3
ISubscription defines no state); it is owned by SubscriptionManager. Lifecycle
tests live in test_subscription_manager.py.
"""

import uuid

import pytest

from aios.events.core.errors import EventRegistryError
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.ids import is_uuid7, uuid7
from aios.events.core.subscription import (
    HandlerPriority,
    RetryPolicy,
    Subscription,
    SubscriptionState,
    WILDCARD,
    WILDCARD_PRIORITY,
)
from aios.events.core.types import EventType

_EVENT_TYPES_MODULE = "aios.events.core.types"


def _subscriber(name: str = "TestService") -> ComponentIdentity:
    return ComponentIdentity(
        component_type=ComponentType.ENGINEERING_SERVICE,
        component_name=name,
    )


def _handler() -> None:
    pass


def _make(event_types=EventType.TASK_CREATED, handler=None, **kw) -> Subscription:
    return Subscription.create(
        subscriptionId=uuid7(),
        subscriber=_subscriber(),
        eventTypes=event_types,
        handler=handler or _handler,
        **kw,
    )


# 1. valid construction
def test_valid_construction():
    sub = _make()
    assert isinstance(sub, Subscription)


# 2. required-field validation
def test_non_uuid7_id_rejected():
    with pytest.raises(EventRegistryError):
        _make(subscriptionId=uuid.uuid4())  # not v7


def test_non_component_identity_subscriber_rejected():
    with pytest.raises(EventRegistryError):
        Subscription.create(
            subscriptionId=uuid7(),
            subscriber="not-an-identity",  # type: ignore[arg-type]
            eventTypes=(EventType.TASK_CREATED,),
            handler=_handler,
        )


def test_empty_event_types_rejected():
    with pytest.raises(EventRegistryError):
        _make(event_types=())


def test_bad_handler_type_rejected():
    with pytest.raises(EventRegistryError):
        _make(handlerType="weird")


def test_non_callable_handler_rejected():
    with pytest.raises(EventRegistryError):
        _make(handler=123)  # type: ignore[arg-type]


# 3. UUIDv7 subscription ID
def test_subscription_id_is_uuid7():
    sub = _make()
    assert isinstance(sub.subscriptionId, uuid.UUID)
    assert is_uuid7(sub.subscriptionId)


# 4. immutability (BLOCKING FIX 3: frozen, no object.__setattr__ escape)
def test_subscription_is_immutable():
    sub = _make()
    with pytest.raises((AttributeError, TypeError)):
        sub.priority = 1  # type: ignore[misc]
    with pytest.raises((AttributeError, TypeError)):
        sub.metadata = {}  # type: ignore[misc]


# Subscription has NO lifecycle state field (§2.13.3) — state lives in manager.
def test_subscription_has_no_state_field():
    sub = _make()
    assert not hasattr(sub, "state")


# 5. equality/identity semantics
def test_equality_by_subscription_id():
    sid = uuid7()
    a = _make(subscriptionId=sid)
    b = _make(subscriptionId=sid)
    assert a == b
    assert hash(a) == hash(b)


def test_different_ids_not_equal():
    a = _make()
    b = _make()
    assert a != b


# ===== BLOCKING FIX 1 — HandlerPriority conformance (§2.5.4 / §2.14.2) =====


def test_handler_priority_every_valid_level():
    for lvl in HandlerPriority:
        sub = _make(priority=lvl)
        assert sub.priority is lvl
        assert isinstance(sub.priority, HandlerPriority)


def test_handler_priority_accepts_equivalent_int_of_level():
    # The integer equal to a defined HandlerPriority level is accepted.
    sub = _make(priority=HandlerPriority.NORMAL.value)
    assert sub.priority == HandlerPriority.NORMAL


def test_handler_priority_invalid_arbitrary_int_rejected():
    # Arbitrary integers (e.g. 250, 999, -1) are PROHIBITED (§2.14.2 fixed 5
    # levels).
    for bad in (250, 999, -1, 7, 5000):
        with pytest.raises(EventRegistryError):
            _make(priority=bad)


def test_handler_priority_ordering():
    assert HandlerPriority.FIRST < HandlerPriority.HIGH < HandlerPriority.NORMAL
    assert HandlerPriority.NORMAL < HandlerPriority.LOW < HandlerPriority.LAST
    assert HandlerPriority.LAST < WILDCARD_PRIORITY  # LAST + 1


# ===== BLOCKING FIX 4 — eventTypes type safety & deep immutability =====


def test_event_types_normalized_to_tuple():
    src = [EventType.TASK_CREATED, EventType.WORKFLOW_STARTED]
    sub = _make(event_types=src)
    assert isinstance(sub.eventTypes, tuple)
    assert sub.eventTypes == tuple(src)


def test_input_list_cannot_mutate_subscription():
    src = [EventType.TASK_CREATED, EventType.WORKFLOW_STARTED]
    sub = _make(event_types=src)
    src.append(EventType.TASK_FAILED)
    assert sub.eventTypes == (EventType.TASK_CREATED, EventType.WORKFLOW_STARTED)
    assert len(sub.eventTypes) == 2


def test_stored_event_types_immutable():
    sub = _make(event_types=[EventType.TASK_CREATED, EventType.TASK_FAILED])
    with pytest.raises((AttributeError, TypeError)):
        sub.eventTypes[0] = EventType.TASK_FAILED  # type: ignore[index]


def test_invalid_event_type_member_rejected():
    with pytest.raises(EventRegistryError):
        Subscription.create(
            subscriptionId=uuid7(),
            subscriber=_subscriber(),
            eventTypes=(EventType.TASK_CREATED, "NOT_AN_EVENT_TYPE"),  # type: ignore[list-item]
            handler=_handler,
        )


def test_non_eventtype_object_rejected():
    with pytest.raises(EventRegistryError):
        Subscription.create(
            subscriptionId=uuid7(),
            subscriber=_subscriber(),
            eventTypes=("TASK_CREATED",),  # strings are not EventType members
            handler=_handler,
        )


def test_wildcard_distinct_from_empty():
    w = _make(event_types=WILDCARD)
    assert w.is_wildcard
    with pytest.raises(EventRegistryError):
        _make(event_types=())


# ===== BLOCKING FIX 6 — metadata deep immutability =====


def test_metadata_nested_dict_immutable():
    md = {"a": {"b": 1}, "c": [1, 2, 3]}
    sub = _make(metadata=md)
    with pytest.raises((TypeError, AttributeError)):
        sub.metadata["a"]["b"] = 99  # type: ignore[index]
    with pytest.raises((TypeError, AttributeError)):
        sub.metadata["c"].append(4)  # type: ignore[attr-defined]


def test_metadata_input_mutation_does_not_affect_subscription():
    md = {"k": [1, 2]}
    sub = _make(metadata=md)
    md["k"].append(3)  # type: ignore[union-attr]
    md["new"] = 9  # type: ignore[index]
    assert list(sub.metadata["k"]) == [1, 2]
    assert "new" not in sub.metadata


def test_metadata_default_is_empty_and_immutable():
    sub = _make()
    assert "anything" not in sub.metadata
    with pytest.raises((TypeError, AttributeError)):
        sub.metadata["x"] = 1  # type: ignore[index]


# ===== BLOCKING FIX 5 — RetryPolicy conformance (§2.5.8) =====


def test_retry_policy_defaults():
    sub = _make(retryPolicy=None)
    assert sub.retryPolicy is None
    rp = RetryPolicy()
    assert rp.maxAttempts == 3
    assert rp.baseDelayMs == 1000
    assert rp.maxDelayMs == 30000
    assert rp.backoffMultiplier == 2.0
    assert rp.jitter is True
    assert rp.retryableErrors == ("TRANSIENT", "TIMEOUT", "UNAVAILABLE")


def test_retry_policy_from_dict():
    rp = RetryPolicy.create({"maxAttempts": 5, "jitter": False})
    assert rp.maxAttempts == 5
    assert rp.jitter is False
    assert rp.backoffMultiplier == 2.0


def test_retry_policy_immutable_errors():
    rp = RetryPolicy()
    with pytest.raises((TypeError, AttributeError)):
        rp.maxAttempts = 7  # type: ignore[misc]


def test_retry_policy_invalid_max_attempts_rejected():
    with pytest.raises(EventRegistryError):
        RetryPolicy(maxAttempts=0)
    with pytest.raises(EventRegistryError):
        RetryPolicy(maxAttempts=11)  # §2.14.1 maxAttempts <= 10


def test_retry_policy_invalid_type_rejected():
    with pytest.raises(EventRegistryError):
        _make(retryPolicy="not-a-policy")  # type: ignore[arg-type]


def test_retry_policy_attached_to_subscription():
    rp = RetryPolicy(maxAttempts=5)
    sub = _make(retryPolicy=rp)
    assert sub.retryPolicy is rp


# ===== wildcard flag + matching =====


def test_wildcard_flag_and_matching():
    sub = _make(event_types=WILDCARD)
    assert sub.is_wildcard
    assert sub.matches_event_type(EventType.KERNEL_READY)
    assert sub.matches_event_type(EventType.TASK_CREATED)


def test_explicit_matching_only_declared_types():
    sub = _make(event_types=EventType.TASK_CREATED)
    assert not sub.is_wildcard
    assert sub.matches_event_type(EventType.TASK_CREATED)
    assert not sub.matches_event_type(EventType.WORKFLOW_STARTED)


def test_identity_key_order_independent():
    a = _make(event_types=(EventType.TASK_CREATED, EventType.TASK_FAILED))
    b = _make(event_types=(EventType.TASK_FAILED, EventType.TASK_CREATED))
    # Same subscriber + same handler -> identical identity key regardless of order.
    assert a.identity_key() == b.identity_key()


def test_handler_identity_in_key():
    def h1(): pass
    def h2(): pass
    a = _make(handler=h1)
    b = _make(handler=h2)
    assert a.identity_key() != b.identity_key()


def test_handler_identity_by_reference_uses_id():
    # INV-SUB-011: handler identity by reference -> Python id().
    def h(): pass
    sub = _make(handler=h)
    assert sub.identity_key()[-1] == id(h)
