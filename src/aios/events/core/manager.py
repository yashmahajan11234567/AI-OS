"""
SubscriptionManager (Part 2 §2.5.1–§2.5.8, §2.4.5 Subscriber Registry).

Owns the mapping ``EventType -> set[Subscription]`` plus a separate list of
wildcard subscriptions, and drives the subscription lifecycle (§2.5.6). It
integrates with the existing ``EventTypeRegistry`` to validate explicit
EventTypes at registration (§2.5.1 step 1) and bypasses that validation for
wildcards (§2.5.5).

CRITICAL DESIGN DECISION (Task 4 fix — immutability, §2.13.3):
  The ``Subscription`` value object is IMMUTABLE and carries NO lifecycle
  ``state`` (§2.13.3 ISubscription defines no state field). Therefore the
  lifecycle state is owned HERE, in ``SubscriptionManager`` (``_lifecycle``),
  and is mutated only by the manager — never via ``object.__setattr__`` on the
  frozen Subscription. This preserves the immutability contract.

Thread safety: a single ``RLock`` guards all mutable state.

Authoritative contracts:
  * Registration / idempotency ...... Part 2 §2.5.1 / §2.5.7 / INV-SUB-001/011
  * Deregistration / drain .......... Part 2 §2.5.2 / INV-SUB-003/004
  * Wildcards ....................... Part 2 §2.5.5 / INV-SUB-009
  * Filter purity ................... Part 2 §2.5.3 / INV-SUB-005
  * Lifecycle ....................... Part 2 §2.5.6
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Optional

from aios.events.core.errors import EventRegistryError
from aios.events.core.filters import EventFilter, is_async_filter
from aios.events.core.subscription import (
    HandlerPriority,
    Subscription,
    SubscriptionState,
    WILDCARD,
    WILDCARD_PRIORITY,
)
from aios.events.core.types import EventType

if TYPE_CHECKING:
    from aios.events.core.event import Event
    from aios.events.core.identity import ComponentIdentity
    from aios.events.core.registry import EventTypeRegistry

# DERIVED constant: wildcard implicit lowest priority (Part 2 §2.5.5, LAST + 1).
_WILDCARD_PRIORITY = WILDCARD_PRIORITY


class ManagerState(str, Enum):
    """Lifecycle of the SubscriptionManager (Part 2 §2.5.6 analog).

    INITIALIZED -> RUNNING -> SHUTTING_DOWN -> SHUTDOWN. During SHUTTING_DOWN,
    deregistration is immediate (no graceful wait, INV-SUB-004 analog).
    """

    INITIALIZED = "INITIALIZED"
    RUNNING = "RUNNING"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    SHUTDOWN = "SHUTDOWN"


@dataclass(frozen=True)
class SubscribeOptions:
    """Normalized registration options (Part 2 §2.5.1 SubscribeOptions)."""

    subscriber: "ComponentIdentity"
    event_types: Any  # '*' or tuple[EventType, ...]
    handler: Callable[["Event"], Any]
    handler_type: str = "sync"
    filter: Optional[EventFilter] = None
    priority: Optional[Any] = None  # HandlerPriority (or None -> NORMAL)
    max_concurrency: int = 1
    timeout_ms: int = 30000
    retry_policy: Optional[Any] = None
    metadata: Optional[dict[str, Any]] = None


class SubscriptionManager:
    """Registry of subscriptions and the subscription lifecycle driver.

    Public API mirrors the architecture's subscribe/unsubscribe intent without
    implementing EventBus dispatch:
      * ``register(options)`` / ``subscribe(...)`` -> subscriptionId (idempotent)
      * ``unsubscribe(subscription_id | event_types | all_)`` -> removed count
      * ``get_subscriptions(event_type)`` / ``matching(event)`` -> lookups
      * lifecycle: ``suspend(sid)`` / ``resume(sid)`` (SUSPENDED recovery, §2.5.6)

    NOTE: ``enter_dispatch`` / ``exit_dispatch`` are intentionally NOT part of
    this API. Part 2 defines no such hooks; in-flight handler tracking is an
    EventBus concern. In Task 4 (no EventBus) there are no in-flight handlers,
    so graceful deregistration (INV-SUB-003) removes immediately after marking
    DEREGISTERING.
    """

    def __init__(
        self,
        registry: "EventTypeRegistry",
        default_priority: Any = HandlerPriority.NORMAL,
    ) -> None:
        if not hasattr(registry, "get"):
            raise EventRegistryError("SubscriptionManager requires an EventTypeRegistry.")
        self._registry = registry
        self._default_priority = default_priority
        self._lock = threading.RLock()
        # EventType -> set of subscriptions (explicit, non-wildcard).
        self._by_type: dict[EventType, set[Subscription]] = {}
        # Wildcard subscriptions.
        self._wildcards: list[Subscription] = []
        # subscriptionId -> Subscription (fast lookup for unregister).
        self._by_id: dict[Any, Subscription] = {}
        # identity tuple -> subscriptionId (idempotency, INV-SUB-001/011).
        self._by_identity: dict[tuple[Any, ...], Any] = {}
        # subscriptionId -> lifecycle state (OWNED BY MANAGER, not the object).
        self._lifecycle: dict[Any, SubscriptionState] = {}
        self._state = ManagerState.INITIALIZED
        self._state = ManagerState.RUNNING

    # --- helpers ----------------------------------------------------------

    @staticmethod
    def _normalize_event_types(
        event_types: "EventType | list[EventType] | str",
    ) -> Any:
        if event_types == WILDCARD:
            return WILDCARD
        if isinstance(event_types, EventType):
            return (event_types,)
        if isinstance(event_types, (list, tuple, set)):
            ets = tuple(event_types)
            if not ets:
                raise EventRegistryError(
                    "event_types MUST be '*' or a non-empty collection of EventType."
                )
            return ets
        raise EventRegistryError(
            "event_types MUST be '*', an EventType, or a collection of EventType."
        )

    # --- registration -----------------------------------------------------

    def register(self, options: SubscribeOptions) -> Any:
        """Register a subscription (Part 2 §2.5.1). Idempotent per INV-SUB-001."""
        if not isinstance(options, SubscribeOptions):
            raise EventRegistryError("register() requires a SubscribeOptions.")

        event_types = options.event_types
        wildcard = event_types == WILDCARD

        # Async-filter rejection (INV-SUB-005): filters MUST be synchronous.
        if options.filter is not None:
            if is_async_filter(options.filter):
                raise EventRegistryError(
                    "Async filters are PROHIBITED (INV-SUB-005). The filter "
                    "function MUST be a synchronous, pure predicate."
                )

        # Explicit (non-wildcard) EventTypes MUST resolve in the registry
        # (§2.5.1 step 1). Wildcards bypass per-type validation (§2.5.5).
        if not wildcard:
            for et in event_types:
                reg = self._registry.get(et)
                if reg is None:
                    raise EventRegistryError(
                        f"EventType {et.name} is not registered in the "
                        f"EventTypeRegistry; cannot subscribe (INV-SUB-001)."
                    )

        if wildcard:
            priority = options.priority if options.priority is not None else _WILDCARD_PRIORITY
        else:
            priority = options.priority if options.priority is not None else self._default_priority

        # Build the immutable value object via the factory (normalizes
        # eventTypes to a tuple, deep-freezes metadata, validates priority &
        # retry policy). The lifecycle state is NOT part of the object.
        subscription = Subscription.create(
            subscriptionId=_uuid7(),
            subscriber=options.subscriber,
            eventTypes=event_types,
            handler=options.handler,
            filter=options.filter,
            handlerType=options.handler_type,
            priority=priority,
            maxConcurrency=options.max_concurrency,
            timeoutMs=options.timeout_ms,
            retryPolicy=options.retry_policy,
            metadata=options.metadata,
        )

        with self._lock:
            key = subscription.identity_key()
            existing_id = self._by_identity.get(key)
            if existing_id is not None:
                # Idempotent: return existing subscriptionId, do not duplicate.
                return existing_id
            sid = subscription.subscriptionId
            # CREATED -> REGISTERED -> ACTIVE (lifecycle owned by manager).
            self._lifecycle[sid] = SubscriptionState.CREATED
            self._by_id[sid] = subscription
            self._by_identity[key] = sid
            self._lifecycle[sid] = SubscriptionState.REGISTERED
            if wildcard:
                self._wildcards.append(subscription)
            else:
                for et in subscription.eventTypes:
                    self._by_type.setdefault(et, set()).add(subscription)
            self._lifecycle[sid] = SubscriptionState.ACTIVE
            return sid

    def subscribe(
        self,
        subscriber: "ComponentIdentity",
        event_types: "EventType | list[EventType] | str",
        handler: Callable[["Event"], Any],
        *,
        filter: Optional[EventFilter] = None,
        handler_type: str = "sync",
        priority: Optional[Any] = None,
        max_concurrency: int = 1,
        timeout_ms: int = 30000,
        retry_policy: Optional[Any] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Convenience wrapper over ``register`` (Part 2 §2.5.1)."""
        options = SubscribeOptions(
            subscriber=subscriber,
            event_types=self._normalize_event_types(event_types),
            handler=handler,
            handler_type=handler_type,
            filter=filter,
            priority=priority,
            max_concurrency=max_concurrency,
            timeout_ms=timeout_ms,
            retry_policy=retry_policy,
            metadata=metadata,
        )
        return self.register(options)

    # --- lookup -----------------------------------------------------------

    def get_subscription(self, subscription_id: Any) -> Optional[Subscription]:
        with self._lock:
            return self._by_id.get(subscription_id)

    def state_of(self, subscription_id: Any) -> Optional[SubscriptionState]:
        """Manager-owned lifecycle state for ``subscription_id`` (§2.5.6)."""
        with self._lock:
            return self._lifecycle.get(subscription_id)

    def get_subscriptions(self, event_type: EventType) -> list[Subscription]:
        """All explicit subscriptions for ``event_type`` (Part 2 §2.4.5 map)."""
        if not isinstance(event_type, EventType):
            raise EventRegistryError("get_subscriptions requires a canonical EventType.")
        with self._lock:
            explicit = list(self._by_type.get(event_type, set()))
            return explicit + list(self._wildcards)

    def matching(self, event: "Event") -> list[Subscription]:
        """Subscriptions that should receive ``event`` after filter evaluation.

        Returns explicit + wildcard subscriptions whose eventTypes include the
        event's type and whose filter (if any) passes. Filters are evaluated
        read-only against the Event (§2.5.3). A throwing filter is treated as a
        non-match for this event (§2.5.8: skip subscription for this event).
        """
        out: list[Subscription] = []
        for sub in self.get_subscriptions(event.eventType):
            if sub.filter is None or _safe_filter(sub.filter, event):
                out.append(sub)
        return out

    def list_all(self) -> list[Subscription]:
        with self._lock:
            return list(self._by_id.values())

    # --- lifecycle: suspend / resume (§2.5.6 SUSPENDED) --------------------

    def suspend(self, subscription_id: Any) -> bool:
        """Mark a live subscription SUSPENDED (handler error, §2.5.6).

        ACTIVE -> SUSPENDED. Returns False if the subscription is not ACTIVE.
        """
        with self._lock:
            st = self._lifecycle.get(subscription_id)
            if st is not SubscriptionState.ACTIVE:
                return False
            self._lifecycle[subscription_id] = SubscriptionState.SUSPENDED
            return True

    def resume(self, subscription_id: Any) -> bool:
        """Recover a SUSPENDED subscription to ACTIVE (§2.5.6 recovery)."""
        with self._lock:
            st = self._lifecycle.get(subscription_id)
            if st is not SubscriptionState.SUSPENDED:
                return False
            self._lifecycle[subscription_id] = SubscriptionState.ACTIVE
            return True

    # --- lifecycle: unsubscribe / drain ------------------------------------

    def unregister(self, subscription_id: Any, immediate: bool = False) -> int:
        """Deregister a subscription (Part 2 §2.5.2).

        Graceful (``immediate=False``): mark DEREGISTERING, then remove. In
        Task 4 there is no EventBus, so no handlers are in-flight; removal
        proceeds immediately (INV-SUB-003 satisfied trivially). During
        SHUTTING_DOWN, removal is immediate regardless (INV-SUB-004).
        """
        with self._lock:
            sub = self._by_id.get(subscription_id)
            if sub is None:
                return 0
            if self._lifecycle.get(subscription_id) in (
                SubscriptionState.DEREGISTERED,
            ):
                return 0
            self._lifecycle[subscription_id] = SubscriptionState.DEREGISTERING
            if not immediate and self._state is not ManagerState.SHUTTING_DOWN:
                # No in-flight handlers exist in Task 4; removal is immediate.
                pass
            self._remove_locked(sub)
            return 1

    def unsubscribe(
        self,
        subscription_id: Optional[Any] = None,
        event_types: Optional[list[EventType]] = None,
        all_: bool = False,
        immediate: bool = False,
    ) -> int:
        """Flexible deregistration (Part 2 §2.5.2 UnsubscribeOptions).

        NOTE: Part 2 §2.5.2 UnsubscribeOptions contains ONLY ``subscriptionId``,
        ``eventTypes``, and ``all``. There is NO ``subscriber`` field in the
        architectural interface, so it is not part of this API.
        """
        with self._lock:
            targets: list[Subscription] = []
            if subscription_id is not None:
                sub = self._by_id.get(subscription_id)
                if sub is not None:
                    targets.append(sub)
            if all_:
                targets.extend(self._by_id.values())
            if event_types:
                ets = set(event_types)
                targets.extend(
                    s
                    for s in self._by_id.values()
                    if not s.is_wildcard
                    and any(et in ets for et in s.eventTypes)
                )
            removed = 0
            for sub in targets:
                sid = sub.subscriptionId
                if self._lifecycle.get(sid) in (SubscriptionState.DEREGISTERED,):
                    continue
                self._lifecycle[sid] = SubscriptionState.DEREGISTERING
                self._remove_locked(sub)
                removed += 1
            return removed

    def _remove_locked(self, sub: Subscription) -> None:
        sid = sub.subscriptionId
        self._by_id.pop(sid, None)
        self._by_identity.pop(sub.identity_key(), None)
        self._lifecycle[sid] = SubscriptionState.DEREGISTERED
        if sub.is_wildcard:
            if sub in self._wildcards:
                self._wildcards.remove(sub)
        else:
            for et in sub.eventTypes:
                subs = self._by_type.get(et)
                if subs and sub in subs:
                    subs.discard(sub)
                    if not subs:
                        del self._by_type[et]

    # --- manager lifecycle ------------------------------------------------

    def shutdown(self) -> None:
        """Transition to SHUTTING_DOWN then SHUTDOWN (Part 2 §2.5.6)."""
        with self._lock:
            self._state = ManagerState.SHUTTING_DOWN
            # Immediate removal of all subscriptions during shutdown drain.
            for sub in list(self._by_id.values()):
                self._lifecycle[sub.subscriptionId] = SubscriptionState.DEREGISTERING
                self._remove_locked(sub)
            self._wildcards.clear()
            self._by_type.clear()
            self._by_identity.clear()
            self._state = ManagerState.SHUTDOWN

    @property
    def state(self) -> ManagerState:
        with self._lock:
            return self._state

    @property
    def subscription_count(self) -> int:
        with self._lock:
            return len(self._by_id)

    @property
    def wildcard_count(self) -> int:
        with self._lock:
            return len(self._wildcards)


def _safe_filter(filter_fn: EventFilter, event: "Event") -> bool:
    """Apply a filter; any exception => non-match (§2.5.8)."""
    try:
        return bool(filter_fn(event))
    except Exception:  # noqa: BLE001
        return False


def _uuid7() -> Any:
    from aios.events.core.ids import uuid7

    return uuid7()


__all__ = [
    "SubscriptionManager",
    "SubscribeOptions",
    "ManagerState",
]
