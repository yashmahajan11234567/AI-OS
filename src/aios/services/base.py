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
from aios.events.core.types import EventType as CanonicalEventType, SemanticVersion
from aios.events.base import EventType as LegacyEventType

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
        self._events_published: int = 0
        self._events_subscribed: int = 0

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
        logger.info(f"Service '{self.name}' start() called, status: {self._status}")
        if self._status in (ServiceStatus.RUNNING, ServiceStatus.STARTING):
            logger.info(f"Service '{self.name}' already running/starting, returning")
            return
        self._status = ServiceStatus.STARTING
        try:
            await self.on_start()
            self._status = ServiceStatus.RUNNING
            self._started_at = datetime.utcnow()
            logger.info("Service '%s' started", self.name)
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

    # Legacy to Canonical EventType mapping
    _LEGACY_TO_CANONICAL = {
        # Kernel
        LegacyEventType.KERNEL_STARTED: CanonicalEventType.KERNEL_READY,
        LegacyEventType.KERNEL_STOPPED: CanonicalEventType.KERNEL_TERMINATED,
        LegacyEventType.KERNEL_ERROR: CanonicalEventType.KERNEL_FATAL_ERROR,

        # Task
        LegacyEventType.TASK_CREATED: CanonicalEventType.TASK_CREATED,
        LegacyEventType.TASK_STARTED: CanonicalEventType.TASK_STARTED,
        LegacyEventType.TASK_COMPLETED: CanonicalEventType.TASK_COMPLETED,
        LegacyEventType.TASK_FAILED: CanonicalEventType.TASK_FAILED,
        LegacyEventType.TASK_RETRY_REQUESTED: CanonicalEventType.TASK_RETRIED,
        LegacyEventType.TASK_CANCELLED: CanonicalEventType.TASK_CANCELLED,

        # Workflow
        LegacyEventType.WORKFLOW_CREATED: CanonicalEventType.WORKFLOW_STARTED,
        LegacyEventType.WORKFLOW_STARTED: CanonicalEventType.WORKFLOW_STARTED,
        LegacyEventType.WORKFLOW_COMPLETED: CanonicalEventType.WORKFLOW_COMPLETED,
        LegacyEventType.WORKFLOW_FAILED: CanonicalEventType.WORKFLOW_FAILED,
        LegacyEventType.WORKFLOW_PAUSED: CanonicalEventType.WORKFLOW_PAUSED,
        LegacyEventType.WORKFLOW_RESUMED: CanonicalEventType.WORKFLOW_RESUMED,

        # Planning
        LegacyEventType.PLANNING_REQUESTED: CanonicalEventType.PLANNING_REQUESTED,
        LegacyEventType.PLANNING_STARTED: CanonicalEventType.PLANNING_REQUESTED,
        LegacyEventType.PLANNING_COMPLETED: CanonicalEventType.PLANNING_COMPLETED,
        LegacyEventType.PLANNING_FAILED: CanonicalEventType.PLANNING_FAILED,
        LegacyEventType.PLAN_APPROVED: CanonicalEventType.COUNCIL_CONSENSUS_REACHED,
        LegacyEventType.PLAN_REJECTED: CanonicalEventType.PLAN_REJECTED,

        # Coding
        LegacyEventType.CODING_STARTED: CanonicalEventType.CODE_GENERATED,
        LegacyEventType.CODING_COMPLETED: CanonicalEventType.CODING_COMPLETED,
        LegacyEventType.CODING_FAILED: CanonicalEventType.CODING_FAILED,
        LegacyEventType.CODE_GENERATED: CanonicalEventType.CODE_GENERATED,
        LegacyEventType.CODE_REVIEW_REQUESTED: CanonicalEventType.CODE_REVIEW_REQUESTED,

        # Review
        LegacyEventType.REVIEW_STARTED: CanonicalEventType.REVIEW_STARTED,
        LegacyEventType.REVIEW_COMPLETED: CanonicalEventType.REVIEW_APPROVED,
        LegacyEventType.REVIEW_FAILED: CanonicalEventType.REVIEW_FAILED,
        LegacyEventType.REVIEW_APPROVED: CanonicalEventType.REVIEW_APPROVED,
        LegacyEventType.REVIEW_REJECTED: CanonicalEventType.REVIEW_REJECTED,

        # Testing
        LegacyEventType.TESTING_STARTED: CanonicalEventType.TESTING_COMPLETED,
        LegacyEventType.TESTING_COMPLETED: CanonicalEventType.TESTING_COMPLETED,
        LegacyEventType.TESTING_FAILED: CanonicalEventType.TESTING_FAILED,
        LegacyEventType.TESTS_PASSED: CanonicalEventType.TESTS_PASSED,
        LegacyEventType.TESTS_FAILED: CanonicalEventType.TESTS_FAILED,
        LegacyEventType.TEST_GENERATED: CanonicalEventType.TESTS_GENERATED,
        LegacyEventType.SECURITY_ISSUE_FOUND: CanonicalEventType.SECURITY_ISSUE_FOUND,
        LegacyEventType.PERFORMANCE_ISSUE_FOUND: CanonicalEventType.PERFORMANCE_ISSUE_FOUND,

        # Deployment
        LegacyEventType.DEPLOYMENT_REQUESTED: CanonicalEventType.DEPLOYMENT_REQUESTED,
        LegacyEventType.DEPLOYMENT_STARTED: CanonicalEventType.DEPLOYMENT_STARTED,
        LegacyEventType.DEPLOYMENT_COMPLETED: CanonicalEventType.DEPLOYMENT_COMPLETED,
        LegacyEventType.DEPLOYMENT_FAILED: CanonicalEventType.DEPLOYMENT_FAILED,
        LegacyEventType.DEPLOYMENT_ROLLED_BACK: CanonicalEventType.DEPLOYMENT_ROLLED_BACK,

        # Operations
        LegacyEventType.PRODUCTION_INCIDENT: CanonicalEventType.SERVICE_FAILED,
        LegacyEventType.METRICS_ALERT: CanonicalEventType.METRIC_EMITTED,
        LegacyEventType.LOG_ANOMALY_DETECTED: CanonicalEventType.METRIC_EMITTED,
        LegacyEventType.USER_FEEDBACK_RECEIVED: CanonicalEventType.METRIC_EMITTED,

        # Memory
        LegacyEventType.MEMORY_STORED: CanonicalEventType.MEMORY_STORED,
        LegacyEventType.MEMORY_RETRIEVED: CanonicalEventType.MEMORY_RETRIEVED,
        LegacyEventType.MEMORY_UPDATED: CanonicalEventType.MEMORY_UPDATED,
        LegacyEventType.MEMORY_CONSOLIDATED: CanonicalEventType.MEMORY_CONSOLIDATED,

        # Skill
        LegacyEventType.SKILL_LOADED: CanonicalEventType.SKILL_EXECUTED,
        LegacyEventType.SKILL_UNLOADED: CanonicalEventType.SKILL_FAILED,
        LegacyEventType.SKILL_EXECUTED: CanonicalEventType.SKILL_EXECUTED,
        LegacyEventType.SKILL_FAILED: CanonicalEventType.SKILL_FAILED,

        # MCP
        LegacyEventType.MCP_SERVER_CONNECTED: CanonicalEventType.MCP_TOOL_CALLED,
        LegacyEventType.MCP_SERVER_DISCONNECTED: CanonicalEventType.MCP_TOOL_FAILED,
        LegacyEventType.MCP_TOOL_CALLED: CanonicalEventType.MCP_TOOL_CALLED,
        LegacyEventType.MCP_TOOL_RESULT: CanonicalEventType.MCP_TOOL_SUCCEEDED,

        # Council
        LegacyEventType.COUNCIL_CONVENED: CanonicalEventType.COUNCIL_CONVENED,
        LegacyEventType.COUNCIL_DELIBERATED: CanonicalEventType.COUNCIL_VOTE_CAST,
        LegacyEventType.COUNCIL_DECIDED: CanonicalEventType.COUNCIL_CONSENSUS_REACHED,
        LegacyEventType.COUNCIL_DISSENTED: CanonicalEventType.COUNCIL_DISSENT_REGISTERED,

        # AI Agency
        LegacyEventType.SECURITY_AUDIT_REQUESTED: CanonicalEventType.AI_AGENT_AUDIT_EMITTED,
        LegacyEventType.SECURITY_AUDIT_COMPLETED: CanonicalEventType.AI_AGENT_AUDIT_EMITTED,
        LegacyEventType.PERFORMANCE_AUDIT_REQUESTED: CanonicalEventType.AI_AGENT_AUDIT_EMITTED,
        LegacyEventType.PERFORMANCE_AUDIT_COMPLETED: CanonicalEventType.AI_AGENT_AUDIT_EMITTED,
        LegacyEventType.CHAOS_EXPERIMENT_REQUESTED: CanonicalEventType.AI_AGENT_AUDIT_EMITTED,
        LegacyEventType.CHAOS_EXPERIMENT_COMPLETED: CanonicalEventType.AI_AGENT_AUDIT_EMITTED,
        LegacyEventType.ACCESSIBILITY_AUDIT_REQUESTED: CanonicalEventType.AI_AGENT_AUDIT_EMITTED,
        LegacyEventType.ACCESSIBILITY_AUDIT_COMPLETED: CanonicalEventType.AI_AGENT_AUDIT_EMITTED,
        LegacyEventType.DOCUMENTATION_AUDIT_REQUESTED: CanonicalEventType.AI_AGENT_AUDIT_EMITTED,
        LegacyEventType.DOCUMENTATION_AUDIT_COMPLETED: CanonicalEventType.AI_AGENT_AUDIT_EMITTED,
        LegacyEventType.CONCURRENCY_AUDIT_REQUESTED: CanonicalEventType.AI_AGENT_AUDIT_EMITTED,
        LegacyEventType.CONCURRENCY_AUDIT_COMPLETED: CanonicalEventType.AI_AGENT_AUDIT_EMITTED,
        LegacyEventType.BUG_HUNT_REQUESTED: CanonicalEventType.AI_AGENT_AUDIT_EMITTED,
        LegacyEventType.BUG_HUNT_COMPLETED: CanonicalEventType.AI_AGENT_AUDIT_EMITTED,
        LegacyEventType.ARCHITECTURE_VALIDATION_REQUESTED: CanonicalEventType.AI_AGENT_AUDIT_EMITTED,
        LegacyEventType.ARCHITECTURE_VALIDATION_COMPLETED: CanonicalEventType.AI_AGENT_AUDIT_EMITTED,
        LegacyEventType.FINAL_JUDGMENT_REQUESTED: CanonicalEventType.FINAL_JUDGE_DECISION,
        LegacyEventType.FINAL_JUDGMENT_COMPLETED: CanonicalEventType.FINAL_JUDGE_DECISION,

        # Checkpoint
        LegacyEventType.CHECKPOINT_CREATED: CanonicalEventType.CHECKPOINT_CREATED,
        LegacyEventType.CHECKPOINT_RESTORED: CanonicalEventType.CHECKPOINT_RESTORED,
        LegacyEventType.CHECKPOINT_DELETED: CanonicalEventType.CHECKPOINT_PRUNED,

        # Retry
        LegacyEventType.RETRY_BUDGET_EXHAUSTED: CanonicalEventType.RETRY_BUDGET_EXHAUSTED,
        LegacyEventType.RETRY_SCHEDULED: CanonicalEventType.RETRY_SCHEDULED,
        LegacyEventType.RETRY_EXECUTED: CanonicalEventType.RETRY_EXECUTED,

        # Root Cause
        LegacyEventType.ROOT_CAUSE_ANALYZED: CanonicalEventType.ROOT_CAUSE_ANALYZED,
        LegacyEventType.FAILURE_CLASSIFIED: CanonicalEventType.FAILURE_CLASSIFIED,

        # Learning
        LegacyEventType.LEARNING_CAPTURED: CanonicalEventType.AI_AGENT_AUDIT_EMITTED,
        LegacyEventType.PATTERN_EXTRACTED: CanonicalEventType.AI_AGENT_AUDIT_EMITTED,
        LegacyEventType.KNOWLEDGE_UPDATED: CanonicalEventType.AI_AGENT_AUDIT_EMITTED,

        # State
        LegacyEventType.STATE_TRANSITIONED: CanonicalEventType.STATE_CHANGED,
        LegacyEventType.STATE_CHECKPOINTED: CanonicalEventType.STATE_SNAPSHOT_CREATED,
        LegacyEventType.STATE_RESTORED: CanonicalEventType.STATE_RESTORED,

        # Service
        LegacyEventType.SERVICE_STARTED: CanonicalEventType.SERVICE_STARTED,
        LegacyEventType.SERVICE_STOPPED: CanonicalEventType.SERVICE_STOPPED,
        LegacyEventType.SERVICE_HEALTHY: CanonicalEventType.HEALTH_CHECK_PASSED,
        LegacyEventType.SERVICE_UNHEALTHY: CanonicalEventType.HEALTH_CHECK_FAILED,
    }

    # ----- event helpers ----------------------------------------------
    def subscribe(
        self,
        handler: Callable[[CoreEvent], Any],
        event_types: list[CanonicalEventType] | CanonicalEventType | LegacyEventType | list[LegacyEventType] | type | list[type],
        filter_fn: Callable[[CoreEvent], bool] | None = None,
    ) -> str:
        """Subscribe a handler, tracking the subscription for cleanup.

        Args:
            handler: Event handler (sync or async)
            event_types: Event type(s) to subscribe to (canonical EventType enum, legacy EventType enum, or concrete event classes)
            filter_fn: Optional filter function
        Returns:
            Subscription ID for later unsubscription
        """
        # Normalize to list
        if not isinstance(event_types, list):
            event_types = [event_types]

        # Extract canonical EventType from concrete event classes or legacy EventType if needed
        normalized_event_types = []
        for et in event_types:
            if isinstance(et, CanonicalEventType):
                normalized_event_types.append(et)
            elif isinstance(et, LegacyEventType):
                # Translate legacy EventType to canonical
                canonical = self._LEGACY_TO_CANONICAL.get(et)
                if canonical is None:
                    raise ValueError(f"No canonical EventType mapping for legacy {et}")
                normalized_event_types.append(canonical)
            elif isinstance(et, type) and hasattr(et, 'event_type'):
                # Concrete event class (e.g., PlanningRequested) - extract event_type
                legacy_et = et.event_type
                if isinstance(legacy_et, CanonicalEventType):
                    normalized_event_types.append(legacy_et)
                elif isinstance(legacy_et, LegacyEventType):
                    canonical = self._LEGACY_TO_CANONICAL.get(legacy_et)
                    if canonical is None:
                        raise ValueError(f"No canonical EventType mapping for legacy {legacy_et}")
                    normalized_event_types.append(canonical)
                else:
                    raise TypeError(f"Concrete event class has unknown event_type type: {type(legacy_et)}")
            else:
                raise TypeError(f"Expected EventType or event class, got {type(et)}")

        is_async = asyncio.iscoroutinefunction(handler)

        logger.debug(f"Service {self.name} subscribing to event types: {[str(et) for et in normalized_event_types]}")
        logger.info(f"Service {self.name} subscribing to event types: {[str(et) for et in normalized_event_types]}")
        options = SubscribeOptions(
            subscriber=self._identity,
            event_types=normalized_event_types,
            handler=handler,
            priority=HandlerPriority.NORMAL,
            filter=filter_fn,
            retry_policy=RetryPolicy(),
            metadata={"service_name": self.name, "instance_id": self._instance_id},
        )

        sub_id = self.event_bus.subscribe(options)
        logger.info(f"Service {self.name} subscribed with ID: {sub_id}")
        self._subscription_ids.append(sub_id)
        self._events_subscribed += len(normalized_event_types)
        return sub_id

    async def emit(self, event: CoreEvent) -> int:
        """Publish an event on the shared canonical event bus.

        Returns:
            1 if accepted, 0 if rejected
        """
        result = await self.event_bus.publish(event)
        logger.info(f"Service {self.name} emit result: accepted={result.accepted}, status={result.status}, eventId={result.eventId}, message={result.message}")
        if result.accepted:
            self._events_published += 1
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
            "events_published": self._events_published,
            "events_subscribed": self._events_subscribed,
            "last_error": self._error,
        }

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<{type(self).__name__} name={self.name!r} status={self._status.value}>"


__all__ = [
    "BaseService",
    "ServiceStatus",
    "ServiceInfo",
]