"""
Subscription value object, handler-priority model, and retry policy
(Part 2 §2.13.3, §2.5.4, §2.5.5, §2.5.8).

A ``Subscription`` is an IMMUTABLE record (Part 2 §2.13.3 ISubscription). It
carries no lifecycle ``state`` — §2.13.3 lists no state field, and the
lifecycle (§2.5.6: CREATED -> REGISTERED -> ACTIVE -> DEREGISTERING ->
DEREGISTERED, with SUSPENDED on error recovery) is owned by the
SubscriptionManager. Keeping the value object frozen and stateless preserves
the immutability contract (INV-EVT-012 style) and makes the object safe to
hand to the future EventBus.

Authoritative contracts:
  * ISubscription fields ................ Part 2 §2.13.3 (NO state field)
  * HandlerPriority scale ............... Part 2 §2.5.4 (FIXED 5 levels,
                                          §2.14.2 prohibits adding levels)
  * Wildcard opt-in / priority .......... Part 2 §2.5.5 (implicit LAST + 1)
  * RetryPolicy ......................... Part 2 §2.5.8 (6 fields)
  * Idempotency identity tuple .......... Part 2 §2.5.7 / INV-SUB-011
  * Lifecycle ........................... Part 2 §2.5.6 (owned by manager)

This module does NOT implement EventBus dispatch.
"""

from __future__ import annotations

import datetime
import enum
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Callable, Optional

from aios.events.core.errors import EventRegistryError
from aios.events.core.identity import ComponentIdentity
from aios.events.core.ids import is_uuid7
from aios.events.core.types import EventType

if TYPE_CHECKING:
    from aios.events.core.filters import EventFilter

# Wildcard marker (Part 2 §2.5.5): eventTypes == '*' opts into all types.
WILDCARD = "*"


class HandlerPriority(int, enum.Enum):
    """Subscription execution-order priority (Part 2 §2.5.4).

    Distinct scale from EventPriority (§2.2.3). The set is FIXED at five
    levels (§2.14.2 "Adding Priority Levels ... Fixed at 5"); arbitrary
    priority integers are NOT permitted. Subscriptions are ordered by this
    value, ties broken by subscriptionId (UUIDv7 = creation time,
    INV-SUB-007).
    """

    FIRST = 0
    HIGH = 100
    NORMAL = 500
    LOW = 1000
    LAST = 10000

    def __str__(self) -> str:
        return self.name


# Wildcard subscriptions have IMPLICIT lowest priority unless an explicit
# handler priority is provided (Part 2 §2.5.5: "implicit lowest priority
# (LAST + 1)"). This is a DERIVED implementation constant, NOT an
# architecture-defined enum member — handler priority itself remains the
# fixed HandlerPriority scale. Documented as DERIVED per the Task 4 directive.
WILDCARD_PRIORITY = 10001  # == HandlerPriority.LAST + 1


class SubscriptionState(str, enum.Enum):
    """Lifecycle states for a single subscription (Part 2 §2.5.6).

    CREATED -> REGISTERED -> ACTIVE -> DEREGISTERING -> DEREGISTERED
    (SUSPENDED is reachable from ACTIVE on handler error; recovered back to
    ACTIVE, per §2.5.6 "on error: SUSPENDED -> ACTIVE on recovery".)

    NOTE: this state is owned by SubscriptionManager, NOT by the immutable
    Subscription value object (§2.13.3 ISubscription defines no state field).
    """

    CREATED = "CREATED"
    REGISTERED = "REGISTERED"
    ACTIVE = "ACTIVE"
    DEREGISTERING = "DEREGISTERING"
    DEREGISTERED = "DEREGISTERED"
    SUSPENDED = "SUSPENDED"


# Type alias for the handler callable (Part 2 §2.5.1 signature).
# (event: Event) -> None  (sync) or -> Awaitable[None] (async, via handlerType).
EventHandler = Callable[["Any"], Any]


def _now_iso() -> str:
    """Current UTC instant in ISO 8601 with Z suffix (§2.13.3 createdAt)."""
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _deep_freeze(obj: Any) -> Any:
    """Recursively freeze a metadata value into an immutable structure.

    dict -> MappingProxyType (recursive), list/tuple -> tuple (recursive),
    set -> frozenset (recursive), scalars unchanged. The resulting object is
    fully read-only: any mutation attempt (including through nested views)
    raises ``TypeError``. This honours the immutability contract for
    Subscription.metadata (Part 2 §2.13.3 ``metadata: Record<string, unknown>``
    is treated as an immutable snapshot at registration time).
    """
    if isinstance(obj, Mapping):
        return MappingProxyType({k: _deep_freeze(v) for k, v in obj.items()})
    if isinstance(obj, (list, tuple)):
        return tuple(_deep_freeze(v) for v in obj)
    if isinstance(obj, set):
        return frozenset(_deep_freeze(v) for v in obj)
    return obj


@dataclass(frozen=True)
class RetryPolicy:
    """Subscription retry policy (Part 2 §2.5.8 RetryPolicy).

    Concrete architectural contract: maxAttempts, baseDelayMs, maxDelayMs,
    backoffMultiplier, jitter, retryableErrors. Defaults match the
    architecture's "Retry Policy (default)" block. ``maxAttempts`` is bounded
    by §2.14.1 (custom policies: maxAttempts <= 10).

    ``retryableErrors`` is stored as an immutable tuple of error-category
    names. The authoritative ``ErrorType`` enumeration is defined by the
    (future) error-handling subsystem; until then it is represented as a tuple
    of strings per the architecture's default set [TRANSIENT, TIMEOUT,
    UNAVAILABLE]. This is the documented unspecified portion of the boundary.
    """

    maxAttempts: int = 3
    baseDelayMs: int = 1000
    maxDelayMs: int = 30000
    backoffMultiplier: float = 2.0
    jitter: bool = True
    retryableErrors: tuple[str, ...] = ("TRANSIENT", "TIMEOUT", "UNAVAILABLE")

    @classmethod
    def create(cls, value: Any) -> "Optional[RetryPolicy]":
        """Normalize a RetryPolicy input (None / RetryPolicy / dict)."""
        if value is None:
            return None
        if isinstance(value, RetryPolicy):
            return value
        if isinstance(value, dict):
            allowed = {f for f in cls.__dataclass_fields__}
            cleaned = {k: v for k, v in value.items() if k in allowed}
            return cls(**cleaned)
        raise EventRegistryError(
            "RetryPolicy MUST be None, a RetryPolicy, or a dict of RetryPolicy "
            "fields (Part 2 §2.5.8)."
        )

    def __post_init__(self) -> None:
        if not isinstance(self.maxAttempts, int) or self.maxAttempts < 1:
            raise EventRegistryError("RetryPolicy.maxAttempts MUST be an int >= 1.")
        # §2.14.1: custom retry policies MUST have maxAttempts <= 10.
        if self.maxAttempts > 10:
            raise EventRegistryError(
                "RetryPolicy.maxAttempts MUST be <= 10 (Part 2 §2.14.1)."
            )
        if not isinstance(self.baseDelayMs, int) or self.baseDelayMs < 0:
            raise EventRegistryError("RetryPolicy.baseDelayMs MUST be an int >= 0.")
        if not isinstance(self.maxDelayMs, int) or self.maxDelayMs < 0:
            raise EventRegistryError("RetryPolicy.maxDelayMs MUST be an int >= 0.")
        if (
            not isinstance(self.backoffMultiplier, (int, float))
            or self.backoffMultiplier <= 0
        ):
            raise EventRegistryError(
                "RetryPolicy.backoffMultiplier MUST be a positive number."
            )
        if not isinstance(self.jitter, bool):
            raise EventRegistryError("RetryPolicy.jitter MUST be a bool.")
        if not isinstance(self.retryableErrors, (tuple, list, set, frozenset)):
            raise EventRegistryError(
                "RetryPolicy.retryableErrors MUST be a collection of error names."
            )
        # Immutable, order-stable snapshot.
        object.__setattr__(
            self, "retryableErrors", tuple(str(e) for e in self.retryableErrors)
        )


@dataclass(frozen=True)
class Subscription:
    """Immutable subscription record (Part 2 §2.13.3 ISubscription).

    The object is frozen (no lifecycle state, no mutation post-construction).
    Lifecycle is owned by SubscriptionManager.

    ``subscriptionId`` is always UUIDv7 (INV-EVT-002 analog).
    ``eventTypes`` is either the wildcard marker ``'*'`` or an immutable tuple
    of ``EventType`` members (caller-provided mutable sequences are normalized
    to a tuple at construction and never escape).
    ``handler`` is stored by reference; idempotency is keyed on its identity
    (INV-SUB-011).
    ``priority`` MUST be a ``HandlerPriority`` for explicit subscriptions
    (fixed 5 levels, §2.14.2); wildcards may additionally carry the derived
    ``WILDCARD_PRIORITY`` (LAST + 1, §2.5.5).
    ``metadata`` is deep-frozen (fully read-only).
    """

    subscriptionId: "uuid.UUID"
    subscriber: "ComponentIdentity"
    eventTypes: "tuple[EventType, ...] | str"  # '*' or tuple[EventType, ...]
    handler: "EventHandler"
    filter: "Optional[EventFilter]"
    handlerType: str  # 'sync' | 'async'
    priority: "HandlerPriority | int"  # HandlerPriority; WILDCARD_PRIORITY for wildcards
    maxConcurrency: int
    timeoutMs: int
    retryPolicy: "Optional[RetryPolicy]"
    createdAt: str
    metadata: "Mapping[str, Any]"  # deep-frozen, read-only

    @classmethod
    def create(
        cls,
        *,
        subscriptionId: "uuid.UUID",
        subscriber: "ComponentIdentity",
        eventTypes: Any,
        handler: "EventHandler",
        filter: "Optional[EventFilter]" = None,
        handlerType: str = "sync",
        priority: Any = None,
        maxConcurrency: int = 1,
        timeoutMs: int = 30000,
        retryPolicy: Any = None,
        createdAt: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> "Subscription":
        """Construct a Subscription with full input normalization.

        Normalizes eventTypes (wildcard or tuple), deep-freezes metadata, and
        validates the priority/retry-policy contracts before constructing the
        frozen record. Normalization happens HERE (construction time), not via
        post-hoc ``object.__setattr__`` mutation of the frozen instance.
        """
        # eventTypes: normalize to immutable tuple (or wildcard marker).
        # API allows EventType | EventType[] | '*' (§2.5.1), so a single
        # EventType is wrapped into a 1-tuple before construction.
        if eventTypes == WILDCARD:
            norm_event_types: Any = WILDCARD
        elif isinstance(eventTypes, EventType):
            norm_event_types = (eventTypes,)
        elif isinstance(eventTypes, (list, tuple, set)):
            norm_event_types = tuple(eventTypes)
        else:
            norm_event_types = eventTypes  # invalid -> caught in __post_init__

        norm_priority = HandlerPriority.NORMAL if priority is None else priority
        norm_retry = RetryPolicy.create(retryPolicy)

        return cls(
            subscriptionId=subscriptionId,
            subscriber=subscriber,
            eventTypes=norm_event_types,
            handler=handler,
            filter=filter,
            handlerType=handlerType,
            priority=norm_priority,
            maxConcurrency=maxConcurrency,
            timeoutMs=timeoutMs,
            retryPolicy=norm_retry,
            createdAt=createdAt if createdAt is not None else _now_iso(),
            # Metadata deep-freezing is performed in __post_init__ so that ALL
            # construction paths (factory and direct) yield an immutable
            # snapshot. Passing the raw mapping here is intentional.
            metadata=metadata if metadata is not None else {},
        )

    def __post_init__(self) -> None:
        if not isinstance(self.subscriptionId, uuid.UUID) or not is_uuid7(
            self.subscriptionId
        ):
            raise EventRegistryError(
                "Subscription.subscriptionId MUST be a UUIDv7."
            )
        if not isinstance(self.subscriber, ComponentIdentity):
            raise EventRegistryError(
                "Subscription.subscriber MUST be a ComponentIdentity."
            )
        # eventTypes type safety (§2.5.1 / §2.13.3).
        if self.eventTypes != WILDCARD:
            if not isinstance(self.eventTypes, tuple) or not self.eventTypes:
                raise EventRegistryError(
                    "Subscription.eventTypes MUST be '*' (wildcard) or a "
                    "non-empty tuple of EventType members."
                )
            from aios.events.core.types import EventType as _ET

            for et in self.eventTypes:
                if not isinstance(et, _ET):
                    raise EventRegistryError(
                        "Subscription.eventTypes MUST contain EventType members "
                        "only (got %r)." % (et,)
                    )
        if not callable(self.handler):
            raise EventRegistryError("Subscription.handler MUST be callable.")
        if self.handlerType not in ("sync", "async"):
            raise EventRegistryError(
                "Subscription.handlerType MUST be 'sync' or 'async'."
            )
        # Priority: fixed HandlerPriority scale (§2.5.4 / §2.14.2). Explicit
        # subscriptions MUST use a HandlerPriority; wildcards may additionally
        # use the derived WILDCARD_PRIORITY (LAST + 1, §2.5.5).
        valid_priority_values = {m.value for m in HandlerPriority}
        if isinstance(self.priority, HandlerPriority):
            pass
        elif isinstance(self.priority, int) and self.priority in valid_priority_values:
            # Accept the equivalent integer of a defined level (coerced form).
            pass
        elif self.is_wildcard and self.priority == WILDCARD_PRIORITY:
            # Derived lowest priority for wildcards (§2.5.5).
            pass
        else:
            raise EventRegistryError(
                "Subscription.priority MUST be a HandlerPriority "
                f"(one of {sorted(valid_priority_values)}); arbitrary priority "
                "integers are PROHIBITED (Part 2 §2.5.4 / §2.14.2)."
            )
        if not isinstance(self.maxConcurrency, int) or self.maxConcurrency < 1:
            raise EventRegistryError(
                "Subscription.maxConcurrency MUST be an int >= 1."
            )
        if not isinstance(self.timeoutMs, int) or self.timeoutMs < 0:
            raise EventRegistryError(
                "Subscription.timeoutMs MUST be a non-negative int."
            )
        if self.retryPolicy is not None and not isinstance(
            self.retryPolicy, RetryPolicy
        ):
            raise EventRegistryError(
                "Subscription.retryPolicy MUST be a RetryPolicy or None."
            )
        if not isinstance(self.metadata, Mapping):
            raise EventRegistryError("Subscription.metadata MUST be a mapping.")
        if not isinstance(self.createdAt, str):
            raise EventRegistryError("Subscription.createdAt MUST be an ISO8601 str.")
        # Deep-freeze metadata on EVERY construction path so the value object's
        # metadata is always an immutable, read-only snapshot (no caller can
        # mutate it — through the input, through .metadata, or via nesting).
        object.__setattr__(self, "metadata", _deep_freeze(dict(self.metadata)))

    # --- identity / matching ----------------------------------------------

    @property
    def is_wildcard(self) -> bool:
        return self.eventTypes == WILDCARD

    def matches_event_type(self, event_type: "EventType") -> bool:
        """True if this subscription should receive ``event_type`` (§2.5.5)."""
        if self.is_wildcard:
            return True
        return event_type in self.eventTypes

    def identity_key(self) -> tuple[Any, ...]:
        """Idempotency identity tuple (Part 2 §2.5.7 / INV-SUB-011).

        (subscriber, eventTypes, handler identity). EventTypes are normalized
        to a sorted tuple of names so order does not matter; handler identity
        is BY REFERENCE (id) per INV-SUB-011 "Function identity is by
        reference." Python's ``id()`` is the correct language-level
        representation of reference identity.
        """
        if self.is_wildcard:
            types_key: Any = WILDCARD
        else:
            types_key = tuple(sorted(et.name for et in self.eventTypes))
        return (self.subscriber, types_key, id(self.handler))

    # --- equality / hash (by identity, not content) -----------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Subscription):
            return NotImplemented
        return self.subscriptionId == other.subscriptionId

    def __hash__(self) -> int:
        return hash(self.subscriptionId)

    def __repr__(self) -> str:
        kinds = "WILDCARD" if self.is_wildcard else f"{len(self.eventTypes)} types"
        return (
            f"Subscription(id={self.subscriptionId}, "
            f"subscriber={self.subscriber.component_name!r}, {kinds}, "
            f"priority={self.priority})"
        )


__all__ = [
    "Subscription",
    "SubscriptionState",
    "HandlerPriority",
    "RetryPolicy",
    "WILDCARD",
    "WILDCARD_PRIORITY",
    "EventHandler",
]
