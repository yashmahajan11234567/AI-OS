"""
Tests for Cyber Turtle State Management.
"""

import pytest
from aios.cli.mascot.state import (
    MascotState,
    MascotStateContext,
    MascotStateMapper,
    STATE_PRIORITY,
)
from aios.core.lifecycle_manager import LifecycleState
from aios.core.health_manager import HealthStatus


class TestMascotStateEnum:
    """Tests for MascotState enum."""

    def test_all_states_exist(self):
        """All 8 canonical states should exist."""
        expected = [
            "IDLE", "PLANNING", "EXECUTING", "REVIEWING",
            "VERIFYING", "LEARNING", "ESCALATING", "COMPLETE"
        ]
        for name in expected:
            assert hasattr(MascotState, name)
            assert isinstance(getattr(MascotState, name), MascotState)

    def test_state_values_lowercase(self):
        """State values should be lowercase strings."""
        for state in MascotState:
            assert state.value == state.name.lower()
            assert state.value.islower()

    def test_state_priority_order(self):
        """STATE_PRIORITY should have all states in correct order."""
        assert len(STATE_PRIORITY) == 8
        # ESCALATING highest priority
        assert STATE_PRIORITY[0] == MascotState.ESCALATING
        # COMPLETE second
        assert STATE_PRIORITY[1] == MascotState.COMPLETE
        # IDLE lowest
        assert STATE_PRIORITY[-1] == MascotState.IDLE


class TestMascotStateContext:
    """Tests for MascotStateContext dataclass."""

    def test_context_creation(self):
        """Context should create with defaults."""
        context = MascotStateContext()
        assert context.lifecycle_state is None
        assert context.health_status is None
        assert context.has_active_workflow is False
        assert context.workflow_phase is None
        assert context.human_escalation_required is False
        assert context.is_shutting_down is False
        assert context.is_terminated is False
        assert context.completion_result is None

    def test_context_with_values(self):
        """Context should accept all values."""
        context = MascotStateContext(
            lifecycle_state=LifecycleState.OPERATIONAL,
            health_status=HealthStatus.HEALTHY,
            has_active_workflow=True,
            workflow_phase="executing",
            human_escalation_required=True,
            is_shutting_down=True,
            is_terminated=False,
            completion_result="PASS",
        )
        assert context.lifecycle_state == LifecycleState.OPERATIONAL
        assert context.health_status == HealthStatus.HEALTHY
        assert context.has_active_workflow is True
        assert context.workflow_phase == "executing"
        assert context.human_escalation_required is True
        assert context.is_shutting_down is True
        assert context.is_terminated is False
        assert context.completion_result == "PASS"


class TestMascotStateMapper:
    """Tests for MascotStateMapper."""

    def test_priority_1_human_escalation(self):
        """Human escalation should map to ESCALATING."""
        context = MascotStateContext(human_escalation_required=True)
        result = MascotStateMapper.map(context)
        assert result == MascotState.ESCALATING

    def test_priority_2_completion(self):
        """Completion result should map to COMPLETE."""
        context = MascotStateContext(completion_result="PASS")
        result = MascotStateMapper.map(context)
        assert result == MascotState.COMPLETE

    def test_priority_3_unhealthy(self):
        """UNHEALTHY health should map to ESCALATING."""
        context = MascotStateContext(health_status=HealthStatus.UNHEALTHY)
        result = MascotStateMapper.map(context)
        assert result == MascotState.ESCALATING

    def test_priority_4_degraded_health(self):
        """DEGRADED health should map to ESCALATING."""
        context = MascotStateContext(health_status=HealthStatus.DEGRADED)
        result = MascotStateMapper.map(context)
        assert result == MascotState.ESCALATING

    def test_priority_4_degraded_lifecycle(self):
        """DEGRADED lifecycle should map to ESCALATING."""
        context = MascotStateContext(lifecycle_state=LifecycleState.DEGRADED)
        result = MascotStateMapper.map(context)
        assert result == MascotState.ESCALATING

    def test_priority_5_workflow_planning(self):
        """Active workflow in planning phase should map to PLANNING."""
        context = MascotStateContext(
            has_active_workflow=True,
            workflow_phase="planning",
            lifecycle_state=LifecycleState.OPERATIONAL,
            health_status=HealthStatus.HEALTHY,
        )
        result = MascotStateMapper.map(context)
        assert result == MascotState.PLANNING

    def test_priority_5_workflow_executing(self):
        """Active workflow in executing phase should map to EXECUTING."""
        context = MascotStateContext(
            has_active_workflow=True,
            workflow_phase="executing",
            lifecycle_state=LifecycleState.OPERATIONAL,
            health_status=HealthStatus.HEALTHY,
        )
        result = MascotStateMapper.map(context)
        assert result == MascotState.EXECUTING

    def test_priority_5_workflow_reviewing(self):
        """Active workflow in reviewing phase should map to REVIEWING."""
        context = MascotStateContext(
            has_active_workflow=True,
            workflow_phase="reviewing",
            lifecycle_state=LifecycleState.OPERATIONAL,
            health_status=HealthStatus.HEALTHY,
        )
        result = MascotStateMapper.map(context)
        assert result == MascotState.REVIEWING

    def test_priority_5_workflow_verifying(self):
        """Active workflow in verifying phase should map to VERIFYING."""
        context = MascotStateContext(
            has_active_workflow=True,
            workflow_phase="verifying",
            lifecycle_state=LifecycleState.OPERATIONAL,
            health_status=HealthStatus.HEALTHY,
        )
        result = MascotStateMapper.map(context)
        assert result == MascotState.VERIFYING

    def test_priority_5_workflow_learning(self):
        """Active workflow in learning phase should map to LEARNING."""
        context = MascotStateContext(
            has_active_workflow=True,
            workflow_phase="learning",
            lifecycle_state=LifecycleState.OPERATIONAL,
            health_status=HealthStatus.HEALTHY,
        )
        result = MascotStateMapper.map(context)
        assert result == MascotState.LEARNING

    def test_priority_5_workflow_complete(self):
        """Active workflow in complete phase should map to COMPLETE."""
        context = MascotStateContext(
            has_active_workflow=True,
            workflow_phase="complete",
            lifecycle_state=LifecycleState.OPERATIONAL,
            health_status=HealthStatus.HEALTHY,
        )
        result = MascotStateMapper.map(context)
        assert result == MascotState.COMPLETE

    def test_priority_6_idle_operational_healthy(self):
        """No workflow + operational + healthy should map to IDLE."""
        context = MascotStateContext(
            has_active_workflow=False,
            lifecycle_state=LifecycleState.OPERATIONAL,
            health_status=HealthStatus.HEALTHY,
        )
        result = MascotStateMapper.map(context)
        assert result == MascotState.IDLE

    def test_priority_6_idle_operational_unknown(self):
        """No workflow + operational + unknown health should map to IDLE."""
        context = MascotStateContext(
            has_active_workflow=False,
            lifecycle_state=LifecycleState.OPERATIONAL,
            health_status=HealthStatus.UNKNOWN,
        )
        result = MascotStateMapper.map(context)
        assert result == MascotState.IDLE

    def test_priority_7_shutting_down(self):
        """Shutting down should map to IDLE."""
        context = MascotStateContext(is_shutting_down=True)
        result = MascotStateMapper.map(context)
        assert result == MascotState.IDLE

    def test_priority_7_terminated(self):
        """Terminated should map to IDLE."""
        context = MascotStateContext(is_terminated=True)
        result = MascotStateMapper.map(context)
        assert result == MascotState.IDLE

    def test_lifecycle_mapping_uninitialized(self):
        """UNINITIALIZED lifecycle should map to IDLE."""
        context = MascotStateContext(lifecycle_state=LifecycleState.UNINITIALIZED)
        result = MascotStateMapper.map(context)
        assert result == MascotState.IDLE

    def test_lifecycle_mapping_initializing(self):
        """INITIALIZING lifecycle should map to PLANNING."""
        context = MascotStateContext(lifecycle_state=LifecycleState.INITIALIZING)
        result = MascotStateMapper.map(context)
        assert result == MascotState.PLANNING

    def test_lifecycle_mapping_recovery(self):
        """RECOVERY_IN_PROGRESS should map to LEARNING."""
        context = MascotStateContext(lifecycle_state=LifecycleState.RECOVERY_IN_PROGRESS)
        result = MascotStateMapper.map(context)
        assert result == MascotState.LEARNING

    def test_lifecycle_mapping_rollback(self):
        """ROLLBACK_IN_PROGRESS should map to ESCALATING."""
        context = MascotStateContext(lifecycle_state=LifecycleState.ROLLBACK_IN_PROGRESS)
        result = MascotStateMapper.map(context)
        assert result == MascotState.ESCALATING

    def test_should_animate(self):
        """IDLE and COMPLETE should not animate; others should."""
        assert MascotStateMapper.should_animate(MascotState.IDLE) is False
        assert MascotStateMapper.should_animate(MascotState.COMPLETE) is False
        for state in [
            MascotState.PLANNING, MascotState.EXECUTING,
            MascotState.REVIEWING, MascotState.VERIFYING,
            MascotState.LEARNING, MascotState.ESCALATING,
        ]:
            assert MascotStateMapper.should_animate(state) is True

    def test_is_interruptible_escalation(self):
        """ESCALATING should always interrupt."""
        for current in MascotState:
            assert MascotStateMapper.is_interruptible(current, MascotState.ESCALATING) is True

    def test_is_interruptible_complete(self):
        """COMPLETE should always interrupt."""
        for current in MascotState:
            if current != MascotState.COMPLETE:
                assert MascotStateMapper.is_interruptible(current, MascotState.COMPLETE) is True

    def test_is_interruptible_same_state(self):
        """Same state should not interrupt (except ESCALATING and COMPLETE which always interrupt per spec)."""
        for state in MascotState:
            if state in (MascotState.ESCALATING, MascotState.COMPLETE):
                # ESCALATING and COMPLETE always interrupt per spec §10
                assert MascotStateMapper.is_interruptible(state, state) is True
            else:
                assert MascotStateMapper.is_interruptible(state, state) is False

    def test_is_interruptible_idle_from_active(self):
        """IDLE should interrupt active states."""
        for state in [
            MascotState.PLANNING, MascotState.EXECUTING,
            MascotState.REVIEWING, MascotState.VERIFYING,
            MascotState.LEARNING, MascotState.ESCALATING,
        ]:
            assert MascotStateMapper.is_interruptible(state, MascotState.IDLE) is True

    def test_from_kernel_state(self):
        """from_kernel_state convenience method."""
        result = MascotStateMapper.from_kernel_state(
            lifecycle_state=LifecycleState.OPERATIONAL,
            health_status=HealthStatus.HEALTHY,
        )
        assert result == MascotState.IDLE

    def test_describe_state(self):
        """describe_state should return human-readable descriptions."""
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
        for state, expected in descriptions.items():
            assert MascotStateMapper.describe_state(state) == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])