"""
Autonomous Objective Generator for AI-OS M10.

Generates self-directed objectives based on learning analytics, system stagnation
detection, or internal metrics. Emits PlanningRequested events with source=autonomous.

This is M10-N1 implementation per M10-IMPLEMENTATION-SPEC.md §11.1.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from aios.events.base import Event
from aios.events.types import PlanningRequested
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.payload import EventPayload
from aios.events.core.category import category_for_event_type
from aios.events.core.priority import EventPriority
from aios.events.core.types import EventType, SemanticVersion
from aios.services.base import BaseService

logger = logging.getLogger(__name__)


@dataclass
class ObjectiveConfig:
    """Configuration for AutonomousObjectiveGenerator bounds."""
    enabled: bool = False  # Disabled by default; enabled via config
    min_interval_seconds: int = 3600  # Minimum time between autonomous objectives
    max_concurrent_objectives: int = 3  # Maximum concurrent autonomous objectives
    stagnation_threshold: int = 3  # Number of failed/stalling workflows before triggering


@dataclass
class ObjectiveCandidate:
    """A candidate autonomous objective."""
    objective_id: str
    goal: str
    reason: str
    priority: float
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    learning_ids: list[str] = field(default_factory=list)


class AutonomousObjectiveGenerator(BaseService):
    """
    Generates autonomous objectives based on learning trends, system stagnation,
    or internal metrics. Emits PlanningRequested events with source=autonomous.

    M10-N1: Autonomous Objective Generator (GAP-M10-01)
    - Guarded: Disabled by default; enabled via services.objective_generator.enabled config
    - Unit tests: Objective generation logic, provenance marking, config gating
    """

    name = "objective_generator"
    version = "1.0.0"
    description = "Autonomous objective generation for self-directed planning"
    depends_on: list[str] = ["memory", "learning"]

    def __init__(
        self,
        config: ObjectiveConfig | None = None,
        event_bus=None,
        info=None,
        **kwargs,
    ):
        super().__init__(event_bus=event_bus, info=info)
        self._config = config or ObjectiveConfig()
        self._active_objectives: dict[str, ObjectiveCandidate] = {}
        self._last_generated: datetime | None = None
        self._event_bus = get_core_event_bus()

    @property
    def config(self) -> ObjectiveConfig:
        return self._config

    async def on_start(self) -> None:
        logger.info(f"AutonomousObjectiveGenerator.on_start called, enabled={self._config.enabled}")
        if self._config.enabled:
            # Subscribe to workflow completion events to detect stagnation
            from aios.events.types import WorkflowCompleted, WorkflowFailed
            self.subscribe(self._on_workflow_completed, WorkflowCompleted)
            self.subscribe(self._on_workflow_failed, WorkflowFailed)
            logger.info("AutonomousObjectiveGenerator subscribed to workflow events")
        else:
            logger.info("AutonomousObjectiveGenerator disabled by config")

    async def on_stop(self) -> None:
        self._active_objectives.clear()
        logger.info("AutonomousObjectiveGenerator stopped")

    async def _on_workflow_completed(self, event: Event) -> None:
        """Track successful workflow completions."""
        payload = event.payload.to_dict() if hasattr(event.payload, 'to_dict') else dict(event.payload)
        execution_id = payload.get("execution_id", "")
        if execution_id:
            logger.debug(f"Workflow completed: {execution_id}")

    async def _on_workflow_failed(self, event: Event) -> None:
        """Track failed workflows to detect stagnation patterns."""
        payload = event.payload.to_dict() if hasattr(event.payload, 'to_dict') else dict(event.payload)
        execution_id = payload.get("execution_id", "")
        error = payload.get("error", "")
        logger.warning(f"Workflow failed: {execution_id} - {error}")
        await self._check_stagnation_and_generate()

    def _can_generate(self) -> bool:
        """Check if generator can produce a new objective."""
        if not self._config.enabled:
            return False
        if len(self._active_objectives) >= self._config.max_concurrent_objectives:
            return False
        if self._last_generated:
            elapsed = (datetime.utcnow() - self._last_generated).total_seconds()
            if elapsed < self._config.min_interval_seconds:
                return False
        return True

    async def _check_stagnation_and_generate(self) -> None:
        """Check for stagnation patterns and generate objective if threshold met."""
        # In a real implementation, this would query workflow history
        # For now, we simulate stagnation detection
        if self._can_generate():
            await self._generate_stagnation_objective()

    async def _generate_stagnation_objective(self) -> ObjectiveCandidate:
        """Generate an objective to address system stagnation."""
        objective_id = f"obj_auto_{uuid.uuid4().hex[:12]}"
        candidate = ObjectiveCandidate(
            objective_id=objective_id,
            goal="Investigate and resolve workflow stagnation pattern",
            reason="stagnation_detected",
            priority=0.8,
            metadata={
                "trigger": "stagnation_pattern",
                "origin": "autonomous",
                "authority": "autonomous",
            },
        )
        self._active_objectives[objective_id] = candidate
        self._last_generated = datetime.utcnow()
        await self._emit_planning_requested(candidate)
        logger.info(f"Generated autonomous objective: {objective_id}")
        return candidate

    async def _generate_learning_objective(self) -> ObjectiveCandidate:
        """Generate an objective based on learning analytics."""
        if not self._can_generate():
            return None

        # Query learning service for patterns
        try:
            from aios.services.learning import get_learning_service
            learning_service = get_learning_service()
            recent_learnings = learning_service.get_learnings(limit=10)
        except Exception:
            recent_learnings = []

        objective_id = f"obj_auto_{uuid.uuid4().hex[:12]}"
        candidate = ObjectiveCandidate(
            objective_id=objective_id,
            goal="Apply recent learnings to improve system behavior",
            reason="learning_threshold",
            priority=0.6,
            metadata={
                "trigger": "learning_analytics",
                "origin": "autonomous",
                "authority": "autonomous",
                "learning_count": len(recent_learnings),
            },
            learning_ids=[l.get("learning_id", "") for l in recent_learnings],
        )
        self._active_objectives[objective_id] = candidate
        self._last_generated = datetime.utcnow()
        await self._emit_planning_requested(candidate)
        logger.info(f"Generated learning-based objective: {objective_id}")
        return candidate

    async def _emit_planning_requested(self, candidate: ObjectiveCandidate) -> None:
        """Emit PlanningRequested event with autonomous source."""
        if self._event_bus is None:
            logger.warning("EventBus not available, cannot emit PlanningRequested")
            return

        correlation_id = uuid.uuid4()

        core_event = CoreEvent(
            eventType=EventType.PLANNING_REQUESTED,
            source=ComponentIdentity(
                component_type=ComponentType.ENGINEERING_SERVICE,
                component_name=self.name,
                version=SemanticVersion.parse(self.version),
            ),
            correlationId=correlation_id,
            causationId=correlation_id,
            payload=EventPayload({
                "task_id": candidate.objective_id,
                "goal": candidate.goal,
                "reason": candidate.reason,
                "origin": "autonomous",
                "objective_authority": "autonomous",
                "objective_id": candidate.objective_id,
                "metadata": candidate.metadata,
                "learning_ids": candidate.learning_ids,
                # M10 provenance: autonomous action marker
                "autonomous": True,
                "authority_level": "autonomous",
            }),
            priority=EventPriority.NORMAL,
            category=category_for_event_type(EventType.PLANNING_REQUESTED),
        )

        try:
            result = await self._event_bus.publish(core_event)
            logger.info(f"Emitted autonomous PlanningRequested: {candidate.objective_id}, result={result}")
        except Exception as e:
            logger.error(f"Failed to emit autonomous PlanningRequested: {e}")

    def get_active_objectives(self) -> list[ObjectiveCandidate]:
        """Get currently active autonomous objectives."""
        return list(self._active_objectives.values())

    def mark_objective_completed(self, objective_id: str) -> bool:
        """Mark an autonomous objective as completed."""
        if objective_id in self._active_objectives:
            del self._active_objectives[objective_id]
            logger.info(f"Autonomous objective completed: {objective_id}")
            return True
        return False

    def get_stats(self) -> dict[str, Any]:
        stats = super().get_stats()
        stats.update({
            "enabled": self._config.enabled,
            "active_objectives": len(self._active_objectives),
            "max_concurrent": self._config.max_concurrent_objectives,
            "min_interval_seconds": self._config.min_interval_seconds,
            "last_generated": self._last_generated.isoformat() if self._last_generated else None,
        })
        return stats


# Global instance
_global_objective_generator: AutonomousObjectiveGenerator | None = None


def get_objective_generator(
    config: ObjectiveConfig | None = None,
) -> AutonomousObjectiveGenerator:
    """Get or create the global AutonomousObjectiveGenerator."""
    global _global_objective_generator
    if _global_objective_generator is None:
        _global_objective_generator = AutonomousObjectiveGenerator(config=config)
    return _global_objective_generator


def set_objective_generator(generator: AutonomousObjectiveGenerator) -> None:
    """Set the global AutonomousObjectiveGenerator."""
    global _global_objective_generator
    _global_objective_generator = generator


__all__ = [
    "AutonomousObjectiveGenerator",
    "ObjectiveConfig",
    "ObjectiveCandidate",
    "get_objective_generator",
    "set_objective_generator",
]