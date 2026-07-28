"""
Event Handler Base Classes for AI-OS.

Provides base classes for synchronous and asynchronous event handlers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable

from aios.events.base import Event


class EventHandler(ABC):
    """
    Base class for synchronous event handlers.

    Subclasses must implement the handle method.
    """

    @abstractmethod
    def handle(self, event: Event) -> Any:
        """Handle an event. Called synchronously."""
        pass

    def can_handle(self, event: Event) -> bool:
        """Check if this handler can process the event. Default: all events."""
        return True


class AsyncEventHandler(ABC):
    """
    Base class for asynchronous event handlers.

    Subclasses must implement the handle method.
    """

    @abstractmethod
    async def handle(self, event: Event) -> Any:
        """Handle an event. Called asynchronously."""
        pass

    def can_handle(self, event: Event) -> bool:
        """Check if this handler can process the event. Default: all events."""
        return True


def handler_for(
    event_type: str | list[str],
    filter_fn: Callable[[Event], bool] | None = None,
) -> Callable[[Callable[[Event], Any]], Callable[[Event], Any]]:
    """
    Decorator to mark a function as an event handler.

    Usage:
        @handler_for("task.created")
        def handle_task_created(event: Event):
            ...

        @handler_for(["planning.completed", "coding.completed"])
        def handle_workflow_step(event: Event):
            ...
    """
    event_types = [event_type] if isinstance(event_type, str) else event_type

    def decorator(fn: Callable[[Event], Any]) -> Callable[[Event], Any]:
        fn._aios_event_types = event_types
        fn._aios_filter_fn = filter_fn
        return fn

    return decorator


def async_handler_for(
    event_type: str | list[str],
    filter_fn: Callable[[Event], bool] | None = None,
) -> Callable[[Callable[[Event], Any]], Callable[[Event], Any]]:
    """
    Decorator to mark an async function as an event handler.

    Usage:
        @async_handler_for("task.created")
        async def handle_task_created(event: Event):
            ...
    """
    event_types = [event_type] if isinstance(event_type, str) else event_type

    def decorator(fn: Callable[[Event], Any]) -> Callable[[Event], Any]:
        fn._aios_event_types = event_types
        fn._aios_filter_fn = filter_fn
        fn._aios_is_async = True
        return fn

    return decorator


__all__ = [
    "EventHandler",
    "AsyncEventHandler",
    "handler_for",
    "async_handler_for",
]