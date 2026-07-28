"""
Event Bus Implementation for AI-OS.

The Event Bus is the central communication mechanism for the event-driven architecture.
All services communicate ONLY through the Event Bus - no direct service-to-service calls.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from aios.events.base import Event, EventType
from aios.events.handlers import EventHandler, AsyncEventHandler, handler_for, async_handler_for

logger = logging.getLogger(__name__)


@dataclass
class Subscription:
    """Represents a subscription to event types."""

    handler: EventHandler | AsyncEventHandler | Callable[[Event], Any]
    event_types: list[str]
    filter_fn: Callable[[Event], bool] | None = None
    is_async: bool = False
    subscription_id: str = field(default_factory=lambda: f"sub_{datetime.utcnow().timestamp()}")


class EventBus:
    """
    Central Event Bus for AI-OS.

    All services communicate exclusively through this event bus.
    Supports both synchronous and asynchronous event handlers.
    Provides event history, filtering, and subscription management.
    """

    def __init__(self, max_history: int = 10000):
        """
        Initialize the Event Bus.

        Args:
            max_history: Maximum number of events to keep in history
        """
        self._subscriptions: dict[str, list[Subscription]] = defaultdict(list)
        self._all_subscriptions: list[Subscription] = []
        self._history: list[Event] = []
        self._max_history = max_history
        self._running = True
        self._lock = asyncio.Lock()
        self._event_count = 0

    def subscribe(
        self,
        handler: EventHandler | AsyncEventHandler | Callable[[Event], Any],
        event_types: str | list[str] | EventType | list[EventType] = EventType,
        filter_fn: Callable[[Event], bool] | None = None,
    ) -> str:
        """
        Subscribe a handler to event types.

        Args:
            handler: Event handler (sync or async)
            event_types: Event type(s) to subscribe to (string, EventType, or list)
            filter_fn: Optional filter function to further filter events

        Returns:
            Subscription ID for later unsubscription
        """
        event_type_strs = self._normalize_event_types(event_types)

        # Detect if handler is async
        is_async = asyncio.iscoroutinefunction(handler) or hasattr(handler, "_aios_is_async")

        # Check for decorator metadata
        if hasattr(handler, "_aios_event_types"):
            event_type_strs = [str(et) for et in handler._aios_event_types]
            if filter_fn is None and hasattr(handler, "_aios_filter_fn"):
                filter_fn = handler._aios_filter_fn
            is_async = is_async or getattr(handler, "_aios_is_async", False)

        subscription = Subscription(
            handler=handler,
            event_types=event_type_strs,
            filter_fn=filter_fn,
            is_async=is_async,
        )

        for event_type in event_type_strs:
            self._subscriptions[event_type].append(subscription)
        self._all_subscriptions.append(subscription)

        logger.debug(f"Subscribed {handler} to {event_type_strs} (async={is_async})")
        return subscription.subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe a handler by subscription ID.

        Args:
            subscription_id: ID returned from subscribe()

        Returns:
            True if unsubscribed, False if not found
        """
        for event_type, subs in self._subscriptions.items():
            for i, sub in enumerate(subs):
                if sub.subscription_id == subscription_id:
                    subs.pop(i)
                    break

        for i, sub in enumerate(self._all_subscriptions):
            if sub.subscription_id == subscription_id:
                self._all_subscriptions.pop(i)
                break

        logger.debug(f"Unsubscribed {subscription_id}")
        return True

    def _normalize_event_types(
        self, event_types: str | list[str] | EventType | list[EventType]
    ) -> list[str]:
        """Normalize event types to string list."""
        if isinstance(event_types, (str, EventType)):
            return [str(event_types)]

        if not event_types:
            return [et.value for et in EventType]

        return [str(et) for et in event_types]

    def publish(self, event: Event) -> int:
        """
        Publish an event to all subscribers (synchronous).

        Args:
            event: Event to publish

        Returns:
            Number of handlers that received the event
        """
        self._add_to_history(event)
        self._event_count += 1

        # Get matching subscriptions
        handlers = self._get_matching_handlers(event)
        count = 0

        for sub in handlers:
            try:
                if sub.is_async:
                    # Schedule async handler
                    asyncio.create_task(self._run_async_handler(sub, event))
                else:
                    # Run sync handler
                    sub.handler(event)
                count += 1
            except Exception as e:
                logger.error(f"Error in event handler {sub.handler}: {e}", exc_info=True)

        return count

    async def publish_async(self, event: Event) -> int:
        """
        Publish an event to all subscribers (asynchronous).

        Args:
            event: Event to publish

        Returns:
            Number of handlers that received the event
        """
        self._add_to_history(event)
        self._event_count += 1

        handlers = self._get_matching_handlers(event)
        count = 0

        # Run all handlers concurrently
        tasks = []
        for sub in handlers:
            if sub.is_async:
                tasks.append(self._run_async_handler(sub, event))
            else:
                tasks.append(asyncio.get_event_loop().run_in_executor(None, sub.handler, event))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error in event handler: {result}", exc_info=result)
                else:
                    count += 1

        return count

    def _get_matching_handlers(self, event: Event) -> list[Subscription]:
        """Get all handlers that match the event."""
        # Get string representation of event type
        if isinstance(event.event_type, EventType):
            event_type_str = event.event_type.value
        else:
            event_type_str = event.event_type
        handlers = []

        # Exact match
        for sub in self._subscriptions.get(event_type_str, []):
            if sub.filter_fn is None or sub.filter_fn(event):
                handlers.append(sub)

        # Wildcard match (handlers subscribed to '*' or all types)
        for sub in self._subscriptions.get("*", []):
            if sub.filter_fn is None or sub.filter_fn(event):
                handlers.append(sub)

        return handlers

    async def _run_async_handler(self, sub: Subscription, event: Event) -> None:
        """Run an async handler with error handling."""
        try:
            if asyncio.iscoroutinefunction(sub.handler):
                await sub.handler(event)
            else:
                await sub.handler.handle(event)
        except Exception as e:
            logger.error(f"Error in async event handler {sub.handler}: {e}", exc_info=True)

    def _add_to_history(self, event: Event) -> None:
        """Add event to history, maintaining max size."""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

    def get_history(
        self,
        event_type: str | None = None,
        correlation_id: str | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """
        Get event history with optional filtering.

        Args:
            event_type: Filter by event type
            correlation_id: Filter by correlation ID
            limit: Maximum events to return

        Returns:
            List of matching events (most recent first)
        """
        filtered = self._history

        if event_type:
            filtered = [
                e
                for e in filtered
                if (e.event_type.value if isinstance(e.event_type, EventType) else e.event_type)
                == event_type
            ]

        if correlation_id:
            filtered = [e for e in filtered if e.correlation_id == correlation_id]

        return filtered[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Get event bus statistics."""
        return {
            "total_events_published": self._event_count,
            "active_subscriptions": len(self._all_subscriptions),
            "subscriptions_by_type": {
                et: len(subs) for et, subs in self._subscriptions.items()
            },
            "history_size": len(self._history),
            "max_history": self._max_history,
        }

    def clear_history(self) -> None:
        """Clear event history."""
        self._history.clear()
        self._event_count = 0

    def shutdown(self) -> None:
        """Shutdown the event bus."""
        self._running = False
        self._subscriptions.clear()
        self._all_subscriptions.clear()

    async def start(self) -> None:
        """Start the event bus (no-op, ready immediately)."""
        self._running = True


# Global event bus instance
_global_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus instance."""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def set_event_bus(bus: EventBus) -> None:
    """Set the global event bus instance."""
    global _global_event_bus
    _global_event_bus = bus


@asynccontextmanager
async def event_bus_context(bus: EventBus | None = None):
    """Context manager for event bus lifecycle."""
    event_bus = bus or EventBus()
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


