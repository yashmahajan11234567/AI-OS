"""
Tests for the Event filter DSL (Task 4; Part 2 §2.5.3).

Covers all eight combinators, nested composition, evaluation against an Event,
invalid-filter rejection, async-filter detection, and filter purity.
"""

import asyncio

import pytest

from aios.events.core.errors import EventRegistryError
from aios.events.core.filters import (
    COMBINATORS,
    FilterDSL,
    and_,
    contains,
    equals,
    in_,
    is_async_filter,
    matches,
    not_,
    notEquals,
    or_,
)
from aios.events.core.types import EventType


def _make_event(event_type=EventType.TASK_CREATED, payload=None):
    """Build a minimal Event-like object the filters read via dot notation."""
    class _Payload:
        def __init__(self, data):
            self._d = data or {}
        def get(self, k, default=None):
            return self._d.get(k, default)

    class _Event:
        def __init__(self):
            self.eventType = event_type
            self.category = "control"
            self.source = "svc"
            self.priority = 2
            self.payload = _Payload({"taskId": "t-1", "tags": ["a", "b"], "note": "hello world"})
    return _Event()


# 18. all eight combinators present
def test_eight_combinators_exist():
    assert COMBINATORS == (
        "equals", "notEquals", "in_", "contains",
        "matches", "and_", "or_", "not_",
    )
    for name in COMBINATORS:
        assert hasattr(FilterDSL, name), name


# single combinator evaluation
def test_equals():
    ev = _make_event()
    assert equals("payload.taskId", "t-1")(ev) is True
    assert equals("payload.taskId", "nope")(ev) is False
    # base field
    assert equals("eventType", EventType.TASK_CREATED)(ev) is True


def test_not_equals():
    ev = _make_event()
    assert notEquals("payload.taskId", "x")(ev) is True
    assert notEquals("payload.taskId", "t-1")(ev) is False


def test_in():
    ev = _make_event()
    assert in_("payload.taskId", ["t-1", "t-2"])(ev) is True
    assert in_("payload.taskId", ["x"])(ev) is False


def test_contains():
    ev = _make_event()
    assert contains("payload.note", "world")(ev) is True
    assert contains("payload.tags", "a")(ev) is True
    assert contains("payload.note", "absent")(ev) is False


def test_matches():
    ev = _make_event()
    assert matches("payload.taskId", r"t-\d+")(ev) is True
    assert matches("payload.taskId", r"x-\d+")(ev) is False


def test_matches_invalid_regex_rejected():
    with pytest.raises(EventRegistryError):
        matches("payload.taskId", r"([invalid")


def test_and():
    ev = _make_event()
    f = and_(equals("payload.taskId", "t-1"), contains("payload.note", "world"))
    assert f(ev) is True
    assert and_(equals("payload.taskId", "t-1"), equals("payload.taskId", "x"))(ev) is False


def test_or():
    ev = _make_event()
    f = or_(equals("payload.taskId", "x"), contains("payload.note", "world"))
    assert f(ev) is True
    assert or_(equals("payload.taskId", "x"), equals("payload.taskId", "y"))(ev) is False


def test_not():
    ev = _make_event()
    assert not_(equals("payload.taskId", "x"))(ev) is True
    assert not_(equals("payload.taskId", "t-1"))(ev) is False


# 19. nested combinations
def test_nested_composition():
    ev = _make_event()
    f = and_(
        equals("payload.taskId", "t-1"),
        or_(
            contains("payload.note", "world"),
            in_("payload.taskId", ["z"]),
        ),
        not_(equals("payload.taskId", "zzz")),
    )
    assert f(ev) is True


def test_and_short_circuits_false():
    ev = _make_event()
    calls = {"n": 0}

    def counting(flag):
        def _f(e):
            calls["n"] += 1
            return flag
        return _f

    f = and_(counting(False), counting(True))
    assert f(ev) is False
    # second predicate not evaluated because first is False (short-circuit).
    assert calls["n"] == 1


# 20. filter evaluation behavior
def test_missing_field_does_not_match():
    ev = _make_event()
    assert equals("payload.missing", "x")(ev) is False
    assert contains("payload.missing", "x")(ev) is False
    assert matches("payload.missing", ".*")(ev) is False


# 21. invalid filters
def test_and_requires_at_least_one():
    with pytest.raises(EventRegistryError):
        and_()


def test_or_requires_at_least_one():
    with pytest.raises(EventRegistryError):
        or_()


# 22. async filter rejection
def test_async_filter_detected():
    async def af(e):
        return True
    assert is_async_filter(af) is True


def test_sync_filter_not_flagged_async():
    def sf(e):
        return True
    assert is_async_filter(sf) is False


def test_async_filter_rejected_by_manager_register(monkeypatch):
    # Manager.register rejects async filters (tested in manager suite); here we
    # assert is_async_filter is the gate used. End-to-end rejection lives in
    # test_subscription_manager.
    async def af(e):
        return True
    assert is_async_filter(af)


def test_async_method_filter_detected():
    class C:
        async def f(self, e):
            return True
    assert is_async_filter(C().f) is True


# 23. filter purity / determinism
def test_filter_is_deterministic():
    ev = _make_event()
    f = equals("payload.taskId", "t-1")
    assert f(ev) == f(ev)


def test_filters_do_not_mutate_event():
    ev = _make_event()
    f = contains("payload.note", "world")
    before = ev.payload.get("note")
    f(ev)
    assert ev.payload.get("note") == before
