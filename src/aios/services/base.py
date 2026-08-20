"""Engineering Service Framework for AI-OS.

Every subsystem in AI-OS is an *Engineering Service*. Services:
  * never call other services directly - they communicate ONLY via the Event Bus;
  * subscribe to events (requests) in ``on_start`` and emit completion/failure events;
  * expose a small async API that the Kernel/Workflow can invoke through events;
  * report status to the ServiceRegistry so the Kernel can observe health.

This module defines the abstract ``BaseService`` and a simple lifecycle. Concrete
services live under ``aios.services.<name>``.

Uses the canonical EventBus (C1, Task 5) and ServiceRegistry (C2, Task 6)
to eliminate split-brain architecture (INV-EB-001, INV-SR-STR-001).
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable
from uuid import uuid4

from aios.events.core.bus import EventBus as CoreEventBus, UnsubscribeOptions
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.manager import SubscribeOptions
from aios.events.core.subscription import HandlerPriority, RetryPolicy, Subscription as CoreSubscription
from aios.events.core.types import EventType, SemanticVersion

logger = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    """Lifecycle status of an Engineering Service."""

    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    DEGRADED = "degraded"


@dataclass
class ServiceInfo:
    """Static description of a service."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    # Services this one conceptually depends on (informational - NOT used for
    # direct calls; only to hint the registry about start ordering).
    depends_on: list[str] = field(default_factory=list)


class BaseService(ABC):
    """Base class for all Engineering Services.

    Subclasses set the class attributes ``name`` and ``version`` and override
    ``on_start`` (subscribe to events, initialise) and optionally ``on_stop``.

    Contract enforced by convention:
      * Services obtain the shared event bus from the canonical EventBus singleton.
      * Use ``self.subscribe(...)`` so subscriptions are tracked and cleaned up.
      * Use ``self.emit(event)`` to publish results back to the bus.
      * Never construct another concrete service or call its methods directly.
    """

    name: str = "base_service"
    version: str = "1.0.0"
    description: str = ""
    depends_on: list[str] = []

    def __init__(
        self,
        event_bus: CoreEventBus | None = None,
        info: ServiceInfo | None = None,
    ):
        # Use canonical EventBus (C1). The kernel initializes the singleton.
        # If not provided, get from global singleton.
        self._event_bus = event_bus
        self._info = info or ServiceInfo(
            name=self.name,
            version=self.version,
            description=self.description,
            depends_on=list(self.depends_on),
        )
        self._status: ServiceStatus = ServiceStatus.CREATED
        self._subscription_ids: list[str] = []  # Core subscription IDs (UUIDs)
        self._started_at: datetime | None = None
        self._error: str | None = None
        self._instance_id = f"{self.name}_{uuid4().hex[:8]}"

        # Component identity for event emission
        self._identity = ComponentIdentity(
            component_type=ComponentType.ENGINEERING_SERVICE,
            component_name=self.name,
            version=SemanticVersion.parse(self.version),
        )

    # ----- properties -------------------------------------------------
    @property
    def event_bus(self) -> CoreEventBus:
        if self._event_bus is None:
            from aios.events.core.bus import get_core_event_bus
            self._event_bus = get_core_event_bus()
            if self._event_bus is None:
                raise RuntimeError("Canonical EventBus not initialized. Start the kernel first.")
        return self._event_bus

    @property
    def info(self) -> ServiceInfo:
        return self._info

    @property
    def status(self) -> ServiceStatus:
        return self._status

    @property
    def is_running(self) -> bool:
        return self._status in (ServiceStatus.RUNNING, ServiceStatus.DEGRADED)

    @property
    def is_healthy(self) -> bool:
        return self._status in (ServiceStatus.RUNNING, ServiceStatus.CREATED)

    @property
    def started_at(self) -> datetime | None:
        return self._started_at

    @property
    def last_error(self) -> str | None:
        return self._error

    # ----- lifecycle hooks (override in subclasses) ------------------
    async def on_start(self) -> None:
        """Override to subscribe to events and initialise. Call super().on_start()."""
        # Abstract base: subclasses override. We keep it non-abstract so
        # trivial services can be instantiated directly.
        pass

    async def on_stop(self) -> None:
        """Override for graceful shutdown."""
        pass

    async def on_health_check(self) -> bool:
        """Override to report real health. Default: healthy if running."""
        return self.is_running

    # ----- lifecycle --------------------------------------------------
    async def start(self) -> None:
        """Start the service (subscribe, initialise)."""
        if self._status in (ServiceStatus.RUNNING, ServiceStatus.STARTING):
            return
        self._status = ServiceStatus.STARTING
        try:
            await self.on_start()
            self._status = ServiceStatus.RUNNING
            self._started_at = datetime.utcnow()
            logger.debug("Service '%s' started", self.name)
        except Exception as e:  # noqa: BLE001
            self._status = ServiceStatus.FAILED
            self._error = str(e)
            logger.exception("Service '%s' failed to start: %s", self.name, e)
            raise

    async def stop(self) -> None:
        """Stop the service and unsubscribe all handlers."""
        try:
            await self.on_stop()
        finally:
            for sub_id in self._subscription_ids:
                try:
                    # Unsubscribe by subscriptionId immediately
                    self.event_bus.unsubscribe(
                        UnsubscribeOptions(subscription_id=sub_id, immediate=True)
                    )
                except Exception:  # noqa: BLE001
                    logger.debug("Failed to unsubscribe %s", sub_id)
            self._subscription_ids.clear()
            self._status = ServiceStatus.STOPPED
            logger.debug("Service '%s' stopped", self.name)

    # ----- event helpers ----------------------------------------------
    def subscribe(
        self,
        handler: Callable[[CoreEvent], Any],
        event_types: list[EventType] | EventType,
        filter_fn: Callable[[CoreEvent], bool] | None = None,
    ) -> str:
        """Subscribe a handler, tracking the subscription for cleanup.

        Args:
            handler: Event handler (sync or async)
            event_types: Event type(s) to subscribe to (canonical EventType enum)
            filter_fn: Optional filter function
        Returns:
            Subscription ID for later unsubscription
        """
        if isinstance(event_types, EventType):
            event_types = [event_types]

        is_async = asyncio.iscoroutinefunction(handler)

        options = SubscribeOptions(
            event_types=event_types,
            handler=handler,
            priority=HandlerPriority.NORMAL,
            filter_fn=filter_fn,
            retry_policy=RetryPolicy(),
            metadata={"service_name": self.name, "instance_id": self._instance_id},
        )

        sub_id = self.event_bus.subscribe(options)
        self._subscription_ids.append(sub_id)
        return sub_id

    async def emit(self, event: CoreEvent) -> int:
        """Publish an event on the shared canonical event bus.

        Returns:
            1 if accepted, 0 if rejected
        """
        result = await self.event_bus.publish(event)
        return 1 if result.accepted else 0

    def emit_sync(self, event: CoreEvent) -> int:
        """Publish an event synchronously (legacy API compatibility).

        Returns:
            1 if accepted, 0 if rejected
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(self.event_bus.publish(event))
        return 1 if result.accepted else 0

    @staticmethod
    def create_core_event(
        event_type: EventType,
        payload: dict[str, Any],
        correlation_id: str | None = None,
        causation_id: str | None = None,
        source_service: str | None = None,
    ) -> CoreEvent:
        """Factory to create a canonical CoreEvent with the service's identity."""
        import uuid

        return CoreEvent(
            eventType=event_type,
            source=ComponentIdentity(
                component_type=ComponentType.ENGINEERING_SERVICE,
                component_name=source_service or "unknown",
                version=SemanticVersion.parse("1.0.0"),
            ),
            correlationId=uuid.UUID(correlation_id) if correlation_id else uuid.uuid4(),
            causationId=uuid.UUID(causation_id) if causation_id else None,
            payload=payload,
        )

    # ----- introspection ----------------------------------------------
    def get_stats(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "instance_id": self._instance_id,
            "version": self.version,
            "status": self._status.value,
            "healthy": self.is_healthy,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "subscriptions": len(self._subscription_ids),
            "last_error": self._error,
        }

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<{type(self).__name__} name={self.name!r} status={self._status.value}>"


__all__ = [
    "BaseService",
    "ServiceStatus",
    "ServiceInfo",
]