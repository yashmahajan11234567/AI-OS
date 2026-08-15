"""
Event filter DSL (Part 2 §2.5.3).

An ``EventFilter`` is a pure, synchronous predicate ``(event: Event) -> bool``.
The DSL provides eight declarative combinators that the future EventBus (or any
registrant) can compose: equals, notEquals, in, contains, matches, and, or, not.

Architectural constraints enforced here:
  * Filters operate on base contract fields + payload fields, with nested
    access via dot notation (e.g. ``payload.taskId``) — Part 2 §2.5.3.
  * Filters MUST be pure and synchronous (INV-SUB-005). We provide
    ``is_async_filter`` so registrants can reject async filters explicitly.
  * Filters MUST NOT mutate the Event. They only read.
  * Unknown field paths / missing values simply fail to match (do not raise),
    except ``matches`` which validates its regex at construction time.

No new error class is introduced; invalid filters reuse ``EventRegistryError``.
"""

from __future__ import annotations

import inspect
import re
from typing import TYPE_CHECKING, Any, Callable, Iterable

from aios.events.core.errors import EventRegistryError

if TYPE_CHECKING:
    from aios.events.core.event import Event

EventFilter = Callable[["Event"], bool]

_MISSING = object()


def is_async_filter(filter_fn: Any) -> bool:
    """Return True if ``filter_fn`` is an async/coroutine filter (INV-SUB-005).

    Async filters are prohibited; registrants use this to reject them before
    they ever reach the bus.
    """
    return inspect.iscoroutinefunction(filter_fn) or (
        callable(filter_fn) and inspect.iscoroutinefunction(getattr(filter_fn, "__call__", None))
    )


def _resolve(event: "Event", field: str) -> Any:
    """Resolve a dot-notation field path against an Event (§2.5.3).

    ``payload.taskId`` reads ``event.payload.get('taskId')`` (supporting deeper
    dotted payload paths). A bare ``payload`` yields the payload view. Any other
    name resolves against the Event's base-contract properties. Missing paths
    return ``_MISSING`` so callers can treat them as non-matches.
    """
    if field.startswith("payload"):
        rest = field[len("payload"):]
        if rest == "" or rest == ".":
            return getattr(event, "payload", _MISSING)
        cur: Any = getattr(event, "payload", None)
        for part in rest.lstrip(".").split("."):
            if cur is None:
                return _MISSING
            if isinstance(cur, dict):
                cur = cur.get(part, _MISSING)
            else:
                cur = getattr(cur, part, _MISSING)
        return cur
    return getattr(event, field, _MISSING)


class FilterDSL:
    """Declarative filter combinators (Part 2 §2.5.3 FilterDSL).

    Every combinator returns a synchronous ``EventFilter``. Combinators compose
    freely (and/or/not nest arbitrarily). Construction of ``matches`` compiles
    its pattern eagerly and raises on an invalid regex.
    """

    @staticmethod
    def equals(field: str, value: Any) -> EventFilter:
        def _f(event: "Event") -> bool:
            return _resolve(event, field) == value

        return _f

    @staticmethod
    def notEquals(field: str, value: Any) -> EventFilter:
        def _f(event: "Event") -> bool:
            return _resolve(event, field) != value

        return _f

    @staticmethod
    def in_(field: str, values: Iterable[Any]) -> EventFilter:
        value_set = list(values)

        def _f(event: "Event") -> bool:
            return _resolve(event, field) in value_set

        return _f

    @staticmethod
    def contains(field: str, substring: str) -> EventFilter:
        def _f(event: "Event") -> bool:
            val = _resolve(event, field)
            if val is _MISSING:
                return False
            if isinstance(val, str):
                return substring in val
            if isinstance(val, (list, tuple, set, dict)):
                return substring in val  # type: ignore[operator]
            return False

        return _f

    @staticmethod
    def matches(field: str, pattern: str) -> EventFilter:
        try:
            compiled = re.compile(pattern)
        except re.error as exc:
            raise EventRegistryError(
                f"Invalid regex pattern {pattern!r} for filter.matches: {exc}"
            ) from exc

        def _f(event: "Event") -> bool:
            val = _resolve(event, field)
            if val is _MISSING or not isinstance(val, str):
                return False
            return compiled.search(val) is not None

        return _f

    @staticmethod
    def and_(*filters: EventFilter) -> EventFilter:
        if not filters:
            raise EventRegistryError("FilterDSL.and_ requires at least one filter.")
        fs = list(filters)

        def _f(event: "Event") -> bool:
            return all(f(event) for f in fs)

        return _f

    @staticmethod
    def or_(*filters: EventFilter) -> EventFilter:
        if not filters:
            raise EventRegistryError("FilterDSL.or_ requires at least one filter.")
        fs = list(filters)

        def _f(event: "Event") -> bool:
            return any(f(event) for f in fs)

        return _f

    @staticmethod
    def not_(filter_fn: EventFilter) -> EventFilter:
        def _f(event: "Event") -> bool:
            return not filter_fn(event)

        return _f


# Module-level convenience mirroring the architectural DSL names.
def equals(field: str, value: Any) -> EventFilter:
    return FilterDSL.equals(field, value)


def notEquals(field: str, value: Any) -> EventFilter:
    return FilterDSL.notEquals(field, value)


def in_(field: str, values: Iterable[Any]) -> EventFilter:
    return FilterDSL.in_(field, values)


def contains(field: str, substring: str) -> EventFilter:
    return FilterDSL.contains(field, substring)


def matches(field: str, pattern: str) -> EventFilter:
    return FilterDSL.matches(field, pattern)


def and_(*filters: EventFilter) -> EventFilter:
    return FilterDSL.and_(*filters)


def or_(*filters: EventFilter) -> EventFilter:
    return FilterDSL.or_(*filters)


def not_(filter_fn: EventFilter) -> EventFilter:
    return FilterDSL.not_(filter_fn)


# Eight combinators in canonical order for documentation/tests.
COMBINATORS = (
    "equals",
    "notEquals",
    "in_",
    "contains",
    "matches",
    "and_",
    "or_",
    "not_",
)


__all__ = [
    "EventFilter",
    "FilterDSL",
    "is_async_filter",
    "equals",
    "notEquals",
    "in_",
    "contains",
    "matches",
    "and_",
    "or_",
    "not_",
    "COMBINATORS",
]
