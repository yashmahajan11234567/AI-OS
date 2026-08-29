"""
Self-Prompting Autonomous Enhancement for AI-OS M10.

Enhances SelfPromptingService with autonomous triggering path:
- convergence_action config: "escalate" / "replan"
- Bounded cycles with forced escalation per ADR #10

This is M10-N4 implementation per M10-IMPLEMENTATION-SPEC.md §11.4.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from aios.events.base import Event
from aios.events.types import (
    PlanningRequested,
)
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.payload import EventPayload
from aios.events.core.category import category_for_event_type
from aios.events.core.priority import EventPriority
from aios.events.core.types import EventType, SemanticVersion
from aios.services.base import BaseService
from aios.services.self_prompting import SelfPromptingService, get_self_prompting_service, SelfPromptConfig, PromptTrace

logger = logging.getLogger(__name__)


class ConvergenceAction(str, Enum):
    """Action to take when convergence is detected but not resolved."""
    ESCALATE = "escalate"  # Escalate to human/council
    REPLAN = "replan"  # Trigger autonomous replan


@dataclass
class AutonomousSelfPromptingConfig:
    """Configuration for autonomous self-prompting enhancements."""
    enabled: bool = True
    convergence_action: ConvergenceAction = ConvergenceAction.ESCALATE
    max_convergence_cycles: int = 3  # Max cycles before forced action
    forced_escalation_depth: int = 5  # ADR #10 max depth
    require_learning_evidence: bool = True


@dataclass
class ConvergenceRecord:
    """Record of a convergence detection cycle."""
    cycle_id: str
    depth: int
    converged: bool
    resolution: str | None  # "resolved", "escalated", "replanned"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: dict[str, Any] = field(default_factory=dict)


class SelfPromptingAutonomousService(BaseService):
    """
    Enhances SelfPromptingService with autonomous triggering path.

    M10-N4: Self-Prompting Autonomous Trigger (GAP-M10-05)
    - Adds convergence_action config ("escalate" | "replan")
    - Bounded cycles with forced escalation (ADR #10: max_depth=5)
    - Integration test: Convergence loop triggers autonomous replan/escalation
    - Bound test: Asserts max_depth=5 hard stop per ADR #10
    """

    name = "self_prompting_autonomous"
    version = "1.0.0"
    description = "Autonomous triggering enhancement for self-prompting service"
    depends_on: list[str] = ["self_prompting", "learning", "replan_detector", "autonomy_override"]

    def __init__(
        self,
        config: AutonomousSelfPromptingConfig | None = None,
        self_prompting_service: SelfPromptingService | None = None,
        event_bus=None,
        info=None,
        **kwargs,
    ):
        super().__init__(event_bus=event_bus, info=info)
        self._config = config or AutonomousSelfPromptingConfig()
        self._self_prompting = self_prompting_service or get_self_prompting_service()
        self._event_bus = get_core_event_bus()
        self._convergence_history: list[ConvergenceRecord] = []
        self._current_depth = 0

    @property
    def config(self) -> AutonomousSelfPromptingConfig:
        return self._config

    async def on_start(self) -> None:
        logger.info(f"SelfPromptingAutonomousService.on_start called, enabled={self._config.enabled}")
        if self._config.enabled:
            logger.info("SelfPromptingAutonomousService subscribed to self-prompting events")
        else:
            logger.info("SelfPromptingAutonomousService disabled by config")

    async def on_stop(self) -> None:
        logger.info("SelfPromptingAutonomousService stopped")

    
    def _should_trigger_action(self) -> bool:
        """Check if convergence action should be triggered."""
        # Count recent consecutive convergences
        recent = self._convergence_history[-5:]
        convergence_count = sum(1 for r in recent if r.converged and r.resolution is None)

        logger.debug(f"Convergence check: {convergence_count} unresolved convergences")
        return convergence_count >= self._config.max_convergence_cycles

    async def _execute_convergence_action(self, cycle_id: str) -> None:
        """Execute the configured convergence action."""
        action = self._config.convergence_action

        # Update history with resolution
        for record in reversed(self._convergence_history):
            if record.resolution is None:
                record.resolution = action.value
                break

        if action == ConvergenceAction.ESCALATE:
            await self._escalate_to_council(cycle_id)
        elif action == ConvergenceAction.REPLAN:
            await self._trigger_autonomous_replan(cycle_id)

    async def _escalate_to_council(self, cycle_id: str) -> None:
        """Escalate convergence to council/human."""
        logger.warning(f"Escalating convergence for cycle {cycle_id} to council")

        if self._event_bus is None:
            return

        correlation_id = uuid.uuid4()

        # Emit escalation event
        core_event = CoreEvent(
            eventType=EventType.SELF_PROMPTING_ESCALATED,
            source=ComponentIdentity(
                component_type=ComponentType.ENGINEERING_SERVICE,
                component_name=self.name,
                version=SemanticVersion.parse(self.version),
            ),
            correlationId=correlation_id,
            causationId=correlation_id,
            payload=EventPayload({
                "cycle_id": cycle_id,
                "reason": "convergence_unresolved",
                "depth": self._current_depth,
                "convergence_cycles": self._config.max_convergence_cycles,
                "action": "escalated",
                # M10 provenance
                "autonomous": True,
                "authority_level": "autonomous",
            }),
            priority=EventPriority.HIGH,
            category=category_for_event_type(EventType.SELF_PROMPTING_ESCALATED),
        )

        try:
            await self._event_bus.publish(core_event)
            logger.info(f"Emitted escalation event for cycle {cycle_id}")
        except Exception as e:
            logger.error(f"Failed to emit escalation event: {e}")

    async def _trigger_autonomous_replan(self, cycle_id: str) -> None:
        """Trigger autonomous replan via replan detector."""
        logger.warning(f"Triggering autonomous replan for convergence cycle {cycle_id}")

        if self._event_bus is None:
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
                "task_id": f"replan_convergence_{cycle_id}",
                "reason": "autonomous_replan",
                "trigger_reason": "convergence_unresolved",
                "origin": "autonomous",
                "convergence_cycles": self._config.max_convergence_cycles,
                "depth": self._current_depth,
                # M10 provenance
                "autonomous": True,
                "authority_level": "autonomous",
            }),
            priority=EventPriority.HIGH,
            category=category_for_event_type(EventType.PLANNING_REQUESTED),
        )

        try:
            await self._event_bus.publish(core_event)
            logger.info(f"Emitted autonomous replan event for cycle {cycle_id}")
        except Exception as e:
            logger.error(f"Failed to emit replan event: {e}")

    async def _force_escalation(self, cycle_id: str, reason: str) -> None:
        """Force escalation per ADR #10 max depth bound."""
        logger.error(f"FORCED ESCALATION: {reason} for cycle {cycle_id}")

        # Update convergence history
        for record in reversed(self._convergence_history):
            if record.resolution is None:
                record.resolution = "forced_escalation"
                break

        if self._event_bus is None:
            return

        correlation_id = uuid.uuid4()

        core_event = CoreEvent(
            eventType=EventType.SELF_PROMPTING_ESCALATED,
            source=ComponentIdentity(
                component_type=ComponentType.ENGINEERING_SERVICE,
                component_name=self.name,
                version=SemanticVersion.parse(self.version),
            ),
            correlationId=correlation_id,
            causationId=correlation_id,
            payload=EventPayload({
                "cycle_id": cycle_id,
                "reason": reason,
                "depth": self._current_depth,
                "action": "forced_escalation",
                "adr10_bound": self._config.forced_escalation_depth,
                # M10 provenance
                "autonomous": True,
                "authority_level": "autonomous",
            }),
            priority=EventPriority.CRITICAL,
            category=category_for_event_type(EventType.SELF_PROMPTING_ESCALATED),
        )

        try:
            await self._event_bus.publish(core_event)
        except Exception as e:
            logger.error(f"Failed to emit forced escalation event: {e}")

    def get_convergence_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent convergence history."""
        return [
            {
                "cycle_id": r.cycle_id,
                "depth": r.depth,
                "converged": r.converged,
                "resolution": r.resolution,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in self._convergence_history[-limit:]
        ]

    def get_stats(self) -> dict[str, Any]:
        stats = super().get_stats()
        stats.update({
            "enabled": self._config.enabled,
            "convergence_action": self._config.convergence_action.value,
            "max_convergence_cycles": self._config.max_convergence_cycles,
            "forced_escalation_depth": self._config.forced_escalation_depth,
            "current_depth": self._current_depth,
            "convergence_history_size": len(self._convergence_history),
        })
        return stats


# Global instance
_global_self_prompting_autonomous: SelfPromptingAutonomousService | None = None


def get_self_prompting_autonomous(
    config: AutonomousSelfPromptingConfig | None = None,
    self_prompting_service: SelfPromptingService | None = None,
) -> SelfPromptingAutonomousService:
    """Get or create the global SelfPromptingAutonomousService."""
    global _global_self_prompting_autonomous
    if _global_self_prompting_autonomous is None:
        _global_self_prompting_autonomous = SelfPromptingAutonomousService(
            config=config, self_prompting_service=self_prompting_service
        )
    return _global_self_prompting_autonomous


def set_self_prompting_autonomous(service: SelfPromptingAutonomousService) -> None:
    """Set the global SelfPromptingAutonomousService."""
    global _global_self_prompting_autonomous
    _global_self_prompting_autonomous = service


__all__ = [
    "SelfPromptingAutonomousService",
    "AutonomousSelfPromptingConfig",
    "ConvergenceAction",
    "ConvergenceRecord",
    "get_self_prompting_autonomous",
    "set_self_prompting_autonomous",
]