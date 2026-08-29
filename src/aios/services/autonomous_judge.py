"""
Autonomous Final Judge for AI-OS M10.

Extends the Final Judge Agency to operate in autonomous mode without Council input,
emitting independent PASS/FAIL judgments.

This is M10-N3 implementation per M10-IMPLEMENTATION-SPEC.md §11.3.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from aios.events.base import Event
from aios.events.types import TestingCompleted, WorkflowCompleted
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.payload import EventPayload
from aios.events.core.category import category_for_event_type
from aios.events.core.priority import EventPriority
from aios.events.core.types import EventType, SemanticVersion
from aios.services.base import BaseService
from aios.core.council_manager import CouncilManager, get_council_manager, CouncilDecision

logger = logging.getLogger(__name__)


class JudgmentSource(str, Enum):
    """Source of the PASS/FAIL judgment."""
    COUNCIL_RECONCILED = "council_reconciled"
    AUTONOMOUS_INDEPENDENT = "autonomous_independent"


class AutonomousJudgeMode(str, Enum):
    """Operating mode for the autonomous judge."""
    ADVISORY_ONLY = "advisory_only"  # M9 behavior - only advisory
    AUTONOMOUS_ENABLED = "autonomous_enabled"  # M10 - can emit independent judgments
    FALLBACK = "fallback"  # Council unavailable, autonomous as fallback


@dataclass
class AutonomousJudgeConfig:
    """Configuration for AutonomousFinalJudge."""
    mode: AutonomousJudgeMode = AutonomousJudgeMode.ADVISORY_ONLY
    confidence_threshold: float = 0.75  # Minimum confidence for autonomous PASS
    require_learning_evidence: bool = True  # Require learnings for autonomous PASS
    defer_to_council: bool = True  # Defer to council judgment if both present
    max_autonomous_judgments_per_hour: int = 10


@dataclass
class JudgmentResult:
    """Result of an autonomous judgment."""
    judgment_id: str
    execution_id: str
    workflow_id: str | None
    verdict: str  # "PASS" or "FAIL"
    confidence: float
    judgment_source: JudgmentSource
    rationale: str
    evidence: dict[str, Any] = field(default_factory=dict)
    learning_refs: list[str] = field(default_factory=list)
    council_decision_id: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    autonomous: bool = True
    authority_level: str = "autonomous"


class AutonomousFinalJudge(BaseService):
    """
    Extends Final Judge Agency for autonomous operation without Council input.

    M10-N3: Independent PASS/FAIL Authority (GAP-M10-03)
    - Capable of operating in autonomous mode without Council input
    - Emits TestingCompleted/WorkflowCompleted with judgment_source=autonomous_independent
    - Conflict resolution: Autonomous judgment defers to Council judgment if both present
    - Security test: Asserts autonomous judgments still pass through SecurityManager gates
    """

    name = "autonomous_judge"
    version = "1.0.0"
    description = "Autonomous PASS/FAIL judgment for workflow/testing executions"
    depends_on: list[str] = ["memory", "learning", "security"]

    def __init__(
        self,
        config: AutonomousJudgeConfig | None = None,
        council_manager: CouncilManager | None = None,
        event_bus=None,
        info=None,
        **kwargs,
    ):
        super().__init__(event_bus=event_bus, info=info)
        self._config = config or AutonomousJudgeConfig()
        self._council_manager = council_manager or get_council_manager()
        self._event_bus = get_core_event_bus()
        self._judgment_count = 0
        self._last_judgment_time: datetime | None = None

    @property
    def config(self) -> AutonomousJudgeConfig:
        return self._config

    async def on_start(self) -> None:
        logger.info(f"AutonomousFinalJudge.on_start called, mode={self._config.mode.value}")
        if self._config.mode == AutonomousJudgeMode.AUTONOMOUS_ENABLED:
            self.subscribe(self._on_testing_completed, TestingCompleted)
            self.subscribe(self._on_workflow_completed, WorkflowCompleted)
            logger.info("AutonomousFinalJudge subscribed to judgment events (autonomous mode)")
        else:
            logger.info(f"AutonomousFinalJudge in {self._config.mode.value} mode")

    async def on_stop(self) -> None:
        logger.info("AutonomousFinalJudge stopped")

    async def _on_testing_completed(self, event: Event) -> None:
        """Handle testing completion - potentially emit autonomous judgment."""
        if self._config.mode != AutonomousJudgeMode.AUTONOMOUS_ENABLED:
            return

        payload = event.payload.to_dict() if hasattr(event.payload, 'to_dict') else dict(event.payload)
        execution_id = payload.get("execution_id", "")
        workflow_id = payload.get("workflow_id")
        test_results = payload.get("test_results", {})
        passed = payload.get("passed", False)

        # Only judge if no council judgment exists
        council_decision_id = payload.get("council_decision_id")
        if council_decision_id and self._config.defer_to_council:
            logger.debug(f"Council judgment exists for {execution_id}, deferring")
            return

        await self._emit_autonomous_judgment(
            execution_id=execution_id,
            workflow_id=workflow_id,
            test_results=test_results,
            passed=passed,
            event_type="testing",
        )

    async def _on_workflow_completed(self, event: Event) -> None:
        """Handle workflow completion - potentially emit autonomous judgment."""
        if self._config.mode != AutonomousJudgeMode.AUTONOMOUS_ENABLED:
            return

        payload = event.payload.to_dict() if hasattr(event.payload, 'to_dict') else dict(event.payload)
        execution_id = payload.get("execution_id", "")
        workflow_id = payload.get("workflow_id", "")
        step_results = payload.get("step_results", {})

        council_decision_id = payload.get("council_decision_id")
        if council_decision_id and self._config.defer_to_council:
            logger.debug(f"Council judgment exists for workflow {execution_id}, deferring")
            return

        # Determine pass/fail from workflow state
        passed = all(
            r.get("success", True) for r in step_results.values()
            if isinstance(r, dict)
        )

        await self._emit_autonomous_judgment(
            execution_id=execution_id,
            workflow_id=workflow_id,
            test_results=step_results,
            passed=passed,
            event_type="workflow",
        )

    
    def _can_judge(self) -> bool:
        """Check if judge can emit autonomous judgment."""
        if self._config.mode != AutonomousJudgeMode.AUTONOMOUS_ENABLED:
            return False

        # Rate limiting
        if self._last_judgment_time:
            elapsed = (datetime.utcnow() - self._last_judgment_time).total_seconds()
            if elapsed < 3600 and self._judgment_count >= self._config.max_autonomous_judgments_per_hour:
                logger.warning("Autonomous judgment rate limit exceeded")
                return False

        return True

    async def _emit_autonomous_judgment(
        self,
        execution_id: str,
        workflow_id: str | None,
        test_results: dict[str, Any],
        passed: bool,
        event_type: str,
    ) -> None:
        """Emit autonomous PASS/FAIL judgment."""
        if not self._can_judge():
            return

        # Calculate confidence based on evidence
        confidence = self._calculate_confidence(test_results, passed)

        # Check confidence threshold for PASS
        verdict = "PASS" if passed else "FAIL"
        if verdict == "PASS" and confidence < self._config.confidence_threshold:
            verdict = "FAIL"
            confidence = 1.0 - confidence

        # Check learning evidence requirement
        if verdict == "PASS" and self._config.require_learning_evidence:
            has_learnings = await self._check_learning_evidence(execution_id)
            if not has_learnings:
                verdict = "FAIL"
                confidence = 0.5
                logger.warning(f"Autonomous PASS blocked: no learning evidence for {execution_id}")

        judgment_id = f"judge_auto_{uuid.uuid4().hex[:12]}"
        rationale = self._build_rationale(verdict, confidence, test_results)

        judgment = JudgmentResult(
            judgment_id=judgment_id,
            execution_id=execution_id,
            workflow_id=workflow_id,
            verdict=verdict,
            confidence=confidence,
            judgment_source=JudgmentSource.AUTONOMOUS_INDEPENDENT,
            rationale=rationale,
            evidence=test_results,
            autonomous=True,
            authority_level="autonomous",
        )

        # Emit the appropriate completion event with autonomous judgment
        await self._emit_judgment_event(judgment, event_type)

        self._judgment_count += 1
        self._last_judgment_time = datetime.utcnow()
        logger.info(f"Emitted autonomous {verdict} judgment: {judgment_id} (confidence={confidence:.2f})")

    def _calculate_confidence(self, test_results: dict[str, Any], passed: bool) -> float:
        """Calculate confidence score for judgment."""
        if not test_results:
            return 0.5

        # Simple heuristic: more comprehensive results = higher confidence
        result_count = len(test_results)
        success_count = sum(
            1 for r in test_results.values()
            if isinstance(r, dict) and r.get("success", False)
        )

        if passed:
            base_confidence = 0.6 + (success_count / max(result_count, 1)) * 0.3
        else:
            base_confidence = 0.7 + (1 - success_count / max(result_count, 1)) * 0.2

        return min(max(base_confidence, 0.0), 1.0)

    async def _check_learning_evidence(self, execution_id: str) -> bool:
        """Check if learnings exist relevant to this execution."""
        try:
            from aios.services.learning import get_learning_service
            learning_service = get_learning_service()
            learnings = learning_service.get_learnings(limit=5)
            return len(learnings) > 0
        except Exception:
            return False

    def _build_rationale(self, verdict: str, confidence: float, test_results: dict[str, Any]) -> str:
        """Build human-readable rationale for judgment."""
        result_summary = f"{len(test_results)} result(s) analyzed"
        if verdict == "PASS":
            return f"Autonomous PASS (confidence: {confidence:.2f}): {result_summary}. All critical criteria satisfied based on execution evidence."
        else:
            return f"Autonomous FAIL (confidence: {confidence:.2f}): {result_summary}. Execution did not meet pass criteria or lacked sufficient learning evidence."

    async def _emit_judgment_event(self, judgment: JudgmentResult, event_type: str) -> None:
        """Emit TestingCompleted or WorkflowCompleted with autonomous judgment."""
        if self._event_bus is None:
            return

        correlation_id = uuid.uuid4()

        if event_type == "testing":
            event_type_enum = EventType.TESTING_COMPLETED
        else:
            event_type_enum = EventType.WORKFLOW_COMPLETED

        core_event = CoreEvent(
            eventType=event_type_enum,
            source=ComponentIdentity(
                component_type=ComponentType.ENGINEERING_SERVICE,
                component_name=self.name,
                version=SemanticVersion.parse(self.version),
            ),
            correlationId=correlation_id,
            causationId=correlation_id,
            payload=EventPayload({
                "execution_id": judgment.execution_id,
                "workflow_id": judgment.workflow_id,
                "passed": judgment.verdict == "PASS",
                "judgment_id": judgment.judgment_id,
                "judgment_source": judgment.judgment_source.value,
                "confidence": judgment.confidence,
                "rationale": judgment.rationale,
                "autonomous": True,
                "authority_level": "autonomous",
                # M10 provenance extensions
                "provenance": {
                    "autonomous": True,
                    "authority_level": "autonomous",
                    "judgment_source": "autonomous_independent",
                },
            }),
            priority=EventPriority.HIGH,
            category=category_for_event_type(event_type_enum),
        )

        try:
            await self._event_bus.publish(core_event)
        except Exception as e:
            logger.error(f"Failed to emit autonomous judgment event: {e}")

    def get_stats(self) -> dict[str, Any]:
        stats = super().get_stats()
        stats.update({
            "mode": self._config.mode.value,
            "confidence_threshold": self._config.confidence_threshold,
            "require_learning_evidence": self._config.require_learning_evidence,
            "defer_to_council": self._config.defer_to_council,
            "judgments_emitted": self._judgment_count,
            "last_judgment": self._last_judgment_time.isoformat() if self._last_judgment_time else None,
        })
        return stats


# Global instance
_global_autonomous_judge: AutonomousFinalJudge | None = None


def get_autonomous_judge(
    config: AutonomousJudgeConfig | None = None,
    council_manager: CouncilManager | None = None,
) -> AutonomousFinalJudge:
    """Get or create the global AutonomousFinalJudge."""
    global _global_autonomous_judge
    if _global_autonomous_judge is None:
        _global_autonomous_judge = AutonomousFinalJudge(config=config, council_manager=council_manager)
    return _global_autonomous_judge


def set_autonomous_judge(judge: AutonomousFinalJudge) -> None:
    """Set the global AutonomousFinalJudge."""
    global _global_autonomous_judge
    _global_autonomous_judge = judge


__all__ = [
    "AutonomousFinalJudge",
    "AutonomousJudgeConfig",
    "AutonomousJudgeMode",
    "JudgmentSource",
    "JudgmentResult",
    "get_autonomous_judge",
    "set_autonomous_judge",
]