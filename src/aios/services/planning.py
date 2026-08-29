"""Planning Service.

Engineering Service responsible for task decomposition, scheduling, and
resource allocation. Consumes PlanningRequested / PlanRejected events and
emits PlanningCompleted / PlanningFailed. Planning never calls other services
directly; it relies on the Memory service (via events) and kernel managers.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4, UUID

from aios.events.base import Event
from aios.events.types import (
    PlanningCompleted,
    PlanningFailed,
    PlanningRequested,
    PlanRejected,
    TaskCreated,
)
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.types import EventType, SemanticVersion
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.payload import EventPayload
from aios.events.core.category import EventCategory, category_for_event_type
from aios.events.core.priority import EventPriority
from aios.services.base import BaseService

logger = logging.getLogger(__name__)


class PlanningService(BaseService):
    """Decompose a task into a plan (ordered steps + resources)."""

    name = "planning"
    version = "1.0.0"
    description = "Task decomposition, scheduling, resource allocation"
    depends_on: list[str] = ["memory"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def on_start(self) -> None:
        logger.info(f"PlanningService.on_start called")
        self.subscribe(self.handle_planning_requested, PlanningRequested)
        self.subscribe(self.handle_plan_rejected, PlanRejected)
        logger.info(f"PlanningService.on_start completed")

    # ----- event handlers -------------------------------------------
    async def handle_planning_requested(self, event: CoreEvent) -> None:
        """Handle PlanningRequested event and emit PlanningCompleted."""
        logger.info(f"PlanningService received event: {event.eventType}, correlationId: {event.correlationId}")
        payload = event.payload.to_dict() if hasattr(event.payload, 'to_dict') else dict(event.payload)
        plan = self.plan(payload)

        correlation_id = event.correlationId

        if plan is None:
            await self.emit_core_event(
                EventType.PLANNING_FAILED,
                {
                    "task_id": payload.get("task_id", ""),
                    "reason": "planning produced no steps",
                },
                correlation_id=correlation_id,
                causation_id=correlation_id,
            )
            return

        await self.emit_core_event(
            EventType.PLANNING_COMPLETED,
            {
                "task_id": payload.get("task_id", ""),
                "plan_id": plan["plan_id"],
                "steps": plan["steps"],
                "resources": plan["resources"],
                # M9-N3: advisory learning refs only — never directives.
                "advisory_context": plan.get("advisory_context", {}),
            },
            correlation_id=correlation_id,
            causation_id=correlation_id,
        )

    async def handle_plan_rejected(self, event: CoreEvent) -> None:
        """Handle PlanRejected event and re-plan with feedback."""
        payload = event.payload.to_dict() if hasattr(event.payload, 'to_dict') else dict(event.payload)
        correlation_id = event.correlationId

        await self.emit_core_event(
            EventType.PLANNING_REQUESTED,
            {
                "task_id": payload.get("task_id", ""),
                "reason": "plan rejected",
                "feedback": payload.get("feedback", {}),
                "previous_plan": payload.get("plan_id", ""),
            },
            correlation_id=correlation_id,
            causation_id=correlation_id,
        )

    async def emit_core_event(
        self,
        event_type: EventType,
        payload: dict[str, Any],
        correlation_id: UUID | None = None,
        causation_id: UUID | None = None,
    ) -> int:
        """Emit a canonical CoreEvent."""
        if correlation_id is None:
            correlation_id = uuid4()
        if causation_id is None:
            causation_id = correlation_id

        logger.info(f"PlanningService emitting event: {event_type}, correlation_id: {correlation_id}, payload: {payload}")
        core_event = CoreEvent(
            eventType=event_type,
            source=ComponentIdentity(
                component_type=ComponentType.ENGINEERING_SERVICE,
                component_name=self.name,
                version=SemanticVersion.parse(self.version),
            ),
            correlationId=correlation_id,
            causationId=causation_id,
            payload=EventPayload(payload),
            priority=EventPriority.NORMAL,
            category=category_for_event_type(event_type),
        )
        logger.info(f"PlanningService created event: eventId={core_event.eventId}, checksum={core_event.checksum}")
        result = await self.emit(core_event)
        logger.info(f"PlanningService emit result: {result}")
        return result

    # ----- API ------------------------------------------------------
    def plan(self, request: dict[str, Any]) -> dict[str, Any] | None:
        """Produce a simple, deterministic plan from a request.

        This is a deterministic planner suitable for tests and demos; it
        emits the canonical SDLC sequence so the Workflow Manager can drive
        the pipeline through events.

        M9-N3 (spec §11.3): relevant learnings are attached as
        ``advisory_context`` — advisory input only. They NEVER override
        Council/Judge authority or alter plan semantics; when no learning
        service is bound (minimal kernels) planning proceeds unchanged.
        """
        task_id = request.get("task_id", f"task_{uuid4().hex[:8]}")
        goal = request.get("goal") or request.get("description") or "undefined"
        steps = request.get("steps") or ["coding", "review", "testing", "deployment"]
        return {
            "plan_id": f"plan_{uuid4().hex[:8]}",
            "task_id": task_id,
            "goal": goal,
            "steps": list(steps),
            "resources": request.get("resources", {}),
            "advisory_context": self._collect_advisory_context(goal),
        }

    def _collect_advisory_context(self, objective: str) -> dict[str, Any]:
        """Gather advisory learnings for an objective (M9-N3).

        Guarded: the global LearningService may be absent in minimal kernels,
        and any retrieval failure must never block planning. The result is a
        plain payload field — consumers treat it as advisory context, not as
        instructions or verdicts (M9 §16 authority boundaries).
        """
        try:
            from aios.services.learning import get_learning_service

            service = get_learning_service()
        except RuntimeError:
            return {}
        try:
            learnings = service.query_relevant(objective, limit=5)
        except Exception as exc:  # noqa: BLE001 — advisory must not block planning
            logger.warning("Advisory learning retrieval failed (ignored): %s", exc)
            return {}
        return {
            "learnings": learnings,
            "source": "learning_service",
            "advisory": True,
        }


__all__ = ["PlanningService"]