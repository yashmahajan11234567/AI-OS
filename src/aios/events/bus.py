"""
Event Bus Compatibility Layer for AI-OS.

This module provides the legacy EventBus API surface while delegating to the
canonical EventBus (C1, Task 5) to eliminate the split-brain architecture
where two EventBus instances existed concurrently (INV-EB-001).

All new code should import from aios.events.core.bus directly.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from aios.events.core.bus import (
    EventBus as CoreEventBus,
    EventBusConfig,
    get_core_event_bus,
    reset_core_event_bus_singleton,
    _INSTANCE,
    _INSTANCE_LOCK,
)
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.subscription import (
    Subscription as CoreSubscription,
    HandlerPriority,
    RetryPolicy,
)
from aios.events.core.manager import SubscribeOptions
from aios.events.core.bus import UnsubscribeOptions
from aios.events.core.types import EventType

logger = logging.getLogger(__name__)


@dataclass
class Subscription:
    """Legacy-compatible subscription representation."""

    handler: Callable[[Any], Any]
    event_types: list[str]
    filter_fn: Callable[[Any], bool] | None = None
    is_async: bool = False
    subscription_id: str = field(default_factory=lambda: f"sub_{datetime.utcnow().timestamp()}")


# Global state to track legacy subscriptions for compatibility
_legacy_subscriptions: list[Subscription] = []
_legacy_subscription_index = 0


def _ensure_core_bus() -> CoreEventBus:
    """Get the canonical EventBus, initializing if necessary."""
    bus = get_core_event_bus()
    if bus is None:
        # Initialize canonical EventBus with default config
        reset_core_event_bus_singleton()
        bus = CoreEventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
        # Note: The kernel is responsible for calling initialize() and shutdown()
        # We don't auto-initialize here to respect the kernel's lifecycle control
    return bus


def _get_core_bus_for_publish() -> CoreEventBus:
    """Get the core bus, raising if not initialized (for publish)."""
    bus = get_core_event_bus()
    if bus is None:
        raise RuntimeError("Canonical EventBus not initialized. Start the kernel first.")
    return bus


def _convert_event_type(event_type: str | EventType) -> EventType:
    """Convert legacy string/event_type to canonical EventType enum."""
    if isinstance(event_type, EventType):
        return event_type
    try:
        return EventType(event_type)
    except ValueError:
        # For event types not in the canonical enum, we can't publish them
        # via the canonical bus. This maintains legacy behavior for unknown types.
        raise ValueError(f"Unknown EventType: {event_type}. Must be a canonical EventType.")


def _convert_to_core_event(event: Any) -> CoreEvent:
    """Convert legacy Event to canonical Event if needed."""
    if isinstance(event, CoreEvent):
        return event
    # Legacy Event from aios.events.base - convert
    # This is a minimal conversion; the canonical bus expects fully-formed CoreEvents
    raise TypeError("All events must be canonical CoreEvent instances. "
                    "Use aios.events.core.event.Event to create events.")


# Legacy compatibility wrapper class (Rule 8 — permitted to remain as a
# compatibility surface AS LONG AS it does not create a second runtime
# authority). This class delegates every operation to the canonical
# aios.events.core.bus.EventBus singleton; it never constructs or holds its own
# bus instance. The ``get_event_bus()`` accessor (below) returns the canonical
# singleton directly so that ``kernel.event_bus is get_event_bus()`` holds
# (Rule 10).
class EventBus:
    """Legacy-compatible EventBus wrapper delegating to canonical C1."""

    def __init__(self, max_history: int = 10000):
        # The canonical EventBus is a singleton managed by the kernel.
        # This wrapper does NOT create its own instance.
        self._max_history = max_history

    def subscribe(
        self,
        handler: Callable[[Any], Any],
        event_types: str | list[str] | EventType | list[EventType] = EventType,
        filter_fn: Callable[[Any], bool] | None = None,
    ) -> str:
        """
        Subscribe a handler to event types (legacy API).

        Delegates to canonical EventBus subscribe with SubscribeOptions.
        """
        global _legacy_subscription_index
        _legacy_subscription_index += 1
        sub_id = f"legacy_sub_{_legacy_subscription_index}"

        # Normalize event types
        if isinstance(event_types, (str, EventType)):
            event_type_list = [event_types]
        elif not event_types:
            event_type_list = [et for et in EventType]
        else:
            event_type_list = list(event_types)

        # Convert to canonical EventType enums
        core_event_types = [_convert_event_type(et) for et in event_type_list]

        # Determine if handler is async
        is_async = asyncio.iscoroutinefunction(handler)

        # Create subscription options for canonical bus
        # Use a generic legacy subscriber identity for legacy API calls
        legacy_subscriber = ComponentIdentity(
            component_type=ComponentType.ENGINEERING_SERVICE,
            component_name="legacy-subscriber"
        )
        options = SubscribeOptions(
            subscriber=legacy_subscriber,
            event_types=core_event_types,
            handler=handler,
            priority=HandlerPriority.NORMAL,
            filter=filter_fn,
            retry_policy=RetryPolicy(),
            metadata={"legacy_sub_id": sub_id},
        )

        # Register with canonical EventBus (synchronous delegate)
        core_bus = _get_core_bus_for_publish()
        subscription = core_bus.subscribe(options)

        # Track for legacy unsubscribe
        legacy_sub = Subscription(
            handler=handler,
            event_types=[str(et) for et in core_event_types],
            filter_fn=filter_fn,
            is_async=is_async,
            subscription_id=sub_id,
        )
        legacy_sub.__dict__["_core_subscription_id"] = subscription.subscriptionId
        _legacy_subscriptions.append(legacy_sub)

        logger.debug(f"Subscribed legacy handler {handler} to {event_type_list} (async={is_async}) via canonical bus")
        return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe a handler by subscription ID (legacy API).

        Delegates to canonical EventBus unsubscribe.
        """
        global _legacy_subscriptions
        for i, sub in enumerate(_legacy_subscriptions):
            if sub.subscription_id == subscription_id:
                core_sub_id = sub.__dict__.get("_core_subscription_id")
                if core_sub_id:
                    core_bus = _get_core_bus_for_publish()
                    core_bus.unsubscribe(
                        UnsubscribeOptions(subscription_id=core_sub_id, immediate=True)
                    )
                _legacy_subscriptions.pop(i)
                logger.debug(f"Unsubscribed legacy subscription {subscription_id}")
                return True
        return False

    def publish(self, event: Any) -> int:
        """
        Publish an event to all subscribers (legacy sync API).

        NOTE: This is synchronous for legacy compatibility but delegates to
        the canonical async publish. The event is enqueued; handlers execute
        during drain(). Returns 1 if accepted, 0 if rejected.
        """
        core_bus = _get_core_bus_for_publish()
        core_event = _convert_to_core_event(event)

        # Run the async publish in the event loop (legacy sync API)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(core_bus.publish(core_event))
        return 1 if result.accepted else 0

    async def publish_async(self, event: Any) -> int:
        """
        Publish an event to all subscribers (legacy async API).

        Delegates to canonical EventBus publish.
        """
        core_bus = _get_core_bus_for_publish()
        core_event = _convert_to_core_event(event)

        result = await core_bus.publish(core_event)
        return 1 if result.accepted else 0

    def get_history(
        self,
        event_type: str | None = None,
        correlation_id: str | None = None,
        limit: int = 100,
    ) -> list[Any]:
        """
        Get event history with optional filtering (legacy API).

        Delegates to canonical EventBus get_history.
        """
        core_bus = _get_core_bus_for_publish()

        # Convert event_type string to EventType if provided
        et = None
        if event_type:
            try:
                et = EventType(event_type)
            except ValueError:
                # Unknown event type - return empty
                return []

        cid = None
        if correlation_id:
            cid = uuid.UUID(correlation_id)

        return core_bus.get_history(
            event_type=et,
            correlation_id=cid,
            limit=limit,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get event bus statistics (legacy API with canonical extensions)."""
        core_bus = _get_core_bus_for_publish()
        return core_bus.get_stats()

    def clear_history(self) -> None:
        """Clear event history - not supported on canonical bus (history is bounded)."""
        # Canonical bus uses bounded ring buffer; cannot clear
        logger.warning("clear_history() not supported on canonical EventBus (bounded history)")

    def shutdown(self) -> None:
        """Shutdown the event bus (legacy sync API).

        Delegates to canonical async shutdown. Kernel controls actual shutdown.
        """
        # The kernel owns the canonical EventBus lifecycle
        # This is a no-op for the wrapper
        logger.debug("Legacy EventBus.shutdown() called; kernel manages canonical bus shutdown")

    async def start(self) -> None:
        """Start the event bus (legacy API).

        Canonical bus is initialized by kernel. This is a no-op.
        """
        logger.debug("Legacy EventBus.start() called; kernel manages canonical bus initialization")


# Legacy accessor: returns the canonical EventBus singleton (INV-EB-001 — exactly
# one EventBus instance per process). The kernel constructs and owns that
# singleton; this accessor exposes the SAME object so that
# ``kernel.event_bus is get_event_bus()`` holds (Rule 10). No separate legacy
# runtime authority is created.
def get_event_bus() -> EventBus:
    """Get the canonical EventBus singleton (Rule 8 / Rule 10).

    Returns the single process-wide EventBus instance owned by the kernel.
    """
    return get_core_event_bus()


def set_event_bus(bus: EventBus) -> None:
    """Set the canonical EventBus singleton (kernel-owned construction).

    Provided for backward compatibility; writing the global accessor sets the
    canonical singleton directly rather than a separate legacy object.
    """
    global _INSTANCE
    with _INSTANCE_LOCK:
        _INSTANCE = bus


@asynccontextmanager
async def event_bus_context(bus: EventBus | None = None):
    """Context manager for event bus lifecycle (legacy API).

    Canonical bus lifecycle is managed by the kernel.
    """
    event_bus = bus or get_event_bus()
    try:
        yield event_bus
    finally:
        event_bus.shutdown()


__all__ = [
    "EventBus",
    "Subscription",
    "get_event_bus",
    "set_event_bus",
    "event_bus_context",
]