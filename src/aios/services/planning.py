"""Planning Service.

Engineering Service responsible for task decomposition, scheduling, and
resource allocation. Consumes PlanningRequested / PlanRejected events and
emits PlanningCompleted / PlanningFailed. Planning never calls other services
directly; it relies on the Memory service (via events) and kernel managers.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from aios.events.base import Event
from aios.events.types import (
    PlanningCompleted,
    PlanningFailed,
    PlanningRequested,
    PlanRejected,
    TaskCreated,
)
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
        self.subscribe(self.handle_planning_requested, PlanningRequested)
        self.subscribe(self.handle_plan_rejected, PlanRejected)

    # ----- event handlers -------------------------------------------
    def handle_planning_requested(self, event: Event) -> None:
        plan = self.plan(event.payload)
        if plan is None:
            self.emit(
                PlanningFailed(
                    source_service=self.name,
                    correlation_id=event.correlation_id,
                    causation_id=event.correlation_id,
                    payload={
                        "task_id": event.payload.get("task_id", ""),
                        "reason": "planning produced no steps",
                    },
                )
            )
            return
        self.emit(
            PlanningCompleted(
                source_service=self.name,
                correlation_id=event.correlation_id,
                causation_id=event.correlation_id,
                payload={
                    "task_id": event.payload.get("task_id", ""),
                    "plan_id": plan["plan_id"],
                    "steps": plan["steps"],
                    "resources": plan["resources"],
                },
            )
        )

    def handle_plan_rejected(self, event: Event) -> None:
        # Review/council rejected a plan -> re-plan with the feedback
        self.emit(
            PlanningRequested(
                source_service=self.name,
                correlation_id=event.correlation_id,
                causation_id=event.correlation_id,
                payload={
                    "task_id": event.payload.get("task_id", ""),
                    "reason": "plan rejected",
                    "feedback": event.payload.get("feedback", {}),
                    "previous_plan": event.payload.get("plan_id", ""),
                },
            )
        )

    # ----- API ------------------------------------------------------
    def plan(self, request: dict[str, Any]) -> dict[str, Any] | None:
        """Produce a simple, deterministic plan from a request.

        This is a deterministic planner suitable for tests and demos; it
        emits the canonical SDLC sequence so the Workflow Manager can drive
        the pipeline through events.
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
        }


__all__ = ["PlanningService"]