"""
Adaptive Replan Detector for AI-OS M10.

Monitors workflow execution for stagnation patterns (no progress, repeating failures)
and emits PlanningRequested events with trigger_reason=stagnation_pattern.

This is M10-N2 implementation per M10-IMPLEMENTATION-SPEC.md §11.2.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from aios.events.base import Event
from aios.events.types import WorkflowCompleted, WorkflowFailed, PlanningRequested
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
class ReplanDetectorConfig:
    """Configuration for AdaptiveReplanDetector."""
    enabled: bool = True
    sensitivity: float = 0.7  # Stagnation detection sensitivity (0.0-1.0)
    min_workflows_for_analysis: int = 3  # Minimum workflows before analysis
    max_replan_depth: int = 3  # Maximum consecutive autonomous replans
    stagnation_window: int = 5  # Number of recent workflows to analyze


@dataclass
class WorkflowExecutionRecord:
    """Record of a workflow execution for stagnation analysis."""
    execution_id: str
    workflow_id: str
    status: str
    error: str | None = None
    step_results: dict[str, Any] = field(default_factory=dict)
    completed_steps: list[str] = field(default_factory=list)
    failed_steps: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: datetime | None = None
    duration_seconds: float = 0.0
    replan_depth: int = 0


class AdaptiveReplanDetector(BaseService):
    """
    Monitors workflow execution for stagnation patterns and triggers autonomous replanning.

    M10-N2: Self-Directed Replanning Trigger (GAP-M10-02)
    - Monitors for: no progress, repeating failure patterns
    - Emits PlanningRequested with trigger_reason=stagnation_pattern
    - Integration test: Closed loop with stagnation detection triggering autonomous replan
    """

    name = "replan_detector"
    version = "1.0.0"
    description = "Adaptive replan detection for autonomous workflow recovery"
    depends_on: list[str] = ["memory"]

    def __init__(
        self,
        config: ReplanDetectorConfig | None = None,
        event_bus=None,
        info=None,
        **kwargs,
    ):
        super().__init__(event_bus=event_bus, info=info)
        self._config = config or ReplanDetectorConfig()
        self._execution_history: list[WorkflowExecutionRecord] = []
        self._replan_depths: dict[str, int] = {}  # workflow_id -> current replan depth
        self._event_bus = get_core_event_bus()

    @property
    def config(self) -> ReplanDetectorConfig:
        return self._config

    async def on_start(self) -> None:
        logger.info(f"AdaptiveReplanDetector.on_start called, enabled={self._config.enabled}")
        if self._config.enabled:
            self.subscribe(self._on_workflow_completed, WorkflowCompleted)
            self.subscribe(self._on_workflow_failed, WorkflowFailed)
            logger.info("AdaptiveReplanDetector subscribed to workflow events")
        else:
            logger.info("AdaptiveReplanDetector disabled by config")

    async def on_stop(self) -> None:
        self._execution_history.clear()
        self._replan_depths.clear()
        logger.info("AdaptiveReplanDetector stopped")

    async def _on_workflow_completed(self, event: Event) -> None:
        """Record successful workflow completion."""
        payload = event.payload.to_dict() if hasattr(event.payload, 'to_dict') else dict(event.payload)
        execution_id = payload.get("execution_id", "")
        workflow_id = payload.get("workflow_id", "")

        record = WorkflowExecutionRecord(
            execution_id=execution_id,
            workflow_id=workflow_id,
            status="completed",
            ended_at=datetime.utcnow(),
        )
        self._execution_history.append(record)
        self._trim_history()
        logger.debug(f"Recorded workflow completion: {execution_id}")

    async def _on_workflow_failed(self, event: Event) -> None:
        """Record failed workflow and check for stagnation."""
        payload = event.payload.to_dict() if hasattr(event.payload, 'to_dict') else dict(event.payload)
        execution_id = payload.get("execution_id", "")
        workflow_id = payload.get("workflow_id", "")
        error = payload.get("error", "")

        record = WorkflowExecutionRecord(
            execution_id=execution_id,
            workflow_id=workflow_id,
            status="failed",
            error=error,
            ended_at=datetime.utcnow(),
        )
        self._execution_history.append(record)
        self._trim_history()

        logger.warning(f"Recorded workflow failure: {execution_id} - {error}")
        await self._analyze_and_trigger_replan(workflow_id)

    
    def _trim_history(self) -> None:
        """Keep only recent execution history."""
        max_history = self._config.stagnation_window * 3
        if len(self._execution_history) > max_history:
            self._execution_history = self._execution_history[-max_history:]

    def _get_recent_workflows(self, workflow_id: str, limit: int) -> list[WorkflowExecutionRecord]:
        """Get recent executions for a specific workflow."""
        return [
            r for r in self._execution_history
            if r.workflow_id == workflow_id
        ][-limit:]

    def _detect_stagnation(self, workflow_id: str) -> tuple[bool, str, float]:
        """
        Detect stagnation patterns in recent workflow executions.

        Returns:
            (is_stagnant, trigger_reason, confidence)
        """
        recent = self._get_recent_workflows(workflow_id, self._config.stagnation_window)
        if len(recent) < self._config.min_workflows_for_analysis:
            return False, "insufficient_data", 0.0

        # Check for repeated failures
        failures = [r for r in recent if r.status == "failed"]
        failure_rate = len(failures) / len(recent)

        # Check for no progress (same steps failing)
        failed_steps_sets = [set(r.failed_steps) for r in failures]
        if len(failed_steps_sets) >= 2:
            # Check intersection of failed steps
            common_failed = set.intersection(*failed_steps_sets) if failed_steps_sets else set()
            repeating_failure_ratio = len(common_failed) / max(len(failed_steps_sets[0]), 1)
        else:
            repeating_failure_ratio = 0.0

        # Check for short durations (immediate failures)
        short_durations = [r for r in recent if r.duration_seconds < 10]
        quick_failure_ratio = len(short_durations) / len(recent) if recent else 0.0

        # Calculate stagnation score
        stagnation_score = (
            failure_rate * 0.5 +
            repeating_failure_ratio * 0.3 +
            quick_failure_ratio * 0.2
        )

        is_stagnant = stagnation_score >= self._config.sensitivity

        if is_stagnant:
            if repeating_failure_ratio > 0.5:
                trigger_reason = "repeating_failure_pattern"
            elif failure_rate > 0.8:
                trigger_reason = "high_failure_rate"
            elif quick_failure_ratio > 0.5:
                trigger_reason = "quick_failure_cascade"
            else:
                trigger_reason = "stagnation_pattern"
            return True, trigger_reason, stagnation_score

        return False, "no_stagnation", stagnation_score

    async def _analyze_and_trigger_replan(self, workflow_id: str) -> None:
        """Analyze workflow history and trigger autonomous replan if needed."""
        if not self._config.enabled:
            return

        # Check replan depth limit
        current_depth = self._replan_depths.get(workflow_id, 0)
        if current_depth >= self._config.max_replan_depth:
            logger.warning(f"Max replan depth ({self._config.max_replan_depth}) reached for {workflow_id}, not triggering replan")
            return

        is_stagnant, trigger_reason, confidence = self._detect_stagnation(workflow_id)
        if not is_stagnant:
            logger.debug(f"No stagnation detected for {workflow_id}: {trigger_reason} (score: {confidence:.2f})")
            return

        # Trigger autonomous replan
        await self._trigger_autonomous_replan(workflow_id, trigger_reason, confidence, current_depth + 1)

    async def _trigger_autonomous_replan(
        self,
        workflow_id: str,
        trigger_reason: str,
        confidence: float,
        new_depth: int,
    ) -> None:
        """Emit PlanningRequested event for autonomous replan."""
        if self._event_bus is None:
            logger.warning("EventBus not available, cannot emit PlanningRequested")
            return

        task_id = f"replan_{workflow_id}_{uuid.uuid4().hex[:8]}"
        correlation_id = uuid.uuid4()

        # Update replan depth
        self._replan_depths[workflow_id] = new_depth

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
                "task_id": task_id,
                "workflow_id": workflow_id,
                "reason": "autonomous_replan",
                "trigger_reason": trigger_reason,
                "confidence": confidence,
                "origin": "autonomous",
                "replan_depth": new_depth,
                "max_replan_depth": self._config.max_replan_depth,
                # M10 provenance
                "autonomous": True,
                "authority_level": "autonomous",
                "judgment_source": "autonomous_independent",
            }),
            priority=EventPriority.HIGH,
            category=category_for_event_type(EventType.PLANNING_REQUESTED),
        )

        try:
            result = await self._event_bus.publish(core_event)
            logger.info(f"Emitted autonomous replan for {workflow_id}: depth={new_depth}, reason={trigger_reason}, result={result}")
        except Exception as e:
            logger.error(f"Failed to emit autonomous replan: {e}")

    def get_replan_depth(self, workflow_id: str) -> int:
        """Get current replan depth for a workflow."""
        return self._replan_depths.get(workflow_id, 0)

    def reset_replan_depth(self, workflow_id: str) -> None:
        """Reset replan depth (e.g., after successful completion)."""
        if workflow_id in self._replan_depths:
            del self._replan_depths[workflow_id]

    def get_stats(self) -> dict[str, Any]:
        stats = super().get_stats()
        stats.update({
            "enabled": self._config.enabled,
            "sensitivity": self._config.sensitivity,
            "execution_history_size": len(self._execution_history),
            "tracked_workflows": len(self._replan_depths),
            "max_replan_depth": self._config.max_replan_depth,
            "stagnation_window": self._config.stagnation_window,
        })
        return stats


# Global instance
_global_replan_detector: AdaptiveReplanDetector | None = None


def get_replan_detector(
    config: ReplanDetectorConfig | None = None,
) -> AdaptiveReplanDetector:
    """Get or create the global AdaptiveReplanDetector."""
    global _global_replan_detector
    if _global_replan_detector is None:
        _global_replan_detector = AdaptiveReplanDetector(config=config)
    return _global_replan_detector


def set_replan_detector(detector: AdaptiveReplanDetector) -> None:
    """Set the global AdaptiveReplanDetector."""
    global _global_replan_detector
    _global_replan_detector = detector


__all__ = [
    "AdaptiveReplanDetector",
    "ReplanDetectorConfig",
    "WorkflowExecutionRecord",
    "get_replan_detector",
    "set_replan_detector",
]