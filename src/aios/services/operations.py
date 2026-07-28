"""Operations Service.

Engineering Service for post-deployment monitoring. Deployment is not the
end: operations watches metrics/logs/user feedback and turns production
incidents into NEW engineering tasks (TaskCreated events). It never calls
Planning directly.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from aios.events.base import Event
from aios.events.types import (
    DeploymentCompleted,
    LogAnomalyDetected,
    MetricsAlert,
    ProductionIncident,
    TaskCreated,
    UserFeedbackReceived,
)
from aios.services.base import BaseService

logger = logging.getLogger(__name__)


class OperationsService(BaseService):
    """Monitor production and generate follow-up engineering tasks."""

    name = "operations"
    version = "1.0.0"
    description = "Monitoring, logs, metrics, incidents, follow-up tasks"
    depends_on: list[str] = ["deployment"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._incidents: list[dict[str, Any]] = []

    async def on_start(self) -> None:
        self.subscribe(self.handle_deployment_completed, DeploymentCompleted)
        self.subscribe(self.handle_incident, ProductionIncident)
        self.subscribe(self.handle_metrics_alert, MetricsAlert)
        self.subscribe(self.handle_log_anomaly, LogAnomalyDetected)
        self.subscribe(self.handle_user_feedback, UserFeedbackReceived)

    # ----- handlers --------------------------------------------------
    def handle_deployment_completed(self, event: Event) -> None:
        # Confirm monitoring is enabled for the new deployment; ops-only event.
        logger.info("Operations now monitoring deployment %s", event.payload)

    def handle_incident(self, event: Event) -> None:
        self._incidents.append(event.payload)
        self._emit_followup_task(
            event,
            goal=f"Investigate and resolve production incident: {event.payload.get('title','')}",
            severity=event.payload.get("severity", "high"),
        )

    def handle_metrics_alert(self, event: Event) -> None:
        # Only severe alerts spawn new tasks; minor alerts are observed.
        if event.payload.get("severity") in ("high", "critical"):
            self._emit_followup_task(
                event,
                goal=f"Address metrics alert: {event.payload.get('metric','')}",
                severity="high",
            )

    def handle_log_anomaly(self, event: Event) -> None:
        if event.payload.get("severity") in ("high", "critical"):
            self._emit_followup_task(
                event,
                goal=f"Investigate log anomaly: {event.payload.get('pattern','')}",
                severity="high",
            )

    def handle_user_feedback(self, event: Event) -> None:
        if event.payload.get("severity") in ("high", "critical"):
            self._emit_followup_task(
                event,
                goal=f"Act on user feedback: {event.payload.get('summary','')}",
                severity="high",
            )

    # ----- helpers ---------------------------------------------------
    def _emit_followup_task(self, event: Event, goal: str, severity: str) -> None:
        task_id = f"task_{uuid4().hex[:8]}"
        self.emit(
            TaskCreated(
                source_service=self.name,
                correlation_id=event.correlation_id,
                causation_id=event.correlation_id,
                payload={
                    "task_id": task_id,
                    "goal": goal,
                    "severity": severity,
                    "origin": "operations",
                    "trigger_event": event.event_type.value,
                },
            )
        )

    def stats(self) -> dict[str, Any]:
        return {"incidents_seen": len(self._incidents)}


__all__ = ["OperationsService"]