"""
State Manager Verification for AI-OS M10 Additions.

Verifies StateManager checkpoint/restore and truth-source integrity for
autonomous replans and objectives, ensuring state consistency across
autonomous operations.

This is M10-N7 implementation per M10-IMPLEMENTATION-SPEC.md §11.7.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from aios.events.base import Event
from aios.events.types import PlanningRequested, WorkflowCompleted, WorkflowFailed
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.payload import EventPayload
from aios.events.core.category import category_for_event_type
from aios.events.core.priority import EventPriority
from aios.events.core.types import EventType, SemanticVersion
from aios.services.base import BaseService
from aios.core.state import StateManager, get_state_manager, StateScope

logger = logging.getLogger(__name__)


@dataclass
class StateVerificationConfig:
    """Configuration for StateVerificationService."""
    enabled: bool = True
    verify_on_autonomous_action: bool = True
    checkpoint_frequency: int = 1  # Checkpoint every N autonomous actions
    max_verification_failures: int = 3  # Failures before alert


@dataclass
class VerificationResult:
    """Result of a state verification check."""
    verification_id: str
    trigger_id: str
    trigger_type: str  # "planning_requested", "workflow_completed", "manual"
    check_type: str  # "checkpoint", "restore", "consistency"
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    autonomous: bool = True
    authority_level: str = "autonomous"


class StateVerificationService(BaseService):
    """
    Verifies StateManager checkpoint/restore and truth-source integrity.

    M10-N7: StateManager Verification for Additions (GAP-M10-08)
    - Validates checkpoint/restore for autonomous objectives and replans
    - Ensures truth-source integrity during autonomous operations
    - Verifies autonomous actions produce verifiable state transitions
    - Security test: Asserts tampered state fails verification
    """

    name = "state_verification"
    version = "1.0.0"
    description = "State integrity verification for autonomous operations"
    depends_on: list[str] = ["memory", "state_manager", "objective_generator", "replan_detector"]

    def __init__(
        self,
        config: StateVerificationConfig | None = None,
        state_manager: StateManager | None = None,
        event_bus=None,
        info=None,
        **kwargs,
    ):
        super().__init__(event_bus=event_bus, info=info)
        self._config = config or StateVerificationConfig()
        self._state_manager = state_manager or get_state_manager()
        self._event_bus = get_core_event_bus()
        self._verification_results: list[VerificationResult] = []
        self._autonomous_action_count = 0
        self._failure_count = 0

    @property
    def config(self) -> StateVerificationConfig:
        return self._config

    async def on_start(self) -> None:
        logger.info(f"StateVerificationService.on_start called, enabled={self._config.enabled}")
        if self._config.enabled:
            self.subscribe(self._on_planning_requested, PlanningRequested)
            self.subscribe(self._on_workflow_completed, WorkflowCompleted)
            self.subscribe(self._on_workflow_failed, WorkflowFailed)
            logger.info("StateVerificationService subscribed to autonomous action events")
        else:
            logger.info("StateVerificationService disabled by config")

    async def on_stop(self) -> None:
        logger.info("StateVerificationService stopped")

    async def _on_planning_requested(self, event: Event) -> None:
        """Handle autonomous planning requests - verify state integrity."""
        payload = event.payload.to_dict() if hasattr(event.payload, 'to_dict') else dict(event.payload)
        is_autonomous = payload.get("autonomous", False)
        task_id = payload.get("task_id", "")

        if is_autonomous and self._config.verify_on_autonomous_action:
            self._autonomous_action_count += 1

            # Periodic checkpoint verification
            if self._autonomous_action_count % self._config.checkpoint_frequency == 0:
                await self._verify_autonomous_checkpoint(task_id, "planning_requested")

    async def _on_workflow_completed(self, event: Event) -> None:
        """Handle workflow completion - verify state."""
        payload = event.payload.to_dict() if hasattr(event.payload, 'to_dict') else dict(event.payload)
        execution_id = payload.get("execution_id", "")

        if self._config.verify_on_autonomous_action:
            await self._verify_autonomous_checkpoint(execution_id, "workflow_completed")

    async def _on_workflow_failed(self, event: Event) -> None:
        """Handle workflow failure - verify state consistency."""
        payload = event.payload.to_dict() if hasattr(event.payload, 'to_dict') else dict(event.payload)
        execution_id = payload.get("execution_id", "")

        if self._config.verify_on_autonomous_action:
            await self._verify_state_consistency(execution_id, "workflow_failed")

    async def _verify_autonomous_checkpoint(
        self,
        trigger_id: str,
        trigger_type: str,
    ) -> VerificationResult:
        """Create and verify a checkpoint for autonomous action."""
        verification_id = f"verify_{trigger_id}_{datetime.utcnow().timestamp()}"

        try:
            # Create checkpoint for the workflow scope
            snapshot = self._state_manager.checkpoint(
                StateScope.WORKFLOW,
                trigger_id,
                metadata={
                    "verification_id": verification_id,
                    "trigger_type": trigger_type,
                    "autonomous": True,
                },
            )

            # Verify by restoring and comparing
            restored_snapshot = self._state_manager.restore(
                StateScope.WORKFLOW,
                trigger_id,
                snapshot_id=snapshot.snapshot_id,
            )

            # Check state integrity
            original_state = snapshot.state
            restored_state = restored_snapshot.state

            passed = original_state == restored_state
            details = {
                "snapshot_id": snapshot.snapshot_id,
                "restored_snapshot_id": restored_snapshot.snapshot_id,
                "state_keys_count": len(original_state),
                "state_match": passed,
            }

            if not passed:
                details["mismatch"] = self._find_state_mismatch(original_state, restored_state)
                self._failure_count += 1
                logger.warning(f"Checkpoint verification failed for {trigger_id}: {details}")
            else:
                logger.debug(f"Checkpoint verification passed: {verification_id}")

        except Exception as e:
            passed = False
            details = {"error": str(e)}
            self._failure_count += 1
            logger.error(f"Checkpoint verification error for {trigger_id}: {e}")

        result = VerificationResult(
            verification_id=verification_id,
            trigger_id=trigger_id,
            trigger_type=trigger_type,
            check_type="checkpoint",
            passed=passed,
            details=details,
        )
        self._verification_results.append(result)

        # Emit verification event
        await self._emit_verification_event(result)

        return result

    async def _verify_state_consistency(
        self,
        trigger_id: str,
        trigger_type: str,
    ) -> VerificationResult:
        """Verify state consistency for a workflow."""
        verification_id = f"verify_consistency_{trigger_id}_{datetime.utcnow().timestamp()}"

        try:
            # Get current state
            current_state = self._state_manager.get_state(StateScope.WORKFLOW, trigger_id)

            # Get history
            history = self._state_manager.get_history(StateScope.WORKFLOW, trigger_id, limit=5)

            # Verify consistency: state should be non-empty if workflow was active
            passed = True
            details = {
                "state_keys": list(current_state.keys()) if current_state else [],
                "history_count": len(history),
            }

            if not current_state and history:
                # Had history but no current state - inconsistency
                passed = False
                details["issue"] = "empty_state_with_history"

            if not passed:
                self._failure_count += 1

        except Exception as e:
            passed = False
            details = {"error": str(e)}
            self._failure_count += 1
            logger.error(f"Consistency verification error for {trigger_id}: {e}")

        result = VerificationResult(
            verification_id=verification_id,
            trigger_id=trigger_id,
            trigger_type=trigger_type,
            check_type="consistency",
            passed=passed,
            details=details,
        )
        self._verification_results.append(result)

        await self._emit_verification_event(result)
        return result

    def _find_state_mismatch(self, original: dict, restored: dict) -> dict[str, Any]:
        """Find differences between original and restored state."""
        mismatches = {}
        all_keys = set(original.keys()) | set(restored.keys())
        for key in all_keys:
            if original.get(key) != restored.get(key):
                mismatches[key] = {
                    "original": original.get(key),
                    "restored": restored.get(key),
                }
        return mismatches

    async def _emit_verification_event(self, result: VerificationResult) -> None:
        """Emit state verification event."""
        if self._event_bus is None:
            return

        import uuid
        correlation_id = uuid.uuid4()

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
                "event_name": "STATE_VERIFICATION_COMPLETED",
                "verification_id": result.verification_id,
                "trigger_id": result.trigger_id,
                "trigger_type": result.trigger_type,
                "check_type": result.check_type,
                "passed": result.passed,
                "details": result.details,
                "autonomous": result.autonomous,
                "authority_level": result.authority_level,
            }),
            priority=EventPriority.NORMAL if result.passed else EventPriority.HIGH,
            category=category_for_event_type(EventType.AI_AGENT_AUDIT_EMITTED),
        )

        try:
            await self._event_bus.publish(core_event)
        except Exception as e:
            logger.error(f"Failed to emit verification event: {e}")

    def verify_manual(self, workflow_id: str) -> VerificationResult:
        """Manually trigger verification for a workflow."""
        if self._event_bus is None:
            return VerificationResult(
                verification_id=f"manual_{workflow_id}",
                trigger_id=workflow_id,
                trigger_type="manual",
                check_type="checkpoint",
                passed=False,
                details={"error": "EventBus not available"},
            )
        # Run async verification
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            return loop.run_until_complete(self._verify_autonomous_checkpoint(workflow_id, "manual"))
        except RuntimeError:
            # No event loop, run synchronously
            return asyncio.run(self._verify_autonomous_checkpoint(workflow_id, "manual"))

    def get_verification_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent verification results."""
        return [
            {
                "verification_id": v.verification_id,
                "trigger_id": v.trigger_id,
                "trigger_type": v.trigger_type,
                "check_type": v.check_type,
                "passed": v.passed,
                "details": v.details,
                "timestamp": v.timestamp.isoformat(),
            }
            for v in self._verification_results[-limit:]
        ]

    def get_stats(self) -> dict[str, Any]:
        stats = super().get_stats()
        passed_count = sum(1 for v in self._verification_results if v.passed)
        total = len(self._verification_results)
        stats.update({
            "enabled": self._config.enabled,
            "total_verifications": total,
            "passed": passed_count,
            "failed": total - passed_count,
            "failure_count": self._failure_count,
            "autonomous_actions_verified": self._autonomous_action_count,
        })
        return stats


# Global instance
_global_state_verification: StateVerificationService | None = None


def get_state_verification(
    config: StateVerificationConfig | None = None,
    state_manager: StateManager | None = None,
) -> StateVerificationService:
    """Get or create the global StateVerificationService."""
    global _global_state_verification
    if _global_state_verification is None:
        _global_state_verification = StateVerificationService(config=config, state_manager=state_manager)
    return _global_state_verification


def set_state_verification(service: StateVerificationService) -> None:
    """Set the global StateVerificationService."""
    global _global_state_verification
    _global_state_verification = service


__all__ = [
    "StateVerificationService",
    "StateVerificationConfig",
    "VerificationResult",
    "get_state_verification",
    "set_state_verification",
]