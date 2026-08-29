"""
Learning Application Feedback Loop for AI-OS M10.

Extends LearningService to retrieve and apply learnings during autonomous
objective generation and replanning, closing the advisory-only loop.

This is M10-N5 implementation per M10-IMPLEMENTATION-SPEC.md §11.5.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from aios.events.base import Event
from aios.events.types import LearningCaptured, PlanningRequested
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.payload import EventPayload
from aios.events.core.category import category_for_event_type
from aios.events.core.priority import EventPriority
from aios.events.core.types import EventType, SemanticVersion
from aios.services.base import BaseService
from aios.services.learning import LearningService, get_learning_service

logger = logging.getLogger(__name__)


@dataclass
class LearningApplyConfig:
    """Configuration for LearningApplyService."""
    enabled: bool = False  # Disabled by default; enabled via config
    auto_apply_on_objective: bool = True  # Auto-apply learnings when objectives created
    confidence_threshold: float = 0.6  # Minimum confidence for auto-application
    max_applications_per_hour: int = 20


@dataclass
class AppliedLearning:
    """Record of a learning application."""
    application_id: str
    learning_id: str
    context: str  # "objective_generation", "replanning", "workflow_execution"
    objective_id: str | None
    workflow_id: str | None
    applied_at: datetime = field(default_factory=datetime.utcnow)
    confidence: float = 0.0
    result: str = "pending"  # "pending", "success", "failed"
    metadata: dict[str, Any] = field(default_factory=dict)


class LearningApplyService(BaseService):
    """
    Extends LearningService with retrieval and application for autonomous operations.

    M10-N5: Learning Application Feedback Loop (GAP-M10-06)
    - Retrieves relevant learnings during objective generation/replanning
    - Applies learnings and tracks application outcomes
    - Emits LearningApplied events with autonomous provenance
    - Closes the advisory-only loop from M8/M9
    """

    name = "learning_apply"
    version = "1.0.0"
    description = "Learning retrieval and application for autonomous operations"
    depends_on: list[str] = ["memory", "learning", "objective_generator", "replan_detector"]

    def __init__(
        self,
        config: LearningApplyConfig | None = None,
        learning_service: LearningService | None = None,
        event_bus=None,
        info=None,
        **kwargs,
    ):
        super().__init__(event_bus=event_bus, info=info)
        self._config = config or LearningApplyConfig()
        self._learning_service = learning_service or get_learning_service()
        self._event_bus = get_core_event_bus()
        self._applications: list[AppliedLearning] = []
        self._application_count = 0
        self._last_application_time: datetime | None = None

    @property
    def config(self) -> LearningApplyConfig:
        return self._config

    async def on_start(self) -> None:
        logger.info(f"LearningApplyService.on_start called, enabled={self._config.enabled}")
        if self._config.enabled:
            self.subscribe(self._on_learning_captured, LearningCaptured)
            self.subscribe(self._on_planning_requested, PlanningRequested)
            logger.info("LearningApplyService subscribed to learning/planning events")
        else:
            logger.info("LearningApplyService disabled by config")

    async def on_stop(self) -> None:
        logger.info("LearningApplyService stopped")

    async def _on_learning_captured(self, event: Event) -> None:
        """Track newly captured learnings."""
        payload = event.payload.to_dict() if hasattr(event.payload, 'to_dict') else dict(event.payload)
        learning_id = payload.get("learning_id", "")
        logger.debug(f"New learning captured: {learning_id}")

    async def _on_planning_requested(self, event: Event) -> None:
        """React to planning requests - apply relevant learnings if autonomous."""
        payload = event.payload.to_dict() if hasattr(event.payload, 'to_dict') else dict(event.payload)
        is_autonomous = payload.get("autonomous", False)
        objective_id = payload.get("objective_id") or payload.get("task_id", "")

        if is_autonomous and self._config.auto_apply_on_objective:
            await self._apply_relevant_learnings(objective_id, "objective_generation", payload)

    async def _apply_relevant_learnings(
        self,
        objective_id: str,
        context: str,
        trigger_payload: dict[str, Any],
    ) -> list[AppliedLearning]:
        """Retrieve and apply relevant learnings for a given context."""
        if not self._config.enabled:
            return []

        # Rate limiting
        if self._last_application_time:
            elapsed = (datetime.utcnow() - self._last_application_time).total_seconds()
            if elapsed < 3600 and self._application_count >= self._config.max_applications_per_hour:
                logger.warning("Learning application rate limit exceeded")
                return []

        # Get relevant learnings from LearningService
        learnings = self._learning_service.get_learnings(limit=50)
        if not learnings:
            logger.debug("No learnings available for application")
            return []

        # Filter for relevant learnings based on context
        relevant = self._filter_relevant_learnings(learnings, trigger_payload, context)
        applied = []

        for learning in relevant:
            if learning.get("confidence", 0) >= self._config.confidence_threshold:
                applied_learning = await self._apply_single_learning(
                    learning, objective_id, context, trigger_payload
                )
                if applied_learning:
                    applied.append(applied_learning)

        self._application_count += len(applied)
        self._last_application_time = datetime.utcnow()

        logger.info(f"Applied {len(applied)} learnings for {context} objective {objective_id}")
        return applied

    def _filter_relevant_learnings(
        self,
        learnings: list[dict[str, Any]],
        trigger_payload: dict[str, Any],
        context: str,
    ) -> list[dict[str, Any]]:
        """Filter learnings relevant to the current context."""
        relevant = []
        workflow_id = trigger_payload.get("workflow_id", "").lower()
        goal = trigger_payload.get("goal", "").lower()

        for learning in learnings:
            # Match based on workflow similarity
            learning_wf = learning.get("workflow_id", "").lower()
            learning_context = learning.get("context", "").lower()
            learning_tags = learning.get("tags", [])

            # Score relevance
            score = 0
            if workflow_id and workflow_id == learning_wf:
                score += 0.5
            if goal and any(tag in goal for tag in learning_tags):
                score += 0.3
            if context in learning_context:
                score += 0.2

            if score > 0.2:  # Threshold for relevance
                learning["relevance_score"] = score
                relevant.append(learning)

        # Sort by relevance and confidence
        relevant.sort(key=lambda x: (x.get("relevance_score", 0), x.get("confidence", 0)), reverse=True)
        return relevant[:10]  # Top 10 most relevant

    async def _apply_single_learning(
        self,
        learning: dict[str, Any],
        objective_id: str,
        context: str,
        trigger_payload: dict[str, Any],
    ) -> AppliedLearning | None:
        """Apply a single learning and track the application."""
        learning_id = learning.get("learning_id", "")
        if not learning_id:
            return None

        application_id = f"apply_{learning_id}_{datetime.utcnow().timestamp()}"

        applied = AppliedLearning(
            application_id=application_id,
            learning_id=learning_id,
            context=context,
            objective_id=objective_id,
            workflow_id=trigger_payload.get("workflow_id"),
            confidence=learning.get("confidence", 0),
            result="pending",
            metadata={
                "learning_summary": learning.get("summary", ""),
                "learning_tags": learning.get("tags", []),
                "relevance_score": learning.get("relevance_score", 0),
            },
        )

        # Record the application
        self._applications.append(applied)

        # Emit LearningApplied event
        await self._emit_learning_applied(applied, learning)

        return applied

    async def _emit_learning_applied(
        self,
        applied: AppliedLearning,
        learning: dict[str, Any],
    ) -> None:
        """Emit LearningApplied event with autonomous provenance."""
        if self._event_bus is None:
            return

        import uuid
        correlation_id = uuid.uuid4()

        # Use generic AI_AGENT_AUDIT_EMITTED for learning applied
        core_event = CoreEvent(
            eventType=EventType.AI_AGENT_AUDIT_EMITTED,
            source=ComponentIdentity(
                component_type=ComponentType.ENGINEERING_SERVICE,
                component_name=self.name,
                version=SemanticVersion.parse(self.version),
            ),
            correlationId=correlation_id,
            causationId=correlation_id,
            payload=EventPayload({
                "audit_id": applied.application_id,
                "event_subtype": "LEARNING_APPLIED",
                "learning_id": applied.learning_id,
                "context": applied.context,
                "objective_id": applied.objective_id,
                "workflow_id": applied.workflow_id,
                "confidence": applied.confidence,
                "result": applied.result,
                "learning_summary": learning.get("summary", ""),
                "learning_tags": learning.get("tags", []),
                # M10 provenance: autonomous application marker
                "autonomous": True,
                "authority_level": "autonomous",
                "judgment_source": "autonomous_independent",
            }),
            priority=EventPriority.NORMAL,
            category=category_for_event_type(EventType.AI_AGENT_AUDIT_EMITTED),
        )

        try:
            await self._event_bus.publish(core_event)
            logger.debug(f"Emitted LearningApplied: {applied.application_id}")
        except Exception as e:
            logger.error(f"Failed to emit LearningApplied: {e}")

    async def mark_application_result(
        self,
        application_id: str,
        result: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Mark the result of a learning application (success/failed)."""
        for applied in self._applications:
            if applied.application_id == application_id:
                applied.result = result
                if metadata:
                    applied.metadata.update(metadata)
                logger.info(f"Learning application {application_id} marked as {result}")
                return True
        return False

    def get_applications(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent learning applications."""
        return [
            {
                "application_id": a.application_id,
                "learning_id": a.learning_id,
                "context": a.context,
                "objective_id": a.objective_id,
                "workflow_id": a.workflow_id,
                "applied_at": a.applied_at.isoformat(),
                "confidence": a.confidence,
                "result": a.result,
            }
            for a in self._applications[-limit:]
        ]

    def get_stats(self) -> dict[str, Any]:
        stats = super().get_stats()
        stats.update({
            "enabled": self._config.enabled,
            "total_applications": len(self._applications),
            "successful_applications": sum(1 for a in self._applications if a.result == "success"),
            "failed_applications": sum(1 for a in self._applications if a.result == "failed"),
            "pending_applications": sum(1 for a in self._applications if a.result == "pending"),
            "confidence_threshold": self._config.confidence_threshold,
        })
        return stats


# Global instance
_global_learning_apply: LearningApplyService | None = None


def get_learning_apply(
    config: LearningApplyConfig | None = None,
    learning_service: LearningService | None = None,
) -> LearningApplyService:
    """Get or create the global LearningApplyService."""
    global _global_learning_apply
    if _global_learning_apply is None:
        _global_learning_apply = LearningApplyService(config=config, learning_service=learning_service)
    return _global_learning_apply


def set_learning_apply(service: LearningApplyService) -> None:
    """Set the global LearningApplyService."""
    global _global_learning_apply
    _global_learning_apply = service


__all__ = [
    "LearningApplyService",
    "LearningApplyConfig",
    "AppliedLearning",
    "get_learning_apply",
    "set_learning_apply",
]