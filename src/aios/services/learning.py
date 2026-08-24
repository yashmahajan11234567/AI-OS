"""Learning Service.

Engineering Service that captures learnings from successful projects and
failures and stores them as Engineering Intelligence (a memory category), so
future workflows can reuse them. It consumes RootCauseResolved / WorkflowCompleted /
TestingCompleted / DeploymentCompleted and emits LearningCaptured events.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import uuid4

from aios.events.base import Event
from aios.events.types import (
    LearningCaptured,
    RootCauseResolved,
)
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.types import EventType as CanonicalEventType, SemanticVersion
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.payload import EventPayload
from aios.events.core.category import category_for_event_type
from aios.events.core.priority import EventPriority
from aios.services.base import BaseService

logger = logging.getLogger(__name__)


class LearningService(BaseService):
    """Capture successes, failures, decisions as Engineering Intelligence."""

    name = "learning"
    version = "1.0.0"
    description = "Pattern extraction, learnings, engineering intelligence"
    depends_on: list[str] = ["memory"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._learnings: list[dict[str, Any]] = []

    async def on_start(self) -> None:
        self.subscribe(self.handle_root_cause_resolved, RootCauseResolved)
        # Register this instance globally for RootCauseAnalyzer to access
        set_learning_service_instance(self)

    async def _emit_legacy_event(self, event: Event) -> int:
        """Emit a legacy event by converting to CoreEvent."""
        from aios.services.base import BaseService

        # If legacy_event_type is already a canonical EventType, use it directly
        legacy_event_type = event.event_type
        if isinstance(legacy_event_type, CanonicalEventType):
            canonical_type = legacy_event_type
        else:
            # Otherwise look up in the legacy mapping
            canonical_type = BaseService._LEGACY_TO_CANONICAL.get(legacy_event_type)
            if canonical_type is None:
                logger.warning(f"No canonical mapping for legacy event type: {legacy_event_type}")
                canonical_type = CanonicalEventType.AI_AGENT_AUDIT_EMITTED

        # Always generate a proper UUID for correlationId
        import uuid
        correlation_uuid = uuid.uuid4()

        core_event = CoreEvent(
            eventType=canonical_type,
            source=ComponentIdentity(
                component_type=ComponentType.ENGINEERING_SERVICE,
                component_name=self.name,
                version=SemanticVersion.parse(self.version),
            ),
            correlationId=correlation_uuid,
            causationId=uuid.uuid4(),
            payload=EventPayload(event.payload),
            priority=EventPriority.NORMAL,
            category=category_for_event_type(canonical_type),
        )

        result = await self.emit(core_event)
        logger.info(f"LearningService emit legacy event {legacy_event_type} -> {canonical_type}: {result}")
        return result

    async def handle_root_cause_resolved(self, event: Event) -> None:
        learning = {
            "learning_id": f"learn_{uuid4().hex[:8]}",
            "type": "failure_resolution",
            "analysis_id": event.payload.get("analysis_id", ""),
            "resolution": event.payload.get("resolution", ""),
            "preventive_measures": event.payload.get("preventive_measures", []),
            "captured_at": time.time(),
        }
        self._learnings.append(learning)
        await self._emit_legacy_event(
            LearningCaptured(
                source_service=self.name,
                correlation_id=event.correlation_id,
                causation_id=event.correlation_id,
                payload=learning,
            )
        )

    async def capture_learning_from_analysis(
        self,
        analysis_id: str,
        failure_category: str,
        recommended_action: str,
        root_cause: str,
        preventive_measures: list[str],
    ) -> None:
        """Capture learning directly from RootCauseAnalysis without waiting for resolution.

        This is called by RootCauseAnalyzer to immediately capture learnings from
        the analysis phase, before the actual resolution is implemented.
        """
        logger.info(f"LearningService.capture_learning_from_analysis called with analysis_id={analysis_id}")
        print(f"LEARNING SERVICE: capture_learning_from_analysis called with analysis_id={analysis_id}")
        learning = {
            "learning_id": f"learn_{uuid4().hex[:8]}",
            "type": "failure_resolution",
            "analysis_id": analysis_id,
            "resolution": recommended_action,
            "preventive_measures": preventive_measures,
            "captured_at": time.time(),
            "root_cause": root_cause,
            "failure_category": failure_category,
        }
        self._learnings.append(learning)
        logger.info(f"LearningService added learning, total learnings: {len(self._learnings)}")
        print(f"LEARNING SERVICE: Added learning, total learnings: {len(self._learnings)}")
        await self._emit_legacy_event(
            LearningCaptured(
                source_service=self.name,
                correlation_id=analysis_id,
                causation_id=analysis_id,
                payload=learning,
            )
        )
        logger.info(f"LearningService emitted LearningCaptured event")
        print(f"LEARNING SERVICE: Emitted LearningCaptured event")

    def stats(self) -> dict[str, Any]:
        return {"learnings_captured": len(self._learnings)}


_learning_service_instance: LearningService | None = None


def set_learning_service_instance(instance: LearningService) -> None:
    """Set the global LearningService instance."""
    global _learning_service_instance
    _learning_service_instance = instance


def get_learning_service() -> LearningService:
    """Get the global LearningService instance."""
    if _learning_service_instance is None:
        raise RuntimeError("LearningService not initialized. Call set_learning_service_instance first.")
    return _learning_service_instance


__all__ = ["LearningService", "set_learning_service_instance", "get_learning_service"]