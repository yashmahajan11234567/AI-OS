"""
AI-OS Cyber Turtle State Management.

Deterministic state mapping from authoritative AI-OS state/events to mascot states.
The mapper is side-effect-free and never mutates kernel state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime

from aios.core.lifecycle_manager import LifecycleState
from aios.core.health_manager import HealthStatus, HealthManager
from aios.core.constants import APP_NAME
from aios.core.version import __version__


class MascotState(str, Enum):
    """Logical mascot states driven by authoritative AI-OS state/events."""
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    REVIEWING = "reviewing"
    VERIFYING = "verifying"
    LEARNING = "learning"
    ESCALATING = "escalating"
    COMPLETE = "complete"


# Priority order for state resolution (highest priority first)
STATE_PRIORITY: List[MascotState] = [
    MascotState.ESCALATING,
    MascotState.COMPLETE,
    MascotState.PLANNING,
    MascotState.EXECUTING,
    MascotState.REVIEWING,
    MascotState.VERIFYING,
    MascotState.LEARNING,
    MascotState.IDLE,
]


@dataclass
class MascotStateContext:
    """Context for state mapping - all authoritative inputs."""
    lifecycle_state: Optional[LifecycleState] = None
    health_status: Optional[HealthStatus] = None
    has_active_workflow: bool = False
    workflow_phase: Optional[str] = None  # "planning", "executing", "reviewing", "verifying", "learning"
    human_escalation_required: bool = False
    is_shutting_down: bool = False
    is_terminated: bool = False
    completion_result: Optional[str] = None  # For COMPLETE state result display


class MascotStateMapper:
    """
    Deterministic mapper from AI-OS authoritative state to MascotState.

    Pure function - no side effects, no mutations, no event publishing.
    Only reads authoritative state.
    """

    # Mapping from lifecycle state to base mascot state (when no workflow active)
    LIFECYCLE_TO_MASCOT: Dict[LifecycleState, MascotState] = {
        LifecycleState.UNINITIALIZED: MascotState.IDLE,
        LifecycleState.INITIALIZING: MascotState.PLANNING,
        LifecycleState.OPERATIONAL: MascotState.IDLE,
        LifecycleState.DEGRADED: MascotState.ESCALATING,
        LifecycleState.SHUTTING_DOWN: MascotState.IDLE,
        LifecycleState.TERMINATED: MascotState.IDLE,
        LifecycleState.ROLLBACK_IN_PROGRESS: MascotState.ESCALATING,
        LifecycleState.RECOVERY_IN_PROGRESS: MascotState.LEARNING,
    }

    # Mapping from health status to mascot state influence
    HEALTH_TO_MASCOT: Dict[HealthStatus, MascotState] = {
        HealthStatus.HEALTHY: MascotState.IDLE,
        HealthStatus.DEGRADED: MascotState.ESCALATING,
        HealthStatus.UNHEALTHY: MascotState.ESCALATING,
        HealthStatus.UNKNOWN: MascotState.IDLE,
    }

    # Workflow phase to mascot state mapping
    WORKFLOW_PHASE_TO_MASCOT: Dict[str, MascotState] = {
        "planning": MascotState.PLANNING,
        "executing": MascotState.EXECUTING,
        "reviewing": MascotState.REVIEWING,
        "verifying": MascotState.VERIFYING,
        "learning": MascotState.LEARNING,
        "complete": MascotState.COMPLETE,
    }

    @classmethod
    def map(cls, context: MascotStateContext) -> MascotState:
        """
        Map authoritative AI-OS context to MascotState using deterministic priority.

        Priority order (per spec §9):
        1. HUMAN_ESCALATION_REQUIRED -> ESCALATING
        2. COMPLETE -> COMPLETE
        3. UNHEALTHY / ERROR -> ESCALATING
        4. DEGRADED -> ESCALATING
        5. Active workflow/event -> PLANNING/EXECUTING/REVIEWING/VERIFYING/LEARNING
        6. No active workflow + healthy/operational -> IDLE
        7. SHUTTING_DOWN / TERMINATED -> IDLE static
        """
        # Priority 1: Human escalation required
        if context.human_escalation_required:
            return MascotState.ESCALATING

        # Priority 2: Completion (has completion result)
        if context.completion_result is not None:
            return MascotState.COMPLETE

        # Priority 3: Unhealthy / Error states
        if context.health_status == HealthStatus.UNHEALTHY:
            return MascotState.ESCALATING

        # Check lifecycle for terminal error states
        if context.lifecycle_state in (LifecycleState.TERMINATED, LifecycleState.RECOVERY_IN_PROGRESS):
            # TERMINATED is handled at priority 7
            # RECOVERY_IN_PROGRESS maps to LEARNING per LIFECYCLE_TO_MASCOT
            pass  # Let normal mapping handle it

        # Priority 4: Degraded
        if context.health_status == HealthStatus.DEGRADED:
            return MascotState.ESCALATING
        if context.lifecycle_state == LifecycleState.DEGRADED:
            return MascotState.ESCALATING

        # Priority 5: Active workflow/event
        if context.has_active_workflow and context.workflow_phase:
            phase_state = cls.WORKFLOW_PHASE_TO_MASCOT.get(context.workflow_phase)
            if phase_state:
                return phase_state

        # Priority 6: No active workflow + healthy/operational
        if not context.has_active_workflow:
            if context.lifecycle_state == LifecycleState.OPERATIONAL:
                if context.health_status in (HealthStatus.HEALTHY, HealthStatus.UNKNOWN):
                    return MascotState.IDLE

        # Priority 7: Shutting down / Terminated -> IDLE static
        if context.is_shutting_down or context.is_terminated:
            return MascotState.IDLE

        # Default: use lifecycle mapping
        if context.lifecycle_state:
            return cls.LIFECYCLE_TO_MASCOT.get(context.lifecycle_state, MascotState.IDLE)

        # Fallback
        return MascotState.IDLE

    @classmethod
    def should_animate(cls, state: MascotState) -> bool:
        """Determine if a state should animate (vs static)."""
        # IDLE and COMPLETE are static; all others animate
        return state not in (MascotState.IDLE, MascotState.COMPLETE)

    @classmethod
    def is_interruptible(cls, current: MascotState, incoming: MascotState) -> bool:
        """
        Determine if incoming state should interrupt current animation.

        Per spec §10:
        - New authoritative state interrupts current animation
        - Escalation overrides normal activity
        - Shutdown cancels animation
        """
        # Escalation always interrupts (matches owl behavior)
        if incoming == MascotState.ESCALATING:
            return True
        # Completion always interrupts (matches owl behavior)
        if incoming == MascotState.COMPLETE:
            return True
        # Shutdown/terminated interrupts
        if incoming == MascotState.IDLE and current != MascotState.IDLE:
            return True
        # Same state doesn't restart
        if current == incoming:
            return False
        # Different active states interrupt
        return True

    @classmethod
    def from_kernel_state(
        cls,
        lifecycle_state: Optional[LifecycleState] = None,
        health_status: Optional[HealthStatus] = None,
        has_active_workflow: bool = False,
        workflow_phase: Optional[str] = None,
        human_escalation_required: bool = False,
        is_shutting_down: bool = False,
        is_terminated: bool = False,
        completion_result: Optional[str] = None,
    ) -> MascotState:
        """Convenience method to create context and map in one call."""
        context = MascotStateContext(
            lifecycle_state=lifecycle_state,
            health_status=health_status,
            has_active_workflow=has_active_workflow,
            workflow_phase=workflow_phase,
            human_escalation_required=human_escalation_required,
            is_shutting_down=is_shutting_down,
            is_terminated=is_terminated,
            completion_result=completion_result,
        )
        return cls.map(context)

    @classmethod
    def describe_state(cls, state: MascotState) -> str:
        """Human-readable description of mascot state."""
        descriptions = {
            MascotState.IDLE: "Idle - awaiting input",
            MascotState.PLANNING: "Planning - analyzing task",
            MascotState.EXECUTING: "Executing - performing work",
            MascotState.REVIEWING: "Reviewing - evaluating results",
            MascotState.VERIFYING: "Verifying - checking correctness",
            MascotState.LEARNING: "Learning - extracting patterns",
            MascotState.ESCALATING: "Escalating - requires attention",
            MascotState.COMPLETE: "Complete - task finished",
        }
        return descriptions.get(state, "Unknown state")


def create_status_context(
    lifecycle_manager: Any,
    health_manager: Optional[HealthManager] = None,
    kernel: Any = None,
) -> MascotStateContext:
    """
    Create MascotStateContext from kernel components.

    Pure extraction - no side effects.
    """
    context = MascotStateContext()

    # Lifecycle state
    if lifecycle_manager is not None:
        context.lifecycle_state = lifecycle_manager.state
        context.is_shutting_down = lifecycle_manager.state == LifecycleState.SHUTTING_DOWN
        context.is_terminated = lifecycle_manager.state == LifecycleState.TERMINATED

    # Health status
    if health_manager is not None:
        context.health_status = health_manager.overall_status

    # Workflow activity (from kernel or event bus)
    if kernel is not None:
        # Check for active workflow via workflow manager
        wm = getattr(kernel, 'workflow_manager', None)
        if wm is not None:
            context.has_active_workflow = hasattr(wm, '_active_workflows') and len(wm._active_workflows) > 0
            # Could extract phase from active workflow if available
            # For now, infer from lifecycle
            if context.has_active_workflow:
                if context.lifecycle_state == LifecycleState.INITIALIZING:
                    context.workflow_phase = "planning"
                elif context.lifecycle_state == LifecycleState.OPERATIONAL:
                    context.workflow_phase = "executing"

    # Check for human escalation event (could come from EventBus)
    # This would be set by external event observation
    # For now, check health manager for UNHEALTHY as proxy
    if health_manager is not None and health_manager.overall_status == HealthStatus.UNHEALTHY:
        context.human_escalation_required = True

    return context